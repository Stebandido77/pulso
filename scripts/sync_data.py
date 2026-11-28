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


# Same function as in python/hatch_build.py (that file needs hatchling, which
# the lint job does not install). Keep both copies identical.
def _force_remove_tree(path: Path, attempts: int = 3, delay: float = 0.5) -> None:
    """Delete the contents of *path* (and *path* itself when possible), robustly on Windows.

    Windows refuses to delete read-only files (``shutil.copytree`` used to copy
    the read-only bit from ``data/``) and files or directories another process
    holds open (an editor, an antivirus scan, a shell whose cwd is inside).
    Read-only entries get their write bit set and are retried; locked entries
    are retried ``attempts`` times. If *path* itself stays locked but ends up
    empty, it is kept and reused. Anything else raises a RuntimeError that
    names the entry and the fix.
    """
    import contextlib
    import os
    import stat
    import time

    def _rm(entry: Path) -> None:
        last: OSError | None = None
        for i in range(attempts):
            try:
                if entry.is_dir() and not entry.is_symlink():
                    entry.rmdir()
                else:
                    entry.unlink()
                return
            except FileNotFoundError:
                return
            except PermissionError as exc:
                last = exc
                with contextlib.suppress(OSError):
                    entry.chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
                time.sleep(delay * i)
        raise RuntimeError(
            f"Could not delete {entry}: {last}. It is read-only or open in another "
            "program (editor, antivirus, a terminal whose working directory is inside "
            "it). Close it, or on Windows run 'attrib -R /S /D' on that folder, and "
            "build again."
        )

    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            _rm(Path(root) / name)
        for name in dirs:
            _rm(Path(root) / name)
    try:
        _rm(path)
    except RuntimeError:
        if any(path.iterdir()):
            raise
        # Empty but locked (e.g. a shell's cwd): keep it and copy into it.


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: canonical data dir not found at {SRC}", file=sys.stderr)
        return 1
    if DST.exists():
        try:
            _force_remove_tree(DST)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    shutil.copytree(
        SRC,
        DST,
        ignore=shutil.ignore_patterns(".gitkeep", "reference"),
        copy_function=shutil.copyfile,
        dirs_exist_ok=True,
    )
    n = sum(1 for _ in DST.rglob("*.json"))
    print(f"Synced {n} JSON files from {SRC} -> {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
