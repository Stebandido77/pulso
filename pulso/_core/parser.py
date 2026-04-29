"""Parser: reads files inside the ZIP into pandas DataFrames.

Format dispatch is driven by the epoch's `file_format` field.
"""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING, Literal

from pulso._config.registry import _load_sources
from pulso._utils.exceptions import ParseError

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

    from pulso._config.epochs import Epoch

Area = Literal["cabecera", "resto", "total"]


def _parse_csv(
    zip_path: Path,
    inner_path: str,
    epoch: Epoch,
    columns: list[str] | None,
) -> pd.DataFrame:
    """Stream-read a CSV from inside a ZIP without extracting to disk.

    Lee un CSV dentro de un ZIP sin extraerlo al disco.

    Raises:
        ParseError: If the inner file is missing or malformed.
    """
    import pandas as pd

    try:
        with zipfile.ZipFile(zip_path) as zf, zf.open(inner_path) as fh:
            df: pd.DataFrame = pd.read_csv(
                fh,
                encoding=epoch.encoding,
                sep=epoch.separator if epoch.separator is not None else ",",
                decimal=epoch.decimal,
                usecols=columns,
                low_memory=False,
            )
    except KeyError as exc:
        raise ParseError(f"File {inner_path!r} not found inside {zip_path.name}.") from exc
    except Exception as exc:
        raise ParseError(f"Failed to parse {inner_path!r} in {zip_path.name}: {exc}") from exc
    return df


def _parse_sav(zip_path: Path, inner_path: str) -> pd.DataFrame:
    """Optional: requires pyreadstat. Used for SPSS-format files."""
    raise NotImplementedError("Phase 4: Claude Code (legacy formats)")


def _parse_dta(zip_path: Path, inner_path: str) -> pd.DataFrame:
    """Optional: requires pyreadstat. Used for Stata-format files."""
    raise NotImplementedError("Phase 4: Claude Code (legacy formats)")


def parse_module(
    zip_path: Path,
    year: int,
    month: int,
    module: str,
    area: Area,
    epoch: Epoch,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Extract and parse a module from the ZIP.

    Extrae y parsea un módulo del archivo ZIP.

    File paths are looked up from the registry entry for (year, month).
    If area='total', both cabecera and resto are parsed and concatenated,
    with a '_area' column added ('cabecera' / 'resto').

    Args:
        zip_path: Path to the local ZIP file.
        year: Year of the data record (for registry lookup).
        month: Month of the data record (for registry lookup).
        module: Canonical module name.
        area: 'cabecera', 'resto', or 'total'.
        epoch: Epoch object with encoding/format/separator.
        columns: Optional list of column names to keep.

    Returns:
        Raw DataFrame with original DANE column names.

    Raises:
        ParseError: If the file inside the ZIP is missing or malformed.
    """
    import pandas as pd

    sources = _load_sources()
    key = f"{year}-{month:02d}"
    record = sources["data"][key]
    module_files = record["modules"][module]

    if epoch.file_format == "csv":
        _parse_fn = _parse_csv
    elif epoch.file_format in ("sav", "dta"):
        raise NotImplementedError("Phase 4")
    else:
        raise ParseError(f"Unknown file format: {epoch.file_format!r}")

    if area == "cabecera":
        inner = module_files["cabecera"]
        if inner is None:
            raise ParseError(f"Module {module!r} has no cabecera file for {key}.")
        return _parse_fn(zip_path, inner, epoch, columns)

    if area == "resto":
        inner = module_files["resto"]
        if inner is None:
            raise ParseError(f"Module {module!r} has no resto file for {key}.")
        return _parse_fn(zip_path, inner, epoch, columns)

    # area == "total": parse both and concatenate
    frames = []
    for label, path_key in (("cabecera", "cabecera"), ("resto", "resto")):
        inner = module_files.get(path_key)
        if inner is None:
            continue
        part = _parse_fn(zip_path, inner, epoch, columns)
        part["_area"] = label
        frames.append(part)

    if not frames:
        raise ParseError(f"Module {module!r} has no files for {key}.")

    return pd.concat(frames, ignore_index=True)
