"""Test that the bundled JSON data files validate against their schemas.

This is the most important test in Phase 0: it locks the contract between
the code-side agent (Claude Code) and the data-side agent (Codex).
If this test passes, both agents can rely on the JSON shape.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import jsonschema
import pytest

if TYPE_CHECKING:
    from pathlib import Path


SCHEMA_FILE_PAIRS = [
    ("epochs.schema.json", "epochs.json"),
    ("sources.schema.json", "sources.json"),
    ("variable_map.schema.json", "variable_map.json"),
]


@pytest.mark.parametrize(("schema_name", "data_name"), SCHEMA_FILE_PAIRS)
def test_data_validates_against_schema(
    data_dir: Path,
    schemas_dir: Path,
    schema_name: str,
    data_name: str,
) -> None:
    """Each bundled JSON file must validate against its schema."""
    schema_path = schemas_dir / schema_name
    data_path = data_dir / data_name

    assert schema_path.exists(), f"Missing schema: {schema_path}"
    assert data_path.exists(), f"Missing data file: {data_path}"

    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)
    with data_path.open(encoding="utf-8") as f:
        data = json.load(f)

    # Will raise jsonschema.ValidationError on failure.
    jsonschema.validate(instance=data, schema=schema)


def test_sources_references_only_defined_epochs(data_dir: Path) -> None:
    """Every `epoch` referenced in sources.json must exist in epochs.json."""
    with (data_dir / "epochs.json").open(encoding="utf-8") as f:
        epochs = json.load(f)
    with (data_dir / "sources.json").open(encoding="utf-8") as f:
        sources = json.load(f)

    defined_epochs = set(epochs["epochs"].keys())
    for month_key, record in sources["data"].items():
        assert record["epoch"] in defined_epochs, (
            f"sources.json[{month_key}] references undefined epoch: {record['epoch']}"
        )


def test_sources_references_only_defined_modules(data_dir: Path) -> None:
    """Every module referenced in sources.json data must be defined in modules section."""
    with (data_dir / "sources.json").open(encoding="utf-8") as f:
        sources = json.load(f)

    defined_modules = set(sources["modules"].keys())
    for month_key, record in sources["data"].items():
        for mod in record["modules"]:
            assert mod in defined_modules, (
                f"sources.json[{month_key}] references undefined module: {mod}"
            )


def test_variable_map_references_only_defined_epochs(data_dir: Path) -> None:
    """Every epoch in variable_map.json must exist in epochs.json."""
    with (data_dir / "epochs.json").open(encoding="utf-8") as f:
        epochs = json.load(f)
    with (data_dir / "variable_map.json").open(encoding="utf-8") as f:
        vmap = json.load(f)

    defined_epochs = set(epochs["epochs"].keys())
    for var_name, var_def in vmap["variables"].items():
        for epoch_key in var_def["mappings"]:
            assert epoch_key in defined_epochs, (
                f"variable_map.json[{var_name}] references undefined epoch: {epoch_key}"
            )


def test_variable_map_references_only_defined_modules(data_dir: Path) -> None:
    """Every module in variable_map.json variables must exist in sources.json modules."""
    with (data_dir / "sources.json").open(encoding="utf-8") as f:
        sources = json.load(f)
    with (data_dir / "variable_map.json").open(encoding="utf-8") as f:
        vmap = json.load(f)

    defined_modules = set(sources["modules"].keys())
    for var_name, var_def in vmap["variables"].items():
        assert var_def["module"] in defined_modules, (
            f"variable_map.json[{var_name}] references undefined module: {var_def['module']}"
        )
