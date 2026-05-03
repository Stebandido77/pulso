"""Unit tests for pulso._core.empalme and the apply_smoothing parameter."""

from __future__ import annotations

import hashlib
import io
import zipfile
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_empalme_sub_zip(csv_content: str | None = None) -> bytes:
    """Return bytes of a minimal Shape C Empalme monthly sub-ZIP."""
    if csv_content is None:
        csv_content = "DIRECTORIO;SECUENCIA_P;ORDEN;P6020;CLASE\n1;1;1;1;1\n2;1;2;2;2\n"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "6. Junio/CSV/Características generales (personas).CSV",
            csv_content.encode("latin-1"),
        )
        zf.writestr(
            "6. Junio/CSV/Ocupados.CSV",
            csv_content.encode("latin-1"),
        )
    return buf.getvalue()


def _make_annual_empalme_zip(tmp_path: Path, year: int = 2015) -> Path:
    """Build a minimal annual Empalme ZIP with one monthly sub-ZIP."""
    inner_bytes = _make_empalme_sub_zip()
    annual_path = tmp_path / f"{year}.zip"
    with zipfile.ZipFile(annual_path, "w") as outer:
        outer.writestr(f"GEIH_Empalme_{year}/6. Junio.zip", inner_bytes)
    return annual_path


# ── year validation ───────────────────────────────────────────────────────────


def test_load_empalme_invalid_year_raises() -> None:
    """Years outside 2010-2020 must raise ValueError."""
    from pulso._core.empalme import load_empalme

    with pytest.raises(ValueError, match="2010"):
        load_empalme(2009)

    with pytest.raises(ValueError, match="2020"):
        load_empalme(2021)


def test_load_empalme_2020_raises_data_not_available() -> None:
    """Year 2020 exists in registry but ZIP is unpublished → DataNotAvailableError."""
    from pulso._core.empalme import load_empalme
    from pulso._utils.exceptions import DataNotAvailableError

    with pytest.raises(DataNotAvailableError):
        load_empalme(2020)


# ── callable with mocked downloader ──────────────────────────────────────────


def test_load_empalme_year_in_range_is_callable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """load_empalme for a valid year returns a DataFrame when downloader is mocked."""
    import pandas as pd

    from pulso._core import empalme as empalme_mod

    annual_path = _make_annual_empalme_zip(tmp_path, year=2015)

    monkeypatch.setattr(empalme_mod, "download_empalme_zip", lambda *a, **kw: annual_path)

    result = empalme_mod.load_empalme(2015, module="caracteristicas_generales", harmonize=False)

    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
    assert "year" in result.columns
    assert result["year"].iloc[0] == 2015
    assert "month" in result.columns
    assert result["month"].iloc[0] == 6


# ── apply_smoothing interface ─────────────────────────────────────────────────


def test_apply_smoothing_default_false() -> None:
    """load_merged must have apply_smoothing=False as its default."""
    import inspect

    from pulso._core.loader import load_merged

    sig = inspect.signature(load_merged)
    assert "apply_smoothing" in sig.parameters
    assert sig.parameters["apply_smoothing"].default is False


def test_apply_smoothing_out_of_range_silent(monkeypatch: pytest.MonkeyPatch) -> None:
    """apply_smoothing=True for year outside 2010-2020 is a silent no-op (no warning)."""
    import warnings

    import pandas as pd

    import pulso._config.registry as reg
    import pulso._core.loader as loader_mod

    fake_sources = {
        "metadata": {"schema_version": "1.1.0", "data_version": "2008.06"},
        "modules": {
            "caracteristicas_generales": {
                "level": "persona",
                "description_es": "CG",
                "available_in": ["geih_2006_2020"],
            }
        },
        "data": {
            "2008-06": {
                "epoch": "geih_2006_2020",
                "download_url": "https://example.com/x.zip",
                "checksum_sha256": "a" * 64,
                "modules": {
                    "caracteristicas_generales": {"cabecera": "Cab.CSV", "resto": "Rest.CSV"}
                },
                "validated": True,
            }
        },
    }
    monkeypatch.setattr(reg, "_SOURCES", fake_sources)

    fake_df = pd.DataFrame({"DIRECTORIO": [1], "SECUENCIA_P": [1], "ORDEN": [1], "CLASE": [1]})
    monkeypatch.setattr(loader_mod, "load", lambda *a, **kw: fake_df.copy())

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        loader_mod.load_merged(2008, 6, apply_smoothing=True, harmonize=False)


