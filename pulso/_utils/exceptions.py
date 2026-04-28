"""Typed exceptions for the pulso package."""

from __future__ import annotations


class PulsoError(Exception):
    """Base exception for all pulso errors."""


class ConfigError(PulsoError):
    """Raised when sources.json, variable_map.json, or epochs.json is invalid or inconsistent."""


class DataNotAvailableError(PulsoError):
    """Raised when the requested (year, month) is not in sources.json."""

    def __init__(self, year: int, month: int, hint: str | None = None) -> None:
        msg = f"Data for {year}-{month:02d} is not available in the registry."
        if hint:
            msg += f" {hint}"
        super().__init__(msg)
        self.year = year
        self.month = month


class DataNotValidatedError(PulsoError):
    """Raised when an entry exists but `validated=false` and `allow_unvalidated=False`."""


class ModuleNotAvailableError(PulsoError):
    """Raised when the requested module does not exist in the requested epoch."""


class DownloadError(PulsoError):
    """Raised when the ZIP download fails or the checksum mismatches."""


class ParseError(PulsoError):
    """Raised when the parser cannot read a file inside the ZIP."""


class HarmonizationError(PulsoError):
    """Raised when a transform in variable_map.json fails to apply."""


class MergeError(PulsoError):
    """Raised when modules cannot be merged due to incompatible keys."""


class CacheError(PulsoError):
    """Raised on cache I/O issues."""
