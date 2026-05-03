"""Unit tests for pulso._core.downloader."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_verify_checksum_match(tmp_path: Path) -> None:
    from pulso._core.downloader import verify_checksum

    f = tmp_path / "data.bin"
    data = b"hello pulso"
    f.write_bytes(data)
    assert verify_checksum(f, _sha256(data)) is True


def test_verify_checksum_mismatch(tmp_path: Path) -> None:
    from pulso._core.downloader import verify_checksum

    f = tmp_path / "data.bin"
    f.write_bytes(b"hello pulso")
    assert verify_checksum(f, "a" * 64) is False


def test_verify_checksum_case_insensitive(tmp_path: Path) -> None:
    from pulso._core.downloader import verify_checksum

    data = b"case test"
    f = tmp_path / "data.bin"
    f.write_bytes(data)
    digest = _sha256(data).upper()
    assert verify_checksum(f, digest) is True


def test_download_zip_raises_when_not_in_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DataNotAvailableError if the period is not in sources.json."""
    import pulso._config.registry as reg

    monkeypatch.setattr(
        reg,
        "_SOURCES",
        {
            "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
            "modules": {},
            "data": {},
        },
    )

    from pulso._core.downloader import download_zip
    from pulso._utils.exceptions import DataNotAvailableError

    with pytest.raises(DataNotAvailableError):
        download_zip(2024, 6)


