"""Tests for pulso.update_catalog() (catalog refresh without a package upgrade)."""

from __future__ import annotations

import copy
import json
from typing import TYPE_CHECKING, Any

import pytest

import pulso
from pulso._config import registry as reg
from pulso._utils.exceptions import ConfigError, DownloadError

if TYPE_CHECKING:
    from pathlib import Path


class _Resp:
    def __init__(self, content: bytes, status: int = 200) -> None:
        self.content = content
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")


@pytest.fixture
def isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("PULSO_IGNORE_CACHED_CATALOG", raising=False)
    monkeypatch.setattr(reg, "_SOURCES", None)
    return tmp_path


def _newer_catalog() -> dict[str, Any]:
    src = copy.deepcopy(reg._load_sources())
    last = max(src["data"])
    year, month = int(last[:4]), int(last[5:])
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    key = f"{year}-{month:02d}"
    src["data"][key] = copy.deepcopy(src["data"][last])
    src["data"][key]["validated"] = False
    src["metadata"]["covered_range"][1] = key
    return src


def test_update_catalog_saves_newer_catalog_and_load_uses_it(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fresh = _newer_catalog()
    monkeypatch.setattr("requests.get", lambda *a, **k: _Resp(json.dumps(fresh).encode()))

    info = pulso.update_catalog()

    assert info["latest_end"] == fresh["metadata"]["covered_range"][1]
    assert info["path"] is not None
    assert (isolated / "catalog" / "sources.json").exists()
    assert reg._load_sources()["metadata"]["covered_range"][1] == info["latest_end"]


def test_update_catalog_ignores_older_catalog(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    older = copy.deepcopy(reg._load_sources())
    older["data"].pop(max(older["data"]))
    older["metadata"]["covered_range"][1] = max(older["data"])
    monkeypatch.setattr("requests.get", lambda *a, **k: _Resp(json.dumps(older).encode()))

    info = pulso.update_catalog()

    assert info["path"] is None
    assert not (isolated / "catalog" / "sources.json").exists()


def test_update_catalog_rejects_invalid_payload(
    isolated: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("requests.get", lambda *a, **k: _Resp(b"<html>nope</html>"))
    with pytest.raises(ConfigError):
        pulso.update_catalog()


def test_update_catalog_network_error(isolated: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("requests.get", lambda *a, **k: _Resp(b"", status=503))
    with pytest.raises(DownloadError):
        pulso.update_catalog()
