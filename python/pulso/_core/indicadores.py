"""Labor-market indicators: ``pulso.indicadores()``.

Indicadores de mercado laboral (TD, TO, TGP) por dominio, mensuales o de
trimestre móvil, calculados con las definiciones de ``variable_map.json``
(``pet``, ``fuerza_trabajo``, ``condicion_actividad``, ``peso_expansion``).

Point estimates only. The public GEIH microdata carry no design variables
(strata, PSU) or replicate weights, so no standard errors are computed; see
``docs/roadmap/w5-errores-estandar.md``. DANE publishes confidence limits and
relative errors in the "Errores relativos" sheet of its monthly annex.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pandas as pd

# AREA codes (city/metropolitan area) in the GEIH microdata.
CITIES_13 = (11, 5, 76, 8, 68, 17, 52, 66, 54, 73, 23, 13, 50)
CITIES_23 = (*CITIES_13, 15, 18, 19, 20, 27, 41, 44, 47, 63, 70)

DOMINIOS = (
    "nacional",
    "cabeceras",
    "centros_poblados_rural",
    "13_ciudades",
    "23_ciudades",
    "ciudad",
    "departamento",
)

HARMONIZED = ["pet", "fuerza_trabajo", "condicion_actividad", "peso_expansion"]
LABOR_MODULES = ("ocupados", "desocupados", "inactivos")


def _labor_modules(record: dict[str, Any]) -> list[str]:
    """Labor modules to merge: Desocupados and Inactivos share one file since 2022."""
    import json

    mods = record["modules"]
    shared = json.dumps(mods.get("desocupados"), sort_keys=True) == json.dumps(
        mods.get("inactivos"), sort_keys=True
    )
    return ["ocupados", "desocupados"] if shared else list(LABOR_MODULES)


def _load_month(year: int, month: int, strict: bool | None, cache: bool) -> pd.DataFrame:
    from pulso._config.registry import _load_sources
    from pulso._core.loader import load_merged

    record = _load_sources()["data"][f"{year}-{month:02d}"]
    modules = ["caracteristicas_generales", *_labor_modules(record)]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = load_merged(
            year,
            month,
            modules=modules,
            harmonize=True,
            variables=HARMONIZED,
            cache=cache,
            show_progress=False,
            strict=strict,
        )
    failed = [str(w.message) for w in caught if "failed to load" in str(w.message)]
    for w in caught:
        if "failed to load" not in str(w.message) and "not been" not in str(w.message):
            warnings.warn(w.message, w.category, stacklevel=3)
    missing = [c for c in HARMONIZED if c not in df.columns]
    if df.empty or failed or missing:
        reason = failed[0] if failed else f"variables {missing} not available"
        raise RuntimeError(f"{year}-{month:02d}: {reason}")
    return df


def _groups(df: pd.DataFrame, dominio: str) -> list[tuple[str, pd.Series]]:
    import pandas as pd

    clase = pd.to_numeric(df["CLASE"], errors="coerce")
    area = pd.to_numeric(df["AREA"], errors="coerce") if "AREA" in df.columns else None
    if dominio == "nacional":
        return [("total", clase.notna() | clase.isna())]
    if dominio == "cabeceras":
        return [("cabeceras", clase.eq(1))]
    if dominio == "centros_poblados_rural":
        return [("centros_poblados_rural", clase.isin([2, 3]))]
    if dominio in ("13_ciudades", "23_ciudades", "ciudad"):
        if area is None:
            raise KeyError("AREA column not in the microdata; city domains need it.")
        if dominio == "13_ciudades":
            return [("13_ciudades", area.isin(CITIES_13))]
        if dominio == "23_ciudades":
            return [("23_ciudades", area.isin(CITIES_23))]
        return [(f"{int(c):02d}", area.eq(c)) for c in sorted(area.dropna().unique())]
    if dominio == "departamento":
        dpto = pd.to_numeric(df["DPTO"], errors="coerce")
        return [(f"{int(d):02d}", dpto.eq(d)) for d in sorted(dpto.dropna().unique())]
    raise ValueError(f"dominio must be one of {DOMINIOS}, got {dominio!r}.")


def _rates(df: pd.DataFrame, weight: pd.Series) -> dict[str, float]:
    pet = df["pet"].astype("boolean").fillna(False).astype(bool)
    ft = df["fuerza_trabajo"].astype("boolean").fillna(False).astype(bool)
    status = df["condicion_actividad"].astype("string")
    oc = status.eq("1").fillna(False).astype(bool)
    ds = status.eq("2").fillna(False).astype(bool)
    pet_w, ft_w = float(weight[pet].sum()), float(weight[ft].sum())
    oc_w, ds_w = float(weight[oc].sum()), float(weight[ds].sum())
    nan = float("nan")
    return {
        "pet": pet_w,
        "ft": ft_w,
        "oc": oc_w,
        "ds": ds_w,
        "td": 100 * ds_w / ft_w if ft_w else nan,
        "to": 100 * oc_w / pet_w if pet_w else nan,
        "tgp": 100 * ft_w / pet_w if pet_w else nan,
    }


def indicadores(
    start: str,
    end: str | None = None,
    dominio: str = "nacional",
    trimestre_movil: bool = False,
    strict: bool | None = None,
    cache: bool = True,
) -> pd.DataFrame:
    """Labor-market rates (TD, TO, TGP) and levels by domain.

    Calcula TD, TO y TGP (y los niveles de PET, FT, ocupados y desocupados)
    con las definiciones de ``variable_map.json``.

    Args:
        start, end: ``'YYYY-MM'``. ``end`` defaults to ``start``. With
            ``trimestre_movil=True`` each row is the quarter ending in that
            month (e.g. ``'2026-09'`` = Jul-Sep 2026), so the two previous
            months are loaded too.
        dominio: ``'nacional'``, ``'cabeceras'``, ``'centros_poblados_rural'``,
            ``'13_ciudades'``, ``'23_ciudades'`` (13 and 23 cities with their
            metropolitan areas, DANE's ``AREA`` codes), ``'ciudad'`` (one row
            per ``AREA`` code) or ``'departamento'`` (one row per ``DPTO``).
        trimestre_movil: Pool each month with the two before it, with the
            expansion factor divided by 3 (DANE's moving-quarter levels are the
            average of the monthly levels).
        strict, cache: as in :func:`pulso.load`.

    Returns:
        DataFrame with ``periodo``, ``meses`` (months pooled), ``dominio``,
        ``grupo``, ``pet``, ``ft``, ``oc``, ``ds`` (persons), ``td``, ``to``,
        ``tgp`` (%) and ``se`` (always NA: the public microdata have no design
        variables; see the module docstring). Months that cannot be computed
        (e.g. 2020-03/04, where DANE published no unemployed file) are
        skipped with a warning.
    """
    import pandas as pd

    from pulso._core.range import period_range, sampling_frame

    if dominio not in DOMINIOS:
        raise ValueError(f"dominio must be one of {DOMINIOS}, got {dominio!r}.")
    end = end or start
    targets = period_range(start, end)
    lag = 2 if trimestre_movil else 0
    needed = period_range(_window(*targets[0], lag)[0], end)

    if len({sampling_frame(y, m) for y, m in needed}) > 1:
        warnings.warn(
            f"The months {needed[0][0]}-{needed[0][1]:02d}..{end} mix microdata on the 2005 "
            "and 2018 census frames; rates are not comparable across frames.",
            UserWarning,
            stacklevel=2,
        )

    monthly: dict[tuple[int, int], pd.DataFrame] = {}
    for y, m in needed:
        try:
            monthly[(y, m)] = _load_month(y, m, strict, cache)
        except RuntimeError as exc:
            if strict:
                raise
            warnings.warn(f"Skipping {exc}", UserWarning, stacklevel=2)

    rows: list[dict[str, Any]] = []
    for y, m in targets:
        window = period_range(*_window(y, m, lag)) if lag else [(y, m)]
        if any(p not in monthly for p in window):
            continue
        pooled = pd.concat([monthly[p] for p in window], ignore_index=True)
        weight = pd.to_numeric(pooled["peso_expansion"], errors="coerce") / len(window)
        for grupo, mask in _groups(pooled, dominio):
            r = _rates(pooled[mask], weight[mask])
            rows.append(
                {
                    "periodo": f"{y}-{m:02d}",
                    "meses": len(window),
                    "dominio": dominio,
                    "grupo": grupo,
                    **r,
                    "se": float("nan"),
                }
            )
    return cast("pd.DataFrame", pd.DataFrame(rows))


def _window(year: int, month: int, lag: int) -> tuple[str, str]:
    idx = year * 12 + month - 1 - lag
    return f"{idx // 12}-{idx % 12 + 1:02d}", f"{year}-{month:02d}"
