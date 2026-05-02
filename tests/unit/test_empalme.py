"""Unit tests for pulso._core.empalme and the apply_smoothing parameter."""

from __future__ import annotations

import io
import zipfile
from typing import TYPE_CHECKING

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
