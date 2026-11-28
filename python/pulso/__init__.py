"""pulso: Python library to load GEIH microdata from Colombia's DANE.

*El pulso del mercado laboral colombiano.*

Public API:

    pulso.load(year, month, module, ...) -> pd.DataFrame
    pulso.load_merged(year, month, modules, ...) -> pd.DataFrame
    pulso.load_range(start, end, module, ...) -> pd.DataFrame
    pulso.indicadores(start, end=None, dominio='nacional', ...) -> pd.DataFrame
    pulso.list_available(year=None) -> pd.DataFrame
    pulso.list_modules() -> pd.DataFrame
    pulso.list_variables() -> pd.DataFrame
    pulso.describe(module, year=None) -> dict
    pulso.describe_column(df, column) -> str
    pulso.describe_variable(name) -> dict
    pulso.describe_harmonization(variable) -> pd.DataFrame
    pulso.expand(df, weight=None) -> pd.DataFrame
    pulso.list_columns_metadata(df) -> pd.DataFrame
    pulso.cache_info() -> dict
    pulso.cache_clear(level="all") -> None
    pulso.cache_path() -> Path
    pulso.data_version() -> str
    pulso.tpm(start=None, end=None, use_fixture=None) -> pd.DataFrame
    pulso.trm(start=None, end=None, use_fixture=None) -> pd.DataFrame
    pulso.ipc(use_fixture=None) -> pd.DataFrame
    pulso.salario_minimo() -> pd.DataFrame
    pulso.deflactar(df, columns, deflate_to) -> pd.DataFrame
"""

from __future__ import annotations

from pulso._config.registry import (
    data_version,
    describe,
    describe_harmonization,
    describe_variable,
    list_available,
    list_modules,
    list_validated_range,
    list_variables,
    update_catalog,
    validation_status,
)
from pulso._core.banrep_tpm import tpm
from pulso._core.empalme import load_empalme
from pulso._core.expander import expand
from pulso._core.indicadores import indicadores
from pulso._core.loader import load, load_merged
from pulso._core.range import load_range
from pulso._core.real_income import deflactar, ipc, salario_minimo
from pulso._core.trm import trm
from pulso._utils.cache import cache_clear, cache_info, cache_path
from pulso._utils.exceptions import (
    CacheError,
    ChecksumMismatchError,
    ConfigError,
    DataNotAvailableError,
    DataNotValidatedError,
    DownloadError,
    HarmonizationError,
    MergeError,
    ModuleNotAvailableError,
    ParseError,
    PulsoError,
)
from pulso.metadata.api import describe_column, list_columns_metadata

__version__ = "1.3.0"

__all__ = [
    "CacheError",
    "ChecksumMismatchError",
    "ConfigError",
    "DataNotAvailableError",
    "DataNotValidatedError",
    "DownloadError",
    "HarmonizationError",
    "MergeError",
    "ModuleNotAvailableError",
    "ParseError",
    "PulsoError",
    "__version__",
    "cache_clear",
    "cache_info",
    "cache_path",
    "data_version",
    "deflactar",
    "describe",
    "describe_column",
    "describe_harmonization",
    "describe_variable",
    "expand",
    "indicadores",
    "ipc",
    "list_available",
    "list_columns_metadata",
    "list_modules",
    "list_validated_range",
    "list_variables",
    "load",
    "load_empalme",
    "load_merged",
    "load_range",
    "salario_minimo",
    "tpm",
    "trm",
    "update_catalog",
    "validation_status",
]
