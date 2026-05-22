"""Merger: joins DataFrames from multiple modules using epoch-appropriate keys."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from pulso._utils.exceptions import MergeError

if TYPE_CHECKING:
    import pandas as pd

    from pulso._config.epochs import Epoch


def _detect_module_level(df: pd.DataFrame, epoch: Epoch) -> Literal["persona", "hogar"]:
    """Auto-detect module level by inspecting which merge keys are present.

    Returns "persona" if all persona keys (including ORDEN) are present.
    Returns "hogar" if hogar base keys and a HOGAR column are present.

    Raises:
        MergeError: If the module lacks sufficient keys for either level.
    """
    persona_keys = list(epoch.merge_keys_persona)
    hogar_base_keys = list(epoch.merge_keys_hogar)

    if all(k in df.columns for k in persona_keys):
        return "persona"
    if all(k in df.columns for k in hogar_base_keys) and "HOGAR" in df.columns:
        return "hogar"
    raise MergeError(
        f"Module is missing merge keys: expected {persona_keys} (persona level) "
        f"or {[*hogar_base_keys, 'HOGAR']} (hogar level). "
        f"Got columns: {df.columns.tolist()[:10]}"
    )


def _merge_within_level(
    dfs_dict: dict[str, pd.DataFrame],
    keys: list[str],
    how: str,
) -> pd.DataFrame | None:
    """Merge multiple DataFrames on the same keys, deduplicating shared non-key columns."""
    if not dfs_dict:
        return None
    items = list(dfs_dict.items())
    _, merged = items[0]
    merged = merged.copy()
    for _, df in items[1:]:
        existing_non_key = set(merged.columns) - set(keys)
        cols_to_drop = [c for c in df.columns if c in existing_non_key]
        df_to_merge = df.drop(columns=cols_to_drop) if cols_to_drop else df
        merged = merged.merge(df_to_merge, on=keys, how=how)
    return cast("pd.DataFrame", merged)


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
        level: Output level. "persona" (default) auto-detects each module's
            level and performs a multi-level merge: persona modules are merged
            together, hogar modules are merged together, then the hogar result
            is LEFT JOINed into persona on [DIRECTORIO, SECUENCIA_P, HOGAR].
            "hogar" uses legacy behavior: all modules merged on hogar keys
            (ORDEN not required), useful for hogar-level-only operations.
        how: pandas merge strategy ("outer" is the default so condicion_actividad
             works correctly — persons can appear in only one of ocupados /
             no_ocupados).

    Returns:
        Merged DataFrame. Columns that already exist in the running merged
        DataFrame are dropped from each incoming module before the join so that
        shared identifier columns (CLASE, DPTO, FEX_C18, MES, HOGAR, PERIODO)
        appear exactly once rather than getting suffixed variants.

    Raises:
        MergeError: If module_dfs is empty or a DataFrame is missing merge keys.
    """
    if not module_dfs:
        raise MergeError("merge_modules called with empty module_dfs.")

    if level == "hogar":
        # Legacy behavior: all modules merged on hogar keys (ORDEN not required).
        keys = list(epoch.merge_keys_hogar)
        for name, df in module_dfs.items():
            missing = [k for k in keys if k not in df.columns]
            if missing:
                raise MergeError(
                    f"Module {name!r} is missing merge keys {missing}. "
                    f"Required for level={level!r} merge."
                )
        result = _merge_within_level(module_dfs, keys, how)
        assert result is not None  # module_dfs is non-empty
        return result

    if level != "persona":
        raise MergeError(f"Unknown merge level {level!r}. Expected 'persona' or 'hogar'.")

    # level == "persona": auto-detect each module's level, then merge across levels.
    by_level: dict[str, dict[str, pd.DataFrame]] = {"persona": {}, "hogar": {}}
    for name, df in module_dfs.items():
        detected = _detect_module_level(df, epoch)
        by_level[detected][name] = df

    persona_keys = list(epoch.merge_keys_persona)
    hogar_base_keys = list(epoch.merge_keys_hogar)
    hogar_join_keys = [*hogar_base_keys, "HOGAR"]

    persona_merged = _merge_within_level(by_level["persona"], persona_keys, how)
    hogar_merged = _merge_within_level(by_level["hogar"], hogar_join_keys, how)

    if persona_merged is None:
        raise MergeError("Cannot produce persona-level output: no persona-level modules provided.")

    result = persona_merged
    if hogar_merged is not None:
        missing = [k for k in hogar_join_keys if k not in result.columns]
        if missing:
            raise MergeError(
                f"Persona-level merged DataFrame is missing hogar join keys: {missing}"
            )
        # Drop from hogar_merged any non-join columns already present in persona (keep persona's)
        existing_non_join = set(result.columns) - set(hogar_join_keys)
        cols_to_drop = [c for c in hogar_merged.columns if c in existing_non_join]
        hogar_to_merge = hogar_merged.drop(columns=cols_to_drop) if cols_to_drop else hogar_merged
        result = result.merge(hogar_to_merge, on=hogar_join_keys, how="left")

    return result
