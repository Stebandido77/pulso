"""Integration tests: Phase 2 harmonizer + merger against the unified fixture.

The `registry_with_unified_fixture` conftest fixture supplies a Shape B (GEIH-2)
ZIP with three modules sharing overlapping DIRECTORIO/SECUENCIA_P/ORDEN keys:
  - caracteristicas_generales: 50 persons (DIRECTORIOs "00001"-"00050")
  - ocupados: persons 1-30 (OCI=1)
  - no_ocupados: persons 31-50 (DSI=1 for 6 desocupados, NaN for 14 inactivos)

Run with:
    pytest --run-integration tests/integration/
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_load_with_harmonize_true_returns_canonical_columns(
    registry_with_unified_fixture: None,
) -> None:
    """load(harmonize=True) adds canonical columns to the raw DataFrame."""
    import pulso

    df = pulso.load(
        year=2024,
        month=6,
        module="caracteristicas_generales",
        area="total",
        harmonize=True,
    )
    assert "DIRECTORIO" in df.columns, "Raw column must be preserved"
    assert "P6040" in df.columns, "Raw column must be preserved"
    assert "edad" in df.columns, "Canonical 'edad' must be added"
    assert "grupo_edad" in df.columns, "Canonical 'grupo_edad' must be added"
    assert df.shape[0] == 50


@pytest.mark.integration
def test_load_merged_with_three_modules_works(
    registry_with_unified_fixture: None,
) -> None:
    """load_merged() with all three modules produces a 50-row persona DataFrame."""
    import pulso

    df = pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales", "ocupados", "no_ocupados"],
        area="total",
        harmonize=False,
    )
    assert df.shape[0] == 50
    assert "DIRECTORIO" in df.columns
    assert "OCI" in df.columns
    assert "DSI" in df.columns


@pytest.mark.integration
def test_load_merged_condicion_actividad_classifies_correctly(
    registry_with_unified_fixture: None,
) -> None:
    """condicion_actividad correctly classifies ocupados, desocupados, inactivos."""
    import pulso

    df = pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales", "ocupados", "no_ocupados"],
        area="total",
        harmonize=True,
        variables=["condicion_actividad"],
    )

    assert "condicion_actividad" in df.columns
    ca = df["condicion_actividad"].dropna()

    # All values must be in {"1", "2", "3"}
    assert set(ca.unique()).issubset({"1", "2", "3"}), (
        f"Unexpected condicion_actividad values: {set(ca.unique())}"
    )

    # Fixture has 30 ocupados (OCI=1), 6 desocupados (DSI=1), 14 inactivos (DSI=NaN)
    counts = ca.value_counts()
    assert counts.get("1", 0) == 30, f"Expected 30 ocupados, got {counts.get('1', 0)}"
    assert counts.get("2", 0) == 6, f"Expected 6 desocupados, got {counts.get('2', 0)}"
    assert counts.get("3", 0) == 14, f"Expected 14 inactivos, got {counts.get('3', 0)}"


@pytest.mark.integration
def test_load_merged_subset_of_variables(
    registry_with_unified_fixture: None,
) -> None:
    """variables= restricts harmonization to the specified subset."""
    import pulso

    df = pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales", "ocupados", "no_ocupados"],
        area="total",
        harmonize=True,
        variables=["edad"],
    )

    assert "edad" in df.columns
    assert "grupo_edad" not in df.columns
    assert "condicion_actividad" not in df.columns


@pytest.mark.integration
def test_load_merged_returns_persona_level_unique_keys(
    registry_with_unified_fixture: None,
) -> None:
    """After merging, each (DIRECTORIO, SECUENCIA_P, ORDEN) tuple is unique."""
    import pulso

    df = pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales", "ocupados", "no_ocupados"],
        area="total",
        harmonize=False,
    )

    keys = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
    n_unique = df[keys].drop_duplicates().shape[0]
    assert n_unique == df.shape[0], (
        f"Expected {df.shape[0]} unique persona keys, got {n_unique}. "
        "The merge produced duplicate rows."
    )
