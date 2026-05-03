"""Cache management for downloaded and processed data.

Layout:
    <cache_root>/
    ├── raw/{year}/{month:02d}/{checksum_short}.zip
    ├── parsed/{year}/{month:02d}/{module}.parquet
    └── harmonized/{year}/{month:02d}/{module}.parquet
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Literal

import platformdirs

CacheLevel = Literal["raw", "parsed", "harmonized", "all"]

_LEVELS: tuple[str, ...] = ("raw", "parsed", "harmonized")


def cache_path() -> Path:
    """Return the root cache directory, creating it if needed.

    Retorna el directorio raíz de caché, creándolo si no existe.

    Respects the ``PULSO_CACHE_DIR`` environment variable. Falls back to
    the platform default via ``platformdirs.user_cache_dir("pulso")``.

    Returns:
        Absolute path to the cache root.
    """
    env_override = os.environ.get("PULSO_CACHE_DIR")
    root = Path(env_override) if env_override else Path(platformdirs.user_cache_dir("pulso"))
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def cache_info() -> dict[str, object]:
    """Return a summary of the current cache state.

    Retorna un resumen del estado actual del caché.

    Returns:
        Dict with keys: 'path', 'total_size_bytes', 'n_files', 'by_level'.
    """
    root = cache_path()
    total_size = 0
    n_files = 0
    by_level: dict[str, dict[str, int]] = {lvl: {"size_bytes": 0, "n_files": 0} for lvl in _LEVELS}
    for lvl in _LEVELS:
        lvl_dir = root / lvl
        if lvl_dir.exists():
            for f in lvl_dir.rglob("*"):
                if f.is_file():
                    size = f.stat().st_size
                    total_size += size
                    n_files += 1
                    by_level[lvl]["size_bytes"] += size
                    by_level[lvl]["n_files"] += 1
    return {
        "path": str(root),
        "total_size_bytes": total_size,
        "n_files": n_files,
        "by_level": by_level,
    }


def cache_clear(level: CacheLevel = "all") -> None:
    """Remove cached files at the given level.

    Elimina archivos en caché en el nivel especificado.

    Args:
        level: Which layer to clear. ``'all'`` removes every cached file.
            Must be one of ``'raw'``, ``'parsed'``, ``'harmonized'``,
            ``'all'``.

    Raises:
        CacheError: ``level`` is not a recognised cache level. Previously
            this silently no-op'd when an unknown string was passed.
    """
    from pulso._utils.exceptions import CacheError

    valid = (*_LEVELS, "all")
    if level not in valid:
        raise CacheError(f"Unknown cache level {level!r}. Valid choices: {list(valid)}.")

    root = cache_path()
    if level == "all":
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
    else:
        target = root / level
        if target.exists():
            shutil.rmtree(target)
