"""Unit regression tests for nested-ZIP parsing (Fix 1, 2024-03/04 ParseError).

The DANE GEIH releases for 2024-03 and 2024-04 ship the data in a *wrapped*
form: the outer ZIP contains only ``CSV.zip``, ``DTA.zip``, and ``SAV.zip``
entries, and the actual CSVs live inside the matching format ZIP. The
parser must descend into the inner ZIP transparently — without changing
``sources.json`` (which lists the inner path as if there were no wrapper).
"""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING, Any

import pytest

from pulso._config.epochs import get_epoch
from pulso._core.parser import (
    _is_nested_format_wrapper,
    _open_nested_zip,
    _parse_csv,
)
from pulso._utils.exceptions import ParseError

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _build_inner_csv_zip() -> bytes:
    """Build a minimal CSV.zip containing one Ocupados.CSV file."""
    inner_buf = io.BytesIO()
    with zipfile.ZipFile(inner_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as izf:
        # Mimic the geih_2021_present CSV: comma separator, CLASE column.
        csv_payload = (
            "DIRECTORIO,SECUENCIA_P,ORDEN,CLASE,P6040\n1,1,1,1,25\n2,1,1,2,30\n3,1,1,1,45\n"
        )
        izf.writestr("CSV/Ocupados.CSV", csv_payload)
    return inner_buf.getvalue()


def _build_nested_outer_zip(tmp_path: Path) -> Path:
    """Build a 2024-03/04-style outer ZIP containing only CSV.zip/DTA.zip/SAV.zip."""
    outer = tmp_path / "unvalidated_2024-03.zip"
    inner_csv_bytes = _build_inner_csv_zip()
    with zipfile.ZipFile(outer, mode="w", compression=zipfile.ZIP_DEFLATED) as ozf:
        ozf.writestr("CSV.zip", inner_csv_bytes)
        # Stub DTA/SAV ZIPs so the wrapper detection still succeeds.
        ozf.writestr("DTA.zip", b"PK\x05\x06" + b"\x00" * 18)
        ozf.writestr("SAV.zip", b"PK\x05\x06" + b"\x00" * 18)
    return outer


def _build_direct_outer_zip(tmp_path: Path) -> Path:
    """Build a non-nested ZIP that places CSV/Ocupados.CSV at the root (control)."""
    outer = tmp_path / "direct_2024-05.zip"
    with zipfile.ZipFile(outer, mode="w", compression=zipfile.ZIP_DEFLATED) as ozf:
        csv_payload = "DIRECTORIO,SECUENCIA_P,ORDEN,CLASE,P6040\n1,1,1,1,25\n2,1,1,2,30\n"
        ozf.writestr("CSV/Ocupados.CSV", csv_payload)
    return outer


# ---------------------------------------------------------------------------
# _is_nested_format_wrapper
# ---------------------------------------------------------------------------


def test_is_nested_format_wrapper_detects_2024_03_layout(tmp_path: Path) -> None:
    outer = _build_nested_outer_zip(tmp_path)
    with zipfile.ZipFile(outer) as zf:
        assert _is_nested_format_wrapper(zf) is True


def test_is_nested_format_wrapper_rejects_direct_layout(tmp_path: Path) -> None:
    outer = _build_direct_outer_zip(tmp_path)
    with zipfile.ZipFile(outer) as zf:
        assert _is_nested_format_wrapper(zf) is False


def test_is_nested_format_wrapper_rejects_empty_zip(tmp_path: Path) -> None:
    empty = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty, mode="w") as _zf:
        pass
    with zipfile.ZipFile(empty) as zf:
        assert _is_nested_format_wrapper(zf) is False


def test_is_nested_format_wrapper_rejects_mixed_zip(tmp_path: Path) -> None:
    """A ZIP that has CSV.zip but ALSO has loose CSVs is not a wrapper."""
    p = tmp_path / "mixed.zip"
    with zipfile.ZipFile(p, mode="w") as zf:
        zf.writestr("CSV.zip", b"PK\x05\x06" + b"\x00" * 18)
        zf.writestr("Ocupados.CSV", "x,y\n1,2\n")
    with zipfile.ZipFile(p) as zf:
        assert _is_nested_format_wrapper(zf) is False


