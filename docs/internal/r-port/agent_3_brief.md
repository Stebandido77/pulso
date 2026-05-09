# Agente 3 Brief — Monorepo Migration

**Status:** Ready for execution.
**Approved by user:** 2026-05-09 (Q1, Q2, Q3 of Agente 2 all approved with 4 amendments).
**Branch base:** `feat/r-port` at commit `66e7f1a` (or later).
**Working branch (Agente 3 creates):** `refactor/monorepo-layout`.

---

## Why this brief exists

Agentes 1 R + 2 produced 5 design docs under `docs/internal/r-discovery/` (8 architectural decisions) and `docs/internal/r-port/` (monorepo layout, migration plan, CI design, wheel-identity gate). All are approved.

This brief is the **execution contract**: it states (a) the user-approved amendments to Agente 2's plan, (b) what Agente 3 must do, (c) the gates Agente 3 must pass, (d) what to report back. Agente 3 reads this brief plus the 5 design docs.

---

## Context for a fresh Claude Code session

You are Agente 3 in a multi-agent build of `pulso` — a Python library for Colombia DANE GEIH microdata, currently published as `pulso-co` 1.0.0 on PyPI. The team is adding an R port and converting the repo to a monorepo. Agentes 1 R and 2 did discovery + design; you do the actual file moves + structural refactor.

You'll work entirely under `feat/r-port` → `refactor/monorepo-layout`. You will not touch `main`, will not publish to PyPI, will not write Python or R logic — only structural moves, build hooks, CI workflows, and one bug fix for entry points (W5, see §3 below).

**Repo:** https://github.com/Stebandido77/pulso
**Local path (Windows):** `C:\Users\windows\Documents\Esteban 2025-1\Proyectos\Otros proyectos\pulso`

---

## Approved decisions (no need to re-litigate)

From Agente 1 R discovery (8 decisions, all approved):
1. Lean tidyverse R style.
2. GitHub + CRAN distribution (phased).
3. Codebook: lazy-download for CRAN-compliance + bundled subset.
4. **Sibling monorepo** layout: `python/`, `r/`, `data/` at root + `VERSION` file.
5. R naming: `pulso_xxx()` snake_case + prefix.
6. Metadata storage: `haven::labelled` + `attr(df, "pulso_metadata")`.
7. Return type: tibble always.
8. Loosely synchronized versioning. Tags `python-v*` and `r-v*`.

From Agente 2 design (3 decisions, all approved):
- Q1: **Option B** for `python/pulso/` ↔ `data/`: hatch build hook (wheel + sdist + editable targets) + `scripts/sync_data.py` for dev.
- Q2: Defaults from the proposed tree, **plus** add `make.ps1` PowerShell wrapper (mapping main targets: test, build, dev-install, lint, format).
- Q3: 10-step migration plan in `docs/internal/r-port/02_migration_plan.md`, **plus** the 4 amendments in §3 below.

---

## The 4 user amendments to Agente 2's plan

### Amendment 1 — Add explicit Step 0 (snapshot pre-migration)

The migration plan's "Prerequisites" section does most of this, but the user wants it formalized as **Step 0** with these explicit additions:

```bash
# from repo root, on feat/r-port, BEFORE creating refactor/monorepo-layout

# 1) Build pre-migration wheel + capture SHA
python -m build
sha256sum dist/pulso_co-1.0.0-py3-none-any.whl > pre_migration.sha256
python scripts/wheel_inventory.py dist/pulso_co-1.0.0-py3-none-any.whl > pre_migration_inventory.txt
# (wheel_inventory.py per spec in 04_wheel_identity_verification.md — write it under scripts/ first if missing)

# 2) Pytest baseline log — proof tests are green BEFORE migration
pytest -v --tb=short > pre_migration_pytest.log 2>&1
echo "Exit code: $?" >> pre_migration_pytest.log

# 3) Capture hatchling version (needed to pin in step 4)
unzip -p dist/pulso_co-1.0.0-py3-none-any.whl pulso_co-1.0.0.dist-info/WHEEL > pre_migration_wheel_meta.txt

# 4) Tag pre-migration state for safety
git tag pre-monorepo-migration
git push origin pre-monorepo-migration

# 5) Now create the working branch
git checkout -b refactor/monorepo-layout
```

