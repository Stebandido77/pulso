"""Multi-month loads: ``pulso.load_range()`` and pooled (moving-quarter) weights.

Carga de varios meses consecutivos con una columna ``periodo`` y, si se pide,
el factor de expansión promediado para agregados de varios meses (trimestre
móvil).
"""

from __future__ import annotations

import re
import warnings
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pandas as pd

    from pulso._core.parser import Area

_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")

# Microdata on the 2018 sampling frame: the redesigned GEIH (2022+) and 2020,
# whose files DANE re-weighted to the 2018 census (catalog 780; see
# docs/caveats.md). Everything else is on the 2005 frame.
FRAME_2018_FROM = (2022, 1)
FRAME_2018_EXTRA_YEARS = frozenset({2020})

POOLED_WEIGHT = "peso_expansion_promedio"


def sampling_frame(year: int, month: int) -> str:
    """'2005' or '2018': the census frame the period's microdata are on."""
    if (year, month) >= FRAME_2018_FROM or year in FRAME_2018_EXTRA_YEARS:
        return "2018"
    return "2005"


def _parse_period(value: str, name: str) -> tuple[int, int]:
    m = _PERIOD_RE.match(str(value))
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise ValueError(f"{name} must be 'YYYY-MM', got {value!r}.")
    return int(m.group(1)), int(m.group(2))


def period_range(start: str, end: str) -> list[tuple[int, int]]:
    """Inclusive list of (year, month) from ``start`` to ``end`` ('YYYY-MM')."""
    y, m = _parse_period(start, "start")
    y_end, m_end = _parse_period(end, "end")
    if (y, m) > (y_end, m_end):
        raise ValueError(f"start {start!r} is after end {end!r}.")
    out: list[tuple[int, int]] = []
    while (y, m) <= (y_end, m_end):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _weight_column(df: pd.DataFrame, year: int, month: int) -> str:
    """Expansion-factor column of one period: canonical if harmonized, raw otherwise."""
    if "peso_expansion" in df.columns:
        return "peso_expansion"
    from pulso._config.epochs import epoch_for_month
    from pulso._config.registry import _load_variable_map

    epoch = epoch_for_month(year, month)
    vm = _load_variable_map()
    src = vm["variables"]["peso_expansion"]["mappings"][epoch.key]["source_variable"]
    if src not in df.columns:
        raise KeyError(
            f"Expansion factor {src!r} not in the loaded columns for {year}-{month:02d}; "
            "include it in columns= to use average_weights=True."
        )
    return str(src)


def load_range(
    start: str,
    end: str,
    module: str = "caracteristicas_generales",
    area: Area = "total",
    harmonize: bool = True,
    columns: list[str] | None = None,
    cache: bool = True,
    show_progress: bool = True,
    strict: bool | None = None,
    average_weights: bool = False,
    deflate_to: str | None = None,
    income_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Load consecutive months of one module, stacked with a ``periodo`` column.

    Carga meses consecutivos de un módulo, apilados con una columna ``periodo``.

    Each month goes through :func:`pulso.load` with ``harmonize`` applied with
    its own epoch's mapping, so the canonical columns line up across epochs;
    raw DANE columns that exist only in some months are NaN in the others.

    Args:
        start, end: Inclusive bounds, ``'YYYY-MM'`` (e.g. ``'2026-07'``).
        module, area, harmonize, columns, cache, show_progress, strict: as
            in :func:`pulso.load`.
        average_weights: If True, add ``peso_expansion_promedio`` = expansion
            factor / number of months loaded. Each monthly file expands to the
            whole population, so pooling *n* months with the raw factor counts
            everyone *n* times; DANE's moving-quarter levels are the average of
            the monthly levels (the "Total nacional Trim" sheet of
            ``anex-GEIH-<mes><año>.xlsx``), i.e. factor / 3. Rates (TD, TO,
            TGP) are the same with either factor.
        deflate_to: If given ('YYYY-MM'), add ``<col>_real`` columns in pesos
            of that month with DANE's IPC (:func:`pulso.deflactar`).
        income_columns: Columns to deflate. Default: the ones present among
            ``ingreso_laboral``, ``ingreso_total`` (canonical) and ``INGLABO``.

    Returns:
        DataFrame with ``periodo`` ('YYYY-MM'), ``year`` and ``month`` columns.

    Warns:
        UserWarning: if the range mixes microdata on the 2005 and the 2018
        census frames (2022-01 onwards, and 2020). Levels and rates across
        frames are not comparable (different population projections and
        working-age definitions).
    """
    import pandas as pd

    from pulso._core.loader import load

    periods = period_range(start, end)
    frames_used = sorted({sampling_frame(y, m) for y, m in periods})
    if len(frames_used) > 1:
        by_frame: dict[str, list[str]] = {}
        for y, m in periods:
            by_frame.setdefault(sampling_frame(y, m), []).append(f"{y}-{m:02d}")
        detail = "; ".join(
            f"marco {f}: {v[0]}..{v[-1]} ({len(v)} meses)" for f, v in by_frame.items()
        )
        warnings.warn(
            f"The range {start}..{end} mixes microdata on the 2005 and 2018 census "
            f"frames ({detail}). Levels and rates are not comparable across frames.",
            UserWarning,
            stacklevel=2,
        )

    by_year: dict[int, list[int]] = {}
    for y, m in periods:
        by_year.setdefault(y, []).append(m)

    kwargs: dict[str, Any] = {
        "module": module,
        "area": area,
        "harmonize": harmonize,
        "columns": columns,
        "cache": cache,
        "show_progress": show_progress,
        "strict": strict,
    }
    parts: list[pd.DataFrame] = []
    for y, months in by_year.items():
        df = load(y, months, **kwargs)
        if df.empty:
            continue
        if "year" not in df.columns:  # single-period load: no year/month columns
            df = df.assign(year=y, month=months[0])
        parts.append(df)

    if not parts:
        return cast("pd.DataFrame", pd.DataFrame(columns=["periodo", "year", "month"]))
    out = pd.concat(parts, ignore_index=True)
    out.insert(
        0, "periodo", [f"{y}-{m:02d}" for y, m in zip(out["year"], out["month"], strict=True)]
    )

    if average_weights:
        n_months = out["periodo"].nunique()
        pooled = pd.Series(float("nan"), index=out.index)
        for period in out["periodo"].unique():
            y, m = _parse_period(str(period), "periodo")
            mask = out["periodo"] == period
            wcol = _weight_column(out, y, m)
            pooled[mask] = pd.to_numeric(out.loc[mask, wcol], errors="coerce") / n_months
        out[POOLED_WEIGHT] = pooled
    if deflate_to is not None:
        from pulso._core.real_income import deflactar

        cols = income_columns or [
            c for c in ("ingreso_laboral", "ingreso_total", "INGLABO") if c in out.columns
        ]
        out = deflactar(out, cols, deflate_to)
    return out
