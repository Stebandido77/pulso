"""Merger: joins DataFrames from multiple modules using epoch-appropriate keys."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from pulso._config.epochs import Epoch


def merge_modules(
    dfs: dict[str, pd.DataFrame],
    module_levels: dict[str, str],
    epoch: Epoch,
    how: str = "left",
) -> pd.DataFrame:
    """Merge multiple module DataFrames.

    Person-level modules merge on persona keys.
    Household-level modules join on hogar keys (broadcast to persons).

    Args:
        dfs: Mapping of module_name -> DataFrame.
        module_levels: Mapping of module_name -> 'persona' or 'hogar'.
        epoch: Epoch object providing merge_keys.
        how: pandas merge strategy. Default 'left' from the first persona module.

    Returns:
        Merged DataFrame.

    Raises:
        MergeError: If keys are missing or incompatible.
    """
    raise NotImplementedError("Phase 2: Claude Code")
