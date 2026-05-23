# pulso Pre-CRAN Smoke Test — Bugs Found

**Test date:** 2026-05-23  
**Python:** 3.12.9 / pulso 1.0.0rc1 (NOTE: rc1, not final)  
**R:** 4.5.2 / pulso 0.1.0  
**Periods tested:** 17 (all 17 from spec)  
**Modules tested:** up to 8 per period  

---

## CRAN-BLOCKER Bugs

### BUG-004 — [CRITICAL] R: All epoch1 data completely fails
**Component:** R  
**Severity:** Critical  
**Affects:** ALL `geih_2006_2020` periods (2007-01 through 2021-12) — 14 years of data

**Symptom:**
```
Error in rbind(deparse.level, ...) :
  numbers of columns of arguments do not match
Calls: pulso_load -> .parse_module_csv -> rbind -> rbind
```

**Evidence:** Reproduced on every tested epoch1 period:
- 2007-12 (validated): ALL 6 modules fail
- 2015-06 (validated): ALL 6 modules fail  
- 2021-12 (validated): ALL 6 modules fail
- 2007-01, 2010-06, 2013-01, 2018-09 (unvalidated): ALL fail

**Root cause:** epoch1 ZIPs contain one CSV per city/area. These CSVs have different column counts (some areas have extra columns). Base `rbind()` refuses to combine DataFrames with mismatched column counts.

**Fix:** Replace `rbind()` with `dplyr::bind_rows()` or `data.table::rbindlist(fill=TRUE)` in `.parse_module_csv`.

---

### BUG-003 — [HIGH] R: UTF-8 filenames in ZIP crash on Windows
**Component:** R  
**Severity:** High (CRAN-blocker on Windows)  
**Affects:** `caracteristicas_generales` and `migracion` modules in ALL epoch2 periods

**Symptom:**
```
Error in utils::unzip(zip_path, files = resolved, exdir = temp_dir) :
  invalid multibyte string at '<a1>sti'   # from "Características"
  invalid multibyte string at '<a2>n.C'   # from "Migración"
```

**Evidence:** Reproduced on every tested epoch2 period that has these modules:
- 2022-01 (validated): `caracteristicas_generales` fails, `migracion` fails
- 2024-06 (validated): same
- 2023-03, 2025-01: same

Meanwhile Python handles these modules without errors.

**Root cause:** `utils::unzip()` on Windows cannot handle UTF-8 encoded filenames inside ZIP archives (specifically the accented characters ó, ó, í in "Características generales..." and "Migración").

**Fix:** Use `zip::unzip()` from the `zip` package which has proper Unicode support on Windows, or strip accents before filename comparison.

---

### BUG-008 — [MEDIUM, CRAN-blocker] R: `harmonize=TRUE` adds zero canonical columns
**Component:** R  
**Severity:** Medium — but a CRAN documentation blocker  
**Affects:** All periods where R loads data successfully

**Symptom:** Python `pulso.load(..., harmonize=True)` adds 5-13 canonical columns (`cotiza_pension`, `departamento`, `hogar_id`, `horas_trabajadas_sem`, `ingreso_laboral`, `ocupacion`, `peso_expansion`, `peso_expansion_persona`, `posicion_ocupacional`, `rama_actividad`, `tiene_contrato`, `tipo_contrato`). R `pulso_load(..., harmonize=TRUE)` adds zero canonical columns — the parameter is silently ignored.

**Evidence:**
```
# 2024-06 ocupados:
# Python:  29925 rows × 213 cols (200 raw + 13 canonical)
# R:       29925 rows × 200 cols (200 raw, 0 canonical added)
# 2024-06 desocupados:
# Python:  25605 × 46 cols (37 raw + 9 canonical)
# R:       25605 × 37 cols
# p_coded counts match (confirming same raw data), only canonical cols differ
```

**Fix:** Implement canonical column mapping in R's `.apply_harmonization()` function.

---

## High Severity Bugs

### BUG-001 — [HIGH] Python: `TypeError` on `allow_unvalidated=True` for any period with `checksum_sha256=null`
**Component:** Python  
**Severity:** High  
**Affects:** All unvalidated periods (12 of 17 tested)

