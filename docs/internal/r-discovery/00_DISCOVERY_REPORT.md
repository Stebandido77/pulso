# Pulso R Port — Discovery Report

**Agent:** Agente 1 (R Discovery)
**Date:** 2026-05-08
**Branch:** `feat/r-port`
**Status:** Awaiting human approval on 8 decisions before Agente 2 can begin.

---

## Executive summary

The R ecosystem for survey/microdata loaders has converged on a clear pattern over the last 5 years: **tidyverse-flavored, snake_case, tibbles out, `haven::labelled` for value labels, on-disk caching under a per-user cache dir, and CRAN+GitHub dual distribution.** Pulso-R should ride that pattern rather than re-derive it.

The single most important precedent is **`ipumsr`** (https://tech.popdata.org/ipumsr/): it parses a DDI XML codebook into a structured S3 object, then reads microdata as a tibble whose columns wear `haven::labelled`. That maps almost 1:1 onto Pulso's GEIH situation (codebook + value labels + microdata loader). Pulso-R can lift the architecture wholesale.

Two operational constraints dictate everything else:

1. **The 6.6 MB `dane_codebook.json` cannot ship inside the package** — CRAN's 5 MB limit is strict and exemptions are routinely denied. Solution: lazy-download from a GitHub Release asset into `tools::R_user_dir("pulso", "cache")` on first use, with a small bundled subset for offline first-call.
2. **The Python package is already on PyPI** (`pulso-co` 1.0.0) with import path `pulso`. Any monorepo refactor must produce a byte-identical Python wheel. Recommended layout: `python/`, `r/`, `data/` siblings (apache/arrow + LightGBM pattern). Migration is one ~half-day PR.

Total proposed effort for Agentes 2–6: **3–5 weeks** of build time (reduced from earlier "indefinite" estimates because the architecture is largely a port, not a discovery). Detailed breakdown at end.

---

## Findings by phase

### Phase 1 — R ecosystem precedents (`01_libraries_analysis.md`)

Eight packages surveyed: tidycensus, ipumsr, surveydata, eurostat, wbstats, OECD, imfr, WDI.

- **Style consensus:** snake_case + tibble returns are universal in actively maintained packages from 2020 onward. Only `WDI` and legacy `imfr` still return base data.frames.
- **Two metadata models compete:**
  - (a) `haven::labelled` per column, populated from a parsed codebook (ipumsr's model — works with `srvyr`, `gtsummary`).
  - (b) Separate metadata tibble joined on demand (eurostat, tidycensus).
- **Caching is uniform:** disk-based, opt-in or default-on, under `rappdirs::user_cache_dir()` (older) or `tools::R_user_dir()` (R 4.0+ native).
- **API-key idiom is uniform:** `<pkg>_api_key(install = TRUE)` writing to `~/.Renviron`. Pulso doesn't currently need this; flag for future cloud variant.
- **Bundled-data ceiling:** nobody ships >5 MB. The pattern is lazy-download to cache.
- **Imports range 1–19.** WDI is the lean extreme (only `jsonlite`); eurostat the heavy extreme. Pulso-R should sit in the middle at ~10.

The most consequential takeaway: **adopt ipumsr's architecture pattern** — a `pulso_codebook` S3 object analogous to `ipums_ddi`, with `pulso_load(...)` returning a tibble whose columns carry `haven::labelled` metadata.

### Phase 2 — Tidyverse vs base R (`02_paradigm_choice.md`)

- **Recommendation:** **lean tidyverse** — return tibbles, snake_case names, but minimize hard deps to `tibble`, `vctrs`, `rlang`, `cli`, `haven`, `httr2`, `jsonlite`. Treat `dplyr`/`tidyr` as `Suggests` only.
- Rationale: Colombian R users in this audience (econ + public-health + survey methodologists) overwhelmingly learn through tidyverse. They expect tibble printing and labelled columns. But adding `dplyr` to `Imports` brings ~15 transitive deps for marginal internal benefit (Pulso's internals do little dataframe manipulation).
- **Style guide:** tidyverse style guide (Wickham). Tooling: `styler`, `lintr`, `usethis`.

**Note on tension with Phase 1 recommendation:** The Phase 1 agent suggested `dplyr`+`tidyr` in `Imports` (~10 deps total). I recommend **the leaner profile**. Rationale: Pulso's Python package is deliberately lean (6 hard deps); the R port should match the discipline. Users can `install.packages("dplyr")` themselves.

### Phase 3 — Distribution strategy (`03_distribution_strategy.md`)

- **CRAN's 5 MB rule is binding.** Exemption requests are routinely denied.
- **Codebook gzipped is ~700 KB**, so technically Option B (ship gzipped) would fit. But it locks DANE updates to package release cadence.
- **Recommended:** **Hybrid** — small bundled subset (~500 KB, top ~150 vars) in `inst/extdata/` for offline first-call, plus on-demand download of the full 6.6 MB codebook from a GitHub Release into `tools::R_user_dir("pulso", "cache")`.
- **Phasing:** Phase 1 release (GitHub-only) can use Option B (full codebook bundled, no CRAN). Phase 2 release (CRAN-targeting) switches to Hybrid.
- **Don't use `reticulate`** (Option C). It violates the "no Python dep" constraint.
- **Don't ship subset only** (Option D). It defeats the metadata feature's purpose.

### Phase 4 — Monorepo layout (`04_monorepo_strategy.md`)

Five repos surveyed: facebook/prophet, dmlc/xgboost, apache/arrow, microsoft/LightGBM, mlflow/mlflow.

- **Dominant pattern (4 of 5):** sibling per-language directories (`python/`, `r/`), shared assets at top-level neutral directories, per-language CI workflows.
- **Cautionary tale:** mlflow nests R inside the Python tree at `mlflow/R/mlflow/`; this is widely acknowledged as a wart born of "Python first, R as afterthought" history.
- **Recommended for pulso (Option A):**

  ```
  pulso/
  ├── VERSION                  # canonical semver, LightGBM-style
  ├── data/                    # shared JSON catalog (sources, codebook, maps)
  ├── python/
  │   ├── pyproject.toml       # name = "pulso-co"
  │   ├── pulso/               # ← unchanged import path; data synced at build time
  │   └── tests/
  ├── r/
  │   ├── DESCRIPTION
  │   ├── R/
  │   ├── inst/extdata/        # subset of data/, populated at build time
  │   └── tests/testthat/
  ├── scripts/                 # data sync, version bumper
  ├── docs/internal/           # ADRs, this report
  └── .github/workflows/       # ci-python.yml, ci-r.yml, ci-shared.yml
  ```

- **PyPI compatibility preserved:** the move is `git mv pulso python/pulso` + a hatch hook that copies `data/*.json` into `python/pulso/data/` at build. The wheel is byte-identical to today's; `pip install pulso-co` and `import pulso` are unchanged.
- **Release cadence:** synchronized **headline** version via `VERSION` file; tags `python-v*` and `r-v*` allow patch divergence (CRAN review can lag PyPI without blocking either).
- **Migration cost:** one ~half-day PR. Reversible up to merge.

### Phase 5 — Preliminary R API design (`05_r_api_design.md`)

- **Naming:** `pulso_xxx()` (snake + prefix). Chose this over `pulso::xxx()` because `pulso::load()` would shadow `base::load`, `pulso::merge` would shadow `base::merge`, `pulso::expand` would shadow `base::expand` — all dangerous.
- **Metadata storage:** **hybrid** — `haven::labelled` per column for variable + value labels (industry standard, consumed by `srvyr`/`gtsummary`/etc.), plus `attr(df, "pulso_metadata")` for top-level provenance (mirrors Python's `df.attrs`).
- **Return type:** **tibble** always. Inherits `data.frame`, no surprises for base-R users at `df$col` / `df[["col"]]` access.
- 18 functions to port + 11 condition (error) classes mirroring Python's exception hierarchy.
- Plan for **3 vignettes:** getting-started, metadata, merging-and-harmonization.
- **Don't port:** the Python CLI scripts (`pulso-add-month`, `pulso-validate-sources`), the DDI XML parser (R consumes pre-built `dane_codebook.json` from `shared/data/`), `pyreadstat` legacy SPSS support (R has `haven` natively).

---

## The 8 decisions (with my recommendation for each)

### Decision 1 — R style paradigm

**Question:** Tidyverse / base R / hybrid?

**Recommendation:** **Lean tidyverse** — tibble returns, snake_case names, `haven::labelled` for column metadata, but only `tibble`+`vctrs`+`rlang`+`cli`+`haven`+`httr2`+`jsonlite` in hard `Imports`. `dplyr`/`tidyr` go in `Suggests`.

**Rationale:** Matches user expectations (every actively maintained CRAN analogue from 2020 onward is tidyverse-shaped) without paying the ~15-transitive-dep tax of full tidyverse. Pulso's internals do little dataframe manipulation; we don't need `dplyr` inside.

**Alternative if you disagree:** Full tidyverse (Imports `dplyr`+`tidyr`) — simpler internal code, heavier install. Reasonable if you value internal idiom over user install weight.

### Decision 2 — Distribution channel

**Question:** CRAN / GitHub / both?

**Recommendation:** **Both, phased.** Phase 1 release: GitHub-only via `remotes::install_github()`. Phase 2 release: also on CRAN.

**Rationale:** Phase 1 lets us iterate on API without CRAN's 2–4 week review cycle. Phase 2 adds CRAN once API is frozen — academic users need CRAN for citations + reproducibility. ipumsr, tidycensus, and every survey-data package on the list does both.

**Alternative if you disagree:** CRAN-only from day one — slower iteration. GitHub-only forever — limits academic adoption (Phase 1 ecosystem analysis showed GitHub-only packages get forked + uploaded to CRAN by third parties anyway).

### Decision 3 — Codebook size solution (the 6.6 MB problem)

**Question:** A (runtime download) / B (gzip bundled) / C (reticulate) / D (subset only) / Hybrid?

**Recommendation:** **Hybrid (A + small bundled subset), phased.**

- Phase 1 release (GitHub-only): **Option B alone** — bundle full codebook gzipped (~700 KB). Simple, works offline, fast to ship.
- Phase 2 release (CRAN): **Hybrid** — ~500 KB subset bundled + lazy-download of full 6.6 MB codebook from GitHub Release into `tools::R_user_dir("pulso", "cache")` on first long-tail variable lookup.

**Rationale:** Phase 1 doesn't fight CRAN limits because it's not on CRAN yet. Phase 2 does, with the lightest-touch design (subset gives offline first-call; full codebook fetched on demand). Mirrors how `tidycensus` handles variable lookups.

**Reject:** Option C (reticulate) violates the no-Python-dep constraint. Option D (subset only) silently hides ~85% of codebook variables and defeats the metadata feature.

### Decision 4 — Monorepo structure

**Question:** Sibling layout (`python/` + `r/` + `data/`) / Python-at-root + nested R / split repos?

**Recommendation:** **Sibling layout (Option A).** `python/`, `r/`, `data/` at root, with `VERSION` file and per-language CI workflows.

**Rationale:** Matches apache/arrow, xgboost, LightGBM (the dominant FOSS pattern). Symmetric — neither language is "primary." Future-proof: if pulso adds a Stata or Julia binding, it drops in as another sibling. Migration is one ~half-day PR; the resulting Python wheel is byte-identical to today's, so PyPI users see no change.

**Alternative if you disagree:** **Python-at-root + `r/` subdir** (Option B, mlflow style) — ships R port a week sooner, zero risk of breaking the Python wheel, but encodes "Python primary, R bolt-on" permanently. mlflow's nested `mlflow/R/mlflow/` directory is the cautionary tale.

### Decision 5 — R naming convention

**Question:** `pulso_xxx()` / `pulsoXxx()` / `pulso::xxx()`?

**Recommendation:** **`pulso_xxx()` (snake_case + prefix).**

**Rationale:** Tidyverse-standard, autocomplete-friendly, avoids dangerous collisions: `pulso::load()` would mask `base::load`, `pulso::merge` would mask `base::merge`, `pulso::expand` would mask `base::expand`. The prefix neatly avoids the entire collision class. `pulsoXxx()` is dated camelCase that the modern R community moved away from.

### Decision 6 — Metadata storage on data frames

**Question:** `attr()` only / `haven::labelled` only / Hybrid?

**Recommendation:** **Hybrid: `haven::labelled` per column + `attr(df, "pulso_metadata")` for top-level provenance.**

**Rationale:**
- `haven::labelled` is the industry standard for survey-data variable + value labels. Consumed correctly by `srvyr::as_survey_design()`, `gtsummary::tbl_summary()`, and the entire SPSS/Stata interop stack.
- Top-level `attr()` mirrors Python's `df.attrs["column_metadata"]` semantics, including the same caveat (lost on `merge`/`bind_rows`).
- This is exactly what `ipumsr` does — proven pattern.

### Decision 7 — Return type

**Question:** `tibble` / `data.frame` / configurable?

**Recommendation:** **`tibble` always.**

**Rationale:** Better default printing for 70k-row microdata. Standard in tidyverse. Inherits from `data.frame`, so base-R access patterns (`df$col`, `df[["col"]]`) work identically. The only behavioral difference (`df[, "col"]` returns a 1-col tibble instead of a vector) is rare enough to mention in the vignette and move on. **Don't make it configurable** — global options for return type are a maintenance trap.

### Decision 8 — Versioning between Python and R packages

**Question:** Strictly synchronized / loosely synchronized / fully independent?

**Recommendation:** **Loosely synchronized via root `VERSION` file (LightGBM-style).**

**Rationale:**
- Headline version (`MAJOR.MINOR`) lives in `VERSION` at root. Both `pyproject.toml` and `DESCRIPTION` read it.
- **Patch versions may diverge.** Python `1.1.3`, R `1.1.1` is allowed — CRAN's review lag must not block PyPI bug fixes.
- Tags use prefixes: `python-v1.1.0`, `r-v1.1.0`. Independent release workflows (`release-python.yml`, `release-r.yml`) trigger on the matching tag.
- Strict synchronization (Apache Arrow / xgboost) is overkill for a 2-language project without a shared C/C++ core. Full independence (mlflow) makes user expectations confusing ("which version does what?").

---

## Risks identified

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | Data sync from `data/` → `python/pulso/data/` is forgotten before publishing → wheel ships without codebook | **High** | Hatch build hook automates the copy. CI assertion (`test_wheel_contents.py`) verifies wheel ships expected files. Both run on every release. |
| R2 | Codebook download URL goes stale or GitHub Release deleted accidentally → users on first-install can't fetch | **High** | Bundled subset covers top-150 vars (offline first-call works). Document fallback: manual download path. Pin codebook URL + SHA256 as constants in package. |
| R3 | CRAN reviewer pushes back on lazy-download pattern (rare but happens) | **Medium** | Have Plan B ready: gzipped full codebook in `inst/extdata/` (~700 KB, fits under 5 MB). Phase 1 release uses this anyway, so Plan B is already engineered. |
| R4 | `haven::labelled` columns surprise users when they call `mean(df$P6020)` and get a confusing error | **Medium** | Document `haven::zap_labels()` and `haven::as_factor()` escape hatches in the metadata vignette. ipumsr has the same issue and handles it via docs. |
| R5 | Monorepo migration breaks the Python wheel | **High → Low** | Migration plan includes wheel diff verification step. Smoke-test PR runs `pip install` in clean container + imports `pulso`. Reversible up to merge. |
| R6 | DANE schema changes mid-port require codebook re-build | **Medium** | Codebook is generated artifact (Python's DDI parser); R consumes it as-is. A schema change forces a Python rebuild + new codebook upload to GitHub Release. R unaffected unless schema breaks consuming code. |
| R7 | Disagreement between agents (Phase 1 wanted heavier deps; Phase 2 wanted lean) leads to dep churn after release | **Low** | Resolved in Decision 1: lean tidyverse. Document rationale in `DESCRIPTION` Imports comment so future contributors don't re-add `dplyr`. |
| R8 | First-time R users in air-gapped environments (some Colombian govt offices) can't download codebook on first call | **Medium** | Bundled subset covers top variables. Document offline workflow: download codebook manually + place in cache dir. |
| R9 | CRAN submission rejected for stylistic reasons (ASCII characters, examples timing, etc.) | **Low** | Standard hygiene: `R CMD check --as-cran` clean before submission. Use `usethis::use_release_issue()` checklist. |
| R10 | `tools::R_user_dir` vs `rappdirs` ecosystem disagreement | **Low** | Either works. Decision: use `tools::R_user_dir` (R 4.0+ native, no external dep). If there's strong community pull for `rappdirs`, can switch (one function rewrite). |

---

## Revised effort estimate

Original estimate from project memory: indefinite ("R port: separate project, planned earlier, out of Python scope").

After discovery, **the architecture is largely a port, not a research problem.** Key compressors:

1. ipumsr provides the architectural template (codebook → labelled tibble loader). We don't have to invent it.
2. The DDI XML parser stays in Python. R consumes pre-built `dane_codebook.json`. ~3 days of work avoided.
3. `haven::labelled` solves the metadata storage problem completely. No bespoke class needed.
4. Monorepo migration is one ~half-day PR.

**Revised estimate (Agentes 2–6):**

| Agente | Scope | Estimate |
|---|---|---|
| Agente 2 | Monorepo migration: `git mv` to `python/`, set up `data/`, `r/` skeleton, CI split, wheel-parity test | **0.5–1 day** |
| Agente 3 | R package skeleton: `DESCRIPTION`, `NAMESPACE`, `R/` files, build-time data sync from `data/` → `r/inst/extdata/`, `pulso_load()` MVP returning a tibble | **3–4 days** |
| Agente 4 | Metadata layer: `haven::labelled` integration, `pulso_describe_column()`, `pulso_list_columns_metadata()`, codebook lazy-download (Phase 2 only — Phase 1 uses bundled gzip) | **3–4 days** |
| Agente 5 | Harmonization + merging: `pulso_load_merged()`, `pulso_expand()`, `pulso_describe_harmonization()` | **3–4 days** |
| Agente 6 | Tests, vignettes (×3), pkgdown site, R CMD check clean, GitHub Actions CI green, GitHub-only release tag `r-v0.1.0` | **3–5 days** |

**Total Agentes 2–6:** **3–4 weeks** of build time at one agent at a time. Could compress to ~2 weeks with parallel agents on independent slices (Agente 4 + Agente 5 in parallel).

**Phase 2 (CRAN release of R port):** Add ~1 week for hybrid codebook download + CRAN submission cycle. Trigger only after Phase 1 has user feedback (per project guidance: no urgency).

---

## What happens next

This report is the deliverable for Agente 1. **Agente 2 cannot begin until the human approves all 8 decisions** (or amends them).

Specifically, Agente 2 needs decisions 4 and 8 to act (monorepo structure + version sync). Decisions 1, 5, 6, 7 affect Agente 3's first commit. Decisions 2, 3 are deferrable to Agente 6 (release time).

**Recommended human flow:**
1. Read this report + the 5 phase docs.
2. Skim `01_libraries_analysis.md` (the ipumsr precedent is the most important context).
3. Skim `04_monorepo_strategy.md` §4–§6 (the tree diagram + the migration steps).
4. Approve / amend the 8 decisions.
5. Authorize Agente 2 with the approved decisions inlined into the brief.

---

## Appendix — File index

| File | Purpose |
|---|---|
| `00_DISCOVERY_REPORT.md` | This file. Synthesis + 8 decisions. |
| `01_libraries_analysis.md` | Phase 1: 8-package R ecosystem analysis. |
| `02_paradigm_choice.md` | Phase 2: tidyverse vs base R recommendation. |
| `03_distribution_strategy.md` | Phase 3: how to handle the 6.6 MB codebook on CRAN. |
| `04_monorepo_strategy.md` | Phase 4: 5 reference repos + recommended pulso layout + migration plan. |
| `05_r_api_design.md` | Phase 5: function-by-function Python→R API mapping + 3 style decisions. |

---

## Sources (consolidated)

**R packages surveyed:**
- [tidycensus](https://github.com/walkerke/tidycensus) | [docs](https://walker-data.com/tidycensus/)
- [ipumsr](https://github.com/ipums/ipumsr) | [docs](https://tech.popdata.org/ipumsr/) ← architectural template
- [surveydata](https://github.com/andrie/surveydata)
- [eurostat](https://github.com/rOpenGov/eurostat)
- [wbstats](https://github.com/gshs-ornl/wbstats)
- [OECD](https://github.com/expersso/OECD)
- [imfr](https://github.com/christophergandrud/imfr) (cautionary tale)
- [WDI](https://github.com/vincentarelbundock/WDI) (lean extreme)

**Monorepo references:**
- [facebook/prophet](https://github.com/facebook/prophet)
- [dmlc/xgboost](https://github.com/dmlc/xgboost)
- [apache/arrow](https://github.com/apache/arrow)
- [microsoft/LightGBM](https://github.com/microsoft/LightGBM) ← VERSION file pattern
- [mlflow/mlflow](https://github.com/mlflow/mlflow) (cautionary tale)

**CRAN / R standards:**
- [CRAN Repository Policy](https://cran.r-project.org/web/packages/policies.html)
- [Tidyverse style guide](https://style.tidyverse.org)
- [haven](https://cran.r-project.org/web/packages/haven/refman/haven.html)
- [labelled](https://larmarange.github.io/labelled/articles/labelled.html)
- [piggyback](https://cran.r-project.org/package=piggyback)
- [R Packages 2e — Data chapter](https://r-pkgs.org/data.html)
