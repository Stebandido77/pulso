"""Unit tests for ``pulso.metadata.parser``."""

from __future__ import annotations

from pathlib import Path

import pytest

from pulso.metadata.parser import DDIParseError, parse_ddi

ROOT = Path(__file__).resolve().parents[3]
SAMPLE_2024 = ROOT / "docs/internal/investigations/dictionaries/samples/geih_2024_ddi.xml"
SAMPLE_2018 = ROOT / "docs/internal/investigations/dictionaries/samples/geih_2018_ddi.xml"


@pytest.fixture(scope="module")
def parsed_2024() -> dict:
    return parse_ddi(SAMPLE_2024, year=2024)


@pytest.fixture(scope="module")
def parsed_2018() -> dict:
    return parse_ddi(SAMPLE_2018, year=2018)


# ── Existence / counts ────────────────────────────────────────────────


def test_sample_files_exist() -> None:
    assert SAMPLE_2024.exists(), f"Missing sample: {SAMPLE_2024}"
    assert SAMPLE_2018.exists(), f"Missing sample: {SAMPLE_2018}"


def test_parse_ddi_2024_count(parsed_2024: dict) -> None:
    # DANE repeats each <var> once per <fileDscr> it belongs to. The 2024
    # DDI has 760 <var> elements but only 675 unique variable codes (the
    # parser deduplicates and accumulates file_ids).
    assert len(parsed_2024["variables"]) == 675


def test_parse_ddi_2018_count(parsed_2018: dict) -> None:
    # 2018 DDI has 24 fileDscr blocks — most variables appear in many of
    # them. 1302 <var> elements collapse to 372 unique codes.
    assert len(parsed_2018["variables"]) == 372


def test_parse_ddi_aggregates_file_ids_for_repeated_codes(parsed_2024: dict) -> None:
    # PERIODO appears in 8 of 8 fileDscr blocks in 2024.
    periodo = parsed_2024["variables"]["PERIODO"]
    file_ids = periodo["available_in"]["2024"]["file_id_in_year"]
    assert file_ids is not None
    parts = file_ids.split(",")
    assert len(parts) == 8
    assert "F63" in parts
    assert "F70" in parts


def test_parse_ddi_returns_top_level_metadata(parsed_2024: dict) -> None:
    assert parsed_2024["year"] == 2024
    assert parsed_2024["ddi_id"] == "DANE-DIMPE-GEIH-2024"
    assert "F63" in parsed_2024["file_descriptors"]


def test_year_inference_when_omitted() -> None:
    out = parse_ddi(SAMPLE_2024)  # no year=
    assert out["year"] == 2024


# ── Per-variable correctness ──────────────────────────────────────────


def test_parse_ddi_2018_p6020_categorical(parsed_2018: dict) -> None:
    p6020 = parsed_2018["variables"]["P6020"]
    assert p6020["code"] == "P6020"
    assert p6020["type"] == "categorical"
    assert p6020["label"] == "Sexo"
    assert p6020["categories"] == {"1": "Hombre", "2": "Mujer"}
    assert "2018" in p6020["available_in"]
    year_entry = p6020["available_in"]["2018"]
    assert year_entry["epoch"] == "geih_2006_2020"
    assert year_entry["categories"] == {"1": "Hombre", "2": "Mujer"}
    # P6020 appears in 3 of the 24 fileDscr blocks; the parser concatenates them.
    assert "F256" in (year_entry["file_id_in_year"] or "").split(",")


def test_parse_ddi_2024_p3271_numeric(parsed_2024: dict) -> None:
    p3271 = parsed_2024["variables"]["P3271"]
    assert p3271["code"] == "P3271"
    # P3271 in the 2024 sample has no <catgry>; <valrng> says min=1 max=2.
    assert p3271["type"] == "numeric"
    assert p3271["categories"] is None
    assert p3271["value_range"] == {"min": 1.0, "max": 2.0}
    assert "Cuál fue su sexo al nacer?" in p3271["label"]
    year_entry = p3271["available_in"]["2024"]
    assert year_entry["epoch"] == "geih_2021_present"


def test_parse_ddi_2024_inglabo_continuous(parsed_2024: dict) -> None:
    inglabo = parsed_2024["variables"]["INGLABO"]
    assert inglabo["type"] == "numeric"
    assert inglabo["categories"] is None
    assert inglabo["value_range"] is not None
    assert inglabo["value_range"]["min"] == 0.0
    assert inglabo["value_range"]["max"] == 30000000.0


def test_parse_ddi_preserves_tildes(parsed_2018: dict) -> None:
    p6040 = parsed_2018["variables"]["P6040"]
    assert "ñ" in p6040["label"], (
        f"expected tildes preserved in P6040 label, got {p6040['label']!r}"
    )
    # Also ensure the P6090 universe (when present) carries 'ó' or 'á'.
    p6090 = parsed_2018["variables"]["P6090"]
    assert any(c in p6090["universe"] for c in "áéíóúñÁÉÍÓÚÑ¿¡")


