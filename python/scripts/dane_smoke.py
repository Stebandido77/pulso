"""Weekly smoke test of pulso (Python) against the live DANE portal.

Smoke test semanal: descarga del DANE real un periodo y verifica que los
módulos se lean bien. Lo usa ``.github/workflows/dane_smoke.yml``.

Checks per (period, module):
    * more than 1000 rows;
    * ``FEX_C18`` present and numeric;
    * no mojibake (``Ã`` or U+FFFD) in column names nor in a sample of text values.

Every failure is written literally (error type + message) to ``--failures``
as Markdown, so the workflow can paste it into the ``dane-format-change`` issue.

Usage:
    python python/scripts/dane_smoke.py --period latest
    python python/scripts/dane_smoke.py --period 2024-03 --modules ocupados vivienda_hogares
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_PATH = REPO_ROOT / "data" / "sources.json"
DEFAULT_MODULES = ("ocupados", "vivienda_hogares")
MIN_ROWS = 1000
MOJIBAKE = ("Ã", "�")
SAMPLE_ROWS = 500


def resolve_period(spec: str, sources_path: Path = SOURCES_PATH) -> str:
    if spec != "latest":
        return spec
    data = json.loads(sources_path.read_text(encoding="utf-8"))["data"]
    return max(data)


def check_frame(df: Any) -> list[str]:
    """Return the list of failed assertions for one loaded module (empty = OK)."""
    import pandas as pd

    problems: list[str] = []
    if len(df) <= MIN_ROWS:
        problems.append(f"expected more than {MIN_ROWS} rows, got {len(df)}")
    if "FEX_C18" not in df.columns:
        problems.append(f"FEX_C18 column missing; first columns: {list(df.columns[:10])}")
    elif not pd.api.types.is_numeric_dtype(df["FEX_C18"]):
        problems.append(f"FEX_C18 is not numeric (dtype={df['FEX_C18'].dtype})")
    bad_cols = [str(c) for c in df.columns if any(m in str(c) for m in MOJIBAKE)]
    if bad_cols:
        problems.append(f"mojibake in column names: {bad_cols[:10]}")
    sample = df.head(SAMPLE_ROWS)
    for col in sample.columns:
        if pd.api.types.is_numeric_dtype(sample[col]):
            continue
        values = sample[col].dropna().astype(str)
        hits = values[values.str.contains("|".join(MOJIBAKE), regex=True)]
        if not hits.empty:
            problems.append(f"mojibake in values of {col!r}: {hits.iloc[0]!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--period", default="latest", help="YYYY-MM or 'latest'.")
    parser.add_argument("--modules", nargs="+", default=list(DEFAULT_MODULES))
    parser.add_argument("--failures", type=Path, default=Path("smoke_failures.md"))
    args = parser.parse_args(argv)

    import pulso

    period = resolve_period(args.period)
    year, month = int(period[:4]), int(period[5:])
    failures: list[str] = []
    for module in args.modules:
        try:
            df = pulso.load(year, month, module, show_progress=False)
            problems = check_frame(df)
        except Exception as exc:  # report every load failure literally
            problems = ["".join(traceback.format_exception_only(type(exc), exc)).strip()]
        status = "OK" if not problems else "FAIL"
        print(f"[python] {period} {module}: {status}")
        for p in problems:
            print(f"    {p}")
            failures.append(f"- **python** `{period}` `{module}`:\n\n  ```\n  {p}\n  ```")

    if failures:
        header = f"Smoke test (Python, pulso-co {pulso.__version__}) failed for {period}.\n\n"
        args.failures.write_text(header + "\n".join(failures) + "\n", encoding="utf-8")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
