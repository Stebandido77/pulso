"""Agent scraper for the DANE microdata portal.

Phase 5 implementation. Stubbed in Phase 0.

Strategy (in priority order):
  1. Try DANE NADA-style API endpoints if discoverable.
  2. Parse catalog HTML pages with BeautifulSoup.
  3. Fall back to Playwright for JS-rendered content.

Usage:
    python scripts/agent_scraper.py --output pulso/data/sources.json --report report.md
    python scripts/agent_scraper.py --year 2026 --month 3  # single month

The scraper is conservative:
  - New entries are written with `validated: false`
  - Previously-validated entries are NOT overwritten unless their checksum changes
  - The output is a diff report in Markdown for human review
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("pulso/data/sources.json"),
        help="Path to sources.json to update.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("scrape_report.md"),
        help="Path to write the markdown diff report.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="If provided, scrape only this year (otherwise scrape everything).",
    )
    parser.add_argument(
        "--month",
        type=int,
        default=None,
        help="If provided with --year, scrape only this month.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write changes; print what would happen.",
    )
    parser.parse_args()

    print(
        "scripts/agent_scraper.py is a stub. Implementation comes in Phase 5.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
