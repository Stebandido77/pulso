# 02 — Migration Plan (for Agente 3 to execute)

**Phase:** Agente 2, Phase 2
**Status:** Plan — awaits human approval before Agente 3 executes.
**Constraint reminder:** This plan only executes if the wheel byte-identity gate (`04_wheel_identity_verification.md`) passes. Agente 3 may not merge to `main` if Tier 1 fails.

---

## TL;DR

The migration is **10 atomic steps**, each with explicit verify + revert. Estimated time end-to-end: **~half a day** of focused work, executable by one agent on a fresh branch off `feat/r-port`.

The migration produces a single PR (`refactor/monorepo-layout` → `feat/r-port`). All Python tests must remain green and the wheel content inventory must match the reference.

**Gate:** No file moves merge until `python -m build` from `python/` produces a wheel whose content inventory matches `docs/internal/r-port/wheel_reference_inventory.txt` byte-for-byte.

---

## 0. Prerequisites (Agente 3 runs before step 1)

```bash
cd /path/to/pulso
git checkout feat/r-port           # base branch with Agente 1+2 reports
git pull origin feat/r-port
git status                          # must be clean
git checkout -b refactor/monorepo-layout

# Capture reference inventory FROM THE CURRENT (pre-migration) tree.
python -m build  # produces dist/pulso_co-1.0.0-py3-none-any.whl
python scripts/wheel_inventory.py dist/pulso_co-1.0.0-py3-none-any.whl > /tmp/wheel-pre.txt
sha256sum dist/pulso_co-1.0.0-py3-none-any.whl > /tmp/wheel-pre.sha256

# Find hatchling version that built the wheel — needed to pin in step 4.
unzip -p dist/pulso_co-1.0.0-py3-none-any.whl pulso_co-1.0.0.dist-info/WHEEL
# Note the "Generator: hatchling X.Y.Z" line. Save X.Y.Z for step 4.
```

**Verify:** `git status` clean, `dist/pulso_co-1.0.0-py3-none-any.whl` produced, `/tmp/wheel-pre.txt` non-empty.

**Revert (only if anything goes wrong here):** `git checkout feat/r-port; git branch -D refactor/monorepo-layout`. Nothing has been changed.

---

## Step 1 — Create empty top-level structure

**Atomic:** create empty directories that don't exist yet. Doesn't move anything.

```bash
mkdir -p python r data docs/shared docs/python docs/r scripts
mkdir -p .github/workflows  # already exists, no-op
mkdir -p docs/internal/r-port  # already exists from this report
```

Add `.gitkeep` to ones that would otherwise be empty (git ignores empty dirs):

```bash
touch python/.gitkeep r/.gitkeep data/.gitkeep
touch docs/shared/.gitkeep docs/r/.gitkeep
```

**Verify:**
```bash
ls -la python r data docs/shared docs/python docs/r scripts
# All directories exist.
```

**Revert:**
```bash
rmdir python r data docs/shared docs/r 2>/dev/null
rm python/.gitkeep r/.gitkeep data/.gitkeep docs/shared/.gitkeep docs/r/.gitkeep
```

---

## Step 2 — Move Python package + tests + scripts

**Atomic:** three `git mv` operations.

```bash
git mv pulso python/pulso
git mv tests python/tests
git mv scripts python/scripts          # rename target dir doesn't exist yet, OK
rm python/.gitkeep                     # no longer needed
```

**Verify:**
```bash
git status
# Should show: rename: pulso/__init__.py -> python/pulso/__init__.py (and ~50 more)
ls python/pulso/__init__.py            # exists
ls python/tests/                       # populated
ls python/scripts/                     # populated
ls pulso 2>/dev/null && echo "STILL EXISTS - bad" || echo "moved OK"
```

**Revert:**
```bash
git mv python/pulso pulso
git mv python/tests tests
git mv python/scripts scripts
rmdir python
```

---

## Step 3 — Move data/ files to canonical top-level location

**Atomic:** move JSON files + schemas/.

