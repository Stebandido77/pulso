# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0rc2] — 2026-05-02

### Fixed

- **CRITICAL (C-1):** `download_zip` no longer crashes with `TypeError`
  / `AttributeError` when loading entries with `validated=false` and
  `checksum_sha256: null`. Three separate code paths (cache-key
  generation, cache-hit verification, post-download verification) all
  failed in production for 225 of 230 registry entries. The fix treats
  `checksum=None` as "not verifiable, skip", logs an INFO line, and
  uses a stable period-derived cache filename
  (`unvalidated_{year}-{month:02d}.zip`).
- **MAJOR (M-3):** `download_empalme_zip` now actually performs SHA-256
  verification when the registry has a checksum (9 of 11 years),
  matching the README's promise. Cached files with mismatched checksums
  are removed and re-downloaded; mismatch after re-download raises
  `ChecksumMismatchError`. When no checksum is recorded, verification
  is skipped with an INFO log.
- **MAJOR (M-1):** `load_merged(apply_smoothing=True, modules=[...])`
  now respects the explicit `modules` argument instead of silently
  loading every empalme module.
- **MAJOR (M-2):** `load_merged(modules=["x"])` raises
  `ModuleNotAvailableError` when "x" is unavailable for the period
  instead of silently dropping it. Auto-discovery (`modules=None`)
  still skips silently.
- **MAJOR (M-5):** Multi-period `load(year=range(...))` and
  `load_merged` continue past per-period failures when `strict=False`
  (the new default). Skipped periods are summarised in the same
  aggregated `UserWarning` that lists unvalidated periods. With
  `strict=True` the original abort-on-first-failure behaviour is
  preserved (rc1).
- **MAJOR (M-4):** `expand`, `list_variables`, `describe_variable`,
  and `describe_harmonization` are no longer
  `NotImplementedError("Phase 6")` stubs — they now have working
  implementations with tests.
- README installation snippet (`pip install pulso-co`) and badges now
  use the actual PyPI distribution name (rc1 still said `pulso`).
- `validate_year_month` rejects `bool` and `str` upfront with a clear
  `TypeError` instead of crashing mid-iteration with a cryptic int()
  error.
- `cache_clear(level="...")` raises `CacheError` for unknown levels
  instead of silently no-op'ing (rc1 quietly accepted any string).
- `DataNotValidatedError` message points at the new `strict=False`
  flag instead of the deprecated `allow_unvalidated=True`.

### Added

- **All exception classes** (`PulsoError`, `DataNotValidatedError`,
  `DataNotAvailableError`, `ModuleNotAvailableError`,
  `ChecksumMismatchError`, `DownloadError`, `ParseError`,
  `HarmonizationError`, `MergeError`, `CacheError`, `ConfigError`)
  exported at the top-level `pulso` namespace and listed in `__all__`.
  Users can `except pulso.DataNotValidatedError` directly.
- New `ChecksumMismatchError(DownloadError)` for the post-download
  hash-mismatch path. Existing `except DownloadError` keeps working
  (it's a subclass).
- New `pulso.list_validated_range()` — sorted `list[(year, month)]`
  of entries flagged `validated=True`. Validated months are
  non-contiguous in production, so this deliberately does NOT return
  `(min, max)`.
- New `pulso.validation_status()` — DataFrame with one row per
  registry entry: `year`, `month`, `validated`, `checksum_sha256`,
  `validated_at`, `modules`. Column name `validated_at` matches
  `sources.schema.json`.
- New parameter `strict: bool = False` in `load`, `load_merged`
  (replaces `allow_unvalidated`).
- Integration test matrix (`tests/integration/test_all_validated_months.py`)
  parameterised over every `validated=true` entry in the registry,
  picks up newly validated months automatically.

### Changed

- **BEHAVIORAL CHANGE:** Default for unvalidated entries flips from
  "raise `DataNotValidatedError`" (rc1: `allow_unvalidated=False`) to
  "load with single aggregated `UserWarning`" (rc2: `strict=False`).
  Old behaviour is recoverable via `strict=True`.
  See [`BREAKING_CHANGES_v1.0.0rc2.md`](BREAKING_CHANGES_v1.0.0rc2.md).
- Multi-period load with `strict=False` emits ONE aggregated
  `UserWarning` covering both unvalidated periods and skipped failures,
  instead of N warnings (one per period). Truncates with
  `... and N more` past 10 examples.

### Deprecated

- `allow_unvalidated` parameter in `load`, `load_merged`. Use `strict`
  instead. Will be removed in **v2.0.0**. See
  [`DEPRECATIONS.md`](DEPRECATIONS.md). Emits `DeprecationWarning` at
  every call.

### Internal

- `_emit_unvalidated_warning_at_end=False` private kwarg in `load` so
  `load_merged` can suppress per-module warnings and emit only the
  outer aggregated one.
- Streaming download factored into `_stream_to_file` in
  `pulso/_core/empalme.py`.

## [1.0.0rc1] — 2026-05-01

Initial public release on PyPI as `pulso-co`.

### Critical issue identified post-release

Bug C-1: `download_zip` crashes for any entry with `checksum_sha256: null`,
which is 225 of 230 production entries. Documented and fixed in 1.0.0rc2.
**Users on rc1 should upgrade.**

[1.0.0rc2]: https://github.com/Stebandido77/pulso/compare/v1.0.0rc1...v1.0.0rc2
[1.0.0rc1]: https://github.com/Stebandido77/pulso/releases/tag/v1.0.0rc1
