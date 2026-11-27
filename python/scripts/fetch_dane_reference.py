"""Download DANE's official labor-market annexes and extract national monthly TD/TO/TGP.

Descarga los anexos oficiales de mercado laboral de la GEIH y extrae la serie
mensual del Total Nacional (TD, TO, TGP) a ``data/reference/dane_labor_indicators.csv``.

Why two annexes
---------------
DANE's *current* annex (``anex-GEIH-<mes><año>.xlsx``, sheet "Total nacional")
publishes 2001-2020 **retro-projected to the 2018 census frame** with PET = 15+.
The pulso catalog serves 2007-2021 microdata on the **2005 frame**
(``fex_c_2011``, PET = 12+ urban / 10+ rural), so those months are only
comparable with the last annex DANE published on the 2005 frame:
``anexo_empleo_dic_21.xlsx`` (sheet "Tnal mensual", "Datos expandidos con
proyecciones de población, elaboradas con base en los resultados del censo
2005"). Each epoch is therefore compared with the annex built on its own frame.
The epoch date ranges come from ``data/epochs.json``.

Usage:
    python python/scripts/fetch_dane_reference.py
    python python/scripts/fetch_dane_reference.py --current-url URL
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
import unicodedata
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "reference" / "dane_labor_indicators.csv"
EPOCHS_PATH = REPO_ROOT / "data" / "epochs.json"

DANE_BASE = "https://www.dane.gov.co"
CURRENT_LISTING_URL = (
    f"{DANE_BASE}/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo"
)
HISTORICAL_2005_FRAME_URL = (
    f"{DANE_BASE}/files/investigaciones/boletines/ech/ech/anexo_empleo_dic_21.xlsx"
)
USER_AGENT = "Mozilla/5.0 (compatible; pulso-maintenance)"

MONTHS_ES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

FIELDS = ["period", "td", "to", "tgp", "source_url", "retrieved_at"]


@dataclass(frozen=True)
class AnnexSpec:
    """Where to find the national monthly block inside one annex workbook."""

    epoch: str
    url: str
    sheet: str


def _norm(text: Any) -> str:
    """Lowercase, strip accents and collapse whitespace."""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def classify_label(label: Any) -> str | None:
    """Map an annex row label to 'tgp' / 'to' / 'td', or None.

    Handles both vocabularies: 2005 frame ("TGP", "TO", "TD") and the
    redesigned annex ("Tasa Global de Participación (TGP)", ...). Sub-rates
    such as "T.D. Abierto" or "Tasa de Subocupación" return None.
    """
    if label is None:
        return None
    s = _norm(label)
    if s in {"tgp", "to", "td"}:
        return s
    if s.startswith("tasa global de participacion"):
        return "tgp"
    if s.startswith("tasa de ocupacion"):
        return "to"
    if s.startswith(("tasa de desocupacion", "tasa de desempleo")):
        return "td"
    return None


def parse_national_block(rows: list[tuple[Any, ...]]) -> dict[str, dict[str, float]]:
    """Parse the first 'Concepto' block of a national monthly sheet.

    Layout (both annex generations): a row whose first cell is 'Concepto'
    carries the year in the first column of each 12-month run; the next row
    carries month abbreviations ('Ene'..'Dic'); then indicator rows follow
    until a blank first cell.

    Returns ``{"YYYY-MM": {"td": .., "to": .., "tgp": ..}}``.
    """
    header_idx = next(
        (i for i, r in enumerate(rows) if r and _norm(r[0]) == "concepto"),
        None,
    )
    if header_idx is None:
        raise ValueError("No 'Concepto' header row found in sheet.")
    years_row, months_row = rows[header_idx], rows[header_idx + 1]

    columns: dict[int, str] = {}
    year: int | None = None
    for j in range(1, len(years_row)):
        y = years_row[j]
        if y is not None and str(y).strip() not in ("", "Concepto"):
            year = int(float(str(y).strip()))
        m = months_row[j] if j < len(months_row) else None
        if m is None or year is None:
            continue
        key = _norm(m).rstrip(".*")[:3]
        if key in MONTHS_ES:
            columns[j] = f"{year:04d}-{MONTHS_ES[key]:02d}"

    out: dict[str, dict[str, float]] = {}
    for r in rows[header_idx + 2 :]:
        if not r or r[0] is None or str(r[0]).strip() == "":
            break
        indicator = classify_label(r[0])
        if indicator is None:
            continue
        for j, period in columns.items():
            v = r[j] if j < len(r) else None
            if v is None or str(v).strip() == "":
                continue
            out.setdefault(period, {})[indicator] = float(v)
    complete = {p: v for p, v in out.items() if {"td", "to", "tgp"} <= v.keys()}
    if not complete:
        raise ValueError("Found the header but no TD/TO/TGP rows.")
    return complete


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return bytes(resp.read())


def discover_current_annex_url(listing_html: str) -> str:
    """Return the most recent ``anex-GEIH-<mes><año>.xlsx`` link on DANE's page."""
    pattern = re.compile(r'href="(/files/operaciones/GEIH/anex-GEIH-([a-z]{3})(\d{4})\.xlsx)"')
    best: tuple[int, int, str] | None = None
    for path, mon, year in pattern.findall(listing_html):
        if mon not in MONTHS_ES:
            continue
        cand = (int(year), MONTHS_ES[mon], path)
        if best is None or cand > best:
            best = cand
    if best is None:
        raise RuntimeError(f"No anex-GEIH-<mes><año>.xlsx link found at {CURRENT_LISTING_URL}")
    return DANE_BASE + best[2]


