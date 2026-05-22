# Phase 5 — R API Design (preliminary)

**Question:** What should the R-side public API look like, mapped from the existing Python `pulso` 1.0.0 surface?
**Status:** Three style decisions need human approval. The function-by-function mapping is mechanical once those three land.

---

## TL;DR

- **Naming:** snake_case with `pulso_` prefix (`pulso_load`, `pulso_describe_column`).
- **Metadata storage:** `haven::labelled` columns + a top-level `attr(df, "pulso_metadata")` list mirroring `df.attrs`.
- **Return type:** `tibble` (S3, inherits from `data.frame`).
- All public functions take `data.frame` OR `tibble`; never gate on tibble class.

These choices come from Phase 2 (lean tidyverse) and the Phase 1 ecosystem analysis. Detailed mapping table at the end.

---

## Three style decisions

### Decision A — Function naming

**Three live options:**

| Option | Example | Pros | Cons |
|---|---|---|---|
| `pulso_xxx()` | `pulso_load()` | Tidyverse standard. Matches `tidycensus::get_acs()` style. Autocomplete-friendly (type "pul…" → see all). Works without `library(pulso)`. | A bit verbose. |
| `pulsoXxx()` | `pulsoLoad()` | Camel-style; matches some older R packages. | Tidyverse community moved away from this; feels dated. |
| `pulso::xxx()` | `pulso::load()` | Cleanest at call site if user `library(pulso)`-loaded. | Conflicts with base `load()`! Same risk for `merge()`, `expand()`. Dangerous. |

**Recommendation: `pulso_xxx()`** — tidyverse-standard, matches the Python `pulso.load()` mental model when you squint, avoids name collisions with base R primitives like `load`, `merge`, `expand`.

A loud reason against the namespaced approach: `pulso.load()` in Python becomes either `pulso::load()` (clean but masks `base::load`) or `load()` (catastrophically masks `base::load`). Same for `merge`, `expand`. The prefix avoids the entire class of collision.

### Decision B — Metadata storage

**Three live options:**

| Option | What it looks like | Pros | Cons |
|---|---|---|---|
| `attr()` only | `attr(df, "pulso_metadata") <- list(column_metadata = ...)` | Simple. Mirrors Python `df.attrs`. | Lost on most operations (subsetting, joins). Same problem Python has. No first-class column-level support. |
| `haven::labelled` per column | `df$P6020 <- haven::labelled(df$P6020, labels = c(hombre=1, mujer=2), label = "Sexo")` | Industry standard for survey data. Persists through `vctrs`-aware ops. Works with `srvyr`, `gtsummary`, etc. | Doesn't carry top-level metadata (source, epoch, harmonization notes). Needs companion attribute. |
| `list-with-df` | `list(data = df, metadata = list(...))` | Always carries metadata. | Breaks every existing R workflow expecting a data.frame return. Forces users to re-extract `$data`. |

**Recommendation: hybrid `haven::labelled` + top-level `attr()`.**

- Per-column variable label & value labels → `haven::labelled` class (industry standard).
- Top-level provenance/source/epoch → `attr(df, "pulso_metadata") <- list(source_metadata = ..., column_metadata = ..., loaded_at = ...)`.
- Document the same caveat Python documents: top-level attr is lost on `merge`/`bind_rows`. Provide a helper `pulso_attach_metadata(df, source_df)` to copy attrs from one to another.
- Provide `pulso_metadata(df)` accessor and `pulso_strip_metadata(df)` (returns plain tibble).

This gives:
- ✅ Drop-in compatibility with `srvyr::as_survey_design()` (consumes labelled cols correctly).
- ✅ `gtsummary::tbl_summary()` auto-uses variable labels for table headers.
- ✅ `pulso_describe_column(df, "P6020")` reads the per-column label.
- ✅ `pulso_describe(df)` (no col) reads top-level attr for source provenance.
- ✅ Mirrors Python's `df.attrs["column_metadata"]` semantics for the top-level dict.

### Decision C — Return type

**Three live options:**

| Option | Pros | Cons |
|---|---|---|
| `tibble` always | Better default printing for 70k-row microdata. Standard in tidyverse. Inherits `data.frame`. | Tibble subsetting drops to tibble (not vector) by default; surprises base-R users. |
| `data.frame` always | Familiar to all R users. | Ugly default print on large data. |
| Configurable | `pulso.return_type` global option. | More complexity, more bugs. Don't. |

