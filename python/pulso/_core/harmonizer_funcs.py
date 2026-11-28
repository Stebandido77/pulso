"""Custom harmonization functions for variable_map.json transforms.

Each function is registered via @register("name") and referenced in
variable_map.json as {"op": "custom", "name": "..."}.

Signature for all custom functions:
    fn(df, source_var, variable_entry, epoch) -> pd.Series
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from pulso._utils.exceptions import ConfigError, HarmonizationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from pulso._config.epochs import Epoch

CUSTOM_FUNCTIONS: dict[str, Callable[..., pd.Series]] = {}


def register(name: str) -> Callable[[Callable[..., pd.Series]], Callable[..., pd.Series]]:
    """Decorator: register a custom harmonization function under `name`."""

    def wrapper(fn: Callable[..., pd.Series]) -> Callable[..., pd.Series]:
        if name in CUSTOM_FUNCTIONS:
            raise ValueError(f"Custom function {name!r} already registered.")
        CUSTOM_FUNCTIONS[name] = fn
        return fn

    return wrapper


def get_custom(name: str) -> Callable[..., pd.Series]:
    """Return a registered custom function, or raise ConfigError."""
    if name not in CUSTOM_FUNCTIONS:
        raise ConfigError(f"Custom function {name!r} not registered in CUSTOM_FUNCTIONS.")
    return CUSTOM_FUNCTIONS[name]


@register("bin_edad_quinquenal")
def bin_edad_quinquenal(
    df: pd.DataFrame,
    source_var: str | list[str],
    _variable_entry: dict,
    _epoch: Epoch,
) -> pd.Series:
    """Cut edad (P6040) into 14 quinquennial bins matching grupo_edad.categories."""
    col = source_var[0] if isinstance(source_var, list) else source_var

    if col not in df.columns:
        raise HarmonizationError(f"bin_edad_quinquenal: column {col!r} not found in DataFrame.")

    age = df[col]
    bins = [-0.001, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, np.inf]
    labels = [
        "0-4",
        "5-9",
        "10-14",
        "15-19",
        "20-24",
        "25-29",
        "30-34",
        "35-39",
        "40-44",
        "45-49",
        "50-54",
        "55-59",
        "60-64",
        "65+",
    ]

    result = pd.cut(age, bins=bins, labels=labels, right=True, include_lowest=True)
    return result.astype("string")


@register("merge_labor_status")
def merge_labor_status(
    df: pd.DataFrame,
    source_var: str | list[str],
    _variable_entry: dict,
    _epoch: Epoch,
) -> pd.Series:
    """Combine OCI (ocupados) and DSI (no_ocupados) into condicion_actividad code.

    Expects a PRE-MERGED DataFrame containing both OCI and DSI columns.
    The merger is responsible for producing this merged DF via outer join.

    Coding:
        "1" = ocupado   (OCI == 1)
        "2" = desocupado (OCI is NA, DSI == 1)
        "3" = inactivo   (OCI is NA, DSI is NA or 0)  — heuristic, see PHASE_2_CODE_NOTES.md

    DANE coded DSI as 1/blank until 2026-07 and as 1/0 from 2026-08 onwards
    (pulso #76); both 0 and blank mean "not unemployed", so both map to "3".
    """
    if not isinstance(source_var, list) or len(source_var) < 2:
        raise ConfigError("merge_labor_status requires source_variable as a list ['OCI', 'DSI'].")

    oci_col, dsi_col = source_var[0], source_var[1]

    missing = [c for c in (oci_col, dsi_col) if c not in df.columns]
    if missing:
        raise HarmonizationError(
            f"merge_labor_status: columns {missing} not found in DataFrame. "
            "Did you forget to merge ocupados and no_ocupados modules?"
        )

    oci = _num(df[oci_col])
    dsi = _num(df[dsi_col])

    result = pd.Series(pd.NA, index=df.index, dtype="string")
    result[oci.eq(1)] = "1"  # ocupado
    result[oci.isna() & dsi.eq(1)] = "2"  # desocupado
    if "FFT" in df.columns:
        # DANE's own flag: FFT == 1 marks persons outside the labor force in
        # No ocupados.CSV. Persons that are in neither module (under 15, not
        # in the PET) stay NA instead of being coded inactive (#79).
        result[oci.isna() & ~dsi.eq(1) & _num(df["FFT"]).eq(1)] = "3"
    else:
        result[oci.isna() & (dsi.isna() | dsi.eq(0))] = "3"  # inactivo (heuristic)

    return result


def _num(s: pd.Series) -> pd.Series:
    """Numeric view of a DANE flag column (blank/text -> NaN)."""
    return pd.to_numeric(s, errors="coerce")


def _flag_columns(source_var: str | list[str], name: str, df: pd.DataFrame) -> list[pd.Series]:
    if not isinstance(source_var, list) or len(source_var) != 3:
        raise ConfigError(
            f"{name} requires source_variable as a list of three flags "
            "[employed, unemployed, outside_labor_force]."
        )
    missing = [c for c in source_var if c not in df.columns]
    if missing:
        raise HarmonizationError(
            f"{name}: columns {missing} not found in DataFrame. "
            "Load the labor modules together with load_merged()."
        )
    return [_num(df[c]) for c in source_var]


@register("labor_status_from_flags")
def labor_status_from_flags(
    df: pd.DataFrame,
    source_var: str | list[str],
    _variable_entry: dict[str, Any],
    _epoch: Epoch,
) -> pd.Series:
    """condicion_actividad from DANE's per-module flags.

    ``source_var`` = [employed, unemployed, outside] flags, each 1 for the
    persons of its module: ``[OCI, DSI, INI]`` on the 2005 frame (Ocupados,
    Desocupados, Inactivos files) and ``[OCI, DSI, FFT]`` on the 2018 frame
    (Ocupados and No ocupados files). Coding: "1" ocupado, "2" desocupado,
    "3" inactivo, NA for persons in none of the modules (outside the PET).
    """
    occ, unemp, outside = _flag_columns(source_var, "labor_status_from_flags", df)
    result = pd.Series(pd.NA, index=df.index, dtype="string")
    result[outside.eq(1)] = "3"
    result[unemp.eq(1)] = "2"
    result[occ.eq(1)] = "1"
    return result


@register("labor_force_from_flags")
def labor_force_from_flags(
    df: pd.DataFrame,
    source_var: str | list[str],
    _variable_entry: dict[str, Any],
    _epoch: Epoch,
) -> pd.Series:
    """fuerza_trabajo (FT): True for employed or unemployed, False for inactive.

    Same flags as ``labor_status_from_flags``; NA outside the PET.
    """
    occ, unemp, outside = _flag_columns(source_var, "labor_force_from_flags", df)
    result = pd.Series(pd.NA, index=df.index, dtype="boolean")
    result[outside.eq(1)] = False
    result[occ.eq(1) | unemp.eq(1)] = True
    return result


@register("pet_by_age_zone")
def pet_by_age_zone(
    df: pd.DataFrame,
    source_var: str | list[str],
    variable_entry: dict[str, Any],
    epoch: Epoch,
) -> pd.Series:
    """pet: True if the person is in the working-age population (PET).

    ``source_var`` = [age, CLASE]. Thresholds come from the mapping's
    ``transform.params``: ``min_age_urban`` (CLASE == 1) and
    ``min_age_rural`` (CLASE 2 or 3). ``frame_2018_periods`` lists
    ``[start, end]`` month ranges of this epoch whose microdata are on the
    2018 frame (2020, see docs/caveats.md); for those, ``frame_2018_min_age``
    applies to everyone. The period is read from ``df.attrs["pulso_period"]``
    ("YYYY-MM"), which ``load()`` and ``load_merged()`` set.
    """
    if not isinstance(source_var, list) or len(source_var) != 2:
        raise ConfigError("pet_by_age_zone requires source_variable [age, CLASE].")
    age_col, zone_col = source_var
    params = variable_entry["mappings"][epoch.key]["transform"].get("params", {})
    urban = params["min_age_urban"]
    rural = params["min_age_rural"]
    period = df.attrs.get("pulso_period")
    if period is not None:
        for lo, hi in params.get("frame_2018_periods", []):
            if lo <= period <= hi:
                urban = rural = params["frame_2018_min_age"]
                break

    age = _num(df[age_col])
    zone = _num(df[zone_col])
    threshold = pd.Series(np.where(zone.eq(1), urban, rural), index=df.index, dtype="float")
    threshold[zone.isna()] = np.nan if urban != rural else urban
    result = (age >= threshold).astype("boolean")
    result[age.isna() | threshold.isna()] = pd.NA
    return result


@register("compute_ingreso_total")
def compute_ingreso_total(
    df: pd.DataFrame,
    source_var: str | list[str],
    _variable_entry: dict,
    _epoch: Epoch,
) -> pd.Series:
    """Sum INGLABO + non-labor income components to construct ingreso_total.

    INGTOT is absent in GEIH-2 monthly microdata; this function reconstructs
    it by summing all available income sub-components. Missing components are
    treated as 0 (fillna=0) before summing.
    """
    source_cols = [source_var] if isinstance(source_var, str) else list(source_var)

    available = [c for c in source_cols if c in df.columns]
    if not available:
        raise HarmonizationError(
            f"compute_ingreso_total: none of the declared source columns "
            f"{source_cols} found in DataFrame."
        )

    sub = df[available].fillna(0)
    return sub.sum(axis=1)
