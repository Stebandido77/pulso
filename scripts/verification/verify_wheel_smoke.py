"""Smoke test del wheel — se ejecuta DENTRO del venv limpio con pulso recién instalado."""

from __future__ import annotations

import inspect
import sys

import pulso

print("=" * 60)
print("VERIFICACIÓN 2: Smoke test del wheel en venv limpio")
print("=" * 60)
print()

print(f"Python: {sys.version.split()[0]}")
print(f"Pulso versión: {pulso.__version__}")
print(f"Pulso path:    {pulso.__file__}")
assert pulso.__version__ == "1.0.0rc2", f"Esperaba 1.0.0rc2, got {pulso.__version__}"
print()

# ── Exceptions exportadas (C-2 fix) ─────────────────────────────────────
print("--- Exceptions exportadas (C-2 fix) ---")
required_exceptions = [
    "PulsoError",
    "DataNotValidatedError",
    "DataNotAvailableError",
    "ModuleNotAvailableError",
    "ChecksumMismatchError",
    "DownloadError",
    "ParseError",
    "HarmonizationError",
    "MergeError",
    "CacheError",
    "ConfigError",
]
for exc_name in required_exceptions:
    has_it = hasattr(pulso, exc_name)
    status = "OK" if has_it else "FAIL"
    print(f"  [{status}] pulso.{exc_name}")
    assert has_it, f"Falta exception {exc_name}"

# Hierarchy spot checks.
assert issubclass(pulso.DataNotValidatedError, pulso.PulsoError)
assert issubclass(pulso.ChecksumMismatchError, pulso.DownloadError)
print("  [OK] hierarchy: DataNotValidatedError <: PulsoError")
print("  [OK] hierarchy: ChecksumMismatchError <: DownloadError")

# ── Helpers nuevos (Commits 8, 9, 13.5) ─────────────────────────────────
print()
print("--- Helpers nuevos ---")
ranges = pulso.list_validated_range()
print(f"  list_validated_range() = {ranges}")
assert isinstance(ranges, list)
assert all(isinstance(t, tuple) and len(t) == 2 for t in ranges)

status = pulso.validation_status()
print(f"  validation_status() shape = {status.shape}")
assert status.shape[0] > 0
assert "validated_at" in status.columns
assert "last_validated_at" not in status.columns

vars_df = pulso.list_variables()
print(f"  list_variables() = {len(vars_df)} variables")
assert len(vars_df) > 0

info = pulso.describe("ocupados", year=2024, month=6)
print(f"  describe('ocupados', 2024, 6) keys = {list(info.keys())}")
assert info["validated"] is True
assert info["checksum_sha256"] is not None

# Iterable signature (Commit 13)
sig = inspect.signature(pulso.load)
month_hint = str(sig.parameters["month"].annotation)
year_hint = str(sig.parameters["year"].annotation)
assert "range" in year_hint, f"year hint missing range: {year_hint}"
assert "range" in month_hint, f"month hint missing range: {month_hint}"
print(f"  load() type hints: year={year_hint}")
print(f"                     month={month_hint}")

# ── Caso real (mes ya cacheado, debería ser instantáneo o usar cache) ───
print()
print("--- Caso real (load 2024-06 ocupados) ---")
df = pulso.load(year=2024, month=6, module="ocupados", show_progress=False)
print(f"  Shape: {df.shape}")
assert len(df) > 0

print()
print("OK: wheel funciona correctamente en venv limpio")
