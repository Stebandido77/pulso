"""Benchmark ``pulso.load`` for one period/module: wall time and peak memory.

Mide ``pulso.load`` en un periodo y módulo: tiempo de reloj y pico de memoria.

Each measurement runs in a fresh Python process, so a "second load" is what a
user gets when re-running a script: the downloaded zip and (since v3) the
parsed-module parquet cache are on disk, nothing is in memory.

* ``first``: the zip is in the raw cache; the parsed cache is cleared first.
* ``second``: run right after ``first``, with whatever cache it left behind.

Peak memory is the growth of the process's resident memory during the call
(working set on Windows, ``/proc/self/statm`` on Linux), sampled every 2 ms,
in MiB, so it includes what pyarrow allocates outside Python. The download is excluded:
the zip is fetched once before timing. ``--no-cache`` passes ``cache=False``
(no parquet cache; ``columns=`` is then parsed with ``usecols``).

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
import json, sys, time, warnings
warnings.simplefilter("ignore")


def rss_bytes():
    # Current resident memory of this process, including memory that
    # pyarrow/NumPy allocate outside Python's allocator.
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
        k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
        # Explicit signatures: without them the 64-bit handle is truncated.
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            raise OSError("GetProcessMemoryInfo failed")
        return pmc.WorkingSetSize
    with open("/proc/self/statm") as fh:
        import os
        return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")


import threading
peak = [0]
stop = threading.Event()


def sampler():
    while not stop.is_set():
        peak[0] = max(peak[0], rss_bytes())
        stop.wait(0.002)


import pulso
import pandas, pyarrow.parquet  # noqa: F401  (imports outside the measurement)
args = json.loads(sys.argv[1])
kwargs = {"harmonize": False, "show_progress": False, "cache": args["cache"]}
if args["columns"]:
    kwargs["columns"] = args["columns"]
base = rss_bytes()
peak[0] = base
t = threading.Thread(target=sampler, daemon=True)
t.start()
t0 = time.perf_counter()
df = pulso.load(args["year"], args["month"], args["module"], **kwargs)
elapsed = time.perf_counter() - t0
stop.set()
t.join()
peak[0] = max(peak[0], rss_bytes())
print(json.dumps({"seconds": elapsed, "peak_mib": (peak[0] - base) / 2**20, "rows": len(df),
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
    parser.add_argument("--no-cache", action="store_true", help="Pass cache=False.")
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
        "cache": not args.no_cache,
    }
    print(
        f"pulso.load({args.year}, {args.month}, {args.module!r}, "
        f"columns={payload['columns']}, cache={payload['cache']})"
    )
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
