# 06 — Agente 5 implementation plan

**Phase:** Agente 5 (Discovery + Planning)
**Status:** Awaiting human approval on Section 5 decisions before Mini-5A.
**Scope:** Diagnose all 6 followups in issue #61 and design the 6 remaining v0.1.0 functions from §1.2, §1.5–§1.9 of `05_r_api_design_final.md`.
**Branch:** `feat/r-port` @ `535b205` (post-Agente-4 merge). No new branches in Agente 5 — this doc commits directly to `feat/r-port`. Mini-agents inside Agente 5 will use feature branches.

---

## 1. Executive summary

Agente 5 closes out the v0.1.0 R port in 6 mini-agents over **5–7 working days**:

- **Mini-5A** (1 day): fix the HIGH-priority `.parse_module_csv` bug. Replace fuzzy-grep with explicit lookup via `source_info$modules[[module]]`; dispatch on Shape A (`cabecera`+`resto` concat) vs Shape B (single `file`). This unblocks the vignette and is a prerequisite for every Mini-5C–E function that ever calls `pulso_load()` in tests.
- **Mini-5B** (1 day): the other 5 bug fixes from issue #61 (epoch boundary off-by-one at year 2021, validation order, case-insensitive column lookup, list-valued `source_variable` matching, suppress 99 cosmetic WARN). All independent; can ship as one PR.
- **Mini-5C** (1 day): `pulso_load_merged()` + `pulso_list_validated_range()`.
- **Mini-5D** (1 day): `pulso_validation_status()` + `pulso_describe()`.
- **Mini-5E** (1 day): `pulso_describe_variable()` + `pulso_list_variables()`.
- **Mini-5F** (1 day): tests for the 6 new functions, re-enable vignette R chunks now that `.parse_module_csv` works, optional second vignette on the variable catalog, update DESCRIPTION/NAMESPACE.

**Critical path:** 5A → 5B → (5C, 5D, 5E in any order) → 5F. Mini-5C/D/E can parallelize across human time but each needs `devtools::document()` on the user's R install before push (recurring Mini-4B-1 blocker). Confidence: medium-high. Main risk is the 2024-03 / 2024-04 nested-zip layout the Python `parser.py` handles via `_is_nested_format_wrapper`; deferring that to v0.2.0 with a clear `pulso_parse_error` keeps Mini-5A scope manageable.

---

## 2. Issue #61 bug diagnostics

### 2.1 HIGH: `.parse_module_csv` selects wrong CSV (issue #61 main item)

**Symptom.** `pulso_load(2024, 6, "ocupados")` returns a 37-column DataFrame (`periodo, mes, per, directorio, secuencia_p, ...`) missing the P-coded variables. Vignette `cat(pulso_describe_column(df, "p6020"))` raised `Column 'p6020' is not in the DataFrame` in CI on 4 platforms (now masked by `eval=FALSE` in Fix-4C-v3).

**Location.** `r/R/utils-parse.R:9-42`. The current implementation:

```r
zip_contents <- utils::unzip(zip_path, list = TRUE)$Name
module_pattern <- sprintf("(?i)%s", module)
csv_match <- grep(module_pattern, zip_contents, value = TRUE)
csv_match <- csv_match[grepl("\\.csv$", csv_match, ignore.case = TRUE)]
# ...
csv_name <- csv_match[1]
```

**Root cause.** Fuzzy substring match. For the 2024-06 zip, `module = "ocupados"` matches **both** `CSV/Ocupados.CSV` **and** `CSV/No ocupados.CSV` (the desocupados/inactivos file — same physical file shared by two modules). `csv_match[1]` returns whichever sorts first under the platform's locale; on the CI runners that turned out to be `CSV/No ocupados.CSV`, which is the 37-column admin-heavy file. The bug is silently wrong, not noisy wrong — tests passed because they check generic shape, not column identity.

**Authoritative data.** `r/inst/extdata/sources.json` already encodes the exact file per module:

```json
"2024-06": {
  "epoch": "geih_2021_present",
  "modules": {
    "ocupados":   { "file": "CSV/Ocupados.CSV" },
    "desocupados":{ "file": "CSV/No ocupados.CSV" },
    "inactivos":  { "file": "CSV/No ocupados.CSV" },
    ...
  }
}

"2020-06": {
  "epoch": "geih_2006_2020",
  "modules": {
    "ocupados": {
      "cabecera": "Cabecera - Ocupados.csv",
      "resto":    "Resto - Ocupados.csv"
    },
    ...
  }
}
```

