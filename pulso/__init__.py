"""pulso: Python library to load GEIH microdata from Colombia's DANE.

*El pulso del mercado laboral colombiano.*

Public API:

    pulso.load(year, month, module, ...) -> pd.DataFrame
    pulso.load_merged(year, month, modules, ...) -> pd.DataFrame
    pulso.list_available(year=None) -> pd.DataFrame
    pulso.list_modules() -> pd.DataFrame
    pulso.list_variables() -> pd.DataFrame
    pulso.describe(module, year=None) -> dict
    pulso.describe_variable(name) -> dict
    pulso.describe_harmonization(variable) -> pd.DataFrame
    pulso.expand(df, weight=None) -> pd.DataFrame
    pulso.cache_info() -> dict
    pulso.cache_clear(level="all") -> None
    pulso.cache_path() -> Path
    pulso.data_version() -> str
"""

from __future__ import annotations

from pulso._config.registry import (
    data_version,
    describe,
    describe_harmonization,
    describe_variable,
    list_available,
    list_modules,
    list_variables,
)
from pulso._core.empalme import load_empalme
from pulso._core.expander import expand
from pulso._core.loader import load, load_merged
from pulso._utils.cache import cache_clear, cache_info, cache_path

__version__ = "1.0.0rc1"

__all__ = [
    "__version__",
    "cache_clear",
    "cache_info",
    "cache_path",
    "data_version",
    "describe",
    "describe_harmonization",
    "describe_variable",
    "expand",
    "list_available",
    "list_modules",
    "list_variables",
    "load",
    "load_empalme",
    "load_merged",
]
