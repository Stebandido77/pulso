# Phase 0 — Scaffolding Notes

**Status:** ✅ Complete
**Date:** 2026-04-27
**Owner:** Architect (Claude in chat)

This document closes Phase 0 and hands off to Phase 1. It records what was scaffolded, what's verified, what decisions were made, and what's pending for the next phase.

---

## What was scaffolded

### Project identity
- `README.md` — bilingual (ES tagline, EN technical description), badges, quickstart
- `LICENSE` — MIT
- `CONTRIBUTING.md` — multi-agent build model with branch path conventions
- `CHANGELOG.md` — empty unreleased section
- `.gitignore` — Python + project-specific
- `pyproject.toml` — Hatchling build, pinned deps, ruff/mypy/pytest config

### Package source (`pulso/`)
- `__init__.py` — exposes 13-symbol public API (all stubs)
- `_core/` — `loader.py`, `downloader.py`, `parser.py`, `harmonizer.py`, `merger.py`, `expander.py`
- `_config/` — `registry.py`, `epochs.py`, `variables.py`
- `_utils/` — `cache.py`, `validation.py`, `logging.py`, `exceptions.py`
- `data/` — `epochs.json`, `sources.json`, `variable_map.json` (skeleton with 2 epochs, 6 modules, 3 example variables)
- `data/schemas/` — three JSON Schemas

All Python stubs raise `NotImplementedError` with phase tags (`"Phase 1: Claude Code"`, etc.) so it's obvious which file each phase is responsible for.

### Tests (`tests/`)
- `conftest.py` — pytest options for `--run-integration`, `--run-slow`, shared fixtures
- `unit/test_schemas.py` — 7 tests validating JSON files against schemas + cross-consistency
- `unit/test_smoke.py` — 2 tests verifying package imports and exports
- `fixtures/`, `integration/`, `data_quality/` — placeholder directories for later phases

### CI/CD (`.github/`)
- `workflows/ci.yml` — lint (ruff), typecheck (mypy advisory), tests (Python 3.10/3.11/3.12), JSON validation, **branch path enforcement**
- `workflows/scrape_monthly.yml` — cron job for the scraper, opens PRs to `feat/data-monthly-scrape`
- `workflows/release.yml` — tag-triggered PyPI publish
- `PULL_REQUEST_TEMPLATE.md` — phase + type checklist
- `ISSUE_TEMPLATE/month_fails_to_load.md` — bug report for failed loads
- `ISSUE_TEMPLATE/harmonization_concern.md` — flag harmonization issues

### Scripts (`scripts/`)
- `validate_sources.py` — **functional**: validates all 3 JSONs, prints ✅/❌, exits nonzero on failure
- `agent_scraper.py` — stub with full argparse, Phase 5
- `add_month.py` — stub with full argparse, Phase 1
- `verify_checksums.py` — stub, Phase 1
- `replicate_official_stat.py` — stub, Phase 6

### Documentation (`docs/`)
- `index.md` — landing page
- `quickstart.md` — install + first load
- `modules.md` — list of 6 canonical modules
- `epochs.md` — describes the two epochs
- `harmonization.md` — methodology + per-variable transform documentation (placeholder for variables that fill in Phase 2+)
- `caveats.md` — what the package does NOT promise (critical reading)
- `contributing.md` — quick pointer to root CONTRIBUTING.md
- `examples/README.md` — placeholder for Phase 6 notebooks
- `decisions/0001-build-plan.md` — ADR for multi-agent model
- `decisions/0002-scope-2006-present.md` — ADR explaining ECH exclusion

---

## Verification (all passing)

```
✅ pip install -e ".[dev]"                  → installs without errors
✅ python -c "import pulso"                  → imports successfully, prints version 0.0.1
✅ pulso.__all__                             → exposes the 13 expected symbols
✅ pytest -v                                 → 9/9 tests passing
✅ ruff check pulso tests scripts            → All checks passed
✅ ruff format --check pulso tests scripts   → 29 files already formatted
✅ python scripts/validate_sources.py        → 3 ✅, all JSON files validate
✅ python scripts/agent_scraper.py --help    → CLI argparse works
✅ python scripts/add_month.py --help        → CLI argparse works
```

---

## Key decisions made (recorded for future reference)

1. **Package name:** `pulso` (not `geih`). Tagline: *El pulso del mercado laboral colombiano.* Future-proofs for adding other DANE surveys under `pulso.X` namespaces.
2. **Build backend:** Hatchling. Simpler than setuptools for data-bundling packages.
3. **Cache location:** uses `platformdirs`, default `~/.pulso/`, override via `PULSO_CACHE_DIR`.
4. **Mandatory dep:** `pyarrow` (for parquet caching). Not optional.
5. **Optional `[legacy]`:** `pyreadstat` for `.sav`/`.dta`. Probably unused with 2006-present scope but available.
6. **Mypy advisory in Phase 0:** `continue-on-error: true` because stubs all `NotImplementedError`. Strict mode enabled in CI from Phase 1+.
7. **Python 3.10+** minimum (for `Literal`, PEP 604 unions, structural pattern matching).
8. **Branch path enforcement is non-negotiable.** The `protected-paths` job in CI is the keystone of the multi-agent model. If it fails, the model fails.
9. **`schema_version: 1.0.0`** baseline for all three schemas. Bumps require ADR.
10. **Scope:** GEIH 2006-present only. ECH explicitly excluded (ADR 0002).

