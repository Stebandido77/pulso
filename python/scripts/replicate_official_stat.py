"""Replicate official DANE statistics as a sanity check.

This is the truth-test for the package. We pick a published DANE statistic
(e.g., the national unemployment rate for a given month) and try to reproduce
it from `pulso.load(...) + pulso.expand(...)`. If the reproduced number is
within tolerance of the published value, the harmonization and expansion
pipeline is sound for that case.

Usage:
    python scripts/replicate_official_stat.py
    python scripts/replicate_official_stat.py --stat unemployment_rate --year 2024 --month 6

Reference targets are stored in `tests/data_quality/official_targets.json`
(populated in Phase 6).
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stat", default="unemployment_rate")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--month", type=int, default=None)
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.001,
        help="Absolute tolerance in percentage points.",
    )
    parser.parse_args()

    print(
        "scripts/replicate_official_stat.py is a stub. Implementation comes in Phase 6.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
