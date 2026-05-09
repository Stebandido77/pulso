# 04 — Monorepo Strategy: Python + R in one repo

**Status:** Discovery, pre-decision
**Date:** 2026-05-08
**Audience:** pulso maintainers planning the v1.x R port
**Goal:** Choose how to lay out Python (`pulso-co` on PyPI, importable as `pulso`) and the upcoming R package in a single GitHub repo, informed by how five well-known FOSS projects do it.

---

## 1. Executive summary

Five mature multi-language projects converge on a remarkably consistent pattern:

> **One sibling subdirectory per language at the repo root** (`python/`, `R/` or `R-package/`), **shared assets in language-neutral top-level directories** (`include/`, `cpp/`, `format/`, `docs/`), and **dedicated CI workflow files per language**, all glued by a `Makefile`/`CMakeLists.txt`/shell scripts at the root.

For pulso, that pattern needs one twist: the Python package is **already published** as `pulso-co` with import path `pulso`, so we cannot freely move `pulso/` without breaking installs and importers. The cheapest and least-disruptive layout is to **promote** the existing tree into a `python/` subdirectory, **lift shared JSON data** into a top-level `data/` (or `shared/`) folder, **add a sibling `r/` subdirectory** for the R package, and **split CI** into one workflow file per language (plus shared lint/release).

The R port stays pure-R per the constraint (no reticulate). We accept duplicating some loader logic in R; the prize is independent CRAN releases and an R package that does not require a Python install.

This document is opinionated: I recommend **Option A — Python-at-`python/`, R-at-`r/`, shared data at `data/`** with synchronized SemVer between the two packages but independent release tags (`pulso-py-vX.Y.Z`, `pulso-r-vX.Y.Z`).

---

## 2. Reference repos

### 2.1 facebook/prophet

