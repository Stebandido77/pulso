"""Zip layouts that Python did not load before #75 (parity with r/R/utils-parse.R).

Each fixture mimics the member names of a real DANE zip:

* 2013-04..06: month suffix in the name (``Cabecera - Ocupados04.csv``).
* 2020-01..12 (Shape C): one national file per module with its own CLASE,
  under ``<n>. <Mes>/CSV/``, with typos in some months.
* 2022-10, 2023-04/08/09: nested wrappers with numbered or variant inner
  names (``CSV 4.zip``, ``DTA 9.zip``, ``DAT.zip``, ``CSV 13.zip``) and an
  inner ``CVS/`` folder (2023-04).
* 2024-03: ``CSV/No ocupado.CSV`` (singular).
"""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING

import pytest

from pulso._config.epochs import get_epoch
from pulso._core.parser import (
    _is_nested_format_wrapper,
    _matches_module_keyword,
    _open_nested_zip,
    _parse_csv,
    _parse_shape_c_module,
    _resolve_zip_path,
    find_shape_a_files,
    find_shape_c_file,
)
from pulso._utils.exceptions import ParseError

if TYPE_CHECKING:
    from pathlib import Path

GEIH1_CSV = "DIRECTORIO;SECUENCIA_P;ORDEN;CLASE;FEX_C\n1;1;1;1;10,5\n2;1;1;2;20,5\n3;1;1;1;30,5\n"
GEIH2_CSV = "DIRECTORIO;SECUENCIA_P;ORDEN;CLASE;FEX_C18\n1;1;1;1;10.5\n2;1;1;2;20.5\n"


def _zip(path: Path, members: dict[str, str | bytes]) -> Path:
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, payload in members.items():
            zf.writestr(name, payload)
    return path


def _inner(members: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w") as zf:
        for name, payload in members.items():
            zf.writestr(name, payload)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 2013-04..06: month suffix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("basename", "keyword", "expected"),
    [
        ("cabecera - ocupados04.csv", "Ocupados", True),
        ("cabecera - ocupados.csv", "Ocupados", True),
        ("cabecera - desocupados04.csv", "Ocupados", False),
        ("cabecera - desocupados04.csv", "Desocupados", True),
        ("cabecera - ocupadosx.csv", "Ocupados", False),
    ],
)
def test_matches_module_keyword(basename: str, keyword: str, expected: bool) -> None:
    assert _matches_module_keyword(basename, [keyword]) is expected


def test_find_shape_a_files_accepts_2013_month_suffix(tmp_path: Path) -> None:
    zip_path = _zip(
        tmp_path / "2013-04.zip",
        {
            "Abril.csv/Cabecera - Desocupados04.csv": GEIH1_CSV,
            "Abril.csv/Cabecera - Ocupados04.csv": GEIH1_CSV,
            "Abril.csv/Resto - Ocupados04.csv": GEIH1_CSV,
            "Abril.csv/Resto - Desocupados04.csv": GEIH1_CSV,
        },
    )
    assert find_shape_a_files(zip_path, "ocupados") == (
        "Abril.csv/Cabecera - Ocupados04.csv",
        "Abril.csv/Resto - Ocupados04.csv",
    )
    assert find_shape_a_files(zip_path, "desocupados") == (
        "Abril.csv/Cabecera - Desocupados04.csv",
        "Abril.csv/Resto - Desocupados04.csv",
    )


# ---------------------------------------------------------------------------
# 2020 Shape C
# ---------------------------------------------------------------------------


def _shape_c_zip(tmp_path: Path, desocupados_name: str = "Desocupados.CSV") -> Path:
    return _zip(
        tmp_path / "2020-05.zip",
        {
            "5.Mayo/CSV/Ocupados.CSV": GEIH1_CSV,
            f"5.Mayo/CSV/{desocupados_name}": GEIH1_CSV,
            "5.Mayo/DTA/Ocupados.DTA": b"not a csv",
        },
    )


@pytest.mark.parametrize("typo", ["Desocupados.CSV", "Descupados.CSV", "Desoucpados.CSV"])
def test_find_shape_c_file_tolerates_2020_typos(tmp_path: Path, typo: str) -> None:
    zip_path = _shape_c_zip(tmp_path, typo)
    assert find_shape_c_file(zip_path, "desocupados") == f"5.Mayo/CSV/{typo}"
    # "Ocupados" must not match inside "Desocupados".
    assert find_shape_c_file(zip_path, "ocupados") == "5.Mayo/CSV/Ocupados.CSV"


@pytest.mark.parametrize(
    ("module", "name"),
    [
        ("inactivos", "Ianctivos.CSV"),
        ("inactivos", "Inativos.CSV"),
        ("fuerza_de_trabajo", "Fuerzo de trabajo.CSV"),
    ],
)
def test_find_shape_c_file_other_2020_typos(tmp_path: Path, module: str, name: str) -> None:
    zip_path = _zip(tmp_path / "z.zip", {f"7.Julio/CSV/{name}": GEIH1_CSV})
    assert find_shape_c_file(zip_path, module) == f"7.Julio/CSV/{name}"


def test_find_shape_c_file_ignores_non_csv(tmp_path: Path) -> None:
    zip_path = _zip(tmp_path / "z.zip", {"6.Junio/SAV/Ocupados .SAV": b"x"})
    assert find_shape_c_file(zip_path, "ocupados") is None


