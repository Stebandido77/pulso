"""Parser: reads files inside the ZIP into pandas DataFrames.

Format dispatch is driven by the epoch's `file_format` field.
Shape dispatch:
  - is_shape_a(zip_path) → True   : Shape A (GEIH-1): Cabecera/Resto auto-discovery.
  - is_shape_a(zip_path) → False  : Shape B (GEIH-2): single unified file with CLASE filter.

Shape A auto-discovery (Phase 3.2.B):
  Each module is found by scanning the ZIP for filenames starting with
  'Cabecera' or 'Resto' and containing a keyword from MODULE_KEYWORDS_GEIH1.
  Area files (prefix 'Area') are discarded. Cabecera and Resto DataFrames
  are concatenated with a synthetic CLASE column (1=urban, 2=rural).
"""

from __future__ import annotations

import io
import re
import zipfile
from typing import TYPE_CHECKING, Literal, cast

from pulso._config.registry import _load_sources
from pulso._utils.columns import _normalize_dane_columns
from pulso._utils.exceptions import ParseError

if TYPE_CHECKING:
    from pathlib import Path

    import pandas as pd

    from pulso._config.epochs import Epoch

Area = Literal["cabecera", "resto", "total"]

# ---------------------------------------------------------------------------
# Shape A: module keyword mapping and auto-discovery
# ---------------------------------------------------------------------------

MODULE_KEYWORDS_GEIH1: dict[str, list[str]] = {
    "caracteristicas_generales": [
        "Características generales",  # correct accent, 2015+
        "Caracteristicas generales",  # no accent, fixture / some years
        "Caractericas generales",  # 2007 typo: missing 't'
    ],
    "ocupados": ["Ocupados"],
    "desocupados": ["Desocupados"],
    "inactivos": ["Inactivos"],
    "vivienda_hogares": ["Vivienda y Hogares"],
    "otros_ingresos": ["Otros ingresos"],
    "otras_formas_trabajo": ["Otras actividades y ayudas"],
    "fuerza_de_trabajo": ["Fuerza de trabajo"],
}


