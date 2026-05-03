"""End-to-end integration test for ``metadata=True``.

Uses the same Shape A fixture as :mod:`tests.integration.test_load_fixture`
(``registry_with_fixture``) so it runs offline. Gated by
``--run-integration`` like every other integration test in this folder.

These tests verify the full wiring:

1. ``pulso.load(..., metadata=True)`` populates ``df.attrs["column_metadata"]``.
2. ``pulso.load_merged(..., metadata=True)`` does the same and also
   stashes ``source_modules``.
3. ``pulso.describe_column`` works end-to-end on a real loaded frame.
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_load_with_metadata_true(registry_with_fixture: None) -> None:
    """``df.attrs['column_metadata']`` is non-empty and shaped correctly."""
    import pulso

    df = pulso.load(
        year=2024,
        month=6,
        module="ocupados",
        area="cabecera",
        harmonize=False,
        metadata=True,
    )
    assert df.shape[0] > 0
    column_metadata = df.attrs.get("column_metadata")
    assert isinstance(column_metadata, dict)
    # One entry per column.
    assert set(column_metadata) == set(df.columns)
    # Each entry has the canonical keys.
    sample_meta = next(iter(column_metadata.values()))
    assert "source" in sample_meta
    # Source values are restricted to the four documented options.
    sources = {m["source"] for m in column_metadata.values()}
    assert sources <= {"curator", "codebook", "merged", "missing"}
    # df.attrs anchor fields.
    assert df.attrs.get("source_year") == 2024
    assert df.attrs.get("source_month") == 6
    assert df.attrs.get("source_module") == "ocupados"
    assert df.attrs.get("source_epoch") is not None


@pytest.mark.integration
def test_load_with_metadata_false_omits_attrs(registry_with_fixture: None) -> None:
    """``metadata=False`` (default) leaves attrs empty."""
    import pulso

    df = pulso.load(
        year=2024,
        month=6,
        module="ocupados",
        area="cabecera",
        harmonize=False,
    )
    assert "column_metadata" not in df.attrs
    assert "source_year" not in df.attrs


@pytest.mark.integration
def test_load_merged_with_metadata(registry_with_unified_fixture: None) -> None:
    """``load_merged(metadata=True)`` attaches metadata + source_modules list.

    Uses the Shape B (unified) fixture so the persona-level merge can
    actually succeed across the three Phase-2 modules.
    """
    import pulso

    df = pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales", "ocupados"],
        harmonize=False,
        metadata=True,
    )
    assert df.shape[0] > 0
    column_metadata = df.attrs.get("column_metadata")
    assert isinstance(column_metadata, dict)
    assert set(column_metadata) == set(df.columns)
    source_modules = df.attrs.get("source_modules")
    assert isinstance(source_modules, list)
    assert "caracteristicas_generales" in source_modules
    assert "ocupados" in source_modules


@pytest.mark.integration
def test_describe_column_with_real_load(registry_with_fixture: None) -> None:
    """``describe_column`` renders correctly on a real loaded frame."""
    import pulso

    df = pulso.load(
        year=2024,
        month=6,
        module="ocupados",
        area="cabecera",
        harmonize=False,
        metadata=True,
    )
    # Pick a column we know exists in the fixture.
    assert "DIRECTORIO" in df.columns
    out = pulso.describe_column(df, "DIRECTORIO")
    assert "DIRECTORIO" in out
    assert "Source:" in out


@pytest.mark.integration
def test_list_columns_metadata_with_real_load(registry_with_fixture: None) -> None:
    """``list_columns_metadata`` returns a tidy DataFrame on a real load."""
    import pulso

    df = pulso.load(
        year=2024,
        month=6,
        module="ocupados",
        area="cabecera",
        harmonize=False,
        metadata=True,
    )
    summary = pulso.list_columns_metadata(df)
    assert len(summary) == len(df.columns)
    assert list(summary.columns) == [
        "column",
        "label",
        "type",
        "module",
        "source",
        "has_categories",
    ]
    # No row should have source='missing' for the well-known DIRECTORIO key
    # (it's at minimum codebook-rich).
    directorio_row = summary[summary["column"] == "DIRECTORIO"]
    assert directorio_row.iloc[0]["source"] != "missing"
