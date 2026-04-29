"""Unit tests for pulso._core.parser — exercised against the fixture ZIPs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

FIXTURE_ZIP = Path(__file__).parent.parent / "fixtures" / "zips" / "geih2_sample.zip"
UNIFIED_FIXTURE_ZIP = (
    Path(__file__).parent.parent / "fixtures" / "zips" / "geih2_unified_sample.zip"
)

# File paths inside the Shape A fixture ZIP (must match _build_fixtures.py).
INNER_CARAC_CAB = "Cabecera/Cabecera - Caracteristicas generales (Personas).CSV"
INNER_OCUP_CAB = "Cabecera/Cabecera - Ocupados.CSV"
INNER_OCUP_REST = "Resto/Resto - Ocupados.CSV"

# File paths inside the Shape B unified fixture ZIP.
INNER_OCUP_UNIFIED = "CSV/Ocupados.CSV"
INNER_NO_OCUP_UNIFIED = "CSV/No ocupados.CSV"


@pytest.fixture
def geih2_epoch() -> Any:
    from pulso._config.epochs import get_epoch

    return get_epoch("geih_2021_present")


@pytest.fixture
def shape_a_epoch() -> Any:
    """Synthetic epoch: UTF-8, semicolon separator, area_filter=None (Shape A dispatch)."""
    from pulso._config.epochs import Epoch

    return Epoch(
        key="test_shape_a",
        label="Test Shape A",
        label_en="Test Shape A",
        date_range=("2006-01", "2020-12"),
        merge_keys_persona=("DIRECTORIO", "SECUENCIA_P", "ORDEN"),
        merge_keys_hogar=("DIRECTORIO", "SECUENCIA_P"),
        encoding="utf-8",
        file_format="csv",
        separator=";",
        decimal=",",
        folder_pattern=("Cabecera/", "Resto/"),
        weight_variable="FEX_C18",
        area_filter=None,
        notes_es=None,
        methodology_url=None,
    )


@pytest.fixture
def fixture_sources_2024_06(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a synthetic 2024-06 sources entry (Shape A) pointing at the fixture ZIP."""
    import pulso._config.registry as reg

    monkeypatch.setattr(
        reg,
        "_SOURCES",
        {
            "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
            "modules": {
                "ocupados": {
                    "level": "persona",
                    "description_es": "Ocupados",
                    "available_in": ["geih_2021_present"],
                },
                "caracteristicas_generales": {
                    "level": "persona",
                    "description_es": "Caract. generales",
                    "available_in": ["geih_2021_present"],
                },
            },
            "data": {
                "2024-06": {
                    "epoch": "geih_2021_present",
                    "download_url": "https://example.com/x.zip",
                    "checksum_sha256": "a" * 64,
                    "modules": {
                        "ocupados": {
                            "cabecera": INNER_OCUP_CAB,
                            "resto": INNER_OCUP_REST,
                        },
                        "caracteristicas_generales": {
                            "cabecera": INNER_CARAC_CAB,
                            "resto": "Resto/Resto - Caracteristicas generales (Personas).CSV",
                        },
                    },
                    "validated": True,
                }
            },
        },
    )


