"""Regression tests for DANE filename drift inside monthly ZIPs (v1.2.0)."""

from __future__ import annotations

import io
import zipfile

import pytest

from pulso._core.parser import _name_key, _resolve_zip_path

SSE = "seguridad social en salud y educación"
NB = "\u00a0"  # non-breaking space, as DANE uses since 2025-12


def _zip(names: list[str]) -> zipfile.ZipFile:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in names:
            z.writestr(n, "a;b\n1;2\n")
    buf.seek(0)
    return zipfile.ZipFile(buf)


def test_name_key_folds_nbsp_accents_case_and_extension() -> None:
    assert _name_key(f"CSV/Datos del hogar y{NB}la{NB}vivienda.csv") == _name_key(
        "CSV/Datos del hogar y la vivienda.CSV"
    )
    assert _name_key("CSV/Migración.CSV") == "migracion"


@pytest.mark.parametrize(
    ("member", "requested"),
    [
        (
            f"CSV/Datos{NB}del hogar y{NB}la{NB}vivienda.CSV",
            "CSV/Datos del hogar y la vivienda.CSV",
        ),
        (f"CSV/Otras formas{NB}de{NB}trabajo.csv", "CSV/Otras formas de trabajo.CSV"),
        ("CSV/Ocupados.csv", "CSV/Ocupados.CSV"),
        (
            f"CSV/Capítulos de{NB}características generales, {SSE}.CSV",
            f"CSV/Características generales, {SSE}.CSV",
        ),
    ],
)
def test_resolve_zip_path_tolerates_dane_drift(member: str, requested: str) -> None:
    zf = _zip([member, "CSV/No ocupados.csv"])
    assert _resolve_zip_path(zf, requested) == member


def test_ocupados_never_resolves_to_no_ocupados() -> None:
    zf = _zip(["CSV/No ocupados.csv"])
    with pytest.raises(KeyError):
        _resolve_zip_path(zf, "CSV/Ocupados.CSV")


def test_resolve_prefers_requested_extension_over_dta() -> None:
    # Real 2026-09 layout: DTA/ listed before CSV/, both with NBSP (#78).
    zf = _zip(
        [
            f"DTA/Datos del hogar y la{NB}vivienda.dta",
            f"SAV/Datos del hogar y la{NB}vivienda.sav",
            f"CSV/Datos del hogar y la{NB}vivienda.csv",
        ]
    )
    assert _resolve_zip_path(zf, "CSV/Datos del hogar y la vivienda.csv").startswith("CSV/")
