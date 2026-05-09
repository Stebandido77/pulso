"""Build ``pulso/data/dane_codebook.json`` from per-year DANE DDI XML files.

Pulls one DDI per (year, catalog_id) from
``https://microdatos.dane.gov.co/index.php/metadata/export/{catalog_id}/ddi``,
caches the raw XML under ``.ddi_cache/{year}.xml`` (NOT git-tracked),
parses each via :func:`pulso.metadata.parser.parse_ddi`, merges the
results into the union shape declared by
``pulso/data/schemas/dane_codebook.schema.json``, validates, and writes
the JSON artifact deterministically (sort_keys, UTF-8, indent=2).

Usage
-----

::

    python scripts/build_dane_codebook.py
    python scripts/build_dane_codebook.py --years 2024
    python scripts/build_dane_codebook.py --no-download
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulso.metadata.parser import parse_ddi  # noqa: E402

CATALOG_IDS: dict[int, int] = {
    2007: 317,
    2008: 206,
    2009: 207,
    2010: 205,
    2011: 182,
    2012: 77,
    2013: 68,
    2014: 328,
    2015: 356,
    2016: 427,
    2017: 458,
    2018: 547,
    2019: 599,
    2020: 780,
    2021: 701,
    2022: 771,
    2023: 782,
    2024: 819,
    2025: 853,
    2026: 900,
}

DDI_URL_TMPL = "https://microdatos.dane.gov.co/index.php/metadata/export/{cid}/ddi"

DEFAULT_OUTPUT = ROOT / "pulso/data/dane_codebook.json"
DEFAULT_SCHEMA = ROOT / "pulso/data/schemas/dane_codebook.schema.json"
DEFAULT_CACHE = ROOT / ".ddi_cache"

SCHEMA_VERSION = "1.0.0"

log = logging.getLogger("build_dane_codebook")


def _epoch_for_year(year: int) -> str:
    if year >= 2021:
        return "geih_2021_present"
    return "geih_2006_2020"


def _parse_year_range(spec: str) -> list[int]:
    """Parse '--years' spec: '2007-2026' or '2018,2024' or '2024'."""
    spec = spec.strip()
    if "-" in spec and "," not in spec:
        a, b = spec.split("-", 1)
        return list(range(int(a), int(b) + 1))
    if "," in spec:
        return [int(p) for p in spec.split(",") if p.strip()]
    return [int(spec)]


class EmptyDDIError(RuntimeError):
    """DANE returned HTTP 200 with an empty body — no DDI for that year."""


def _download(year: int, cache_dir: Path, *, timeout: float = 30.0, retries: int = 3) -> Path:
    """Streaming download of one year's DDI; cached on disk.

    Raises :class:`EmptyDDIError` if DANE returns an empty body (some
    catalog entries simply don't have a DDI export — observed for 2013).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{year}.xml"
    if cached.exists() and cached.stat().st_size > 0:
        log.debug("Using cached DDI for %s (%d bytes)", year, cached.stat().st_size)
        return cached

    cid = CATALOG_IDS[year]
    url = DDI_URL_TMPL.format(cid=cid)
    log.info("Downloading DDI for %s from %s", year, url)
    import requests  # imported lazily so --no-download paths don't require it

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=timeout) as resp:
                resp.raise_for_status()
                tmp = cached.with_suffix(".xml.partial")
                with tmp.open("wb") as f:
                    for chunk in resp.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            f.write(chunk)
                size = tmp.stat().st_size
                if size == 0:
                    tmp.unlink(missing_ok=True)
                    raise EmptyDDIError(
                        f"DANE returned empty DDI for year {year} "
                        f"(catalog_id={cid}). No metadata available."
                    )
                tmp.replace(cached)
            log.info("  saved %s (%d bytes)", cached, cached.stat().st_size)
            return cached
        except EmptyDDIError:
            raise
        except (requests.RequestException, OSError) as exc:
            last_exc = exc
            log.warning("  attempt %d failed for %s: %s", attempt, year, exc)
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Failed to download DDI for {year} after {retries} attempts") from last_exc


