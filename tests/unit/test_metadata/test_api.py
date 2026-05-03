"""Unit tests for ``pulso.metadata.api``.

Covers ``describe_column`` and ``list_columns_metadata`` against
synthetic frames whose ``df.attrs["column_metadata"]`` is built from the
real composer (no mocks), so the renderer is exercised end-to-end.
"""

from __future__ import annotations

import pandas as pd
import pytest

import pulso
from pulso.metadata import composer
from pulso.metadata.api import describe_column, list_columns_metadata
from pulso.metadata.composer import compose_dataframe_metadata


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    composer._reset_caches_for_tests()
    yield
    composer._reset_caches_for_tests()


def _make_frame_with_metadata(columns: list[str], year: int = 2024, month: int = 6) -> pd.DataFrame:
    df = pd.DataFrame({c: [1, 2, 3] for c in columns})
    df.attrs["column_metadata"] = compose_dataframe_metadata(
        df, year=year, month=month, module="ocupados"
    )
    return df


def test_describe_column_canonical() -> None:
    """``sexo`` should render with Curator description and categories."""
    df = _make_frame_with_metadata(["sexo"])
    out = describe_column(df, "sexo")
    assert "Sexo" in out  # description_es starts with "Sexo de la persona."
    assert "hombre" in out
    assert "mujer" in out
    assert "Source: curator" in out


def test_describe_column_merged() -> None:
    """``P3271`` is merged: shows Curator categories AND codebook question_text."""
    df = _make_frame_with_metadata(["P3271"])
    out = describe_column(df, "P3271")
    assert "Source: merged" in out
    assert "hombre" in out
    assert "mujer" in out
    # Question text comes from codebook.
    assert "Question text:" in out
    # The merged hint mentions Curator + DANE codebook.
    assert "Curator" in out


def test_describe_column_skeletal_format() -> None:
    """A skeletal codebook variable renders the §B template with the issue URL."""
    df = _make_frame_with_metadata(["P3044S2"])
    out = describe_column(df, "P3044S2")
    assert "P3044S2 (sub-question, skeletal metadata)" in out
    assert "Source: codebook (skeletal)" in out
    assert "https://github.com/Stebandido77/pulso/issues" in out
    # Negative: it must NOT use the canonical/merged renderer.
    assert "Source: codebook\n" not in out  # the trailing \n distinguishes the full renderer


def test_describe_column_not_in_df_raises_valueerror() -> None:
    df = _make_frame_with_metadata(["sexo"])
    with pytest.raises(ValueError, match="DOES_NOT_EXIST"):
        describe_column(df, "DOES_NOT_EXIST")


def test_describe_column_no_metadata_loaded_returns_hint() -> None:
    """Without ``metadata=True``, describe_column returns a clear pointer."""
    df = pd.DataFrame({"sexo": [1, 2, 3]})  # no df.attrs
    out = describe_column(df, "sexo")
    assert "metadata=True" in out
    assert "No metadata loaded" in out


def test_describe_column_metadata_present_but_column_not_in_attrs() -> None:
    """Column added after compose: defensive fall-through to the hint."""
    df = _make_frame_with_metadata(["sexo"])
    df["new_column"] = [1, 2, 3]
    out = describe_column(df, "new_column")
    assert "metadata=True" in out


def test_list_columns_metadata_shape() -> None:
    df = _make_frame_with_metadata(["sexo", "P3271", "P3044S2", "FOOBAR"])
    out = list_columns_metadata(df)
    assert list(out.columns) == [
        "column",
        "label",
        "type",
        "module",
        "source",
        "has_categories",
    ]
    assert len(out) == 4
    rows = {row["column"]: row for _, row in out.iterrows()}
    assert rows["sexo"]["source"] == "curator"
    assert rows["P3271"]["source"] == "merged"
    assert rows["P3044S2"]["source"] == "codebook"
    assert rows["FOOBAR"]["source"] == "missing"
    assert rows["sexo"]["has_categories"] is True
    assert rows["FOOBAR"]["has_categories"] is False


def test_list_columns_metadata_without_attrs() -> None:
    """list_columns_metadata works even when ``column_metadata`` is missing."""
    df = pd.DataFrame({"sexo": [1, 2], "FOOBAR": ["a", "b"]})
    out = list_columns_metadata(df)
    assert len(out) == 2
    assert (out["source"] == "missing").all()
    assert out["label"].isna().all()


def test_describe_column_preserves_tildes() -> None:
    """Output must include Spanish tildes (no ASCII normalization)."""
    df = _make_frame_with_metadata(["OCI"])
    out = describe_column(df, "OCI")
    assert any(ch in out for ch in "óíáéúñ"), (
        f"Expected non-ASCII Spanish char in OCI render: {out!r}"
    )


def test_public_api_exposes_describe_and_list() -> None:
    """``pulso.describe_column`` and ``pulso.list_columns_metadata`` are public."""
    assert pulso.describe_column is describe_column
    assert pulso.list_columns_metadata is list_columns_metadata
    assert "describe_column" in pulso.__all__
    assert "list_columns_metadata" in pulso.__all__
