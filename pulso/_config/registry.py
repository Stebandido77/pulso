"""Registry: read-only access to sources.json, modules, and variable map.

This module is the single point of truth for "what data exists and where".
The rest of the package never reads JSON directly — it goes through here.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def data_version() -> str:
    """Return the data_version string from sources.json metadata.

    Returns:
        Version string in 'YYYY.MM' format.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def list_available(year: int | None = None) -> pd.DataFrame:
    """List which (year, month) entries exist in the registry.

    Args:
        year: If provided, filter to only that year.

    Returns:
        DataFrame with columns: year, month, epoch, validated, modules_available.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def list_modules() -> pd.DataFrame:
    """List all canonical modules and their metadata.

    Returns:
        DataFrame with columns: module, level, description_es, description_en,
        available_in.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def list_variables(harmonized: bool = True) -> pd.DataFrame:
    """List harmonized variables defined in variable_map.json.

    Args:
        harmonized: If True, only list variables with at least one mapping
            in each epoch. If False, list all defined variables.

    Returns:
        DataFrame with columns: variable, type, level, module, description_es,
        comparability_warning.
    """
    raise NotImplementedError("Phase 2: Claude Code")


def describe(module: str, year: int | None = None) -> dict[str, object]:
    """Describe a module's structure and availability.

    Args:
        module: Canonical module name.
        year: If provided, describe in the context of that year's epoch.

    Returns:
        Dict with module metadata.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def describe_variable(name: str) -> dict[str, object]:
    """Describe a harmonized variable: its type, mappings, source docs.

    Args:
        name: Canonical variable name (key in variable_map.json).

    Returns:
        Dict with full variable metadata.
    """
    raise NotImplementedError("Phase 2: Claude Code")


def describe_harmonization(variable: str) -> pd.DataFrame:
    """Show the harmonization chain for a variable across epochs.

    Args:
        variable: Canonical variable name.

    Returns:
        DataFrame with columns: epoch, source_variable, transform, source_doc.
        Useful for transparency in publications.
    """
    raise NotImplementedError("Phase 2: Claude Code")


# ─── Internal API (used by other pulso modules) ──────────────────────


def _load_sources() -> dict[str, object]:
    """Load and validate sources.json against its schema."""
    raise NotImplementedError("Phase 0: validation only at this stage")


def _load_epochs() -> dict[str, object]:
    """Load and validate epochs.json against its schema."""
    raise NotImplementedError("Phase 0: validation only at this stage")


def _load_variable_map() -> dict[str, object]:
    """Load and validate variable_map.json against its schema."""
    raise NotImplementedError("Phase 0: validation only at this stage")


def _data_dir() -> Path:
    """Return the path to the packaged data directory."""
    return Path(__file__).resolve().parent.parent / "data"
