"""Cache management for downloaded and processed data.

Layout:
    ~/.pulso/
    ├── raw/{year}/{month:02d}/{checksum}.zip       # original DANE ZIP
    ├── parsed/{year}/{month:02d}/{module}.parquet  # post-parser, pre-harmonizer
    └── harmonized/{year}/{month:02d}/{module}.parquet
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

CacheLevel = Literal["raw", "parsed", "harmonized", "all"]


def cache_path() -> Path:
    """Return the root cache directory.

    Defaults to `~/.pulso/` but respects `PULSO_CACHE_DIR` environment variable
    and platform conventions via platformdirs.

    Returns:
        Absolute path to the cache root.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def cache_info() -> dict[str, object]:
    """Return information about the current cache state.

    Returns:
        Dict with keys: 'path', 'total_size_bytes', 'n_files',
        'by_level' (raw/parsed/harmonized).
    """
    raise NotImplementedError("Phase 1: Claude Code")


def cache_clear(level: CacheLevel = "all") -> None:
    """Remove cached files at the given level.

    Args:
        level: Which cache layer(s) to clear. 'all' removes everything.
    """
    raise NotImplementedError("Phase 1: Claude Code")