```bash
git mv python/pulso/data/sources.json data/
git mv python/pulso/data/dane_codebook.json data/
git mv python/pulso/data/_scraped_catalog.json data/
git mv python/pulso/data/empalme_sources.json data/
git mv python/pulso/data/epochs.json data/
git mv python/pulso/data/variable_map.json data/
git mv python/pulso/data/variable_module_map.json data/
git mv python/pulso/data/schemas data/schemas
rmdir python/pulso/data                 # should be empty
rm data/.gitkeep                        # no longer needed
```

**Verify:**
```bash
ls data/
# sources.json  dane_codebook.json  _scraped_catalog.json  empalme_sources.json
# epochs.json   variable_map.json   variable_module_map.json   schemas/
ls data/schemas/                       # 6 .schema.json files
ls python/pulso/data 2>/dev/null && echo "STILL EXISTS - bad" || echo "moved OK"

# Sanity: total bytes match pre-migration
du -sh data/
# Expect ~7 MB (codebook is the bulk).
```

**Revert:**
```bash
mkdir python/pulso/data
git mv data/*.json python/pulso/data/
git mv data/schemas python/pulso/data/schemas
rmdir data
```

---

## Step 4 — Update `python/pyproject.toml`: add build hook + pin hatchling

**Atomic:** edit one file, add 2 blocks, pin one version.

```bash
git mv pyproject.toml python/pyproject.toml
```

Then edit `python/pyproject.toml`:

1. **Pin hatchling** in `[build-system]`:
   ```toml
   [build-system]
   requires = ["hatchling==X.Y.Z"]   # X.Y.Z from prereqs step
   build-backend = "hatchling.build"
   ```

2. **Add custom build hook** registration (append, do NOT remove anything):
   ```toml
   [tool.hatch.build.targets.wheel.hooks.custom]
   path = "hatch_build.py"

   [tool.hatch.build.targets.sdist.hooks.custom]
   path = "hatch_build.py"

   [tool.hatch.build.targets.editable.hooks.custom]
   path = "hatch_build.py"
   ```

3. **Verify NO other content changed.** `[project]`, `[project.scripts]`, `[tool.hatch.build.targets.wheel] packages = ["pulso"]`, `[tool.hatch.build.targets.sdist] include/exclude`, `[tool.pytest.ini_options]`, `[tool.coverage]`, `[tool.ruff]`, `[tool.mypy]` blocks must be byte-identical to pre-migration.

