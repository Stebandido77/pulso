"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require real DANE data (network).",
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run tests marked as slow.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="needs --run-integration")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="needs --run-slow")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


# ─── Shared path fixtures ─────────────────────────────────────────────


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Path to the repo root."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def data_dir(project_root: Path) -> Path:
    """Path to the packaged data directory."""
    return project_root / "pulso" / "data"


@pytest.fixture(scope="session")
def schemas_dir(data_dir: Path) -> Path:
    return data_dir / "schemas"


@pytest.fixture(scope="session")
def fixtures_dir(project_root: Path) -> Path:
    return project_root / "tests" / "fixtures"


# ─── Fixture ZIP helpers ──────────────────────────────────────────────


@pytest.fixture(scope="session")
def fixture_zip_path(fixtures_dir: Path) -> Path:
    """Path to the committed Shape A synthetic fixture ZIP."""
    p = fixtures_dir / "zips" / "geih2_sample.zip"
    if not p.exists():
        pytest.skip(f"Fixture ZIP not found: {p}. Run: python tests/_build_fixtures.py")
    return p


@pytest.fixture(scope="session")
def unified_fixture_zip_path(fixtures_dir: Path) -> Path:
    """Path to the committed Shape B (unified) synthetic fixture ZIP."""
    p = fixtures_dir / "zips" / "geih2_unified_sample.zip"
    if not p.exists():
        pytest.skip(f"Unified fixture ZIP not found: {p}. Run: python tests/_build_fixtures.py")
    return p


@pytest.fixture(scope="session")
def fixture_zip_sha256(fixture_zip_path: Path) -> str:
    """SHA-256 hex digest of the Shape A fixture ZIP."""
    h = hashlib.sha256()
    with fixture_zip_path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(scope="session")
def unified_fixture_zip_sha256(unified_fixture_zip_path: Path) -> str:
    """SHA-256 hex digest of the Shape B (unified) fixture ZIP."""
    h = hashlib.sha256()
    with unified_fixture_zip_path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


# ─── Integration registry fixture ────────────────────────────────────

# Synthetic Shape A epoch: UTF-8, semicolon separator, area_filter=None.
# Used by registry_with_fixture so epoch_for_month(2024,6) returns an epoch
# with area_filter=None, causing parse_module to take the Shape A path.
_FIXTURE_EPOCHS: dict[str, Any] = {
    "metadata": {"schema_version": "1.1.0", "last_updated": "2026-04-27T00:00:00Z"},
    "epochs": {
        "test_shape_a": {
            "label": "Test Shape A (fixture epoch)",
            "label_en": "Test Shape A (fixture epoch)",
            "date_range": ["2006-01", None],
            "merge_keys": {
                "persona": ["DIRECTORIO", "SECUENCIA_P", "ORDEM"],
                "hogar": ["DIRECTORIO", "SECUENCIA_P"],
            },
            "encoding": "utf-8",
            "file_format": "csv",
            "separator": ";",
            "decimal": ",",
            "folder_pattern": ["Cabecera/", "Resto/"],
            "weight_variable": "FEX_C18",
            "area_filter": None,
            "notes_es": "Synthetic epoch for Shape A integration tests.",
        }
    },
}


def _make_fixture_sources(sha256: str) -> dict[str, Any]:
    """Return a sources dict for Shape A integration tests.

    Uses "test_shape_a" as the epoch key — must be paired with _FIXTURE_EPOCHS.
    """
    return {
        "metadata": {
            "schema_version": "1.0.0",
            "data_version": "2026.04",
            "last_updated": "2026-04-27T00:00:00Z",
            "scraper_version": None,
            "covered_range": ["2006-01", "2026-03"],
        },
        "modules": {
            "caracteristicas_generales": {
                "level": "persona",
                "description_es": "Características generales",
                "description_en": "General characteristics",
                "available_in": ["geih_2006_2020", "geih_2021_present"],
            },
            "ocupados": {
                "level": "persona",
                "description_es": "Personas ocupadas",
                "description_en": "Employed persons",
                "available_in": ["geih_2006_2020", "geih_2021_present"],
            },
            "desocupados": {
                "level": "persona",
                "description_es": "Personas desocupadas",
                "description_en": "Unemployed persons",
                "available_in": ["geih_2006_2020", "geih_2021_present"],
            },
            "inactivos": {
                "level": "persona",
                "description_es": "Personas inactivas",
                "description_en": "Inactive persons",
                "available_in": ["geih_2006_2020", "geih_2021_present"],
            },
            "vivienda_hogares": {
                "level": "hogar",
                "description_es": "Vivienda y hogares",
                "description_en": "Dwelling and households",
                "available_in": ["geih_2006_2020", "geih_2021_present"],
            },
            "otros_ingresos": {
                "level": "persona",
                "description_es": "Otros ingresos",
                "description_en": "Other income",
                "available_in": ["geih_2006_2020", "geih_2021_present"],
            },
        },
        "data": {
            "2024-06": {
                "epoch": "test_shape_a",
                "download_url": "https://example.com/fake_geih_2024_06.zip",
                "checksum_sha256": sha256,
                "modules": {
                    "ocupados": {
                        "cabecera": "Cabecera/Cabecera - Ocupados.CSV",
                        "resto": "Resto/Resto - Ocupados.CSV",
                    },
                    "caracteristicas_generales": {
                        "cabecera": (
                            "Cabecera/Cabecera - Caracteristicas generales (Personas).CSV"
                        ),
                        "resto": ("Resto/Resto - Caracteristicas generales (Personas).CSV"),
                    },
                },
                "validated": True,
                "validated_by": "manual",
                "validated_at": None,
                "scraped_at": None,
                "landing_page": None,
                "size_bytes": None,
                "notes": "Synthetic fixture for integration tests",
            }
        },
    }