Two shapes appear in the wild: **Shape A** (`cabecera`+`resto` per module, geih_2006_2020 epoch) and **Shape B** (single `file` per module, geih_2021_present epoch).

**Python reference.** `python/pulso/_core/parser.py:353-469` `parse_module()` dispatches on epoch:
1. `is_shape_a(zip_path)` auto-detect → `parse_shape_a_module()` concatenates Cabecera + Resto, then adds a synthetic `CLASE` column for area filtering.
2. Otherwise (`epoch.area_filter is None`, the historical pre-2021 case) → Shape A lookup with explicit paths.
3. Otherwise (Shape B, geih_2021_present) → single-file read; area filter applied later as a row predicate on `CLASE`.

**Proposed fix.**

Replace `.parse_module_csv(zip_path, module)` with `.parse_module_csv(zip_path, module_spec, epoch_info)` where `module_spec = source_info$modules[[module]]` and `epoch_info = .get_epoch(source_info$epoch)`. The call site is `r/R/load.R:54-58`; thread `source_info$modules[[module]]` through.

Logic:

```r
.parse_module_csv <- function(zip_path, module_spec, epoch_info) {
  if (!is.null(module_spec$file)) {
    # Shape B: single file
    return(.read_single_csv_from_zip(zip_path, module_spec$file, epoch_info))
  }
  if (!is.null(module_spec$cabecera) && !is.null(module_spec$resto)) {
    # Shape A: Cabecera + Resto concat with synthetic CLASE
    df_c <- .read_single_csv_from_zip(zip_path, module_spec$cabecera, epoch_info)
    df_c$CLASE <- 1L
    df_r <- .read_single_csv_from_zip(zip_path, module_spec$resto, epoch_info)
    df_r$CLASE <- 2L
    return(rbind(df_c, df_r))
  }
  abort_parse_error(sprintf("Unknown module shape for module spec: %s",
                            paste(names(module_spec), collapse=", ")))
}
```

`.read_single_csv_from_zip()` handles the case-insensitive resolution of the filename inside the zip (handles the `.CSV` vs `.csv` extension variations DANE has used), unzip into temp dir, `utils::read.csv(sep=";", fileEncoding="latin1", ...)`.

**Defer for v0.2.0:** the 2024-03 / 2024-04 nested-zip layout (`CSV.zip` wrapper inside the outer zip) that Python handles via `_is_nested_format_wrapper`. For Mini-5A scope, raise `pulso_parse_error` with a clear message pointing the user to the issue tracker if `.read_single_csv_from_zip()` finds no entries matching the inner path. Affects ~2 periods only.

**Tests.** Need integration tests in `r/tests/testthat/test-load.R`:
- `pulso_load(2024, 6, "ocupados")` returns a DataFrame with ≥ 100 columns and contains `P6020` (case-sensitive, pre-harmonize) or `p6020` (post-harmonize).
- `pulso_load(2024, 6, "desocupados")` returns a different DataFrame than `pulso_load(2024, 6, "ocupados")` (proves the wrong-file bug is gone — both modules used to return the same `No ocupados.CSV` frame).
- `pulso_load(2020, 6, "ocupados")` returns a DataFrame that round-trips Shape A (has `CLASE` column with both 1L and 2L values).

**Effort.** ~4 hours of work for one mini-agent (plus 1–2 hours for tests + manual CI cycle).

---

### 2.2 Epoch boundary off-by-one at year 2021

**Symptom.** `pulso_load(2021, 6, "ocupados", metadata = TRUE)` attaches metadata using the wrong epoch (`geih_2021_present`), so categorical labels and variable mappings for 2021 are read from the post-OIT codebook even though 2021 data is pre-OIT.

**Location.** `r/R/composer.R:18-24`:

```r
.get_epoch_for_year <- function(year) {
  if (!is.numeric(year) || length(year) != 1) {
    abort_validation_error(...)
  }
  if (year >= 2021) "geih_2021_present" else "geih_2006_2020"
}
```

**Root cause.** Hardcoded threshold `year >= 2021`, but `r/inst/extdata/epochs.json:10-13` says `geih_2006_2020` covers `["2006-01", "2021-12"]` and `:42-44` says `geih_2021_present` covers `["2022-01", null]`. The boundary is January 2022, not January 2021. The epoch *name* `geih_2006_2020` is misleading marketing — the canonical range is in `date_range`.

