"""Hatch build hook: copy canonical data/ into pulso/data/ before build.

The canonical data lives at ``<repo_root>/data/``. The Python package needs
the same files at ``python/pulso/data/`` so they are bundled into the wheel
(and sdist) and importable from ``pulso/data/``.

This hook runs for ``wheel``, ``sdist``, and ``editable`` build targets so
that ``pip install -e .`` also populates ``python/pulso/data/``.

Failure modes:
  * ``data/`` missing -> RuntimeError (refuse to build a data-less wheel).
  * ``pulso/data/`` cannot be cleared (read-only or locked files on Windows)
    -> retried with the write bit set; if it still fails, RuntimeError naming
    the file and the fix.
  * Fewer than 13 JSON files after sync -> RuntimeError (sanity check; we
    expect 7 top-level JSONs + 6 schemas).

``data/reference/`` (DANE annex figures and validation results used by the
maintenance scripts) is not package data and is excluded.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


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


class SyncDataHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:  # noqa: ARG002 (Hatch hook signature)
        # self.root is python/ (where pyproject.toml lives). Repo root is its parent.
        repo_root = Path(self.root).parent
        src = repo_root / "data"
        if not src.exists():
            raise RuntimeError(
                f"Canonical data dir not found at {src}. Refusing to build without bundled data."
            )

        dst = Path(self.root) / "pulso" / "data"
        if dst.exists():
            _force_remove_tree(dst)
        # copyfile, not copy2: do not carry the read-only bit over from data/.
        shutil.copytree(
            src,
            dst,
            ignore=shutil.ignore_patterns(".gitkeep", "reference"),
            copy_function=shutil.copyfile,
            dirs_exist_ok=True,
        )

        json_count = sum(1 for _ in dst.rglob("*.json"))
        if json_count < 13:
            raise RuntimeError(
                f"After sync, only {json_count} JSON files in {dst}. "
                f"Expected at least 13 (7 top-level + 6 schemas). Aborting build."
            )
