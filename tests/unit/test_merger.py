"""Unit tests for pulso._core.merger."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from pulso._core.merger import _detect_module_level, merge_modules
from pulso._utils.exceptions import MergeError


def _epoch(persona_keys=("DIRECTORIO", "SECUENCIA_P", "ORDEN")) -> MagicMock:
    e = MagicMock()
    e.merge_keys_persona = tuple(persona_keys)
    e.merge_keys_hogar = tuple(k for k in persona_keys if k != "ORDEN")
    return e


def _carac(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "DIRECTORIO": [f"{i:04d}" for i in range(1, n + 1)],
            "SECUENCIA_P": [1] * n,
            "ORDEN": [1] * n,
            "EDAD": list(range(20, 20 + n)),
        }
    )


def _ocupados(carac: pd.DataFrame, frac: float = 0.6) -> pd.DataFrame:
    n = int(len(carac) * frac)
    sub = carac.iloc[:n][["DIRECTORIO", "SECUENCIA_P", "ORDEN"]].copy()
    sub["INGLABO"] = [1_000_000.0] * n
    return sub.reset_index(drop=True)


def test_merge_two_modules_persona_level() -> None:
    carac = _carac(10)
    ocup = _ocupados(carac)
    result = merge_modules({"carac": carac, "ocup": ocup}, _epoch())
    assert len(result) == 10
    assert "INGLABO" in result.columns
    assert "EDAD" in result.columns


def test_merge_outer_join_partial_overlap() -> None:
    """Outer join: persons in carac but not ocupados get NaN INGLABO."""
    carac = _carac(10)
    ocup = _ocupados(carac, frac=0.5)
    result = merge_modules({"carac": carac, "ocup": ocup}, _epoch(), how="outer")
    assert len(result) == 10
    assert result["INGLABO"].isna().sum() == 5


def test_merge_three_modules() -> None:
    carac = _carac(10)
    ocup = _ocupados(carac, frac=0.6)
    no_ocup = carac.iloc[6:][["DIRECTORIO", "SECUENCIA_P", "ORDEN"]].copy()
    no_ocup["DSI"] = pd.array([1, 1, None, None], dtype="Int64")
    no_ocup = no_ocup.reset_index(drop=True)

    result = merge_modules(
        {"carac": carac, "ocup": ocup, "no_ocup": no_ocup},
        _epoch(),
        how="outer",
    )
    assert len(result) == 10
    assert "INGLABO" in result.columns
    assert "DSI" in result.columns


def test_merge_raises_on_missing_keys() -> None:
    carac = _carac(5)
    bad = pd.DataFrame({"DIRECTORIO": ["0001"], "SECUENCIA_P": [1]})
    with pytest.raises(MergeError, match="missing merge keys"):
        merge_modules({"carac": carac, "bad": bad}, _epoch())


def test_merge_hogar_level_drops_orden() -> None:
    carac = _carac(5)
    hogar_df = pd.DataFrame(
        {
            "DIRECTORIO": [f"{i:04d}" for i in range(1, 6)],
            "SECUENCIA_P": [1] * 5,
            "TENENCIA": ["propia"] * 5,
        }
    )
    result = merge_modules({"carac": carac, "hogar": hogar_df}, _epoch(), level="hogar")
    assert "TENENCIA" in result.columns
    assert len(result) == 5


def test_merge_inner_only_intersection() -> None:
    carac = _carac(10)
    ocup = _ocupados(carac, frac=0.5)
    result = merge_modules({"carac": carac, "ocup": ocup}, _epoch(), how="inner")
    assert len(result) == 5


def test_merge_empty_dict_raises() -> None:
    with pytest.raises(MergeError, match="empty module_dfs"):
        merge_modules({}, _epoch())


def test_merge_deduplicates_shared_non_key_columns() -> None:
    """Shared non-key columns keep only the first module's version (no suffix)."""
    carac = _carac(5)
    ocup = _ocupados(carac, frac=1.0)
    ocup["EDAD"] = [99] * 5  # EDAD also in carac (values 20-24)

    result = merge_modules({"carac": carac, "ocup": ocup}, _epoch())

    # EDAD should appear exactly once — from carac (the first module)
    edad_cols = [c for c in result.columns if "EDAD" in c]
    assert len(edad_cols) == 1
    assert "EDAD" in result.columns
    assert list(result["EDAD"]) == list(range(20, 25))  # carac values, not ocup's 99


