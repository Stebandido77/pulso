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
from typing import TYPE_CHECKING, Any, Literal

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
    # 2020 Shape C typos: "Descupados" (2020-05), "Desoucpados" (2020-09/10).
    "desocupados": ["Desocupados", "Descupados", "Desoucpados"],
    # 2020 Shape C typos: "Ianctivos" (2020-07), "Inativos" (2020-10).
    "inactivos": ["Inactivos", "Ianctivos", "Inativos"],
    "vivienda_hogares": ["Vivienda y Hogares"],
    "otros_ingresos": ["Otros ingresos"],
    "otras_formas_trabajo": ["Otras actividades y ayudas"],
    # 2020 Shape C typo: "Fuerzo de trabajo" (2020-11).
    "fuerza_de_trabajo": ["Fuerza de trabajo", "Fuerzo de trabajo"],
}


def _matches_module_keyword(basename_lower: str, keywords: list[str]) -> bool:
    """True if *basename_lower* contains one of *keywords* as a whole word.

    The word boundary keeps "ocupados" from matching inside "desocupados".
    Optional trailing digits accept the month suffix DANE appended in
    2013-04..06 ("Cabecera - Ocupados04.csv"). Mirrors the R pattern in
    ``r/R/utils-parse.R`` (``\\b\\Qkw\\E\\d*\\b``).
    """
    return any(
        re.search(r"\b" + re.escape(kw.lower()) + r"\d*\b", basename_lower) for kw in keywords
    )


def find_shape_c_file(zip_path: Path, module: str) -> str | None:
    """Locate the single national CSV for *module* in a Shape C ZIP.

    Shape C (2020-01..12): the epoch declares Cabecera/Resto files, but DANE
    published one national file per module (``1. Enero/CSV/Ocupados.CSV``)
    that carries its own CLASE column. Mirrors ``.find_shape_c_file()`` in
    ``r/R/utils-parse.R``: first ``.csv`` member whose basename contains a
    module keyword on a word boundary.
    """
    keywords = MODULE_KEYWORDS_GEIH1.get(module, [module])
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    for name in names:
        if name.endswith("/") or not name.lower().endswith(".csv"):
            continue
        basename = name.rsplit("/", 1)[-1].lower()
        if _matches_module_keyword(basename, keywords):
            return name
    return None


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

        if not _matches_module_keyword(lower, keywords):
            continue

        if prefix == "cabecera":
            cabecera = name
        else:
            resto = name

    return cabecera, resto


def _name_key(name: str) -> str:
    """Fold cosmetic DANE filename drift into a comparison key.

    Handles non-breaking spaces (U+00A0, present since 2025-12), accents,
    letter case, repeated whitespace and the file extension (``.CSV`` vs
    ``.csv`` since 2026-08).
    """
    import unicodedata

    base = name.rsplit("/", 1)[-1].replace("\u00a0", " ")
    base = unicodedata.normalize("NFKD", base)
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", base).lower()
    return re.sub(r"[\s_]+", " ", base).strip()


# Shape B keyword index (redesigned GEIH, 2022+), matched against
# _name_key(basename). Last resolution tier, e.g. 2024-03 ships
# "CSV/No ocupado.CSV" (singular) where sources.json says "No ocupados.CSV".
# Mirrors .MODULE_KEYWORDS_GEIH2 in r/R/utils-parse.R.
MODULE_KEYWORDS_GEIH2: dict[str, str] = {
    "caracteristicas_generales": r"caracteristicas generales",
    "ocupados": r"^ocupados$",
    "desocupados": r"^no ocupados?$",
    "inactivos": r"^no ocupados?$",
    "vivienda_hogares": r"hogar y la vivienda",
    "otros_ingresos": r"^otros ingresos",
    "migracion": r"^migracion$",
    "otras_formas_trabajo": r"^otras formas de trabajo$",
    "fuerza_de_trabajo": r"^fuerza de trabajo$",
}


