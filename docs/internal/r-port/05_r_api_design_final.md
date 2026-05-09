# 05 — pulso (R) API Design Final

**Phase:** Mini-Agente 4A
**Status:** Design contract for Mini-Agentes 4B, 4C, and Agente 5.
**Scope:** complete public API for v0.1.0, S3 class hierarchy, error class hierarchy, naming conventions, path resolution, cache strategy, and Python ↔ R parity table.

---

## TL;DR

- 6 public functions total. Only `pulso_load()` ships in v0.1.0 MVP (Mini-4B). The other 5 are designed here but implemented in Agente 5.
- 2 S3 classes: `pulso_dataframe` (tibble subclass) and `pulso_metadata` (list).
- 4 custom error condition classes, all inheriting from `pulso_error`.
- All public symbols use `pulso_*` snake_case prefix per Decision 5.
- Return type is always tibble per Decision 7. Metadata attached as `attr(df, "pulso_metadata")` per Decision 6.
- Path resolution dual-mode: installed package via `system.file()`, dev mode falls back to `../data/`.

---

## 1. Public functions (6 total for v0.1.0)

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
| `pulso_validation_error`      | argument validation fails (bad year/month/module type or value)              |
| `pulso_data_not_available`    | (year, month) absent from `sources.json` registry                            |
| `pulso_parse_error`           | zip corrupt, expected CSV missing inside zip, encoding unreadable            |
| `pulso_metadata_error`        | codebook download failed, codebook parse error, missing column metadata      |
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

`data/sources.json` and the bundled codebook subset must be reachable both from a development checkout (where `r/` is a sibling of `data/`) and from an installed package (where data has been copied into `inst/extdata/` at build time).

**Resolution order, implemented in `.resolve_data_path(filename)`:**

1. `system.file("extdata", filename, package = "pulso")` — installed package case. If non-empty string, return it.
2. `fs::path_real(file.path(rprojroot::find_package_root_file(), "..", "data", filename))` — dev-mode fallback when running `devtools::load_all()` or `R CMD check` against the source tree. *(Note: rprojroot is base R via `tools` from R 4.0+, so no extra dep needed; or use `here::here()` via Suggests if it simplifies.)*
3. Error: `pulso_data_not_available` with a message pointing to the missing file.

**Build-time data sync.** `r/inst/extdata/` is populated at build time by copying selected files from `data/`. The script that does this is `scripts/sync_data_to_r.R`, referenced by the existing CI workflow but **not yet present in the repo** — it is a known follow-up for Agente 6. For Mini-4B development it is acceptable to manually copy `data/sources.json` into `r/inst/extdata/` and add it to `.gitignore` for `r/inst/extdata/` to avoid duplication; the build hook (Agente 6) will replace this manual step.

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
| `class PulsoDataNotAvailable(Exception)`             | condition class `pulso_data_not_available`               |
| `class PulsoParseError(Exception)`                   | condition class `pulso_parse_error`                      |
| `class PulsoValidationError(Exception)`              | condition class `pulso_validation_error`                 |
| `~/.cache/pulso/` (platformdirs)                     | `tools::R_user_dir("pulso", "cache")`                    |
| `pulso.__version__ == "1.0.0"`                       | `packageVersion("pulso") == "0.1.0"` (independent SemVer per Decision 8) |

---

## 8. Open questions for human approval

These are the same 3 decisions called out in Mini-4A's PR description:

1. **API surface complete?** Are the 6 public functions above the right v0.1.0 surface, or should anything be added/removed/renamed before Mini-4B and Agente 5 lock in?
2. **Signatures locked?** In particular: `pulso_load(metadata = FALSE)` defaults to no metadata; should it default to `TRUE` for parity with the Python side, or is opt-in correct for performance reasons?
3. **Path resolution approach?** Dual-mode (`system.file()` first, then `../data/` fallback) plus a future `scripts/sync_data_to_r.R` build hook — acceptable, or should we adopt a different strategy (e.g., always copy at install time and never read from `../data/`)?

Mini-4B and Agente 5 must not begin until these three are resolved.