Update `[tool.hatch.build.targets.sdist] exclude` to add `python/pulso/data` (since it'll be a generated build artifact, gitignored, but git might still see it under `python/`):

   ```toml
   exclude = [
       ...existing entries...,
       "pulso/data",  # populated by hatch_build.py at build time, not source
   ]
   ```

**Wait — this is wrong.** sdist needs to include the data, otherwise `pip install pulso-co --no-binary` from sdist would fail. Reconsider:

- **Wheel target:** data MUST be in wheel. Build hook populates `pulso/data/` from `../data/` before wheel is packed.
- **sdist target:** data MUST also be in sdist (so `pip install` from sdist still works). Same hook approach.
- **Source tree (git):** data lives ONLY at `data/`. `python/pulso/data/` is a build-time artifact and gitignored.

So `exclude` should NOT add `pulso/data`. Instead, the `.gitignore` covers `python/pulso/data/`. Hatch only sees what's on disk at build time, which IS the populated `pulso/data/` (after the build hook runs).

**Verify:**
```bash
diff <(git show HEAD:pyproject.toml) python/pyproject.toml | head -50
# Differences MUST be:
#   - hatchling pin
#   - 3 new [tool.hatch.build.targets.*.hooks.custom] blocks
# Nothing else.
```

**Revert:**
```bash
git mv python/pyproject.toml pyproject.toml
git checkout pyproject.toml
```

---

## Step 5 — Create `python/hatch_build.py`

**Atomic:** create one new file.

Content (Agente 3 writes this, ~30 lines):

```python
"""Hatch build hook: copy canonical data/ into pulso/data/ before build."""
from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class SyncDataHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        repo_root = Path(self.root).parent
        src = repo_root / "data"
        if not src.exists():
            raise RuntimeError(
                f"Canonical data dir not found at {src}. "
                f"Refusing to build a wheel without bundled data."
            )

        dst = Path(self.root) / "pulso" / "data"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".gitkeep"))

        json_count = sum(1 for _ in dst.rglob("*.json"))
        if json_count < 8:  # 7 top-level + 6 schemas = 13 expected
            raise RuntimeError(
                f"After sync, only {json_count} JSON files in {dst}. "
                f"Expected at least 13. Aborting build."
            )
```

**Verify:**
```bash
ls python/hatch_build.py
python -c "from python.hatch_build import SyncDataHook; print('importable')"
# Or test the hook fires by building:
cd python && python -m build --wheel 2>&1 | grep -i "sync\|hook\|error"
```

**Revert:**
```bash
rm python/hatch_build.py
```

---

## Step 6 — Create `scripts/sync_data.py` (top-level)

**Atomic:** create one new file at top-level scripts/.

Content (~20 lines):

```python
"""Copy canonical data/ into python/pulso/data/ for editable installs and dev."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "data"
DST = REPO_ROOT / "python" / "pulso" / "data"


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: canonical data dir not found at {SRC}", file=sys.stderr)
        return 1
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST, ignore=shutil.ignore_patterns(".gitkeep"))
    n = sum(1 for _ in DST.rglob("*.json"))
    print(f"Synced {n} JSON files from {SRC} → {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Verify:**
```bash
python scripts/sync_data.py
# Output: "Synced 13 JSON files from .../data → .../python/pulso/data"
ls python/pulso/data/
# All 7 top-level JSONs + schemas/ subdir present.
```

**Revert:**
```bash
rm scripts/sync_data.py
rm -rf python/pulso/data  # generated artifact
```

---

## Step 7 — Update `.gitignore` and create `python/.gitignore`

**Atomic:** edit one file + create one new file.

Edit root `.gitignore`, ADD:

```gitignore
# Build artifacts (generated by sync_data.py / hatch_build.py)
python/pulso/data/
python/dist/
python/build/
python/*.egg-info/

# R generated artifacts
r/inst/extdata/
r/.Rcheck/
r/*.tar.gz
r/man/   # if generated by roxygen2 from R/ docstrings; revisit when Agente 4 starts
```

Create `python/.gitignore` (mirror what's in root):

```gitignore
pulso/data/
dist/
build/
*.egg-info/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage*
```

**Verify:**
```bash
git status python/pulso/data/
# Should be ignored (no output, or "ignored" status).
git check-ignore -v python/pulso/data/sources.json
# Confirms which .gitignore rule matched.
```

**Revert:**
```bash
git checkout .gitignore
rm python/.gitignore
```

---

## Step 8 — Move + edit GitHub Actions workflows

**Atomic:** several file operations.

8a. **Delete old workflow files** that are being replaced:

```bash
git rm .github/workflows/ci.yml
git rm .github/workflows/release.yml
```

8b. **Copy new workflow files** from this report's workflows/ dir:

```bash
cp docs/internal/r-port/workflows/python-ci.yml .github/workflows/
cp docs/internal/r-port/workflows/r-ci.yml .github/workflows/
cp docs/internal/r-port/workflows/python-publish.yml .github/workflows/
cp docs/internal/r-port/workflows/r-check.yml .github/workflows/
git add .github/workflows/python-ci.yml .github/workflows/r-ci.yml \
        .github/workflows/python-publish.yml .github/workflows/r-check.yml
```

8c. **Edit `integration.yml`**:

- Cache key: `pulso-cache-${{ hashFiles('pulso/data/sources.json') }}` → `pulso-cache-${{ hashFiles('data/sources.json') }}`
- Add `Sync data` step before install
- `pip install -e ".[dev]"` → run inside `python/` (add `working-directory: python` or `cd python && pip install -e ".[dev]"`)
- Pytest path: `tests/integration/` → `python/tests/integration/`

8d. **Edit `scrape_monthly.yml`**:

- Output path: `pulso/data/sources.json` → `data/sources.json`
- Script invocation: `scripts/agent_scraper.py` → `python/scripts/agent_scraper.py`
- `pip install -e ".[dev,scraper]"` → run inside `python/`
- Pytest path: `tests/unit/test_schemas.py` → `python/tests/unit/test_schemas.py`

**Verify:**
```bash
ls .github/workflows/
# python-ci.yml, r-ci.yml, python-publish.yml, r-check.yml, integration.yml, scrape_monthly.yml
# (no ci.yml, no release.yml)
yamllint .github/workflows/*.yml  # syntax check
```

**Revert:**
```bash
git checkout HEAD -- .github/workflows/  # restore everything
```

---

## Step 9 — Create R skeleton + root files

**Atomic:** several new files.

9a. **R skeleton** (Agente 4 expands; just enough to make `R CMD check` not fail):

Create `r/DESCRIPTION`:
```
Package: pulso
Title: Load GEIH Microdata from Colombia's DANE
Version: 0.0.0.9000
Authors@R: c(person("pulso contributors", role = c("aut", "cre"), email = "noreply@example.com"))
Description: R interface to GEIH (Gran Encuesta Integrada de Hogares) microdata from
    Colombia's DANE. Companion to the Python package pulso-co.
License: MIT + file LICENSE
Encoding: UTF-8
LazyData: false
Imports:
    tibble,
    vctrs,
    rlang,
    cli,
    haven,
    httr2,
    jsonlite
Suggests:
    testthat (>= 3.0.0),
    knitr,
    rmarkdown,
    dplyr,
    tidyr,
    srvyr
Config/testthat/edition: 3
RoxygenNote: 7.3.2
```

Create `r/NAMESPACE`:
```
# Generated by roxygen2: do not edit by hand
```

Create `r/.Rbuildignore`:
```
^.*\.Rproj$
^\.Rproj\.user$
^\.github$
^docs$
^\.\./docs$
^\.\./scripts$
^\.\./python$
^\.\./data$
^\.\./README\.md$
^README\.Rmd$
^_pkgdown\.yml$
^pkgdown$
```

Create `r/README.md`:
```markdown
# pulso (R)

R interface to Colombia DANE GEIH microdata. Companion to [`pulso-co`](https://pypi.org/project/pulso-co/) Python package.

**Status:** under construction (Agente 5 implementation pending).

## Install (planned)

```r
remotes::install_github("Stebandido77/pulso", subdir = "r")
```
```

Create `r/NEWS.md`:
```markdown
# pulso (development version)

* Initial R skeleton. R port under construction.
```

Create `r/inst/extdata/.gitkeep`:
```
# populated by scripts/sync_data_to_r.R at build time
```

9b. **Root files**:

Create `VERSION`:
```
1.0.0
```

Update root `README.md` (add R section; keep existing Python content). Pattern:
```markdown
# pulso

[existing project blurb]

## Python (`pulso-co`)

```bash
pip install pulso-co
```

See `python/README.md`.

## R (`pulso`)

Under construction. See `r/README.md`.
```

Create `Makefile`:
```makefile
.PHONY: sync-data dev-install test-python test-r build-python clean

sync-data:
	python scripts/sync_data.py

dev-install: sync-data
	cd python && pip install -e ".[dev]"

test-python: sync-data
	cd python && pytest -v

test-r:
	Rscript scripts/sync_data_to_r.R
	cd r && Rscript -e 'devtools::test()'

build-python: sync-data
	cd python && python -m build

clean:
	rm -rf python/dist python/build python/*.egg-info
	rm -rf r/.Rcheck r/*.tar.gz
	rm -rf python/pulso/data r/inst/extdata
```

**Verify:**
```bash
ls r/DESCRIPTION r/NAMESPACE r/README.md r/NEWS.md r/.Rbuildignore r/inst/extdata/.gitkeep
ls VERSION Makefile
cat VERSION   # 1.0.0
```

**Revert:**
```bash
rm -rf r/ VERSION Makefile
git checkout README.md
```

---

## Step 10 — End-to-end verification (THE GATE)

**Atomic:** run the full verification suite. **No merge if any fails.**

10a. **Python tests pass from new layout:**
```bash
python scripts/sync_data.py
cd python && pip install -e ".[dev]"
pytest -v
# All 357 tests must pass.
cd ..
```

10b. **Wheel content identity (Tier 1 — mandatory):**
```bash
cd python && python -m build && cd ..
python scripts/wheel_inventory.py python/dist/pulso_co-1.0.0-py3-none-any.whl > /tmp/wheel-post.txt
diff /tmp/wheel-pre.txt /tmp/wheel-post.txt
# MUST be empty diff. Non-empty = BLOCK MERGE.

# Commit the inventory as the permanent reference for CI:
cp /tmp/wheel-pre.txt docs/internal/r-port/wheel_reference_inventory.txt
git add docs/internal/r-port/wheel_reference_inventory.txt
```

10c. **Wheel bytes identity (Tier 2 — target, may be waived):**
```bash
sha256sum python/dist/pulso_co-1.0.0-py3-none-any.whl
# Compare to b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37
# If equal: PASS.
# If differs: investigate, often hatchling version drift. Document in PR description.
```

10d. **Smoke test: pip install + import:**
```bash
python -m venv /tmp/pulso-smoke
source /tmp/pulso-smoke/bin/activate    # Windows: /tmp/pulso-smoke/Scripts/activate
pip install python/dist/pulso_co-1.0.0-py3-none-any.whl
python -c "import pulso; print(pulso.__version__); print(pulso.list_available().head())"
# Expected: 1.0.0 + non-empty DataFrame
deactivate
```

10e. **R skeleton check:**
```bash
cd r && R CMD check . --no-manual --no-build-vignettes 2>&1 | tail -20
# Expected: 0 errors. WARNINGs about empty NAMESPACE are OK (Agente 5 fills it).
cd ..
```

10f. **`.gitignore` works:**
```bash
git status
# python/pulso/data/ should NOT appear (gitignored)
# python/dist/ should NOT appear (gitignored)
```

**If ALL pass:**

```bash
git add -A
git status   # review
git commit -m "$(cat <<'EOF'
refactor(monorepo): migrate to python/+r/+data/ sibling layout

Closes the planning chain: Agente 1 R Discovery → Agente 2 Design →
Agente 3 Migration. This is the first physically-layout change for the
monorepo (Decision 4 from the discovery report).

What changed:
- pulso/         → python/pulso/      (importable as `import pulso` unchanged)
- tests/         → python/tests/
- scripts/       → python/scripts/    (entry-point CLI tools)
- pyproject.toml → python/pyproject.toml + hatch build hook + pinned hatchling
- pulso/data/    → data/              (canonical top-level)
- New: scripts/sync_data.py           (dev-mode sync into python/pulso/data/)
- New: r/                             (R skeleton — Agente 4+ expands)
- New: VERSION                        (1.0.0, single source of truth)
- New: Makefile, root README sections, top-level .gitignore updates
- CI: ci.yml + release.yml replaced by python-ci.yml + r-ci.yml +
      python-publish.yml + r-check.yml; integration.yml + scrape_monthly.yml
      paths-updated.

Wheel content identity verified Tier 1 PASS:
- Reference SHA256: b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37
- Post-migration SHA256: <computed>
- diff against /tmp/wheel-pre.txt: empty

Tier 2 (bytes-of-zip identity): PASS / WAIVED (see PR description).

All 357 Python tests pass. Smoke install + import works.
R skeleton clean under R CMD check (NAMESPACE empty WARNINGs as expected).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push origin refactor/monorepo-layout
gh pr create --base feat/r-port --title "refactor(monorepo): migrate to python/+r/+data/ sibling layout" \
  --body "..."
```

---

## Reverting the WHOLE migration if Tier 1 fails

If anywhere along the way the gate fails and the issue can't be diagnosed quickly:

```bash
git checkout feat/r-port
git branch -D refactor/monorepo-layout    # destroy the WIP
# nothing else changed; you're back to pre-migration state.
```

If the migration WAS pushed and merged before the issue was caught:

```bash
git checkout main
git revert <merge-commit-sha>             # creates a revert PR
```

The revert is mechanical because every step is `git mv`-based.

---

## Common pitfalls to anticipate

| # | Pitfall | Symptom | Fix |
|---|---|---|---|
| P1 | Editable install + tests fail because `python/pulso/data/` empty | `FileNotFoundError: data/sources.json` | Run `python scripts/sync_data.py` first OR `make dev-install` |
| P2 | Wheel includes `python/pulso/data/.gitkeep` | Tier 1 fails: extra file | Build hook uses `ignore_patterns(".gitkeep")` |
| P3 | hatchling version drift between dev and CI | Tier 2 fails: WHEEL line differs | Pin `hatchling==X.Y.Z` in `[build-system].requires` |
| P4 | `python/scripts/__init__.py` missing → `[project.scripts]` entry-points fail | `pulso-add-month` not found after install | Either add `__init__.py` or update entry to `pulso._scripts.add_month:main` (move scripts under pulso package). Test before commit. |
| P5 | `git mv` on Windows with spaces in path | Permission/path errors | Use the WSL/git-bash provided by the user's setup; don't quote-escape badly |
| P6 | `.Rbuildignore` doesn't ignore parent directories properly | `R CMD check` complains about `../python/` | Use `^\.\./` patterns or absolute exclusion |
| P7 | scrape_monthly.yml writes to wrong path → opens broken PR | Monthly job creates PR with `pulso/data/sources.json` (old path) | Fix the workflow's output path AND the script invocation in step 8d |
| P8 | Old `protected-paths` job gone; some old branches break | First post-migration PR fails | Drop or rename `feat/code-*` branches; document in CONTRIBUTING.md |

---

## Step-time estimates

| Step | Estimate |
|---|---|
| 0  Prereqs | 10 min |
| 1  Empty structure | 2 min |
| 2  Move Python | 5 min |
| 3  Move data | 5 min |
| 4  Edit pyproject.toml | 15 min (careful diffs) |
| 5  hatch_build.py | 20 min (write + test) |
| 6  sync_data.py | 10 min |
| 7  .gitignore | 5 min |
| 8  Workflows | 30 min (careful edits to integration.yml + scrape_monthly.yml) |
| 9  R skeleton + root files | 30 min |
| 10 E2E verification | 30 min (build, run tests, smoke install) |
| **TOTAL** | **~3 hours** focused work |

Plus ~30 min for PR description, review prep, push.

---

## Open questions

**Q8 — Does Agente 3 commit `wheel_reference_inventory.txt` to the repo?**

Yes — it's the gate file CI uses on every PR. Committed alongside the migration PR. Updated only when intentional package contents change (manually regenerated + committed in the same PR).

**Q9 — Should we tag the pre-migration state for safety?**

Recommended: yes. Before step 1: `git tag pre-monorepo-1.0.0`. Cheap insurance to navigate history later.

**Q10 — What if `python/scripts/` entry-points break (P4)?**

If the smoke test (`pulso-add-month --help`) fails after install, the cleanest fix is to move the CLI scripts INTO the package: `python/pulso/_scripts/add_month.py` with entry `pulso._scripts.add_month:main`. This is a slight API change (script directory is now `pulso._scripts`) but the *entry-point binary names* stay identical (`pulso-add-month`, `pulso-validate-sources`). Users see no change.

Agente 3 should test this in dry-run before committing. If it breaks, do the rename inside the migration PR (still under "internal scripts" — no public API change).

---

## Sources

- [git-mv documentation](https://git-scm.com/docs/git-mv)
- [PyPI Trusted Publishing setup](https://docs.pypi.org/trusted-publishers/)
- [Hatch build hook plugin interface](https://hatch.pypa.io/1.9/plugins/build-hook/reference/)
- Reference wheel SHA256: `b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37`