**Recommendation: `tibble` always.**

Mitigation for the subsetting surprise: it's actually rare. `df$col` and `df[["col"]]` work identically on tibbles. The only difference is `df[, "col"]` returns a tibble (1 col) instead of a vector. Document in vignette.

This keeps the API simple. No hidden modes, no "depending on options."

---

## Function-by-function mapping

The Python `pulso` 1.0.0 public surface (from `pulso/__init__.py`):

```python
pulso.load(year, month, module, metadata=False, ...) -> pd.DataFrame
pulso.load_merged(year, month, modules, ...) -> pd.DataFrame
pulso.load_empalme(...) -> pd.DataFrame
pulso.list_available(year=None) -> pd.DataFrame
pulso.list_modules() -> pd.DataFrame
pulso.list_variables() -> pd.DataFrame
pulso.list_validated_range() -> ...
pulso.describe(module, year=None) -> dict
pulso.describe_column(df, column) -> str
pulso.describe_variable(name) -> dict
pulso.describe_harmonization(variable) -> pd.DataFrame
pulso.expand(df, weight=None) -> pd.DataFrame
pulso.list_columns_metadata(df) -> pd.DataFrame
pulso.cache_info() -> dict
pulso.cache_clear(level="all") -> None
pulso.cache_path() -> Path
pulso.data_version() -> str
pulso.validation_status() -> ...
```

**R equivalent:**

| Python | R | Notes |
|---|---|---|
| `pulso.load(year, month, module)` | `pulso_load(year, month, module)` | Same args. Returns tibble. |
| `pulso.load(..., metadata=True)` | `pulso_load(..., metadata = TRUE)` | Attaches `haven_labelled` cols + `attr(df, "pulso_metadata")`. |
| `pulso.load_merged(year, month, modules)` | `pulso_load_merged(year, month, modules)` | `modules` accepts character vector. |
| `pulso.load_empalme(...)` | `pulso_load_empalme(...)` | |
| `pulso.list_available(year=None)` | `pulso_list_available(year = NULL)` | |
| `pulso.list_modules()` | `pulso_list_modules()` | |
| `pulso.list_variables()` | `pulso_list_variables()` | |
| `pulso.list_validated_range()` | `pulso_list_validated_range()` | |
| `pulso.describe(module, year=None)` | `pulso_describe(module, year = NULL)` | Returns S3 `pulso_description` with `print()` method. |
| `pulso.describe_column(df, col)` | `pulso_describe_column(df, col)` | Returns S3 `pulso_column_description`. `print()` matches Python's pretty-print. |
| `pulso.describe_variable(name)` | `pulso_describe_variable(name)` | |
| `pulso.describe_harmonization(var)` | `pulso_describe_harmonization(var)` | Returns tibble. |
| `pulso.expand(df, weight=None)` | `pulso_expand(df, weight = NULL)` | |
| `pulso.list_columns_metadata(df)` | `pulso_list_columns_metadata(df)` | Returns tibble. |
| `pulso.cache_info()` | `pulso_cache_info()` | |
| `pulso.cache_clear(level="all")` | `pulso_cache_clear(level = "all")` | |
| `pulso.cache_path()` | `pulso_cache_path()` | Returns `fs::path` or character. |
| `pulso.data_version()` | `pulso_data_version()` | |
| `pulso.validation_status()` | `pulso_validation_status()` | |
| `df.attrs["column_metadata"]` | `attr(df, "pulso_metadata")$column_metadata` | Same semantics; lost on joins/merges. |
| Exception classes (`PulsoError`, ...) | `rlang::abort()` with classed conditions | See condition mapping below. |

---

## Condition (error) class mapping

Python uses exception classes; R uses S3 condition classes via `rlang::abort()`.