def read_sheet_rows(content: bytes, sheet: str) -> list[tuple[Any, ...]]:
    import openpyxl  # optional dependency: pip install "pulso-co[validation]"

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    names = {_norm(n): n for n in wb.sheetnames}
    if _norm(sheet) not in names:
        raise ValueError(f"Sheet {sheet!r} not in workbook; found {wb.sheetnames}")
    ws = wb[names[_norm(sheet)]]
    return [tuple(r) for r in ws.iter_rows(values_only=True)]


def epoch_ranges(epochs_path: Path = EPOCHS_PATH) -> dict[str, tuple[str, str | None]]:
    data = json.loads(epochs_path.read_text(encoding="utf-8"))
    return {k: (v["date_range"][0], v["date_range"][1]) for k, v in data["epochs"].items()}


def build_reference(
    specs: list[AnnexSpec],
    ranges: dict[str, tuple[str, str | None]],
    fetch: Any = _http_get,
    now: dt.datetime | None = None,
) -> list[dict[str, Any]]:
    """Fetch every annex and keep, for each one, only its own epoch's months."""
    retrieved = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: dict[str, dict[str, Any]] = {}
    for spec in specs:
        lo, hi = ranges[spec.epoch]
        series = parse_national_block(read_sheet_rows(fetch(spec.url), spec.sheet))
        for period, vals in series.items():
            if period < lo or (hi is not None and period > hi):
                continue
            rows[period] = {
                "period": period,
                "td": round(vals["td"], 6),
                "to": round(vals["to"], 6),
                "tgp": round(vals["tgp"], 6),
                "source_url": spec.url,
                "retrieved_at": retrieved,
            }
    return [rows[p] for p in sorted(rows)]


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--current-url",
        default=None,
        help="Current annex URL. Default: newest anex-GEIH-*.xlsx on DANE's page.",
    )
    parser.add_argument("--historical-url", default=HISTORICAL_2005_FRAME_URL)
    args = parser.parse_args(argv)

    current = args.current_url or discover_current_annex_url(
        _http_get(CURRENT_LISTING_URL).decode("utf-8", errors="replace")
    )
    specs = [
        AnnexSpec("geih_2006_2020", args.historical_url, "Tnal mensual"),
        AnnexSpec("geih_2021_present", current, "Total nacional"),
    ]
    rows = build_reference(specs, epoch_ranges())
    write_csv(rows, args.output)
    for spec in specs:
        n = sum(1 for r in rows if r["source_url"] == spec.url)
        print(f"{spec.epoch}: {n} meses desde {spec.url}")
    print(f"Escrito {args.output} ({len(rows)} filas, {rows[0]['period']}..{rows[-1]['period']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
