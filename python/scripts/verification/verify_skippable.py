"""
Verificación 1: ParseError en _SKIPPABLE

Three-step verification because `_SKIPPABLE` is defined as a function-local
tuple inside `load()` and `load_merged()` (not a module-level constant —
each function carries its own copy):

  Step 1: try the prompt-specified module-import path. Reports honestly
          if it fails, then proceeds to Step 2.
  Step 2: parse the source AST to find the function-local _SKIPPABLE
          tuples and verify they include ParseError.
  Step 3: behavioural check — call load() with a registry stubbed to a
          single period, monkey-patch parse_module to raise ParseError,
          and confirm the load does NOT re-raise (i.e. ParseError IS in
          the actual catch tuple as exercised at runtime).
"""

from __future__ import annotations

import ast
import inspect
import os
import sys
import tempfile
import warnings
from typing import Any
from unittest.mock import MagicMock

import requests

import pulso
import pulso._config.registry as reg
import pulso._core.downloader as dl_mod
import pulso._core.loader as loader_mod
import pulso._core.parser as parser_mod
from pulso._utils.exceptions import ParseError

print("=" * 60)
print("VERIFICACIÓN 1: ParseError en _SKIPPABLE")
print("=" * 60)
print()


# ──────────────────────────────────────────────────────────────────
# Step 1: try the module-level import the prompt specified.
# ──────────────────────────────────────────────────────────────────

print("--- Step 1: module-level import ---")
module_level_skippable = getattr(loader_mod, "_SKIPPABLE", None)
if module_level_skippable is not None:
    print("Encontrado: pulso._core.loader._SKIPPABLE")
    print()
    print("Excepciones:")
    for exc in module_level_skippable:
        print(f"  - {exc.__name__}")
    names_module = [exc.__name__ for exc in module_level_skippable]
    if "ParseError" in names_module:
        print("OK: ParseError en _SKIPPABLE (module-level)")
    else:
        print("WARN: ParseError NO en _SKIPPABLE (module-level)")
else:
    print("  No hay _SKIPPABLE module-level.")
    print("  -> _SKIPPABLE vive function-local en load() y load_merged().")
    print("  -> No es un bug; es un detalle de implementación.")
    print()


# ──────────────────────────────────────────────────────────────────
# Step 2: AST-introspect the function bodies for their local _SKIPPABLE.
# ──────────────────────────────────────────────────────────────────

print("--- Step 2: AST introspection of load() and load_merged() ---")

source = inspect.getsource(loader_mod)
tree = ast.parse(source)

found_skippable: dict[str, list[str]] = {}
for fn in ast.walk(tree):
    if not isinstance(fn, ast.FunctionDef):
        continue
    if fn.name not in {"load", "load_merged"}:
        continue
    for node in ast.walk(fn):
        # Look for ``_SKIPPABLE: ... = (...)`` (AnnAssign).
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "_SKIPPABLE"
            and isinstance(node.value, ast.Tuple)
        ):
            names = [elt.id for elt in node.value.elts if isinstance(elt, ast.Name)]
            found_skippable[fn.name] = names

if not found_skippable:
    print("  ERROR: no se encontraron tuplas _SKIPPABLE en load/load_merged")
    sys.exit(2)

ast_ok = True
for fn_name, names in found_skippable.items():
    print(f"  {fn_name}() local _SKIPPABLE: {names}")
    if "ParseError" in names:
        print("    OK: ParseError presente")
    else:
        print("    FAIL: ParseError ausente")
        ast_ok = False
print()


# ──────────────────────────────────────────────────────────────────
# Step 3: behavioural check — drive load() and confirm ParseError is
#         actually swallowed at runtime.
# ──────────────────────────────────────────────────────────────────

print("--- Step 3: behavioural check (call load, mock ParseError) ---")

# Stub registry to one validated period.
reg._SOURCES = {
    "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
    "modules": {
        "ocupados": {
            "level": "persona",
            "description_es": "Ocu",
            "description_en": "Ocu",
            "available_in": ["geih_2021_present"],
        }
    },
    "data": {
        "2024-06": {
            "epoch": "geih_2021_present",
            "download_url": "https://example.com/x.zip",
            "checksum_sha256": "a" * 64,
            "modules": {"ocupados": {"cabecera": "x.CSV"}},
            "validated": True,
        }
    },
}

os.environ["PULSO_CACHE_DIR"] = tempfile.mkdtemp()
dl_mod.verify_checksum = lambda *_a, **_kw: True


# Patch requests.get with a fake response so download_zip succeeds.
class _FakeResponse:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def raise_for_status(self) -> None:
        pass

    def iter_content(self, chunk_size: int = 0) -> Any:  # noqa: ARG002
        return [b"bytes"]


requests.get = lambda *_a, **_kw: _FakeResponse()  # type: ignore[assignment]

# Patch parse_module to always raise ParseError.
parser_mod.parse_module = MagicMock(side_effect=ParseError("simulated parser failure"))

# strict=False: ParseError MUST be caught and surfaced via the aggregated warning.
behavioural_ok = True
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        df = pulso.load(year=2024, month=6, module="ocupados", strict=False)
    print(f"  Strict=False: ParseError swallowed, returned df.shape={df.shape}")
except ParseError as exc:
    print(f"  FAIL: ParseError propagated under strict=False: {exc}")
    behavioural_ok = False

# strict=True must still propagate.
try:
    pulso.load(year=2024, month=6, module="ocupados", strict=True)
    print("  FAIL: ParseError did NOT propagate under strict=True")
    behavioural_ok = False
except ParseError:
    print("  Strict=True: ParseError correctly propagated")

print()

if ast_ok and behavioural_ok:
    print("OK: ParseError is in _SKIPPABLE in both load() and load_merged(),")
    print("    and the behavioural check confirms it's caught under")
    print("    strict=False and re-raised under strict=True.")
    sys.exit(0)
else:
    print("FAIL: see messages above.")
    sys.exit(1)