# ---------------------------------------------------------------------------
# _open_nested_zip
# ---------------------------------------------------------------------------


def test_open_nested_zip_returns_inner_handle(tmp_path: Path) -> None:
    outer = _build_nested_outer_zip(tmp_path)
    with zipfile.ZipFile(outer) as zf, _open_nested_zip(zf, "csv") as inner:
        names = inner.namelist()
        assert "CSV/Ocupados.CSV" in names


def test_open_nested_zip_unknown_format_raises(tmp_path: Path) -> None:
    outer = _build_nested_outer_zip(tmp_path)
    with zipfile.ZipFile(outer) as zf, pytest.raises(KeyError, match="No known nested wrapper"):
        _open_nested_zip(zf, "parquet")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _parse_csv end-to-end (Fix 1 regression)
# ---------------------------------------------------------------------------


def test_parse_csv_handles_2024_03_nested_wrapper(tmp_path: Path) -> None:
    """Regression: pulso 1.0.0rc2 raised ParseError on 2024-03 because the
    parser opened the outer ZIP and couldn't find ``CSV/Ocupados.CSV`` —
    the file actually lives inside ``CSV.zip``. After Fix 1 the parser
    descends into the nested wrapper transparently.
    """
    outer = _build_nested_outer_zip(tmp_path)
    epoch = get_epoch("geih_2021_present")

    df = _parse_csv(outer, "CSV/Ocupados.CSV", epoch, columns=None)

    assert list(df.columns) == ["DIRECTORIO", "SECUENCIA_P", "ORDEN", "CLASE", "P6040"]
    assert len(df) == 3
    assert df["P6040"].tolist() == [25, 30, 45]


def test_parse_csv_direct_layout_unchanged(tmp_path: Path) -> None:
    """Non-nested layouts (the common case) keep working unchanged."""
    outer = _build_direct_outer_zip(tmp_path)
    epoch = get_epoch("geih_2021_present")

    df = _parse_csv(outer, "CSV/Ocupados.CSV", epoch, columns=None)

    assert len(df) == 2
    assert "DIRECTORIO" in df.columns


def test_parse_csv_missing_file_in_nested_still_raises(tmp_path: Path) -> None:
    """If the requested CSV is not in the inner ZIP either, raise ParseError —
    don't silently return empty.
    """
    outer = _build_nested_outer_zip(tmp_path)
    epoch = get_epoch("geih_2021_present")

    with pytest.raises(ParseError, match="not found"):
        _parse_csv(outer, "CSV/DoesNotExist.CSV", epoch, columns=None)


# ---------------------------------------------------------------------------
# parse_module dispatch through nested wrapper (full pipeline regression)
# ---------------------------------------------------------------------------


@pytest.fixture
def fixture_sources_2024_03_nested(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> dict[str, Any]:
    """Inject a synthetic 2024-03 sources entry pointing at a nested-wrapper ZIP."""
    import pulso._config.registry as reg

    outer = _build_nested_outer_zip(tmp_path)

    # Build a sources fragment that mirrors the real 2024-03 entry shape.
    fake_sources = {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.03"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Ocupados",
                "available_in": ["geih_2021_present"],
            },
        },
        "data": {
            "2024-03": {
                "epoch": "geih_2021_present",
                "download_url": "https://example.com/2024-03.zip",
                "checksum_sha256": None,
                "modules": {"ocupados": {"file": "CSV/Ocupados.CSV"}},
                "validated": False,
            }
        },
    }
    monkeypatch.setattr(reg, "_SOURCES", fake_sources)
    return {"zip_path": outer}


def test_parse_module_2024_03_nested_works(
    fixture_sources_2024_03_nested: dict[str, Any],
) -> None:
    """End-to-end: parse_module on a 2024-03-shaped nested ZIP returns rows."""
    from pulso._core.parser import parse_module

    epoch = get_epoch("geih_2021_present")
    df: pd.DataFrame = parse_module(
        fixture_sources_2024_03_nested["zip_path"],
        2024,
        3,
        "ocupados",
        "total",
        epoch,
    )
    # All 3 rows pass through (no area filter on "total" — both CLASE 1 & 2 stay).
    assert len(df) == 3
    assert "CLASE" in df.columns
