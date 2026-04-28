"""Verify that locally-cached ZIPs match the checksums in sources.json.

Useful before a release or after a long pause to detect cache corruption.

Usage:
    python scripts/verify_checksums.py
    python scripts/verify_checksums.py --year 2024
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--month", type=int, default=None)
    parser.parse_args()

    print(
        "scripts/verify_checksums.py is a stub. Implementation comes in Phase 1.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
