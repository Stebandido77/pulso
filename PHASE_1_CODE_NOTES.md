# Phase 1 (Code) — Builder Notes

**Status:** ✅ Complete
**Date:** 2026-04-27
**Branch:** `feat/code-vertical-slice`
**Owner:** Builder (Claude Code)

---

## What was implemented

### A. Config loaders (`pulso/_config/registry.py`)

- `_load_json_validated()` — shared helper: loads JSON, validates against schema, raises `ConfigError` on failure.
- `_load_sources()`, `_load_epochs()`, `_load_variable_map()` — module-level singleton cache (global variables). Callers can inject test data by setting `pulso._config.registry._SOURCES = custom_dict` before the call.
- `data_version()`, `list_available()`, `list_modules()`, `describe()` — implemented.
- `list_variables()`, `describe_variable()`, `describe_harmonization()` — raise `NotImplementedError("Phase 2")`.

### B. Epoch system (`pulso/_config/epochs.py`)

- `AreaFilter` frozen dataclass — holds `column`, `cabecera_values`, `resto_values`; present on GEIH-2 epochs, `None` on GEIH-1.
- `Epoch` frozen dataclass — gained `area_filter: AreaFilter | None` in schema 1.1.0 alignment (PR #5 + test-fix commit). `None` means files are physically split (Shape A); set means a single nationwide file filtered by column (Shape B).
- `_epoch_from_raw()` — converts raw JSON dict to frozen `Epoch` dataclass; parses `area_filter` if present.
- `get_epoch(key)` — raises `ConfigError` on unknown key.
- `epoch_for_month(year, month)` — handles open-ended epochs (`end_date=null`) correctly. Raises `ConfigError` for dates before 2006-01.
- `list_epochs()` — returns all epochs from `epochs.json`.

### C. Input validation (`pulso/_utils/validation.py`)

- `validate_year_month()` — normalizes all input forms (int, range, list, None-month) to a sorted `list[tuple[int, int]]`. Year range: 2006–2100.
- `validate_area()` — returns a `Literal` type.
- `validate_module()` — raises `ModuleNotAvailableError` with a helpful message listing available modules.

### D. Cache (`pulso/_utils/cache.py`)

- `cache_path()` — respects `PULSO_CACHE_DIR` env var; falls back to `platformdirs.user_cache_dir("pulso")`.
- `cache_info()` — walks the cache tree and returns stats by level.
- `cache_clear(level)` — removes files at the given level or all.

### E. Downloader (`pulso/_core/downloader.py`)

- `verify_checksum()` — SHA-256 in 8 KB chunks, case-insensitive comparison.
- `download_zip()` — registry lookup → validation guard → cache check (with checksum verification) → HTTP download with tqdm progress → atomic `tmp.replace(dest)` → post-download checksum verification.

### F. Parser (`pulso/_core/parser.py`)

- `_parse_csv()` — streams from ZIP via `zf.open()` with a single `with` statement. Passes encoding, separator, decimal from the epoch.
- `parse_module()` — looks up file paths from `_load_sources()["data"][key]["modules"][module]`. Currently handles **Shape A only** (`cabecera`/`resto` keys). The integration fixture (conftest) injects Shape A entries so integration tests pass. Proper Shape B dispatch (single `file` key + `area_filter` column filtering) is deferred to Phase 2, when the parser will check `epoch.area_filter` and branch accordingly.
- Added `year` and `month` parameters to `parse_module()` for registry lookup (not in the original stub). **Rationale:** the file paths are per `(year, month)` in `sources.json`, not per epoch. Without year/month the parser has no way to find the right paths.

### G. Loader (`pulso/_core/loader.py`)

- `load()` — validates inputs, gets epoch, validates module in data record, calls `download_zip` + `parse_module`. Multi-period loads add `year` and `month` columns. `harmonize=True` raises `NotImplementedError("Phase 2")`.
- `load_merged()` — raises `NotImplementedError("Phase 2")`.

### H. Synthetic fixture (`tests/_build_fixtures.py`)

- Generates `tests/fixtures/zips/geih2_sample.zip` with:
  - `Cabecera/` and `Resto/` sub-trees
  - `Caracteristicas generales (Personas).CSV`: 50 rows, `random.seed(42)`
  - `Ocupados.CSV`: ~60% of those rows (random subset)
- ZIP committed to repo (whitelisted in `.gitignore`).
- SHA-256: `8ebddffa3ee73ed3cc9d7f6cf37deb86038c660234a8b1653862e88d11097ac2`

### I. Tests

82 tests total (74 unit, 8 integration):
- `test_registry.py` — 14 tests
- `test_epochs.py` — 13 tests
- `test_validation.py` — 16 tests
- `test_cache.py` — 7 tests
- `test_downloader.py` — 6 tests
- `test_parser.py` — 6 tests
- `test_load_fixture.py` — 8 integration tests (skipped by default, run with `--run-integration`)

Integration test approach: `registry_with_fixture` conftest fixture redirects `PULSO_CACHE_DIR` to a temp directory, pre-populates the raw cache slot with the fixture ZIP, and injects a `2024-06` sources entry via `monkeypatch.setattr(reg, "_SOURCES", ...)`.

### J. Scripts

- `scripts/add_month.py` — downloads a ZIP, computes SHA-256, lists CSV files, proposes module mappings heuristically, prints a JSON snippet to stdout for manual copy into `sources.json`.
- `scripts/verify_checksums.py` — walks the raw cache, compares each file's checksum against `sources.json`, exits nonzero on mismatch.

---

## Decisions made

1. **Module-level singletons instead of `@functools.cache`** for `_load_sources/epochs/variable_map`. This makes test injection trivial: `monkeypatch.setattr(reg, "_SOURCES", custom)`. With `@cache`, the function itself is replaced by monkeypatch, but the internal global is untouched — the two approaches are equivalent but singletons are more explicit.

2. **`parse_module` takes `year` and `month` parameters** (deviation from stub). The stub signature `parse_module(zip_path, module, area, epoch, columns)` has no way to look up per-`(year, month)` file paths. Adding `year` and `month` is the minimal change needed. Internal API, no public impact.

3. **No download happens in the integration test** — the fixture is pre-seeded into the cache. `download_zip` finds the file, verifies the checksum, and returns immediately. This tests the cache-hit path, which is the common production path too.

4. **Fixture uses `utf-8` encoding** matching `geih_2021_present`. Older epoch (`geih_2006_2020`) uses `latin-1`; that's Phase 4's problem.

5. **`allow_unvalidated=False` by default** — operator safety: new entries start as `validated=false` after `add_month.py`. Users must explicitly opt in.

---

## What's deferred

- **Phase 2**: `harmonize=True`, `load_merged()`, `list_variables()`, `describe_variable()`, `describe_harmonization()`; Shape B parser dispatch (`epoch.area_filter` column filtering for GEIH-2 real ZIPs); `row_filter` for `desocupados`/`inactivos` separation inside `No ocupados.CSV`.
- **Phase 4**: `.sav`/`.dta` parsing (`_parse_sav`, `_parse_dta`); GEIH-1 Shape A coverage against real ZIPs.
- **Phase 5**: `scripts/agent_scraper.py`.
- **Phase 6**: `expand()`, examples, release prep.

---

## Open questions for Curator / Architect

1. **Column case in 2024 ZIPs**: Are DIRECTORIO/SECUENCIA_P/ORDEN uppercase in the real 2024-06 ZIP? The fixture assumes uppercase (matching `epochs.json`). If DANE switched to mixed case, the parser may need normalization logic, and `epochs.json` may need a `column_case` field.

2. **Module path patterns**: The Curator must confirm the exact internal ZIP paths for 2024-06. The `add_month.py` script infers paths heuristically — the Curator should verify the proposal and flip `validated: true` manually.

3. **sources.json data section is empty**: This is by design (Curator fills it). All unit tests that need a non-empty data section inject a synthetic entry via `monkeypatch`. The integration tests work the same way.
