# 03 — CI Design (Six Workflows)

**Phase:** Agente 2, Phase 3
**Status:** Design — workflow YAMLs are in `workflows/` ready for Agente 3 to drop into `.github/workflows/`.

---

## TL;DR

After migration, `.github/workflows/` contains **six** files:

| File | Trigger | Purpose | Source |
|---|---|---|---|
| `python-ci.yml` | push/PR to `python/**`, `data/**` | Python lint, typecheck, tests, schema validation, wheel identity gate | NEW (replaces `ci.yml`) |
| `r-ci.yml` | push/PR to `r/**`, `data/**` | R CMD check across OS x R-version matrix, lintr | NEW |
| `python-publish.yml` | tag `python-v*` | Build wheel + sdist, verify identity, publish to PyPI | NEW (replaces `release.yml`) |
| `r-check.yml` | tag `r-v*` or `workflow_dispatch` | Full `R CMD check --as-cran` for CRAN submission readiness | NEW (placeholder for CRAN flow) |
| `integration.yml` | weekly cron + dispatch | Real DANE downloads (Python only) | EDITED (paths) |
| `scrape_monthly.yml` | monthly cron | DANE catalog scraper, opens PR with updated `data/sources.json` | EDITED (paths) |

The four NEW workflows are committed in this report's `workflows/` directory.

The two EDITED workflows are described in `02_migration_plan.md` (path edits only — no functional change).

---

## 1. Design principles

1. **Per-language paths-filter.** A PR that only edits `r/` should not trigger `python-ci.yml`. Saves Action minutes and reduces noise.
2. **Shared `data/` triggers both.** Any change to canonical data must validate against both languages.
3. **`defaults.run.working-directory`** scopes Python jobs to `python/` so commands like `pytest` and `pip install -e ".[dev]"` Just Work without per-step `cd`.
4. **Sync data first.** Every job that runs Python or R code first runs `python scripts/sync_data.py` (or `Rscript scripts/sync_data_to_r.R`) to populate the per-language data dirs. The dirs are gitignored, so a fresh checkout has them empty.
5. **Wheel identity gate** on every Python push (catches accidental drift in package contents).
6. **No coupling between Python and R workflows.** A failing R test can't block a Python release and vice versa.

---

## 2. `python-ci.yml`

**Triggers:** push to `main`/`feat/**`/`fix/**`/`docs/**` OR PR to `main`, when paths under `python/**` or `data/**` change.

**Jobs:**

| Job | Steps | Purpose |
|---|---|---|
| `lint` | sync data → ruff check → ruff format check | Style + lint |
| `typecheck` | sync data → install `[dev]` → mypy (advisory) | Type discipline (continues on error like today) |
| `test` (3.10, 3.11, 3.12) | sync data → install `[dev]` → pytest | Unit tests in matrix |
| `validate-data` | sync data → install `[dev]` → schema tests | JSON schema validation |
| `wheel-identity` | install build → `python -m build --wheel` → diff against committed reference inventory | Migration safety net |

**Key changes vs current `ci.yml`:**

- Adds `paths:` filter so R-only PRs don't trigger.
- Adds `defaults.run.working-directory: python` so commands run from there without `cd`.
- Adds `Sync data` step before any code execution.
- Adds `wheel-identity` job (NEW — see `04_wheel_identity_verification.md`).
- **Drops** the `protected-paths` job — it enforced `feat/code-*` vs `feat/data-*` branch conventions that don't generalize cleanly to a monorepo. Replaced by paths-based filtering, which makes the branch convention obsolete.

The `protected-paths` job was useful during Phase 2 of the original Python development (Curator/Builder split). Post-monorepo, the boundary is enforced by directory rather than branch name. Worth flagging for human approval (decision Q4 below).

## 3. `r-ci.yml`

**Triggers:** push to `main`/`feat/**`/`fix/**`/`docs/**` OR PR to `main`, when paths under `r/**` or `data/**` change.

**Jobs:**

| Job | OS x R version | Steps | Purpose |
|---|---|---|---|
| `R-CMD-check` | 4 cells: ubuntu-{release,devel} + macos-release + windows-release | setup-r → setup-pandoc → setup-r-dependencies → sync data → check-r-package | Standard R CMD check, soft (no `--as-cran`) |
| `lint` | ubuntu R-release | setup-r → setup-r-dependencies (lintr, styler) → `lintr::lint_package()` | R style/lint, soft-fail until R/ has files |

**Key design choices:**

