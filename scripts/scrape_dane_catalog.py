"""Scrape the DANE GEIH catalog and produce _scraped_catalog.json.

Strategy (discovered via Phase 3.1 research):
  DANE GEIH data is organized in ANNUAL catalogs under the MERCLAB-Microdatos
  collection at microdatos.dane.gov.co.  Each annual catalog (e.g., 2024 → ID 819)
  has its own /get_microdata page listing all monthly ZIP files.

  This script:
    1. Enumerates the MERCLAB-Microdatos collection pages (up to 15 pages)
       to discover annual GEIH catalog IDs.
    2. Filters to main annual GEIH catalogs (excludes Empalme, San Andrés,
       Ciudades Intermedias, Módulos auxiliares, etc.).
    3. For each annual catalog, fetches /get_microdata and parses monthly
       file entries.
    4. Selects a primary download file per month (CSV preferred; SPSS fallback).
    5. Writes structured output to _scraped_catalog.json.

Note: The ADR 0004 described a sequential-ID-scan strategy.  Inspection of the
live site revealed that annual catalogs are the actual unit of organisation;
collection enumeration is both faster and more reliable.  CATALOG_NOTES.md
documents this deviation.

Usage:
    python scripts/scrape_dane_catalog.py --output pulso/data/_scraped_catalog.json
    python scripts/scrape_dane_catalog.py --output ... --dry-run
    python scripts/scrape_dane_catalog.py --output ... --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_AGENT = "pulso-catalog-scraper/0.3.1 (https://github.com/Stebandido77/pulso)"
BASE_URL = "https://microdatos.dane.gov.co"
COLLECTION_URL = BASE_URL + "/index.php/catalog/?collection[]=MERCLAB-Microdatos&page={page}"
CATALOG_URL = BASE_URL + "/index.php/catalog/{cid}"
MICRODATA_URL = BASE_URL + "/index.php/catalog/{cid}/get_microdata"

RATE_LIMIT_SECONDS = 2.0
TIMEOUT_SECONDS = 15
MAX_RETRIES = 3

SPANISH_MONTHS = {
    # Full names
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    # Abbreviations used by DANE in newer catalogs (e.g. "Ene_2024")
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    # "may" omitted — ambiguous without "_" context; "mayo" already covers it
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

# Patterns that indicate an auxiliary (non-primary) file
AUXILIARY_KEYWORDS_RE = re.compile(
    r"total|fex|fact.?exp|proyecci|cnpv|factores|amdr|factor",
    re.IGNORECASE,
)

# Title patterns that identify a MAIN annual GEIH catalog (not a module/special)
MAIN_GEIH_TITLE_RE = re.compile(
    r"gran encuesta integrada de hogares.*?geih.*?\d{4}",
    re.IGNORECASE,
)
EXCLUDE_KEYWORDS_RE = re.compile(
    r"empalme|san andr[eé]s|ciudades intermedias|m[oó]dulo|mfpt|mti|mtic"
    r"|etnia|ciiu|factores de expansi[oó]n|nuevos departamentos|pandemia"
    r"|anuario|semestre|trimestre",
    re.IGNORECASE,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def fetch_with_retry(
    url: str,
    session: requests.Session,
    label: str = "",
) -> str | None:
    """Fetch URL with rate-limiting and retries. Returns HTML or None."""
    time.sleep(RATE_LIMIT_SECONDS)
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, timeout=TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                log.debug("%s: 404 not found", label or url)
                return None
            log.warning("%s: HTTP %s (attempt %d)", label or url, resp.status_code, attempt + 1)
        except requests.RequestException as exc:
            log.warning("%s: %s (attempt %d)", label or url, exc, attempt + 1)
        if attempt < MAX_RETRIES - 1:
            time.sleep(2 ** (attempt + 1))
    log.error("%s: all retries exhausted", label or url)
    return None


# ---------------------------------------------------------------------------
# Collection discovery
# ---------------------------------------------------------------------------


def discover_annual_geih_catalogs(session: requests.Session) -> list[tuple[int, int, str]]:
    """Return list of (catalog_id, year, title) for main annual GEIH catalogs.

    Enumerates up to 15 pages of MERCLAB-Microdatos collection.
    """
    found: list[tuple[int, int, str]] = []
    seen_ids: set[int] = set()

    for page in range(1, 16):
        url = COLLECTION_URL.format(page=page)
        html = fetch_with_retry(url, session, f"collection page {page}")
        if html is None:
            log.warning("Failed to fetch collection page %d, stopping.", page)
            break

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)
        entries_on_page = 0

        for a in links:
            href = a["href"]
            m = re.search(r"/catalog/(\d+)$", href)
            if not m:
                continue
            cid = int(m.group(1))
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            title = a.text.strip()
            entries_on_page += 1

            if not MAIN_GEIH_TITLE_RE.search(title):
                continue
            if EXCLUDE_KEYWORDS_RE.search(title):
                log.debug("Skipping non-main GEIH: ID=%d %s", cid, title)
                continue

            year_m = re.search(r"\b(20\d{2})\b", title)
            if not year_m:
                log.debug("No year in title: ID=%d %s", cid, title)
                continue

            year = int(year_m.group(1))
            log.info("Annual GEIH catalog: ID=%d year=%d  %s", cid, year, title)
            found.append((cid, year, title))

        log.info("Collection page %d: %d catalog links examined", page, entries_on_page)
        if entries_on_page == 0:
            log.info("No entries on page %d, stopping collection scan.", page)
            break

    # Deduplicate by year — keep the one with higher catalog_id if duplicated
    by_year: dict[int, tuple[int, int, str]] = {}
    for cid, year, title in found:
        if year not in by_year or cid > by_year[year][0]:
            by_year[year] = (cid, year, title)

    result = sorted(by_year.values(), key=lambda x: x[1])
    log.info("Total main annual GEIH catalogs: %d", len(result))
    return result


# ---------------------------------------------------------------------------
# Monthly file parsing
# ---------------------------------------------------------------------------


def parse_size_bytes(alt_text: str) -> int | None:
    """Parse 'Descargar [ZIP, 7.82 MB]' → bytes as int."""
    m = re.search(r"([\d.,]+)\s*(MB|GB|KB)", alt_text, re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    unit = m.group(2).upper()
    multipliers = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
    return int(value * multipliers[unit])


def detect_month_from_name(name: str) -> int | None:
    """Return month number (1-12) if name contains a Spanish month name.

    Checks full names before abbreviations to avoid false positives
    (e.g., "enero" must be matched before "ene").
    """
    name_lower = name.lower()
    # Check full names first (sorted longest-first to avoid prefix clashes)
    full_names = [
        ("enero", 1),
        ("febrero", 2),
        ("marzo", 3),
        ("abril", 4),
        ("mayo", 5),
        ("junio", 6),
        ("julio", 7),
        ("agosto", 8),
        ("septiembre", 9),
        ("octubre", 10),
        ("noviembre", 11),
        ("diciembre", 12),
    ]
    for month_name, month_num in full_names:
        if month_name in name_lower:
            return month_num
    # Fall back to abbreviations (only if no full name matched)
    abbrevs = [
        ("sep", 9),
        ("oct", 10),
        ("nov", 11),
        ("dic", 12),
        ("ene", 1),
        ("feb", 2),
        ("mar", 3),
        ("abr", 4),
        ("jun", 6),
        ("jul", 7),
        ("ago", 8),
    ]
    for abbrev, month_num in abbrevs:
        if abbrev in name_lower:
            return month_num
    return None


def detect_format_priority(name: str) -> int:
    """Lower = more preferred. CSV > no-extension ZIP > SPSS > Stata > TXT.

    Trailing dots/spaces in file names (e.g. "Mayo.csv.") are stripped before
    checking the suffix to handle DANE's occasional naming inconsistencies.
    """
    lower = name.strip(". ").lower()
    if lower.endswith(".csv"):
        return 0
    if lower.endswith(".zip"):
        return 1
    if "." not in lower.rsplit("/", 1)[-1]:
        return 1  # no extension = likely primary SPSS/ZIP
    if lower.endswith((".spss", ".sav")):
        return 2
    if lower.endswith(".dta"):
        return 3
    if lower.endswith(".txt"):
        return 4
    return 5


def parse_microdata_files(
    html: str,
    catalog_id: int,
    year: int,
) -> tuple[list[dict], list[str]]:
    """Parse /get_microdata HTML and return (monthly_entries, anomalies).

    Returns one entry per month found, selecting the primary download file.
    """
    soup = BeautifulSoup(html, "html.parser")
    spans = soup.find_all("span", class_="resource-info")

    # Collect all candidate files: {month_num: [(priority, file_id, name, size_bytes, url)]}
    candidates: dict[int, list[tuple[int, str, str, int | None, str]]] = {}
    skipped_names: list[str] = []

    for span in spans:
        file_id = span.get("id", "").strip()
        raw_name = span.text.strip()

        if not file_id:
            continue

        # Check if auxiliary
        if AUXILIARY_KEYWORDS_RE.search(raw_name):
            log.debug("  Skipping auxiliary file: %s (id=%s)", raw_name, file_id)
            skipped_names.append(raw_name)
            continue

        month_num = detect_month_from_name(raw_name)
        if month_num is None:
            log.debug("  No month in file name: %s", raw_name)
            skipped_names.append(raw_name)
            continue

        # Get size and URL from input button
        parent_div = span.find_parent("div", class_="resource-left-col")
        size_bytes: int | None = None
        download_url = f"{BASE_URL}/index.php/catalog/{catalog_id}/download/{file_id}"

        if parent_div:
            inp = parent_div.find("input")
            if inp:
                alt = inp.get("alt", "")
                size_bytes = parse_size_bytes(alt)
                onclick = inp.get("onclick", "")
                url_m = re.search(r"'(https://[^']+)'", onclick)
                if url_m:
                    download_url = url_m.group(1).strip()

        priority = detect_format_priority(raw_name)
        candidates.setdefault(month_num, []).append(
            (priority, file_id, raw_name, size_bytes, download_url)
        )

    # Build one entry per month, selecting the best-priority file
    entries = []
    anomalies = []

    for month_num in sorted(candidates.keys()):
        files = sorted(candidates[month_num], key=lambda x: x[0])
        best = files[0]
        priority, file_id, name, size_bytes, download_url = best

        epoch = infer_epoch(year, month_num)
        entry: dict = {
            "year": year,
            "month": month_num,
            "catalog_id": catalog_id,
            "file_id": int(file_id),
            "download_url": download_url,
            "landing_page": CATALOG_URL.format(cid=catalog_id),
            "checksum_sha256": None,
            "size_bytes": size_bytes,
            "epoch_inferred": epoch,
            "file_name": name,
            "anomalies": [],
        }

        if len(files) > 1:
            alt_formats = [f[2] for f in files[1:]]
            note = f"Multiple formats available: {', '.join(alt_formats)}"
            entry["anomalies"].append(note)
            log.debug("  Month %d: selected %s (alternatives: %s)", month_num, name, alt_formats)

        entries.append(entry)
        log.info("  Month %02d: %s  size=%s", month_num, name, size_bytes)

    if not entries:
        anomalies.append(f"No monthly files parsed from catalog {catalog_id}")

    return entries, anomalies


# ---------------------------------------------------------------------------
# Epoch inference
# ---------------------------------------------------------------------------


def infer_epoch(year: int, _month: int) -> str:
    if year < 2021:
        return "geih_2006_2020"
    return "geih_2021_present"


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------


def detect_gaps(entries: list[dict], min_year: int, max_year: int) -> list[dict]:
    """Return list of {year, month, reason} for expected but missing months."""
    present: set[tuple[int, int]] = {(e["year"], e["month"]) for e in entries}
    gaps = []
    today = datetime.now(timezone.utc)
    current_year, current_month = today.year, today.month

    for year in range(min_year, max_year + 1):
        start_month = 8 if year == 2006 else 1  # GEIH started Aug 2006
        for month in range(start_month, 13):
            # Don't flag future months as gaps
            if (year, month) > (current_year, current_month):
                break
            if (year, month) not in present:
                reason = _gap_reason(year, month)
                gaps.append({"year": year, "month": month, "reason": reason})

    return gaps


def _gap_reason(year: int, month: int) -> str:
    """Best-effort explanation for known gaps."""
    today = datetime.now(timezone.utc)
    # DANE publishes with ~2 month lag; recent months are not yet available
    months_since = (today.year - year) * 12 + (today.month - month)
    if 0 <= months_since <= 2:
        return "Not yet published by DANE (publication lag is typically 1-2 months)"
    if year == 2020 and month in (4, 5):
        return "DANE suspended in-person operations due to COVID-19 pandemic"
    if year == 2006:
        return "GEIH 2006 (Aug-Dec) microdata not published in MERCLAB catalog"
    return "Month not found in DANE MERCLAB catalog (scraping may need retry)"


# ---------------------------------------------------------------------------
# Main scraper
# ---------------------------------------------------------------------------


def scrape_catalog(
    output_path: Path,
    dry_run: bool = False,
    save_interval: int = 5,
) -> dict:
    """Discover and scrape all main annual GEIH catalogs."""
    session = make_session()
    all_entries: list[dict] = []
    catalog_errors: list[dict] = []
    catalog_anomalies: list[dict] = []
    catalogs_visited = 0

    # Step 1: Discover annual GEIH catalogs from MERCLAB collection
    log.info("=== Step 1: Discovering annual GEIH catalogs from MERCLAB collection ===")
    annual_catalogs = discover_annual_geih_catalogs(session)

    if not annual_catalogs:
        log.error("No annual GEIH catalogs found. Aborting.")
        sys.exit(1)

    log.info(
        "Found %d annual GEIH catalogs: years %d-%d",
        len(annual_catalogs),
        annual_catalogs[0][1],
        annual_catalogs[-1][1],
    )

    # Step 2: For each annual catalog, scrape monthly files
    log.info("=== Step 2: Scraping monthly files from each annual catalog ===")
    for i, (catalog_id, year, title) in enumerate(annual_catalogs):
        log.info("[%d/%d] Catalog %d: %s", i + 1, len(annual_catalogs), catalog_id, title)

        url = MICRODATA_URL.format(cid=catalog_id)
        html = fetch_with_retry(url, session, f"catalog {catalog_id} /get_microdata")
        catalogs_visited += 1

        if html is None:
            msg = f"Failed to fetch /get_microdata for catalog {catalog_id} (year {year})"
            log.error(msg)
            catalog_errors.append(
                {"catalog_id": catalog_id, "year": year, "reason": "fetch_failed"}
            )
            continue

        entries, anomalies = parse_microdata_files(html, catalog_id, year)
        all_entries.extend(entries)

        if anomalies:
            for anomaly in anomalies:
                log.warning("Catalog %d: %s", catalog_id, anomaly)
                catalog_anomalies.append({"catalog_id": catalog_id, "year": year, "note": anomaly})

        month_count = len(entries)
        if month_count < 12:
            note = f"Only {month_count}/12 months found"
            log.info("  Warning: %s", note)
            catalog_anomalies.append({"catalog_id": catalog_id, "year": year, "note": note})

        # Save partial results periodically
        if not dry_run and (i + 1) % save_interval == 0:
            _write_partial(
                output_path, all_entries, catalogs_visited, catalog_errors, annual_catalogs
            )
            log.info("Partial save after %d catalogs.", i + 1)

    # Step 3: Sort entries and detect gaps
    all_entries.sort(key=lambda e: (e["year"], e["month"]))

    min_year = annual_catalogs[0][1] if annual_catalogs else 2007
    max_year = annual_catalogs[-1][1] if annual_catalogs else 2026
    gaps = detect_gaps(all_entries, min_year, max_year)
    if gaps:
        log.info("Detected %d gaps in the catalog", len(gaps))

    # Build final output
    result = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "scraped_by": "scripts/scrape_dane_catalog.py",
        "schema_version": "0.1.0",
        "entries": all_entries,
        "gaps": gaps,
        "scrape_log": {
            "catalogs_visited": catalogs_visited,
            "geih_matches": len(all_entries),
            "errors": catalog_errors,
            "anomalies": catalog_anomalies,
            "annual_catalogs_found": len(annual_catalogs),
            "annual_catalogs": [
                {"id": cid, "year": year, "title": title} for cid, year, title in annual_catalogs
            ],
        },
    }

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        log.info("Written to %s", output_path)

    return result


def _write_partial(
    output_path: Path,
    entries: list[dict],
    visited: int,
    errors: list[dict],
    _annual_catalogs: list[tuple[int, int, str]],
) -> None:
    partial = {
        "scraped_at": datetime.now(timezone.utc).isoformat() + " (partial)",
        "scraped_by": "scripts/scrape_dane_catalog.py",
        "schema_version": "0.1.0",
        "entries": sorted(entries, key=lambda e: (e["year"], e["month"])),
        "gaps": [],
        "scrape_log": {
            "catalogs_visited": visited,
            "geih_matches": len(entries),
            "errors": errors,
            "partial": True,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(partial, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape DANE GEIH annual catalogs and produce _scraped_catalog.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to write _scraped_catalog.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape but do not write output file",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("pulso DANE catalog scraper starting")
    log.info("Output: %s", args.output)
    if args.dry_run:
        log.info("DRY RUN — no file will be written")

    result = scrape_catalog(args.output, dry_run=args.dry_run)
    scrape_log = result["scrape_log"]

    print("\nScrape complete.")
    print(f"  Annual catalogs found  : {scrape_log['annual_catalogs_found']}")
    print(f"  Monthly entries found  : {scrape_log['geih_matches']}")
    print(f"  Catalogs visited       : {scrape_log['catalogs_visited']}")
    print(f"  Errors                 : {len(scrape_log['errors'])}")
    print(f"  Gaps detected          : {len(result['gaps'])}")
    if not args.dry_run:
        print(f"  Output written to      : {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
