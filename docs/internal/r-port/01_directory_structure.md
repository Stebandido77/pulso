# 01 — Directory Structure (Final Monorepo Layout)

**Phase:** Agente 2, Phase 1
**Status:** Design — awaits human approval before Agente 3 executes.

---

## TL;DR

```
pulso/                                    # repo root
├── python/                               # Python package "pulso-co"
│   ├── pulso/                            # importable as `import pulso`
│   ├── tests/
│   ├── scripts/                          # release / scrape / verification
│   ├── pyproject.toml
│   ├── hatch_build.py                    # build hook copies ../../data → pulso/data
│   ├── README.md                         # short, points to root
│   └── .gitignore                        # ignores pulso/data/ (build artifact)
├── r/                                    # R package "pulso"
│   ├── DESCRIPTION
│   ├── NAMESPACE
│   ├── R/                                # empty for Agente 4
│   ├── tests/testthat/                   # empty for Agente 5
│   ├── inst/extdata/                     # codebook subset, populated at build
│   ├── inst/CITATION
│   ├── vignettes/                        # 3 vignettes (Agente 5)
│   ├── man/                              # roxygen2 output
│   ├── README.md
│   ├── NEWS.md
│   └── .Rbuildignore
├── data/                                 # CANONICAL source of truth
│   ├── sources.json
│   ├── dane_codebook.json                # 6.6 MB
│   ├── _scraped_catalog.json
│   ├── empalme_sources.json
│   ├── epochs.json
│   ├── variable_map.json
│   ├── variable_module_map.json
│   └── schemas/                          # 6 .schema.json
├── docs/
│   ├── shared/                           # cross-language guides
│   ├── python/                           # Python-only (mkdocs source)
│   ├── r/                                # R-only (pkgdown source)
│   └── internal/                         # ADRs, agent reports
│       ├── investigations/               # historical (pre-monorepo)
│       ├── metadata/                     # historical
│       ├── r-discovery/                  # Agente 1 R reports
│       └── r-port/                       # Agente 2+ reports (THIS DIR)
├── scripts/                              # cross-language helpers
│   ├── sync_data.py                      # data/ → python/pulso/data/  (dev / editable)
│   ├── sync_data_to_r.R                  # data/ → r/inst/extdata/      (dev / R CMD build)
│   └── bump_version.py                   # rewrites VERSION + pyproject.toml + DESCRIPTION
├── .github/
│   └── workflows/
│       ├── python-ci.yml
│       ├── r-ci.yml
│       ├── python-publish.yml
│       ├── r-check.yml
│       ├── integration.yml               # MOVED, paths-filtered
│       └── scrape_monthly.yml            # MOVED, writes to data/ not pulso/data/
├── README.md                             # root: install Python + install R
├── CHANGELOG.md                          # combined, sectioned by language
├── VERSION                               # canonical headline (e.g. "1.0.0")
├── LICENSE
├── Makefile                              # convenience: make sync-data, make test, make build
└── .gitignore
```

---

## 1. Decision required: how `python/pulso/` accesses `data/`

The user's prompt names three options. Analysis below.

### Option A — Symlink

```
python/pulso/data → ../../data    # symbolic link
```

| Property | Verdict |
|---|---|
| Linux / macOS | ✅ Works. Git supports symlinks via `core.symlinks`. |
| Windows | ❌ Symlinks require Developer Mode or Administrator. Half of contributors on Windows would hit `git checkout` failures or `pip install -e .` finding empty directories. |
| Wheel build | ⚠️ Hatch follows symlinks; wheel ends up with the data files. But cross-platform breakage during dev makes this unworkable. |
| Editable install | ✅ Reads through symlink at runtime. |
| CI on Windows runners | ❌ Same issue. Would need `git config core.symlinks true` + Developer Mode on the runner. |

**Verdict: REJECT.** Cross-platform brittleness disqualifies it for a project with Windows contributors (the user is on Windows 11).

### Option B — Build-time copy via hatch build hook (RECOMMENDED)

```
data/*.json                       # canonical, git-tracked
python/pulso/data/*.json          # gitignored, generated
hatch_build.py                    # copies ../../data → pulso/data before wheel/sdist build
scripts/sync_data.py              # for editable installs and dev use
```