- Uses `r-lib/actions/setup-r-dependencies@v2` with `working-directory: r` and `needs: check` so DESCRIPTION's Imports get installed automatically.
- `error-on: '"warning"'` on R CMD check — fails on warnings, not just errors. CRAN convention.
- `--as-cran` is **NOT** used here (it's for `r-check.yml`). This workflow runs on every push and is the day-to-day gate.
- `lint` job is `continue-on-error: true` until Agente 5 fills `r/R/` with code.

## 4. `python-publish.yml`

**Triggers:** tag `python-v*` (e.g., `python-v1.1.0`).

**Jobs:**

| Job | Purpose |
|---|---|
| `build` | sync data → `python -m build` → verify wheel identity → upload artifact |
| `publish-pypi` | download artifact → publish via PyPI Trusted Publishing |

**Key changes vs current `release.yml`:**

- Tag prefix changes from `v*` to `python-v*` (per Decision 8).
- Adds wheel identity gate before upload — if the wheel diverges unexpectedly from the committed reference inventory, **publish is blocked**.
- Trusted Publisher config on PyPI must be updated:
  - Old: workflow `release.yml`, environment `pypi`.
  - New: workflow `python-publish.yml`, environment `pypi`.
  - Action item for human: update PyPI project settings before first `python-v*` tag.

## 5. `r-check.yml`

**Triggers:** tag `r-v*` OR `workflow_dispatch`.

**Jobs:**

| Job | Purpose |
|---|---|
| `cran-check` | OS matrix `R CMD check --as-cran` with `_R_CHECK_CRAN_INCOMING_=TRUE` |
| `revdep` (manual only) | `revdepcheck::revdep_check()` to verify reverse-dependencies still work — only run before CRAN submission |

**Key design choices:**

- `error-on: '"note"'` — CRAN reviewers want NOTE-clean.
- `revdep` is gated behind `workflow_dispatch` input because it's slow (hours) and only relevant for CRAN submission.
- This workflow is **placeholder** — Agente 6 will refine it as part of CRAN submission prep.

## 6. `integration.yml` (EDITED)

Existing workflow. Edits required:

- Cache key: `pulso-cache-${{ hashFiles('pulso/data/sources.json') }}` → `pulso-cache-${{ hashFiles('data/sources.json') }}`.
- All `pulso/data/*` path references → `data/*`.
- `pip install -e ".[dev]"` → either `pip install -e "python[dev]"` (if `python/` made into installable layout) or wrap with `working-directory: python`.
- Pytest path: `tests/integration/` → `python/tests/integration/`.
- Add `Sync data` step (since `python/pulso/data/` is gitignored).

Functional behavior unchanged.

## 7. `scrape_monthly.yml` (EDITED)

Existing workflow. Edits required:

- Output path: `python scripts/agent_scraper.py --output pulso/data/sources.json` → `python scripts/agent_scraper.py --output data/sources.json`.
- The script `scripts/agent_scraper.py` lives at `python/scripts/agent_scraper.py` post-migration. Adjust invocation: `python python/scripts/agent_scraper.py --output data/sources.json`.
- Pytest path for validation: `pytest tests/unit/test_schemas.py` → `cd python && pytest tests/unit/test_schemas.py`. Sync data first.

Functional behavior unchanged.

---

## 8. Workflow file locations (deliverables)

The four NEW workflow YAMLs are committed in this report's `workflows/` subdirectory:

```
docs/internal/r-port/workflows/
├── python-ci.yml          # ready to copy to .github/workflows/python-ci.yml
├── r-ci.yml               # ready to copy to .github/workflows/r-ci.yml
├── python-publish.yml     # ready to copy to .github/workflows/python-publish.yml
└── r-check.yml            # ready to copy to .github/workflows/r-check.yml
```

Agente 3 copies these into `.github/workflows/` as part of step 8 of the migration plan, deletes the old `ci.yml` and `release.yml`, and edits `integration.yml` + `scrape_monthly.yml` per §6 and §7 above.

---

## 9. CI matrix dimensions summary

| Workflow | OS coverage | R/Python coverage | Approx Action minutes per run |
|---|---|---|---|
| `python-ci.yml` | ubuntu only | py3.10/3.11/3.12 (matrix on `test`) | ~10 min (5 jobs, mostly parallel) |
| `r-ci.yml` | ubuntu/macos/windows | release + devel (4 cells) | ~25 min (slowest: windows + devel) |
| `python-publish.yml` | ubuntu only | py3.11 only | ~3 min |
| `r-check.yml` | ubuntu/macos/windows | release + devel (4 cells) | ~30 min |
| `integration.yml` | ubuntu only | py3.12 only | ~60 min (real downloads) |
| `scrape_monthly.yml` | ubuntu only | py3.11 only | ~5 min |

Total budget for a typical PR touching `python/**`: ~10 min (python-ci only).
Total for a PR touching `r/**`: ~25 min (r-ci only).
Total for a PR touching `data/**`: ~35 min (python-ci + r-ci).

---

## 10. Open questions for human

**Q4 — Drop `protected-paths` job from `python-ci.yml`?**

Recommended: **drop it.** The job enforced `feat/code-*` vs `feat/data-*` branch naming for the Curator/Builder split. Post-monorepo, the boundary is per-directory and paths-filter handles it. The branch convention can be retired or moved to a CONTRIBUTING.md guideline.

**Q5 — Tag scheme `python-v*` and `r-v*` confirmed?**

Decision 8 from the discovery report says yes. Restating to avoid surprise: PyPI publish triggers on `python-v1.1.0`, not `v1.1.0`. The PyPI Trusted Publisher config must be updated to match.

**Q6 — `error-on` strictness for R CMD check?**

R-CI default: `error-on: '"warning"'` (fails on warnings, not just errors).
R-check: `error-on: '"note"'` (CRAN-strict).

Agree?

**Q7 — Add `concurrency` cancel-in-progress for the publish workflow?**

Currently no — a publish should never be canceled mid-flight. Recommend keeping it that way.

---

## Sources

- [r-lib/actions](https://github.com/r-lib/actions) — `setup-r`, `setup-r-dependencies`, `check-r-package`
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- Existing workflows analyzed: `.github/workflows/ci.yml`, `release.yml`, `integration.yml`, `scrape_monthly.yml`