Top-level layout (https://github.com/facebook/prophet):

```
prophet/
  python/          # the modern PyPI package "prophet"
    prophet/       # __init__.py, forecaster.py, models.py, ...
    pyproject.toml
    setup.py
    stan/          # Stan model files (built into the wheel)
    scripts/
  python_shim/     # legacy "fbprophet" rename shim → imports prophet
    fbprophet/
    setup.py
  R/               # CRAN package "prophet"
    DESCRIPTION
    NAMESPACE
    R/  src/  inst/  man/  tests/  vignettes/
    data-raw/      # generated_holidays.R + generated_holidays.csv
    configure / configure.win
  notebooks/  examples/  docs/
  Makefile
  Dockerfile  docker-compose.yml
```

- **Python at `python/prophet/`**, R at `R/`. Strict siblings.
- **Shared assets:** the Stan model lives at `python/stan/` (Python-only because the R package builds its own copy from `R/inst/stan/`). Generated holiday tables sit at `R/data-raw/generated_holidays.csv`.
- **CI** (https://github.com/facebook/prophet/tree/main/.github/workflows): just two workflows — `build-and-test.yml` and `wheel.yml`. The `build-and-test.yml` is a single matrix that branches into Python and R steps. Smaller project, lighter CI.
- **Release cadence:** synchronized — `prophet` PyPI 1.1.7 maps to CRAN `prophet` 1.0; versions tracked in tandem in repo tags. PR #1844 (https://github.com/facebook/prophet/pull/1844) shows the rename was deliberately handled with the `python_shim/` directory.
- **Metadata:** `python/pyproject.toml` and `R/DESCRIPTION` live side by side, no shared file.
- **R impl:** native R implementation that links to Stan via `rstan`, **not** a Python wrapper.
- **README:** single `README.md` at the root with install instructions for both.
- **Tooling:** root `Makefile`. No bazel/just.

### 2.2 dmlc/xgboost

Top-level layout (https://github.com/dmlc/xgboost):

```
xgboost/
  python-package/    # PyPI "xgboost"
    xgboost/         # the importable package
    pyproject.toml  hatch_build.py  packager/
  R-package/         # CRAN "xgboost"
    DESCRIPTION  NAMESPACE  R/  src/  man/  tests/  vignettes/
    CMakeLists.txt   data/  configure  configure.win
  jvm-packages/      # JVM bindings
  src/               # the C++ library (shared core)
  include/           # C++ headers (shared core)
  amalgamation/      # single-TU C++ build for embed targets
  cmake/             # shared CMake helpers
  plugin/  ops/  tests/
  CMakeLists.txt   # single root build file
  doc/
```

- **Python at `python-package/`**, R at `R-package/`, JVM at `jvm-packages/`. Hyphenated, language suffix.
- **Shared core:** the entire C++ implementation in `src/` + `include/` is consumed by all three bindings. R and Python each have their own thin glue.
- **CI** (https://github.com/dmlc/xgboost/tree/main/.github/workflows): **one workflow file per concern** — `python_tests.yml`, `r_tests.yml`, `jvm_tests.yml`, `python_wheels_variants.yml`, `r_nold.yml`, plus `lint.yml`, `main.yml`, `windows.yml`, `freebsd.yml`, `sycl_tests.yml`. Heavy CI matrix because the C++ core is platform-sensitive.
- **Release cadence:** **synchronized** — major/minor version on PyPI and CRAN match (3.0.x both places). Patch releases sometimes drift but headline number stays in lock.
- **Metadata:** `python-package/pyproject.toml` (generated from `pyproject.toml.in`) and `R-package/DESCRIPTION`.
- **R impl:** native R glue calling shared C++ core via `.Call`. No Python dependency.
- **README:** single root `README.md` covers all bindings; each language dir also has its own short README.
- **Tooling:** root `CMakeLists.txt`, `.pre-commit-config.yaml`.

### 2.3 apache/arrow

Top-level layout (https://github.com/apache/arrow):

```
arrow/
  cpp/             # core C++ library (the real implementation)
  c_glib/          # GLib bindings
  python/          # pyarrow
    pyarrow/       # importable
    pyproject.toml  setup.cfg  MANIFEST.in
    benchmarks/    requirements*.txt
  r/               # CRAN "arrow"
    DESCRIPTION  NAMESPACE  R/  src/  man/  tests/  vignettes/
    data-raw/      # codegen.R, docgen.R (generators, not data)
    Makefile  configure  configure.win
  ruby/  matlab/   # other language bindings
  format/          # the canonical Arrow IPC/columnar spec (.fbs files)
  ci/              # shell + Docker CI scaffolding
  docs/  dev/
  compose.yaml
```

- **Python at `python/`**, R at `r/` (lowercase). Same sibling pattern.
- **Shared assets:** `format/` (the Arrow specification) and `cpp/` (core C++ library) are language-neutral. `docs/` is unified. `ci/` holds shared shell scripts called by per-language workflows.
- **CI** (https://github.com/apache/arrow/tree/main/.github/workflows): **one workflow per language**: `python.yml`, `r.yml`, `r_extra.yml`, `r_nightly.yml`, `cpp.yml`, `cpp_extra.yml`, `cpp_windows.yml`, `ruby.yml`, `matlab.yml`, plus orchestration (`release.yml`, `verify_rc.yml`, `package_linux.yml`).
- **Release cadence:** strictly **synchronized** — Apache foundation does monolithic releases (e.g. Arrow 23.0.0 in Jan 2026 covered all bindings simultaneously). Driven by Apache release management policy, not technical necessity.
- **Metadata:** per-language. `python/pyproject.toml`, `r/DESCRIPTION`.
- **R impl:** native R glue compiled against the same `libarrow` C++ library that pyarrow links to. The `arrow` R package can interoperate with pyarrow via the C Data Interface but does **not require** Python.
- **README:** single root `README.md` plus per-language READMEs.
- **Tooling:** root `compose.yaml`, `pre-commit`, no monorepo build orchestrator — each language stands alone but shares CMake config.

### 2.4 microsoft/LightGBM

Top-level layout (https://github.com/microsoft/LightGBM):

```
LightGBM/
  python-package/    # PyPI "lightgbm"
    lightgbm/  pyproject.toml
  R-package/         # CRAN "lightgbm"
    DESCRIPTION  NAMESPACE  R/  src/  man/  tests/  vignettes/
    data/  configure  configure.win
  src/  include/     # shared C++ core
  swig/              # SWIG bindings (JVM/.NET)
  cmake/             # CMake helpers
  examples/  docs/  tests/
  CMakeLists.txt
  build-cran-package.sh
  build-python.sh
  build_r.R
  VERSION.txt        # ← single source of truth for version!
```

- **Python at `python-package/`**, R at `R-package/`. Same as xgboost.
- **Shared:** `src/` + `include/` C++ core. **`VERSION.txt`** at root is consumed by both packages — the most disciplined version-sync mechanism of all five repos.
- **CI** (https://github.com/microsoft/LightGBM/tree/main/.github/workflows): per-language workflows: `python_package.yml`, `r_package.yml`, `r_configure.yml`, `r_valgrind.yml`, `cpp.yml`, `cuda.yml`, plus `static_analysis.yml`, `swig.yml`. Plus AppVeyor (`.appveyor.yml`) for legacy Windows.
- **Release cadence:** **synchronized via `VERSION.txt`** — both packages read the same number.
- **Metadata:** `python-package/pyproject.toml`, `R-package/DESCRIPTION`. Both inject the version from `VERSION.txt` at build time.
- **R impl:** native R, links to shared C++ core. No Python.
- **README:** root README + per-package READMEs.
- **Tooling:** root `CMakeLists.txt`, plus dedicated build scripts (`build-cran-package.sh`, `build-python.sh`, `build_r.R`).

### 2.5 mlflow/mlflow

Top-level layout (https://github.com/mlflow/mlflow):

```
mlflow/
  mlflow/            # the Python package
    __init__.py  client.py  ...
    R/              # ← R package nested inside the Python package!
      mlflow/
        DESCRIPTION  NAMESPACE  R/  tests/
        Dockerfile.dev  build-package.sh
    typescript/  tracing/  skinny/
  libs/              # auxiliary libraries
  tests/             # Python tests at root
  pyproject.toml     # Python at the root
  pyproject.release.toml
  uv.lock
  docs/  examples/  dev/  docker/
```

- **Python at root** (`mlflow/` package, `pyproject.toml` at root). R **nested inside** the Python tree at `mlflow/R/mlflow/` — this is unusual and reflects mlflow's Python-first history.
- **Shared assets:** none in the strict sense. The R package talks to the MLflow tracking server over **HTTP** (it Imports `httr`, `httpuv`, `jsonlite`), so it doesn't share data files with Python at all. It's a parallel client, not a binding.
- **CI** (https://github.com/mlflow/mlflow/tree/main/.github/workflows): enormous (~80 workflow files). The R-specific one is `r.yml`. Python lives in `master.yml`, `examples.yml`, `cross-version-tests.yml`, etc.
- **Release cadence:** **independent**. CRAN `mlflow` 3.11.2 vs PyPI `mlflow` 3.x — close but not strictly locked. CRAN's slow review cycle forces some lag.
- **Metadata:** `pyproject.toml` at root, `mlflow/R/mlflow/DESCRIPTION` deeply nested.
- **R impl:** native R REST client (uses `httr`, `swagger`); `reticulate` is in `Suggests` only, used optionally for local-mode model serving.
- **README:** single root README.
- **Tooling:** uv (`uv.lock`), root `pyproject.toml`, no shared build system needed because there's no shared C/C++.

---

## 3. Comparison table

| Repo | Python location | R location | Shared resources at | Per-language CI? | Release sync? | R uses Python? | Build orchestrator |
|---|---|---|---|---|---|---|---|
| facebook/prophet | `python/prophet/` (+ `python_shim/` for legacy name) | `R/` | None top-level; Stan in each | One workflow, branched | Tight (manual) | No (Stan via rstan) | Makefile |
| dmlc/xgboost | `python-package/` | `R-package/` | `src/`, `include/`, `cmake/`, `doc/` | Yes (`python_tests.yml`, `r_tests.yml`) | Tight (manual) | No (shared C++) | Root CMake |
| apache/arrow | `python/` | `r/` | `cpp/`, `format/`, `docs/`, `ci/` | Yes (`python.yml`, `r.yml`) | Strict (Apache release) | No (shared C++) | None monorepo-wide |
| microsoft/LightGBM | `python-package/` | `R-package/` | `src/`, `include/`, `cmake/`, `VERSION.txt` | Yes (`python_package.yml`, `r_package.yml`) | Strict (`VERSION.txt`) | No (shared C++) | Root CMake + shell |
| mlflow/mlflow | repo root (`mlflow/` package) | `mlflow/R/mlflow/` (nested) | None (R is REST client) | Yes (`r.yml`) | Loose | No (REST + optional reticulate) | uv |

Pattern recognition:

- **Sibling per-language directories** is the dominant pattern (4 of 5).
- **Per-language CI workflow files** is unanimous once the project is large enough.
- **Shared resources at top-level neutral directories** (`include/`, `format/`, `cpp/`, `data-raw/`) is unanimous when there is anything to share.
- **`VERSION.txt` at root** (LightGBM) is the cleanest version-sync trick.
- **No project requires reticulate.** Even mlflow, which could most easily delegate to Python, uses HTTP instead.
- **No project uses Bazel** for the Python+R combo. Make / CMake / shell scripts dominate.

---

## 4. Recommended structure for pulso

### 4.1 The decision

**Option A: Python-at-`python/`, R-at-`r/`, shared data at `data/`, per-language CI, version-sync via `VERSION` file, independent release tags.**

This mirrors apache/arrow and prophet most closely, scaled down for a small Python+R project with no native compiled core. The reasoning:

1. **No C/C++ core to share.** Pulso's "core" is the JSON catalog (sources, codebook, variable maps). That belongs at the **top level** (`data/`) so neither language owns it. This is the cleanest analog to arrow's `format/` directory.
2. **R must not depend on Python.** Therefore the R package needs its own native loaders for the shared JSON. Duplication of ~200 lines of R loader code is an acceptable tax for clean independence — the same trade arrow, xgboost, and LightGBM all chose.
3. **Existing PyPI users.** `import pulso` must keep working. Moving the source to `python/pulso/` does not change the import path because pyproject's `[tool.setuptools.packages.find]` (or `tool.hatch.build.targets.wheel.packages`) targets the package, not its on-disk parent directory. A user typing `pip install pulso-co` and `import pulso` notices nothing.
4. **Independent release cycles.** Tags `python-v1.0.0` and `r-v0.1.0` let CRAN's slow review (mlflow's pain) not block a Python patch. We sync the **headline** version through a root `VERSION` file (LightGBM-style) but allow patch divergence.

### 4.2 Concrete tree

```
pulso/                                  # repo root
  README.md                             # single root README, links to both packages
  LICENSE
  VERSION                               # single source of truth for semver core (e.g. "1.1.0")
  CHANGELOG.md                          # combined or per-language

  data/                                 # shared, language-neutral
    sources.json
    dane_codebook.json
    variable_map.json
    variable_module_map.json
    empalme_sources.json
    epochs.json
    schemas/
    _scraped_catalog.json               # if still needed; consider .gitignore

  python/                               # Python package "pulso-co"
    pyproject.toml                      # name = "pulso-co"
    pulso/                              # ← UNCHANGED import path
      __init__.py
      _config/
      _core/
      _utils/
      metadata/
      data/                             # symlink OR generated copy of ../data/  at build time
    tests/
    README.md                           # short, points to root
    MANIFEST.in                         # if needed for sdist

  r/                                    # R package "pulso"
    DESCRIPTION                         # Package: pulso, no Python dep
    NAMESPACE
    R/
      sources.R
      codebook.R
      loader.R
      utils.R
    inst/
      extdata/                          # ← R packages MUST ship data here
                                        # populated from ../data/ by a pre-build script
    tests/
      testthat/
    man/
    vignettes/
    .Rbuildignore                       # ignore parent paths
    README.md

  docs/                                 # shared docs, mostly Python today; can host both
    internal/                           # the ADRs and discovery docs (this file lives here)

  scripts/                              # shared build/release helpers
    sync_data_to_python.py              # copies data/ → python/pulso/data/
    sync_data_to_r.R                    # copies data/ → r/inst/extdata/
    bump_version.py                     # rewrites VERSION + pyproject + DESCRIPTION

  .github/
    workflows/
      ci-python.yml                     # tests + lint Python only, paths-filter on python/** + data/**
      ci-r.yml                          # tests + R CMD check, paths-filter on r/** + data/**
      ci-shared.yml                     # data validation, schema lint, runs on data/** changes
      release-python.yml                # triggered by tag python-v*
      release-r.yml                     # triggered by tag r-v*  (CRAN draft + R-universe)
      lint.yml                          # pre-commit, link-checker

  .pre-commit-config.yaml
  Makefile                              # convenience: make test, make build, make sync-data
```

### 4.3 Rationale tied to constraints

| Constraint | How the layout addresses it |
|---|---|
| Both packages in one repo | Sibling `python/` and `r/` at root. |
| Shared data used by both | Single canonical copy at top-level `data/`; build-time sync scripts copy into each package's required location (R cannot read `../data/` at install time, only `inst/extdata/`). |
| Independent releases | Tag prefixes `python-v*` and `r-v*` trigger separate workflows; CHANGELOG can be combined or split. |
| Per-language CI tests | Three GH Actions workflows scoped via `paths:` filters. |
| R cannot depend on Python | `r/` has its own R loaders for `sources.json`/`dane_codebook.json` via `jsonlite`; no `reticulate` import. |
| `import pulso` must not break | Source still at `python/pulso/__init__.py`; `pip install pulso-co` resolves the same wheel content. The directory move is invisible to PyPI consumers. |
| Minimize disruption to importers | Only the **maintainer's** working tree changes; downstream is untouched. |

### 4.4 Version-sync policy

Adopt LightGBM's pattern:

- `VERSION` at root holds the canonical headline (`MAJOR.MINOR`).
- `python/pyproject.toml` reads it at build time (Hatch's `tool.hatch.version.source = "regex"` or a `__version__.py` generated from `VERSION`).
- `r/DESCRIPTION`'s `Version:` field is rewritten by `scripts/bump_version.py`.
- Patch numbers may diverge: Python `1.1.3`, R `1.1.1` is allowed.
- A tagged release of either always corresponds to a frozen `VERSION` snapshot in the same commit.

---

## 5. Migration considerations

The Python package is already on PyPI as `pulso-co`. The migration must be a **single atomic refactor PR** that yields an identical wheel and an identical import path. Steps:

1. **Inventory the current wheel.** `pip download pulso-co==1.0.0 --no-deps`, unzip, list contents. Record exactly which files are in the wheel (especially `pulso/data/*.json`).
2. **Create the new tree** in a feature branch (`refactor/monorepo-layout`):
   - `git mv pulso python/pulso`
   - `git mv tests python/tests`
   - `git mv pyproject.toml python/pyproject.toml`
   - `mkdir data && git mv python/pulso/data/*.json data/`
   - Update `python/pyproject.toml`:
     - `[tool.hatch.build.targets.wheel]` → `packages = ["pulso"]` (Hatch is run from `python/` cwd, so `pulso/` is found relative).
     - Or with setuptools: `[tool.setuptools.packages.find] where = ["."]`.
   - Add `python/scripts/prebuild_copy_data.py` (or hook into `hatch_build.py`) that copies `../data/*.json` into `python/pulso/data/` **before** wheel build. Wheel must contain `pulso/data/*.json` exactly as today.
3. **Verify wheel parity.** Build new wheel, diff `unzip -l old.whl` vs `unzip -l new.whl`. The only acceptable diff is metadata version. The file tree under `pulso/` inside the wheel must be byte-identical.
4. **Set up `r/`** as an empty R package skeleton (`usethis::create_package("r")` then move into `r/`). Add a placeholder `DESCRIPTION` with `Version: 0.0.0.9000` so it doesn't get released yet.
5. **Update CI:**
   - Move existing Python workflow to `.github/workflows/ci-python.yml` and add `paths: ['python/**', 'data/**', '.github/workflows/ci-python.yml']`.
   - Add `ci-r.yml` (using `r-lib/actions/setup-r@v2` and `r-lib/actions/check-r-package@v2`).
   - Add `ci-shared.yml` that runs JSON-schema validation on `data/**`.
6. **Update docs** referencing `pulso/data/` to `data/` (developer docs only — user docs are unaffected because `pulso.metadata.X` import paths don't change).
7. **Adjust `.gitignore` and `MANIFEST.in`** if any. `MANIFEST.in` should include `recursive-include pulso/data *.json` (relative to where build runs).
8. **Cut `pulso-co 1.1.0`** as the first post-refactor release. Same import, same data, no behavior change. Run a smoke test in a clean venv: `pip install pulso-co==1.1.0 && python -c "import pulso; print(pulso.list_sources())"`.
9. **Tag scheme switches** going forward: `python-v1.1.0`, `python-v1.1.1`, ... and (when ready) `r-v0.1.0`.

**Risk mitigations:**

- A `tests/test_wheel_contents.py` that asserts the wheel ships expected files (run in CI on every release).
- A pre-release dry-run job that builds the wheel and `pip install`s it into a fresh container, then runs `import pulso`.
- The `VERSION` file is the only place the canonical version lives — eliminates drift.

---

## 6. Tradeoffs: Option A vs Option B

### Option A (recommended): `python/`, `r/`, `data/` siblings

**Pros**
- Symmetric. Either language can be released, lint-checked, or tested without involving the other.
- Matches the dominant FOSS pattern (arrow, xgboost, LightGBM, prophet).
- Shared `data/` makes the source of truth obvious — no "which copy is authoritative" debate.
- CI paths-filtering is trivial (R PRs don't pay for Python CI minutes and vice versa).
- Future bindings (Stata? Julia? a CLI in Go?) drop in as `stata/`, `julia/`, `cli/` siblings.

**Cons**
- One-time disruption: every `pulso/` path in scripts, READMEs, and developer muscle memory shifts to `python/pulso/`.
- Build-time data sync adds a step. Forgetting to run it before publishing leads to a wheel without data files. Mitigated by the `hatch_build.py` hook + a CI assertion on wheel contents.
- Two CHANGELOGs (or one carefully sectioned one) to maintain.
- Slight friction for "I just want to read the Python source" newcomers — they have to descend one level.

### Option B (alternative): Python-at-root, R-at-`r/` (mlflow style)

Layout:
```
pulso/
  pulso/              # Python package, unchanged
  tests/              # Python tests at root
  pyproject.toml      # at root
  r/                  # R package
    DESCRIPTION  R/  inst/extdata/  ...
  data/               # shared data
  docs/  scripts/  .github/
```

**Pros**
- **Zero disruption** to Python. No moves, no path updates, no risk of breaking the wheel.
- Faster to ship: just add `r/` and a CI workflow, done in a day.
- The "Python is the primary language and R is a port" narrative reads directly off the layout — honest about pulso's history.
- One `pyproject.toml` at root means tools like `pip install -e .`, `ruff`, `pytest`, `uv` work without a `cd python/` step.

**Cons**
- **Asymmetric.** Python is privileged, R is a second-class subdirectory. Every contributor's first impression is "this is a Python repo with an R afterthought."
- If pulso ever adds a third language, it lives in *another* asymmetric subdirectory — eventually the layout drifts toward Option A under pressure (this is exactly mlflow's history; their R subdirectory is acknowledged as a wart).
- Tests at the repo root mix with non-Python concerns; CI paths-filters become awkward (`paths: ['pulso/**', 'tests/**', 'data/**', 'pyproject.toml']` — error-prone).
- `data/` at root is fine, but the Python package will need to either symlink or copy data the same way Option A does, so the work isn't actually saved.
- README cannot pretend the project is multi-language equally — top-level `pyproject.toml` + `pulso/` says "Python first" loud.

### Verdict

**Option A is correct long-term, Option B is correct if shipping the R port in under a week is the only goal.**

Given the team's stated intent to develop both packages seriously and the explicit "independent ability to release each" requirement, Option A pays back its one-time refactor cost within the first quarter. The migration plan in §5 is one PR, ~half a day of work, fully reversible up to merge.

If the team disagrees, Option B is a reasonable fallback. A future migration from Option B to Option A is mechanically identical to today's migration — the `git mv` of Python sources — just done later when more contributors and more downstream importers will feel it.

---

## References

- facebook/prophet: https://github.com/facebook/prophet — `python/`, `R/`, `python_shim/` (rename PR: https://github.com/facebook/prophet/pull/1844)
- dmlc/xgboost: https://github.com/dmlc/xgboost — `python-package/`, `R-package/`, `jvm-packages/`, shared `src/` + `include/`
- apache/arrow: https://github.com/apache/arrow — `python/`, `r/`, shared `cpp/` + `format/`; CI at https://github.com/apache/arrow/tree/main/.github/workflows
- microsoft/LightGBM: https://github.com/microsoft/LightGBM — `python-package/`, `R-package/`, root `VERSION.txt`
- mlflow/mlflow: https://github.com/mlflow/mlflow — Python-at-root, R nested at `mlflow/R/mlflow/`
- Arrow R changelog: https://arrow.apache.org/docs/r/news/
- Arrow 23.0.0 release (Jan 2026): https://arrow.apache.org/release/23.0.0.html
- Apache Arrow release management: https://cwiki.apache.org/confluence/display/ARROW/Release+Management+Guide
- Prophet shim PR: https://github.com/facebook/prophet/pull/1844
