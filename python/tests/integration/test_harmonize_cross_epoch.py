"""Cross-epoch harmonization tests for representative months.

Verifies that the full parse → merge → harmonize pipeline produces canonical
variables for months from both GEIH-1 (2006-2021) and GEIH-2 (2022-present)
epochs using synthetic fixtures.

Run with:
    pytest tests/integration/test_harmonize_cross_epoch.py --run-integration -v
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from pulso._config.epochs import epoch_for_month
from pulso._core.harmonizer import harmonize_dataframe
from pulso._core.merger import merge_modules
from pulso._core.parser import parse_module
from tests._build_fixtures import build_fixture_from_sources_entry

_SOURCES_PATH = Path(__file__).parent.parent.parent / "pulso" / "data" / "sources.json"
_SOURCES: dict[str, Any] = json.loads(_SOURCES_PATH.read_text(encoding="utf-8"))

_VM_PATH = Path(__file__).parent.parent.parent / "pulso" / "data" / "variable_map.json"
_CANONICAL_VARS: list[str] = list(
    json.loads(_VM_PATH.read_text(encoding="utf-8"))["variables"].keys()
)

# Representative months: one early GEIH-1, mid GEIH-1, late GEIH-1, early GEIH-2, recent
_REPRESENTATIVE_MONTHS = [
    (2007, 12),  # first stable GEIH-1 month in catalog
    (2010, 6),  # mid GEIH-1
    (2015, 6),  # mid GEIH-1
    (2019, 6),  # late GEIH-1
    (2021, 12),  # last GEIH-1
    (2022, 1),  # first GEIH-2
    (2024, 6),  # manually validated GEIH-2 reference
    (2025, 6),  # recent GEIH-2
]

# Variables producible from our minimal synthetic columns (always expected)
_CORE_CANONICAL_VARS = {
    "sexo",
    "edad",
    "grupo_edad",
    "area",
    "peso_expansion",
    "peso_expansion_persona",
}


@pytest.mark.integration
@pytest.mark.parametrize(
    ("year", "month"),
    _REPRESENTATIVE_MONTHS,
    ids=[f"{y}-{m:02d}" for y, m in _REPRESENTATIVE_MONTHS],
)
def test_harmonize_produces_canonical_variables(
    year: int,
    month: int,
    tmp_path: Path,
) -> None:
    """Build fixture, merge all modules, harmonize, and assert core canonical vars present.

    Covers both epochs (GEIH-1 and GEIH-2) and verifies that harmonize_dataframe
    runs without error and produces at least the core variables derived from
    the synthetic fixture columns.
    """
    key = f"{year}-{month:02d}"
    entry = _SOURCES["data"][key]

    zip_path = tmp_path / f"{key}.zip"
    build_fixture_from_sources_entry(entry, zip_path)

    epoch = epoch_for_month(year, month)

    module_dfs: dict[str, pd.DataFrame] = {}
    for module_name in entry["modules"]:
        df = parse_module(zip_path, year, month, module_name, "total", epoch)
        module_dfs[module_name] = df

    merged = merge_modules(module_dfs, epoch, level="persona", how="outer")

    harmonized = harmonize_dataframe(merged, epoch)

    assert isinstance(harmonized, pd.DataFrame), (
        f"[{key}] harmonize_dataframe must return DataFrame"
    )
    assert len(harmonized) > 0, f"[{key}] harmonized DataFrame must be non-empty"

    actual_canonical = {v for v in _CANONICAL_VARS if v in harmonized.columns}

    assert _CORE_CANONICAL_VARS.issubset(actual_canonical), (
        f"[{key}] Core canonical variables missing. "
        f"Expected {sorted(_CORE_CANONICAL_VARS)}, "
        f"got {sorted(actual_canonical)}"
    )

    # With comprehensive fixture columns, most canonical variables should be produced
    assert len(actual_canonical) >= len(_CANONICAL_VARS) // 2, (
        f"[{key}] Only {len(actual_canonical)} of {len(_CANONICAL_VARS)} canonical vars produced. "
        f"Got: {sorted(actual_canonical)}"
    )