def is_shape_a(zip_path: Path) -> bool:
    """Detect Shape A by checking for 'Cabecera' in any filename inside the ZIP."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    return any("Cabecera" in n for n in names)


def find_shape_a_files(
    zip_path: Path,
    module: str,
) -> tuple[str | None, str | None]:
    """Locate Cabecera and Resto files for *module* inside a Shape A ZIP.

    Uses substring keyword matching against MODULE_KEYWORDS_GEIH1 to tolerate
    filename variations across GEIH-1 years (typos, spacing, encoding).

    Returns:
        (cabecera_inner_path, resto_inner_path). Either may be None if not found.
    """
    keywords = MODULE_KEYWORDS_GEIH1.get(module, [module])

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()

    cabecera: str | None = None
    resto: str | None = None

    for name in names:
        if name.endswith("/"):
            continue  # directory entry
        basename = name.rsplit("/", 1)[-1] if "/" in name else name
        lower = basename.lower()

        # Only accept files with Cabecera or Resto prefix; discard Area and others.
        if lower.startswith("cabecera"):
            prefix = "cabecera"
        elif lower.startswith("resto"):
            prefix = "resto"
        else:
            continue

        # Match at least one keyword using word-boundary regex so that e.g.
        # "ocupados" does NOT match inside "desocupados".
        if not any(re.search(r"\b" + re.escape(kw.lower()) + r"\b", lower) for kw in keywords):
            continue

        if prefix == "cabecera":
            cabecera = name
        else:
            resto = name

    return cabecera, resto


def _resolve_zip_path(zf: zipfile.ZipFile, path: str) -> str:
    """Resolve a ZIP member path, tolerating mojibake encoding and missing subfolder prefix.

    Tries in order: (1) exact match, (2) mojibake-fixed path, (3) case-insensitive
    basename match across all ZIP entries.  Raises KeyError if nothing matches.
    """
    names = zf.namelist()

    if path in names:
        return path

    try:
        fixed = path.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        fixed = path

    if fixed in names:
        return fixed

    target = fixed.rsplit("/", 1)[-1].lower()
    for name in names:
        if not name.endswith("/") and name.rsplit("/", 1)[-1].lower() == target:
            return name

    raise KeyError(f"No item named {path!r} in the archive")


# ---------------------------------------------------------------------------
# Nested ZIP support
# ---------------------------------------------------------------------------
#
# Some DANE releases (notably 2024-03 and 2024-04 GEIH) wrap the actual data
# files inside *another* ZIP layer.  The outer archive contains only
# ``CSV.zip``, ``DTA.zip``, ``SAV.zip`` entries; the user-facing CSVs live
# inside the matching format-named inner ZIP.  The helper below transparently
# descends one level so callers don't have to special-case the layout.

_FORMAT_TO_NESTED_NAME: dict[str, str] = {
    "csv": "CSV.zip",
    "dta": "DTA.zip",
    "sav": "SAV.zip",
}


def _is_nested_format_wrapper(zf: zipfile.ZipFile) -> bool:
    """True when the archive only contains ``CSV.zip``/``DTA.zip``/``SAV.zip`` entries.

    Used to detect the 2024-03/04 nested layout where DANE wraps each
    format in its own inner ZIP.
    """
    names = [n for n in zf.namelist() if not n.endswith("/")]
    if not names:
        return False
    nested_targets = set(_FORMAT_TO_NESTED_NAME.values())
    return all(n.rsplit("/", 1)[-1] in nested_targets for n in names)


def _open_nested_zip(zf: zipfile.ZipFile, format_name: str) -> zipfile.ZipFile:
    """Open the inner format-named ZIP (CSV.zip / DTA.zip / SAV.zip) for ``format_name``.

    Reads the nested ZIP fully into memory (DANE inner ZIPs are small,
    ~5-10 MB) and wraps it in a new ``ZipFile`` so the caller can use the
    full ``zipfile`` API (resolution, ``.open(...)`` member streaming).
    The caller is responsible for closing the returned object.
    """
    target = _FORMAT_TO_NESTED_NAME.get(format_name.lower())
    if target is None:
        raise KeyError(
            f"No known nested wrapper for file_format={format_name!r}; "
            f"expected one of {sorted(_FORMAT_TO_NESTED_NAME)}."
        )

    # Outer ZIP entries may live at the root or under a subfolder.
    # Match by basename (case-sensitive — DANE consistently uses uppercase).
    inner_member: str | None = None
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        if name.rsplit("/", 1)[-1] == target:
            inner_member = name
            break
    if inner_member is None:
        raise KeyError(f"Nested ZIP {target!r} not found in outer archive.")

    with zf.open(inner_member) as fh:
        inner_bytes = fh.read()
    return zipfile.ZipFile(io.BytesIO(inner_bytes))


def _read_csv_with_fallback(raw_bytes: bytes, epoch: Epoch) -> pd.DataFrame:
    """Try epoch separator; if 1-column result, auto-detect. Strip BOM and normalize merge keys.

    Column normalization is intentionally narrow: BOM is stripped from all columns;
    only merge-key columns (DIRECTORIO, SECUENCIA_P, ORDEN) are uppercased.  Other
    columns (e.g. fex_c_2011) keep their original case to match variable_map.json.
    """
    import pandas as pd

    sep = epoch.separator if epoch.separator is not None else ","
    buf = io.BytesIO(raw_bytes)
    df: pd.DataFrame = pd.read_csv(
        buf,
        encoding=epoch.encoding,
        sep=sep,
        decimal=epoch.decimal,
        low_memory=False,
    )
    if df.shape[1] == 1:
        buf.seek(0)
        df = pd.read_csv(
            buf,
            encoding=epoch.encoding,
            sep=None,
            engine="python",
            decimal=epoch.decimal,
        )

    # Strip BOM in both its UTF-8 unicode form and latin-1 decoded artifact (ï»¿).
    df.columns = df.columns.str.replace("﻿", "", regex=False).str.replace(
        "\xef\xbb\xbf", "", regex=False
    )

    # Normalize merge-key column names to their canonical uppercase form.
    # Handles years where DANE stored e.g. 'Directorio' instead of 'DIRECTORIO'.
    all_merge_keys = set(epoch.merge_keys_persona) | set(epoch.merge_keys_hogar)
    upper_map = {k.lower(): k for k in all_merge_keys}
    df.columns = pd.Index([upper_map.get(col.lower(), col) for col in df.columns])

    return df


def parse_shape_a_module(
    zip_path: Path,
    module: str,
    epoch: Epoch,
) -> pd.DataFrame:
    """Load *module* from a Shape A ZIP by concatenating Cabecera + Resto.

    Adds a synthetic CLASE column (1 = Cabecera/urban, 2 = Resto/rural) so
    downstream area-filter code that expects CLASE works without modification.

    Raises:
        ParseError: If neither a Cabecera nor a Resto file is found.
    """
    import pandas as pd

    cab_name, resto_name = find_shape_a_files(zip_path, module)

    if not cab_name and not resto_name:
        with zipfile.ZipFile(zip_path) as _zf:
            sample = _zf.namelist()[:8]
        raise ParseError(
            f"Module {module!r}: no Cabecera or Resto file found in {zip_path.name}. "
            f"First entries in ZIP: {sample}"
        )

    dfs: list[pd.DataFrame] = []

    with zipfile.ZipFile(zip_path) as zf:
        if cab_name:
            with zf.open(cab_name) as fh:
                raw = fh.read()
            try:
                df_cab: pd.DataFrame = _normalize_dane_columns(_read_csv_with_fallback(raw, epoch))
            except Exception as exc:
                raise ParseError(f"Failed to parse {cab_name!r} in {zip_path.name}: {exc}") from exc
            df_cab["CLASE"] = 1
            dfs.append(df_cab)
        if resto_name:
            with zf.open(resto_name) as fh:
                raw = fh.read()
            try:
                df_resto: pd.DataFrame = _normalize_dane_columns(
                    _read_csv_with_fallback(raw, epoch)
                )
            except Exception as exc:
                raise ParseError(
                    f"Failed to parse {resto_name!r} in {zip_path.name}: {exc}"
                ) from exc
            df_resto["CLASE"] = 2
            dfs.append(df_resto)

    return dfs[0] if len(dfs) == 1 else pd.concat(dfs, axis=0, ignore_index=True)


def _parse_csv(
    zip_path: Path,
    inner_path: str,
    epoch: Epoch,
    columns: list[str] | None,
) -> pd.DataFrame:
    """Stream-read a CSV from inside a ZIP without extracting to disk.

    Lee un CSV dentro de un ZIP sin extraerlo al disco.

    Transparently handles two layouts:
        - Direct: outer ZIP contains the CSV at ``inner_path`` (with optional
          subfolder prefix and case variation, resolved by ``_resolve_zip_path``).
        - Nested wrapper: outer ZIP contains only ``CSV.zip``/``DTA.zip``/``SAV.zip``
          (DANE 2024-03 / 2024-04 layout). In that case the matching inner
          format-named ZIP is opened and the CSV is resolved inside it.

    Raises:
        ParseError: If the inner file is missing or malformed.
    """

    try:
        with zipfile.ZipFile(zip_path) as zf:
            if _is_nested_format_wrapper(zf):
                with _open_nested_zip(zf, "csv") as inner_zf:
                    resolved = _resolve_zip_path(inner_zf, inner_path)
                    with inner_zf.open(resolved) as fh:
                        raw_bytes = fh.read()
            else:
                resolved = _resolve_zip_path(zf, inner_path)
                with zf.open(resolved) as fh:
                    raw_bytes = fh.read()
    except KeyError as exc:
        raise ParseError(f"File {inner_path!r} not found inside {zip_path.name}.") from exc
    except Exception as exc:
        raise ParseError(f"Failed to parse {inner_path!r} in {zip_path.name}: {exc}") from exc

    try:
        df: pd.DataFrame = _read_csv_with_fallback(raw_bytes, epoch)
    except Exception as exc:
        raise ParseError(f"Failed to parse {inner_path!r} in {zip_path.name}: {exc}") from exc

    if columns is not None:
        available = [c for c in columns if c in df.columns]
        df = df[available]

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

    Dispatch order:
    1. is_shape_a(zip_path) → True  : Shape A auto-discovery (Cabecera+Resto concat).
    2. epoch.area_filter is None    : Shape A lookup (explicit paths from sources.json).
    3. epoch.area_filter is not None: Shape B (single file, row-level CLASE filter).

    Args:
        zip_path: Path to the local ZIP file.
        year: Year of the data record (for registry lookup).
        month: Month of the data record (for registry lookup).
        module: Canonical module name.
        area: 'cabecera', 'resto', or 'total'.
        epoch: Epoch object with encoding/format/separator/area_filter.
        columns: Optional list of column names to keep.

    Returns:
        Raw DataFrame with original DANE column names.

    Raises:
        ParseError: If the file inside the ZIP is missing or malformed.
    """
    import pandas as pd

    # ── Shape A auto-discovery ────────────────────────────────────────────────
    # Detect by presence of 'Cabecera' filenames; bypass sources.json path lookup.
    if is_shape_a(zip_path):
        df = parse_shape_a_module(zip_path, module, epoch)
        # _area column for backward compatibility with callers that expect it.
        df["_area"] = df["CLASE"].map({1: "cabecera", 2: "resto"})
        # Area filtering via the synthetic CLASE column.
        if area == "cabecera":
            df = df[df["CLASE"] == 1].reset_index(drop=True)
        elif area == "resto":
            df = df[df["CLASE"] == 2].reset_index(drop=True)
        # Column selection (keeps CLASE and _area unless caller explicitly omits them).
        if columns is not None:
            available = [c for c in columns if c in df.columns]
            df = df[available]
        return df

    # ── Shape A lookup / Shape B ──────────────────────────────────────────────
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

    if epoch.area_filter is None:
        # Shape A lookup: explicit cabecera/resto paths from sources.json.
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
        frames: list[pd.DataFrame] = []
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

    # Shape B: single unified file with row-level area filter
    inner_path: str = module_files["file"]
    row_filter_def = module_files.get("row_filter")
    area_filter = epoch.area_filter

    # Read all columns so filter columns are available before selection
    df = _parse_fn(zip_path, inner_path, epoch, None)

    if row_filter_def is not None:
        df = df[df[row_filter_def["column"]].isin(row_filter_def["values"])]

    if area == "cabecera":
        df = df[df[area_filter.column].isin(area_filter.cabecera_values)]
    elif area == "resto":
        df = df[df[area_filter.column].isin(area_filter.resto_values)]
    # area == "total": no area filter

    df = df.reset_index(drop=True)

    if columns is not None:
        df = df[columns]

    return cast("pd.DataFrame", df)
