"""Incremental updater for ``data/sources.json`` from the DANE microdata portal.

Run monthly by ``.github/workflows/scrape_monthly.yml``. It only looks at the
annual GEIH catalogs from the latest year already in ``sources.json`` onwards,
so a run takes a few requests instead of a full re-scrape.

Rules (conservative, everything goes through a human-reviewed PR):
  - New periods are added with ``validated: false``. Their ``modules`` block is
    copied from the most recent period of the same epoch, because the
    redesigned-GEIH layout is stable and the R/Python readers tolerate DANE's
    cosmetic filename drift (NBSP, case, renamed files).
  - Existing *unvalidated* periods whose download URL changed (DANE
    republished the file) get the new URL and size; the change is reported.
  - Validated periods are never modified; a URL change on one is only
    reported, so a human re-validates it.

Usage:
    python python/scripts/agent_scraper.py --output data/sources.json \\
        --r-copy r/inst/extdata/sources.json --report scrape_report.md
    python python/scripts/agent_scraper.py --dry-run
    python python/scripts/agent_scraper.py --year 2026        # one catalog year
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("agent_scraper")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _latest_template(data: dict[str, Any], epoch: str) -> dict[str, Any] | None:
    keys = sorted(k for k, v in data.items() if v.get("epoch") == epoch)
    return copy.deepcopy(data[keys[-1]]) if keys else None


def merge_entries(
    sources: dict[str, Any],
    entries: list[dict[str, Any]],
    now: str,
) -> dict[str, list[str]]:
    """Merge scraped catalog entries into ``sources`` in place.

    ``entries`` follow ``scrape_dane_catalog.parse_microdata_files`` output
    (keys: year, month, download_url, landing_page, size_bytes,
    epoch_inferred, file_name). Returns a change log with the keys
    ``added``, ``updated`` and ``flagged``.
    """
    data: dict[str, Any] = sources["data"]
    changes: dict[str, list[str]] = {"added": [], "updated": [], "flagged": []}

    for e in sorted(entries, key=lambda x: (x["year"], x["month"])):
        key = f"{e['year']}-{e['month']:02d}"
        url = e["download_url"].strip()
        existing = data.get(key)

        if existing is None:
            epoch = e["epoch_inferred"]
            template = _latest_template(data, epoch)
            if template is None:
                changes["flagged"].append(f"{key}: no template for epoch {epoch!r}; skipped")
                continue
            template.update(
                {
                    "epoch": epoch,
                    "download_url": url,
                    "landing_page": e.get("landing_page"),
                    "checksum_sha256": None,
                    "size_bytes": e.get("size_bytes"),
                    "scraped_at": now,
                    "validated": False,
                    "validated_by": None,
                    "validated_at": None,
                    "notes": None,
                }
            )
            data[key] = template
            changes["added"].append(f"{key}: {e.get('file_name', '')} -> {url}")
            continue

        if existing.get("download_url", "").strip() == url:
            continue

        if existing.get("validated"):
            changes["flagged"].append(
                f"{key}: validated entry, DANE now serves {url} "
                f"(was {existing.get('download_url')}); left unchanged, re-validate"
            )
            continue

        changes["updated"].append(f"{key}: {existing.get('download_url')} -> {url}")
        existing["download_url"] = url
        existing["size_bytes"] = e.get("size_bytes")
        existing["checksum_sha256"] = None
        existing["scraped_at"] = now

    sources["data"] = dict(sorted(data.items()))
    if changes["added"] or changes["updated"]:
        keys = sorted(sources["data"])
        meta = sources["metadata"]
        meta["covered_range"] = [keys[0], keys[-1]]
        meta["last_updated"] = now.replace("+00:00", "Z")
        meta["data_version"] = now[:7].replace("-", ".")
    return changes


def render_report(changes: dict[str, list[str]], catalogs: list[tuple[int, int, str]]) -> str:
    lines = ["## DANE monthly scrape", ""]
    lines.append(
        "Catalogs checked: " + (", ".join(f"{y} (ID {c})" for c, y, _ in catalogs) or "none")
    )
    lines.append("")
    for title, key in (("Added", "added"), ("Updated URL", "updated"), ("Needs review", "flagged")):
        lines.append(f"### {title} ({len(changes[key])})")
        lines.extend(f"- {item}" for item in changes[key]) if changes[key] else lines.append(
            "- none"
        )
        lines.append("")
    return "\n".join(lines)


def write_sources(sources: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(sources, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "data" / "sources.json")
    parser.add_argument(
        "--r-copy",
        type=Path,
        default=REPO_ROOT / "r" / "inst" / "extdata" / "sources.json",
        help="Also write the result here (R package bundle). Pass '' to skip.",
    )
    parser.add_argument("--report", type=Path, default=Path("scrape_report.md"))
    parser.add_argument("--year", type=int, default=None, help="Only this catalog year.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s"
    )

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scrape_dane_catalog import (
        MICRODATA_URL,
        discover_annual_geih_catalogs,
        fetch_with_retry,
        make_session,
        parse_microdata_files,
    )

    sources = json.loads(args.output.read_text(encoding="utf-8"))
    latest_year = int(max(sources["data"])[:4])
    min_year = args.year if args.year is not None else latest_year

    session = make_session()
    catalogs = [c for c in discover_annual_geih_catalogs(session) if c[1] >= min_year]
    if args.year is not None:
        catalogs = [c for c in catalogs if c[1] == args.year]
    if not catalogs:
        log.error(
            "No annual GEIH catalog found for year >= %d (DANE unreachable or layout changed).",
            min_year,
        )
        args.report.write_text(
            f"## DANE monthly scrape\n\nERROR: no annual catalog found for year >= {min_year}.\n"
        )
        return 1

    entries: list[dict[str, Any]] = []
    for cid, year, _title in catalogs:
        html = fetch_with_retry(MICRODATA_URL.format(cid=cid), session, f"catalog {cid}")
        if html is None:
            log.error("Could not fetch get_microdata for catalog %d", cid)
            return 1
        found, anomalies = parse_microdata_files(html, cid, year)
        for a in anomalies:
            log.warning("catalog %d: %s", cid, a)
        entries.extend(found)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    changes = merge_entries(sources, entries, now)
    report = render_report(changes, catalogs)
    args.report.write_text(report, encoding="utf-8")
    print(report)

    if args.dry_run or not (changes["added"] or changes["updated"]):
        return 0

    write_sources(sources, args.output)
    if args.r_copy and str(args.r_copy):
        write_sources(sources, args.r_copy)
    return 0


if __name__ == "__main__":
    sys.exit(main())