---

## Pending for Phase 1 (Vertical slice)

### Builder (Claude Code, branch `feat/code-vertical-slice`)
- Implement `_load_sources()`, `_load_epochs()`, `_load_variable_map()` with runtime schema validation
- Implement `cache_path()`, `cache_info()`, `cache_clear()`
- Implement `validate_year_month()`, `validate_area()`, `validate_module()`
- Implement `Epoch.get_epoch()`, `epoch_for_month()`, `list_epochs()`
- Implement `download_zip()` with checksum verification and caching
- Implement `parse_module()` for CSV (delegating to `_parse_csv()`)
- Implement `loader.load()` for the simple case: single (year, month, module, area=cabecera), `harmonize=False`
- Implement `data_version()`, `list_available()`, `list_modules()`, `describe()`
- Construct synthetic fixture `tests/fixtures/zips/geih2_sample.zip` mimicking GEIH-2 epoch structure
- Add unit tests for each component plus an integration test against the fixture
- Implement `scripts/add_month.py` and `scripts/verify_checksums.py`

### Curator (Codex / separate Claude Code, branch `feat/data-2024-06`)
- Visit https://microdatos.dane.gov.co/index.php/catalog/MERCLAB-Microdatos
- Find GEIH June 2024 dataset
- Download ZIP, compute SHA-256, list internal files
- Produce `sources.json` entry with `validated: true` (manual verification)
- Write `PHASE_1_DATA_NOTES.md` documenting the ZIP's exact contents, any quirks, and confirmation of which files map to which canonical module names

### Architect / QA (Claude in chat + human)
- Review both PRs
- Verify the synchronization point: `pulso.load(2024, 6, "ocupados", area="cabecera", harmonize=False)` loads the real DANE ZIP into a DataFrame
- Sign off on Phase 1 → Phase 2 transition

### Phase 1 definition of done
A live execution of the following must succeed without errors:

```python
import pulso
df = pulso.load(year=2024, month=6, module="ocupados", area="cabecera", harmonize=False)
assert df.shape[0] > 0
assert "DIRECTORIO" in df.columns
assert "P6020" in df.columns or "p6020" in df.columns  # sex variable present
```

---

## Open questions for Phase 1

1. **Are the merge keys really uppercase `DIRECTORIO`/`SECUENCIA_P`/`ORDEN`** in 2024 ZIPs, or did DANE switch to lowercase at some point in `geih_2021_present`? Curator must confirm by inspection. If lowercase appears, parser needs case-normalization logic, and `epochs.json` may need a `column_case: "upper"|"lower"|"mixed"` field.

2. **Does the 2024-06 ZIP contain all 6 modules?** Sources from earlier reconnaissance suggest yes, but the Curator should confirm by listing the ZIP's internal structure and report any missing modules.

3. **Cache directory: `~/.pulso/` or platformdirs default?** Default is `~/.pulso/` on Linux, `~/Library/Caches/pulso/` on macOS, `%LOCALAPPDATA%\pulso\Cache\` on Windows. The Builder should use `platformdirs.user_cache_dir("pulso")` and document the actual path returned by `cache_path()` for each platform.

---

## Repo layout summary (final Phase 0)

```
pulso/
├── .github/
│   ├── ISSUE_TEMPLATE/{harmonization_concern.md, month_fails_to_load.md}
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/{ci.yml, scrape_monthly.yml, release.yml}
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── PHASE_0_NOTES.md             ← this file
├── README.md
├── docs/
│   ├── caveats.md, contributing.md, epochs.md, harmonization.md
│   ├── index.md, modules.md, quickstart.md
│   ├── decisions/{0001-build-plan.md, 0002-scope-2006-present.md}
│   └── examples/README.md
├── pulso/
│   ├── __init__.py              ← public API
│   ├── _config/{__init__.py, epochs.py, registry.py, variables.py}
│   ├── _core/{__init__.py, downloader.py, expander.py, harmonizer.py,
│   │          loader.py, merger.py, parser.py}
│   ├── _utils/{__init__.py, cache.py, exceptions.py, logging.py, validation.py}
│   └── data/
│       ├── epochs.json, sources.json, variable_map.json
│       └── schemas/{epochs, sources, variable_map}.schema.json
├── pyproject.toml
├── scripts/
│   ├── __init__.py
│   ├── add_month.py             (stub)
│   ├── agent_scraper.py         (stub)
│   ├── replicate_official_stat.py  (stub)
│   ├── validate_sources.py      (functional)
│   └── verify_checksums.py      (stub)
└── tests/
    ├── __init__.py, conftest.py
    ├── data_quality/
    ├── fixtures/{README.md, expected_outputs/, zips/}
    ├── integration/__init__.py
    └── unit/{__init__.py, test_schemas.py, test_smoke.py}
```

**File count:** 47 files committed.

---

## Handoff

Phase 0 is complete and verified. The repo is ready for `git init && git add . && git commit -m "Phase 0: scaffolding"`.

Before Phase 1 begins:

1. Replace any remaining `pulso-data` placeholders if the actual GitHub org will be different
2. `gh repo create Stebandido77/pulso --public --source=. --push` (or equivalent)
3. Verify CI runs green on the initial push
4. Open the two Phase 1 branches and brief the Builder and Curator using the prompts in `docs/decisions/0001-build-plan.md`