@pytest.fixture
def fixture_sources_unified(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a synthetic 2024-06 sources entry (Shape B) pointing at the unified fixture ZIP."""
    import pulso._config.registry as reg

    monkeypatch.setattr(
        reg,
        "_SOURCES",
        {
            "metadata": {"schema_version": "1.1.0", "data_version": "2024.06"},
            "modules": {
                "ocupados": {
                    "level": "persona",
                    "description_es": "Ocupados",
                    "available_in": ["geih_2021_present"],
                },
                "desocupados": {
                    "level": "persona",
                    "description_es": "Desocupados",
                    "available_in": ["geih_2021_present"],
                },
            },
            "data": {
                "2024-06": {
                    "epoch": "geih_2021_present",
                    "download_url": "https://example.com/x.zip",
                    "checksum_sha256": "a" * 64,
                    "modules": {
                        "ocupados": {
                            "file": INNER_OCUP_UNIFIED,
                        },
                        "desocupados": {
                            "file": INNER_NO_OCUP_UNIFIED,
                            "row_filter": {"column": "OCI", "values": [2]},
                        },
                    },
                    "validated": True,
                }
            },
        },
    )


def test_parse_csv_direct(geih2_epoch: Any) -> None:
    """_parse_csv reads the fixture CSV without extraction."""
    if not FIXTURE_ZIP.exists():
        pytest.skip("Fixture ZIP not found")

    import pandas as pd

    from pulso._core.parser import _parse_csv

    df = _parse_csv(FIXTURE_ZIP, INNER_CARAC_CAB, geih2_epoch, columns=None)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50
    assert "DIRECTORIO" in df.columns
    assert "P6020" in df.columns
    assert "FEX_C18" in df.columns


def test_parse_csv_with_column_filter(geih2_epoch: Any) -> None:
    if not FIXTURE_ZIP.exists():
        pytest.skip("Fixture ZIP not found")

    from pulso._core.parser import _parse_csv

    df = _parse_csv(FIXTURE_ZIP, INNER_CARAC_CAB, geih2_epoch, columns=["DIRECTORIO", "P6040"])
    assert list(df.columns) == ["DIRECTORIO", "P6040"]


def test_parse_csv_missing_file_raises(geih2_epoch: Any) -> None:
    if not FIXTURE_ZIP.exists():
        pytest.skip("Fixture ZIP not found")

    from pulso._core.parser import _parse_csv
    from pulso._utils.exceptions import ParseError

    with pytest.raises(ParseError, match="not found"):
        _parse_csv(FIXTURE_ZIP, "nonexistent/file.CSV", geih2_epoch, None)


def test_parse_module_cabecera(fixture_sources_2024_06: Any, shape_a_epoch: Any) -> None:
    if not FIXTURE_ZIP.exists():
        pytest.skip("Fixture ZIP not found")

    import pandas as pd

    from pulso._core.parser import parse_module

    df = parse_module(FIXTURE_ZIP, 2024, 6, "ocupados", "cabecera", shape_a_epoch)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "DIRECTORIO" in df.columns
    assert "INGLABO" in df.columns


def test_parse_module_resto(fixture_sources_2024_06: Any, shape_a_epoch: Any) -> None:
    if not FIXTURE_ZIP.exists():
        pytest.skip("Fixture ZIP not found")

    from pulso._core.parser import parse_module

    df = parse_module(FIXTURE_ZIP, 2024, 6, "ocupados", "resto", shape_a_epoch)
    assert len(df) > 0


def test_parse_module_total_concatenates(fixture_sources_2024_06: Any, shape_a_epoch: Any) -> None:
    """Shape A area='total' concatenates cabecera + resto and adds _area column."""
    if not FIXTURE_ZIP.exists():
        pytest.skip("Fixture ZIP not found")

    from pulso._core.parser import parse_module

    df_cab = parse_module(FIXTURE_ZIP, 2024, 6, "ocupados", "cabecera", shape_a_epoch)
    df_rest = parse_module(FIXTURE_ZIP, 2024, 6, "ocupados", "resto", shape_a_epoch)
    df_total = parse_module(FIXTURE_ZIP, 2024, 6, "ocupados", "total", shape_a_epoch)

    assert len(df_total) == len(df_cab) + len(df_rest)
    assert "_area" in df_total.columns
    assert set(df_total["_area"].unique()) == {"cabecera", "resto"}


def test_parse_module_unified_cabecera(fixture_sources_unified: Any, geih2_epoch: Any) -> None:
    """Shape B: filtering on CLASE for cabecera returns only urban rows."""
    if not UNIFIED_FIXTURE_ZIP.exists():
        pytest.skip("Unified fixture ZIP not found. Run: python tests/_build_fixtures.py")

    from pulso._core.parser import parse_module

    df = parse_module(UNIFIED_FIXTURE_ZIP, 2024, 6, "ocupados", "cabecera", geih2_epoch)
    assert len(df) > 0
    assert "DIRECTORIO" in df.columns
    assert (df["CLASE"] == 1).all()


def test_parse_module_unified_resto(fixture_sources_unified: Any, geih2_epoch: Any) -> None:
    """Shape B: filtering on CLASE for resto returns rural rows (2 or 3)."""
    if not UNIFIED_FIXTURE_ZIP.exists():
        pytest.skip("Unified fixture ZIP not found. Run: python tests/_build_fixtures.py")

    from pulso._core.parser import parse_module

    df = parse_module(UNIFIED_FIXTURE_ZIP, 2024, 6, "ocupados", "resto", geih2_epoch)
    assert len(df) > 0
    assert df["CLASE"].isin([2, 3]).all()


def test_parse_module_unified_total(fixture_sources_unified: Any, geih2_epoch: Any) -> None:
    """Shape B: area=total returns all rows without area filtering."""
    if not UNIFIED_FIXTURE_ZIP.exists():
        pytest.skip("Unified fixture ZIP not found. Run: python tests/_build_fixtures.py")

    from pulso._core.parser import parse_module

    df = parse_module(UNIFIED_FIXTURE_ZIP, 2024, 6, "ocupados", "total", geih2_epoch)
    assert len(df) > 0
    assert set(df["CLASE"].unique()) == {1, 2, 3}


def test_parse_module_unified_with_row_filter(
    fixture_sources_unified: Any, geih2_epoch: Any
) -> None:
    """Shape B: row_filter splits a shared file (desocupados from inactivos)."""
    if not UNIFIED_FIXTURE_ZIP.exists():
        pytest.skip("Unified fixture ZIP not found. Run: python tests/_build_fixtures.py")

    from pulso._core.parser import parse_module

    df = parse_module(UNIFIED_FIXTURE_ZIP, 2024, 6, "desocupados", "total", geih2_epoch)
    assert len(df) > 0
    assert (df["OCI"] == 2).all()