**Symptom:**
```
TypeError: 'NoneType' object is not subscriptable
  File "pulso/_core/downloader.py", line 84, in download_zip
    short = checksum[:16]
```

**Evidence:** Reproduced on: 2020-06, 2023-03, 2024-03, 2024-04, 2025-01, 2025-06, 2026-01, 2026-02. All have `checksum_sha256: null` in sources.json.

The correct `DataNotValidatedError` fires first (good) — but when the user passes `allow_unvalidated=True` (as documented), the code crashes with a non-informative TypeError instead of proceeding to download.

**Fix:** `downloader.py:84`: Change `short = checksum[:16]` to `short = checksum[:16] if checksum else 'unvalidated'` (or handle None before use).

---

### BUG-005 — [HIGH] R: 1-column result for some epoch2 modules in 2022-01
**Component:** R  
**Severity:** High  
**Affects:** `ocupados`, `desocupados`, `inactivos`, `otros_ingresos`, `otras_formas_trabajo` in 2022-01

**Symptom:** DataFrame returns 1 column instead of ~200. The column name is the entire header row joined by the actual separator (underscore or tab):
```
"directorio_secuencia_p_orden_hogar_p3044_p6440_p6450_p6460_..." (200+ field names)
```

**Evidence:**
- `pulso_load(2022, 1, "ocupados")`: 31819 rows × 1 col (expected 200 cols)
- `pulso_load(2022, 1, "vivienda_hogares")`: 26098 rows × 48 cols (WORKS)
- `pulso_load(2024, 6, "ocupados")`: 29925 rows × 200 cols (WORKS)

**Root cause:** CSV separator auto-detection failure. The 2022-01 ZIPs for these modules use a different separator than the 2024-06 equivalents. The separator character used in the header ends up concatenating all field names.

**Fix:** Use `readr::read_delim()` with `delim=NULL` for auto-detection, or `data.table::fread()` which detects separator automatically.

---

## Medium Severity Bugs

### BUG-002 — [MEDIUM] Python: Excessive "Skipping variable" warnings during harmonization
**Component:** Python  
**Severity:** Medium  
**Affects:** `ocupados` and other modules for all epoch2 periods

**Symptom:** 32+ warning lines printed to stdout per `pulso.load()` call:
```
Skipping variable 'sexo': Variable 'sexo': source columns missing in DataFrame: ['P3271']. Required for epoch 'geih_2021_present'.
Skipping variable 'edad': Variable 'edad': source columns missing in DataFrame: ['P6040']. Required for epoch 'geih_2021_present'.
Skipping variable 'condicion_actividad': source columns missing: ['DSI']. ...
... (32+ more lines)
```

**Evidence:** Running `pulso.load(2024, 6, 'ocupados')` emits 32 Skipping lines. Same for `pulso.load(2022, 1, 'ocupados')`.

**Note:** Many flagged variables (DSI, OCI) are activity-status variables that logically belong in other modules, not ocupados. The harmonizer shouldn't warn when a cross-module variable isn't found in an unrelated module.

**Fix:** Filter variable_map.json by module before checking — only warn when a variable expected in *this specific module* is missing.

---

### BUG-006 — [MEDIUM] R: No validation guard on `pulso_load()`
**Component:** R  
**Severity:** Medium  
**Affects:** All unvalidated periods

**Symptom:** `pulso_load()` downloads and returns data for `validated=false` periods without any error or warning. Python correctly raises `DataNotValidatedError`.

**Evidence:**
```r
pulso_load(2023, 3, "ocupados")  # Returns 31009 × 200 tibble (no error/warning)
pulso_load(2025, 1, "ocupados")  # Returns 28317 × 202 tibble
pulso_load(2026, 1, "ocupados")  # Downloads 70MB, returns 28359 × 208 tibble
```

**Fix:** Add validation check in `pulso_load()`: if `validated == FALSE`, `stop()` with a `pulso_validation_error` unless `allow_unvalidated = TRUE` is passed by user.

---

