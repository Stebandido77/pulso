# 07 — Dependency justification for `r/DESCRIPTION`

**Phase:** Mini-Agente 4A
**Status:** Companion to `r/DESCRIPTION` v0.1.0.
**Purpose:** justify each entry in `Imports:` and `Suggests:` so reviewers (and future agents) can audit the dependency footprint against Decision 1 (Lean tidyverse).

---

## TL;DR

- **Imports: 8 packages.** All are stable, actively maintained, with minimal transitive deps. No tidyverse meta-package; we depend on individual leaf packages instead.
- **Suggests: 6 packages.** Only loaded for vignettes, examples, tests, or release tooling. Users can install `pulso` without any of them.
- **Total transitive footprint** on a fresh R install: ~25 packages (including base R recommended packages). Comparable to or smaller than `readr` alone.

---

## Imports (8 deps)

### `httr2` (>= 1.0.0)

HTTP requests with retry, caching headers, OAuth (future). Used in `.download_zip()` to fetch DANE microdata zips.

**Justification:** modern tidyverse-aligned HTTP client; successor to `httr`. Lazy connection setup, async-friendly, integrates with `progressr` for download progress bars. Stable since v1.0 (early 2024). Used by 1000+ CRAN packages.

### `jsonlite` (>= 1.8.0)

Reading `data/sources.json` and `data/dane_codebook.json`.

**Justification:** de facto standard JSON parser for R. Pure C, very few dependencies (only `methods`). Same library used by `httr2` internally, so no extra footprint.

### `tibble` (>= 3.2.0)

Return type of every public function (Decision 7).

**Justification:** non-negotiable per architectural Decision 7. tibble's print method, type coercion rules, and column subsetting semantics are the contract we expose to users. v3.2 is the current stable line.

### `haven` (>= 2.5.0)

`labelled` vectors for per-column metadata (Decision 6). Used by `pulso_load(metadata = TRUE)` to attach DANE labels in a way that survives dplyr verbs and round-trips through SPSS/Stata/SAS file formats.

**Justification:** industry standard for labelled survey data in R. Consumed downstream by `srvyr`, `gtsummary`, `flextable`, etc. — keeping our metadata in `haven::labelled` means users get good interop for free. v2.5 added `labelled_spss` improvements relevant to DANE's SPSS-style coding.

### `vctrs` (>= 0.6.0)

Robust S3 class hierarchy for `pulso_dataframe` and `pulso_metadata`. Used to define `vec_ptype2()` and `vec_cast()` so that `pulso_dataframe` survives `dplyr::bind_rows()`, `tidyr::pivot_*()`, and friends.

**Justification:** the canonical framework for tibble subclasses. Without `vctrs`, our class would silently degrade to a plain tibble after most dplyr verbs, losing the attached metadata.

### `rlang` (>= 1.1.0)

`abort()` for custom error conditions (see `05_r_api_design_final.md` §3). Also `ensym()`/`enquo()` for NSE-friendly arguments in `pulso_describe_column()` (Agente 5).

**Justification:** modern error handling with structured conditions. v1.1+ has `abort(parent = ...)` for chaining. Already a transitive dep of cli, tibble, and vctrs, so no marginal footprint.

### `cli` (>= 3.6.0)

Formatted CLI messages (warnings, info, progress). Used for `cli::cli_abort()` in user-facing errors and `cli::cli_progress_bar()` during downloads.

**Justification:** tidyverse standard for CLI UX. Better than base R `message()` / `warning()` for multi-line errors and bullet lists. v3.6 is current stable. Already a transitive dep of rlang and most tidyverse packages.

### `fs` (>= 1.6.0)

Cross-platform path manipulation. Used for cache directory creation, path normalization in `.resolve_data_path()`, and zip extraction targets.

**Justification:** robust alternative to base R `file.path()` / `normalizePath()` that handles Windows long paths, UNC paths, and trailing-slash quirks consistently. Important because pulso targets Windows users (DANE's audience is heavily Windows). Pure C bindings to `libuv`, no R-level deps.

---

## Suggests (6 deps)

### `dplyr`

Used in vignettes and examples to demonstrate idiomatic post-load workflows. Not loaded by the package itself.

**Justification:** users who consume pulso will almost certainly already have dplyr installed; including it in Suggests rather than Imports keeps the core install lean for users who only need the parser.

### `tidyr`

Same as dplyr — vignettes and examples only.

**Justification:** same reasoning. `tidyr::pivot_longer()` is the obvious example for reshaping GEIH panels.

### `testthat` (>= 3.2.0)

Testing framework. v3.2+ for `expect_no_error()` and improved snapshot testing.

**Justification:** de facto standard for R package testing. Used by `R CMD check`. Edition 3 is enabled in DESCRIPTION (`Config/testthat/edition: 3`).

### `knitr`

Vignette engine.

**Justification:** required because `VignetteBuilder: knitr` is declared. Standard.

### `rmarkdown`

Vignette renderer.

**Justification:** required by knitr's R Markdown engine. Standard.

### `rhub`

CRAN-compliance check pre-submission. Used in CI workflow `.github/workflows/r-check.yml` (already present, references `r/`).

**Justification:** allows running `rhub::check_for_cran()` to surface platform-specific issues (Solaris, M1 Mac, etc.) before submitting to CRAN. Suggests because end users never need it.

---

## Decisions deliberately deferred (NOT added)

These were considered and rejected for v0.1.0; documented here so future agents don't re-litigate.

| Package      | Why considered                              | Why rejected for v0.1.0                                 |
|--------------|---------------------------------------------|---------------------------------------------------------|
| `purrr`      | functional iteration in `pulso_load_merged()` | base `lapply()` + `Reduce()` is sufficient; cuts a dep   |
| `readr`      | CSV parsing                                 | base `read.csv2()` handles DANE's `;`-delimited files; readr would add `vroom` + `tzdb` chain |
| `arrow`      | parquet caching                             | premature; v0.1.0 caches raw zips. Revisit if cache size becomes a problem. |
| `srvyr`      | survey-design-aware analysis                | scope is loading, not analysis. Document in vignette as a recommended downstream package. |
| `here`       | path resolution                             | only useful in scripts, not packages. Use `system.file()` and `rprojroot` (base) instead. |
| `glue`       | string interpolation                        | `cli` already provides `cli::format_inline()` with the same syntax; redundant. |

If a future agent wants to add any of these, document the new use case in this file and update DESCRIPTION in the same PR.

---

## Footprint check (informational)

A fresh `install.packages("pulso", dependencies = "Imports")` on R 4.4 brings in approximately:

```
pulso
├── httr2 → curl, openssl, R6, rappdirs, withr, lifecycle, magrittr
├── jsonlite (no deps)
├── tibble → fansi, lifecycle, magrittr, pillar, pkgconfig, vctrs
├── haven → cli, forcats, hms, lifecycle, readr, rlang, tibble, tidyselect, vctrs
├── vctrs → cli, glue, lifecycle, rlang
├── rlang (no deps)
├── cli (no deps)
└── fs (no deps)
```

Approximate package count: ~25 (base R recommended packages excluded). Comparable to installing `readr` standalone. No heavyweight transitive pulls (no Java, no Python, no Rcpp chains).
