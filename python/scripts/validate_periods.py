"""Validate catalog periods by reproducing DANE's national TD, TO and TGP with pulso.

Valida periodos del catálogo: carga con ``pulso`` los módulos de fuerza de
trabajo de cada mes, calcula TD, TO y TGP nacionales ponderados con el factor
de expansión de la época y los compara con las cifras oficiales de
``data/reference/dane_labor_indicators.csv`` (ver ``fetch_dane_reference.py``).

Definitions (DANE):
    TGP = FT / PET        TO = OC / PET        TD = DS / FT        (en %)

How each piece is resolved
--------------------------
* Weight: ``variable_map.json`` -> ``peso_expansion`` mapping of the epoch
  (``FEX_C`` on the 2005 frame, normalized by the parser; ``FEX_C18`` on the
  2018 frame).
* Labor status: ``variable_map.json`` -> ``condicion_actividad``. On
  ``geih_2021_present`` this is ``merge_labor_status(OCI, DSI)`` and the
  package's own implementation is reused. On ``geih_2006_2020`` the map only
  declares ``OCI`` (identity), which codes employed persons but not the
  unemployed or the inactive: that is a mapping gap, reported in ``notes``.
  For that epoch the status falls back to module membership, which is
  unambiguous because DANE ships Ocupados / Desocupados / Inactivos as
  separate files.
* PET: ``variable_map.json`` has no PET or FT variable (gap, reported in
  ``notes``). PET is the union of the labor-force modules, which DANE only
  administers to the working-age population; FT = OC + DS.

Status: max |pulso - DANE| <= 0.1 pp -> ``pass``; <= 0.5 pp -> ``review``;
otherwise ``fail``. ``pending`` means no official figure for that month;
``error`` means pulso could not load or compute the period.

Usage:
    python python/scripts/validate_periods.py
    python python/scripts/validate_periods.py --periods 2024-01:2026-09 --workers 4
    python python/scripts/validate_periods.py --resume
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_PATH = REPO_ROOT / "data" / "sources.json"
VARIABLE_MAP_PATH = REPO_ROOT / "data" / "variable_map.json"
REFERENCE_PATH = REPO_ROOT / "data" / "reference" / "dane_labor_indicators.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "reference" / "validation_results.csv"

PASS_PP = 0.1
REVIEW_PP = 0.5
LABOR_MODULES = ("ocupados", "desocupados", "inactivos")
MEMBERSHIP_CODE = {"ocupados": "1", "desocupados": "2", "inactivos": "3"}
FINAL_STATUSES = {"pass", "review", "fail", "pending"}

FIELDS = [
    "period",
    "td_pulso",
    "td_dane",
    "to_pulso",
    "to_dane",
    "tgp_pulso",
    "tgp_dane",
    "max_abs_diff_pp",
    "status",
    "notes",
]


class MappingGapError(RuntimeError):
    """variable_map.json cannot resolve something the computation needs."""


# ---------------------------------------------------------------------------
# Pure computation (unit-tested with synthetic microdata)
# ---------------------------------------------------------------------------


def classify_status(max_abs_diff_pp: float | None) -> str:
    if max_abs_diff_pp is None:
        return "pending"
    if max_abs_diff_pp <= PASS_PP + 1e-9:
        return "pass"
    if max_abs_diff_pp <= REVIEW_PP + 1e-9:
        return "review"
    return "fail"


def resolve_weight(var_map: dict[str, Any], epoch: str) -> str:
    try:
        src = var_map["variables"]["peso_expansion"]["mappings"][epoch]["source_variable"]
    except KeyError as exc:
        raise MappingGapError(f"variable_map: peso_expansion has no mapping for {epoch}") from exc
    if not isinstance(src, str):
        raise MappingGapError(f"variable_map: peso_expansion[{epoch}] is not a single column")
    return src


def labor_status_mapping(var_map: dict[str, Any], epoch: str) -> dict[str, Any]:
    try:
        return dict(var_map["variables"]["condicion_actividad"]["mappings"][epoch])
    except KeyError as exc:
        raise MappingGapError(
            f"variable_map: condicion_actividad has no mapping for {epoch}"
        ) from exc


def _numeric_weight(df: pd.DataFrame, wcol: str, module: str) -> pd.Series:
    if wcol not in df.columns:
        raise MappingGapError(f"weight column {wcol!r} missing from module {module!r}")
    w = df[wcol]
    if not pd.api.types.is_numeric_dtype(w):
        # pulso (Python) still returns FEX_C18 as text on the 2018 frame: the
        # CSVs use '.' decimals while the epoch declares ','. Coerce here and
        # report it in notes (see compute_indicators) instead of hiding it.
        w = pd.to_numeric(w.astype("string").str.replace(",", ".", regex=False), errors="coerce")
        w.attrs["coerced_from"] = str(df[wcol].dtype)
    if w.isna().any():
        raise ValueError(f"{int(w.isna().sum())} non-numeric {wcol} values in {module!r}")
    return w.astype(float)


def compute_indicators(
    frames: dict[str, pd.DataFrame],
    epoch: str,
    var_map: dict[str, Any],
    merge_keys: tuple[str, ...],
    shared_file: bool,
) -> tuple[dict[str, float], list[str]]:
    """Compute TD/TO/TGP (in %) from the labor-force module frames.

    Args:
        frames: module name -> DataFrame for ``ocupados``, ``desocupados``,
            ``inactivos``. When ``shared_file`` is True, ``desocupados`` and
            ``inactivos`` are the same "No ocupados" file and only
            ``ocupados`` + ``desocupados`` are used.
        epoch: epoch key (``geih_2006_2020`` / ``geih_2021_present``).
        var_map: parsed ``variable_map.json``.
        merge_keys: person-level keys of the epoch.
        shared_file: whether desocupados and inactivos come from one file.

    Returns:
        ({"td","to","tgp","oc","ds","fft"}, notes)
    """
    from pulso._core.harmonizer_funcs import merge_labor_status

    notes: list[str] = []
    wcol = resolve_weight(var_map, epoch)
    mapping = labor_status_mapping(var_map, epoch)
    transform = mapping.get("transform")
    src = mapping.get("source_variable")
    modules = ("ocupados", "desocupados") if shared_file else LABOR_MODULES

    parts = []
    coerced: list[str] = []
    for mod in modules:
        df = frames[mod]
        weight = _numeric_weight(df, wcol, mod)
        if "coerced_from" in weight.attrs:
            coerced.append(f"{mod}:{weight.attrs['coerced_from']}")
        part = pd.DataFrame({"_w": weight, "_module": mod})
        for k in merge_keys:
            part[k] = df[k].to_numpy() if k in df.columns else pd.NA
        cols = src if isinstance(src, list) else [src]
        for c in cols:
            if c in df.columns:
                part[c] = pd.to_numeric(df[c], errors="coerce").to_numpy()
        parts.append(part)
    universe = pd.concat(parts, ignore_index=True)

    if isinstance(transform, dict) and transform.get("name") == "merge_labor_status":
        for c in src:
            if c not in universe.columns:
                universe[c] = pd.NA
        status = merge_labor_status(universe, src, {}, None)  # type: ignore[arg-type]
        notes.append(f"labor_status=variable_map:merge_labor_status({','.join(src)})")
    elif shared_file:
        raise MappingGapError(
            f"variable_map: condicion_actividad[{epoch}] cannot split unemployed from "
            "inactive inside a shared 'No ocupados' file"
        )
    else:
        status = universe["_module"].map(MEMBERSHIP_CODE)
        notes.append(
            f"labor_status=module_membership (gap: variable_map condicion_actividad[{epoch}] "
            f"solo mapea {src})"
        )
        if isinstance(src, str) and src in universe.columns:
            oc_rows = universe["_module"].eq("ocupados")
            bad = int((~universe.loc[oc_rows, src].eq(1)).sum())
            if bad:
                notes.append(f"{bad} filas de ocupados con {src}!=1")
    notes.append("pet=labor_module_union (gap: variable_map no define PET/FT)")
    notes.append(f"weight={wcol}")
    if coerced:
        notes.append(f"weight_coerced_from_text ({', '.join(coerced)})")

    present_keys = [k for k in merge_keys if universe[k].notna().all()]
    if present_keys:
        dup = int(universe.duplicated(subset=present_keys).sum())
        if dup:
            notes.append(f"{dup} personas repetidas entre modulos")

    if status.isna().any():
        raise ValueError(f"{int(status.isna().sum())} persons without labor status")
    w = universe["_w"]
    oc = float(w[status.eq("1")].sum())
    ds = float(w[status.eq("2")].sum())
    fft = float(w[status.eq("3")].sum())
    ft = oc + ds
    pet = ft + fft
    if pet <= 0 or ft <= 0:
        raise ValueError(f"degenerate totals: PET={pet}, FT={ft}")
    return (
        {
            "td": 100.0 * ds / ft,
            "to": 100.0 * oc / pet,
            "tgp": 100.0 * ft / pet,
            "oc": oc,
            "ds": ds,
            "fft": fft,
        },
        notes,
    )


def compare(pulso_vals: dict[str, float], dane: dict[str, float] | None) -> dict[str, Any]:
    row: dict[str, Any] = {}
    diffs = []
    for k in ("td", "to", "tgp"):
        row[f"{k}_pulso"] = round(pulso_vals[k], 6)
        row[f"{k}_dane"] = None if dane is None else round(dane[k], 6)
        if dane is not None:
            diffs.append(abs(pulso_vals[k] - dane[k]))
    mad = round(max(diffs), 6) if diffs else None
    row["max_abs_diff_pp"] = mad
    row["status"] = classify_status(mad)
    if dane is not None:
        row["_diff_note"] = "diff_pp " + " ".join(
            f"{k.upper()}={pulso_vals[k] - dane[k]:+.3f}" for k in ("td", "to", "tgp")
        )
    return row


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def load_reference(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {
            r["period"]: {"td": float(r["td"]), "to": float(r["to"]), "tgp": float(r["tgp"])}
            for r in csv.DictReader(fh)
        }


def read_results(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {r["period"]: r for r in csv.DictReader(fh)}


def write_results(rows: dict[str, dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for p in sorted(rows):
            w.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in rows[p].items()})
    tmp.replace(path)


def parse_period_range(spec: str | None, available: list[str]) -> list[str]:
    if not spec:
        return sorted(available)
    lo, sep, hi = spec.partition(":")
    if not sep:
        hi = lo
    return sorted(p for p in available if (not lo or p >= lo) and (not hi or p <= hi))


def _module_file_key(entry: dict[str, Any], module: str) -> str:
    return json.dumps(entry["modules"].get(module), sort_keys=True)


class LoadFailedError(RuntimeError):
    """pulso.load skipped the period (strict=False) and returned an empty frame."""


def _load_module(pulso: Any, year: int, month: int, module: str) -> pd.DataFrame:
    """``pulso.load`` with ``strict=False`` (the catalog is mostly unvalidated).

    Under ``strict=False`` a parse failure is not raised: the loader skips the
    month, returns an empty DataFrame and only reports the cause in a
    UserWarning. Surface that cause as an exception so it lands in the CSV.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year, month, module, harmonize=False, show_progress=False, strict=False)
    if df.empty:
        msgs = [str(w.message) for w in caught if "failed to load" in str(w.message)]
        detail = msgs[0] if msgs else "pulso.load returned an empty DataFrame"
        marker = "(e.g., "
        if marker in detail:
            detail = detail.split(marker, 2)[-1].split("). Pass strict=True")[0]
        raise LoadFailedError(f"{module}: {detail}")
    if "DIRECTORIO" not in df.columns:
        raise LoadFailedError(
            f"{module}: no DIRECTORIO column; the file has no recognizable header "
            f"(first columns read: {list(df.columns[:4])})"
        )
    return df