| Python class | R condition class | When |
|---|---|---|
| `PulsoError` | `pulso_error` | Base class; all others inherit. |
| `DataNotAvailableError` | `pulso_data_not_available_error` | Year/month/module not in catalog. |
| `DataNotValidatedError` | `pulso_data_not_validated_error` | User opts in to unvalidated source. |
| `ModuleNotAvailableError` | `pulso_module_not_available_error` | Module doesn't exist for that epoch. |
| `DownloadError` | `pulso_download_error` | HTTP/network failure. |
| `ParseError` | `pulso_parse_error` | DDI XML or CSV parse failure. |
| `ChecksumMismatchError` | `pulso_checksum_mismatch_error` | Downloaded file fails SHA. |
| `HarmonizationError` | `pulso_harmonization_error` | Variable map inconsistency. |
| `MergeError` | `pulso_merge_error` | `load_merged` join key issue. |
| `CacheError` | `pulso_cache_error` | Cache dir / write issue. |
| `ConfigError` | `pulso_config_error` | Bad input arg. |

User code:

```r
# pseudo-code
tryCatch(
  pulso_load(year = 2099, month = 12, module = "ocupados"),
  pulso_data_not_available_error = function(cnd) {
    message("Year not available; skipping.")
    NULL
  }
)
```

---

## What gets included where

The Python public API has **18 functions** + **11 exception classes**.

R port public surface (export list in `NAMESPACE`):

- 18 user functions (`pulso_*`).
- S3 methods: `print.pulso_description`, `print.pulso_column_description`, `format.pulso_description`.
- Optional: `summary.pulso_loaded` if useful.

Internal-only (no export):
- HTTP layer (mirror Python `_core/downloader.py`).
- Parser layer (mirror `_core/parser.py`).
- Codebook composer (mirror `metadata/composer.py`).
- Cache layer (mirror `_utils/cache.py`).

---

## Things the R port should NOT replicate

The Python package has scaffolding that doesn't translate cleanly:

- **`pyproject.toml` `[project.scripts]`** (`pulso-validate-sources`, `pulso-add-month`) — internal CLI tools used only by maintainers. Keep them Python-side; no need to port.
- **`scripts/scrape_cache/`** — DANE catalog scraper. Maintenance tooling, runs on Python. R port doesn't need to scrape; it consumes the resulting `sources.json`/`dane_codebook.json` from `shared/`.
- **`pyreadstat` legacy SPSS/Stata extra** — R's `haven` already reads .sav/.dta natively. Use `haven::read_sav()` / `haven::read_dta()` if/where needed.
- **`pulso/metadata/parser.py` (DDI XML parser)** — could go either way. If we always consume the pre-built `dane_codebook.json` from `shared/`, R never needs to parse DDI. Recommendation: don't port the DDI parser. Treat the codebook JSON as the contract between Python and R.

---

## Vignettes (R "tutorials")

Plan three vignettes for the v1.0.0 R release:

1. **`pulso-getting-started`** — install, `pulso_load()`, simple summary, expand by `fex_c_2011`.
2. **`pulso-metadata`** — `metadata = TRUE`, `haven_labelled` columns, `pulso_describe_column()`, `srvyr` integration showing labels carry through.
3. **`pulso-merging-and-harmonization`** — `pulso_load_merged()`, harmonized variables, `pulso_describe_harmonization()`.

Vignettes go in `r/vignettes/` and are listed in `DESCRIPTION` `VignetteBuilder: knitr`.

---

## Decisions required from human

**Q5 — Naming convention:** `pulso_xxx()` / `pulsoXxx()` / `pulso::xxx()`?

Recommendation: **`pulso_xxx()`** (snake + prefix).

**Q6 — Metadata storage:** `attr()` only / `haven::labelled` only / Hybrid (labelled + top-level attr)?

Recommendation: **Hybrid** — `haven::labelled` per column for variable & value labels, `attr(df, "pulso_metadata")` for top-level provenance.

**Q7 — Return type:** `tibble` / `data.frame` / configurable?

Recommendation: **`tibble`** (always; inherits data.frame).

---

## Sources

- [Tidyverse style guide — naming](https://style.tidyverse.org/syntax.html#object-names)
- [haven CRAN docs](https://cran.r-project.org/web/packages/haven/refman/haven.html)
- [labelled vignette — Larmarange](https://larmarange.github.io/labelled/articles/labelled.html)
- [rlang::abort() — structured conditions](https://rlang.r-lib.org/reference/abort.html)
- Python source: `pulso/__init__.py` (this repo, branch `feat/r-port`)
