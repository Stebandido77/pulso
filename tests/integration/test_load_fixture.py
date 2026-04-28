"""Integration test: full load() pipeline against the synthetic fixture.

These tests are skipped by default. Run with:

    pytest --run-integration tests/integration/

The `registry_with_fixture` conftest fixture:
  - Redirects PULSO_CACHE_DIR to a temp directory
  - Pre-populates the raw cache slot with the fixture ZIP
  - Overrides _SOURCES to include a synthetic 2024-06 entry
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_load_ocupados_cabecera(registry_with_fixture: None) -> None:
    """Phase 1 success criterion: load ocupados for 2024-06."""
    import pulso

    df = pulso.load(year=2024, month=6, module="ocupados", area="cabecera", harmonize=False)
    assert df.shape[0] > 0
    assert "DIRECTORIO" in df.columns
    assert "INGLABO" in df.columns


@pytest.mark.integration
def test_load_returns_dataframe(registry_with_fixture: None) -> None:
    import pandas as pd

    import pulso

    df = pulso.load(year=2024, month=6, module="ocupados", area="cabecera", harmonize=False)
    assert isinstance(df, pd.DataFrame)


@pytest.mark.integration
def test_load_cabecera_row_count(registry_with_fixture: None) -> None:
    """Cabecera should have ~60% of 50 rows = ~30 rows in ocupados."""
    import pulso

    df = pulso.load(year=2024, month=6, module="ocupados", area="cabecera", harmonize=False)
    assert 10 <= df.shape[0] <= 50


@pytest.mark.integration
def test_load_total_has_area_column(registry_with_fixture: None) -> None:
    import pulso

    df = pulso.load(year=2024, month=6, module="ocupados", area="total", harmonize=False)
    assert "_area" in df.columns
    assert set(df["_area"].unique()) == {"cabecera", "resto"}


@pytest.mark.integration
def test_load_caracteristicas_generales(registry_with_fixture: None) -> None:
    import pulso

    df = pulso.load(
        year=2024,
        month=6,
        module="caracteristicas_generales",
        area="cabecera",
        harmonize=False,
    )
    assert df.shape[0] == 50
    assert "DIRECTORIO" in df.columns
    assert "P6020" in df.columns


@pytest.mark.integration
def test_load_harmonize_true_raises(registry_with_fixture: None) -> None:
    import pulso

    with pytest.raises(NotImplementedError, match="Phase 2"):
        pulso.load(year=2024, month=6, module="ocupados", harmonize=True)


@pytest.mark.integration
def test_load_unknown_module_raises(registry_with_fixture: None) -> None:
    import pulso
    from pulso._utils.exceptions import ModuleNotAvailableError

    with pytest.raises(ModuleNotAvailableError):
        pulso.load(year=2024, month=6, module="nonexistent_module_xyz", harmonize=False)


@pytest.mark.integration
def test_load_missing_period_raises(registry_with_fixture: None) -> None:
    import pulso
    from pulso._utils.exceptions import DataNotAvailableError

    with pytest.raises(DataNotAvailableError):
        pulso.load(year=2024, month=7, module="ocupados", harmonize=False)
