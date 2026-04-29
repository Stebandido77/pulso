"""Unit tests for pulso._utils.cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_cache_path_uses_env_var(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    custom = tmp_path / "my_cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(custom))

    # Clear any previously imported module state.
    from pulso._utils.cache import cache_path

    p = cache_path()
    assert p == custom.resolve()
    assert p.exists()


def test_cache_path_creates_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "nested" / "pulso_cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(target))

    from pulso._utils.cache import cache_path

    p = cache_path()
    assert p.is_dir()


def test_cache_path_returns_absolute(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    from pulso._utils.cache import cache_path

    p = cache_path()
    assert p.is_absolute()


def test_cache_info_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

    from pulso._utils.cache import cache_info

    info = cache_info()
    assert info["total_size_bytes"] == 0
    assert info["n_files"] == 0
    assert "by_level" in info
    by_level = info["by_level"]
    assert isinstance(by_level, dict)
    for lvl in ("raw", "parsed", "harmonized"):
        assert lvl in by_level


def test_cache_info_counts_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))

    raw_dir = cache_root / "raw" / "2024" / "01"
    raw_dir.mkdir(parents=True)
    (raw_dir / "test.zip").write_bytes(b"x" * 100)

    from pulso._utils.cache import cache_info

    info = cache_info()
    assert info["n_files"] == 1
    assert info["total_size_bytes"] == 100
    by_level = info["by_level"]
    assert isinstance(by_level, dict)
    assert by_level["raw"]["n_files"] == 1


def test_cache_clear_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))

    raw_dir = cache_root / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "a.zip").write_bytes(b"data")

    from pulso._utils.cache import cache_clear, cache_info

    cache_clear("all")
    info = cache_info()
    assert info["n_files"] == 0


def test_cache_clear_level(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("PULSO_CACHE_DIR", str(cache_root))

    (cache_root / "raw").mkdir(parents=True)
    (cache_root / "raw" / "a.zip").write_bytes(b"raw data")
    (cache_root / "parsed").mkdir(parents=True)
    (cache_root / "parsed" / "b.parquet").write_bytes(b"parsed data")

    from pulso._utils.cache import cache_clear, cache_info

    cache_clear("raw")
    info = cache_info()
    assert info["by_level"]["raw"]["n_files"] == 0  # type: ignore[index]
    assert info["by_level"]["parsed"]["n_files"] == 1  # type: ignore[index]
