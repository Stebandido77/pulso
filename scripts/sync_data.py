"""Copy canonical data/ into python/pulso/data/ for editable installs and dev.

The Python package expects its data files at ``python/pulso/data/``, which is
gitignored and populated either by:
  * the Hatch build hook at wheel/sdist/editable build time, OR
  * this script (manually, before running ``pytest`` from a fresh checkout).

Idempotent: re-running cleans and re-copies. Exits 0 on success.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "data"
DST = REPO_ROOT / "python" / "pulso" / "data"


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: canonical data dir not found at {SRC}", file=sys.stderr)
        return 1
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(".gitkeep"))
    n = sum(1 for _ in DST.rglob("*.json"))
    print(f"Synced {n} JSON files from {SRC} -> {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
