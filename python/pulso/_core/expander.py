"""Expander: applies survey expansion factors.

NOTE: Naive expansion (multiplying by weight) ignores complex sample design.
For inference-grade analysis, use a survey-aware package like `samplics`.
This module provides a convenience wrapper for descriptive statistics only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pulso._utils.exceptions import ConfigError

if TYPE_CHECKING:
    import pandas as pd

# Canonical and known DANE-published expansion-weight column names. Listed in
# preference order: `peso_expansion` (canonical/harmonized), then `FEX_C` (the
# pulso-normalised raw column) and historical variants we may still see.
_KNOWN_WEIGHT_COLUMNS: tuple[str, ...] = (
    "peso_expansion",
    "FEX_C",
    "FEX_C18",
    "fex_c_2011",
    "FEX_C_2011",
)


def _infer_weight_column(df: pd.DataFrame) -> str | None:
    """Return the first known weight column present in *df*, or None."""
    for name in _KNOWN_WEIGHT_COLUMNS:
        if name in df.columns:
            return name
    return None


def expand(
    df: pd.DataFrame,
    weight: str | None = None,
) -> pd.DataFrame:
    """Add a ``_weight`` column carrying the survey expansion factor.

    Args:
        df: DataFrame from ``pulso.load(...)``. Must contain a weight column —
            either the canonical ``peso_expansion`` (when ``harmonize=True``)
            or a raw ``FEX_C`` / ``FEX_C18`` column. Pass ``weight=`` if your
            DataFrame uses a non-standard name.
        weight: Name of the weight column. If None, the function looks for
            (in order): ``peso_expansion``, ``FEX_C``, ``FEX_C18``,
            ``fex_c_2011``, ``FEX_C_2011``.

    Returns:
        A *copy* of ``df`` with two changes: a new ``_weight`` column equal
        to the weight values, and ``result.attrs['weight']`` set to the
        column name that was used. The input is not mutated.

    Raises:
        ConfigError: no weight column can be found and ``weight`` was None,
            or the named ``weight`` column is not present in ``df``.

    Notes:
        Use ``df.groupby(...).apply(lambda g: (g[col] * g._weight).sum())`` for
        weighted aggregations. For variance estimation, use a survey-design
        package such as ``samplics``.
    """
    if weight is None:
        weight = _infer_weight_column(df)
        if weight is None:
            raise ConfigError(
                "No weight column found in DataFrame. Expected one of "
                f"{list(_KNOWN_WEIGHT_COLUMNS)}, or pass `weight=` explicitly."
            )

    if weight not in df.columns:
        raise ConfigError(
            f"Weight column {weight!r} not found in DataFrame. "
            f"Available columns include: {df.columns[:10].tolist()}..."
        )

    result = df.copy()
    result["_weight"] = result[weight]
    result.attrs["weight"] = weight
    return result
