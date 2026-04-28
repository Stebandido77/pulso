"""CLI to add a single month manually to sources.json.

Use this when the scraper hasn't picked up a month yet, or when you want to
add an entry while developing.

Usage:
    python scripts/add_month.py --year 2026 --month 4 --url https://...

The script:
  1. Downloads the ZIP
  2. Computes SHA-256
  3. Inspects internal structure (lists files in Cabecera/ and Resto/)
  4. Proposes module path mappings (you confirm interactively or with --auto)
  5. Writes the entry to sources.json (with validated=false)

After adding, run a smoke test:
`pulso.load(year, month, "ocupados", allow_unvalidated=True)`,
then if it works, manually flip `validated: true` and `validated_by: manual`.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True, choices=range(1, 13))
    parser.add_argument("--url", type=str, required=True, help="Direct URL to the ZIP.")
    parser.add_argument("--landing-page", type=str, default=None)
    parser.add_argument(
        "--epoch",
        type=str,
        default=None,
        help="Epoch key. If omitted, inferred from year.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Don't prompt; accept inferred module mappings.",
    )
    parser.parse_args()

    print(
        "scripts/add_month.py is a stub. Implementation comes in Phase 1.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
