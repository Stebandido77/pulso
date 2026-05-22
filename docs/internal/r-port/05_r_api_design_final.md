# 05 — pulso (R) API Design Final

**Phase:** Mini-Agente 4A
**Status:** Design contract for Mini-Agentes 4B, 4C, and Agente 5.
**Scope:** complete public API for v0.1.0, S3 class hierarchy, error class hierarchy, naming conventions, path resolution, cache strategy, and Python ↔ R parity table.

---

## TL;DR

- 9 public functions total. Only `pulso_load()` ships in v0.1.0 MVP (Mini-4B). The other 8 are designed here but implemented in Agente 5.
- 2 S3 classes: `pulso_dataframe` (tibble subclass) and `pulso_metadata` (list).
- 6 custom error condition classes, all inheriting from `pulso_error`.
- All public symbols use `pulso_*` snake_case prefix per Decision 5.
- Return type is always tibble per Decision 7 (where the function returns tabular data). Metadata-describer functions return lists for Python parity. Metadata attached as `attr(df, "pulso_metadata")` per Decision 6.
- Path resolution split by file size: 4 small JSONs (`sources.json`, `variable_map.json`, `variable_module_map.json`, `epochs.json`) bundled via `inst/extdata/`; `dane_codebook.json` (6.6 MB, exceeds CRAN's 5 MB package size limit) lazy-downloaded to `tools::R_user_dir("pulso", "cache")`.

---

## 1. Public functions (9 total for v0.1.0)

Quick index (full subsections below):

| §    | Function                            | Status        | Mirrors Python                       |
|------|-------------------------------------|---------------|--------------------------------------|
| 1.1  | `pulso_load()`                      | **Mini-4B**   | `pulso.load()`                       |
| 1.2  | `pulso_load_merged()`               | Agente 5      | `pulso.load_merged()`                |
| 1.3  | `pulso_describe_column(df, col)`    | Agente 5      | `pulso.describe_column(df, col)`     |
| 1.4  | `pulso_list_columns_metadata(df)`   | Agente 5      | `pulso.list_columns_metadata(df)`    |
| 1.5  | `pulso_list_validated_range()`      | Agente 5      | `pulso.list_validated_range()`       |
| 1.6  | `pulso_validation_status(year, m)`  | Agente 5      | `pulso.validation_status(year, m)`   |
| 1.7  | `pulso_describe(module, ...)`       | Agente 5      | `pulso.describe(module, ...)`        |
| 1.8  | `pulso_describe_variable(name)`     | Agente 5      | `pulso.describe_variable(name)`      |
| 1.9  | `pulso_list_variables(harmonized)`  | Agente 5      | `pulso.list_variables(harmonized)`   |


### 1.1 `pulso_load()` — IMPLEMENT IN MINI-4B

```r
pulso_load(year, month, module,
           area      = NULL,
           harmonize = TRUE,
           cache     = TRUE,
           metadata  = FALSE)
```

**Arguments:**
- `year` *(integer, required)*. Survey year. Validated against `data/sources.json` registry.
- `month` *(integer, required)*. 1–12. Validated against the same registry for the given year.
- `module` *(character, required)*. One of the GEIH module names: `"ocupados"`, `"desocupados"`, `"inactivos"`, `"caracteristicas_generales"`, `"vivienda"`, `"otros_ingresos"`, etc. Canonical list lives in `data/variable_module_map.json`.
- `area` *(character or NULL, default NULL)*. Optional area filter. Accepted: `"urbano"`, `"rural"`, `NULL` (no filter, both areas concatenated).
- `harmonize` *(logical, default TRUE)*. If TRUE, applies harmonization rules (column renames, type coercions, factor levels). If FALSE, returns raw DANE columns.
- `cache` *(logical, default TRUE)*. If TRUE, caches the downloaded zip in `tools::R_user_dir("pulso", "cache")`. If FALSE, downloads to a temp file each call.
- `metadata` *(logical, default FALSE)*. If TRUE, attaches `pulso_metadata` to the returned tibble (per-column labels via `haven::labelled`, plus top-level `attr(df, "pulso_metadata")`). If FALSE, returns a plain tibble. **In v0.1.0 MVP this argument is accepted but defaults to FALSE; full metadata support lands with Agente 5.**

**Returns:** a tibble. If `metadata = TRUE`, the tibble also carries class `pulso_dataframe`.

**Errors raised** (all inherit from `pulso_error`):
- `pulso_validation_error` — invalid year, month out of range, unknown module, future date.
- `pulso_data_not_available` — year/month combination not in `sources.json`.
- `pulso_parse_error` — zip corrupt, expected CSV missing inside zip, unreadable encoding.

---

### 1.2 `pulso_load_merged()` — Agente 5

```r
pulso_load_merged(year, month, modules, ...)
```

Merges multiple modules for the same year/month into a single tibble (e.g., `c("ocupados", "caracteristicas_generales")`) using DANE's standard household + person identifier keys. Optionally accepts a vector of `(year, month)` pairs to also merge multi-period.

**Returns:** tibble. Schema = union of input modules' columns, joined on identifier keys.

**Errors:** `pulso_data_not_available`, `pulso_parse_error`, plus `pulso_merge_error` if identifier columns are missing or inconsistent across modules.

---

### 1.3 `pulso_describe_column(df, column)` — Agente 5

```r
pulso_describe_column(df, column)
```

Returns a formatted multi-line character string describing a column: its DANE label, type, source module, valid value ranges, factor levels (if categorical), and a link to the codebook section.

**Arguments:**
- `df` — a tibble previously returned by `pulso_load()` (any class).
- `column` — character (column name) or symbol (NSE-friendly via `rlang::ensym()`).

**Returns:** character (length 1, possibly multi-line). Suitable for `cat()`.

**Errors:** `column_not_in_dataframe` (sub-class of `pulso_validation_error`).

---

### 1.4 `pulso_list_columns_metadata(df)` — Agente 5

```r
pulso_list_columns_metadata(df)
```

Returns a tibble with one row per column in `df`, summarizing metadata:

| column | label | type | module | source | has_categories |

Useful for `View()` or `kableExtra::kable()` rendering.

**Returns:** tibble (always; class `tbl_df`).

**Errors:** none — gracefully returns an empty tibble if `df` carries no metadata.

---

### 1.5 `pulso_list_validated_range()` — Agente 5

```r
pulso_list_validated_range()
```

Returns a tibble listing every (year, month) combination present in `data/sources.json`, with validation status:

| year | month | validated | url | sha256 | last_checked |

**Returns:** tibble.

**Errors:** none.

---

### 1.6 `pulso_validation_status(year, month)` — Agente 5

```r
pulso_validation_status(year, month)
```

Returns a list with detailed validation info for a single (year, month):

```r
list(
  validated     = TRUE,
  validated_at  = "2025-12-15T10:23:00Z",
  source        = "https://...",
  sha256        = "b1c6...",
  notes         = "..."
)
```

**Returns:** list.

**Errors:** `pulso_data_not_available` if (year, month) not in registry.

---

### 1.7 `pulso_describe(module, year = NULL, month = NULL)` — Agente 5

R counterpart to Python's `pulso.describe()` (`python/pulso/_config/registry.py:253`). Three call shapes:

- `pulso_describe(module)` — catalog overview across all registered periods (epochs covering the module, validated count, total period count, harmonized variable count, available period range).
- `pulso_describe(module, year)` — year overview (epoch, available months, validated months, comparability notes).
- `pulso_describe(module, year, month)` — specific period detail (epoch, validated flag, sha256 checksum, validated_at, file URL).

**Arguments:**
- `module` *(character, required)*. Canonical module name. If unknown, the error message includes a `did you mean ...?` suggestion (R equivalent of Python's `difflib.get_close_matches()` — use `utils::adist()`).
- `year` *(integer or NULL, default NULL)*. Required when `month` is set.
- `month` *(integer or NULL, default NULL)*. 1–12.

**Returns:** named list. Always contains `module`; remaining keys depend on the call shape.

**Errors:**
- `pulso_validation_error` — `module` not in registry; `month` passed without `year`.
- `pulso_data_not_available` — period not in registry.
- `pulso_module_not_available` — module exists but isn't available for the requested (year, month).

---

### 1.8 `pulso_describe_variable(name)` — Agente 5

R counterpart to Python's `pulso.describe_variable()` (`python/pulso/_config/registry.py:383`).

```r
pulso_describe_variable(name)
```

Returns full metadata for a single canonical (harmonized) variable: type, level, module, Spanish/English descriptions, categories (if categorical), comparability warnings, and per-epoch source-variable mappings.

**Arguments:**
- `name` *(character, required)*. Canonical variable name (matches a key in `data/variable_map.json`).

**Returns:** named list. First element is `canonical_name = name`; remaining elements come from `variable_map.json`. Mirrors the Python dict shape so cross-language users have a parallel mental model.

**Errors:**
- `pulso_validation_error` — `name` not in `variable_map.json`. Error message lists the available variables.

---

### 1.9 `pulso_list_variables(harmonized = TRUE)` — Agente 5

R counterpart to Python's `pulso.list_variables()` (`python/pulso/_config/registry.py:219`).

```r
pulso_list_variables(harmonized = TRUE)
```

Returns a tibble of canonical (harmonized) variables defined in `variable_map.json`.

**Arguments:**
- `harmonized` *(logical, default TRUE)*. If TRUE, only list variables with at least one epoch mapping. If FALSE, list every entry in the variable map (including catalog-only entries with empty mappings).

**Returns:** tibble with columns:

| variable | type | level | module | description_es | description_en | available_in_epochs |

`available_in_epochs` is a list-column (one character vector per row) — same shape as the Python list values, idiomatic R via `tibble`.

**Errors:** none under normal use. Raises `pulso_metadata_error` if `variable_map.json` is missing or malformed.

---

## 2. S3 class hierarchy

### `pulso_dataframe`

A subclass of tibble (`c("pulso_dataframe", "tbl_df", "tbl", "data.frame")`). Created by `pulso_load(metadata = TRUE)` and `pulso_load_merged()`. Carries `attr(., "pulso_metadata")`.

**S3 methods to implement (Agente 5):**
- `print.pulso_dataframe` — same as tibble's print but appends a footer noting metadata is attached and how to access it (`pulso_describe_column()`, `pulso_list_columns_metadata()`).
- `format.pulso_dataframe` — proxies to `format.tbl_df`.
- `[.pulso_dataframe` — preserves class and `pulso_metadata` attribute on column subsetting.
- `as_tibble.pulso_dataframe` — strips the `pulso_dataframe` class, returns plain tibble (for users who want to drop metadata).

### `pulso_metadata`

A list with this structure:

```r
list(
  package_version  = "0.1.0",
  loaded_at        = "2025-12-15T10:23:00Z",
  query            = list(year = 2024, month = 6, module = "ocupados", area = NULL),
  source           = list(url = "...", sha256 = "...", validated_at = "..."),
  columns          = list(
    P6020 = list(label = "...", type = "factor", categories = list(...), module = "ocupados"),
    P6040 = list(label = "Edad", type = "integer", module = "ocupados"),
    ...
  )
)
```

Class vector: `c("pulso_metadata", "list")`.

**S3 methods:**
- `print.pulso_metadata` — pretty-printed summary (CLI-styled via `cli::cli_*`).
- `format.pulso_metadata` — character form for embedding.

Per-column labels are also redundantly attached via `haven::labelled` so they survive haven write/read round-trips, dplyr verbs, and downstream `srvyr`/`gtsummary` consumers (Decision 6).

---

## 3. Error condition class hierarchy

All custom conditions inherit the base class `pulso_error`. The class vector for any abort is:

```
c(<specific>, "pulso_error", "error", "condition")
```

**Specific classes:**

| Class                          | Raised when                                                                  |
|-------------------------------|------------------------------------------------------------------------------|
| `pulso_validation_error`      | argument validation fails (bad year/month/module type or value, unknown variable name in `pulso_describe_variable()`, `month` without `year` in `pulso_describe()`) |
| `pulso_data_not_available`    | (year, month) absent from `sources.json` registry                            |
| `pulso_module_not_available`  | module exists in registry but not for the requested (year, month) — raised by `pulso_describe(module, year, month)` |
| `pulso_parse_error`           | zip corrupt, expected CSV missing inside zip, encoding unreadable            |
| `pulso_metadata_error`        | codebook download failed, codebook parse error, missing column metadata, malformed `variable_map.json` |
| `pulso_merge_error`           | identifier columns missing or inconsistent in `pulso_load_merged()`          |

**Pattern (used everywhere):**

```r
abort_pulso(
  class   = "pulso_data_not_available",
  message = c(
    "x" = "Year 2027, month 6 is not in the validated sources registry.",
    "i" = "Run `pulso_list_validated_range()` to see what is available."
  ),
  year  = 2027,
  month = 6
)
```

`abort_pulso()` is a thin wrapper over `rlang::abort()` (or `cli::cli_abort()`) that prepends `"pulso_error"` to the class vector and ensures the call is captured. Implementation in `r/R/conditions.R` (Mini-4B).

---

## 4. Naming conventions

| Visibility | Convention                                | Example                              |
|------------|-------------------------------------------|--------------------------------------|
| Public     | `pulso_<verb>_<noun>()` snake_case        | `pulso_load()`, `pulso_describe_column()` |
| Internal   | `.<verb>_<noun>()` (leading dot, unexported) | `.validate_year()`, `.download_zip()` |
| S3 method  | `<generic>.<class>`                       | `print.pulso_dataframe`, `format.pulso_metadata` |

Internal helpers are NOT exported in NAMESPACE. They live in `r/R/utils-*.R` files grouped by concern (`utils-validation.R`, `utils-source.R`, `utils-download.R`, `utils-parse.R`, `utils-harmonize.R`).

---

## 5. Path resolution strategy

The repo's `data/` directory holds 5 JSON artifacts that the R package needs at runtime. They split cleanly into two groups by size, and the resolution strategy differs accordingly. CRAN's package size limit is 5 MB total; bundling the codebook would blow past it on its own.

### 5.1 Per-file strategy

| File                          | Size  | Strategy                                                       | Why                                                                          |
|-------------------------------|-------|----------------------------------------------------------------|------------------------------------------------------------------------------|
| `sources.json`                | 300K  | **Bundle** in `r/inst/extdata/`                                | Needed on first call; small; changes infrequently (per release)              |
| `variable_map.json`           | 37K   | **Bundle** in `r/inst/extdata/`                                | Required by `pulso_describe_variable()` and `pulso_list_variables()`         |
| `variable_module_map.json`    | 2.3K  | **Bundle** in `r/inst/extdata/`                                | Required by harmonization in `pulso_load(harmonize = TRUE)`                  |
| `epochs.json`                 | 3.1K  | **Bundle** in `r/inst/extdata/`                                | Required by `pulso_describe(module, year)` epoch lookup                      |
| `dane_codebook.json`          | 6.6M  | **Lazy download** to `tools::R_user_dir("pulso", "cache")`     | Exceeds CRAN's 5 MB total package size limit; only needed for metadata mode  |

Bundled total: ~342 KB — well within CRAN limits even with package source overhead.

### 5.2 Bundled files — resolution order

Implemented in `.resolve_bundled_path(filename)`:

1. `system.file("extdata", filename, package = "pulso")` — installed package case. If the returned string is non-empty (i.e., the file exists), return it.
2. Dev-mode fallback: walk up from the calling file's location (or `getwd()`) until a directory named `data/` containing `sources.json` is found. This handles `devtools::load_all()` and `R CMD check` against the source tree without needing `here` or `rprojroot` as a hard dep.
3. Error: `pulso_metadata_error` with a message pointing to the missing file and how to fix it (`devtools::load_all()` from repo root, or reinstall package).

### 5.3 Lazy-download codebook — resolution order

Implemented in `.resolve_codebook_path()` (Agente 5):

1. Check `tools::R_user_dir("pulso", "cache")/codebook/dane_codebook.json`. If present and not stale (TTL check, default 30 days), return it.
2. If absent or stale: download from a stable GitHub Release asset URL (e.g., `https://github.com/Stebandido77/pulso/releases/download/data-vYYYY.MM/dane_codebook.json`), verify SHA256 against a value pinned in `inst/extdata/codebook_release.json` (small, bundled), write to cache, return path.
3. If offline and no cache present: raise `pulso_metadata_error` with a message instructing the user how to run `pulso_codebook_download()` (Agente 5) when online, or how to point the cache to a manually-downloaded file.

Codebook download is opt-in — only triggered by functions that need it (`pulso_describe_column()`, `pulso_list_columns_metadata()`, and `pulso_load(metadata = TRUE)`). Core functions like `pulso_load(metadata = FALSE)` never trigger a codebook download.

### 5.4 Build-time sync

`r/inst/extdata/` is populated at build time by copying the 4 small files from `data/`. The script that does this is `scripts/sync_data_to_r.R`, referenced by the existing CI workflow but **not yet present in the repo** — it is a known follow-up for Agente 6. For Mini-4B development it is acceptable to manually copy the files into `r/inst/extdata/` and gitignore that directory; the build hook (Agente 6) will replace the manual step.

---

## 6. Cache strategy (full version: Agente 5; minimal version: Mini-4B)

**Location:** `tools::R_user_dir("pulso", which = "cache")`.

This resolves to:
- macOS: `~/Library/Caches/org.R-project.R/R/pulso/`
- Linux (XDG): `$XDG_CACHE_HOME/R/pulso/`
- Windows: `%LOCALAPPDATA%\R\cache\R\pulso\`

**Layout:**

```
<cache_root>/
├── raw/
│   └── <year>/
│       └── <month>/
│           └── <module>.zip
├── codebook/
│   └── dane_codebook.json
└── _meta/
    └── ttl.json                    # last-fetched timestamps per artifact
```

**TTL:** configurable via `options(pulso.cache_ttl_days = ...)`. Default: 30 days. On cache hit older than TTL, re-download (HEAD request to compare ETag/SHA before pulling full body). Mini-4B implements only the read/write part — the TTL+revalidate logic is Agente 5.

**User-facing controls** (Agente 5):
- `pulso_cache_path()` — return cache root as character.
- `pulso_cache_clear(year = NULL, month = NULL, module = NULL)` — selective clear.
- `pulso_cache_size()` — return total bytes cached.

---

## 7. Python ↔ R parity table

| Python (`pulso-co`)                                  | R (`pulso`)                                              |
|------------------------------------------------------|----------------------------------------------------------|
| `pulso.load(2024, 6, "ocupados")`                    | `pulso_load(2024, 6, "ocupados")`                        |
| `pulso.load_merged(...)`                             | `pulso_load_merged(...)`                                 |
| `df.attrs["column_metadata"]`                        | `attr(df, "pulso_metadata")$columns`                     |
| `df.attrs["pulso_metadata"]`                         | `attr(df, "pulso_metadata")`                             |
| `pulso.describe_column(df, "P6020")`                 | `pulso_describe_column(df, "P6020")`                     |
| `pulso.list_columns_metadata(df)` → DataFrame        | `pulso_list_columns_metadata(df)` → tibble               |
| `pulso.list_validated_range()` → DataFrame           | `pulso_list_validated_range()` → tibble                  |
| `pulso.validation_status(2024, 6)` → dict            | `pulso_validation_status(2024, 6)` → list                |
| `pulso.describe(module, year, month)` → dict         | `pulso_describe(module, year, month)` → list             |
| `pulso.describe_variable(name)` → dict               | `pulso_describe_variable(name)` → list                   |
| `pulso.list_variables(harmonized=True)` → DataFrame  | `pulso_list_variables(harmonized = TRUE)` → tibble       |
| `class PulsoDataNotAvailable(Exception)`             | condition class `pulso_data_not_available`               |
| `class PulsoParseError(Exception)`                   | condition class `pulso_parse_error`                      |
| `class PulsoValidationError(Exception)`              | condition class `pulso_validation_error`                 |
| `~/.cache/pulso/` (platformdirs)                     | `tools::R_user_dir("pulso", "cache")`                    |
| `pulso.__version__ == "1.0.0"`                       | `packageVersion("pulso") == "0.1.0"` (independent SemVer per Decision 8) |

---

## 8. Open questions for human approval — RESOLVED

The 3 decisions originally posed in Mini-4A's PR description have been resolved by the user; this section documents the resolution so future agents have the audit trail.

1. **API surface complete?** **Resolved: 9 functions, not 6.** The user added `pulso_list_variables()`, `pulso_describe_variable()`, and `pulso_describe()` for full parity with the Python `_config/registry.py` API (Python `pulso.list_variables`, `pulso.describe_variable`, `pulso.describe`). All three are now documented in §1.7–§1.9.
2. **Signatures locked?** **Resolved: `pulso_load(metadata = FALSE)` default confirmed.** Opt-in metadata kept for Python parity (Python's `load()` does not attach column metadata by default either) and for performance — codebook lookup is non-trivial.
3. **Path resolution approach?** **Resolved: differentiated by file size.** The 4 small JSONs are bundled in `inst/extdata/`; `dane_codebook.json` (6.6 MB, exceeds CRAN's 5 MB package size limit) is lazy-downloaded to `tools::R_user_dir("pulso", "cache")`. Full per-file table and resolution orders are in §5.

Mini-4B may begin once PR #55 is merged to `feat/r-port`.
