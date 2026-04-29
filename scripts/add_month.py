"""CLI to add a single month manually to sources.json.

Use this when the scraper hasn't picked up a month yet, or when you want to
add an entry while developing.

Usage:
    python scripts/add_month.py --year 2026 --month 4 --url https://...

The script:
  1. Downloads the ZIP to a temp file
  2. Computes SHA-256
  3. Lists internal files (Cabecera/ and Resto/ sub-trees)
  4. Proposes module path mappings
  5. Prints a JSON snippet to stdout (copy into sources.json manually)

After adding, run a smoke test:
    pulso.load(year, month, "ocupados", allow_unvalidated=True)
Then flip `validated: true` and `validated_by: "manual"` in sources.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    import requests
    from tqdm import tqdm

    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    total = int(r.headers.get("content-length", 0)) or None
    with dest.open("wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc="download") as bar:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))


def _infer_epoch(year: int, epoch_override: str | None) -> str:
    if epoch_override:
        return epoch_override
    return "geih_2021_present" if year >= 2021 else "geih_2006_2020"


def _propose_modules(names: list[str]) -> dict[str, dict[str, str | None]]:
    """Match ZIP internal paths to canonical module names heuristically."""
    KEYWORDS: dict[str, str] = {
        "ocupados": "ocupados",
        "desocupados": "desocupados",
        "inactivos": "inactivos",
        "caracteristicas": "caracteristicas_generales",
        "vivienda": "vivienda_hogares",
        "otros": "otros_ingresos",
    }
    result: dict[str, dict[str, str | None]] = {}
    for path in names:
        lower = path.lower()
        for kw, canonical in KEYWORDS.items():
            if kw in lower:
                if canonical not in result:
                    result[canonical] = {"cabecera": None, "resto": None}
                if "cabecera" in lower:
                    result[canonical]["cabecera"] = path
                elif "resto" in lower:
                    result[canonical]["resto"] = path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True, choices=range(1, 13), metavar="MONTH")
    parser.add_argument("--url", type=str, required=True, help="Direct URL to the ZIP.")
    parser.add_argument("--landing-page", type=str, default=None)
    parser.add_argument(
        "--epoch", type=str, default=None, help="Epoch key. Inferred from year if omitted."
    )
    parser.add_argument(
        "--auto", action="store_true", help="Don't prompt; accept inferred module mappings."
    )
    args = parser.parse_args()

    year: int = args.year
    month: int = args.month
    url: str = args.url
    epoch = _infer_epoch(year, args.epoch)

    print(f"Downloading {year}-{month:02d} from {url} …", file=sys.stderr)

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "download.zip"
        try:
            _download(url, dest)
        except Exception as exc:
            print(f"ERROR: download failed: {exc}", file=sys.stderr)
            return 1

        sha = _sha256(dest)
        size = dest.stat().st_size
        print(f"SHA-256 : {sha}", file=sys.stderr)
        print(f"Size    : {size:,} bytes", file=sys.stderr)

        with zipfile.ZipFile(dest) as zf:
            all_names = zf.namelist()

        csv_names = [n for n in all_names if n.lower().endswith((".csv", ".sav", ".dta"))]
        print(f"\nInternal files ({len(csv_names)} data files):", file=sys.stderr)
        for n in csv_names:
            print(f"  {n}", file=sys.stderr)

        modules = _propose_modules(csv_names)

    entry = {
        "epoch": epoch,
        "download_url": url,
        "landing_page": args.landing_page,
        "checksum_sha256": sha,
        "size_bytes": size,
        "scraped_at": None,
        "validated": False,
        "validated_by": None,
        "validated_at": None,
        "modules": modules,
        "notes": None,
    }

    key = f"{year}-{month:02d}"
    print('\n# Paste this into sources.json under "data":\n', file=sys.stderr)
    print(json.dumps({key: entry}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
