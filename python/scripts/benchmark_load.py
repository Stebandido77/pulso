"""Benchmark ``pulso.load`` for one period/module: wall time and peak memory.

Mide ``pulso.load`` en un periodo y módulo: tiempo de reloj y pico de memoria.

Each measurement runs in a fresh Python process, so a "second load" is what a
user gets when re-running a script: the downloaded zip and (since v3) the
parsed-module parquet cache are on disk, nothing is in memory.

* ``first``: the zip is in the raw cache; the parsed cache is cleared first.
* ``second``: run right after ``first``, with whatever cache it left behind.

Peak memory is ``tracemalloc``'s peak (Python and NumPy allocations made
during the call), in MiB. The download is excluded: the zip is fetched once
before timing.

Usage:
    python python/scripts/benchmark_load.py --year 2026 --month 9 --module ocupados
    python python/scripts/benchmark_load.py --columns DIRECTORIO,SECUENCIA_P,ORDEN,P6500 --repeat 3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PYTHON_DIR = Path(__file__).resolve().parents[1]

_CHILD = r"""
import json, sys, time, tracemalloc, warnings
warnings.simplefilter("ignore")
import pulso
args = json.loads(sys.argv[1])
kwargs = {"harmonize": False, "show_progress": False}
if args["columns"]:
    kwargs["columns"] = args["columns"]
tracemalloc.start()
t0 = time.perf_counter()
df = pulso.load(args["year"], args["month"], args["module"], **kwargs)
elapsed = time.perf_counter() - t0
_, peak = tracemalloc.get_traced_memory()
print(json.dumps({"seconds": elapsed, "peak_mib": peak / 2**20, "rows": len(df),
                  "cols": df.shape[1]}))
"""


def _run_child(payload: dict[str, object]) -> dict[str, float]:
    out = subprocess.run(
        [sys.executable, "-c", _CHILD, json.dumps(payload)],
        cwd=PYTHON_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])  # type: ignore[no-any-return]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=9)
    parser.add_argument("--module", default="ocupados")
    parser.add_argument("--columns", default=None, help="Comma-separated column list.")
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(PYTHON_DIR))
    from pulso._core.downloader import download_zip
    from pulso._utils.cache import cache_clear

    download_zip(args.year, args.month, show_progress=False, allow_unvalidated=True)
    payload = {
        "year": args.year,
        "month": args.month,
        "module": args.module,
        "columns": args.columns.split(",") if args.columns else None,
    }
    print(f"pulso.load({args.year}, {args.month}, {args.module!r}, columns={payload['columns']})")
    print("run  carga    segundos  pico_MiB  filas  columnas")
    for i in range(1, args.repeat + 1):
        cache_clear("parsed")
        for label in ("first", "second"):
            r = _run_child(payload)
            print(
                f"{i:>3}  {label:<7} {r['seconds']:>8.2f}  {r['peak_mib']:>8.1f}"
                f"  {r['rows']:>5}  {r['cols']:>8}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
