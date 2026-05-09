"""Custom harmonization functions for variable_map.json transforms.

Each function is registered via @register("name") and referenced in
variable_map.json as {"op": "custom", "name": "..."}.

Signature for all custom functions:
    fn(df, source_var, variable_entry, epoch) -> pd.Series
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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
        "3" = inactivo   (OCI is NA, DSI is NA)  — heuristic, see PHASE_2_CODE_NOTES.md
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

    oci = df[oci_col]
    dsi = df[dsi_col]

    result = pd.Series(pd.NA, index=df.index, dtype="string")
    result[oci.eq(1)] = "1"  # ocupado
    result[oci.isna() & dsi.eq(1)] = "2"  # desocupado
    result[oci.isna() & dsi.isna()] = "3"  # inactivo (heuristic)

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
