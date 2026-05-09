"""Updates sources.json with real SHA256 for the 5 strategic months.

Run AFTER all smoke tests pass and ZIPs are cached:
    python tests/integration/_update_checksums.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from tests.integration._helpers import SOURCES_PATH, compute_sha256, get_cached_zip

REPRESENTATIVE_MONTHS = [
    (2007, 12),
    (2015, 6),
    (2021, 12),
    (2022, 1),
    (2024, 6),
]


def main() -> None:
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))

    updated = 0
    for year, month in REPRESENTATIVE_MONTHS:
        zip_path = get_cached_zip(year, month)
        sha = compute_sha256(zip_path)

        key = f"{year}-{month:02d}"
        old_sha = sources["data"][key].get("checksum_sha256")

        if old_sha == sha:
            print(f"{key}: checksum unchanged ({sha[:16]}...)")
        else:
            sources["data"][key]["checksum_sha256"] = sha
            sources["data"][key]["validated"] = True
            sources["data"][key]["validated_by"] = "automated"
            sources["data"][key]["validated_at"] = datetime.now(timezone.utc).isoformat()
            updated += 1
            print(f"{key}: updated to {sha[:16]}...")

    SOURCES_PATH.write_text(
        json.dumps(sources, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Validate against schema
    import jsonschema

    schema = json.loads(
        (SOURCES_PATH.parent / "schemas" / "sources.schema.json").read_text(encoding="utf-8")
    )
    jsonschema.validate(instance=sources, schema=schema)
    print(f"\nUpdated {updated} entries. Schema validation: OK")


if __name__ == "__main__":
    main()