def _merge_year_into(
    aggregate: dict[str, dict[str, Any]],
    parsed: dict[str, Any],
    year: int,
) -> None:
    """Merge a single parsed year into the running aggregate.

    For each variable code, append/replace ``available_in[year]`` and
    bring forward the most recent year's top-level fields.
    """
    year_str = str(year)
    for code, record in parsed["variables"].items():
        year_entry = record["available_in"][year_str]
        if code not in aggregate:
            # First sighting: clone.
            aggregate[code] = {
                "code": code,
                "label": record["label"],
                "type": record["type"],
                "question_text": record.get("question_text"),
                "universe": record.get("universe"),
                "response_unit": record.get("response_unit"),
                "categories": record.get("categories"),
                "value_range": record.get("value_range"),
                "notes": record.get("notes"),
                "available_in": {year_str: year_entry},
            }
            continue
        agg = aggregate[code]
        agg["available_in"][year_str] = year_entry
        # Top-level fields = most recent year (= max year currently in available_in).
        latest = max(int(y) for y in agg["available_in"])
        if int(year_str) >= latest:
            agg["label"] = record["label"]
            agg["type"] = record["type"]
            agg["question_text"] = record.get("question_text")
            agg["universe"] = record.get("universe")
            agg["response_unit"] = record.get("response_unit")
            agg["categories"] = record.get("categories")
            agg["value_range"] = record.get("value_range")
            agg["notes"] = record.get("notes")


def _build(years: list[int], cache_dir: Path, *, no_download: bool) -> dict[str, Any]:
    aggregate_vars: dict[str, dict[str, Any]] = {}
    epoch_years: dict[str, set[int]] = {"geih_2006_2020": set(), "geih_2021_present": set()}
    actual_years: list[int] = []
    skipped_years: list[tuple[int, str]] = []

    for year in years:
        cache_path = cache_dir / f"{year}.xml"
        if no_download:
            if not cache_path.exists() or cache_path.stat().st_size == 0:
                log.warning("Skipping %s: no usable cached file at %s", year, cache_path)
                skipped_years.append((year, "no cache"))
                continue
        else:
            try:
                cache_path = _download(year, cache_dir)
            except EmptyDDIError as exc:
                log.warning("Skipping %s: %s", year, exc)
                skipped_years.append((year, "empty DDI"))
                continue

        log.info("Parsing %s ...", year)
        parsed = parse_ddi(cache_path, year=year)
        log.info("  Parsed %s: %d unique vars", year, len(parsed["variables"]))
        _merge_year_into(aggregate_vars, parsed, year)
        epoch_years[_epoch_for_year(year)].add(year)
        actual_years.append(year)

    if skipped_years:
        log.warning("Years skipped: %s", skipped_years)

    if not actual_years:
        raise RuntimeError("No years were parsed; check --years and --cache-dir")

    epoch_summary = {
        ek: {
            "years": sorted(yrs),
            "variable_count": sum(
                1
                for v in aggregate_vars.values()
                if any(_epoch_for_year(int(y)) == ek for y in v["available_in"])
            ),
        }
        for ek, yrs in epoch_years.items()
        if yrs
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "DANE DDI-XML 1.2.2",
        "coverage_years": sorted(actual_years),
        "epochs": epoch_summary,
        "variables": aggregate_vars,
    }


def _validate(payload: dict[str, Any], schema_path: Path) -> None:
    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)
    jsonschema.validate(payload, schema)


def _write(payload: dict[str, Any], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    output.write_text(text + "\n", encoding="utf-8")
    return output.stat().st_size


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    p.add_argument(
        "--years",
        default="2007-2026",
        help="Year spec: '2007-2026', '2018,2024', or '2024'. Default: 2007-2026.",
    )
    p.add_argument(
        "--no-download",
        action="store_true",
        help="Use only cached XML files (don't hit the network).",
    )
    p.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Path to the JSON Schema for validation.",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    requested_years = _parse_year_range(args.years)
    invalid = [y for y in requested_years if y not in CATALOG_IDS]
    if invalid:
        log.error("No catalog_id known for years: %s", invalid)
        return 2

    log.info("Building dane_codebook for years: %s", requested_years)
    payload = _build(requested_years, args.cache_dir, no_download=args.no_download)
    _validate(payload, args.schema)
    nbytes = _write(payload, args.output)
    log.info(
        "Total unique variables: %d; written to %s (%d bytes)",
        len(payload["variables"]),
        args.output,
        nbytes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
