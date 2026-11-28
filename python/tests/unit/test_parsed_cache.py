"""Parquet cache of parsed modules and columns= (W3, #86)."""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pandas as pd
import pytest

from pulso._config.epochs import get_epoch
from pulso._core.parser import parse_module, parse_module_cached, parsed_cache_key

if TYPE_CHECKING:
    from pathlib import Path

CSV = (
    "DIRECTORIO;SECUENCIA_P;ORDEN;HOGAR;P6040;INGLABO;fex_c_2011\n"
    "1;1;1;1;30;1000;10,5\n"
    "2;1;1;1;40;;20,5\n"
)
RECORD = {"download_url": "https://example.org/x.zip", "epoch": "geih_2006_2020"}


@pytest.fixture
def shape_a_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))
    path = tmp_path / "2015-06.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Cabecera - Ocupados.csv", CSV)
        zf.writestr("Resto - Ocupados.csv", CSV)
    return path


def _cached_files(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "cache" / "parsed").rglob("*.parquet"))


@pytest.mark.parametrize("area", ["total", "cabecera", "resto"])
@pytest.mark.parametrize("columns", [None, ["p6040", "FEX_C", "NOPE"]])
def test_cached_result_equals_direct_parse(
    shape_a_zip: Path, tmp_path: Path, area: str, columns: list[str] | None
) -> None:
    epoch = get_epoch("geih_2006_2020")
    ctx = pytest.warns(UserWarning, match="NOPE") if columns else _nullcontext()
    with ctx:
        expected = parse_module(shape_a_zip, 2015, 6, "ocupados", area, epoch, columns)
    for _ in range(2):  # first load writes the cache, second reads it
        with pytest.warns(UserWarning, match="NOPE") if columns else _nullcontext():
            got = parse_module_cached(
                shape_a_zip, 2015, 6, "ocupados", area, epoch, columns, RECORD
            )
        pd.testing.assert_frame_equal(got, expected)
    assert len(_cached_files(tmp_path)) == 1


def test_columns_keep_merge_keys_first(shape_a_zip: Path) -> None:
    epoch = get_epoch("geih_2006_2020")
    df = parse_module_cached(shape_a_zip, 2015, 6, "ocupados", "total", epoch, ["P6040"], RECORD)
    assert list(df.columns) == ["DIRECTORIO", "SECUENCIA_P", "ORDEN", "HOGAR", "P6040"]


def test_cache_false_writes_nothing(shape_a_zip: Path, tmp_path: Path) -> None:
    epoch = get_epoch("geih_2006_2020")
    parse_module_cached(shape_a_zip, 2015, 6, "ocupados", "total", epoch, None, RECORD, cache=False)
    assert _cached_files(tmp_path) == []


def test_corrupt_cache_is_replaced(shape_a_zip: Path, tmp_path: Path) -> None:
    epoch = get_epoch("geih_2006_2020")
    first = parse_module_cached(shape_a_zip, 2015, 6, "ocupados", "total", epoch, None, RECORD)
    (path,) = _cached_files(tmp_path)
    path.write_bytes(b"not a parquet file")
    again = parse_module_cached(shape_a_zip, 2015, 6, "ocupados", "total", epoch, None, RECORD)
    pd.testing.assert_frame_equal(again, first)
    assert pd.read_parquet(path).shape == first.shape


def test_cache_key_ignores_validation_but_not_url_or_module() -> None:
    base = parsed_cache_key(RECORD, "ocupados")
    validated = {**RECORD, "validated": True, "validated_at": "2026-11-28", "notes": "x"}
    assert parsed_cache_key(validated, "ocupados") == base
    assert (
        parsed_cache_key({**RECORD, "download_url": "https://example.org/y.zip"}, "ocupados")
        != base
    )
    assert parsed_cache_key(RECORD, "desocupados") != base


def test_cache_clear_parsed_removes_it(shape_a_zip: Path, tmp_path: Path) -> None:
    import pulso

    epoch = get_epoch("geih_2006_2020")
    parse_module_cached(shape_a_zip, 2015, 6, "ocupados", "total", epoch, None, RECORD)
    assert _cached_files(tmp_path)
    pulso.cache_clear("parsed")
    assert _cached_files(tmp_path) == []


class _nullcontext:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> None:
        return None
