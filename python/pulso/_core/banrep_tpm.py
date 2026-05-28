from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from datetime import date

import pandas as pd
import requests

_SDMX_NS = {"g": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic"}
_FIXTURE_NAME = "tpm_jdbr_manual_20260422.xlsx"
_API_FLOW = "ESTAT,DF_CBR_DAILY_HIST,1.0"
_BASE_URL = "https://totoro.banrep.gov.co/nsi-jax-ws/rest/data"


def tpm(
    start: str | None = None,
    end: str | None = None,
    use_fixture: bool | None = None,
) -> pd.DataFrame:
    """Fetch Colombia's Tasa de Politica Monetaria (TPM).

    Parameters
    ----------
    start : str, optional
        Start date in YYYY-MM-DD format.
    end : str, optional
        End date in YYYY-MM-DD format.
    use_fixture : bool, optional
        None (default): auto-detect -- tries API, falls back to bundled snapshot.
        True: always use bundled snapshot (no network required).
        False: force API call (raises if API is down).

    Returns
    -------
    pd.DataFrame
        Columns: fecha (datetime64), valor (float64), serie (str).
    """
    start_d = _validate_date(start, "start") if start else None
    end_d = _validate_date(end, "end") if end else None

    if start_d and end_d and start_d > end_d:
        raise ValueError(f"start ({start_d}) must be <= end ({end_d})")

    if use_fixture is None:
        use_fixture = not _banrep_api_available()

    if use_fixture:
        warnings.warn(
            "Using bundled TPM snapshot (extends to 2026-04-21). "
            "Pass use_fixture=False to force a live API call.",
            stacklevel=2,
        )
        return _tpm_from_fixture(start=start_d, end=end_d)

    try:
        return _tpm_from_api(start=start_d, end=end_d)
    except Exception as exc:
        warnings.warn(
            f"Banrep API call failed: {exc}. Falling back to bundled snapshot.",
            stacklevel=2,
        )
        return _tpm_from_fixture(start=start_d, end=end_d)


# ---------------------------------------------------------------------------
# Internal helpers (reusable for pulso_ibr in v0.2.0)
# ---------------------------------------------------------------------------


def _validate_date(date_str: str, arg_name: str) -> date:
    try:
        return pd.to_datetime(date_str).date()
    except Exception as exc:
        raise ValueError(f"{arg_name} must be a YYYY-MM-DD string, got {date_str!r}") from exc


def _banrep_api_available(timeout: float = 5.0) -> bool:
    url = f"{_BASE_URL}/{_API_FLOW}/all/ALL/?startPeriod=2025&endPeriod=2026"
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False


def _fixture_path() -> Path:
    return Path(__file__).parent.parent / "ext" / _FIXTURE_NAME


def _tpm_from_fixture(
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    path = _fixture_path()
    if not path.exists():
        raise FileNotFoundError(f"TPM fixture not found at {path}")

    # Sheet "Datos": row 0 = column headers, row 1 = units (skip via skiprows)
    # Values stored as strings with comma decimal ("3,50"), missing = "-"
    raw = pd.read_excel(
        path,
        sheet_name="Datos",
        header=0,
        skiprows=[1],  # skip the units row (index 1 after header row 0)
        dtype=str,
    )

    fecha_col = raw.iloc[:, 0]
    valor_col = raw.iloc[:, 1]  # "Tasa de politica monetaria(Dato diario)"

    fecha = pd.to_datetime(fecha_col, format="%d/%m/%Y", errors="coerce")
    valor = valor_col.str.replace(",", ".", regex=False).replace("-", float("nan")).astype(float)

    df = pd.DataFrame({"fecha": fecha, "valor": valor, "serie": "tpm"})
    df = df.dropna(subset=["fecha", "valor"]).reset_index(drop=True)

    if start:
        df = df[df["fecha"].dt.date >= start]
    if end:
        df = df[df["fecha"].dt.date <= end]

    return df.reset_index(drop=True)


def _tpm_from_api(
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    year_start = str(start.year) if start else "2010"
    # endPeriod is exclusive on year granularity; add 1 year to include target
    year_end = str(end.year + 1) if end else "2027"

    url = f"{_BASE_URL}/{_API_FLOW}/all/ALL/"
    params = {"startPeriod": year_start, "endPeriod": year_end}
    headers = {"Accept": "application/xml"}

    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()

    df = _parse_sdmx_xml(r.content, serie_name="tpm")

    if start:
        df = df[df["fecha"].dt.date >= start]
    if end:
        df = df[df["fecha"].dt.date <= end]

    return df.reset_index(drop=True)


def _parse_sdmx_xml(xml_bytes: bytes, serie_name: str) -> pd.DataFrame:
    """Generic SDMX-ML 2.1 parser -- reusable for IBR in v0.2.0."""
    root = ET.fromstring(xml_bytes)
    records = []
    for obs in root.findall(".//g:Obs", _SDMX_NS):
        dim = obs.find("g:ObsDimension", _SDMX_NS)
        val = obs.find("g:ObsValue", _SDMX_NS)
        if dim is None or val is None:
            continue
        records.append(
            {
                "fecha": dim.attrib.get("value"),
                "valor": float(val.attrib.get("value")),
            }
        )
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["fecha", "valor", "serie"])
    df["fecha"] = pd.to_datetime(df["fecha"], format="%Y%m%d")
    df["serie"] = serie_name
    return df
