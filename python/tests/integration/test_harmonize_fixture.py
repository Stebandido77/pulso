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

import hashlib
import io
import zipfile
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pathlib import Path


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


@pytest.mark.integration
def test_load_merged_raises_on_invalid_module(
    registry_with_unified_fixture: None,
) -> None:
    """ModuleNotAvailableError is raised for an invalid module name, not silently skipped."""
    import pulso
    from pulso._utils.exceptions import ModuleNotAvailableError

    with pytest.raises(ModuleNotAvailableError):
        pulso.load_merged(
            year=2024,
            month=6,
            modules=["caracteristicas_generales", "ocupados", "no_ocupados", "nonexistent_module"],
            harmonize=False,
        )


@pytest.mark.integration
def test_load_merged_auto_includes_required_modules_with_real_data() -> None:
    """Auto-inclusion works against real DANE data: vivienda_hogares is added for vivienda_propia.

    Requires the 2024-06 DANE ZIP to be cached locally (--run-integration).
    """
    import pulso

    # User specifies only person-level modules; vivienda_hogares is NOT in the list.
    # When harmonize=True, vivienda_hogares should be auto-included so that
    # vivienda_propia is harmonized instead of silently skipped.
    df = pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales", "ocupados", "desocupados", "inactivos"],
        harmonize=True,
    )

    assert "vivienda_propia" in df.columns, (
        "vivienda_propia missing — vivienda_hogares was not auto-included"
    )


# ─── Multi-level merge integration ───────────────────────────────────


_SEP = ";"
_DECIMAL = ","
_N = 10


def _df_to_bytes_local(df: Any) -> bytes:
    import pandas as pd

    buf = io.BytesIO()
    pd.DataFrame(df).to_csv(buf, index=False, sep=_SEP, decimal=_DECIMAL, encoding="utf-8")
    return buf.getvalue()


def _build_multilevel_zip() -> tuple[bytes, str]:
    """Build an in-memory ZIP with persona (caracteristicas_generales) and hogar (vivienda_hogares).

    Returns (zip_bytes, sha256_hex).
    """
    import pandas as pd

    carac = pd.DataFrame(
        {
            "DIRECTORIO": [f"{i:05d}" for i in range(1, _N + 1)],
            "SECUENCIA_P": [1] * _N,
            "ORDEN": [1] * _N,
            "HOGAR": [1] * _N,
            "CLASE": [1] * _N,
            "P6040": list(range(20, 20 + _N)),
            "FEX_C18": [1000.0] * _N,
        }
    )

    vivienda = pd.DataFrame(
        {
            "DIRECTORIO": [f"{i:05d}" for i in range(1, _N + 1)],
            "SECUENCIA_P": [1] * _N,
            "HOGAR": [1] * _N,
            "P5090": list(range(1, _N + 1)),
        }
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "CSV/Características generales, seguridad social en salud y educación.CSV",
            _df_to_bytes_local(carac),
        )
        zf.writestr("CSV/Vivienda y hogares.CSV", _df_to_bytes_local(vivienda))

    zip_bytes = buf.getvalue()
    sha256 = hashlib.sha256(zip_bytes).hexdigest()
    return zip_bytes, sha256


def _make_multilevel_sources(sha256: str) -> dict[str, Any]:
    return {
        "metadata": {
            "schema_version": "1.1.0",
            "data_version": "2026.04",
            "last_updated": "2026-04-30T00:00:00Z",
            "scraper_version": None,
            "covered_range": ["2024-06", "2024-06"],
        },
        "modules": {
            "caracteristicas_generales": {
                "level": "persona",
                "description_es": "Características generales",
                "description_en": "General characteristics",
                "available_in": ["geih_2021_present"],
            },
            "vivienda_hogares": {
                "level": "hogar",
                "description_es": "Vivienda y hogares",
                "description_en": "Dwelling and households",
                "available_in": ["geih_2021_present"],
            },
        },
        "data": {
            "2024-06": {
                "epoch": "geih_2021_present",
                "download_url": "https://example.com/fake_multilevel.zip",
                "checksum_sha256": sha256,
                "modules": {
                    "caracteristicas_generales": {
                        "file": (
                            "CSV/Características generales, "
                            "seguridad social en salud y educación.CSV"
                        ),
                    },
                    "vivienda_hogares": {
                        "file": "CSV/Vivienda y hogares.CSV",
                    },
                },
                "validated": True,
                "validated_by": "manual",
                "validated_at": None,
                "scraped_at": None,
                "landing_page": None,
                "size_bytes": None,
                "notes": "Synthetic multi-level fixture for hogar merge tests",
            }
        },
    }


@pytest.fixture
def registry_with_multilevel_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Inject a registry with persona + hogar modules sharing the same ZIP."""
    import pulso._config.registry as reg

    zip_bytes, sha256 = _build_multilevel_zip()

    cache_root = tmp_path / "cache"
    short = sha256[:16]
    dest = cache_root / "raw" / "2024" / "06" / f"{short}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(zip_bytes)

    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))
    monkeypatch.setattr(reg, "_SOURCES", _make_multilevel_sources(sha256))


@pytest.mark.integration
def test_load_merged_hogar_module_propagates_info(
    registry_with_multilevel_fixture: None,
) -> None:
    """vivienda_hogares (hogar-level) is merged with persona-level modules without error.

    Hogar info (P5090) must be propagated to all persons in that household.
    """
    import pulso

    df = pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales", "vivienda_hogares"],
        area="total",
        harmonize=False,
    )

    assert df.shape[0] == _N, f"Expected {_N} rows, got {df.shape[0]}"
    assert "DIRECTORIO" in df.columns
    assert "ORDEN" in df.columns, "Persona key must be present"
    assert "P6040" in df.columns, "Persona-level variable must be present"
    assert "P5090" in df.columns, "Hogar-level variable must be propagated to all persons"
    assert df["P5090"].notna().all(), "Every person must receive hogar info (left join)"
