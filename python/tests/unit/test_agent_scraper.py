"""Unit tests for the incremental DANE updater (python/scripts/agent_scraper.py)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("bs4")

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from agent_scraper import merge_entries  # noqa: E402
from scrape_dane_catalog import parse_microdata_files  # noqa: E402

SOURCES = Path(__file__).resolve().parents[3] / "data" / "sources.json"
NOW = "2026-12-05T03:00:00+00:00"


def _block(fid: int, name: str, mb: str) -> str:
    url = f"https://microdatos.dane.gov.co/index.php/catalog/900/download/{fid}"
    return (
        '<div class="resource-left-col">'
        f'<span class="resource-info" id="{fid}">{name}</span>'
        f"<input alt=\"Descargar [ZIP, {mb} MB]\" onclick=\"mostrarModal('{name}.zip' , '{url} ');\">"
        "</div>"
    )


def _sources() -> dict:
    return json.loads(SOURCES.read_text(encoding="utf-8"))


def test_new_month_is_added_unvalidated_with_template_modules() -> None:
    html = _block(24884, "Septiembre 2026.", "25.33") + _block(24999, "Octubre 2026", "30.1")
    entries, _ = parse_microdata_files(html, 900, 2026)
    src = _sources()
    before = copy.deepcopy(src["data"]["2026-09"])

    changes = merge_entries(src, entries, NOW)

    assert [c.split(":")[0] for c in changes["added"]] == ["2026-10"]
    new = src["data"]["2026-10"]
    assert new["validated"] is False
    assert new["download_url"].endswith("/24999")
    assert set(new["modules"]) == set(src["data"]["2026-09"]["modules"])
    assert src["data"]["2026-09"] == before
    assert src["metadata"]["covered_range"][1] == "2026-10"


def test_validated_entry_is_never_rewritten() -> None:
    src = _sources()
    key = next(k for k, v in src["data"].items() if v["validated"])
    year, month = int(key[:4]), int(key[5:])
    entry = {
        "year": year,
        "month": month,
        "download_url": "https://example.org/new.zip",
        "landing_page": None,
        "size_bytes": 1,
        "epoch_inferred": src["data"][key]["epoch"],
        "file_name": "x",
    }
    before = copy.deepcopy(src["data"][key])

    changes = merge_entries(src, [entry], NOW)

    assert src["data"][key] == before
    assert changes["flagged"]
    assert not changes["updated"]
