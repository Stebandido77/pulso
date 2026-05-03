"""Loader: the top-level orchestrator.

Coordinates: registry lookup → download → parse → harmonize → (merge).
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

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


# Maximum number of canonical variable names to enumerate verbatim in the
# aggregated harmonization-skip warning before truncating the rest.
_AGG_SKIPPED_VARS_EXAMPLE_LIMIT: int = 5


def _drain_skipped_variables(df: pd.DataFrame) -> list[str]:
    """Pop the transient ``_skipped_variables`` list from ``df.attrs`` if present.

    Returns the (possibly empty) list and removes the key so users never see it.
    """
    return list(df.attrs.pop("_skipped_variables", []) or [])


def _emit_aggregated_skipped_variables_warning(
    skipped_per_period: list[list[str]],
    total_periods: int,
    *,
    stacklevel: int = 3,
) -> None:
    """Emit ONE aggregated ``UserWarning`` for canonical vars skipped during harmonization.

    Each inner list is the set of canonical names skipped for one period.
    The aggregated message reports the unique set across all periods and
    truncates the example list at ``_AGG_SKIPPED_VARS_EXAMPLE_LIMIT``.
    """
    unique = sorted({v for run in skipped_per_period for v in run})
    if not unique:
        return

    n_unique = len(unique)
    examples = unique[:_AGG_SKIPPED_VARS_EXAMPLE_LIMIT]
    extra = n_unique - len(examples)
    suffix = f", and {extra} more" if extra > 0 else ""

    msg = (
        f"{n_unique} canonical variable(s) skipped during harmonization across "
        f"{total_periods} period(s) (e.g., {', '.join(examples)}{suffix}). "
        "This is expected when canonical variables don't apply to the loaded "
        "module or when a transform's source columns are missing for the epoch. "
        "Use pulso.list_variables() for the full mapping."
    )
    warnings.warn(msg, UserWarning, stacklevel=stacklevel)


def _emit_unvalidated_warning(
    unvalidated_keys: list[str],
    total_loaded: int,
    total_requested: int,
    *,
    failures: list[tuple[str, str]] | None = None,
    stacklevel: int = 3,
) -> None:
    """Emit ONE aggregated UserWarning for unvalidated periods loaded.

    Called once at the end of multi-period (or single-period) load when
    ``strict=False`` and at least one period was loaded without validation
    or one or more periods failed (continue-on-failure path).
    """
    failures = failures or []
    if not unvalidated_keys and not failures:
        return

    parts: list[str] = [f"Loaded {total_loaded} of {total_requested} months from registry."]

    if unvalidated_keys:
        examples = unvalidated_keys[:_AGG_WARNING_EXAMPLE_LIMIT]
        extra = len(unvalidated_keys) - len(examples)
        suffix = f", ... and {extra} more" if extra > 0 else ""
        parts.append(
            f"{len(unvalidated_keys)} months had not been checksum-validated "
            f"(e.g., {', '.join(examples)}{suffix})."
        )

    if failures:
        fail_examples = failures[:_AGG_WARNING_EXAMPLE_LIMIT]
        fail_extra = len(failures) - len(fail_examples)
        fail_suffix = f", ... and {fail_extra} more" if fail_extra > 0 else ""
        sample = "; ".join(f"{k}: {err}" for k, err in fail_examples)
        parts.append(
            f"{len(failures)} months failed to load and were skipped (e.g., {sample}{fail_suffix})."
        )

    parts.append(
        "Pass strict=True to enforce validation and abort on the first failure, "
        "or call pulso.list_validated_range() to see which months ARE validated."
    )
    warnings.warn(" ".join(parts), UserWarning, stacklevel=stacklevel)


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
    year: int | range | Iterable[int],
    month: int | range | list[int] | tuple[int, ...] | Iterable[int] | None = None,
    module: str = "caracteristicas_generales",
    area: Area = "total",
    harmonize: bool = True,
    columns: list[str] | None = None,
    cache: bool = True,
    show_progress: bool = True,
    strict: bool | None = None,
    allow_unvalidated: bool | None = None,
    _emit_unvalidated_warning_at_end: bool = True,
    *,
    metadata: bool = False,
) -> pd.DataFrame:
    """Load GEIH microdata for a given module.

    Carga microdatos del GEIH para el módulo indicado.

    Args:
        year: Single ``int`` (e.g. ``2024``), a ``range`` (e.g.
            ``range(2007, 2025)``), or any iterable of ints (list, tuple,
            set). All inputs are normalised internally to a sorted list.
        month: Single ``int`` (1-12), a ``range`` (e.g. ``range(1, 13)``),
            any iterable of ints, or ``None`` for all 12 months. The
            cartesian product of ``year`` x ``month`` defines the periods to
            load.
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
        metadata: If True, attach composed Curator + DANE codebook metadata
            to ``df.attrs["column_metadata"]`` (and stash the source
            ``year``/``month``/``module``/``epoch`` under ``df.attrs``). Use
            :func:`pulso.describe_column` and :func:`pulso.list_columns_metadata`
            to inspect it. ``df.attrs`` survives slicing but pandas does not
            propagate it across :meth:`pandas.DataFrame.merge`,
            :meth:`pandas.DataFrame.groupby`, or :func:`pandas.concat`. Default
            False to keep ``load`` cheap when callers don't need metadata.

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
    failures: list[tuple[str, str]] = []
    skipped_per_period: list[list[str]] = []
    multi = len(periods) > 1

    from pulso._utils.exceptions import (
        DataNotAvailableError,
        DownloadError,
        HarmonizationError,
        MergeError,
        ModuleNotAvailableError,
        ParseError,
    )

    # Errors that represent per-period data/network issues (transient or
    # period-specific). These are skippable under strict=False. Usage errors
    # like ModuleNotAvailableError (user typed a module that doesn't exist
    # for the period) and ConfigError (bad json) are NOT caught — they need
    # to surface even under strict=False.
    _SKIPPABLE: tuple[type[BaseException], ...] = (
        DataNotAvailableError,
        DownloadError,
        ParseError,
        MergeError,
        HarmonizationError,
    )

    for y, m in periods:
        key = f"{y}-{m:02d}"

        try:
            epoch = epoch_for_month(y, m)

            record = sources["data"].get(key)
            if record is None:
                raise DataNotAvailableError(
                    y,
                    m,
                    hint="Use pulso.list_available() to see which months are in the registry.",
                )

            if module not in record["modules"]:
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
                period_skipped = _drain_skipped_variables(df)
                if period_skipped:
                    skipped_per_period.append(period_skipped)

            if multi:
                # Wide GEIH DataFrames (>100 cols) are already block-fragmented
                # by the harmonizer's per-variable concat. Adding `year` and
                # `month` here would trigger a pandas PerformanceWarning that
                # the project's `filterwarnings = ["error"]` config escalates
                # to a real error. Ignoring just this warning, scoped to
                # these two columns, keeps the message-as-error policy
                # everywhere else.
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
                    df = df.assign(year=y, month=m)

            frames.append(df)
        except _SKIPPABLE as exc:
            if strict_flag:
                raise
            failures.append((key, f"{type(exc).__name__}: {exc}"))
            logger.info("Skipping %s under strict=False: %s", key, exc)
            continue

    if not strict_flag and _emit_unvalidated_warning_at_end:
        _emit_unvalidated_warning(
            unvalidated_keys,
            total_loaded=len(frames),
            total_requested=len(periods),
            failures=failures,
        )
        _emit_aggregated_skipped_variables_warning(
            skipped_per_period,
            total_periods=len(periods),
        )

    if not frames:
        result = pd.DataFrame()
    elif len(frames) == 1:
        result = frames[0]
    else:
        result = pd.concat(frames, ignore_index=True)

    # Defensive: strip the transient channel before returning to the user.
    # _drain_skipped_variables removes it from each per-period frame, but
    # pd.concat does not propagate attrs and a single-period path could
    # leave it on the returned frame.
    result.attrs.pop("_skipped_variables", None)

    if metadata:
        _attach_metadata_for_load(result, periods, module)

    return result


