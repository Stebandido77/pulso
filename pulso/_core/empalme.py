"""Empalme loader: annual GEIH Empalme datasets (2010-2020).

Shape C (Empalme): each annual ZIP contains 12 monthly sub-ZIPs structured as
    <NN>. <Mes>/CSV/<ModuleName>.CSV
No Cabecera/Resto split — unified nationwide CSV per module.
Year range: 2010-2020.  Years 2010-2019 are downloadable; 2020 exists in DANE
catalog but the ZIP has not been published.
"""

from __future__ import annotations

import importlib.resources
import json
import logging
import re
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from pulso._config.epochs import get_epoch
from pulso._core.parser import MODULE_KEYWORDS_GEIH1, _read_csv_with_fallback
from pulso._utils.cache import cache_path
from pulso._utils.columns import _normalize_dane_columns
from pulso._utils.exceptions import DataNotAvailableError, DownloadError, ParseError

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)

# ── Public range constants (imported by loader.py) ──────────────────────────
EMPALME_YEAR_MIN: int = 2010
EMPALME_YEAR_MAX: int = 2020
EMPALME_DOWNLOADABLE_MAX: int = 2019

_SPANISH_MONTHS: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


# ── Registry helpers ─────────────────────────────────────────────────────────


def _load_empalme_registry() -> dict:
    """Load empalme_sources.json from the package data directory."""
    data = importlib.resources.files("pulso") / "data" / "empalme_sources.json"
    with data.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _get_empalme_entry(year: int) -> dict:
    """Return the registry entry for *year*, validating range and downloadable status.

    Raises:
        ValueError: year is outside EMPALME_YEAR_MIN..EMPALME_YEAR_MAX.
        DataNotAvailableError: year is in range but ZIP has not been published (2020).
    """
    if year < EMPALME_YEAR_MIN or year > EMPALME_YEAR_MAX:
        raise ValueError(
            f"Empalme data is only available for years {EMPALME_YEAR_MIN}-{EMPALME_YEAR_MAX}. "
            f"Got {year}."
        )
    registry = _load_empalme_registry()
    entry = registry["data"][str(year)]
    if not entry["downloadable"]:
        raise DataNotAvailableError(
            year,
            0,
            hint=(
                f"The Empalme ZIP for {year} has not been published by DANE. "
                f"See https://microdatos.dane.gov.co/index.php/catalog/{entry['catalog_id']}."
            ),
        )
    return entry


# ── Download ─────────────────────────────────────────────────────────────────


