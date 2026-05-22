"""Helpers for real-data validation tests."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from urllib.request import Request, urlopen

CACHE_DIR = Path.home() / ".cache" / "pulso" / "raw_zips"
SOURCES_PATH = Path(__file__).parent.parent.parent / "pulso" / "data" / "sources.json"

# Pulso downloader cache root (for 2024-06 which is already cached there)
_PULSO_CACHE_ROOT = Path.home() / "AppData" / "Local" / "pulso" / "pulso" / "Cache"


def _find_in_pulso_cache(year: int, month: int) -> Path | None:
    """Return the path to a ZIP already cached by the pulso downloader, or None."""
    slot = _PULSO_CACHE_ROOT / "raw" / str(year) / f"{month:02d}"
    if slot.exists():
        zips = list(slot.glob("*.zip"))
        if zips:
            return zips[0]
    return None


def get_cached_zip(year: int, month: int) -> Path:
    """Return path to cached ZIP for (year, month). Downloads if missing.

    Checks ~/.cache/pulso/raw_zips/ first, then the pulso downloader cache,
    then downloads from the sources.json download_url.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    key = f"{year}-{month:02d}"
    zip_path = CACHE_DIR / f"{key}.zip"

    if zip_path.exists():
        return zip_path

    # Re-use from the pulso downloader cache if already present (avoids re-download)
    existing = _find_in_pulso_cache(year, month)
    if existing is not None:
        shutil.copy2(existing, zip_path)
        print(f"Copied from pulso cache: {existing} -> {zip_path}")
        return zip_path

    # Download fresh
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    entry = sources["data"][key]
    url: str = entry["download_url"]

    print(f"Downloading {url}")
    print(f"  -> {zip_path} (expected ~{entry.get('size_bytes', 0) // 1_000_000} MB)")

    req = Request(url, headers={"User-Agent": "pulso-real-data-tests/0.3.4"})
    with urlopen(req, timeout=180) as resp, zip_path.open("wb") as f:
        f.write(resp.read())

    print(f"  Downloaded: {zip_path.stat().st_size:,} bytes")
    return zip_path


def compute_sha256(path: Path) -> str:
    """Compute SHA256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