Stash `pre_migration.sha256`, `pre_migration_inventory.txt`, `pre_migration_pytest.log`, `pre_migration_wheel_meta.txt` somewhere outside the repo (e.g., `~/pulso-migration-evidence/`). DO NOT commit them — they're throwaway artifacts. The verification gates in step 10 reference these files.

If anything fails post-migration, rollback is just `git reset --hard pre-monorepo-migration` (or `git checkout pre-monorepo-migration` for inspection).

### Amendment 2 — Apply W5 fix preventively (move scripts inside the package)

User-approved decision: instead of treating W5 as a fallback, **fix it during the migration**.

**Why this is more than preventive:** I verified (2026-05-09) that the v1.0.0 wheel on PyPI declares `[console_scripts]` for `pulso-add-month` and `pulso-validate-sources` pointing at `scripts.add_month:main` and `scripts.validate_sources:main` — but `scripts/` is **not in the wheel**. Confirmed by `unzip -l dist/pulso_co-1.0.0-py3-none-any.whl | grep -i scripts` returning nothing. End users running `pip install pulso-co && pulso-add-month` get `ModuleNotFoundError: No module named 'scripts'`. **Latent bug — fixing in this migration.**

**Concrete instructions for Agente 3:**

In step 2 (Move Python), after `git mv scripts python/scripts`, do an additional move:

```bash
mkdir -p python/pulso/_scripts
git mv python/scripts/add_month.py python/pulso/_scripts/add_month.py
git mv python/scripts/validate_sources.py python/pulso/_scripts/validate_sources.py
# Move ALL .py files that are referenced by [project.scripts] OR are CLI entry points.
# Keep maintenance-only files (e.g. agent_scraper.py is run from CI workflow, not as console script)
# under python/scripts/ — those don't need to be in the wheel.

touch python/pulso/_scripts/__init__.py
echo '"""Internal CLI scripts exposed via [project.scripts]."""' > python/pulso/_scripts/__init__.py
```

Then in step 4 (edit `python/pyproject.toml`), update `[project.scripts]`:

```toml
[project.scripts]
pulso-validate-sources = "pulso._scripts.validate_sources:main"
pulso-add-month = "pulso._scripts.add_month:main"
```

**Smoke test in step 10**:

```bash
# After building + pip-installing the post-migration wheel into a fresh venv:
pulso-add-month --help
pulso-validate-sources --help
# Both must exit 0 with helpful output. Pre-migration these would error with ModuleNotFoundError.
```

### Amendment 3 — Wheel identity gate is now "expected delta", not "zero diff"

The W5 fix changes the wheel contents intentionally. Post-migration wheel will have:

**Additions (expected, allowed):**
- `pulso/_scripts/__init__.py` (new file)
- `pulso/_scripts/add_month.py` (was at `scripts/add_month.py` outside wheel)
- `pulso/_scripts/validate_sources.py` (was at `scripts/validate_sources.py` outside wheel)
- Any other `python/pulso/_scripts/*.py` that's an entry point.

**Modifications (expected, allowed):**
- `pulso_co-1.0.0.dist-info/entry_points.txt` — paths change from `scripts.X` to `pulso._scripts.X`. Now ~118 bytes instead of 114.
- `pulso_co-1.0.0.dist-info/RECORD` — changes because the file inventory and SHA256s change.