def _attach_metadata_for_load(
    df: pd.DataFrame,
    periods: list[tuple[int, int]],
    module: str,
) -> None:
    """Attach composed metadata to ``df.attrs`` for :func:`load`.

    Anchors the metadata at the last successfully-loaded period (or the
    first requested one when ``df`` is empty). Multi-period frames span
    one epoch in the typical case; if the caller asked for periods that
    cross an epoch boundary the attached metadata corresponds to the
    anchor period — the cross-epoch story is documented in the API
    docstring rather than papered over here.
    """
    if not periods:
        return
    anchor_year, anchor_month = periods[-1]
    from pulso._config.epochs import epoch_for_month
    from pulso.metadata.composer import compose_dataframe_metadata

    df.attrs["column_metadata"] = compose_dataframe_metadata(df, anchor_year, anchor_month, module)
    df.attrs["source_year"] = anchor_year
    df.attrs["source_month"] = anchor_month
    df.attrs["source_module"] = module
    df.attrs["source_epoch"] = epoch_for_month(anchor_year, anchor_month).key


def load_merged(
    year: int | range | Iterable[int],
    month: int | range | list[int] | tuple[int, ...] | Iterable[int] | None = None,
    modules: list[str] | None = None,
    area: Area = "total",
    harmonize: bool = True,
    variables: list[str] | None = None,
    cache: bool = True,
    show_progress: bool = True,
    strict: bool | None = None,
    allow_unvalidated: bool | None = None,
    apply_smoothing: bool = False,
    *,
    metadata: bool = False,
) -> pd.DataFrame:
    """Load multiple modules, merge on epoch keys, and optionally harmonize.

    Carga múltiples módulos, los combina por las claves de la época, y aplica
    armonización opcional.

    Args:
        year: Single ``int``, a ``range``, or any iterable of ints.
        month: Single ``int`` (1-12), a ``range``, any iterable of ints,
            or ``None`` for all 12 months.
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
        metadata: If True, attach composed Curator + DANE codebook metadata
            to ``df.attrs["column_metadata"]`` and stash the merged
            ``source_modules`` list under ``df.attrs``. See :func:`load`
            for the same caveats around ``df.attrs`` propagation.

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
    failures: list[tuple[str, str]] = []
    used_modules: list[str] = []  # preserve insertion order; dedup on output
    skipped_per_period: list[list[str]] = []
    multi = len(periods) > 1

    from pulso._utils.exceptions import (
        DataNotAvailableError,
        DownloadError,
        HarmonizationError,
        MergeError,
        ModuleNotAvailableError,
        ParseError,
    )

    # Same skippable set as `load`: per-period data/network errors are
    # skipped under strict=False; usage errors (ModuleNotAvailableError,
    # ConfigError) are raised regardless.
    _SKIPPABLE: tuple[type[BaseException], ...] = (
        DataNotAvailableError,
        DownloadError,
        ParseError,
        MergeError,
        HarmonizationError,
    )

    for y, mo in periods:
        key = f"{y}-{mo:02d}"

        try:
            # ── Empalme smoothing path ────────────────────────────────────────
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

            # ── Normal loading path ───────────────────────────────────────────
            epoch = epoch_for_month(y, mo)

            record = sources["data"].get(key)
            if record is None:
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
            # in the list must exist for this period. Silently dropping is the
            # old bug — surface it so callers know what they actually got.
            if modules is not None:
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
                required = _required_modules_for_variables(
                    variable_map, sources, epoch.key, variables
                )
                for m in required:
                    if m not in working_modules:
                        working_modules.append(m)
                        logger.debug(
                            "Auto-including module %r required by harmonized variables.", m
                        )

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
            for mod in module_dfs:
                if mod not in used_modules:
                    used_modules.append(mod)

            merged = merge_modules(module_dfs, epoch, level="persona", how="outer")

            if harmonize:
                merged = harmonize_dataframe(merged, epoch, variables=variables)
                period_skipped = _drain_skipped_variables(merged)
                if period_skipped:
                    skipped_per_period.append(period_skipped)

            if multi:
                # See note in `load`: scope the suppression of pandas'
                # PerformanceWarning to just this assignment so the
                # filterwarnings = ["error"] policy holds everywhere else.
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
                    merged = merged.assign(year=y, month=mo)

            all_frames.append(merged)
        except _SKIPPABLE as exc:
            if strict_flag:
                raise
            failures.append((key, f"{type(exc).__name__}: {exc}"))
            logger.info("Skipping %s under strict=False: %s", key, exc)
            continue

    if not strict_flag:
        _emit_unvalidated_warning(
            unvalidated_keys,
            total_loaded=len(all_frames),
            total_requested=len(periods),
            failures=failures,
        )
        _emit_aggregated_skipped_variables_warning(
            skipped_per_period,
            total_periods=len(periods),
        )

    if not all_frames:
        result = pd.DataFrame()
    elif len(all_frames) == 1:
        result = all_frames[0]
    else:
        result = pd.concat(all_frames, ignore_index=True)

    # Defensive: strip the transient channel before returning to the user.
    result.attrs.pop("_skipped_variables", None)

    if metadata:
        _attach_metadata_for_load_merged(result, periods, used_modules)

    return result


def _attach_metadata_for_load_merged(
    df: pd.DataFrame,
    periods: list[tuple[int, int]],
    used_modules: list[str],
) -> None:
    """Attach composed metadata to ``df.attrs`` for :func:`load_merged`.

    ``df.attrs["source_modules"]`` is the list of modules that
    participated in the merge (deduplicated, in first-seen order).
    Anchoring is the same as :func:`_attach_metadata_for_load`: the
    last-loaded period.
    """
    if not periods:
        return
    anchor_year, anchor_month = periods[-1]
    from pulso._config.epochs import epoch_for_month
    from pulso.metadata.composer import compose_dataframe_metadata

    # When multiple modules merged, no single 'module' is correct; use a
    # synthetic '+'-joined label so the composer's `module=` argument is
    # informative without leaking into Curator lookups (which are
    # canonical-name-driven, not module-driven).
    module_label = "+".join(used_modules) if used_modules else "merged"
    df.attrs["column_metadata"] = compose_dataframe_metadata(
        df, anchor_year, anchor_month, module_label
    )
    df.attrs["source_year"] = anchor_year
    df.attrs["source_month"] = anchor_month
    df.attrs["source_modules"] = list(used_modules)
    df.attrs["source_epoch"] = epoch_for_month(anchor_year, anchor_month).key