def test_parse_ddi_categories_count_matches_2018_area(parsed_2018: dict) -> None:
    area = parsed_2018["variables"]["AREA"]
    assert area["type"] == "categorical"
    assert len(area["categories"]) == 13


def test_parse_ddi_categories_count_matches_2024_area(parsed_2024: dict) -> None:
    area = parsed_2024["variables"]["AREA"]
    assert area["type"] == "categorical"
    assert len(area["categories"]) == 23


def test_parse_ddi_notes_captured_for_p6090(parsed_2024: dict) -> None:
    p6090 = parsed_2024["variables"]["P6090"]
    assert p6090["notes"] is not None
    assert "Cotizantes" in p6090["notes"]


def test_parse_ddi_response_unit_present(parsed_2024: dict) -> None:
    inglabo = parsed_2024["variables"]["INGLABO"]
    assert inglabo["response_unit"] is not None
    assert "informante" in inglabo["response_unit"].lower()


# ── Failure modes ─────────────────────────────────────────────────────


def test_parse_ddi_malformed_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<root><not-a-codebook/></root>", encoding="utf-8")
    with pytest.raises(DDIParseError, match="codeBook"):
        parse_ddi(bad)


def test_parse_ddi_wrong_namespace_raises(tmp_path: Path) -> None:
    bad = tmp_path / "wrongns.xml"
    bad.write_text(
        '<codeBook xmlns="http://example.org/wrong" version="1.2.2"></codeBook>',
        encoding="utf-8",
    )
    with pytest.raises(DDIParseError, match="namespace"):
        parse_ddi(bad)


def test_parse_ddi_wrong_version_raises(tmp_path: Path) -> None:
    bad = tmp_path / "wrongver.xml"
    bad.write_text(
        '<codeBook xmlns="http://www.icpsr.umich.edu/DDI" version="2.0.0"></codeBook>',
        encoding="utf-8",
    )
    with pytest.raises(DDIParseError, match="version"):
        parse_ddi(bad)


def test_parse_ddi_invalid_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "broken.xml"
    bad.write_text("<not-closed>", encoding="utf-8")
    with pytest.raises(DDIParseError, match="Malformed"):
        parse_ddi(bad)


def test_parse_ddi_missing_dataDscr_raises(tmp_path: Path) -> None:
    bad = tmp_path / "nodata.xml"
    bad.write_text(
        '<codeBook xmlns="http://www.icpsr.umich.edu/DDI" '
        'ID="DANE-2030" version="1.2.2"></codeBook>',
        encoding="utf-8",
    )
    with pytest.raises(DDIParseError, match="dataDscr"):
        parse_ddi(bad, year=2030)


def test_parse_ddi_missing_year_unable_to_infer(tmp_path: Path) -> None:
    bad = tmp_path / "noyear.xml"
    bad.write_text(
        '<codeBook xmlns="http://www.icpsr.umich.edu/DDI" '
        'ID="GENERIC-NOYEAR" version="1.2.2">'
        "<dataDscr/>"
        "</codeBook>",
        encoding="utf-8",
    )
    with pytest.raises(DDIParseError, match="year"):
        parse_ddi(bad)


def test_parse_ddi_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_ddi(tmp_path / "nope.xml")


def test_parse_ddi_minimal_codebook_round_trip(tmp_path: Path) -> None:
    minimal = tmp_path / "min.xml"
    minimal.write_text(
        '<codeBook xmlns="http://www.icpsr.umich.edu/DDI" '
        'ID="DANE-DIMPE-GEIH-2030" version="1.2.2">'
        "<dataDscr>"
        '<var ID="V1" name="FOO" files="F1">'
        "<labl>Etiqueta foo</labl>"
        '<varFormat type="numeric"/>'
        "</var>"
        '<var ID="V2" name="BAR" files="F1">'
        "<labl>Categórica</labl>"
        '<varFormat type="numeric"/>'
        "<catgry><catValu>1</catValu><labl>Sí</labl></catgry>"
        "<catgry><catValu>2</catValu><labl>No</labl></catgry>"
        "</var>"
        "</dataDscr>"
        "</codeBook>",
        encoding="utf-8",
    )
    out = parse_ddi(minimal)
    assert out["year"] == 2030
    assert set(out["variables"]) == {"FOO", "BAR"}
    assert out["variables"]["FOO"]["type"] == "numeric"
    assert out["variables"]["BAR"]["type"] == "categorical"
    assert out["variables"]["BAR"]["categories"] == {"1": "Sí", "2": "No"}
    assert out["variables"]["BAR"]["available_in"]["2030"]["epoch"] == "geih_2021_present"