**Everything else MUST be byte-identical to the pre-migration reference.** Specifically:
- Every existing `pulso/**/*.py` file: name + size + SHA256 unchanged.
- Every `pulso/data/*.json` file: name + size + SHA256 unchanged.
- `pulso_co-1.0.0.dist-info/METADATA`: unchanged.
- `pulso_co-1.0.0.dist-info/WHEEL`: unchanged (assuming hatchling pinned).
- `pulso_co-1.0.0.dist-info/licenses/LICENSE`: unchanged.

**Gate procedure for step 10 (REVISED):**

```bash
# After building post-migration wheel:
python scripts/wheel_inventory.py python/dist/pulso_co-1.0.0-py3-none-any.whl > post_migration_inventory.txt

# Diff against pre-migration:
diff pre_migration_inventory.txt post_migration_inventory.txt > diff.txt

# Inspect diff.txt. The ONLY allowed lines are:
# > <size>  <sha256>  pulso/_scripts/__init__.py
# > <size>  <sha256>  pulso/_scripts/add_month.py
# > <size>  <sha256>  pulso/_scripts/validate_sources.py
# > [any other intentional pulso/_scripts/ additions]
# < <old_size>  <old_sha>  pulso_co-1.0.0.dist-info/entry_points.txt
# > <new_size>  <new_sha>  pulso_co-1.0.0.dist-info/entry_points.txt
# < <old_size>  <old_sha>  pulso_co-1.0.0.dist-info/RECORD
# > <new_size>  <new_sha>  pulso_co-1.0.0.dist-info/RECORD

# If diff.txt contains anything OUTSIDE that set → BLOCK MERGE. Investigate the offending file.
```

Commit the post-migration inventory as the new permanent reference:

```bash
cp post_migration_inventory.txt docs/internal/r-port/wheel_reference_inventory.txt
git add docs/internal/r-port/wheel_reference_inventory.txt
```

The committed reference = the **post-migration** wheel content. CI's `wheel-identity` job (in `python-ci.yml`) diffs against this, so it permanently locks the new wheel shape.

**Version handling:** Keep `VERSION = "1.0.0"` in the migration commit. The fix ships in the next planned release (e.g., `python-v1.0.1`) — do NOT publish to PyPI from the migration commit.

### Amendment 4 — Final report MUST include post-merge checklist for the user

Agente 3's PR description (and final report to the user) MUST include this checklist. The user will execute these manually after merging the migration to `feat/r-port` (or to `main`):

```markdown
## Post-merge action items for human

Before tagging the next `python-v*` release:

- [ ] **PyPI Trusted Publisher config update.** Old workflow `release.yml` is gone. Update at:
      https://pypi.org/manage/project/pulso-co/settings/publishing/
      Set:
        - Workflow: `python-publish.yml`
        - Environment: `pypi`
      Otherwise the next release tag will fail to publish.

- [ ] **Re-test entry points end-to-end.** In a fresh venv:
        pip install python/dist/pulso_co-X.Y.Z.whl
        pulso-add-month --help        # should work; was BROKEN in v1.0.0
        pulso-validate-sources --help # should work; was BROKEN in v1.0.0

- [ ] **Update CHANGELOG** for v1.0.1 (or chosen version) noting the entry-point bug fix.

- [ ] **Verify monthly scrape workflow** (`scrape_monthly.yml`) still opens PRs correctly with new path
      `data/sources.json` — wait for next monthly cron OR trigger manually via
      `gh workflow run scrape_monthly.yml` and review the PR it opens.

- [ ] **Notify Stata/R-port watchers** (none yet — this becomes relevant only when R port ships).

- [ ] **Drop or rename open `feat/code-*` / `feat/data-*` branches** — the path-convention enforcement
      from old `protected-paths` job is gone. Any work-in-progress on those branches needs to be
      rebased or closed.

- [ ] **Update local dev environments** — anyone with the repo cloned needs to re-run:
        git pull
        make dev-install   # or: ./make.ps1 dev-install on Windows
      (because pulso/data/ is now gitignored and populated by the sync script).
```