def test_apply_smoothing_2020_warns_and_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    """apply_smoothing=True for year=2020 emits UserWarning and proceeds with raw data."""
    import pandas as pd

    import pulso._config.registry as reg
    import pulso._core.loader as loader_mod

    fake_sources = {
        "metadata": {"schema_version": "1.1.0", "data_version": "2020.06"},
        "modules": {
            "caracteristicas_generales": {
                "level": "persona",
                "description_es": "CG",
                "available_in": ["geih_2006_2020"],
            }
        },
        "data": {
            "2020-06": {
                "epoch": "geih_2006_2020",
                "download_url": "https://example.com/x.zip",
                "checksum_sha256": "a" * 64,
                "modules": {
                    "caracteristicas_generales": {"cabecera": "Cab.CSV", "resto": "Rest.CSV"}
                },
                "validated": True,
            }
        },
    }
    monkeypatch.setattr(reg, "_SOURCES", fake_sources)

    # Mock the internal load() so no real download happens.
    fake_df = pd.DataFrame({"DIRECTORIO": [1], "SECUENCIA_P": [1], "ORDEN": [1], "CLASE": [1]})
    monkeypatch.setattr(loader_mod, "load", lambda *a, **kw: fake_df.copy())

    # Non-smoothed reference
    result_raw = loader_mod.load_merged(2020, 6, harmonize=False)

    # Smoothed for 2020 must warn
    with pytest.warns(UserWarning, match="2020"):
        result_smooth = loader_mod.load_merged(2020, 6, apply_smoothing=True, harmonize=False)

    # Shapes must match: smoothing fell back to the raw path
    assert result_smooth.shape == result_raw.shape


# ── _normalize_empalme_columns unit tests ─────────────────────────────────────


def test_normalize_empalme_columns_uppercases_all() -> None:
    """All column names must be uppercased by _normalize_empalme_columns."""
    import pandas as pd

    from pulso._core.empalme import _normalize_empalme_columns

    df = pd.DataFrame({"Hogar": [1], "Area": [2], "directorio": [3], "FEX_C": [4]})
    result = _normalize_empalme_columns(df)

    assert list(result.columns) == ["HOGAR", "AREA", "DIRECTORIO", "FEX_C"]


def test_normalize_empalme_columns_renames_fex_variants() -> None:
    """FEX_C_XXXX variants must be renamed to canonical FEX_C; others untouched."""
    import warnings

    import pandas as pd

    from pulso._core.empalme import _normalize_empalme_columns

    # FEX_C_2011 → FEX_C
    df_2011 = pd.DataFrame({"FEX_C_2011": [1.0], "P6020": [1]})
    r = _normalize_empalme_columns(df_2011)
    assert "FEX_C" in r.columns, "FEX_C_2011 must be renamed to FEX_C"
    assert "FEX_C_2011" not in r.columns
    assert "P6020" in r.columns  # unrelated column untouched

    # FEX_C_2018 → FEX_C
    df_2018 = pd.DataFrame({"fex_c_2018": [2.0]})
    r2 = _normalize_empalme_columns(df_2018)
    assert "FEX_C" in r2.columns

    # FEX_C already canonical → idempotent
    df_canonical = pd.DataFrame({"FEX_C": [3.0]})
    r3 = _normalize_empalme_columns(df_canonical)
    assert "FEX_C" in r3.columns
    assert r3["FEX_C"].iloc[0] == 3.0

    # Duplicate FEX_C + FEX_C_2011 → warns, keeps one
    df_dual = pd.DataFrame({"FEX_C": [1.0], "FEX_C_2011": [2.0], "P6040": [3]})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        r4 = _normalize_empalme_columns(df_dual)
    assert any(
        "Multiple FEX_C" in str(w.message) for w in caught
    ), "Expected UserWarning about multiple FEX_C columns"
    assert "FEX_C" in r4.columns
    assert r4.columns.tolist().count("FEX_C") == 1  # only one FEX_C column


