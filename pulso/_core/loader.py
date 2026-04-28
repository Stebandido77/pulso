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

    Carga microdatos del GEIH para el módulo indicado.

    Args:
        year: Single year, range, or iterable of years.
        month: Single month (1-12), list of months, or None for all 12.
        module: Canonical module name (e.g., 'ocupados').
        area: 'cabecera' (urban), 'resto' (rural), or 'total'.
        harmonize: If True, apply variable_map.json transforms (Phase 2+).
        columns: Optional column names to keep (reduces memory).
        cache: If True, use the local cache.
        show_progress: If True, display a tqdm progress bar.
        allow_unvalidated: If True, allow entries marked validated=false.

    Returns:
        DataFrame with one row per observation. Multiple periods add 'year'
        and 'month' columns.

    Raises:
        DataNotAvailableError: Requested period not in registry.
        ModuleNotAvailableError: Module not present for the period's epoch.
        DownloadError: Network or checksum failure.
        ParseError: ZIP contents not parseable.
        NotImplementedError: If harmonize=True (Phase 2).
    """
    import pandas as pd

    from pulso._config.epochs import epoch_for_month
    from pulso._config.registry import _load_sources
    from pulso._core.downloader import download_zip
    from pulso._core.parser import parse_module
    from pulso._utils.validation import validate_area, validate_module, validate_year_month

    if harmonize:
        raise NotImplementedError("Phase 2")

    validated_area = validate_area(area)
    periods = validate_year_month(year, month)

    sources = _load_sources()
    all_modules = list(sources["modules"].keys())
    validate_module(module, all_modules)

    frames: list[pd.DataFrame] = []
    multi = len(periods) > 1

    for y, m in periods:
        epoch = epoch_for_month(y, m)
        key = f"{y}-{m:02d}"

        # Validate the module is available for this specific (year, month) record.
        record = sources["data"].get(key)
        if record is None:
            from pulso._utils.exceptions import DataNotAvailableError

            raise DataNotAvailableError(
                y,
                m,
                hint="Use pulso.list_available() to see which months are in the registry.",
            )

        if module not in record["modules"]:
            from pulso._utils.exceptions import ModuleNotAvailableError

            raise ModuleNotAvailableError(
                f"Module {module!r} is not available for {key}. "
                f"Available: {list(record['modules'].keys())}."
            )

        zip_path = download_zip(y, m, cache=cache, show_progress=show_progress, allow_unvalidated=allow_unvalidated)
        df = parse_module(zip_path, y, m, module, validated_area, epoch, columns)

        if multi:
            df["year"] = y
            df["month"] = m

        frames.append(df)

    if not frames:
        return pd.DataFrame()

    if len(frames) == 1:
        return frames[0]

    return pd.concat(frames, ignore_index=True)


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

    Carga múltiples módulos y los combina por las claves de la época.

    Raises:
        NotImplementedError: Phase 2.
    """
    raise NotImplementedError("Phase 2")
