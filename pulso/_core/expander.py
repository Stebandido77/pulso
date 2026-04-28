"""Expander: applies survey expansion factors.

NOTE: Naive expansion (multiplying by weight) ignores complex sample design.
For inference-grade analysis, use a survey-aware package like `samplics`.
This module provides a convenience wrapper for descriptive statistics only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def expand(
    df: pd.DataFrame,
    weight: str | None = None,
) -> pd.DataFrame:
    """Add an `_weight` column representing weighted population estimates.

    Args:
        df: DataFrame from `pulso.load(...)`. Must contain the weight variable.
        weight: Name of the weight column. If None, infers from epoch
            (fex_c_2011 for 2006-2020, FEX_C18 for 2021+).

    Returns:
        DataFrame with all original columns plus `_weight` (the weight value)
        and metadata attribute `df.attrs['weight']`.

    Notes:
        Use `df.groupby(...).apply(lambda g: (g[col] * g._weight).sum())` for
        weighted aggregations. For variance estimation, use a survey package.
    """
    raise NotImplementedError("Phase 6: Claude Code")
