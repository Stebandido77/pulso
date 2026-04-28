"""Harmonizer: applies variable_map.json transforms to standardize variables.

Supported transforms (from variable_map.schema.json):
    - identity / rename: just rename to canonical name
    - recode: value mapping
    - cast: type conversion
    - compute: safe arithmetic expression
    - coalesce: first non-null across multiple source variables
    - custom: registered Python function
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    import pandas as pd


# Registry for custom transforms. Phase 2 implements the dispatcher.
# Phase 4+ may register epoch-specific custom functions here.
_CUSTOM_TRANSFORMS: dict[str, Callable[..., object]] = {}


def harmonize(
    df: pd.DataFrame,
    module: str,
    epoch: str,
) -> pd.DataFrame:
    """Apply harmonization to a raw module DataFrame.

    Args:
        df: Raw DataFrame from parser (original DANE column names).
        module: Canonical module name (selects which variables apply).
        epoch: Epoch key (selects which mapping to use per variable).

    Returns:
        DataFrame with canonical column names and standardized codings.
        Variables defined in variable_map.json are renamed/transformed;
        other columns are preserved with original names.

    Raises:
        HarmonizationError: If a required source variable is missing or a
            transform fails.
    """
    raise NotImplementedError("Phase 2: Claude Code")


def register_custom_transform(name: str, fn: Callable[..., object]) -> None:
    """Register a named custom transform for use in variable_map.json.

    Custom transforms are referenced as:
        {"op": "custom", "name": "my_transform"}
    """
    raise NotImplementedError("Phase 2: Claude Code")