---

## Plan (10 steps with the 4 amendments folded in)

Agente 3 follows `docs/internal/r-port/02_migration_plan.md` AS WRITTEN, with these deltas:

| Step | Amendment delta |
|---|---|
| **0 (Prereqs)** | Apply Amendment 1 in full. Tag `pre-monorepo-migration`, capture pytest baseline log, store evidence outside repo. |
| **1 (Empty structure)** | No change. |
| **2 (Move Python)** | After `git mv scripts python/scripts`, ALSO move CLI entry-point files into `python/pulso/_scripts/` per Amendment 2. Add `__init__.py`. |
| **3 (Move data)** | No change. |
| **4 (Edit pyproject.toml)** | Pin hatchling, add 3 hooks blocks. ALSO update `[project.scripts]` paths to `pulso._scripts.X:main` per Amendment 2. |
| **5 (hatch_build.py)** | No change. |
| **6 (sync_data.py)** | No change. |
| **7 (.gitignore)** | No change. |
| **8 (Workflows)** | No change. (4 new files copied from `docs/internal/r-port/workflows/`; ci.yml + release.yml deleted; integration.yml + scrape_monthly.yml edited per `03_ci_design.md` §6 + §7.) |
| **9 (R skeleton + root files)** | Defaults plus **create `make.ps1`** per Amendment 2. PowerShell wrapper mapping main targets (see §4 below). |
| **10 (Gate / E2E)** | Apply Amendment 3 (revised gate: expected delta set, not zero diff). ALSO add the entry-point smoke test (`pulso-add-month --help`) per Amendment 2. Commit `wheel_reference_inventory.txt` as POST-MIGRATION reference. |
| **PR description** | Apply Amendment 4 (post-merge checklist). |

---

## §4 — `make.ps1` spec (Amendment 2)

Create `make.ps1` at repo root. PowerShell wrapper for the same targets as the Makefile. Pattern:

```powershell
# make.ps1 — PowerShell wrapper for Windows users.
# Usage: ./make.ps1 <target>   (e.g. ./make.ps1 test)

param([Parameter(Position=0)][string]$Target = "help")

function Invoke-Sync-Data {
    python scripts/sync_data.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Target) {
    "sync-data"   { Invoke-Sync-Data }
    "dev-install" { Invoke-Sync-Data; Set-Location python; pip install -e ".[dev]"; Set-Location .. }
    "test"        { Invoke-Sync-Data; Set-Location python; pytest -v; Set-Location .. }
    "test-r"      { Rscript scripts/sync_data_to_r.R; Set-Location r; Rscript -e "devtools::test()"; Set-Location .. }
    "lint"        { Set-Location python; ruff check pulso tests scripts; Set-Location .. }
    "format"      { Set-Location python; ruff format pulso tests scripts; Set-Location .. }
    "build"       { Invoke-Sync-Data; Set-Location python; python -m build; Set-Location .. }
    "clean"       {
        Remove-Item -Recurse -Force python/dist, python/build, python/*.egg-info -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force python/pulso/data, r/inst/extdata -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force r/.Rcheck, r/*.tar.gz -ErrorAction SilentlyContinue
    }
    "help"        {
        Write-Host "Targets: sync-data, dev-install, test, test-r, lint, format, build, clean"
    }
    default { Write-Host "Unknown target: $Target"; Write-Host "Run: ./make.ps1 help"; exit 1 }
}
```

Test on Windows: `./make.ps1 help`, then `./make.ps1 sync-data`, then `./make.ps1 test`.

---

## Restrictions (immutable)

NO podés:
- Mover archivos fuera de los pasos definidos en el plan.
- Modificar código Python (cambios funcionales). Solo edits a `pyproject.toml` para pin + hooks blocks + entry_points paths.
- Tocar PyPI ni CRAN.
- Saltarte el wheel identity gate (Amendment 3) — si el diff contiene algo fuera del expected delta set, **NO mergeás**.
- Usar `--no-verify` en commits ni `--force` en push.
- Modificar `main`. Trabajás en `refactor/monorepo-layout` → PR a `feat/r-port`.

