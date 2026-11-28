"""Real income: DANE's CPI (IPC), the legal minimum wage and deflation.

Ingresos reales: el IPC del DANE (base diciembre 2018 = 100), el salario mínimo
legal por año y la conversión de pesos corrientes a pesos de un mes de referencia.

The IPC follows the interface of :func:`pulso.tpm`: a bundled snapshot
(``ipc_dane_indices_202610.csv``, 2003-01..2026-10, from DANE's
``anex-IPC-Indices-oct2026.xlsx``) plus a live download of the newest
``anex-IPC-Indices-<mes><año>.xlsx`` linked from DANE's IPC page.
"""

from __future__ import annotations

import io
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    import pandas as pd

_EXT = Path(__file__).parent.parent / "ext"
_IPC_FIXTURE = "ipc_dane_indices_202610.csv"
_IPC_FIXTURE_END = "2026-10"
_SMMLV_FILE = "salario_minimo.csv"
_DANE = "https://www.dane.gov.co"
_IPC_PAGE = (
    f"{_DANE}/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc"
)
_MESES = {
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


def ipc(use_fixture: bool | None = None) -> pd.DataFrame:
    """DANE's monthly CPI index (IPC total, base December 2018 = 100).

    Índice de precios al consumidor del DANE, mensual.

    Args:
        use_fixture: None (default) tries DANE's newest annex and falls back
            to the bundled snapshot (ends 2026-10); True always uses the
            snapshot; False forces the download (raises if it fails).

    Returns:
        DataFrame with ``periodo`` ('YYYY-MM'), ``anio``, ``mes``, ``indice``.
    """
    if use_fixture is True:
        return _ipc_from_fixture()
    try:
        return _ipc_from_dane()
    except Exception as exc:
        if use_fixture is False:
            raise
        warnings.warn(
            f"DANE IPC download failed: {exc}. Falling back to bundled snapshot "
            f"(extends to {_IPC_FIXTURE_END}).",
            stacklevel=2,
        )
        return _ipc_from_fixture()


def _finish(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["anio", "mes"]).reset_index(drop=True)
    df.insert(0, "periodo", [f"{a}-{m:02d}" for a, m in zip(df["anio"], df["mes"], strict=True)])
    return df


def _ipc_from_fixture() -> pd.DataFrame:
    import pandas as pd

    return _finish(pd.read_csv(_EXT / _IPC_FIXTURE))


def parse_ipc_annex(content: bytes) -> pd.DataFrame:
    """Parse DANE's ``anex-IPC-Indices-*.xlsx`` (sheet with a 'Mes' x years table)."""
    import openpyxl
    import pandas as pd

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    header = next(i for i, r in enumerate(rows) if r and str(r[0]).strip() == "Mes")
    years = [int(str(v)) for v in rows[header][1:] if v is not None]
    out = []
    for r in rows[header + 1 : header + 13]:
        mes = _MESES[str(r[0]).strip().lower()]
        for anio, v in zip(years, r[1 : 1 + len(years)], strict=False):
            if v not in (None, ""):
                out.append({"anio": anio, "mes": mes, "indice": float(v)})
    return _finish(pd.DataFrame(out))


def _ipc_from_dane() -> pd.DataFrame:
    import requests

    headers = {"User-Agent": "Mozilla/5.0 (compatible; pulso)"}
    page = requests.get(_IPC_PAGE, headers=headers, timeout=30)
    page.raise_for_status()
    links = re.findall(
        r'href="(/files/operaciones/IPC/[a-z]{3}\d{4}/anex-IPC-Indices-[a-z]{3}\d{4}\.xlsx)"',
        page.text,
    )
    if not links:
        raise RuntimeError("no anex-IPC-Indices-<mes><año>.xlsx link on DANE's IPC page")
    r = requests.get(_DANE + links[0], headers=headers, timeout=60)
    r.raise_for_status()
    return parse_ipc_annex(r.content)


def salario_minimo() -> pd.DataFrame:
    """Monthly legal minimum wage (SMMLV) by year, with the decree that set it.

    Salario mínimo mensual legal vigente por año (sin auxilio de transporte),
    con el decreto y la página oficial donde se verificó (Gestor Normativo de
    Función Pública; 2026 en el normograma del MinTIC).
    """
    import pandas as pd

    return pd.read_csv(_EXT / _SMMLV_FILE)


def deflactar(
    df: pd.DataFrame,
    columns: list[str],
    deflate_to: str,
    periodo_col: str = "periodo",
    ipc_table: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Add ``<col>_real`` columns in pesos of the ``deflate_to`` month.

    ``real = nominal * IPC(deflate_to) / IPC(periodo of the row)``.

    Args:
        df: Data with a ``periodo`` ('YYYY-MM') column, e.g. from
            :func:`pulso.load_range`.
        columns: Nominal peso columns to deflate (non-numeric values -> NaN).
        deflate_to: Reference month 'YYYY-MM'.
        periodo_col: Name of the period column.
        ipc_table: Optional output of :func:`ipc`; defaults to ``ipc()``.

    Raises:
        KeyError: if a period or ``deflate_to`` is not in the IPC table.
    """
    import pandas as pd

    table = ipc_table if ipc_table is not None else ipc()
    index = dict(zip(table["periodo"], table["indice"], strict=True))
    if deflate_to not in index:
        raise KeyError(
            f"deflate_to {deflate_to!r} is not in the IPC table (last: {table['periodo'].max()})."
        )
    missing = sorted(set(df[periodo_col]) - set(index))
    if missing:
        raise KeyError(f"No IPC for periods {missing}.")
    factor = index[deflate_to] / df[periodo_col].map(index)
    out = df.copy()
    for col in columns:
        out[f"{col}_real"] = pd.to_numeric(out[col], errors="coerce") * factor
    return cast("pd.DataFrame", out)
