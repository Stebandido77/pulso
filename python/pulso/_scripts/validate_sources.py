"""Validate that sources.json, variable_map.json, and epochs.json
are well-formed and mutually consistent.

This is a CLI wrapper around the same checks run by tests/unit/test_schemas.py,
intended for ad-hoc local use after editing JSON files manually.

Usage:
    python scripts/validate_sources.py
    python scripts/validate_sources.py --data-dir pulso/data
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema


def validate(data_dir: Path) -> int:
    schemas_dir = data_dir / "schemas"
    pairs = [
        ("epochs.schema.json", "epochs.json"),
        ("sources.schema.json", "sources.json"),
        ("variable_map.schema.json", "variable_map.json"),
    ]

    errors = 0
    for schema_name, data_name in pairs:
        schema_path = schemas_dir / schema_name
        data_path = data_dir / data_name
        if not schema_path.exists():
            print(f"❌ Missing schema: {schema_path}")
            errors += 1
            continue
        if not data_path.exists():
            print(f"❌ Missing data: {data_path}")
            errors += 1
            continue
        try:
            with schema_path.open(encoding="utf-8") as f:
                schema = json.load(f)
            with data_path.open(encoding="utf-8") as f:
                data = json.load(f)
            jsonschema.validate(instance=data, schema=schema)
            print(f"✅ {data_name} validates against {schema_name}")
        except jsonschema.ValidationError as e:
            print(f"❌ {data_name}:")
            print(f"   {e.message}")
            print(f"   at: {' -> '.join(str(x) for x in e.absolute_path)}")
            errors += 1
        except json.JSONDecodeError as e:
            print(f"❌ {data_name} is not valid JSON: {e}")
            errors += 1

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("pulso/data"),
    )
    args = parser.parse_args()

    errors = validate(args.data_dir)
    if errors == 0:
        print("\nAll JSON files validate.")
        return 0
    print(f"\n{errors} validation error(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
