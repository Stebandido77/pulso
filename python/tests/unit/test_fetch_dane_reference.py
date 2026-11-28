"""Unit tests for python/scripts/fetch_dane_reference.py (no network)."""

from __future__ import annotations

import datetime as dt
import io
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fetch_dane_reference import (  # noqa: E402
    AnnexSpec,
    build_reference,
    classify_label,
    discover_current_annex_url,
    parse_national_block,
)


def _rows(labels: tuple[str, str, str], years: list[int]) -> list[tuple]:
    months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    yr_row: list = ["Concepto"]
    mo_row: list = [None]
    for y in years:
        yr_row += [y] + [None] * 11
        mo_row += months
    n = len(mo_row) - 1
    return [
        ("Gran Encuesta Integrada de Hogares",),
        tuple(yr_row),
        tuple(mo_row),
        ("% poblacion en edad de trabajar ", *[70.0] * n),
        (labels[0], *[60.0 + i / 100 for i in range(n)]),
        (labels[1], *[55.0] * n),
        (labels[2], *[10.0] * n),
        ("T.D. Abierto", *[9.0] * n),
        (None,),
        ("Total Cabeceras",),
        tuple(yr_row),
        tuple(mo_row),
        (labels[2], *[99.0] * n),
    ]


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("TGP", "tgp"),
        ("TO", "to"),
        ("TD", "td"),
        ("Tasa Global de Participación (TGP)", "tgp"),
        ("Tasa de Ocupación (TO)", "to"),
        ("Tasa de Desocupación (TD)", "td"),
        ("T.D. Abierto", None),
        ("Tasa de Subocupación (TS)", None),
        (None, None),
    ],
)
def test_classify_label(label: str | None, expected: str | None) -> None:
    assert classify_label(label) == expected


def test_parse_national_block_reads_only_the_first_block() -> None:
    out = parse_national_block(_rows(("TGP", "TO", "TD"), [2020, 2021]))
    assert len(out) == 24
    assert out["2020-01"] == {"tgp": 60.0, "to": 55.0, "td": 10.0}
    assert out["2021-12"]["tgp"] == pytest.approx(60.23)
    assert all(v["td"] == 10.0 for v in out.values())  # Cabeceras block ignored


def test_parse_national_block_redesign_labels() -> None:
    labels = (
        "Tasa Global de Participación (TGP)",
        "Tasa de Ocupación (TO)",
        "Tasa de Desocupación (TD)",
    )
    out = parse_national_block(_rows(labels, [2026]))
    assert set(out) == {f"2026-{m:02d}" for m in range(1, 13)}


def test_parse_without_header_raises() -> None:
    with pytest.raises(ValueError, match="Concepto"):
        parse_national_block([("foo",), ("bar",)])


def test_discover_current_annex_picks_latest_and_skips_seasonal() -> None:
    html = (
        '<a href="/files/operaciones/GEIH/anex-GEIH-dic2025.xlsx">'
        '<a href="/files/operaciones/GEIH/anex-GEIH-Desestacionalizado-sep2026.xlsx">'
        '<a href="/files/operaciones/GEIH/anex-GEIH-sep2026.xlsx">'
        '<a href="/files/operaciones/GEIH/anex-GEIH-ago2026.xlsx">'
    )
    assert discover_current_annex_url(html) == (
        "https://www.dane.gov.co/files/operaciones/GEIH/anex-GEIH-sep2026.xlsx"
    )


def test_build_reference_keeps_each_annex_inside_its_epoch() -> None:
    openpyxl = pytest.importorskip("openpyxl")

    def workbook(sheet: str, labels: tuple[str, str, str], years: list[int], td: float) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet
        for r in _rows(labels, years):
            ws.append(list(r))
        for row in ws.iter_rows():
            if row[0].value == labels[2]:
                for c in row[1:]:
                    c.value = td
                break
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    files = {
        "hist": workbook("Tnal mensual", ("TGP", "TO", "TD"), [2021, 2022], td=11.0),
        "cur": workbook(
            "Total nacional",
            (
                "Tasa Global de Participación (TGP)",
                "Tasa de Ocupación (TO)",
                "Tasa de Desocupación (TD)",
            ),
            [2021, 2022],
            td=22.0,
        ),
    }
    specs = [
        AnnexSpec("geih_2006_2020", "hist", "Tnal mensual"),
        AnnexSpec("geih_2021_present", "cur", "Total nacional"),
    ]
    ranges = {"geih_2006_2020": ("2006-01", "2021-12"), "geih_2021_present": ("2022-01", None)}
    rows = build_reference(
        specs,
        ranges,
        fetch=files.__getitem__,
        now=dt.datetime(2026, 11, 26, tzinfo=dt.timezone.utc),
    )
    by = {r["period"]: r for r in rows}
    assert len(rows) == 24
    assert by["2021-12"]["td"] == 11.0
    assert by["2021-12"]["source_url"] == "hist"
    assert by["2022-01"]["td"] == 22.0
    assert by["2022-01"]["source_url"] == "cur"
    assert by["2022-01"]["retrieved_at"] == "2026-11-26T00:00:00Z"


def test_build_reference_takes_2020_from_the_2018_frame_annex() -> None:
    """2020 microdata are retro-projected to the 2018 frame (catalog 780)."""
    openpyxl = pytest.importorskip("openpyxl")

    def workbook(sheet: str, labels: tuple[str, str, str], td: float) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet
        for r in _rows(labels, [2019, 2020, 2021]):
            ws.append(list(r))
        for row in ws.iter_rows():
            if row[0].value == labels[2]:
                for c in row[1:]:
                    c.value = td
                break
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    files = {
        "hist": workbook("Tnal mensual", ("TGP", "TO", "TD"), td=11.0),
        "cur": workbook(
            "Total nacional",
            (
                "Tasa Global de Participación (TGP)",
                "Tasa de Ocupación (TO)",
                "Tasa de Desocupación (TD)",
            ),
            td=22.0,
        ),
    }
    specs = [
        AnnexSpec("geih_2006_2020", "hist", "Tnal mensual"),
        AnnexSpec("geih_2021_present", "cur", "Total nacional"),
    ]
    ranges = {"geih_2006_2020": ("2006-01", "2021-12"), "geih_2021_present": ("2022-01", None)}
    by = {r["period"]: r for r in build_reference(specs, ranges, fetch=files.__getitem__)}
    assert len(by) == 36
    assert by["2019-12"]["source_url"] == "hist"
    assert all(by[f"2020-{m:02d}"]["source_url"] == "cur" for m in range(1, 13))
    assert by["2020-06"]["td"] == 22.0
    assert by["2021-01"]["source_url"] == "hist"
