"""Unit tests for pulso._core.parser — exercised against the fixture ZIPs."""

from __future__ import annotations

import zipfile
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
                "no_ocupados": {
                    "level": "persona",
                    "description_es": "No ocupados",
                    "available_in": ["geih_2021_present"],
                },
                "desocupados": {
                    "level": "persona",
                    "description_es": "Desocupados (filtrado de no_ocupados)",
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
                        "no_ocupados": {
                            "file": INNER_NO_OCUP_UNIFIED,
                        },
                        "desocupados": {
                            "file": INNER_NO_OCUP_UNIFIED,
                            "row_filter": {"column": "DSI", "values": [1]},
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
    assert df["CLASE"].isin([1, 2]).all()


def test_parse_module_unified_with_row_filter(
    fixture_sources_unified: Any, geih2_epoch: Any
) -> None:
    """Shape B: row_filter splits a shared file (desocupados via DSI=1)."""
    if not UNIFIED_FIXTURE_ZIP.exists():
        pytest.skip("Unified fixture ZIP not found. Run: python tests/_build_fixtures.py")

    from pulso._core.parser import parse_module

    df = parse_module(UNIFIED_FIXTURE_ZIP, 2024, 6, "desocupados", "total", geih2_epoch)
    assert len(df) > 0
    assert (df["DSI"] == 1).all()


# ---------------------------------------------------------------------------
# Shape A auto-discovery tests (Phase 3.2.B)
# ---------------------------------------------------------------------------


def test_is_shape_a_detects_cabecera_files(tmp_path: Path, shape_a_epoch: Any) -> None:
    """Shape A is detected when the ZIP contains a file with 'Cabecera' in its name."""
    from pulso._core.parser import is_shape_a

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Diciembre.csv/Cabecera - Ocupados.csv", "DIRECTORIO;P6020\n1;1\n")

    assert is_shape_a(zip_path) is True


def test_is_shape_a_returns_false_for_shape_b(tmp_path: Path) -> None:
    """Shape B (unified) ZIP has no 'Cabecera' file — is_shape_a returns False."""
    from pulso._core.parser import is_shape_a

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("CSV/Ocupados.CSV", "DIRECTORIO;P6020\n1;1\n")

    assert is_shape_a(zip_path) is False


def test_find_shape_a_files_returns_cabecera_and_resto(tmp_path: Path) -> None:
    """find_shape_a_files locates both Cabecera and Resto for a module."""
    from pulso._core.parser import find_shape_a_files

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Junio.csv/Cabecera - Ocupados.csv", "x")
        zf.writestr("Junio.csv/Resto - Ocupados.csv", "x")
        zf.writestr("Junio.csv/Area - Ocupados.csv", "x")  # should be ignored

    cab, resto = find_shape_a_files(zip_path, "ocupados")
    assert cab is not None
    assert "Cabecera" in cab
    assert resto is not None
    assert "Resto" in resto


def test_find_shape_a_files_handles_2007_typo(tmp_path: Path) -> None:
    """'Caractericas generales' (2007 typo) matches the canonical module."""
    from pulso._core.parser import find_shape_a_files

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Diciembre.csv/Cabecera - Caractericas generales.csv", "x")

    cab, _resto = find_shape_a_files(zip_path, "caracteristicas_generales")
    assert cab is not None  # matched despite typo


def test_find_shape_a_files_ignores_area_files(tmp_path: Path) -> None:
    """Area - * files are never returned by find_shape_a_files."""
    from pulso._core.parser import find_shape_a_files

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("CSV/Area - Ocupados.csv", "x")
        zf.writestr("CSV/Cabecera - Ocupados.csv", "x")
        zf.writestr("CSV/Resto - Ocupados.csv", "x")

    cab, resto = find_shape_a_files(zip_path, "ocupados")
    assert cab is not None
    assert "Cabecera" in cab
    assert resto is not None
    assert "Resto" in resto
    assert "Area" not in (cab or "")
    assert "Area" not in (resto or "")


def test_parse_shape_a_concatenates_cabecera_and_resto(tmp_path: Path, shape_a_epoch: Any) -> None:
    """parse_shape_a_module concatenates Cabecera + Resto, adds CLASE column."""
    import pandas as pd

    from pulso._core.parser import parse_shape_a_module

    rows_cab = pd.DataFrame(
        {"DIRECTORIO": ["0001", "0002", "0003"], "SECUENCIA_P": [1, 1, 1], "ORDEN": [1, 1, 1]}
    )
    rows_resto = pd.DataFrame(
        {"DIRECTORIO": ["0004", "0005"], "SECUENCIA_P": [1, 1], "ORDEN": [1, 1]}
    )

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "Test.csv/Cabecera - Ocupados.csv",
            rows_cab.to_csv(sep=";", decimal=",", index=False).encode("utf-8"),
        )
        zf.writestr(
            "Test.csv/Resto - Ocupados.csv",
            rows_resto.to_csv(sep=";", decimal=",", index=False).encode("utf-8"),
        )

    df = parse_shape_a_module(zip_path, "ocupados", shape_a_epoch)

    assert len(df) == 5  # 3 Cabecera + 2 Resto
    assert "CLASE" in df.columns
    assert (df["CLASE"] == 1).sum() == 3
    assert (df["CLASE"] == 2).sum() == 2
    # DIRECTORIO is read as int by pandas (zero-padding lost); just check uniqueness
    assert df["DIRECTORIO"].nunique() == 5


def test_parse_shape_a_raises_when_module_missing(tmp_path: Path, shape_a_epoch: Any) -> None:
    """parse_shape_a_module raises ParseError if no Cabecera or Resto file matches."""
    from pulso._core.parser import parse_shape_a_module
    from pulso._utils.exceptions import ParseError

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("CSV/Cabecera - Ocupados.csv", "x")  # only has ocupados, not vivienda

    with pytest.raises(ParseError, match="vivienda_hogares"):
        parse_shape_a_module(zip_path, "vivienda_hogares", shape_a_epoch)


# ---------------------------------------------------------------------------
# Regression tests: word-boundary keyword matching (Phase 3.3.1 hotfix)
# ---------------------------------------------------------------------------


def test_find_shape_a_files_distinguishes_ocupados_from_desocupados(tmp_path: Path) -> None:
    """Regression: 'ocupados' must NOT match 'Desocupados' as a substring.

    Before this fix, searching for module 'ocupados' would match
    'Cabecera - Desocupados.csv' because 'ocupados' is a substring of 'desocupados'.
    """
    from pulso._core.parser import find_shape_a_files

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("CSV/Cabecera - Desocupados.csv", "x")
        zf.writestr("CSV/Resto - Desocupados.csv", "x")

    cab, resto = find_shape_a_files(zip_path, "ocupados")
    assert cab is None, f"Expected no match for 'ocupados', got: {cab}"
    assert resto is None, f"Expected no match for 'ocupados', got: {resto}"


def test_find_shape_a_files_robust_to_filename_order(tmp_path: Path) -> None:
    """Regression: file order in the ZIP must not affect keyword-match correctness.

    Before this fix, fixtures relied on alphabetical ordering (D < O) so that
    'Ocupados' would overwrite 'Desocupados' as the last match. Real DANE ZIPs
    do not guarantee any file order, so the fix must work regardless of order.
    """
    from pulso._core.parser import find_shape_a_files

    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        # Desocupados written FIRST (non-alphabetical: if old code iterated this
        # order and Ocupados came after, Ocupados would win by last-match — but
        # in real ZIPs the order could be reversed, so the fix must not rely on it)
        zf.writestr("CSV/Cabecera - Desocupados.csv", "x")
        zf.writestr("CSV/Resto - Desocupados.csv", "x")
        zf.writestr("CSV/Cabecera - Ocupados.csv", "x")
        zf.writestr("CSV/Resto - Ocupados.csv", "x")

    cab_o, resto_o = find_shape_a_files(zip_path, "ocupados")
    assert cab_o is not None, "Expected to find Cabecera - Ocupados"
    assert "Ocupados" in cab_o, f"Wrong file matched: {cab_o}"
    assert "Desocupados" not in cab_o, f"Matched Desocupados instead of Ocupados: {cab_o}"
    assert resto_o is not None
    assert "Ocupados" in resto_o, f"Wrong file: {resto_o}"
    assert "Desocupados" not in resto_o, f"Matched Desocupados instead of Ocupados: {resto_o}"

    cab_d, resto_d = find_shape_a_files(zip_path, "desocupados")
    assert cab_d is not None
    assert "Desocupados" in cab_d, f"Wrong file matched: {cab_d}"
    assert resto_d is not None
    assert "Desocupados" in resto_d, f"Wrong file: {resto_d}"