Mechanism (per [Hatch docs](https://hatch.pypa.io/1.9/config/build/) + [Build Hook plugin interface](https://hatch.pypa.io/1.9/plugins/build-hook/reference/)):

```toml
# python/pyproject.toml
[tool.hatch.build.targets.wheel.hooks.custom]
path = "hatch_build.py"

[tool.hatch.build.targets.sdist.hooks.custom]
path = "hatch_build.py"
```

```python
# python/hatch_build.py — pseudo-code, real impl is Agente 3's job
from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from pathlib import Path
import shutil

class SyncDataHook(BuildHookInterface):
    def initialize(self, version, build_data):
        repo_root = Path(self.root).parent  # python/.. == repo root
        src = repo_root / "data"
        dst = Path(self.root) / "pulso" / "data"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
```

| Property | Verdict |
|---|---|
| Linux / macOS / Windows | ✅ Pure Python, cross-platform. |
| Wheel build | ✅ Files end up inside the wheel exactly where they are today. Byte-identity preserved (see `04_wheel_identity_verification.md`). |
| sdist build | ✅ Same hook runs for sdist target. |
| Editable install (`pip install -e .`) | ⚠️ Hatch editable installs **do not** run wheel hooks by default. Mitigation: also register the hook for `editable` target, OR document `python scripts/sync_data.py` as a one-time post-install step. |
| CI | ✅ Trivial — just runs `python -m build` from `python/`. |
| Single source of truth | ✅ `data/` is canonical; `python/pulso/data/` is a generated artifact. |
| R consumption | ✅ R has its own pre-build hook (`scripts/sync_data_to_r.R`) reading from same `data/`. |
| Risk: forgot to sync in editable mode | Medium. `pip install -e .` works but `import pulso` fails when reading missing data files. Mitigation: README + `make dev-install` target that does both. |

**Sub-decision B.1: also register `editable` hook?**
Yes. `[tool.hatch.build.targets.editable.hooks.custom]` ensures `pip install -e .` also populates `pulso/data/`. Same hook file, same `initialize()` method.

**Sub-decision B.2: gitignore `python/pulso/data/`?**
Yes. Otherwise the generated copy and the canonical copy will drift, and someone will edit the wrong one. Gitignored generated artifact + clear comment in `pulso/data/.gitkeep` (or `README.md`) avoids confusion.

### Option C — Runtime path resolution

```python
# pulso/_utils/data_path.py — pseudo-code
def data_dir():
    # Try monorepo dev path first
    monorepo_data = Path(__file__).parent.parent.parent.parent / "data"
    if monorepo_data.exists():
        return monorepo_data
    # Fall back to bundled
    return Path(__file__).parent / "data"
```

| Property | Verdict |
|---|---|
| Wheel build | ❌ Wheel must still bundle data (PyPI users can't access monorepo). So you still need a build hook. C reduces to B + extra runtime fallback code. |
| Editable install | ✅ Reads from monorepo `data/` directly. |
| Code complexity | ⚠️ Adds runtime branching. Tested wheel paths and dev paths diverge. |
| Risk: silent drift | If dev edits `pulso/data/X.json` instead of `data/X.json` and tests use the dev fallback, dev passes but wheel ships stale. |

**Verdict: REJECT as standalone.** Use B exclusively. The runtime fallback complicates code without solving anything that B + sync script doesn't already solve.

### Recommendation

**Option B** (build-time copy via Hatch hook for both `wheel` and `editable` targets, plus `scripts/sync_data.py` for explicit dev sync). `python/pulso/data/` is gitignored.

Why:
- Cross-platform correct (Windows-safe).
- Single source of truth.
- Wheel byte-identity preserved (Hatch's deterministic timestamps + same file contents = same wheel).
- R port uses an analogous R-side script for its own copy into `r/inst/extdata/`.
- Editable mode is handled by registering the hook on the `editable` target plus a Makefile/script for explicit re-sync.

---

## 2. Full tree explanation

### `python/`

| Path | Source | Notes |
|---|---|---|
| `python/pulso/` | `git mv pulso/ → python/pulso/` | The importable package. Import path `pulso` is unchanged. |
| `python/pulso/data/` | Generated | gitignored. Populated by build hook at build time and by `scripts/sync_data.py` at dev time. |
| `python/tests/` | `git mv tests/ → python/tests/` | All 357 tests. Pytest config in `python/pyproject.toml`. |
| `python/scripts/` | `git mv scripts/ → python/scripts/` | Internal scrape/verification scripts. `pulso-add-month`, `pulso-validate-sources`. |
| `python/pyproject.toml` | `git mv pyproject.toml → python/pyproject.toml` + edit | Edit: add `[tool.hatch.build.targets.wheel.hooks.custom]` + `[tool.hatch.build.targets.editable.hooks.custom]` block. Other content unchanged. |
| `python/hatch_build.py` | New | Build hook that copies `../data/` → `pulso/data/`. ~30 lines. |
| `python/README.md` | New (short) | Says "this is the Python implementation of pulso. See repo root README for project overview." |
| `python/.gitignore` | New | `pulso/data/` (generated), `dist/`, `build/`, `*.egg-info/`, `.pytest_cache/`. |
| `python/MANIFEST.in` | Not needed | Hatch doesn't use MANIFEST.in. Existing project doesn't have one either. |

### `r/`

| Path | Source | Notes |
|---|---|---|
| `r/DESCRIPTION` | New (skeleton) | `Package: pulso`, `Version: 0.0.0.9000`, lean tidyverse Imports placeholder. Agente 4 expands. |
| `r/NAMESPACE` | New (empty) | `# Generated by roxygen2: do not edit by hand`. roxygen2 fills it. |
| `r/R/` | New (empty) | Agente 5 fills with `pulso_load.R`, `pulso_codebook.R`, etc. |
| `r/tests/testthat/` | New (empty) | Agente 5 fills with `test-load.R`, etc. |
| `r/inst/extdata/` | Generated (empty for now) | Populated by `scripts/sync_data_to_r.R` (subset codebook + manifest) at R CMD build. |
| `r/inst/CITATION` | New | Pulso citation entry; references DANE GEIH. |
| `r/vignettes/` | New (empty) | 3 vignettes (Agente 5). |
| `r/man/` | New (empty) | roxygen2-generated. |
| `r/README.md` | New | R-specific install + quick example. |
| `r/NEWS.md` | New | R-package changelog (separate from Python's CHANGELOG.md sections). |
| `r/.Rbuildignore` | New | Excludes `^scripts$`, `^docs$`, `^\.github$`, `^README\.Rmd$`, `^_pkgdown\.yml$`, `^docs$`. |

### `data/` (top-level, canonical)

| File | Source | Notes |
|---|---|---|
| `data/sources.json` | `git mv pulso/data/sources.json → data/` | 300 KB |
| `data/dane_codebook.json` | `git mv pulso/data/dane_codebook.json → data/` | 6.6 MB |
| `data/variable_map.json` | `git mv pulso/data/variable_map.json → data/` | 37 KB |
| `data/variable_module_map.json` | `git mv pulso/data/variable_module_map.json → data/` | 2.3 KB |
| `data/epochs.json` | `git mv pulso/data/epochs.json → data/` | 3.1 KB |
| `data/empalme_sources.json` | `git mv pulso/data/empalme_sources.json → data/` | 5.9 KB |
| `data/_scraped_catalog.json` | `git mv pulso/data/_scraped_catalog.json → data/` | 111 KB |
| `data/schemas/*.schema.json` | `git mv pulso/data/schemas/ → data/schemas/` | 6 files, ~28 KB total |

### `docs/`

| Path | Source | Notes |
|---|---|---|
| `docs/shared/` | New (empty initially) | Cross-language overview docs to migrate from `docs/` over time. |
| `docs/python/` | Move existing `docs/*.md` here | Python-specific architecture, harmonization spec. |
| `docs/r/` | New (empty for now) | Agente 5 fills (pkgdown source). |
| `docs/internal/investigations/` | UNMOVED | Historical pre-monorepo agent reports. Keep in place. |
| `docs/internal/metadata/` | UNMOVED | Historical pre-monorepo. Keep in place. |
| `docs/internal/r-discovery/` | UNMOVED | Agente 1 R outputs. Keep in place. |
| `docs/internal/r-port/` | THIS DIR | Agente 2+ outputs. |

### `scripts/` (top-level cross-language)

| File | Purpose |
|---|---|
| `scripts/sync_data.py` | Copy `data/*.json` → `python/pulso/data/`. Cross-platform (uses `pathlib`, `shutil`). Idempotent. Exits 0 on success. |
| `scripts/sync_data_to_r.R` | Copy `data/dane_codebook.json` (and select files) → `r/inst/extdata/`. Generates the codebook subset for the R bundled-fallback (Phase 2). |
| `scripts/bump_version.py` | Read `VERSION`, rewrite `python/pyproject.toml` `version = "..."`, rewrite `r/DESCRIPTION` `Version: ...`. Used by release workflows. |

### `.github/workflows/`

See `03_ci_design.md` for the workflow YAMLs. Six files:
- `python-ci.yml` (replaces existing `ci.yml`)
- `r-ci.yml` (NEW)
- `python-publish.yml` (replaces `release.yml`)
- `r-check.yml` (NEW, placeholder)
- `integration.yml` (MOVED, paths-filtered to `python/**` + `data/**`)
- `scrape_monthly.yml` (MOVED, output path updated to `data/sources.json`)

### Root files

| File | Purpose |
|---|---|
| `README.md` | Single root README. Sections: project overview, Python install (`pip install pulso-co`), R install (TBD post-Agente 5). Links to per-language READMEs. |
| `CHANGELOG.md` | Existing file; update structure to have `## Python` and `## R` sub-sections under each release. |
| `VERSION` | New file. Single line: `1.0.0`. Read by `python/pyproject.toml` (via hatch dynamic version) and `r/DESCRIPTION` (via `scripts/bump_version.py`). |
| `LICENSE` | UNMOVED. Single MIT license covers both packages. |
| `Makefile` | New. Convenience targets: `make sync-data`, `make test-python`, `make test-r`, `make build-python`, `make dev-install`. |
| `.gitignore` | EDITED. Add `python/pulso/data/` (generated), `r/inst/extdata/` (generated), `python/dist/`, `python/build/`, `r/.Rcheck/`, `r/*.tar.gz`. |

---

## 3. What the wheel looks like post-migration

After Agente 3 runs the migration, building from `python/` produces a wheel whose internal structure is byte-identical to today's:

```
pulso/__init__.py                                       (2325 bytes)
pulso/_config/__init__.py                               (83 bytes)
pulso/_config/epochs.py                                 (4959 bytes)
pulso/_config/registry.py                               (16098 bytes)
pulso/_config/variables.py                              (1404 bytes)
pulso/_core/__init__.py                                 (56 bytes)
pulso/_core/downloader.py                               (4809 bytes)
... [same 27 .py files] ...
pulso/data/_scraped_catalog.json                        (113553 bytes)
pulso/data/dane_codebook.json                           (6853633 bytes)
pulso/data/empalme_sources.json                         (6033 bytes)
pulso/data/epochs.json                                  (3174 bytes)
pulso/data/sources.json                                 (306831 bytes)
pulso/data/variable_map.json                            (37384 bytes)
pulso/data/variable_module_map.json                     (2297 bytes)
pulso/data/schemas/*.schema.json                        (6 files)
pulso/metadata/__init__.py                              (1309 bytes)
pulso/metadata/api.py                                   (7178 bytes)
pulso/metadata/composer.py                              (14637 bytes)
pulso/metadata/parser.py                                (10097 bytes)
pulso/metadata/schema.py                                (1891 bytes)
pulso_co-1.0.0.dist-info/METADATA                       (28131 bytes)
pulso_co-1.0.0.dist-info/WHEEL                          (87 bytes)
pulso_co-1.0.0.dist-info/entry_points.txt               (114 bytes)
pulso_co-1.0.0.dist-info/licenses/LICENSE               (1075 bytes)
pulso_co-1.0.0.dist-info/RECORD                         (3629 bytes)
```

**Current wheel SHA256 (for the gate test):**

```
b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37  pulso_co-1.0.0-py3-none-any.whl
```

(Confirmed locally on `dist/pulso_co-1.0.0-py3-none-any.whl`, 418,158 bytes.)

The wheel uses Hatch's deterministic Feb 2, 2020 timestamps for every file, so byte-identity is achievable. Details in `04_wheel_identity_verification.md`.

---

## 4. Cross-cutting decisions baked into this layout

| Question | Answer | Where |
|---|---|---|
| Where do test fixtures live? | `python/tests/fixtures/` (Python) and `r/tests/testthat/_fixtures/` (R). Not shared — fixture formats differ. | by-language |
| Where does mkdocs/pkgdown source live? | `docs/python/` for mkdocs, `docs/r/` for pkgdown. | by-language |
| Single CHANGELOG or per-language? | **Single root `CHANGELOG.md`** with `## Python X.Y.Z` and `## R X.Y.Z` sections. R also has `r/NEWS.md` because CRAN expects it. Cross-link the two. | hybrid |
| Where does `LICENSE` live? | Root only. Both packages reference it. R copies it into `r/LICENSE` on build (CRAN convention). | root |
| Pre-commit config? | Root `.pre-commit-config.yaml`. Hooks: ruff (Python), styler/lintr (R), trailing-whitespace, JSON validation on `data/`. | root |
| Where does `pulso-add-month`, `pulso-validate-sources` live? | `python/scripts/` (already there). `pyproject.toml` `[project.scripts]` paths updated to `python.scripts.add_month:main` etc. **Or simpler:** keep them as `scripts.add_month:main` since hatch builds from `python/` cwd, `scripts/` is a sibling of `pulso/`. Test in Agente 3. | python/ |

---

## 5. Open questions / risks specific to layout

| # | Question | Default plan |
|---|---|---|
| L1 | Hatch's `editable` hook support is less documented than `wheel`/`sdist`. May require `[tool.hatch.envs]` plumbing. | If editable hook doesn't fire, fall back to documented `make dev-install` (runs `pip install -e python/` then `python scripts/sync_data.py`). |
| L2 | `r/inst/extdata/` size limits during R CMD build (pkgdown wants source on disk). | Subset codebook ≤ 500 KB easily fits. Full codebook lives only in user cache (Phase 2 distribution). |
| L3 | `[project.scripts]` entry points (`pulso-add-month`, `pulso-validate-sources`) currently reference `scripts.X:main`. After move, hatch must find them at `python/scripts/X.py`. | Verified by smoke-test in Agente 3 (run `pulso-add-month --help` after `pip install -e python/`). |
| L4 | `docs/internal/` cross-references (existing reports link `pulso/data/X.json`). | Not migrating; old reports remain accurate as snapshots-in-time. New reports reference `data/X.json` going forward. |

---

## Decision required from human

**Q1 — `python/pulso/` access to `data/`: A (symlink), B (build-time copy), C (path resolution)?**

Recommendation: **B (build-time copy via Hatch hook for `wheel` + `sdist` + `editable` targets, plus `scripts/sync_data.py` for explicit dev sync).** `python/pulso/data/` gitignored.

**Q2 — Any structural objections to the tree above?**

Default: proceed as drawn. Specific points the human may want to re-decide:
- `docs/python/` vs `python/docs/`? (Recommended: `docs/python/` — keeps all docs discoverable from one root location.)
- Single `CHANGELOG.md` at root vs per-language? (Recommended: single + per-language `NEWS.md` for R as CRAN expects.)
- `Makefile` vs Python `tasks.py` (Invoke) vs `justfile`? (Recommended: `Makefile` — universally available, matches LightGBM/Arrow style.)

**Q3 — OK to use the 10-step migration plan in `02_migration_plan.md`?**

Default: yes. See that file for atomic/verifiable/reversible step list.

---

## Sources

- [Hatch — Build Hooks](https://hatch.pypa.io/1.9/config/build/) — `[tool.hatch.build.targets.<target>.hooks.custom]`
- [Hatch — Build Hook plugin interface](https://hatch.pypa.io/1.9/plugins/build-hook/reference/)
- [apache/arrow monorepo](https://github.com/apache/arrow) — `cpp/`, `python/`, `r/` siblings
- [microsoft/LightGBM monorepo](https://github.com/microsoft/LightGBM) — `VERSION.txt` pattern