def _make_unified_fixture_sources(sha256: str) -> dict[str, Any]:
    """Return a sources dict (Shape B) for the unified fixture."""
    return {
        "metadata": {
            "schema_version": "1.1.0",
            "data_version": "2026.04",
            "last_updated": "2026-04-27T00:00:00Z",
            "scraper_version": None,
            "covered_range": ["2024-06", "2024-06"],
        },
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Personas ocupadas",
                "description_en": "Employed persons",
                "available_in": ["geih_2021_present"],
            },
            "desocupados": {
                "level": "persona",
                "description_es": "Personas desocupadas",
                "description_en": "Unemployed persons",
                "available_in": ["geih_2021_present"],
            },
        },
        "data": {
            "2024-06": {
                "epoch": "geih_2021_present",
                "download_url": "https://example.com/fake_geih_2024_06_unified.zip",
                "checksum_sha256": sha256,
                "modules": {
                    "ocupados": {
                        "file": "CSV/Ocupados.CSV",
                    },
                    "desocupados": {
                        "file": "CSV/No ocupados.CSV",
                        "row_filter": {"column": "OCI", "values": [2]},
                    },
                },
                "validated": True,
                "validated_by": "manual",
                "validated_at": None,
                "scraped_at": None,
                "landing_page": None,
                "size_bytes": None,
                "notes": "Synthetic Shape B (unified) fixture for integration tests",
            }
        },
    }


@pytest.fixture
def registry_with_unified_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unified_fixture_zip_path: Path,
    unified_fixture_zip_sha256: str,
) -> None:
    """Inject a Shape B 2024-06 registry entry and pre-populate the cache.

    Mirrors registry_with_fixture but uses the unified (Shape B) fixture ZIP.
    """
    import pulso._config.registry as reg

    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))

    short = unified_fixture_zip_sha256[:16]
    dest = cache_root / "raw" / "2024" / "06" / f"{short}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(unified_fixture_zip_path, dest)

    custom_sources = _make_unified_fixture_sources(unified_fixture_zip_sha256)
    monkeypatch.setattr(reg, "_SOURCES", custom_sources)


@pytest.fixture
def registry_with_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fixture_zip_path: Path,
    fixture_zip_sha256: str,
) -> None:
    """Inject a synthetic 2024-06 registry entry (Shape A) and pre-populate the cache.

    This fixture:
    1. Redirects PULSO_CACHE_DIR to a temp directory.
    2. Copies the fixture ZIP into the expected cache slot.
    3. Overrides _SOURCES and _EPOCHS so the loader uses a Shape A epoch
       (area_filter=None) for 2024-06, matching the Cabecera/Resto file structure.

    After the test, monkeypatch restores everything automatically.
    """
    import pulso._config.registry as reg

    # Redirect cache to an isolated temp directory.
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))

    # Pre-populate cache: copy fixture ZIP to expected slot.
    short = fixture_zip_sha256[:16]
    dest = cache_root / "raw" / "2024" / "06" / f"{short}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture_zip_path, dest)

    # Override both singletons: sources uses Shape A paths; epochs supplies
    # a synthetic epoch with area_filter=None so the parser takes Shape A path.
    monkeypatch.setattr(reg, "_SOURCES", _make_fixture_sources(fixture_zip_sha256))
    monkeypatch.setattr(reg, "_EPOCHS", _FIXTURE_EPOCHS)
