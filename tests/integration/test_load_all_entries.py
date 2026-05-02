"""Parametrized integration tests over all 230 entries in sources.json.

For each entry, builds a synthetic ZIP and verifies that every declared module
loads without errors using the real parser (no network, no download).

Shape A entries: auto-discovery via Cabecera/Resto filenames.
Shape B entries: explicit file paths from sources.json matched in the synthetic ZIP.

Run with:
    pytest tests/integration/test_load_all_entries.py --run-integration -v
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from pulso._config.epochs import epoch_for_month
from pulso._core.parser import parse_module
from tests._build_fixtures import build_fixture_from_sources_entry

_SOURCES_PATH = Path(__file__).parent.parent.parent / "pulso" / "data" / "sources.json"
_SOURCES: dict[str, Any] = json.loads(_SOURCES_PATH.read_text(encoding="utf-8"))
_ENTRIES: dict[str, Any] = _SOURCES["data"]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("year_month", "entry"),
    list(_ENTRIES.items()),
    ids=list(_ENTRIES.keys()),
)
def test_load_all_modules_from_entry(
    year_month: str,
    entry: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Build a synthetic ZIP for the entry and parse every declared module.

    Validates that parse_module() returns a non-empty DataFrame for each module
    without raising ParseError, regardless of epoch or shape.
    """
    zip_path = tmp_path / f"{year_month}.zip"
    build_fixture_from_sources_entry(entry, zip_path)

    year, month = map(int, year_month.split("-"))
    epoch = epoch_for_month(year, month)

    for module_name in entry["modules"]:
        df = parse_module(zip_path, year, month, module_name, "total", epoch)
        assert isinstance(
            df, pd.DataFrame
        ), f"[{year_month}] Module {module_name!r} did not return a DataFrame"
        assert len(df) > 0, f"[{year_month}] Module {module_name!r} returned empty DataFrame"
