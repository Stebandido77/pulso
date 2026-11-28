"""Validate catalog periods by reproducing DANE's national TD, TO and TGP with pulso.

Valida periodos del catálogo: carga con ``pulso`` los módulos de fuerza de
trabajo de cada mes, calcula TD, TO y TGP nacionales ponderados con el factor
de expansión de la época y los compara con las cifras oficiales de
``data/reference/dane_labor_indicators.csv`` (ver ``fetch_dane_reference.py``).

Definitions (DANE):
    TGP = FT / PET        TO = OC / PET        TD = DS / FT        (en %)

How each piece is resolved
--------------------------
Every piece comes from ``variable_map.json``, through the same path a user
takes: ``pulso.load_merged(year, month, modules, harmonize=True,
variables=[...])`` with Características generales plus the labor modules.

* ``pet``: DANE's working-age population. 12+ in cabeceras and 10+ in
  centros poblados / rural disperso on the 2005 frame; 15+ on the 2018 frame
  (2022+, and 2020, whose microdata are retro-projected to the 2018 frame).
* ``condicion_actividad``: DANE's per-module flags. ``OCI``/``DSI``/``INI`` on
  the 2005 frame; ``OCI``/``DSI``/``FFT`` on the 2018 frame.
* ``fuerza_trabajo``: employed or unemployed (same flags).
* ``peso_expansion``: ``FEX_C`` on the 2005 frame (``fex_c_2011``, normalized
  by the parser), ``FEX_C18`` on the 2018 frame.

PET = sum of weights with ``pet``; FT = with ``fuerza_trabajo``; OC and DS
with ``condicion_actividad`` 1 and 2. Inconsistencies between the
definitions (labor-force members outside the PET, PET members without a
labor status) are counted and written to ``notes``.

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


HARMONIZED_VARIABLES = ["pet", "fuerza_trabajo", "condicion_actividad", "peso_expansion"]


def _numeric_weight(w: pd.Series) -> tuple[pd.Series, str | None]:
    coerced = None
    if not pd.api.types.is_numeric_dtype(w):
        # Report it in notes instead of hiding it (see #77).
        coerced = str(w.dtype)
        w = pd.to_numeric(w.astype("string").str.replace(",", ".", regex=False), errors="coerce")
    return w.astype(float), coerced


def compute_indicators(df: pd.DataFrame) -> tuple[dict[str, float], list[str]]:
    """Compute TD/TO/TGP (in %) from a harmonized, merged person-level frame.

    ``df`` must carry the canonical columns of ``HARMONIZED_VARIABLES`` (the
    output of ``pulso.load_merged(..., harmonize=True)``).

    Returns:
        ({"td","to","tgp","pet","ft","oc","ds"}, notes)
    """
    missing = [c for c in HARMONIZED_VARIABLES if c not in df.columns]
    if missing:
        raise MappingGapError(f"variable_map no resolvio {missing} para este periodo")
    notes: list[str] = ["definiciones=variable_map(pet, fuerza_trabajo, condicion_actividad)"]

    w, coerced = _numeric_weight(df["peso_expansion"])
    if coerced:
        notes.append(f"weight_coerced_from_text ({coerced})")
    pet = df["pet"].astype("boolean")
    ft = df["fuerza_trabajo"].astype("boolean")
    status = df["condicion_actividad"].astype("string")

    in_pet = pet.fillna(False).astype(bool)
    in_ft = ft.fillna(False).astype(bool)
    if w[in_pet].isna().any():
        raise ValueError(
            f"{int(w[in_pet].isna().sum())} personas de la PET sin factor de expansion"
        )

    ft_outside_pet = int((in_ft & ~in_pet).sum())
    pet_without_status = int((in_pet & status.isna()).sum())
    status_outside_pet = int((~in_pet & status.notna()).sum())
    if ft_outside_pet:
        notes.append(f"{ft_outside_pet} personas en FT fuera de la PET")
    if pet_without_status:
        notes.append(f"{pet_without_status} personas de la PET sin condicion_actividad")
    if status_outside_pet:
        notes.append(f"{status_outside_pet} personas con condicion_actividad fuera de la PET")

    pet_w = float(w[in_pet].sum())
    ft_w = float(w[in_ft].sum())
    oc = float(w[status.eq("1").fillna(False).astype(bool)].sum())
    ds = float(w[status.eq("2").fillna(False).astype(bool)].sum())
    if pet_w <= 0 or ft_w <= 0:
        raise ValueError(f"degenerate totals: PET={pet_w}, FT={ft_w}")
    return (
        {
            "td": 100.0 * ds / ft_w,
            "to": 100.0 * oc / pet_w,
            "tgp": 100.0 * ft_w / pet_w,
            "pet": pet_w,
            "ft": ft_w,
            "oc": oc,
            "ds": ds,
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
    """pulso skipped a module (strict=False) and the period cannot be computed."""


def _load_merged(pulso: Any, year: int, month: int, modules: list[str]) -> pd.DataFrame:
    """``pulso.load_merged`` with ``strict=False``; surface skipped modules as errors.

    Under ``strict=False`` a parse failure is not raised: the loader skips it
    and only reports the cause in a UserWarning. A period with a missing
    module cannot be computed, so the cause is raised and lands in the CSV.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load_merged(
            year,
            month,
            modules=modules,
            harmonize=True,
            variables=HARMONIZED_VARIABLES,
            show_progress=False,
            strict=False,
        )
    failed = [str(w.message) for w in caught if "failed to load" in str(w.message)]
    if df.empty or failed:
        detail = failed[0] if failed else "pulso.load_merged returned an empty DataFrame"
        marker = "(e.g., "
        if marker in detail:
            detail = detail.split(marker, 2)[-1].split("). Pass strict=True")[0]
        raise LoadFailedError(detail)
    return df


def validate_one(period: str, dane: dict[str, float] | None) -> dict[str, Any]:
    """Load one period with pulso and build its result row (runs in a worker)."""
    import pulso

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
        labor = ["ocupados", "desocupados"] if shared else list(LABOR_MODULES)
        df = _load_merged(pulso, year, month, ["caracteristicas_generales", *labor])
        vals, notes = compute_indicators(df)
        wcol = resolve_weight(var_map, epoch_key)
        notes.append(f"weight={wcol}")
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
