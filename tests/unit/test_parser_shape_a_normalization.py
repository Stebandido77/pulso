"""Unit tests for Shape A column normalization via _normalize_dane_columns."""

from __future__ import annotations

import warnings

import pandas as pd
import pytest


def _make_df(**cols: list) -> pd.DataFrame:
    """Convenience: build a one-row DataFrame from keyword column names."""
    return pd.DataFrame(dict(cols))


# ── _normalize_dane_columns ───────────────────────────────────────────────────


def test_normalize_shape_a_uppercases_all() -> None:
    """All columns must be uppercased."""
    from pulso._utils.columns import _normalize_dane_columns

    df = _make_df(Hogar=[1], Area=[2], directorio=[3], FEX_C=[4.0])
    result = _normalize_dane_columns(df)
    assert list(result.columns) == ["HOGAR", "AREA", "DIRECTORIO", "FEX_C"]


def test_normalize_shape_a_renames_fex_variants() -> None:
    """FEX_C_XXXX year-suffixed variants must be renamed to FEX_C."""
    from pulso._utils.columns import _normalize_dane_columns

    for original in ("FEX_C_2011", "FEX_C_2018", "fex_c_2011", "Fex_c_2011"):
        df = _make_df(**{original: [1.0]})
        result = _normalize_dane_columns(df)
        assert "FEX_C" in result.columns, f"Expected FEX_C after normalizing {original!r}"
        assert original not in result.columns


def test_normalize_shape_a_fex_c_idempotent() -> None:
    """FEX_C already canonical must stay unchanged."""
    from pulso._utils.columns import _normalize_dane_columns

    df = _make_df(FEX_C=[5.0], DIRECTORIO=[1])
    result = _normalize_dane_columns(df)
    assert "FEX_C" in result.columns
    assert result["FEX_C"].iloc[0] == 5.0


def test_normalize_shape_a_warns_on_multiple_fex() -> None:
    """If DF has both FEX_C and FEX_C_2011, a UserWarning must be raised."""
    from pulso._utils.columns import _normalize_dane_columns

    df = _make_df(FEX_C=[1.0], FEX_C_2011=[2.0], DIRECTORIO=[10])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = _normalize_dane_columns(df)

    assert any(issubclass(w.category, UserWarning) for w in caught), (
        "Expected a UserWarning when multiple FEX_C-pattern columns are present"
    )
    assert "FEX_C" in result.columns
    assert "FEX_C_2011" not in result.columns


def test_normalize_dane_columns_drops_duplicates_with_warning() -> None:
    """Columns that collide after uppercasing must warn and keep first occurrence."""
    from pulso._utils.columns import _normalize_dane_columns

    df = pd.DataFrame({"Clase": [1, 2], "CLASE": [3, 4]})
    with pytest.warns(UserWarning, match="collide"):
        result = _normalize_dane_columns(df)
    assert list(result.columns) == ["CLASE"]
    assert result["CLASE"].tolist() == [1, 2]  # first wins


def test_normalize_shape_a_preserves_data() -> None:
    """Data values must not change — only column names."""
    from pulso._utils.columns import _normalize_dane_columns

    df = _make_df(directorio=[42], secuencia_p=[7], fex_c_2011=[1234.5])
    result = _normalize_dane_columns(df)
    assert result["DIRECTORIO"].iloc[0] == 42
    assert result["SECUENCIA_P"].iloc[0] == 7
    assert result["FEX_C"].iloc[0] == pytest.approx(1234.5)
