"""Hatch build hook: copy canonical data/ into pulso/data/ before build.

The canonical data lives at ``<repo_root>/data/``. The Python package needs
the same files at ``python/pulso/data/`` so they are bundled into the wheel
(and sdist) and importable from ``pulso/data/``.

This hook runs for ``wheel``, ``sdist``, and ``editable`` build targets so
that ``pip install -e .`` also populates ``python/pulso/data/``.

Failure modes:
  * ``data/`` missing -> RuntimeError (refuse to build a data-less wheel).
  * Fewer than 13 JSON files after sync -> RuntimeError (sanity check; we
    expect 7 top-level JSONs + 6 schemas).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


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
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".gitkeep"))

        json_count = sum(1 for _ in dst.rglob("*.json"))
        if json_count < 13:
            raise RuntimeError(
                f"After sync, only {json_count} JSON files in {dst}. "
                f"Expected at least 13 (7 top-level + 6 schemas). Aborting build."
            )
