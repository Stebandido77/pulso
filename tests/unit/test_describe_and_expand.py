"""Tests for the previously-NotImplementedError public API (Commit 8, M-4)."""

from __future__ import annotations

import pandas as pd
import pytest


def test_list_variables_returns_nonempty_dataframe() -> None:
    """list_variables() returns a DataFrame with at least the variables in the map."""
    import pulso

    df = pulso.list_variables()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    expected_cols = {
        "variable",
        "type",
        "level",
        "module",
        "description_es",
        "description_en",
        "available_in_epochs",
    }
    assert expected_cols.issubset(set(df.columns))


def test_list_variables_filters_unharmonized_by_default() -> None:
    """harmonized=True (default) drops variables with no epoch mappings."""
    import pulso

    df_default = pulso.list_variables()
    df_all = pulso.list_variables(harmonized=False)
    assert len(df_default) <= len(df_all)
    assert all(len(epochs) > 0 for epochs in df_default["available_in_epochs"])


def test_describe_variable_for_known_canonical() -> None:
    """describe_variable('sexo') returns full metadata including mappings."""
    import pulso

    info = pulso.describe_variable("sexo")
    assert info["canonical_name"] == "sexo"
    assert "type" in info
    assert "mappings" in info
    assert "geih_2006_2020" in info["mappings"]


def test_describe_variable_for_unknown_raises() -> None:
    """describe_variable('inexistente') raises ConfigError with helpful list."""
    import pulso

    with pytest.raises(pulso.ConfigError, match="not found"):
        pulso.describe_variable("variable_que_no_existe")


def test_describe_harmonization_returns_per_epoch_rows() -> None:
    """describe_harmonization returns one row per epoch with the chain details."""
    import pulso

    df = pulso.describe_harmonization("sexo")
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 1
    expected = {"epoch", "source_variable", "transform", "source_doc", "notes"}
    assert expected.issubset(set(df.columns))


def test_describe_harmonization_unknown_variable_raises() -> None:
    import pulso

    with pytest.raises(pulso.ConfigError):
        pulso.describe_harmonization("variable_que_no_existe")


# ── expand ────────────────────────────────────────────────────────────────


def test_expand_uses_canonical_weight_column() -> None:
    """expand(df) without weight= picks the canonical peso_expansion column."""
    import pulso

    df = pd.DataFrame({"peso_expansion": [1.5, 2.5], "x": [1, 2]})
    out = pulso.expand(df)
    assert "_weight" in out.columns
    assert out["_weight"].tolist() == [1.5, 2.5]
    assert out.attrs["weight"] == "peso_expansion"
    # input not mutated
    assert "_weight" not in df.columns


def test_expand_falls_back_to_FEX_C() -> None:
    """expand uses raw FEX_C when peso_expansion is absent."""
    import pulso

    df = pd.DataFrame({"FEX_C": [3.0, 4.0]})
    out = pulso.expand(df)
    assert out["_weight"].tolist() == [3.0, 4.0]
    assert out.attrs["weight"] == "FEX_C"


def test_expand_explicit_weight_argument() -> None:
    """expand(df, weight='custom') uses the explicit column name."""
    import pulso

    df = pd.DataFrame({"my_w": [10.0, 20.0]})
    out = pulso.expand(df, weight="my_w")
    assert out["_weight"].tolist() == [10.0, 20.0]


def test_expand_no_weight_column_raises() -> None:
    """expand fails clearly when no known weight column is present."""
    import pulso

    df = pd.DataFrame({"x": [1, 2]})
    with pytest.raises(pulso.ConfigError, match="weight"):
        pulso.expand(df)


def test_expand_explicit_weight_missing_column_raises() -> None:
    import pulso

    df = pd.DataFrame({"x": [1, 2]})
    with pytest.raises(pulso.ConfigError, match="not found"):
        pulso.expand(df, weight="nonexistent")
