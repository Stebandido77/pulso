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


def data_version() -> str:
    """Return the data_version string from sources.json metadata.

    Retorna la versión de datos desde el metadato de sources.json.

    Returns:
        Version string in 'YYYY.MM' format.
    """
    return str(_load_sources()["metadata"]["data_version"])


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


def describe(module: str, year: int | None = None) -> dict[str, Any]:
    """Describe a module's structure and availability.

    Describe la estructura y disponibilidad de un módulo.

    Args:
        module: Canonical module name.
        year: If provided, include epoch context for that year.

    Returns:
        Dict with module metadata.
    """
    sources = _load_sources()
    modules = sources["modules"]
    if module not in modules:
        raise ConfigError(f"Module {module!r} not found in registry.")
    result: dict[str, Any] = dict(modules[module])
    result["module"] = module
    if year is not None:
        from pulso._config.epochs import epoch_for_month

        epoch = epoch_for_month(year, 1)
        result["epoch_context"] = {
            "key": epoch.key,
            "label": epoch.label,
            "encoding": epoch.encoding,
            "file_format": epoch.file_format,
        }
    return result


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