def download_empalme_zip(year: int, show_progress: bool = True) -> Path:
    """Download (or retrieve from cache) the annual Empalme ZIP for *year*.

    Cache location: ``~/.cache/pulso/empalme/{year}.zip``

    Raises:
        ValueError: year out of empalme range.
        DataNotAvailableError: year=2020 (ZIP not published).
        DownloadError: network failure.
    """
    entry = _get_empalme_entry(year)

    dest = cache_path() / "empalme" / f"{year}.zip"

    if dest.exists():
        logger.debug("Empalme %d: using cached file %s", year, dest)
        return dest

    url: str = entry["download_url"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")

    logger.info("Downloading Empalme %d from %s", year, url)
    try:
        response = requests.get(url, stream=True, timeout=120, headers={"User-Agent": "pulso/1.0"})
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0)) or None
        if show_progress:
            from tqdm import tqdm

            with (
                tmp.open("wb") as f,
                tqdm(total=total, unit="B", unit_scale=True, desc=f"empalme-{year}") as bar,
            ):
                for chunk in response.iter_content(chunk_size=65536):
                    f.write(chunk)
                    bar.update(len(chunk))
        else:
            with tmp.open("wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    f.write(chunk)
    except requests.RequestException as exc:
        if tmp.exists():
            tmp.unlink()
        raise DownloadError(f"Download failed for Empalme {year}: {exc}") from exc

    tmp.replace(dest)
    return dest


# ── Shape C parsing helpers ───────────────────────────────────────────────────


def _normalize_empalme_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize Empalme CSV columns. Delegates to shared _normalize_dane_columns."""
    return _normalize_dane_columns(df)


def _detect_month_from_name(name: str) -> int | None:
    """Extract month number from a sub-ZIP name like '6. Junio.zip'.

    Handles both bare filenames and paths with directory prefixes.
    Returns None if no Spanish month name is found.
    """
    basename = name.rsplit("/", 1)[-1] if "/" in name else name
    lower = basename.lower()
    for month_name, month_num in _SPANISH_MONTHS.items():
        if month_name in lower:
            return month_num
    return None


def _find_empalme_module_csv(zf: zipfile.ZipFile, module: str) -> str | None:
    """Find the CSV for *module* inside a Shape C (Empalme) sub-ZIP.

    Uses word-boundary keyword matching from MODULE_KEYWORDS_GEIH1, consistent
    with the Shape A parser's find_shape_a_files logic.
    """
    keywords = MODULE_KEYWORDS_GEIH1.get(module, [module])
    for name in zf.namelist():
        if not name.lower().endswith(".csv"):
            continue
        basename = name.rsplit("/", 1)[-1] if "/" in name else name
        lower = basename.lower()
        if any(re.search(r"\b" + re.escape(kw.lower()) + r"\b", lower) for kw in keywords):
            return name
    return None


def _parse_empalme_module(inner_zip_path: Path, module: str) -> pd.DataFrame:
    """Parse one module from a Shape C (Empalme) monthly sub-ZIP.

    Shape C: unified nationwide CSV at ``<NN>. <Mes>/CSV/<ModuleName>.CSV``.
    No Cabecera/Resto split.  Column names are normalized via
    _normalize_empalme_columns so the rest of the pipeline sees uppercase names
    and the canonical FEX_C weight column.
    """
    epoch = get_epoch("geih_2006_2020")
    with zipfile.ZipFile(inner_zip_path) as zf:
        csv_name = _find_empalme_module_csv(zf, module)
        if csv_name is None:
            raise ParseError(
                f"Module {module!r} not found in {inner_zip_path.name}. "
                f"Available CSVs: {[n for n in zf.namelist() if n.lower().endswith('.csv')]}"
            )
        with zf.open(csv_name) as fh:
            raw_bytes = fh.read()
    df = _read_csv_with_fallback(raw_bytes, epoch)
    return _normalize_empalme_columns(df)


def _apply_area_filter(df: pd.DataFrame, area: str) -> pd.DataFrame:
    """Filter *df* by area using CLASE column if present.

    Empalme CSVs are unified (no Cabecera/Resto split) but may contain a CLASE
    column (urban=1/2, rural=3+).  If absent, area filtering is skipped with a
    debug log.
    """
    if area == "total":
        return df
    if "CLASE" not in df.columns:
        logger.debug("CLASE column not found in empalme DataFrame; area filter '%s' skipped.", area)
        return df
    if area == "cabecera":
        return df[df["CLASE"] == 1].reset_index(drop=True)
    if area == "resto":
        return df[df["CLASE"].isin([2, 3])].reset_index(drop=True)
    return df


# ── Internal: single-month merged for apply_smoothing ────────────────────────


def _load_empalme_month_merged(
    year: int,
    month: int,
    area: str = "total",
    harmonize: bool = True,
    variables: list[str] | None = None,
) -> pd.DataFrame:
    """Load one empalme month, all modules merged.  Used by the apply_smoothing path.

    Downloads the annual ZIP (uses cache) and extracts only the requested
    month's sub-ZIP to a temp file — the other 11 months' bytes are never read.

    Raises:
        ParseError: sub-ZIP for *month* not found, or all modules fail to parse.
    """
    from pulso._core.harmonizer import harmonize_dataframe
    from pulso._core.merger import merge_modules

    epoch = get_epoch("geih_2006_2020")
    zip_path = download_empalme_zip(year)

    # Extract only the target month's bytes from the outer ZIP.
    inner_bytes: bytes | None = None
    with zipfile.ZipFile(zip_path) as outer_zf:
        for inner_name in outer_zf.namelist():
            if inner_name.lower().endswith(".zip") and _detect_month_from_name(inner_name) == month:
                inner_bytes = outer_zf.read(inner_name)
                break

    if inner_bytes is None:
        raise ParseError(f"No sub-ZIP found for month {month} in Empalme {year} ({zip_path.name}).")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(inner_bytes)
        tmp_path = Path(tmp.name)

    try:
        module_dfs: dict[str, pd.DataFrame] = {}
        for mod_name in MODULE_KEYWORDS_GEIH1:
            try:
                df = _parse_empalme_module(tmp_path, mod_name)
                df = _apply_area_filter(df, area)
                module_dfs[mod_name] = df
            except Exception as exc:
                logger.debug("Empalme %d-%02d: skipping module %r — %s", year, month, mod_name, exc)

        if not module_dfs:
            raise ParseError(f"No modules could be parsed for Empalme {year}-{month:02d}.")

        merged = merge_modules(module_dfs, epoch, level="persona", how="outer")
    finally:
        tmp_path.unlink(missing_ok=True)

    if harmonize:
        merged = harmonize_dataframe(merged, epoch, variables=variables)

    return merged


# ── Public API ────────────────────────────────────────────────────────────────


def load_empalme(
    year: int,
    module: str | None = None,
    area: str = "total",
    harmonize: bool = True,
) -> pd.DataFrame:
    """Load all 12 months of GEIH Empalme data for *year*, stacked vertically.

    Args:
        year: Year in 2010-2019.  2020 raises DataNotAvailableError (ZIP not
            published); years outside 2010-2020 raise ValueError.
        module: Canonical module name to load alone (e.g. ``'ocupados'``).
            If None, all available modules are loaded and merged at persona level.
        area: ``'cabecera'``, ``'resto'``, or ``'total'``.
        harmonize: If True, apply variable_map.json transforms.

    Returns:
        DataFrame with all 12 months stacked.  ``year`` and ``month`` columns
        are always added.

    Raises:
        ValueError: year outside 2010-2020.
        DataNotAvailableError: year=2020 (ZIP not published by DANE).
        DownloadError: network failure.
        ParseError: cannot parse a module from the sub-ZIP.
    """
    import pandas as pd

    from pulso._core.harmonizer import harmonize_dataframe
    from pulso._core.merger import merge_modules

    # Validate (raises ValueError or DataNotAvailableError before touching network)
    _get_empalme_entry(year)

    epoch = get_epoch("geih_2006_2020")
    zip_path = download_empalme_zip(year)

    frames: list[pd.DataFrame] = []

    # Build (inner_name, month) index in one pass without reading all bytes.
    with zipfile.ZipFile(zip_path) as outer_zf:
        inner_entries = [
            (n, _detect_month_from_name(n))
            for n in sorted(outer_zf.namelist())
            if n.lower().endswith(".zip")
        ]

    for inner_name, detected_month in inner_entries:
        if detected_month is None:
            logger.warning("Cannot detect month from sub-ZIP name: %r — skipping.", inner_name)
            continue

        # Re-open the outer ZIP for each sub-ZIP to avoid holding it open during
        # the (potentially slow) parse step.
        with zipfile.ZipFile(zip_path) as outer_zf:
            inner_bytes = outer_zf.read(inner_name)

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(inner_bytes)
            tmp_path = Path(tmp.name)

        try:
            if module is not None:
                df = _parse_empalme_module(tmp_path, module)
                df = _apply_area_filter(df, area)
                if harmonize:
                    df = harmonize_dataframe(df, epoch)
            else:
                module_dfs: dict[str, pd.DataFrame] = {}
                for mod_name in MODULE_KEYWORDS_GEIH1:
                    try:
                        mod_df = _parse_empalme_module(tmp_path, mod_name)
                        mod_df = _apply_area_filter(mod_df, area)
                        module_dfs[mod_name] = mod_df
                    except Exception as exc:
                        logger.debug(
                            "Empalme %d-%02d: skipping module %r — %s",
                            year,
                            detected_month,
                            mod_name,
                            exc,
                        )
                if not module_dfs:
                    logger.warning(
                        "No modules parsed for Empalme %d-%02d — month skipped.",
                        year,
                        detected_month,
                    )
                    continue
                df = merge_modules(module_dfs, epoch, level="persona", how="outer")
                if harmonize:
                    df = harmonize_dataframe(df, epoch)
        finally:
            tmp_path.unlink(missing_ok=True)

        frames.append(df.assign(year=year, month=detected_month))

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
