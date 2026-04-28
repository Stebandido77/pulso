"""Loader: the top-level orchestrator.

Coordinates: registry lookup → download → parse → harmonize → (merge).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import pandas as pd

Area = Literal["cabecera", "resto", "total"]


def load(
    year: int | range,
    month: int | list[int] | None = None,
    module: str = "caracteristicas_generales",
    area: Area = "total",
    harmonize: bool = True,
    columns: list[str] | None = None,
    cache: bool = True,
    show_progress: bool = True,
    allow_unvalidated: bool = False,
) -> pd.DataFrame:
    """Load GEIH microdata for a given module.

    Args:
        year: Single year, range, or iterable of years.
        month: Single month (1-12), list of months, or None for all 12.
        module: Canonical module name (e.g., 'ocupados').
        area: 'cabecera' (urban), 'resto' (rural), or 'total' (concatenated).
        harmonize: If True, apply variable_map.json to standardize column names
            and codings across epochs.
        columns: Optional list of canonical column names to keep. Filters at
            parse time, reducing memory.
        cache: If True, use the local cache in ~/.pulso/.
        show_progress: If True, display a tqdm progress bar.
        allow_unvalidated: If True, allow loading entries marked as
            `validated=false` in sources.json. Default False.

    Returns:
        A pandas DataFrame with one row per observation. If multiple
        (year, month) requested, includes columns 'year' and 'month'.

    Raises:
        DataNotAvailableError: Requested period not in registry.
        ModuleNotAvailableError: Module not present for the period's epoch.
        DownloadError: Network or checksum failure.
        ParseError: ZIP contents not parseable.

    Examples:
        >>> df = pulso.load(2024, 6, "ocupados")
        >>> df = pulso.load(year=range(2018, 2025), month=6, module="ocupados")
        >>> df = pulso.load(2024, [3, 6, 9, 12], "caracteristicas_generales")
    """
    raise NotImplementedError("Phase 1: Claude Code")


def load_merged(
    year: int | range,
    month: int | list[int] | None,
    modules: list[str],
    area: Area = "total",
    harmonize: bool = True,
    columns: dict[str, list[str]] | None = None,
    cache: bool = True,
    show_progress: bool = True,
    allow_unvalidated: bool = False,
) -> pd.DataFrame:
    """Load multiple modules and merge them on epoch-appropriate keys.

    Args:
        year: Same as `load`.
        month: Same as `load`.
        modules: List of canonical module names to merge.
        area: Same as `load`.
        harmonize: If True, harmonize before merging (recommended).
        columns: Optional dict {module: [columns]} to filter per module.
        cache: Same as `load`.
        show_progress: Same as `load`.
        allow_unvalidated: Same as `load`.

    Returns:
        A merged DataFrame. Person-level modules merge on persona keys;
        if a household-level module is included, it's broadcast to persons.

    Raises:
        MergeError: If modules cannot be merged (e.g., missing keys).
    """
    raise NotImplementedError("Phase 2: Claude Code")
