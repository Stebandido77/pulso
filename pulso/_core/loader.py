"""Loader: the top-level orchestrator.

Coordinates: registry lookup → download → parse → harmonize → (merge).
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    import pandas as pd

Area = Literal["cabecera", "resto", "total"]

logger = logging.getLogger(__name__)


# Maximum number of unvalidated keys to enumerate verbatim in the
# aggregated warning before truncating with "... and N more".
_AGG_WARNING_EXAMPLE_LIMIT: int = 10


def _resolve_strict(
    strict: bool | None,
    allow_unvalidated: bool | None,
    *,
    stacklevel: int = 3,
) -> bool:
    """Resolve the new ``strict`` flag against the deprecated ``allow_unvalidated``.

    Compat rules:
    - If both are passed, ``ValueError``.
    - If only ``allow_unvalidated`` is passed, emit ``DeprecationWarning`` and
      translate to ``strict = not allow_unvalidated``.
    - If neither is passed, default is ``strict=False`` (permissive — load
      unvalidated entries with a warning instead of raising).
    """
    if allow_unvalidated is not None:
        if strict is not None:
            raise ValueError(
                "Cannot pass both `strict` and `allow_unvalidated`. "
                "`allow_unvalidated` is deprecated; use only `strict`."
            )
        warnings.warn(
            "Parameter `allow_unvalidated` is deprecated and will be removed "
            "in pulso 2.0.0. Use `strict` instead. "
            "Mapping: allow_unvalidated=True → strict=False, "
            "allow_unvalidated=False → strict=True.",
            DeprecationWarning,
            stacklevel=stacklevel,
        )
        return not allow_unvalidated
    if strict is None:
        return False
    return strict


def _emit_unvalidated_warning(
    unvalidated_keys: list[str],
    total_loaded: int,
    total_requested: int,
    *,
    stacklevel: int = 3,
) -> None:
    """Emit ONE aggregated UserWarning for unvalidated periods loaded.

    Called once at the end of multi-period (or single-period) load when
    ``strict=False`` and at least one period was loaded without validation.
    """
    if not unvalidated_keys:
        return
    examples = unvalidated_keys[:_AGG_WARNING_EXAMPLE_LIMIT]
    extra = len(unvalidated_keys) - len(examples)
    suffix = f", ... and {extra} more" if extra > 0 else ""
    msg = (
        f"Loaded {total_loaded} of {total_requested} months from registry. "
        f"{len(unvalidated_keys)} months had not been checksum-validated "
        f"(e.g., {', '.join(examples)}{suffix}). "
        f"Pass strict=True to enforce validation, or call "
        f"pulso.list_validated_range() to see which months ARE validated."
    )
    warnings.warn(msg, UserWarning, stacklevel=stacklevel)


def _required_modules_for_variables(
    variable_map: dict[str, Any],
    sources: dict[str, Any],
    epoch_key: str,
    requested_variables: list[str] | None = None,
) -> set[str]:
    """Return modules required by canonical variables for this epoch.

    Only includes modules listed in sources["modules"] that have epoch_key in
    their available_in list. Variables without a mapping for epoch_key are
    silently skipped.
    """
    epoch_modules: set[str] = {
        name
        for name, meta in sources["modules"].items()
        if epoch_key in meta.get("available_in", [])
    }

    required: set[str] = set()
    variables_dict: dict[str, Any] = variable_map["variables"]
    target_vars = (
        requested_variables if requested_variables is not None else list(variables_dict.keys())
    )

    for var_name in target_vars:
        entry = variables_dict.get(var_name)
        if not entry:
            continue
        if epoch_key not in entry.get("mappings", {}):
            continue
        module = entry.get("module")
        if module and module in epoch_modules:
            required.add(module)

    return required


def load(
    year: int | range,
    month: int | list[int] | None = None,
    module: str = "caracteristicas_generales",
    area: Area = "total",
    harmonize: bool = True,
    columns: list[str] | None = None,
    cache: bool = True,
    show_progress: bool = True,
    strict: bool | None = None,
    allow_unvalidated: bool | None = None,
    _emit_unvalidated_warning_at_end: bool = True,
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
        strict: If True, refuse to load any period whose registry entry has
            ``validated=false`` and raise ``DataNotValidatedError``. If False
            (default), load such entries and emit a single aggregated
            ``UserWarning`` listing the unvalidated periods touched.
        allow_unvalidated: **Deprecated.** Use ``strict`` instead. The mapping
            is ``allow_unvalidated=True → strict=False`` and
            ``allow_unvalidated=False → strict=True``. Will be removed in v2.0.0.

    Returns:
        DataFrame with one row per observation. Multiple periods add 'year'
        and 'month' columns. If harmonize=True, canonical columns are added
        alongside the original raw DANE columns (keep_raw=True by default).

    Raises:
        DataNotAvailableError: Requested period not in registry.
        ModuleNotAvailableError: Module not present for the period's epoch.
        DataNotValidatedError: Entry has validated=false and strict=True.
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

    strict_flag = _resolve_strict(strict, allow_unvalidated)

    validated_area = validate_area(area)
    periods = validate_year_month(year, month)

    sources = _load_sources()
    all_modules = list(sources["modules"].keys())
    validate_module(module, all_modules)

    frames: list[pd.DataFrame] = []
    unvalidated_keys: list[str] = []
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

        if not record["validated"]:
            unvalidated_keys.append(key)

        zip_path = download_zip(
            y,
            m,
            cache=cache,
            show_progress=show_progress,
            allow_unvalidated=not strict_flag,
        )
        df = parse_module(zip_path, y, m, module, validated_area, epoch, columns)

        if harmonize:
            from pulso._core.harmonizer import harmonize_dataframe

            df = harmonize_dataframe(df, epoch)

        if multi:
            df["year"] = y
            df["month"] = m

        frames.append(df)

    if not strict_flag and _emit_unvalidated_warning_at_end:
        _emit_unvalidated_warning(
            unvalidated_keys,
            total_loaded=len(frames),
            total_requested=len(periods),
        )

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
    strict: bool | None = None,
    allow_unvalidated: bool | None = None,
    apply_smoothing: bool = False,
) -> pd.DataFrame:
    """Load multiple modules, merge on epoch keys, and optionally harmonize.

    Carga múltiples módulos, los combina por las claves de la época, y aplica
    armonización opcional.

    Args:
        year: Single year (int).
        month: Single month (1-12) or None for all months in the year.
        modules: List of canonical module names. If None, all modules
            registered for the (year, month) are loaded (auto-discovery —
            modules absent from the period are silently skipped). When
            provided explicitly, every name must be available for the period
            or ``ModuleNotAvailableError`` is raised.
        area: 'cabecera', 'resto', or 'total'.
        harmonize: If True, apply variable_map.json transforms after merging.
        variables: Subset of canonical variable names to harmonize. Applies
            only when harmonize=True.
        cache: If True, use the local cache.
        show_progress: If True, display a tqdm progress bar.
        strict: If True, refuse to load periods with ``validated=false`` and
            raise ``DataNotValidatedError``. If False (default), load such
            periods and emit a single aggregated ``UserWarning`` afterwards.
        allow_unvalidated: **Deprecated.** Use ``strict`` instead. Mapping is
            ``allow_unvalidated=True → strict=False``. Will be removed in v2.0.0.
        apply_smoothing: If True and year is in 2010-2019, replace the entire
            month dataset with the Empalme equivalent. For year=2020 warns
            and falls back; years outside 2010-2020 are silently unchanged.

    Returns:
        Merged (and optionally harmonized) DataFrame at persona level.

    Raises:
        DataNotAvailableError: Requested period not in registry.
        DataNotValidatedError: Period has validated=false and strict=True.
        ModuleNotAvailableError: Module explicitly requested but absent for the period.
        MergeError: Modules cannot be merged (missing keys, etc.).
        HarmonizationError: A variable_map transform fails on the data.
    """
    import pandas as pd

    from pulso._config.epochs import epoch_for_month
    from pulso._config.registry import _load_sources, _load_variable_map
    from pulso._core.harmonizer import harmonize_dataframe
    from pulso._core.merger import merge_modules
    from pulso._utils.validation import validate_module, validate_year_month

    strict_flag = _resolve_strict(strict, allow_unvalidated)

    periods = validate_year_month(year, month)
    sources = _load_sources()

    # Issue 1: validate all user-specified modules against the global registry
    # upfront so invalid names raise immediately instead of being silently skipped.
    if modules is not None:
        all_known_modules = list(sources["modules"].keys())
        for mod in modules:
            validate_module(mod, all_known_modules)

    all_frames: list[pd.DataFrame] = []
    unvalidated_keys: list[str] = []
    multi = len(periods) > 1

    for y, mo in periods:
        # ── Empalme smoothing path ────────────────────────────────────────────
        if apply_smoothing:
            from pulso._core.empalme import (
                EMPALME_DOWNLOADABLE_MAX,
                EMPALME_YEAR_MAX,
                EMPALME_YEAR_MIN,
                _load_empalme_month_merged,
            )

            if EMPALME_YEAR_MIN <= y <= EMPALME_DOWNLOADABLE_MAX:
                merged = _load_empalme_month_merged(
                    y,
                    mo,
                    area=area,
                    harmonize=harmonize,
                    variables=variables,
                    modules=modules,
                )
                if multi:
                    merged = merged.assign(year=y, month=mo)
                all_frames.append(merged)
                continue

            if y == EMPALME_YEAR_MAX:
                warnings.warn(
                    f"apply_smoothing=True requested for {y}-{mo:02d} but the Empalme ZIP "
                    f"for {y} has not been published by DANE. "
                    "Falling back to raw GEIH data.",
                    UserWarning,
                    stacklevel=2,
                )
            # For years outside 2010-2020: silently fall through to normal path.
        # ── Normal loading path ───────────────────────────────────────────────
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

        if not record["validated"]:
            unvalidated_keys.append(key)

        # Determine the working module list for this period.
        working_modules = list(record["modules"].keys()) if modules is None else list(modules)

        # M-2: when the user passed `modules=[...]` explicitly, every module
        # in the list must exist for this period. Silently dropping is the old
        # bug — surface it so callers know what they actually got.
        if modules is not None:
            from pulso._utils.exceptions import ModuleNotAvailableError

            for mod in modules:
                if mod not in record["modules"]:
                    raise ModuleNotAvailableError(
                        f"Module {mod!r} is not available for {key}. "
                        f"Available for this period: {list(record['modules'].keys())}."
                    )

        # Issue 2: when harmonize=True and the user provided an explicit module
        # list, auto-include any modules required by the canonical variables so
        # harmonization doesn't silently skip variables whose source columns are
        # absent.  Only applies when harmonize=True; user's list is sacred otherwise.
        if harmonize and modules is not None:
            variable_map = _load_variable_map()
            required = _required_modules_for_variables(variable_map, sources, epoch.key, variables)
            for m in required:
                if m not in working_modules:
                    working_modules.append(m)
                    logger.debug("Auto-including module %r required by harmonized variables.", m)

        module_dfs = {
            mod: load(
                year=y,
                month=mo,
                module=mod,
                area=area,
                harmonize=False,
                cache=cache,
                show_progress=show_progress,
                strict=strict_flag,
                _emit_unvalidated_warning_at_end=False,
            )
            for mod in working_modules
            if mod in record["modules"]
        }

        merged = merge_modules(module_dfs, epoch, level="persona", how="outer")

        if harmonize:
            merged = harmonize_dataframe(merged, epoch, variables=variables)

        if multi:
            merged["year"] = y
            merged["month"] = mo

        all_frames.append(merged)

    if not strict_flag:
        _emit_unvalidated_warning(
            unvalidated_keys,
            total_loaded=len(all_frames),
            total_requested=len(periods),
        )

    if not all_frames:
        return pd.DataFrame()

    if len(all_frames) == 1:
        return all_frames[0]

    return pd.concat(all_frames, ignore_index=True)