def validate_one(period: str, dane: dict[str, float] | None) -> dict[str, Any]:
    """Load one period with pulso and build its result row (runs in a worker)."""
    import pulso
    from pulso._config.epochs import get_epoch

    warnings.simplefilter("ignore")
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    var_map = json.loads(VARIABLE_MAP_PATH.read_text(encoding="utf-8"))
    entry = sources["data"][period]
    epoch_key = entry["epoch"]
    year, month = int(period[:4]), int(period[5:])
    base: dict[str, Any] = {"period": period}
    started = time.monotonic()
    try:
        missing = [m for m in LABOR_MODULES if m not in entry["modules"]]
        if missing:
            raise MappingGapError(f"sources.json sin modulos {missing}")
        shared = _module_file_key(entry, "desocupados") == _module_file_key(entry, "inactivos")
        epoch = get_epoch(epoch_key)
        mods = ("ocupados", "desocupados") if shared else LABOR_MODULES
        frames = {m: _load_module(pulso, year, month, m) for m in mods}
        vals, notes = compute_indicators(
            frames, epoch_key, var_map, tuple(epoch.merge_keys_persona), shared
        )
        row = compare(vals, dane)
        diff_note = row.pop("_diff_note", None)
        if diff_note:
            notes.insert(0, diff_note)
        else:
            notes.insert(0, "sin cifra oficial DANE para este mes")
        notes.append(f"epoch={epoch_key}")
        notes.append(f"{time.monotonic() - started:.1f}s")
        row["notes"] = "; ".join(notes)
        return {**base, **row}
    except Exception as exc:  # every failure must land in the CSV
        tb = f"{type(exc).__name__}: {exc}".replace("\n", " ")
        return {
            **base,
            "td_dane": None if dane is None else round(dane["td"], 6),
            "to_dane": None if dane is None else round(dane["to"], 6),
            "tgp_dane": None if dane is None else round(dane["tgp"], 6),
            "status": "error",
            "notes": f"{tb[:500]}; epoch={epoch_key}",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--periods", default=None, help="YYYY-MM:YYYY-MM (inclusive).")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true", help="Skip periods already computed.")
    parser.add_argument("--reference", type=Path, default=REFERENCE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    periods = parse_period_range(args.periods, list(sources["data"]))
    reference = load_reference(args.reference)
    results = read_results(args.output)
    todo = [
        p
        for p in periods
        if not (args.resume and results.get(p, {}).get("status") in FINAL_STATUSES)
    ]
    print(
        f"{len(periods)} periodos en rango; {len(periods) - len(todo)} ya calculados; "
        f"{len(todo)} por calcular con {args.workers} worker(s)",
        flush=True,
    )

    t0 = time.monotonic()
    done = 0
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(validate_one, p, reference.get(p)): p for p in todo}
        for fut in as_completed(futures):
            row = fut.result()
            results[row["period"]] = row
            write_results(results, args.output)
            done += 1
            print(
                f"[{done}/{len(todo)}] {row['period']} {row['status']:<7} "
                f"max_abs_diff_pp={row.get('max_abs_diff_pp')}",
                flush=True,
            )

    in_range = [results[p] for p in periods if p in results]
    counts: dict[str, int] = {}
    for r in in_range:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"Tiempo total: {time.monotonic() - t0:.1f}s")
    print("Conteo por status:", json.dumps(dict(sorted(counts.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
