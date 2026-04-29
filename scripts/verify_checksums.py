"""Verify that locally-cached ZIPs match the checksums in sources.json.

Useful before a release or after a long pause to detect cache corruption.

Usage:
    python scripts/verify_checksums.py
    python scripts/verify_checksums.py --year 2024
    python scripts/verify_checksums.py --year 2024 --month 6
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--month", type=int, default=None)
    args = parser.parse_args()

    from pulso._config.registry import _load_sources
    from pulso._core.downloader import verify_checksum
    from pulso._utils.cache import cache_path

    sources = _load_sources()
    cache_root = cache_path()

    mismatches: list[str] = []
    checked = 0

    for key, record in sources["data"].items():
        year_str, month_str = key.split("-")
        y, m = int(year_str), int(month_str)

        if args.year is not None and y != args.year:
            continue
        if args.month is not None and m != args.month:
            continue

        sha = record["checksum_sha256"]
        short = sha[:16]
        cached = cache_root / "raw" / str(y) / f"{m:02d}" / f"{short}.zip"

        if not cached.exists():
            print(f"  SKIP  {key}  (not cached)")
            continue

        ok = verify_checksum(cached, sha)
        checked += 1
        status = "  OK  " if ok else "  FAIL"
        print(f"{status}  {key}  {cached}")
        if not ok:
            mismatches.append(key)

    print(f"\nChecked {checked} file(s). {len(mismatches)} mismatch(es).")

    if mismatches:
        print("Mismatched entries:", file=sys.stderr)
        for k in mismatches:
            print(f"  {k}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