**Python reference.** `python/pulso/_config/epochs.py:118-138` `epoch_for_month()` iterates `epochs.json` and compares `date` objects, no hardcoded year boundary.

**Proposed fix.** Replace with `.get_epoch_for_month(year, month)` that consults `epochs.json` directly. Same caching pattern as `.load_variable_map` (closure-backed cache). Update the two call sites: `r/R/load.R:75` (in `pulso_load`'s metadata block) and `r/R/composer.R:36` (in `.compose_column_metadata`).

The wrapper `.get_epoch_for_year(year)` can be kept as a deprecated thin shim that calls `.get_epoch_for_month(year, 6L)` (mid-year heuristic — wrong only on the boundary month, but at least documented as "approximate") OR removed entirely after the two call sites get the month-aware version. Removal is cleaner.

**Decision:** out-of-range handling. See §5 Q2.

**Tests.**
- `.get_epoch_for_month(2021, 12)` returns `"geih_2006_2020"` (was wrong before).
- `.get_epoch_for_month(2022, 1)` returns `"geih_2021_present"`.
- `.get_epoch_for_month(2006, 1)` returns `"geih_2006_2020"`.
- `.get_epoch_for_month(2200, 1)` raises `pulso_validation_error` (per decision Q2).

**Effort.** 1–2 hours including refactor of call sites.

---

### 2.3 Validation order in `pulso_load`

**Symptom.** If a user calls `pulso_load(year = 2200, month = 6, module = "modulo_inexistente")`, they get `pulso_validation_error` ("year out of range") instead of the more helpful `pulso_module_not_available`. Cosmetic but degrades error UX.

**Location.** `r/R/load.R:34-36`:

```r
.validate_year(year)
.validate_month(month)
.validate_module(module)
```

**Root cause.** Argument validation is in source-text order. Year wins because it fires first.

**Python reference.** `python/pulso/_core/loader.py` validates module against the registry early (it's a string lookup that catches typos before any network work). Both orderings are defensible; Python's choice is "module first" because the registry is the source of truth.

**Proposed fix.** Reorder to `module → year → month`. Update one test in `r/tests/testthat/test-load.R` that asserts on the error class for the both-invalid case.

**Effort.** 15 minutes including test update.

---

### 2.4 `.find_canonical_name` doesn't match list-valued `source_variable`

**Symptom.** ~5% of Curator entries in `variable_map.json` have list-valued `source_variable` (derived variables like `ingreso_total = ["INGLABO", "P7500S1A1", ...]`). `pulso_describe_column(df, "INGLABO")` returns "no metadata" instead of the `ingreso_total` canonical entry.

**Location.** `r/R/utils-curator.R:50`:

```r
if (identical(mapping$source_variable, column_code)) {
  return(canonical_name)
}
```

**Root cause.** `identical()` is element-wise strict — won't match a string against a list. The brief specifically called this out (the original Mini-4B-2 brief used `identical()` to match Python's literal behavior, but Python's `==` *does* match a string against a list of strings via the `in` operator in the actual reference impl).

**Python reference.** `python/pulso/metadata/composer.py` walks `variable_map`, but for source_variable lookups it tests both `source == column_code` and `column_code in source` (the latter handles the list case).

**Proposed fix.** Replace the single `identical()` with a two-branch test:

```r
sv <- mapping$source_variable
matched <- if (is.list(sv) || (is.character(sv) && length(sv) > 1)) {
  column_code %in% unlist(sv, use.names = FALSE)
} else {
  identical(sv, column_code)
}
if (matched) return(canonical_name)
```

**Tests.** Use an entry in `variable_map.json` with list-valued `source_variable` (need to find one — pick from real data). Test that `.find_canonical_name("INGLABO", "geih_2006_2020")` returns the canonical name (e.g., `"ingreso_total"`).

**Effort.** ~1 hour including finding a real list-valued entry for the test.

---

### 2.5 `pulso_describe_column` case-sensitivity

**Symptom.** After default `harmonize = TRUE`, column names are lowercased. Users following the Python example (`pulso.describe_column(df, "P6020")`) get `Column 'P6020' is not in the DataFrame` because the column is now `p6020`. This is what made Fix-4C-v2 surface a deeper bug.

**Location.** `r/R/describe.R:25`:

```r
if (!column %in% names(df)) {
  abort_validation_error(...)
}
```

**Root cause.** Strict `%in%` comparison.

**Python reference.** Python is case-sensitive too in `pulso.describe_column()` — but Python's `harmonize=True` keeps the original codes uppercase (no `tolower()` in their harmonizer). The R port chose to lowercase via `r/R/load.R:62`, which created the divergence. Either fix is valid:
- A. Match Python: stop lowercasing in `harmonize = TRUE`.
- B. Keep R lowercase, make lookup case-insensitive.
- C. Both: case-insensitive lookup AND document that R lowercases.

**Recommendation: C** — gentlest UX. Lowercase output is idiomatic R for tibbles (matches `janitor::clean_names()`), and a case-insensitive lookup is a one-line change.

**Proposed fix.**

```r
match_col <- names(df)[tolower(names(df)) == tolower(column)]
if (length(match_col) == 0) {
  abort_validation_error(...)
}
column <- match_col[1]  # use the actual stored name from here on
```

Also update `r/R/load.R:24` example in the Roxygen comment to use lowercase (consistent with how R works post-harmonize).

**Tests.** `pulso_describe_column(df, "p6020")` and `pulso_describe_column(df, "P6020")` both succeed on a harmonized DataFrame.

**Effort.** ~30 minutes.

---

### 2.6 Cosmetic: 99 testthat WARN from grep on non-ASCII filenames

**Symptom.** `[ FAIL 0 | WARN 99 | SKIP 0 | PASS 73 ]` — does not block R CMD check but is noise. Caused by non-ASCII filenames like `SAV/Migración.SAV` inside the DANE zip; `grep()` and `grepl()` on `Sys.getlocale()` non-UTF locales emit `input string N is invalid` / `unable to translate to wide string`.

**Location.** `r/R/utils-parse.R:10-14` (the `unzip(list = TRUE)` followed by `grep`). After Mini-5A removes the fuzzy grep entirely and replaces it with explicit lookup, the issue may disappear naturally because no `grep()` runs on the zip contents.

**Proposed fix.** If Mini-5A removes the grep — no work needed. If `.read_single_csv_from_zip()` still calls `grep()` for case-insensitive filename resolution (it should, to handle `.CSV` vs `.csv`), wrap that single call in `suppressWarnings()` with a comment explaining why.

**Tests.** Spot check `[ WARN 0 ]` or near-zero on at least one platform after Mini-5A.

**Effort.** Folds into Mini-5A; ~0 incremental.

---

## 3. New function designs (6 functions)

### 3.1 `pulso_load_merged(year, month, modules, ...)`

**Signature.**
```r
pulso_load_merged(year, month, modules,
                  area     = NULL,
                  harmonize= TRUE,
                  cache    = TRUE,
                  metadata = FALSE,
                  how      = c("outer", "inner"))
```

**Returns.** tibble; class `pulso_dataframe` if `metadata = TRUE`. Schema = union of inputs' columns, joined on epoch merge keys.

**Python reference.** `python/pulso/_core/merger.py:57-...` `merge_modules()`. Uses `epoch.merge_keys_persona = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]` for persona-level modules and `merge_keys_hogar = ["DIRECTORIO", "SECUENCIA_P"]` for hogar-level. Auto-detects level by inspecting which keys are present.

**Logic.**
1. Validate `modules` is a length ≥ 1 character vector of known modules.
2. Resolve epoch via `.get_epoch_for_month(year, month)`.
3. For each module: call `pulso_load(year, month, module, area, harmonize, cache, metadata = FALSE)` and stash in a named list.
4. Detect per-module level (persona vs hogar) by checking key presence (helper `.detect_level(df, epoch)`).
5. Multi-level merge:
   - All persona-level dfs → merge on `c("directorio","secuencia_p","orden")` (lowercased if `harmonize=TRUE`).
   - All hogar-level dfs → merge on `c("directorio","secuencia_p")`.
   - LEFT JOIN hogar result into persona result on `c("directorio","secuencia_p","hogar")` if both exist. See decision Q4 for hogar+persona mixing policy in v0.1.0.
6. If `metadata = TRUE`, compose metadata for the merged frame.

**Edge cases.**
- Single module: just returns that module's DF (don't error — be permissive). Or error with "use `pulso_load`" — see Q5.
- Module missing keys: `pulso_merge_error`.
- Different sample sizes after merge: expected (outer join), not an error.

**Tests.** Merge `ocupados` + `caracteristicas_generales` for 2024-06; assert resulting tibble has columns from both. Merge invalid module combo (e.g., one persona one hogar where Q4 says error) and assert `pulso_merge_error`.

**Effort.** 4–6 hours including helper extraction.

---

### 3.2 `pulso_list_validated_range()`

**Signature.**
```r
pulso_list_validated_range()
```

**Returns.** tibble with columns `(year, month, validated, validated_by, validated_at, source_url, sha256, size_bytes, epoch)`. One row per (year, month) entry in `sources.json`.

**Python reference.** `python/pulso/_config/registry.py:` look for `list_validated_range` (around line 200 based on the function index in registry.py).

**Logic.**
1. Load `sources.json` via existing `.load_sources()`.
2. `purrr::imap_dfr(sources$data, ~ tibble::tibble(year = ..., month = ..., validated = .x$validated, ...))`.
3. Arrange by (year, month).

**Edge cases.** Empty registry → empty tibble with correct columns. NULL `validated_at` → NA character.

**Tests.** Returned tibble has the expected columns, has at least 1 row, has at least 1 row with `validated == TRUE` and at least 1 with `validated == FALSE`.

**Effort.** 1–2 hours.

---

### 3.3 `pulso_validation_status(year, month)`

**Signature.**
```r
pulso_validation_status(year, month)
```

**Returns.** Named list: `list(year, month, validated, validated_by, validated_at, source_url, sha256, size_bytes, epoch, scraped_at)`.

**Python reference.** `python/pulso/_config/registry.py:` `validation_status(year, month)`.

**Logic.**
1. Validate year/month.
2. `info <- .resolve_source(year, month)` (existing helper; raises `pulso_data_not_available` if absent).
3. Return as a named list.

**Edge cases.** Year/month not in registry → `pulso_data_not_available` (existing behavior of `.resolve_source`).

**Tests.** `pulso_validation_status(2024, 6)$validated == TRUE`. `pulso_validation_status(1900, 1)` raises `pulso_data_not_available`.

**Effort.** 30 minutes.

---

### 3.4 `pulso_describe(module, year = NULL, month = NULL)`

**Signature.**
```r
pulso_describe(module, year = NULL, month = NULL)
```

**Returns.** Named list. Three call shapes covered in `05_r_api_design_final.md` §1.7.

**Python reference.** `python/pulso/_config/registry.py:253` `describe()`.

**Logic.**
1. Validate `module` against `variable_module_map.json` keys; on miss, raise `pulso_validation_error` with `utils::adist()`-based "did you mean ...?".
2. If `month` set without `year`: `pulso_validation_error`.
3. Three branches:
   - `(module)` only: aggregate across all periods — epochs covered, validated count, total count, harmonized variable count, available range.
   - `(module, year)`: filter to year — epoch, months available, validated months, comparability notes (from epochs.json notes).
   - `(module, year, month)`: single-period detail — epoch, validated flag, sha256, validated_at, file URL. If module not in that period: `pulso_module_not_available`.

**Edge cases.** Module exists globally but not in a specific period's modules dict → `pulso_module_not_available` per the design.

**Tests.** Three test cases (one per call shape) for `module = "ocupados"`. Two error tests (unknown module suggestion; month without year).

**Effort.** 3–4 hours including the suggestion logic.

---

### 3.5 `pulso_describe_variable(name)`

**Signature.**
```r
pulso_describe_variable(name)
```

**Returns.** Named list. First element `canonical_name = name`; remaining elements from `variable_map.json[[name]]`.

**Python reference.** `python/pulso/_config/registry.py:383`.

**Logic.**
1. Load `variable_map.json` via existing cached `.load_variable_map()`.
2. If `name` not in `names(variable_map)`: `pulso_validation_error` listing available variables (truncate at e.g. 20 with "and N more").
3. Return `c(list(canonical_name = name), variable_map[[name]])`.

**Edge cases.** None beyond the missing-name case.

**Tests.** Pick a real canonical name from `variable_map.json` (e.g., `"sexo"`). Assert returned list has expected keys. Assert unknown name raises `pulso_validation_error`.

**Effort.** 1–2 hours.

---

### 3.6 `pulso_list_variables(harmonized = TRUE)`

**Signature.**
```r
pulso_list_variables(harmonized = TRUE)
```

**Returns.** tibble with columns `(variable, type, level, module, description_es, description_en, available_in_epochs)`. `available_in_epochs` is a list-column (character vector per row).

**Python reference.** `python/pulso/_config/registry.py:219`.

**Logic.**
1. Load `variable_map.json`.
2. For each canonical_name: extract `(type, level, module, description_es, description_en)` and compute `available_in_epochs = names(entry$mappings)`.
3. If `harmonized = TRUE`: filter to rows where `length(available_in_epochs) > 0` (variable has at least one epoch mapping).
4. Return tibble.

**Edge cases.** Empty variable_map → empty tibble. Variable with `mappings = list()` → `available_in_epochs = character(0)`; filtered out when `harmonized = TRUE`.

**Tests.** `nrow(pulso_list_variables()) > 0`. With `harmonized = FALSE`, count is ≥ count with `harmonized = TRUE`.

**Effort.** 1–2 hours.

---

## 4. Mini-agent breakdown

### Mini-5A — Fix `.parse_module_csv` (HIGH priority)

**Scope.** Replace fuzzy-grep with explicit module-spec dispatch on Shape A / Shape B. Thread `source_info$modules[[module]]` through `pulso_load`. New helper `.read_single_csv_from_zip()`. Defer 2024-03/04 nested-zip layout to v0.2.0 with a clear error.

**Files modified.**
- `r/R/load.R` — signature of `.parse_module_csv` call site at L54.
- `r/R/utils-parse.R` — rewrite `.parse_module_csv`; add `.read_single_csv_from_zip`.
- `r/inst/extdata/sources.json` — possibly add a `nested_zip: true` flag for 2024-03/04 if we want to detect-and-error cleanly. See Q1.

**Files created.** None.

**Tests added** (in `r/tests/testthat/test-load.R`):
1. `pulso_load(2024, 6, "ocupados")` returns ≥ 100 columns; column `p6020` present.
2. `pulso_load(2024, 6, "desocupados")` returns a different column set than `pulso_load(2024, 6, "ocupados")`.
3. `pulso_load(2020, 6, "ocupados")` returns a frame with both `clase = 1` and `clase = 2` rows (Shape A concat).
4. Periods 2024-03 and 2024-04 raise `pulso_parse_error` with a message mentioning v0.2.0 (until we implement nested-zip).

**`devtools::document()` needed?** No (no Roxygen on `.parse_module_csv`, internal only).

**Dependencies.** None — first mini in Agente 5.

**Duration.** 1 day.

---

### Mini-5B — 5 remaining bug fixes from issue #61

**Scope.** Bundle the 5 small, independent fixes from §2.2–2.6 into one PR.

**Files modified.**
- `r/R/composer.R` — replace `.get_epoch_for_year` with `.get_epoch_for_month`.
- `r/R/load.R` — reorder validation; update `.get_epoch_for_month` call.
- `r/R/utils-curator.R` — fix list-valued source_variable matching.
- `r/R/describe.R` — case-insensitive column lookup.
- `r/R/utils-parse.R` — wrap one grep in `suppressWarnings()` if WARN remains after Mini-5A.

**Files created.** None.

**Tests added.**
- `.get_epoch_for_month` boundary tests (2021-12 → geih_2006_2020, 2022-01 → geih_2021_present, 2200-01 → error).
- `pulso_load` validation order test (invalid module + invalid year → `pulso_module_not_available`).
- `.find_canonical_name("INGLABO", "geih_2006_2020")` returns a canonical name.
- `pulso_describe_column(df, "P6020")` works on a lowercase-harmonized frame (case-insensitive).
- Spot check WARN count near zero.

**`devtools::document()`?** No (all internal helpers).

**Dependencies.** Best to land after Mini-5A so the integration tests in §2.5 actually have a real frame to test against. Could ship parallel as a separate PR if you accept the small race risk.

**Duration.** 1 day.

---

### Mini-5C — `pulso_load_merged` + `pulso_list_validated_range`

**Scope.** Two functions: one heavy (merger), one trivial (registry dump). Pairing them in one mini because the trivial one is too small to ship alone.

**Files modified.**
- `r/R/load.R` — add `pulso_load_merged()` (or new file `r/R/load-merged.R`).
- `r/NAMESPACE` — `export(pulso_load_merged)`, `export(pulso_list_validated_range)`.
- `r/man/` — new `.Rd` files (via `devtools::document()`).

**Files created.**
- `r/R/load-merged.R` (preferred over expanding `load.R`).
- `r/R/registry.R` — host `pulso_list_validated_range()` and `pulso_validation_status()` if grouped (or land 5.3 here too).
- `r/tests/testthat/test-load-merged.R`.
- `r/tests/testthat/test-registry.R`.

**Tests added.** ~6 new (per §3.1 and §3.2).

**`devtools::document()`?** YES — user-side R install required. Same Mini-4B-1 friction.

**Dependencies.** Depends on Mini-5A (`pulso_load` must work for `pulso_load_merged` to work).

**Duration.** 1 day.

---

### Mini-5D — `pulso_validation_status` + `pulso_describe`

**Scope.** Two functions: trivial (status) + medium-complex (describe with three call shapes + adist suggestion).

**Files modified.**
- `r/R/registry.R` — add both functions (or split if 5C consolidated registry-style functions).
- `r/NAMESPACE` — exports.
- `r/man/` — new `.Rd` files.

**Files created.** `r/tests/testthat/test-describe-module.R` (or merge with 5C's `test-registry.R`).

**Tests added.** ~5 new (per §3.3 and §3.4).

**`devtools::document()`?** YES.

**Dependencies.** Independent of 5C and 5E once 5A+5B land. Could parallelize with 5C if user authorizes 2 mini-agents concurrently — but each still needs a user-side `devtools::document()` round, which serializes anyway.

**Duration.** 1 day.

---

### Mini-5E — `pulso_describe_variable` + `pulso_list_variables`

**Scope.** Two functions, both read-only against `variable_map.json`.

**Files modified.**
- `r/R/variables.R` (new file) or `r/R/list-metadata.R` (existing).
- `r/NAMESPACE`.
- `r/man/`.

**Files created.** `r/tests/testthat/test-variables.R`.

**Tests added.** ~4 new (per §3.5 and §3.6).

**`devtools::document()`?** YES.

**Dependencies.** Independent.

**Duration.** 1 day.

---

### Mini-5F — Tests + vignette re-enable + cleanup

**Scope.** Quality pass.

**Files modified.**
- `r/vignettes/pulso.Rmd` — remove `eval = FALSE` from R chunks (no longer needed once Mini-5A unblocks `pulso_load`). Verify Python chunk stays Python (display-only).
- `r/DESCRIPTION` — re-evaluate `Suggests` vs `Imports` for `haven`, `vctrs`, `cli`, `digest` based on actual usage post-5A–5E.
- `r/_pkgdown.yml` (new optional) — site config if we want a docs site.

**Files created.**
- Optional second vignette `r/vignettes/variables.Rmd` walking through the canonical variable catalog using `pulso_list_variables()` + `pulso_describe_variable()` + `pulso_describe()`.
- `r/tests/testthat/test-vignette-renders.R` — uses `tools::buildVignette()` to fail-fast if vignette breaks.

**Tests added.** Vignette render check; integration test covering full happy path (`pulso_load` → `pulso_describe_column` → `pulso_list_variables`).

**`devtools::document()`?** Maybe (if DESCRIPTION changes affect roxygen).

**Dependencies.** Runs LAST, after 5A–5E all land.

**Duration.** 1 day.

---

## 5. Decisions needed from user (before Mini-5A)

### Q1. `.parse_module_csv` scope: how far to go in Mini-5A?

**Options.**
- A. **Shape A + Shape B with explicit lookup from `source_info$modules`; defer nested-zip with clear `pulso_parse_error`.** Period coverage: 2007-2024 except 2024-03 and 2024-04.
- B. Shape A + Shape B + nested-zip (parity with Python). Period coverage: all of 2007-current_year.
- C. Replace `.parse_module_csv` entirely with a thin shim around the Python parser (e.g., via `reticulate`). Reduces parity risk but adds Python-on-PATH dependency.

**Recommendation: A.** Nested-zip is 2 periods only, Python's `_is_nested_format_wrapper` is ~30 lines of code but the case-resolution helpers around it are another ~50. Get to green CI first, ship the nested-zip support in v0.2.0 alongside the deferred Shape A auto-discovery edge cases.

**Blast radius.** A: 2024-03 and 2024-04 raise `pulso_parse_error` (currently they raise nothing helpful — silently return wrong file). B: full feature parity but +1 day on Mini-5A budget. C: opens a runtime Python dependency that contradicts Decision 4 (R as standalone package).

---

### Q2. `.get_epoch_for_month` out-of-range behavior

**Options.**
- A. **Raise `pulso_validation_error`** (Python's `epoch_for_month` raises `ConfigError`).
- B. Return NULL silently; caller handles.
- C. Return the latest known epoch with a warning.

**Recommendation: A.** Python parity, fail-fast, doesn't propagate bad epoch downstream to metadata composition. The current silent-default behavior is a real bug — `pulso_load(2200, 6, "ocupados", metadata = TRUE)` would attach metadata using the post-OIT codebook for a clearly impossible year.

**Blast radius.** A: any caller passing far-future or pre-2006 years gets a clear error. B/C: keeps backward "compat" but with garbage metadata.

---

### Q3. `pulso_describe_column` case handling

**Options.**
- A. Stop lowercasing in `harmonize = TRUE` (match Python).
- B. Keep lowercasing; document explicitly that R is lowercase post-harmonize.
- C. **Keep lowercasing AND make column lookup case-insensitive.**

**Recommendation: C.** Lowercase output matches `janitor::clean_names()` idioms and survey-packages conventions (`srvyr`, `gtsummary`). Case-insensitive lookup is a one-line `tolower()` comparison and handles the cross-language user (Python user reading the docs and typing `"P6020"`). Update Roxygen example to use lowercase for the canonical R style.

**Blast radius.** C: better UX. Slight cost: column-resolution helper has to remember which column name was *actually* stored, since downstream metadata lookup needs the post-harmonize string.

---

### Q4. `pulso_load_merged` hogar + persona mixing in v0.1.0

**Options.**
- A. **Error with `pulso_merge_error` if the user requests both a hogar module and a persona module.** Defer hogar→persona LEFT JOIN to v0.2.0.
- B. Implement the full multi-level merge (persona modules merged among themselves; hogar modules merged among themselves; hogar LEFT JOINed into persona). Python parity.

**Recommendation: A.** Multi-level merge is a meaningful design decision that Python evolved over multiple releases. v0.1.0 should ship persona-only merging and hogar-only merging cleanly, with a clear error message pointing to v0.2.0 for mixed merges. The 80/20 use case (econometrics on labor market) is all-persona modules anyway.

**Blast radius.** A: ships 80% of use cases in one mini-agent. B: doubles Mini-5C scope to ~2 days.

---

### Q5. `pulso_load_merged(modules = c(...))` missing-period policy

**Options.**
- A. Fail-fast on any module missing for the requested (year, month).
- B. **Fail-fast when `modules` is explicit; best-effort when `modules = NULL` (Python parity).** `NULL` means "all available", in which case missing modules just get skipped silently with an info message.
- C. Always best-effort; emit a warning per missing module.

**Recommendation: B.** Matches Python's behavior — explicit ask = explicit expectation; implicit "all" = explicit tolerance. C is too quiet for a function whose output shape (column set) silently varies with availability.

**Blast radius.** B: predictable for both call patterns. A: surprising for the `modules = NULL` shorthand. C: silent data-shape drift.

---

## 6. Estimated total effort

| Mini | Duration | Critical path | Notes |
|------|----------|---------------|-------|
| 5A   | 1 day    | yes           | Blocks 5B, 5C; unblocks vignette |
| 5B   | 1 day    | yes           | Depends on 5A for test data |
| 5C   | 1 day    | partially     | Can start after 5A; needs `document()` |
| 5D   | 1 day    | partially     | Independent of 5C/5E once 5A+5B land |
| 5E   | 1 day    | partially     | Independent |
| 5F   | 1 day    | yes           | Runs last |
| **Total** | **5–7 days** | | Conservative sequential: 6 days. With user parallelizing 5C∥5D∥5E (each still needs serialized `document()` cycle on user's R): 5 days. |

**Confidence.** Medium-high.

**Main risks.**
1. **User-side R for `devtools::document()`** — recurring blocker from Mini-4B-1, hits Minis 5C, 5D, 5E, possibly 5F.
2. **Nested-zip 2024-03/04** — if Q1 lands on Option B, +1 day on Mini-5A.
3. **`pulso_load_merged` complexity** — if Q4 lands on Option B (full multi-level merge), Mini-5C doubles in scope.
4. **DANE schema drift** — if any new periods land in `sources.json` between Agente 5 start and Mini-5F, integration tests may need updates. Low probability over 5–7 days.

**Stop rule.** After each mini-agent completes its PR, stop and await user authorization before launching the next, same pattern as Agentes 2–4.