# ──────────────────────────────────────────────────────────────────────────────
# M-3 regression tests: download_empalme_zip must verify SHA-256 when available
# ──────────────────────────────────────────────────────────────────────────────


def _patch_empalme_registry(monkeypatch: pytest.MonkeyPatch, checksum: str | None) -> None:
    """Replace _load_empalme_registry with a single-entry stub for year 2015."""
    from pulso._core import empalme as emp_mod

    fake = {
        "metadata": {"schema_version": "1.0.0"},
        "data": {
            "2015": {
                "year": 2015,
                "downloadable": True,
                "download_url": "https://example.com/empalme-2015.zip",
                "checksum_sha256": checksum,
                "size_bytes": None,
                "catalog_id": "0",
            }
        },
    }
    monkeypatch.setattr(emp_mod, "_load_empalme_registry", lambda: fake)


def test_download_empalme_zip_verifies_checksum_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker,  # type: ignore[no-untyped-def]
) -> None:
    """M-3: empalme con checksum válido pasa verificación end-to-end."""
    from pulso._core import empalme as emp_mod

    payload = b"empalme bytes"
    sha = hashlib.sha256(payload).hexdigest()
    _patch_empalme_registry(monkeypatch, sha)
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [payload]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    p = emp_mod.download_empalme_zip(2015, show_progress=False)
    assert p.exists()
    assert p.read_bytes() == payload


def test_download_empalme_zip_detects_checksum_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker,  # type: ignore[no-untyped-def]
) -> None:
    """M-3: empalme con checksum mismatch raisea ChecksumMismatchError."""
    from pulso._core import empalme as emp_mod
    from pulso._utils.exceptions import ChecksumMismatchError

    _patch_empalme_registry(monkeypatch, "f" * 64)  # never matches real bytes
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"empalme bytes"]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    with pytest.raises(ChecksumMismatchError):
        emp_mod.download_empalme_zip(2015, show_progress=False)


def test_download_empalme_zip_skips_verification_when_no_checksum(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker,  # type: ignore[no-untyped-def]
    caplog,  # type: ignore[no-untyped-def]
) -> None:
    """M-3: empalme con checksum=None acepta el archivo y emite log INFO."""
    import logging

    from pulso._core import empalme as emp_mod

    _patch_empalme_registry(monkeypatch, None)
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"unverified bytes"]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    with caplog.at_level(logging.INFO, logger="pulso._core.empalme"):
        p = emp_mod.download_empalme_zip(2015, show_progress=False)

    assert p.exists()
    assert any(
        "without SHA-256 verification" in record.message for record in caplog.records
    ), "Expected INFO log about skipped verification"


def test_download_empalme_zip_invalidates_corrupted_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker,  # type: ignore[no-untyped-def]
) -> None:
    """M-3: cached file with bad checksum gets removed and re-downloaded once."""
    from pulso._core import empalme as emp_mod

    good_payload = b"good empalme bytes"
    sha = hashlib.sha256(good_payload).hexdigest()
    _patch_empalme_registry(monkeypatch, sha)

    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))

    # Pre-populate cache with corrupted bytes.
    dest = cache_root / "empalme" / "2015.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"corrupt")

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [good_payload]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    p = emp_mod.download_empalme_zip(2015, show_progress=False)
    assert p.read_bytes() == good_payload
