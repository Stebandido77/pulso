"""Parser: reads files inside the ZIP into pandas DataFrames.

Format dispatch is driven by the epoch's `file_format` field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

    from pulso._config.epochs import Epoch

Area = Literal["cabecera", "resto", "total"]


def parse_module(
    zip_path: Path,
    module: str,
    area: Area,
    epoch: Epoch,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Extract and parse a module from the ZIP.

    Args:
        zip_path: Path to the local ZIP file.
        module: Canonical module name.
        area: 'cabecera', 'resto', or 'total' (concatenates both).
        epoch: Epoch object dictating encoding, separator, format.
        columns: Optional list of source-variable names to keep.

    Returns:
        Raw DataFrame with original DANE column names (no harmonization).

    Raises:
        ParseError: If the file inside the ZIP is missing or malformed.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def _parse_csv(
    zip_path: Path,
    inner_path: str,
    epoch: Epoch,
    columns: list[str] | None,
) -> pd.DataFrame:
    raise NotImplementedError("Phase 1: Claude Code")


def _parse_sav(zip_path: Path, inner_path: str) -> pd.DataFrame:
    """Optional: requires pyreadstat. Used for older months in SPSS format."""
    raise NotImplementedError("Phase 4: Claude Code (legacy formats)")


def _parse_dta(zip_path: Path, inner_path: str) -> pd.DataFrame:
    """Optional: requires pyreadstat. Used for older months in Stata format."""
    raise NotImplementedError("Phase 4: Claude Code (legacy formats)")
