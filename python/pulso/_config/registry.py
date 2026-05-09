"""Registry: read-only access to sources.json, modules, and variable map.

This module is the single point of truth for "what data exists and where".
The rest of the package never reads JSON directly — it goes through here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jsonschema

from pulso._utils.exceptions import ConfigError

if TYPE_CHECKING:
    import pandas as pd

# Module-level singletons — set to None to force a reload (useful in tests).
_SOURCES: dict[str, Any] | None = None
_EPOCHS: dict[str, Any] | None = None
_VARIABLE_MAP: dict[str, Any] | None = None
_VARIABLE_MODULE_MAP: dict[str, Any] | None = None


def _data_dir() -> Path:
    """Return the path to the packaged data directory."""
    return Path(__file__).resolve().parent.parent / "data"


def _load_json_validated(data_path: Path, schema_path: Path) -> dict[str, Any]:
    with data_path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    with schema_path.open(encoding="utf-8") as f:
        schema: dict[str, Any] = json.load(f)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ConfigError(exc.message) from exc
    return data


def _load_sources() -> dict[str, Any]:
    """Load and validate sources.json against its schema, caching the result."""
    global _SOURCES
    if _SOURCES is None:
        d = _data_dir()
        _SOURCES = _load_json_validated(d / "sources.json", d / "schemas" / "sources.schema.json")
    return _SOURCES


def _load_epochs() -> dict[str, Any]:
    """Load and validate epochs.json against its schema, caching the result."""
    global _EPOCHS
    if _EPOCHS is None:
        d = _data_dir()
        _EPOCHS = _load_json_validated(d / "epochs.json", d / "schemas" / "epochs.schema.json")
    return _EPOCHS


def _load_variable_map() -> dict[str, Any]:
    """Load and validate variable_map.json against its schema, caching the result."""
    global _VARIABLE_MAP
    if _VARIABLE_MAP is None:
        d = _data_dir()
        _VARIABLE_MAP = _load_json_validated(
            d / "variable_map.json", d / "schemas" / "variable_map.schema.json"
        )
    return _VARIABLE_MAP


def _load_variable_module_map() -> dict[str, Any]:
    """Load and validate variable_module_map.json against its schema.

    Returns the parsed mapping ``{canonical_name: [module_name, ...]}``.
    Cached at the module level — set ``_VARIABLE_MODULE_MAP = None`` in
    tests to force a reload.
    """
    global _VARIABLE_MODULE_MAP
    if _VARIABLE_MODULE_MAP is None:
        d = _data_dir()
        _VARIABLE_MODULE_MAP = _load_json_validated(
            d / "variable_module_map.json",
            d / "schemas" / "variable_module_map.schema.json",
        )
    return _VARIABLE_MODULE_MAP


def data_version() -> str:
    """Return the data_version string from sources.json metadata.

    Retorna la versión de datos desde el metadato de sources.json.

    Returns:
        Version string in 'YYYY.MM' format.
    """
    return str(_load_sources()["metadata"]["data_version"])


def list_validated_range() -> list[tuple[int, int]]:
    """Return the (year, month) pairs for entries with ``validated=True``.

    Validated entries may not be contiguous — production has 5 validated
    months scattered across 2007-2024. Use ``validation_status()`` for the
    full registry including non-validated entries.

    Returns:
        Sorted list of ``(year, month)`` tuples. Empty list if no entries
        are currently flagged as validated.

    Example:
        >>> pulso.list_validated_range()
        [(2007, 12), (2015, 6), (2021, 12), (2022, 1), (2024, 6)]
    """
    sources = _load_sources()
    pairs: list[tuple[int, int]] = []
    for key, record in sources["data"].items():
        if record.get("validated"):
            pairs.append((int(key[:4]), int(key[5:7])))
    pairs.sort()
    return pairs


def validation_status() -> pd.DataFrame:
    """Return the full validation status of every entry in the registry.

    Columns:
        - ``year``: int
        - ``month``: int
        - ``validated``: bool
        - ``checksum_sha256``: str or None
        - ``validated_at``: ISO 8601 datetime str or None (matches the
          ``validated_at`` field name in sources.schema.json)
        - ``modules``: list of module names available for the period

    Example:
        >>> df = pulso.validation_status()
        >>> df[df.validated].shape[0] == len(pulso.list_validated_range())
        True
    """
    import pandas as pd

    sources = _load_sources()
    rows: list[dict[str, Any]] = []
    for key, record in sources["data"].items():
        rows.append(
            {
                "year": int(key[:4]),
                "month": int(key[5:7]),
                "validated": bool(record.get("validated")),
                "checksum_sha256": record.get("checksum_sha256"),
                "validated_at": record.get("validated_at"),
                "modules": list(record.get("modules", {}).keys()),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["year", "month"]).reset_index(drop=True)
    return df


def list_available(year: int | None = None) -> pd.DataFrame:
    """List which (year, month) entries exist in the registry.

    Lista los períodos disponibles en el registro.

    Args:
        year: If provided, filter to only that year.

    Returns:
        DataFrame with columns: year, month, epoch, validated, modules_available.
    """
    import pandas as pd

    sources = _load_sources()
    rows = []
    for key, record in sources["data"].items():
        y, m = int(key[:4]), int(key[5:7])
        if year is not None and y != year:
            continue
        rows.append(
            {
                "year": y,
                "month": m,
                "epoch": record["epoch"],
                "validated": record["validated"],
                "modules_available": list(record["modules"].keys()),
            }
        )
    return pd.DataFrame(rows)


def list_modules() -> pd.DataFrame:
    """List all canonical modules and their metadata.

    Lista todos los módulos canónicos del GEIH.

    Returns:
        DataFrame with columns: module, level, description_es, description_en, available_in.
    """
    import pandas as pd

    sources = _load_sources()
    rows = []
    for name, meta in sources["modules"].items():
        rows.append(
            {
                "module": name,
                "level": meta["level"],
                "description_es": meta["description_es"],
                "description_en": meta.get("description_en", ""),
                "available_in": meta["available_in"],
            }
        )
    return pd.DataFrame(rows)


def list_variables(harmonized: bool = True) -> pd.DataFrame:
    """List harmonized variables defined in variable_map.json.

    Args:
        harmonized: If True (default), only list variables with at least one
            epoch mapping. If False, lists every entry in the variable map
            (including those with mappings={} — useful for catalog queries).

    Returns:
        DataFrame with columns: variable, type, level, module, description_es,
        description_en, available_in_epochs (list of epoch keys).
    """
    import pandas as pd

    vm = _load_variable_map()
    rows: list[dict[str, Any]] = []
    for canonical_name, entry in vm["variables"].items():
        epochs_for_var = list(entry.get("mappings", {}).keys())
        if harmonized and not epochs_for_var:
            continue
        rows.append(
            {
                "variable": canonical_name,
                "type": entry.get("type", ""),
                "level": entry.get("level", ""),
                "module": entry.get("module", ""),
                "description_es": entry.get("description_es", ""),
                "description_en": entry.get("description_en", ""),
                "available_in_epochs": epochs_for_var,
            }
        )
    return pd.DataFrame(rows)


def describe(
    module: str,
    year: int | None = None,
    month: int | None = None,
) -> dict[str, Any]:
    """Describe a module's structure and availability.

    Describe la estructura y disponibilidad de un módulo.

    Three call shapes:

    * ``describe(module)``             — catalog overview across all
      registered periods (epochs that cover the module, validated count,
      total period count, harmonised variable count).
    * ``describe(module, year)``       — year overview (epoch, available
      months, validated months, comparability notes).
    * ``describe(module, year, month)``— specific period detail (epoch,
      validated flag, checksum, validated_at, file URL).

    Args:
        module: Canonical module name. If unknown, the error message
            includes a difflib-based "did you mean ...?" suggestion.
        year: Optional year (2006-...). Required when ``month`` is set.
        month: Optional month (1-12).

    Returns:
        Dict with metadata. Always includes ``module``; the rest depends
        on the call shape (see examples).

    Raises:
        ConfigError: ``module`` is not in the registry.
        ValueError: ``month`` was passed without ``year``.
    """
    import difflib

    sources = _load_sources()
    modules = sources["modules"]
    if module not in modules:
        all_modules = sorted(modules.keys())
        suggestions = difflib.get_close_matches(module, all_modules, n=3)
        msg = f"Module {module!r} not found in registry."
        if suggestions:
            msg += f" Did you mean: {suggestions}?"
        msg += f" Available modules: {all_modules}."
        raise ConfigError(msg)

    if month is not None and year is None:
        raise ValueError("describe(month=...) requires year=... as well.")

    base: dict[str, Any] = dict(modules[module])
    base["module"] = module

    # ── Catalog mode ──────────────────────────────────────────────────────
    if year is None:
        period_keys = [k for k, rec in sources["data"].items() if module in rec["modules"]]
        validated_keys = [k for k in period_keys if sources["data"][k].get("validated")]
        # variable_map is read lazily — only count harmonised variables that
        # name this module.
        try:
            vm = _load_variable_map()
            harmonised = sum(1 for v in vm["variables"].values() if v.get("module") == module)
        except ConfigError:
            harmonised = 0

        base["total_periods_in_registry"] = len(period_keys)
        base["validated_periods"] = len(validated_keys)
        base["epochs_covering"] = list(base.get("available_in", []))
        base["variables_harmonized"] = harmonised
        if period_keys:
            sorted_keys = sorted(period_keys)
            base["available_for_periods"] = f"{sorted_keys[0]} to {sorted_keys[-1]}"
        return base

    # ── Year mode ─────────────────────────────────────────────────────────
    from pulso._config.epochs import epoch_for_month

    if month is None:
        # Use January as the lookup probe; epoch boundaries are month-aligned
        # so any month in the year resolves to the same epoch except across a
        # year that straddles a methodological change (handled gracefully —
        # we just report whichever epoch January falls in).
        epoch = epoch_for_month(year, 1)
        year_keys = [
            k
            for k, rec in sources["data"].items()
            if k.startswith(f"{year}-") and module in rec["modules"]
        ]
        validated_year_keys = [k for k in year_keys if sources["data"][k].get("validated")]
        base["year"] = year
        base["epoch"] = epoch.key
        # Backward-compat: rc1 returned `epoch_context` for describe(module, year).
        # Keep it alongside the newer `epoch` key so existing callers keep working.
        base["epoch_context"] = {
            "key": epoch.key,
            "label": epoch.label,
            "encoding": epoch.encoding,
            "file_format": epoch.file_format,
        }
        base["available_months"] = sorted(int(k[5:7]) for k in year_keys)
        base["validated_months"] = sorted(int(k[5:7]) for k in validated_year_keys)
        return base

    # ── Period mode (year + month) ────────────────────────────────────────
    key = f"{year}-{month:02d}"
    record = sources["data"].get(key)
    if record is None:
        from pulso._utils.exceptions import DataNotAvailableError

        raise DataNotAvailableError(
            year, month, hint="Use pulso.list_available() to see registered periods."
        )
    if module not in record["modules"]:
        from pulso._utils.exceptions import ModuleNotAvailableError

        raise ModuleNotAvailableError(
            f"Module {module!r} is not available for {key}. "
            f"Available for this period: {list(record['modules'].keys())}."
        )

    epoch = epoch_for_month(year, month)
    base["year"] = year
    base["month"] = month
    base["epoch"] = epoch.key
    base["validated"] = bool(record.get("validated"))
    base["checksum_sha256"] = record.get("checksum_sha256")
    base["validated_at"] = record.get("validated_at")
    base["file_url"] = record.get("download_url")
    return base


def describe_variable(name: str) -> dict[str, Any]:
    """Describe a harmonized variable: its type, mappings, source docs.

    Args:
        name: Canonical variable name.

    Returns:
        Dict with full variable metadata. Includes the canonical name as
        the first key plus everything from variable_map.json (type, level,
        module, descriptions, categories, comparability_warning, mappings).

    Raises:
        ConfigError: variable not in variable_map.json.
    """
    vm = _load_variable_map()
    variables: dict[str, Any] = vm["variables"]
    if name not in variables:
        available = sorted(variables.keys())
        raise ConfigError(
            f"Variable {name!r} not found in variable_map.json. "
            f"Available ({len(available)}): {available}."
        )
    result: dict[str, Any] = {"canonical_name": name}
    result.update(variables[name])
    return result


def describe_harmonization(variable: str) -> pd.DataFrame:
    """Show the harmonization chain for a variable across epochs.

    Args:
        variable: Canonical variable name.

    Returns:
        DataFrame with one row per epoch where the variable is mapped.
        Columns: epoch, source_variable, transform, source_doc, notes.

    Raises:
        ConfigError: variable not in variable_map.json.
    """
    import pandas as pd

    vm = _load_variable_map()
    variables: dict[str, Any] = vm["variables"]
    if variable not in variables:
        available = sorted(variables.keys())
        raise ConfigError(
            f"Variable {variable!r} not found in variable_map.json. "
            f"Available ({len(available)}): {available}."
        )

    rows: list[dict[str, Any]] = []
    mappings: dict[str, Any] = variables[variable].get("mappings", {})
    for epoch_key, mapping in mappings.items():
        transform = mapping.get("transform")
        if isinstance(transform, dict):
            transform_repr = transform.get("op", str(transform))
        else:
            transform_repr = str(transform)
        rows.append(
            {
                "epoch": epoch_key,
                "source_variable": mapping.get("source_variable"),
                "transform": transform_repr,
                "source_doc": mapping.get("source_doc"),
                "notes": mapping.get("notes"),
            }
        )
    return pd.DataFrame(rows)