@pytest.mark.parametrize(("area", "n_rows"), [("total", 3), ("cabecera", 2), ("resto", 1)])
def test_parse_shape_c_module_splits_area_by_clase(tmp_path: Path, area: str, n_rows: int) -> None:
    zip_path = _shape_c_zip(tmp_path)
    df = _parse_shape_c_module(
        zip_path, "ocupados", area, get_epoch("geih_2006_2020"), None, "2020-05"
    )  # type: ignore[arg-type]
    assert len(df) == n_rows
    assert set(df["_area"]) <= {"cabecera", "resto"}
    assert df["FEX_C"].dtype.kind == "f"


def test_parse_shape_c_module_missing_module_raises(tmp_path: Path) -> None:
    # 2020-03/04: DANE published no Desocupados or Inactivos file.
    zip_path = _zip(tmp_path / "2020-03.zip", {"3.Marzo/CSV/Ocupados.CSV": GEIH1_CSV})
    with pytest.raises(ParseError, match="no single national CSV"):
        _parse_shape_c_module(
            zip_path, "inactivos", "total", get_epoch("geih_2006_2020"), None, "2020-03"
        )


def test_parse_shape_c_module_without_clase_rejects_area(tmp_path: Path) -> None:
    zip_path = _zip(tmp_path / "z.zip", {"CSV/Ocupados.CSV": "DIRECTORIO;FEX_C\n1;1,0\n"})
    epoch = get_epoch("geih_2006_2020")
    assert len(_parse_shape_c_module(zip_path, "ocupados", "total", epoch, None, "k")) == 1
    with pytest.raises(ParseError, match="no CLASE column"):
        _parse_shape_c_module(zip_path, "ocupados", "cabecera", epoch, None, "k")


# ---------------------------------------------------------------------------
# Nested wrappers with variant names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("members", "inner_csv_name", "inner_dir"),
    [
        (
            ("GEIH_Octubre_Marco_2018/DTA 4.zip", "GEIH_Octubre_Marco_2018/SAV 4.zip"),
            "GEIH_Octubre_Marco_2018/CSV 4.zip",
            "CSV",
        ),  # 2022-10
        (("Abril/DTA 9.zip", "Abril/SAV 9.zip"), "Abril/CSV.zip", "CVS"),  # 2023-04
        (("Agosto/DAT.zip", "Agosto/SAV.zip"), "Agosto/CSV.zip", "CSV"),  # 2023-08
        (("Septiembre/DTA 13.zip", "Septiembre/SAV 12.zip"), "Septiembre/CSV 13.zip", "CSV"),
    ],
)
def test_nested_wrapper_variants_parse(
    tmp_path: Path, members: tuple[str, str], inner_csv_name: str, inner_dir: str
) -> None:
    stub = b"PK\x05\x06" + b"\x00" * 18
    outer = _zip(
        tmp_path / "outer.zip",
        {
            inner_csv_name: _inner({f"{inner_dir}/Ocupados.CSV": GEIH2_CSV}),
            members[0]: stub,
            members[1]: stub,
        },
    )
    with zipfile.ZipFile(outer) as zf:
        assert _is_nested_format_wrapper(zf) is True
    df = _parse_csv(outer, "CSV/Ocupados.CSV", get_epoch("geih_2021_present"), None, "ocupados")
    assert len(df) == 2


def test_open_nested_zip_maps_dat_to_dta(tmp_path: Path) -> None:
    outer = _zip(
        tmp_path / "outer.zip",
        {
            "Agosto/CSV.zip": _inner({"CSV/a.CSV": "x\n1\n"}),
            "Agosto/DAT.zip": _inner({"DAT/a.DTA": "x"}),
        },
    )
    with zipfile.ZipFile(outer) as zf, _open_nested_zip(zf, "dta") as inner:
        assert inner.namelist() == ["DAT/a.DTA"]


@pytest.mark.parametrize("name", ["CSV 4.csv", "CSVX.zip", "Ocupados.zip"])
def test_nested_wrapper_rejects_other_zip_names(tmp_path: Path, name: str) -> None:
    outer = _zip(tmp_path / "outer.zip", {name: b"x", "CSV.zip": b"x"})
    with zipfile.ZipFile(outer) as zf:
        assert _is_nested_format_wrapper(zf) is False


# ---------------------------------------------------------------------------
# 2024-03: "No ocupado.CSV"
# ---------------------------------------------------------------------------


def test_resolve_zip_path_module_keyword_tier(tmp_path: Path) -> None:
    zip_path = _zip(
        tmp_path / "z.zip",
        {"CSV/Ocupados.CSV": GEIH2_CSV, "CSV/No ocupado.CSV": GEIH2_CSV},
    )
    with zipfile.ZipFile(zip_path) as zf:
        assert _resolve_zip_path(zf, "CSV/No ocupados.CSV", "desocupados") == "CSV/No ocupado.CSV"
        assert _resolve_zip_path(zf, "CSV/No ocupados.CSV", "inactivos") == "CSV/No ocupado.CSV"
        # Without a module the old behaviour stays: no fuzzy match.
        with pytest.raises(KeyError):
            _resolve_zip_path(zf, "CSV/No ocupados.CSV")
        # "^ocupados$" must not pick "No ocupado".
        assert _resolve_zip_path(zf, "CSV/Ocupado.CSV", "ocupados") == "CSV/Ocupados.CSV"