def test_merge_drops_duplicate_non_key_columns() -> None:
    """CLASE in 3 modules should appear exactly once after merge (no suffix variants)."""
    epoch = _epoch()
    keys = list(epoch.merge_keys_persona)

    df1 = pd.DataFrame(
        {**{k: [1, 2, 3] for k in keys}, "CLASE": [1, 1, 1], "MOD1_VAR": [10, 20, 30]}
    )
    df2 = pd.DataFrame(
        {**{k: [1, 2, 3] for k in keys}, "CLASE": [1, 1, 1], "MOD2_VAR": [40, 50, 60]}
    )
    df3 = pd.DataFrame(
        {**{k: [1, 2, 3] for k in keys}, "CLASE": [1, 1, 1], "MOD3_VAR": [70, 80, 90]}
    )

    result = merge_modules({"m1": df1, "m2": df2, "m3": df3}, epoch)

    assert "CLASE" in result.columns
    assert "CLASE_m1" not in result.columns
    assert "CLASE_m2" not in result.columns
    assert "MOD1_VAR" in result.columns
    assert "MOD2_VAR" in result.columns
    assert "MOD3_VAR" in result.columns


# ─── Multi-level merge tests ───────────────────────────────────────────


def test_detect_persona_level() -> None:
    df = pd.DataFrame({"DIRECTORIO": [1], "SECUENCIA_P": [1], "ORDEN": [1], "P3271": [1]})
    assert _detect_module_level(df, _epoch()) == "persona"


def test_detect_hogar_level() -> None:
    df = pd.DataFrame({"DIRECTORIO": [1], "SECUENCIA_P": [1], "HOGAR": [1], "P5090": [1]})
    assert _detect_module_level(df, _epoch()) == "hogar"


def test_merge_persona_and_hogar_propagates_hogar_info() -> None:
    """Hogar-level info is left-joined into all persons sharing that household."""
    persona_df = pd.DataFrame(
        {
            "DIRECTORIO": [1, 1, 2],
            "SECUENCIA_P": [1, 1, 1],
            "ORDEN": [1, 2, 1],
            "HOGAR": [1, 1, 1],
            "P3271": [1, 2, 1],
        }
    )
    hogar_df = pd.DataFrame(
        {
            "DIRECTORIO": [1, 2],
            "SECUENCIA_P": [1, 1],
            "HOGAR": [1, 1],
            "P5090": [1, 3],
        }
    )
    result = merge_modules({"persona": persona_df, "hogar": hogar_df}, _epoch(), level="persona")

    assert len(result) == 3
    assert "P5090" in result.columns
    assert result.iloc[0]["P5090"] == 1
    assert result.iloc[1]["P5090"] == 1
    assert result.iloc[2]["P5090"] == 3


def test_existing_persona_only_merge_still_works() -> None:
    """Backward compatibility: persona-only merges produce identical results."""
    df1 = pd.DataFrame(
        {"DIRECTORIO": [1, 2], "SECUENCIA_P": [1, 1], "ORDEN": [1, 1], "X": [10, 20]}
    )
    df2 = pd.DataFrame(
        {"DIRECTORIO": [1, 2], "SECUENCIA_P": [1, 1], "ORDEN": [1, 1], "Y": [30, 40]}
    )
    result = merge_modules({"a": df1, "b": df2}, _epoch(), level="persona")
    assert len(result) == 2
    assert "X" in result.columns
    assert "Y" in result.columns
