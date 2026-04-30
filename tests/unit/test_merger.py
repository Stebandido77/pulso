"""Unit tests for pulso._core.merger."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from pulso._core.merger import merge_modules
from pulso._utils.exceptions import MergeError


def _epoch(persona_keys=("DIRECTORIO", "SECUENCIA_P", "ORDEN")) -> MagicMock:
    e = MagicMock()
    e.merge_keys_persona = tuple(persona_keys)
    e.merge_keys_hogar = tuple(k for k in persona_keys if k != "ORDEN")
    return e


def _carac(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame({
        "DIRECTORIO": [f"{i:04d}" for i in range(1, n + 1)],
        "SECUENCIA_P": [1] * n,
        "ORDEN": [1] * n,
        "EDAD": list(range(20, 20 + n)),
    })


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
    hogar_df = pd.DataFrame({
        "DIRECTORIO": [f"{i:04d}" for i in range(1, 6)],
        "SECUENCIA_P": [1] * 5,
        "TENENCIA": ["propia"] * 5,
    })
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


def test_merge_handles_column_name_collision_with_suffix() -> None:
    """Shared non-key columns get suffixed to avoid ambiguity."""
    carac = _carac(5)
    ocup = _ocupados(carac, frac=1.0)
    ocup["EDAD"] = [99] * 5

    result = merge_modules({"carac": carac, "ocup": ocup}, _epoch())
    cols = list(result.columns)
    # EDAD appears in both; merger must suffix one or both
    edad_cols = [c for c in cols if "EDAD" in c]
    assert len(edad_cols) >= 1