def test_download_zip_raises_when_not_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DataNotValidatedError if entry has validated=false."""
    import pulso._config.registry as reg

    monkeypatch.setattr(
        reg,
        "_SOURCES",
        {
            "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
            "modules": {},
            "data": {
                "2024-06": {
                    "epoch": "geih_2021_present",
                    "download_url": "https://example.com/x.zip",
                    "checksum_sha256": "a" * 64,
                    "modules": {"ocupados": {"cabecera": "x.CSV"}},
                    "validated": False,
                }
            },
        },
    )

    from pulso._core.downloader import download_zip
    from pulso._utils.exceptions import DataNotValidatedError

    with pytest.raises(DataNotValidatedError):
        download_zip(2024, 6)


def test_download_zip_allow_unvalidated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
) -> None:
    """allow_unvalidated=True skips the validation guard and downloads."""
    import pulso._config.registry as reg

    data = b"fake zip content"
    sha = _sha256(data)

    monkeypatch.setattr(
        reg,
        "_SOURCES",
        {
            "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
            "modules": {},
            "data": {
                "2024-06": {
                    "epoch": "geih_2021_present",
                    "download_url": "https://example.com/x.zip",
                    "checksum_sha256": sha,
                    "modules": {"ocupados": {"cabecera": "x.CSV"}},
                    "validated": False,
                }
            },
        },
    )
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [data]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    from pulso._core.downloader import download_zip

    p = download_zip(2024, 6, allow_unvalidated=True, show_progress=False)
    assert p.exists()
    assert p.read_bytes() == data


# ---------------------------------------------------------------------------
# C-1 regression tests: download_zip must not crash when checksum_sha256 is None
# ---------------------------------------------------------------------------


def _sources_with_null_checksum() -> dict[str, Any]:
    """Registry sample mirroring real production rows where checksum_sha256 is null."""
    return {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
        "modules": {},
        "data": {
            "2024-06": {
                "epoch": "geih_2021_present",
                "download_url": "https://example.com/x.zip",
                "checksum_sha256": None,
                "modules": {"ocupados": {"cabecera": "x.CSV"}},
                "validated": False,
            }
        },
    }


def test_verify_checksum_returns_true_for_none(tmp_path: Path) -> None:
    """C-1: verify_checksum(path, None) returns True (skip verification)."""
    from pulso._core.downloader import verify_checksum

    f = tmp_path / "data.bin"
    f.write_bytes(b"anything")
    assert verify_checksum(f, None) is True


def test_download_zip_with_null_checksum_first_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
) -> None:
    """C-1.1: line 84 fix — fresh download when checksum_sha256 is None."""
    import pulso._config.registry as reg

    monkeypatch.setattr(reg, "_SOURCES", _sources_with_null_checksum())
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    payload = b"fake zip content"
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [payload]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    from pulso._core.downloader import download_zip

    p = download_zip(2024, 6, allow_unvalidated=True, show_progress=False)

    assert p.exists()
    assert p.read_bytes() == payload
    # The cache key falls back to a stable, period-derived name.
    assert p.name == "unvalidated_2024-06.zip"


def test_download_zip_with_null_checksum_cache_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """C-1.2: line 88 fix — cache-hit path when checksum_sha256 is None."""
    import pulso._config.registry as reg

    monkeypatch.setattr(reg, "_SOURCES", _sources_with_null_checksum())
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))

    payload = b"already cached"
    dest = cache_root / "raw" / "2024" / "06" / "unvalidated_2024-06.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(payload)

    import requests as req_mod

    def _no_get(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("HTTP GET should not be called when cache is valid")

    monkeypatch.setattr(req_mod, "get", _no_get)

    from pulso._core.downloader import download_zip

    result = download_zip(2024, 6, allow_unvalidated=True, show_progress=False)
    assert result == dest
    assert result.read_bytes() == payload


def test_download_zip_with_null_checksum_post_download(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
) -> None:
    """C-1.3: line 120 fix — post-download verify must not crash when checksum is None."""
    import pulso._config.registry as reg

    monkeypatch.setattr(reg, "_SOURCES", _sources_with_null_checksum())
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"bytes"]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    from pulso._core.downloader import download_zip

    # Should complete without AttributeError on .lower() of None.
    p = download_zip(2024, 6, allow_unvalidated=True, show_progress=False)
    assert p.exists()


def test_load_end_to_end_with_unvalidated_entry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
) -> None:
    """G-2: full load() flow with validated=false and checksum=None.

    This is the end-to-end test that would have caught C-1 originally —
    download_zip is invoked through pulso.load(), not directly.
    """
    import pulso
    import pulso._config.registry as reg
    import pulso._core.parser as parser_mod

    sources = _sources_with_null_checksum()
    sources["modules"] = {
        "ocupados": {
            "level": "persona",
            "description_es": "Ocu",
            "description_en": "Ocu",
            "available_in": ["geih_2021_present"],
        }
    }
    monkeypatch.setattr(reg, "_SOURCES", sources)
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    # Mock HTTP so no real network is touched.
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"fake zip bytes"]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    # Mock parse_module so the test stays at the loader/downloader layer
    # — what we actually verify is that download_zip is reached without
    # crashing on None checksum.
    import pandas as pd

    sentinel = pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})
    monkeypatch.setattr(parser_mod, "parse_module", lambda *a, **kw: sentinel)

    df = pulso.load(
        year=2024,
        month=6,
        module="ocupados",
        harmonize=False,
        show_progress=False,
        allow_unvalidated=True,
    )
    assert df is sentinel


def test_download_zip_uses_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """If the cached file exists with matching checksum, no HTTP call is made."""
    import pulso._config.registry as reg

    data = b"cached zip"
    sha = _sha256(data)
    short = sha[:16]

    monkeypatch.setattr(
        reg,
        "_SOURCES",
        {
            "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
            "modules": {},
            "data": {
                "2024-06": {
                    "epoch": "geih_2021_present",
                    "download_url": "https://example.com/x.zip",
                    "checksum_sha256": sha,
                    "modules": {"ocupados": {"cabecera": "x.CSV"}},
                    "validated": True,
                }
            },
        },
    )
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))

    dest = cache_root / "raw" / "2024" / "06" / f"{short}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)

    import requests as req_mod

    original_get = req_mod.get

    def _no_get(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("HTTP GET should not be called when cache is valid")

    monkeypatch.setattr(req_mod, "get", _no_get)

    from pulso._core.downloader import download_zip

    result = download_zip(2024, 6, show_progress=False)
    assert result == dest

    monkeypatch.setattr(req_mod, "get", original_get)
