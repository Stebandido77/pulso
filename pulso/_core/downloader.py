"""Downloader: fetches ZIPs from DANE, manages local cache, verifies checksums."""

from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from pathlib import Path

from pulso._config.registry import _load_sources
from pulso._utils.cache import cache_path
from pulso._utils.exceptions import DataNotAvailableError, DataNotValidatedError, DownloadError

logger = logging.getLogger(__name__)


def verify_checksum(path: Path, expected_sha256: str) -> bool:
    """Compute the SHA-256 of `path` and compare to `expected_sha256`.

    Verifica que el archivo coincide con el checksum esperado.

    Args:
        path: Local file to hash.
        expected_sha256: Lowercase hex digest to compare against.

    Returns:
        True if the digest matches, False otherwise.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest() == expected_sha256.lower()


def download_zip(
    year: int,
    month: int,
    cache: bool = True,
    show_progress: bool = True,
    allow_unvalidated: bool = False,
) -> Path:
    """Download (or retrieve from cache) the ZIP for a given (year, month).

    Descarga (o recupera del caché) el archivo ZIP para el período dado.

    Args:
        year: Year (e.g., 2024).
        month: Month (1-12).
        cache: If True, cache locally and reuse if checksum matches.
        show_progress: If True, show a tqdm progress bar.
        allow_unvalidated: If True, allow loading unvalidated registry entries.

    Returns:
        Path to the local ZIP file.

    Raises:
        DataNotAvailableError: Period not in registry.
        DataNotValidatedError: Entry exists but validated=false.
        DownloadError: Network failure or checksum mismatch.
    """
    sources = _load_sources()
    key = f"{year}-{month:02d}"

    if key not in sources["data"]:
        raise DataNotAvailableError(
            year,
            month,
            hint="Use pulso.list_available() to see which months are in the registry.",
        )

    record = sources["data"][key]

    if not record["validated"] and not allow_unvalidated:
        raise DataNotValidatedError(
            f"Entry {key!r} has validated=false. Pass allow_unvalidated=True to load it anyway."
        )

    checksum: str = record["checksum_sha256"]
    short = checksum[:16]
    dest = cache_path() / "raw" / str(year) / f"{month:02d}" / f"{short}.zip"

    if cache and dest.exists():
        if verify_checksum(dest, checksum):
            return dest
        logger.warning("Checksum mismatch on cached file %s — re-downloading.", dest)
        dest.unlink()

    url: str = record["download_url"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")

    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0)) or None
        if show_progress:
            from tqdm import tqdm

            with tmp.open("wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=key) as bar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bar.update(len(chunk))
        else:
            with tmp.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.RequestException as exc:
        if tmp.exists():
            tmp.unlink()
        raise DownloadError(f"Download failed for {key}: {exc}") from exc

    tmp.replace(dest)

    if not verify_checksum(dest, checksum):
        dest.unlink()
        raise DownloadError(f"Checksum mismatch after download for {key}.")

    return dest
