"""Merger: joins DataFrames from multiple modules using epoch-appropriate keys."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pulso._utils.exceptions import MergeError

if TYPE_CHECKING:
    import pandas as pd

    from pulso._config.epochs import Epoch


def merge_modules(
    module_dfs: dict[str, pd.DataFrame],
    epoch: Epoch,
    level: Literal["persona", "hogar"] = "persona",
    how: Literal["inner", "outer"] = "outer",
) -> pd.DataFrame:
    """Merge multiple module DataFrames using epoch merge keys.

    Args:
        module_dfs: {module_name: DataFrame} — at least one entry required.
        epoch: Epoch object providing merge_keys_persona / merge_keys_hogar.
        level: "persona" uses all three persona keys; "hogar" drops ORDEN.
        how: pandas merge strategy ("outer" is the default so condicion_actividad
             works correctly — persons can appear in only one of ocupados /
             no_ocupados).

    Returns:
        Merged DataFrame. Column name conflicts get `_{module_name}` suffixes.

    Raises:
        MergeError: If module_dfs is empty or a DataFrame is missing merge keys.
    """
    if not module_dfs:
        raise MergeError("merge_modules called with empty module_dfs.")

    if level == "persona":
        keys = list(epoch.merge_keys_persona)
    elif level == "hogar":
        keys = list(epoch.merge_keys_hogar)
    else:
        raise MergeError(f"Unknown merge level {level!r}. Expected 'persona' or 'hogar'.")

    for name, df in module_dfs.items():
        missing = [k for k in keys if k not in df.columns]
        if missing:
            raise MergeError(
                f"Module {name!r} is missing merge keys {missing}. "
                f"Required for level={level!r} merge."
            )

    items = list(module_dfs.items())
    merged_name, merged = items[0]

    for name, df in items[1:]:
        merged = merged.merge(
            df,
            on=keys,
            how=how,
            suffixes=(f"_{merged_name}", f"_{name}"),
        )
        merged_name = f"{merged_name}+{name}"

    return merged
