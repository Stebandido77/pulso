"""Harmonizer: applies variable_map.json transforms to standardize variables.

Supported transforms (from variable_map.schema.json):
    - identity / rename: copy source column to canonical name
    - recode: value-level mapping (string keys, Decision 4)
    - cast: type conversion (int→Int64, bool→BooleanDtype, etc.)
    - compute: safe expression via pd.DataFrame.eval() or manual parse
    - coalesce: first non-null across multiple source columns
    - custom: registered Python function from harmonizer_funcs.py
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pandas as pd

from pulso._config.registry import _load_variable_map
from pulso._utils.exceptions import ConfigError, HarmonizationError

if TYPE_CHECKING:
    from collections.abc import Generator

    from pulso._config.epochs import Epoch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _iter_relevant_variables(
    epoch: Epoch,
    variables: list[str] | None,
) -> Generator[tuple[str, dict[str, Any]], None, None]:
    """Yield (canonical_name, variable_entry) for variables applicable to epoch."""
    vm = _load_variable_map()
    for canonical_name, entry in vm["variables"].items():
        if variables is not None and canonical_name not in variables:
            continue
        if epoch.key not in entry.get("mappings", {}):
            continue
        yield canonical_name, entry


def _apply_recode(
    source: pd.Series,
    mapping: dict[str, Any],
    default: Any,
    canonical_name: str,
) -> pd.Series:
    """Map source values through `mapping`; use `default` for unmapped non-null values.

    Source is cast to StringDtype before lookup so int64/float64 values like 1
    become "1" to match JSON string keys.
    """
    str_source = source.astype("string")

    if default is None:
        unmapped_mask = ~str_source.isin(mapping.keys()) & str_source.notna()
        if unmapped_mask.any():
            unmapped_values = str_source[unmapped_mask].unique().tolist()
            raise HarmonizationError(
                f"Variable {canonical_name!r}: recode mapping does not cover values "
                f"{unmapped_values}. Extend mapping in variable_map.json or set 'default'."
            )
        return str_source.map(mapping)
    return str_source.map(mapping).fillna(default).where(str_source.notna(), other=pd.NA)


def _apply_cast(source: pd.Series, to: str, canonical_name: str) -> pd.Series:
    """Cast source Series to the target dtype."""
    try:
        if to == "int":
            return source.astype("Int64")
        if to == "float":
            return source.astype("float64")
        if to == "str":
            return source.astype("string")
        if to == "category":
            return source.astype("category")
        if to == "bool":
            return source.astype("boolean")
        raise ConfigError(f"Variable {canonical_name!r}: unknown cast target {to!r}.")
    except (ValueError, TypeError) as exc:
        raise HarmonizationError(
            f"Variable {canonical_name!r}: cast to {to!r} failed: {exc}"
        ) from exc


def _apply_compute_string_concat(
    df: pd.DataFrame,
    expr: str,
    _source_vars: list[str],
    canonical_name: str,
) -> pd.Series:
    """Manually evaluate string-concatenation expressions that use .astype(str).

    Handles the specific pattern:
        COL_A.astype(str) + '_' + COL_B.astype(str) + ...
    """
    parts = [p.strip() for p in expr.split(" + ")]
    pieces: list[pd.Series | str] = []

    for part in parts:
        if (part.startswith("'") and part.endswith("'")) or (
            part.startswith('"') and part.endswith('"')
        ):
            pieces.append(part[1:-1])
        elif ".astype(str)" in part:
            col = part.replace(".astype(str)", "").strip()
            if col not in df.columns:
                raise HarmonizationError(
                    f"Variable {canonical_name!r}: column {col!r} not found in DataFrame "
                    "(needed by compute string-concat expression)."
                )
            pieces.append(df[col].astype(str))
        else:
            raise HarmonizationError(
                f"Variable {canonical_name!r}: cannot parse compute expression "
                f"part {part!r}. Only '<col>.astype(str)' and string literals supported."
            )

    result: pd.Series | None = None
    for piece in pieces:
        if result is None:
            if isinstance(piece, str):
                result = pd.Series([piece] * len(df), index=df.index, dtype="string")
            else:
                result = piece.astype("string")
        else:
            result = result + piece if isinstance(piece, str) else result + piece.astype("string")

    return result if result is not None else pd.Series(dtype="string")


def _apply_compute(
    df: pd.DataFrame,
    expr: str,
    source_vars: list[str],
    canonical_name: str,
) -> pd.Series:
    """Evaluate `expr` in the context of `df`.

    Uses pd.DataFrame.eval() for arithmetic/boolean expressions. Falls back
    to manual string-concat parsing when the expression contains .astype(str).

    Security: pd.DataFrame.eval() does NOT use Python's builtin eval().
    """
    if ".astype(str)" in expr:
        return _apply_compute_string_concat(df, expr, source_vars, canonical_name)

    sub_df = df[source_vars] if source_vars else df
    try:
        result: pd.Series = sub_df.eval(expr, engine="python")
    except Exception as exc:
        raise HarmonizationError(
            f"Variable {canonical_name!r}: compute expression {expr!r} failed: {exc}"
        ) from exc
    return result


def _apply_coalesce(sub_df: pd.DataFrame, canonical_name: str) -> pd.Series:
    """Return first non-null value across columns (left-to-right)."""
    if sub_df.shape[1] == 0:
        raise HarmonizationError(
            f"Variable {canonical_name!r}: coalesce requires at least one source column."
        )
    result = sub_df.iloc[:, 0].copy()
    for col in sub_df.columns[1:]:
        result = result.fillna(sub_df[col])
    return result


def _validate_categorical_domain(
    series: pd.Series,
    variable_entry: dict[str, Any],
    canonical_name: str,
) -> None:
    """Raise HarmonizationError if non-null values fall outside categories keys."""
    categories = variable_entry.get("categories", {})
    if not categories:
        return

    valid_keys = set(categories.keys())
    non_null = series.dropna()
    if len(non_null) == 0:
        return

    str_values = non_null.astype(str)
    invalid_mask = ~str_values.isin(valid_keys)
    if invalid_mask.any():
        invalid_vals = str_values[invalid_mask].unique().tolist()
        raise HarmonizationError(
            f"Variable {canonical_name!r}: out-of-domain categorical values found: "
            f"{invalid_vals}. Valid domain: {sorted(valid_keys)}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def harmonize_variable(
    df: pd.DataFrame,
    canonical_name: str,
    variable_entry: dict[str, Any],
    epoch: Epoch,
) -> pd.Series:
    """Apply the variable_map transform for the given epoch.

    Returns a Series named `canonical_name`. Raises HarmonizationError if the
    source column is missing, a recode value is unmapped, a cast fails, or a
    categorical value falls outside its domain.
    """
    mappings = variable_entry.get("mappings", {})
    if epoch.key not in mappings:
        raise ConfigError(f"Variable {canonical_name!r} has no mapping for epoch {epoch.key!r}.")

    mapping = mappings[epoch.key]
    source_var: str | list[str] = mapping["source_variable"]
    transform: str | dict[str, Any] = mapping["transform"]

    source_cols = [source_var] if isinstance(source_var, str) else list(source_var)

    missing = [c for c in source_cols if c not in df.columns]
    if missing:
        raise HarmonizationError(
            f"Variable {canonical_name!r}: source columns missing in DataFrame: {missing}. "
            f"Required for epoch {epoch.key!r}."
        )

    # --- Dispatch on transform type ---

    if isinstance(transform, str):
        if transform in ("identity", "rename"):
            if isinstance(source_var, list):
                raise ConfigError(
                    f"Variable {canonical_name!r}: identity/rename requires a single "
                    f"source_variable, got a list."
                )
            result = df[source_var].copy()
        else:
            raise ConfigError(
                f"Variable {canonical_name!r}: unknown string transform {transform!r}."
            )

    elif isinstance(transform, dict):
        op = transform.get("op")

        if op == "recode":
            if isinstance(source_var, list):
                raise ConfigError(
                    f"Variable {canonical_name!r}: recode requires a single source_variable."
                )
            result = _apply_recode(
                df[source_var],
                transform["mapping"],
                transform.get("default"),
                canonical_name,
            )

        elif op == "cast":
            if isinstance(source_var, list):
                raise ConfigError(
                    f"Variable {canonical_name!r}: cast requires a single source_variable."
                )
            result = _apply_cast(df[source_var], transform["to"], canonical_name)

        elif op == "compute":
            result = _apply_compute(df, transform["expr"], source_cols, canonical_name)

        elif op == "coalesce":
            result = _apply_coalesce(df[source_cols], canonical_name)

        elif op == "custom":
            from pulso._core.harmonizer_funcs import get_custom

            fn = get_custom(transform["name"])
            result = fn(df, source_var, variable_entry, epoch)

        else:
            raise ConfigError(f"Variable {canonical_name!r}: unknown transform op {op!r}.")

    else:
        raise ConfigError(
            f"Variable {canonical_name!r}: invalid transform type {type(transform)!r}."
        )

    # --- Post-transform: cast boolean type ---
    if variable_entry.get("type") == "boolean":
        try:
            result = result.astype("boolean")
        except (TypeError, ValueError) as exc:
            raise HarmonizationError(
                f"Variable {canonical_name!r}: cannot cast result to BooleanDtype: {exc}"
            ) from exc

    # --- Post-transform: categorical domain validation ---
    if variable_entry.get("type") == "categorical":
        _validate_categorical_domain(result, variable_entry, canonical_name)

    return result.rename(canonical_name)


def harmonize_dataframe(
    df: pd.DataFrame,
    epoch: Epoch,
    variables: list[str] | None = None,
    keep_raw: bool = True,
) -> pd.DataFrame:
    """Harmonize multiple variables from variable_map for the given epoch.

    If `variables` is None, harmonizes all mapped variables whose source
    columns are present in df. Variables with missing source columns are
    silently skipped with a warning.

    If keep_raw=True (default), preserves ALL original raw columns alongside
    the canonical harmonized columns. This is the recommended default so
    researchers have access to both the 30 canonical variables and all raw
    DANE columns.

    Returns a new DataFrame; the input is not mutated.
    """
    canonical_series_list: list[pd.Series] = []

    for canonical_name, entry in _iter_relevant_variables(epoch, variables):
        try:
            series = harmonize_variable(df, canonical_name, entry, epoch)
            canonical_series_list.append(series)
        except HarmonizationError as exc:
            logger.warning("Skipping variable %r: %s", canonical_name, exc)
            continue

    if not canonical_series_list:
        canonical_df = pd.DataFrame(index=df.index)
    else:
        canonical_df = pd.concat(canonical_series_list, axis=1)

    if keep_raw:
        return pd.concat([df, canonical_df], axis=1)
    return canonical_df