SÍ podés:
- Crear `refactor/monorepo-layout` desde `feat/r-port`.
- Hacer commits y push a `refactor/monorepo-layout`.
- Tag `pre-monorepo-migration` (read-only safety).
- Crear PR `refactor/monorepo-layout → feat/r-port` con la descripción incluyendo Amendment 4 checklist.
- Web search si necesitás clarificar comportamiento de hatch o r-lib actions.

---

## Output / final report

When all 10 steps pass and the gate is green, push `refactor/monorepo-layout` and open a PR to `feat/r-port`. PR description MUST contain:

```markdown
## Migration summary

[~5 bullet points of what changed]

## Wheel identity verification (Amendment 3)

Reference wheel (pre-migration v1.0.0):
  SHA256: b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37
  Size:   418158 bytes

Post-migration wheel:
  SHA256: <computed>
  Size:   <computed>

Tier 1 (expected-delta gate): PASS / FAIL
Diff content (must be subset of allowed delta):
  + pulso/_scripts/__init__.py        <size> <sha>
  + pulso/_scripts/add_month.py       <size> <sha>
  + pulso/_scripts/validate_sources.py <size> <sha>
  ~ pulso_co-1.0.0.dist-info/entry_points.txt (118 bytes vs 114; new module paths)
  ~ pulso_co-1.0.0.dist-info/RECORD (recomputed)

Tier 2 (bytes-of-zip identity): PASS / N/A (changed by W5 fix, expected)

## Smoke tests

- All 357 Python tests: PASS
- pulso-add-month --help: PASS (was broken in v1.0.0; fixed by W5)
- pulso-validate-sources --help: PASS (was broken in v1.0.0; fixed by W5)
- pip install of post-migration wheel + import pulso: PASS
- R CMD check (skeleton): PASS with expected NAMESPACE WARNINGs

## Post-merge action items for human

[Amendment 4 checklist verbatim]
```

After PR merge, reply to the user with:
1. PR URL.
2. Wheel SHA256 (post-migration).
3. Confirmation Tier 1 gate passed.
4. The post-merge checklist.

**STOP after the merge. Do NOT proceed to Agente 4 without explicit user authorization.**

---

## Time estimate

3–4 hours focused. If you exceed 5 hours, stop and report.

If anything blocks (wheel diff outside expected set, tests fail post-move, hatchling version drift), commit the work-in-progress to `refactor/monorepo-layout`, push, and report the blocker. Do not destructive-rollback unless the user authorizes.

---

## Files to read before starting

In order:
1. `docs/internal/r-port/00_AGENT_2_REPORT.md` — design summary.
2. `docs/internal/r-port/01_directory_structure.md` — full target tree + Option B rationale.
3. `docs/internal/r-port/02_migration_plan.md` — 10 atomic steps.
4. `docs/internal/r-port/04_wheel_identity_verification.md` — gate spec (note Amendment 3 revises this).
5. `docs/internal/r-port/03_ci_design.md` — workflow design.
6. `docs/internal/r-port/workflows/*.yml` — 4 ready-to-use YAMLs.

Then start at Step 0.

---

## Sources / cross-refs

- Agente 1 R discovery: `docs/internal/r-discovery/00_DISCOVERY_REPORT.md`
- Agente 2 design: `docs/internal/r-port/00_AGENT_2_REPORT.md`
- Branch state at brief authoring: `feat/r-port` @ `66e7f1a`
- Reference v1.0.0 wheel: `dist/pulso_co-1.0.0-py3-none-any.whl` (SHA `b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37`)
- W5 latent bug confirmed via `unzip -l dist/pulso_co-1.0.0-py3-none-any.whl` (no `scripts/` entries)
