"""TRM (Tasa Representativa del Mercado, COP per USD) from the Superfinanciera.

Same interface as :func:`pulso.tpm`: a bundled snapshot plus a live call with
fallback. The source is the Superintendencia Financiera's dataset on
datos.gov.co (``32sa-8pi3``); the Superfinanciera is the entity that certifies
the TRM. Each certified value has a validity window (``vigenciadesde`` ..
``vigenciahasta``, e.g. Friday's value covers the weekend); the result has one
row per calendar day.
"""

from __future__ import annotations

import io
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from datetime import date

import pandas as pd
import requests

_FIXTURE_NAME = "trm_superfinanciera_20261128.csv.gz"
_FIXTURE_END = "2026-11-30"
_API_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"


def trm(
    start: str | None = None,
    end: str | None = None,
    use_fixture: bool | None = None,
) -> pd.DataFrame:
    """Fetch Colombia's TRM (COP per USD), one row per calendar day.

    Trae la TRM certificada por la Superintendencia Financiera, un registro por día.

    Parameters
    ----------
    start, end : str, optional
        Dates in YYYY-MM-DD format (inclusive).
    use_fixture : bool, optional
        None (default): try the live dataset, fall back to the bundled snapshot.
        True: always use the snapshot (no network; ends at 2026-11-30).
        False: force the live call (raises if it fails).

    Returns
    -------
    pd.DataFrame
        Columns: fecha (datetime64), valor (float64), serie (str, "trm").
    """
    from pulso._core.banrep_tpm import _validate_date

    start_d = _validate_date(start, "start") if start else None
    end_d = _validate_date(end, "end") if end else None
    if start_d and end_d and start_d > end_d:
        raise ValueError(f"start ({start_d}) must be <= end ({end_d})")

    if use_fixture is True:
        warnings.warn(
            f"Using bundled TRM snapshot (extends to {_FIXTURE_END}). "
            "Pass use_fixture=False to force a live call.",
            stacklevel=2,
        )
        return _trm_from_fixture(start_d, end_d)

    try:
        return _trm_from_api(start_d, end_d)
    except Exception as exc:
        if use_fixture is False:
            raise
        warnings.warn(
            f"TRM live call failed: {exc}. Falling back to bundled snapshot "
            f"(extends to {_FIXTURE_END}).",
            stacklevel=2,
        )
        return _trm_from_fixture(start_d, end_d)


def _fixture_path() -> Path:
    return Path(__file__).parent.parent / "ext" / _FIXTURE_NAME


def _expand_daily(windows: pd.DataFrame) -> pd.DataFrame:
    """One row per calendar day from (vigenciadesde, vigenciahasta, valor) windows."""
    if windows.empty:
        return cast("pd.DataFrame", pd.DataFrame(columns=["fecha", "valor", "serie"]))
    desde = pd.to_datetime(windows["vigenciadesde"].astype(str).str[:10], format="%Y-%m-%d")
    hasta = pd.to_datetime(windows["vigenciahasta"].astype(str).str[:10], format="%Y-%m-%d")
    valor = pd.to_numeric(windows["valor"], errors="raise").astype(float)
    parts = [
        pd.DataFrame({"fecha": pd.date_range(d, h, freq="D"), "valor": v})
        for d, h, v in zip(desde, hasta, valor, strict=True)
    ]
    out = pd.concat(parts, ignore_index=True)
    # A later certification wins if two windows ever overlap.
    out = out.drop_duplicates(subset="fecha", keep="last").sort_values("fecha")
    out["serie"] = "trm"
    return cast("pd.DataFrame", out.reset_index(drop=True))


def _filter(df: pd.DataFrame, start: date | None, end: date | None) -> pd.DataFrame:
    if start:
        df = df[df["fecha"].dt.date >= start]
    if end:
        df = df[df["fecha"].dt.date <= end]
    return cast("pd.DataFrame", df.reset_index(drop=True))


def _trm_from_fixture(start: date | None = None, end: date | None = None) -> pd.DataFrame:
    path = _fixture_path()
    if not path.exists():
        raise FileNotFoundError(f"TRM fixture not found at {path}")
    windows = pd.read_csv(path, dtype=str, compression="gzip")
    return _filter(_expand_daily(windows), start, end)


def _trm_from_api(start: date | None = None, end: date | None = None) -> pd.DataFrame:
    where = []
    if start:
        where.append(f"vigenciahasta >= '{start.isoformat()}T00:00:00'")
    if end:
        where.append(f"vigenciadesde <= '{end.isoformat()}T00:00:00'")
    params: dict[str, Any] = {
        "$select": "vigenciadesde,vigenciahasta,valor",
        "$order": "vigenciadesde",
        "$limit": 50000,
    }
    if where:
        params["$where"] = " AND ".join(where)
    r = requests.get(_API_URL, params=params, timeout=30)
    r.raise_for_status()
    windows = pd.read_json(io.StringIO(r.text), dtype=False)
    if not windows.empty and not {"vigenciadesde", "vigenciahasta", "valor"} <= set(windows):
        raise ValueError(f"Unexpected TRM response columns: {list(windows.columns)}")
    return _filter(_expand_daily(windows), start, end)