def _resolve_zip_path(zf: zipfile.ZipFile, path: str, module: str | None = None) -> str:
    """Resolve a ZIP member path, tolerating mojibake encoding and DANE filename drift.

    Tries in order: (1) exact match, (2) mojibake-fixed path, (3) folded
    basename match (case, accents, NBSP, extension), (4) unique member whose
    folded basename contains the folded target, for renamed files such as
    2026-04 "Capítulos de características generales ...", and (5) when
    *module* is given, the first ``.csv`` member whose folded basename
    matches ``MODULE_KEYWORDS_GEIH2[module]``. Raises KeyError if nothing
    matches.
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

    files = [n for n in names if not n.endswith("/")]
    target = _name_key(fixed)
    target_ext = fixed.rsplit(".", 1)[-1].lower() if "." in fixed.rsplit("/", 1)[-1] else ""
    # A zip can carry the same table as .csv, .dta and .sav; the key drops the
    # extension, so candidates with the requested extension must win (#78).
    same_ext = [n for n in files if n.rsplit(".", 1)[-1].lower() == target_ext]
    for pool in (same_ext, files):
        for name in pool:
            if _name_key(name) == target:
                return name

    # Containment is only safe for long, specific targets: a short key like
    # "ocupados" would also match "no ocupados".
    if len(target) >= 15:
        hits = [n for n in files if n.lower().endswith(".csv") and target in _name_key(n)]
        if len(hits) == 1:
            return hits[0]

    pattern = MODULE_KEYWORDS_GEIH2.get(module) if module is not None else None
    if pattern is not None:
        for name in files:
            if name.lower().endswith(".csv") and re.search(pattern, _name_key(name)):
                return name

    raise KeyError(f"No item named {path!r} in the archive")


# ---------------------------------------------------------------------------
# Nested ZIP support
# ---------------------------------------------------------------------------
#
# Some DANE releases wrap the actual data files inside *another* ZIP layer.
# The outer archive contains only one inner ZIP per format; the user-facing
# CSVs live inside the CSV one. The inner names drift: ``CSV.zip`` (2024-03),
# ``CSV 4.zip`` (2022-10), ``CSV 13.zip`` / ``SAV 12.zip`` (2023-09),
# ``DTA 9.zip`` (2023-04), ``DAT.zip`` (2023-08). The helpers below
# transparently descend one level so callers don't have to special-case it.

# Basename of an inner format ZIP: format tag, optional " <n>" counter, ".zip".
_NESTED_WRAPPER_RE = re.compile(r"^(CSV|DTA|DAT|SAV)( \d+)?\.zip$", re.IGNORECASE)

_FORMAT_TO_NESTED_TAGS: dict[str, tuple[str, ...]] = {
    "csv": ("CSV",),
    "dta": ("DTA", "DAT"),
    "sav": ("SAV",),
}


def _is_nested_format_wrapper(zf: zipfile.ZipFile) -> bool:
    """True when every file in the archive is an inner format ZIP.

    Detects the nested layout of 2022-10, 2023-04/08/09 and 2024-03/04,
    where DANE wraps each format (CSV, DTA/DAT, SAV) in its own inner ZIP.
    """
    names = [n for n in zf.namelist() if not n.endswith("/")]
    if not names:
        return False
    return all(_NESTED_WRAPPER_RE.match(n.rsplit("/", 1)[-1]) for n in names)


def _open_nested_zip(zf: zipfile.ZipFile, format_name: str) -> zipfile.ZipFile:
    """Open the inner format ZIP (``CSV.zip``, ``CSV 4.zip``, ...) for ``format_name``.

    Reads the nested ZIP fully into memory (DANE inner ZIPs are ~5-70 MB)
    and wraps it in a new ``ZipFile`` so the caller can use the full
    ``zipfile`` API (resolution, ``.open(...)`` member streaming).
    The caller is responsible for closing the returned object.
    """
    tags = _FORMAT_TO_NESTED_TAGS.get(format_name.lower())
    if tags is None:
        raise KeyError(
            f"No known nested wrapper for file_format={format_name!r}; "
            f"expected one of {sorted(_FORMAT_TO_NESTED_TAGS)}."
        )

    # Outer ZIP entries may live at the root or under a subfolder.
    inner_member: str | None = None
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        match = _NESTED_WRAPPER_RE.match(name.rsplit("/", 1)[-1])
        if match and match.group(1).upper() in tags:
            inner_member = name
            break
    if inner_member is None:
        raise KeyError(f"Nested ZIP for format {format_name!r} not found in outer archive.")

    with zf.open(inner_member) as fh:
        inner_bytes = fh.read()
    return zipfile.ZipFile(io.BytesIO(inner_bytes))


_DOT_DECIMAL = re.compile(rb"^-?\d+\.\d+$")
_COMMA_DECIMAL = re.compile(rb"^-?\d+,\d+$")


def _sniff_decimal(raw_bytes: bytes, sep: str, default: str) -> str:
    """Infer the decimal mark from the first data lines.

    DANE is not consistent: older files use ``;`` with comma decimals, while
    the 2018-frame files (2022+) use ``;`` with point decimals
    (``43.55418099``). ``epochs.json`` only carries one value per epoch, so
    the mark is decided from the data and the epoch value breaks ties.
    """
    if sep == ",":
        return "."
    lines = raw_bytes[:2_000_000].splitlines()[1:201]
    sep_b = sep.encode("latin-1")
    dots = commas = 0
    for line in lines:
        for field in line.split(sep_b):
            field = field.strip()
            if _DOT_DECIMAL.match(field):
                dots += 1
            elif _COMMA_DECIMAL.match(field):
                commas += 1
    if dots > commas:
        return "."
    if commas > dots:
        return ","
    return default


def _sniff_separator(raw_bytes: bytes, default: str) -> str:
    """Pick the field separator from the header line.

    The epoch separator wins when the header contains it. Otherwise a tab
    wins over a comma: the 2008 and 2011 ``Mes_txt.zip`` releases are
    tab-separated although their epoch declares ``;``. Deciding this before
    ``_sniff_decimal`` matters, because the decimal mark is counted per
    field. Mirrors the separator rule of ``.read_zip_member()`` in
    ``r/R/utils-parse.R``.
    """
    first = raw_bytes[:65536].split(b"\n", 1)[0]
    if default.encode("latin-1") in first:
        return default
    if b"\t" in first:
        return "\t"
    if b";" in first:
        return ";"
    return ","


_BOM_CHARS = ("﻿", "ï»¿")
_FEX_YEAR_SUFFIX = re.compile(r"^FEX_C_\d{4}$")


def _canon_col(name: str) -> str:
    """Comparison key for a column name: no BOM, upper case, ``FEX_C_2011`` -> ``FEX_C``.

    Used to match ``columns=`` requests against raw DANE headers, whose case
    and weight-column suffix vary by year (see ``_normalize_dane_columns``).
    """
    for bom in _BOM_CHARS:
        name = name.replace(bom, "")
    name = name.strip().upper()
    return "FEX_C" if _FEX_YEAR_SUFFIX.match(name) else name


def _read_csv_with_fallback(
    raw_bytes: bytes, epoch: Epoch, usecols: frozenset[str] | None = None
) -> pd.DataFrame:
    """Try epoch separator; if 1-column result, auto-detect. Strip BOM and normalize merge keys.

    Column normalization is intentionally narrow: BOM is stripped from all columns;
    only merge-key columns (DIRECTORIO, SECUENCIA_P, ORDEN) are uppercased.  Other
    columns (e.g. fex_c_2011) keep their original case to match variable_map.json.

    *usecols*, when given, is a set of ``_canon_col`` names: only matching
    columns are parsed (``pandas.read_csv(usecols=...)``), which saves time
    and memory on the 200-column modules.
    """
    import pandas as pd

    sep = _sniff_separator(raw_bytes, epoch.separator if epoch.separator is not None else ",")
    decimal = _sniff_decimal(raw_bytes, sep, epoch.decimal)
    keep = (lambda c: _canon_col(str(c)) in usecols) if usecols is not None else None
    buf = io.BytesIO(raw_bytes)
    df: pd.DataFrame = pd.read_csv(
        buf,
        encoding=epoch.encoding,
        sep=sep,
        decimal=decimal,
        low_memory=False,
        usecols=keep,
    )
    if df.shape[1] <= 1 and (usecols is None or len(usecols) > 1):
        buf.seek(0)
        df = pd.read_csv(
            buf,
            encoding=epoch.encoding,
            sep=None,
            engine="python",
            decimal=decimal,
            usecols=keep,
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


# GEIH-1 ships one file per labor-force condition, so every row of the
# Ocupados / Desocupados / Inactivos files is in that condition. DANE's flag
# columns (OCI / DSI / INI = 1) are missing in some releases (all three in
# 2007-01..11, INI in 2007-12); they are filled from the file so that
# condicion_actividad can be harmonized (#79). Mirrors .LABOR_FLAG_GEIH1 in
# r/R/utils-parse.R.
LABOR_FLAG_GEIH1: dict[str, str] = {"ocupados": "OCI", "desocupados": "DSI", "inactivos": "INI"}


def _ensure_labor_flag(df: pd.DataFrame, module: str) -> pd.DataFrame:
    flag = LABOR_FLAG_GEIH1.get(module)
    if flag is not None and flag not in df.columns:
        df[flag] = 1
    return df


def parse_shape_a_module(
    zip_path: Path,
    module: str,
    epoch: Epoch,
    usecols: frozenset[str] | None = None,
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
                df_cab: pd.DataFrame = _normalize_dane_columns(
                    _read_csv_with_fallback(raw, epoch, usecols)
                )
            except Exception as exc:
                raise ParseError(f"Failed to parse {cab_name!r} in {zip_path.name}: {exc}") from exc
            df_cab["CLASE"] = 1
            dfs.append(df_cab)
        if resto_name:
            with zf.open(resto_name) as fh:
                raw = fh.read()
            try:
                df_resto: pd.DataFrame = _normalize_dane_columns(
                    _read_csv_with_fallback(raw, epoch, usecols)
                )
            except Exception as exc:
                raise ParseError(
                    f"Failed to parse {resto_name!r} in {zip_path.name}: {exc}"
                ) from exc
            df_resto["CLASE"] = 2
            dfs.append(df_resto)

    out = dfs[0] if len(dfs) == 1 else pd.concat(dfs, axis=0, ignore_index=True)
    return _ensure_labor_flag(out, module)


def _merge_key_names(epoch: Epoch) -> list[str]:
    """Merge keys kept by every ``columns=`` request (epoch keys plus HOGAR).

    HOGAR is kept even where the epoch's household key does not use it, so
    the result matches R's ``.MERGE_KEY_COLUMNS`` in r/R/load.R.
    """
    keys: list[str] = []
    for k in [*epoch.merge_keys_persona, *epoch.merge_keys_hogar, "HOGAR"]:
        if k not in keys:
            keys.append(k)
    return keys


def _read_set(
    columns: list[str] | None, epoch: Epoch, extra: tuple[str, ...] = ()
) -> frozenset[str] | None:
    """``_canon_col`` names to parse for a ``columns=`` request (None = all).

    Always adds the epoch's merge keys, so a column-subset load can still be
    merged with other modules, plus *extra* (area / row-filter columns).
    """
    if columns is None:
        return None
    return frozenset(_canon_col(c) for c in [*columns, *_merge_key_names(epoch), *extra])


def _select_columns(df: pd.DataFrame, columns: list[str] | None, epoch: Epoch) -> pd.DataFrame:
    """Keep the merge keys present plus the requested *columns*, in that order.

    Names are matched with ``_canon_col`` (case, BOM and ``FEX_C_2011``
    tolerant). Requested columns absent from the file are reported in a
    UserWarning instead of raising, because a column can exist in one epoch
    and not in another.
    """
    import warnings

    if columns is None:
        return df
    by_canon: dict[str, str] = {}
    for c in df.columns:
        by_canon.setdefault(_canon_col(str(c)), c)
    keep: list[str] = []
    for c in [*_merge_key_names(epoch), *columns]:
        actual = by_canon.get(_canon_col(c))
        if actual is not None and actual not in keep:
            keep.append(actual)
    missing = [c for c in columns if _canon_col(c) not in by_canon]
    if missing:
        warnings.warn(
            f"Requested columns not found and skipped: {missing}.",
            UserWarning,
            stacklevel=4,
        )
    return df[keep]


def _parse_shape_c_module(
    zip_path: Path,
    module: str,
    area: Area,
    epoch: Epoch,
    columns: list[str] | None,
    key: str,
    usecols: frozenset[str] | None = None,
) -> pd.DataFrame:
    """Load *module* from a Shape C ZIP (one national CSV with its own CLASE).

    The area split uses the file's CLASE column (1 = cabecera, 2 = resto),
    and ``_area`` is added as in the Shape A path.

    Raises:
        ParseError: If no keyword-matching CSV exists, if it cannot be
            parsed, or if an area other than ``total`` is requested and the
            file has no CLASE column.
    """
    inner = find_shape_c_file(zip_path, module)
    if inner is None:
        with zipfile.ZipFile(zip_path) as _zf:
            sample = _zf.namelist()[:8]
        raise ParseError(
            f"Module {module!r}: no Cabecera/Resto pair and no single national "
            f"CSV found in {zip_path.name} ({key}). First entries in ZIP: {sample}"
        )
    try:
        with zipfile.ZipFile(zip_path) as zf, zf.open(inner) as fh:
            raw = fh.read()
        df = _normalize_dane_columns(_read_csv_with_fallback(raw, epoch, usecols))
    except Exception as exc:
        raise ParseError(f"Failed to parse {inner!r} in {zip_path.name}: {exc}") from exc
    df = _ensure_labor_flag(df, module)

    if "CLASE" in df.columns:
        clase = df["CLASE"].astype("string").str.strip()
        df["_area"] = clase.map({"1": "cabecera", "2": "resto"})
        if area == "cabecera":
            df = df[clase == "1"].reset_index(drop=True)
        elif area == "resto":
            df = df[clase == "2"].reset_index(drop=True)
    elif area != "total":
        raise ParseError(
            f"Module {module!r} ({key}): {inner!r} has no CLASE column, "
            f"so area={area!r} cannot be applied."
        )

    return _select_columns(df, columns, epoch)


def _parse_csv(
    zip_path: Path,
    inner_path: str,
    epoch: Epoch,
    columns: list[str] | None,
    module: str | None = None,
    usecols: frozenset[str] | None = None,
) -> pd.DataFrame:
    """Stream-read a CSV from inside a ZIP without extracting to disk.

    Lee un CSV dentro de un ZIP sin extraerlo al disco.

    Transparently handles two layouts:
        - Direct: outer ZIP contains the CSV at ``inner_path`` (with optional
          subfolder prefix and case variation, resolved by ``_resolve_zip_path``).
        - Nested wrapper: outer ZIP contains only ``CSV.zip``/``DTA.zip``/``SAV.zip``
          (and the numbered variants, see ``_NESTED_WRAPPER_RE``). In that
          case the inner CSV ZIP is opened and the CSV is resolved inside it.

    *module* enables the last resolution tier of ``_resolve_zip_path``
    (``MODULE_KEYWORDS_GEIH2``).

    Raises:
        ParseError: If the inner file is missing or malformed.
    """

    try:
        with zipfile.ZipFile(zip_path) as zf:
            if _is_nested_format_wrapper(zf):
                with _open_nested_zip(zf, "csv") as inner_zf:
                    resolved = _resolve_zip_path(inner_zf, inner_path, module)
                    with inner_zf.open(resolved) as fh:
                        raw_bytes = fh.read()
            else:
                resolved = _resolve_zip_path(zf, inner_path, module)
                with zf.open(resolved) as fh:
                    raw_bytes = fh.read()
    except KeyError as exc:
        raise ParseError(f"File {inner_path!r} not found inside {zip_path.name}.") from exc
    except Exception as exc:
        raise ParseError(f"Failed to parse {inner_path!r} in {zip_path.name}: {exc}") from exc

    try:
        df: pd.DataFrame = _read_csv_with_fallback(raw_bytes, epoch, usecols)
    except Exception as exc:
        raise ParseError(f"Failed to parse {inner_path!r} in {zip_path.name}: {exc}") from exc

    # A wide read_csv result is fragmented into one block per column (~200 on
    # the 2018 frame); copy() consolidates it so later assign()/concat calls do
    # not hit pandas' PerformanceWarning or the per-block overhead (#52).
    df = df.copy()
    return _select_columns(df, columns, epoch)


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
        df = parse_shape_a_module(zip_path, module, epoch, _read_set(columns, epoch, ("CLASE",)))
        # _area column for backward compatibility with callers that expect it.
        df["_area"] = df["CLASE"].map({1: "cabecera", 2: "resto"})
        # Area filtering via the synthetic CLASE column.
        if area == "cabecera":
            df = df[df["CLASE"] == 1].reset_index(drop=True)
        elif area == "resto":
            df = df[df["CLASE"] == 2].reset_index(drop=True)
        # Column selection: merge keys + requested columns (CLASE and _area
        # only if requested).
        return _select_columns(df, columns, epoch)

    # ── Shape A lookup / Shape B ──────────────────────────────────────────────
    sources = _load_sources()
    key = f"{year}-{month:02d}"
    record = sources["data"][key]
    module_files = record["modules"][module]

    # ── Shape C: Cabecera/Resto declared, single national file shipped ───────
    # 2020-01..12: no member starts with "Cabecera" (checked above), so the
    # declared paths cannot resolve. Mirrors the Shape C fallback of
    # .parse_module_csv() in r/R/utils-parse.R.
    if "file" not in module_files and ("cabecera" in module_files or "resto" in module_files):
        return _parse_shape_c_module(
            zip_path, module, area, epoch, columns, key, _read_set(columns, epoch, ("CLASE",))
        )

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
            return _parse_fn(zip_path, inner, epoch, columns, module, _read_set(columns, epoch))

        if area == "resto":
            inner = module_files["resto"]
            if inner is None:
                raise ParseError(f"Module {module!r} has no resto file for {key}.")
            return _parse_fn(zip_path, inner, epoch, columns, module, _read_set(columns, epoch))

        # area == "total": parse both and concatenate
        frames: list[pd.DataFrame] = []
        for label, path_key in (("cabecera", "cabecera"), ("resto", "resto")):
            inner = module_files.get(path_key)
            if inner is None:
                continue
            part = _parse_fn(zip_path, inner, epoch, columns, module, _read_set(columns, epoch))
            part["_area"] = label
            frames.append(part)

        if not frames:
            raise ParseError(f"Module {module!r} has no files for {key}.")

        return pd.concat(frames, ignore_index=True)

    # Shape B: single unified file with row-level area filter
    inner_path: str = module_files["file"]
    row_filter_def = module_files.get("row_filter")
    area_filter = epoch.area_filter

    # Parse only what the request needs, plus the filter columns.
    extra = (area_filter.column,) + ((row_filter_def["column"],) if row_filter_def else ())
    df = _parse_fn(zip_path, inner_path, epoch, None, module, _read_set(columns, epoch, extra))

    if row_filter_def is not None:
        df = df[df[row_filter_def["column"]].isin(row_filter_def["values"])]

    if area == "cabecera":
        df = df[df[area_filter.column].isin(area_filter.cabecera_values)]
    elif area == "resto":
        df = df[df[area_filter.column].isin(area_filter.resto_values)]
    # area == "total": no area filter

    df = df.reset_index(drop=True)
    return _select_columns(df, columns, epoch)


# ---------------------------------------------------------------------------
# Parsed-module cache (parquet)
# ---------------------------------------------------------------------------
#
# Bump PARSER_VERSION whenever a change in this module alters what
# parse_module returns for the same zip (columns, dtypes, rows): every cached
# parquet written by an older version is then ignored.
PARSER_VERSION = "3.0"

# Validation bookkeeping changes without changing the zip or its parse.
_VOLATILE_RECORD_FIELDS = ("validated", "validated_by", "validated_at", "notes", "scraped_at")


def parsed_cache_key(record: dict[str, Any], module: str) -> str:
    """Cache key: download URL, module, PARSER_VERSION and the period's sources.json entry.

    Validation bookkeeping fields (``_VOLATILE_RECORD_FIELDS``) are left out
    of the hash so that validating a period does not throw its cache away.
    """
    import hashlib
    import json

    entry = {k: v for k, v in record.items() if k not in _VOLATILE_RECORD_FIELDS}
    payload = json.dumps(
        {
            "url": str(record.get("download_url", "")).strip(),
            "module": module,
            "parser_version": PARSER_VERSION,
            "entry": entry,
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _apply_area(df: pd.DataFrame, area: Area, epoch: Epoch) -> pd.DataFrame:
    """Area filter on a full (area='total') parse_module result."""
    if area == "total":
        return df
    if "_area" in df.columns:  # Shape A / Shape C / Shape A lookup
        return df[df["_area"] == area].reset_index(drop=True)
    area_filter = epoch.area_filter
    if area_filter is None:
        raise ParseError(f"Cannot apply area={area!r}: no _area column and no area filter.")
    values = area_filter.cabecera_values if area == "cabecera" else area_filter.resto_values
    return df[df[area_filter.column].isin(values)].reset_index(drop=True)


def parse_module_cached(
    zip_path: Path,
    year: int,
    month: int,
    module: str,
    area: Area,
    epoch: Epoch,
    columns: list[str] | None,
    record: dict[str, Any],
    cache: bool = True,
) -> pd.DataFrame:
    """``parse_module`` with a parquet cache of the full parsed module.

    Carga el módulo desde ``<cache>/parsed/<año>/<mes>/<módulo>_<clave>.parquet``
    si existe; si no, lo parsea completo (``area='total'``, todas las columnas),
    lo guarda y aplica el área y las columnas.

    The first load parses every column (to fill the cache) and then selects;
    later loads read only the needed columns from the parquet. If the frame
    cannot be written as parquet (e.g. an object column mixing numbers and
    text), the cache is skipped and the result is the same as
    ``parse_module``. ``cache=False`` bypasses it and parses only the
    requested columns. Clear it with ``pulso.cache_clear("parsed")``.
    """
    import logging

    import pandas as pd

    from pulso._utils.cache import cache_path

    if not cache:
        return parse_module(zip_path, year, month, module, area, epoch, columns)

    logger = logging.getLogger(__name__)
    key = parsed_cache_key(record, module)
    path = cache_path() / "parsed" / str(year) / f"{month:02d}" / f"{module}_{key}.parquet"

    df: pd.DataFrame | None = None
    if path.exists():
        try:
            read_cols: list[str] | None = None
            if columns is not None:
                import pyarrow.parquet as pq

                present = pq.read_schema(path).names
                wanted = _read_set(columns, epoch, ("CLASE", "_area"))
                extra = [epoch.area_filter.column] if epoch.area_filter is not None else []
                read_cols = [c for c in present if _canon_col(c) in (wanted or set()) or c in extra]
            df = pd.read_parquet(path, columns=read_cols)
        except Exception as exc:  # corrupt or unreadable cache: re-parse
            logger.warning("Ignoring unreadable parsed cache %s: %s", path, exc)
            path.unlink(missing_ok=True)
            df = None

    if df is None:
        df = parse_module(zip_path, year, month, module, "total", epoch, None)
        tmp = path.with_suffix(".parquet.tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(tmp, index=False)
            tmp.replace(path)
        except Exception as exc:  # not representable as parquet: no cache
            logger.debug("Not caching %s %d-%02d as parquet: %s", module, year, month, exc)
            tmp.unlink(missing_ok=True)

    return _select_columns(_apply_area(df, area, epoch), columns, epoch)
