# Contributing to pulso

This document explains how the project is organized for collaboration, particularly the multi-agent build model used during initial construction.

## Branch convention (enforced by CI)

We separate code changes from data changes to enable parallel work without conflicts:

| Branch prefix | Touches | Does NOT touch |
|---------------|---------|----------------|
| `feat/code-*` | `pulso/_core/`, `pulso/_config/`, `pulso/_utils/`, `tests/`, schemas | `pulso/data/sources.json`, `pulso/data/variable_map.json` |
| `feat/data-*` | `pulso/data/sources.json`, `pulso/data/variable_map.json`, `pulso/data/epochs.json`, `scripts/` | `pulso/_core/`, `pulso/_config/`, `pulso/_utils/` |
| `fix/*` | Anything (small surgical fixes) | — |
| `docs/*` | `docs/`, `README.md`, `CHANGELOG.md` | Code or data |

The CI workflow `protected-paths` rejects PRs that violate this. The reason: during multi-agent construction, two contributors can work in parallel on `feat/code-*` and `feat/data-*` and never conflict.

## The contract: JSON Schemas

The bridge between code and data is the JSON Schema in `pulso/data/schemas/`. The code-side trusts that data files validate against the schema; the data-side guarantees they do.

If you need to change the contract (the schema itself), it's a deliberate event:

1. Open an ADR in `docs/decisions/` describing why
2. Bump `schema_version` in metadata
3. Update both code consumers and data files in coordinated PRs

## Phases of construction

See [`README.md`](README.md) for the current phase and the [Build Plan](docs/decisions/0001-build-plan.md). Each phase has a clear "definition of done":

- **Phase 0 — Scaffolding**: schemas validate, package is importable, CI passes
- **Phase 1 — Vertical slice**: `pulso.load(2024, 6, "ocupados")` works end-to-end
- **Phase 2 — Harmonizer + merger**: `pulso.load_merged(...)` with harmonized columns
- **Phase 3 — GEIH-2 coverage**: 2021-present complete in `sources.json`
- **Phase 4 — GEIH-1 coverage**: 2006-2020 complete, cross-epoch series work
- **Phase 5 — Scraper**: monthly automation in GitHub Actions
- **Phase 6 — Validation + release**: replicates official DANE statistics, ships to PyPI

## Local development

```bash
git clone https://github.com/Stebandido77/pulso
cd pulso
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check pulso tests
ruff format pulso tests

# Type check
mypy pulso
```

## Adding a new month manually

If the scraper hasn't picked up a month yet, you can add it manually:

```bash
python scripts/add_month.py --year 2026 --month 4 --url "https://..."
```

This downloads the ZIP, computes its SHA-256, inspects its internal structure, and proposes an entry for `sources.json`. Review the diff, mark `validated: true` after a smoke test, and open a PR on a `feat/data-*` branch.

## Adding a new harmonized variable

1. Open a PR on a `feat/data-*` branch
2. Add the variable to `pulso/data/variable_map.json`
3. For each epoch where the variable exists, specify `source_variable` and `transform`
4. Cite the DANE source document in `source_doc` — this is mandatory, no exceptions
5. If the transform is non-trivial (recode, compute), explain it in `docs/harmonization.md` with the relevant DANE methodology citation
6. Add a unit test in `tests/unit/test_harmonizer.py` with a tiny synthetic example

## Reporting bugs

Use the issue templates in `.github/ISSUE_TEMPLATE/`:

- **Month fails to load**: a specific period in the registry doesn't load
- **Harmonization concern**: a harmonized variable looks wrong

## Code review checklist (for maintainers)

- [ ] Branch name matches convention
- [ ] CI green (lint, typecheck, tests, schema validation, protected-paths)
- [ ] If touching harmonization: source_doc cited
- [ ] If touching schemas: ADR in `docs/decisions/`
- [ ] Tests added for new behavior
- [ ] No real microdata committed (only synthetic fixtures in `tests/fixtures/`)
