"""Downloader: fetches ZIPs from DANE, manages local cache, verifies checksums."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def download_zip(
    year: int,
    month: int,
    cache: bool = True,
    show_progress: bool = True,
) -> Path:
    """Download (or retrieve from cache) the ZIP for a given (year, month).

    Args:
        year: Year (e.g., 2024).
        month: Month (1-12).
        cache: If True, cache locally and reuse if present and checksum matches.
        show_progress: If True, show a tqdm progress bar.

    Returns:
        Path to the local ZIP file.

    Raises:
        DataNotAvailableError: Period not in registry.
        DownloadError: Network failure or checksum mismatch.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def verify_checksum(path: Path, expected_sha256: str) -> bool:
    """Check that `path`'s SHA-256 matches `expected_sha256`."""
    raise NotImplementedError("Phase 1: Claude Code")
