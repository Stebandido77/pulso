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
        harmonize: If True, apply variable_map.json transforms.
        columns: Optional column names to keep (reduces memory).
        cache: If True, use the local cache.
        show_progress: If True, display a tqdm progress bar.
        allow_unvalidated: If True, allow entries marked validated=false.

    Returns:
        DataFrame with one row per observation. Multiple periods add 'year'
        and 'month' columns. If harmonize=True, canonical columns are added
        alongside the original raw DANE columns (keep_raw=True by default).

    Raises:
        DataNotAvailableError: Requested period not in registry.
        ModuleNotAvailableError: Module not present for the period's epoch.
        DownloadError: Network or checksum failure.
        ParseError: ZIP contents not parseable.
        HarmonizationError: A variable_map transform fails on the data.
    """
    import pandas as pd

    from pulso._config.epochs import epoch_for_month
    from pulso._config.registry import _load_sources
    from pulso._core.downloader import download_zip
    from pulso._core.parser import parse_module
    from pulso._utils.validation import validate_area, validate_module, validate_year_month

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

        zip_path = download_zip(
            y, m, cache=cache, show_progress=show_progress, allow_unvalidated=allow_unvalidated
        )
        df = parse_module(zip_path, y, m, module, validated_area, epoch, columns)

        if harmonize:
            from pulso._core.harmonizer import harmonize_dataframe

            df = harmonize_dataframe(df, epoch)

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
    year: int,
    month: int | None = None,
    modules: list[str] | None = None,
    area: Area = "total",
    harmonize: bool = True,
    variables: list[str] | None = None,
    cache: bool = True,
    show_progress: bool = True,
    allow_unvalidated: bool = False,
) -> pd.DataFrame:
    """Load multiple modules, merge on epoch keys, and optionally harmonize.

    Carga múltiples módulos, los combina por las claves de la época, y aplica
    armonización opcional.

    Args:
        year: Single year (int).
        month: Single month (1-12) or None for all months in the year.
        modules: List of canonical module names. If None, all modules
            registered for the (year, month) are loaded.
        area: 'cabecera', 'resto', or 'total'.
        harmonize: If True, apply variable_map.json transforms after merging.
        variables: Subset of canonical variable names to harmonize. Applies
            only when harmonize=True.
        cache: If True, use the local cache.
        show_progress: If True, display a tqdm progress bar.
        allow_unvalidated: If True, allow entries marked validated=false.

    Returns:
        Merged (and optionally harmonized) DataFrame at persona level.

    Raises:
        DataNotAvailableError: Requested period not in registry.
        MergeError: Modules cannot be merged (missing keys, etc.).
        HarmonizationError: A variable_map transform fails on the data.
    """
    import pandas as pd

    from pulso._config.epochs import epoch_for_month
    from pulso._config.registry import _load_sources
    from pulso._core.harmonizer import harmonize_dataframe
    from pulso._core.merger import merge_modules
    from pulso._utils.validation import validate_year_month

    periods = validate_year_month(year, month)
    sources = _load_sources()

    all_frames: list[pd.DataFrame] = []
    multi = len(periods) > 1

    for y, mo in periods:
        epoch = epoch_for_month(y, mo)
        key = f"{y}-{mo:02d}"

        record = sources["data"].get(key)
        if record is None:
            from pulso._utils.exceptions import DataNotAvailableError

            raise DataNotAvailableError(
                y,
                mo,
                hint="Use pulso.list_available() to see which months are in the registry.",
            )

        available_modules = modules if modules is not None else list(record["modules"].keys())

        module_dfs = {
            mod: load(
                year=y,
                month=mo,
                module=mod,
                area=area,
                harmonize=False,
                cache=cache,
                show_progress=show_progress,
                allow_unvalidated=allow_unvalidated,
            )
            for mod in available_modules
            if mod in record["modules"]
        }

        merged = merge_modules(module_dfs, epoch, level="persona", how="outer")

        if harmonize:
            merged = harmonize_dataframe(merged, epoch, variables=variables)

        if multi:
            merged["year"] = y
            merged["month"] = mo

        all_frames.append(merged)

    if not all_frames:
        return pd.DataFrame()

    if len(all_frames) == 1:
        return all_frames[0]

    return pd.concat(all_frames, ignore_index=True)