### BUG-007 — [MEDIUM] Python: TypeError masks nested-zip error for 2024-03/2024-04
**Component:** Python (and both)  
**Severity:** Medium  
**Affects:** 2024-03, 2024-04

**Symptom:** `pulso.load(2024, 3, 'ocupados', allow_unvalidated=True)` crashes with `TypeError` (BUG-001) before reaching nested-zip detection. R gives a clear, informative error:
```
Period 2024-03 uses a nested-zip layout (CSV.zip wrapper) that is not yet 
supported in pulso v0.1.0. Planned for v0.2.0. See 
https://github.com/Stebandido77/pulso/issues/61
```

**Fix:** Fix BUG-001 first; the nested-zip error should then surface correctly in Python too.

---

## Low Severity Bugs

### BUG-009 — [LOW] Python: `list_variables()` and `describe_variable()` not implemented
**Component:** Python  
**Severity:** Low  
**Affects:** Offline API functions

**Symptom:**
```python
pulso.list_variables()        # raises "Phase 2"
pulso.describe_variable("sexo")  # raises "Phase 2"
```

R equivalents (`pulso_list_variables()`, `pulso_describe_variable("sexo")`) work correctly and return meaningful data.

**Fix:** Implement or clearly document as "not implemented in 1.0.0rc1". Remove from `__all__` or raise a proper `NotImplementedError` with next-steps guidance.

---

### BUG-010 — [LOW] Both: ZIP internal structure changed for periods >= 2025-06
**Component:** Both (R more observable)  
**Severity:** Low  
**Affects:** `caracteristicas_generales` and `migracion` in 2025-06, 2026-01, 2026-02

**Symptom:** R gives "file not found" (different from encoding error on earlier periods):
```
Expected file 'CSV/Características generales, seguridad social en salud y educación.CSV'
not found inside zip 06.zip
```

**Evidence:** 2025-01 gets encoding error (different path). 2025-06 gets file-not-found. Suggests DANE changed the internal ZIP directory structure after January 2025.

**Note:** Affects only unvalidated periods; the validated set (ending at 2024-06) is unaffected.

---

## Summary Table

| Bug ID | Severity | Component | Description | CRAN Blocker |
|--------|----------|-----------|-------------|--------------|
| BUG-004 | Critical | R | All epoch1 data fails (rbind col mismatch) | YES |
| BUG-001 | High | Python | TypeError on allow_unvalidated (null checksum) | YES |
| BUG-003 | High | R | UTF-8 ZIP filenames crash on Windows | YES |
| BUG-005 | High | R | 1-column result (wrong separator, 2022-01) | YES |
| BUG-008 | Medium | R | harmonize=TRUE silently adds no canonical cols | YES (docs) |
| BUG-002 | Medium | Python | 32+ Skipping variable warnings to stdout | NO |
| BUG-006 | Medium | R | No validation guard on pulso_load | YES |
| BUG-007 | Medium | Both | TypeError masks nested-zip error | NO |
| BUG-009 | Low | Python | list_variables/describe_variable unimplemented | NO |
| BUG-010 | Low | Both | ZIP structure changed >= 2025-06 | NO |

**CRAN verdict: NOT READY.** 4 critical/high bugs block R submission.

---

## Positive Findings (What Works)

- **Python validated epochs:** All 5 validated periods load correctly (2007-12, 2015-06, 2021-12, 2022-01, 2024-06)
- **Python validation guard:** Correctly raises `DataNotValidatedError` for unvalidated periods
- **R epoch2 (partial):** For validated epoch2 (2024-06), 6/8 modules load correctly in R
- **R offline API:** `pulso_list_variables()`, `pulso_describe_variable()`, `pulso_validation_status()`, `pulso_describe()` all work
- **Epoch boundary detection:** Both languages correctly assign 2021-12 to `geih_2006_2020` and 2022-01 to `geih_2021_present`
- **R nested-zip error:** Clear, informative error message with GitHub issue reference and planned version
- **Row count consistency:** Where both languages succeed (2024-06 epoch2 modules), row counts match exactly
- **p_coded column consistency:** Where both load the same module, P-coded column counts match exactly
