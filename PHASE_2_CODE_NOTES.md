# Phase 2 (Code) — Builder Notes

**Status:** ✅ Complete  
**Date:** 2026-04-29  
**Branch:** `feat/code-harmonizer`  
**Owner:** Builder (Claude Code)

---

## What was implemented

### A. `pulso/_core/harmonizer.py`

**`harmonize_variable(df, canonical_name, variable_entry, epoch)`**

Dispatches over six transform types from `variable_map.json`:

| Transform | Behavior |
|---|---|
| `identity` / `rename` | `df[source].copy()` — source must be a single column |
| `recode` | Cast source to `StringDtype`, lookup in `mapping` dict (JSON keys are strings); fail-fast if unmapped and no `default` |
| `cast` | `int` → `Int64` (nullable), `bool` → `BooleanDtype`, `str` → `StringDtype`, `float` → `float64`, `category` → `CategoricalDtype` |
| `compute` | `pd.DataFrame.eval(expr, engine='python')` for arithmetic/boolean; manual parser for `.astype(str)` expressions (see Decision 5 below) |
| `coalesce` | Left-to-right first non-null across `source_variable` list |
| `custom` | Decorator-registered functions in `harmonizer_funcs.py` |

Post-transform:
- Boolean variables: result is cast to `BooleanDtype`.
- Categorical variables: non-null values are cast to `str` and checked against `categories.keys()`; any out-of-domain value raises `HarmonizationError`.

**`harmonize_dataframe(df, epoch, variables=None, keep_raw=True)`**

Iterates `_iter_relevant_variables` (variables with epoch mappings). `HarmonizationError` from missing source columns is caught and logged as a warning; the variable is silently skipped. Other errors propagate.

### B. `pulso/_core/harmonizer_funcs.py`

Three custom functions registered via `@register("name")`:

- **`bin_edad_quinquenal`**: `pd.cut(P6040, bins=[-0.001, 4, 9, ..., inf], labels=["0-4", ..., "65+"])`, returns `StringDtype`.
- **`merge_labor_status`**: Requires a pre-merged DataFrame with both OCI and DSI columns; classifies each person into "1" (ocupado), "2" (desocupado), or "3" (inactivo). See "Known Limitation: Inactivo Heuristic" below.
- **`compute_ingreso_total`**: Sums all available income components (INGLABO + non-labor sub-variables), `fillna(0)` before summing. Missing components are silently ignored.

### C. `pulso/_core/merger.py`

**`merge_modules(module_dfs, epoch, level="persona", how="outer")`**

Outer-joins an ordered dict of DataFrames on epoch merge keys. Default `how="outer"` is critical for `condicion_actividad`: persons appear in exactly one of `ocupados` / `no_ocupados`, so an inner join would discard 40% of the population.

Persona-level uses `epoch.merge_keys_persona = (DIRECTORIO, SECUENCIA_P, ORDEN)`.
Hogar-level uses `epoch.merge_keys_hogar = (DIRECTORIO, SECUENCIA_P)`.

### D. `pulso/_core/loader.py`

- `load(harmonize=True)`: after `parse_module`, calls `harmonize_dataframe(df, epoch)`.
- `load_merged(year, month, modules, ...)`: loads each module with `harmonize=False`, merges via `merge_modules`, then optionally harmonizes.

---

## Key Design Decisions

### Decision 9: Preserve raw columns alongside canonical (CRITICAL)

`harmonize_dataframe()` uses `keep_raw=True` by default. The output contains ALL original DANE columns (P3271, P6040, OCI, INGLABO, ...) PLUS the 30 canonical harmonized columns (sexo, edad, condicion_actividad, ingreso_laboral, ...).

**Rationale**: pulso's purpose is to _facilitate_ research, not constrain it. The 30 canonical variables are a cross-epoch comparability starter pack, but economists doing research need access to any variable in the DANE microdata. Dropping raw columns would force users to re-load data if they need a non-canonical variable.

### Decision 8 Option A: Cross-module merge for condicion_actividad

In GEIH-2, `condicion_actividad` requires joining three modules:
- `caracteristicas_generales`: universe of all persons
- `ocupados.CSV`: OCI=1 for employed persons
- `no_ocupados.CSV`: DSI column for non-employed persons

The merger is responsible for producing this pre-merged DataFrame via outer join. `merge_labor_status` then receives a DataFrame that contains both OCI and DSI columns and applies the classification logic.

**Why Option A over alternatives**: Keeps the merger generic (unaware of any specific variable semantics) and custom functions data-aware (they receive a ready-to-query DataFrame).

### Decision 5: Compute uses pd.eval, manual fallback for .astype(str)

`pd.DataFrame.eval(expr, engine='python')` handles arithmetic and boolean expressions safely. For expressions containing `.astype(str)` (like `hogar_id`'s concatenation expression), `pd.eval` does not support method calls. A manual parser splits on ` + ` and processes each token:

```
"DIRECTORIO.astype(str) + '_' + SECUENCIA_P.astype(str) + '_' + HOGAR.astype(str)"
```

→ Parsed as: `[df['DIRECTORIO'].astype(str), '_', df['SECUENCIA_P'].astype(str), '_', df['HOGAR'].astype(str)]`
→ Concatenated into a `StringDtype` Series.

`eval()` (builtin) is NEVER used — only `pd.DataFrame.eval()`.

### Boolean canonicalization to BooleanDtype

After `compute` or `identity` transforms, variables with `type: boolean` are cast to `pd.BooleanDtype()`. This is nullable, supporting `pd.NA` for missing values. Note: `pd.eval("col == 1")` with NaN source returns `False` (not `NA`) for NaN rows — this is an inherent pandas limitation. These False values are preserved in BooleanDtype.

### Recode string-key casting

`variable_map.json` recode mappings use JSON string keys ("1", "2", "3"). DANE source data uses integer or float dtype. The harmonizer casts source to `StringDtype` before lookup. **Known issue**: float64 columns where DANE stores integers as `1.0`, `2.0` would produce "1.0" ≠ "1" mismatch. In our test fixtures this doesn't arise (no float with NaN in recode columns). Real GEIH data may have float64 integer-valued columns if any NaN appears. Phase 3+ should add int-float detection: if `source.dtype` is float, try `source.astype("Int64").astype("string")` before falling back to `source.astype("string")`.

---

## Known Limitations

### Curator's 11 Uncertainties — What They Mean at Runtime

1. **`sexo` — P6016 vs P3271**: P3271 is used for GEIH-2. If P3271 is wrong, categorical validation will catch it (values outside {"1","2"} → `HarmonizationError`). Human verification against DANE questionnaire needed.

2. **`condicion_actividad` — cross-module in GEIH-2**: Correctly handled by `merge_labor_status` + outer join. GEIH-1 mapping uses `OCI` with `identity` transform, which may fail if the actual GEIH-1 file doesn't contain `OCI` (module location uncertain). Runtime: `HarmonizationError("source columns missing")`.

3. **`tipo_desocupacion` — DSCY vs P7240**: GEIH-2 correctly uses `DSCY`. GEIH-1 uses `P7240`; verify the module (desocupados vs caracteristicas_generales).

4. **`tipo_inactividad` — P7430**: Only values 1 and 2 observed in June 2024. If the variable's semantics differ from the 9-category mapping, categorical validation will raise `HarmonizationError` on production data. No fix without DANE questionnaire confirmation.

5. **`busco_trabajo` — DSI proxy for GEIH-2**: Using DSI=1 as proxy for "buscó trabajo". Valid for desocupados; inactivos (DSI=NaN) get False. This is semantically correct but different from the GEIH-1 direct question (P6240).

6. **`disponible` — P7280 vs P7290**: P7290 not found in GEIH-2; P7280 used as best guess. If P7280 is wrong, categorical validation won't catch it (boolean type has no categories). Must verify against questionnaire.

7. **`educ_max` — 9 vs 13 categories**: GEIH-2 has values 1-13 but categories only covers 1-9. Categorical validation will raise `HarmonizationError` for values 10-13. **Open issue needed** — Curator must extend the mapping or update categories.

8. **`ingreso_total` — INGTOT absent in GEIH-2**: `compute_ingreso_total` sums available columns (fillna=0). If the list of sub-variables in variable_map is incomplete, some income components are silently excluded. The sum will be an underestimate.

9. **`posicion_ocupacional` — P6435 not found**: P6430 is used (confirmed in data). Should be correct for both epochs; verify for GEIH-1 if P6435 was truly a different variable.

10. **`anios_educ` ASCII name**: Uses `anios_educ` instead of `años_educ`. No runtime impact; purely a naming decision.

11. **`condicion_actividad` in GEIH-1 — OCI module location**: May require loading a different module than `caracteristicas_generales`. If OCI is absent, `HarmonizationError("source columns missing")` is raised and the variable is skipped.

### Inactivo Heuristic in merge_labor_status

`result[oci.isna() & dsi.isna()] = "3"` classifies any person who is not in `ocupados` and has `DSI=NaN` as inactivo. This is a best-effort heuristic: it correctly handles the case where a person is in `no_ocupados` with `DSI=NaN`. However, it could incorrectly classify persons who are genuinely absent from both modules (data quality issues) as inactivo.

In a well-merged DataFrame where all persons from `caracteristicas_generales` appear in either `ocupados` or `no_ocupados`, this heuristic is exact. If the merge produces rows with neither OCI nor DSI (e.g., universe persons not in any labor module), they would be classified as "3" (inactivo), which may be incorrect.

---

## Performance Notes

- `harmonize_dataframe` iterates the variable_map (30 variables) per call. Each variable does one Series operation. O(V × N) where V=30, N=rows. Should be fast even for 70,000-row GEIH-2 months.
- `merge_modules` uses pandas merge with `how="outer"`. For 3 modules of size 50,000 / 30,000 / 20,000, memory usage is dominated by the wider merged DataFrame (~200+ columns after suffix expansion).
- The unified fixture (N=50) runs all integration tests in under 2 seconds.

---

## Open Issues to Create

1. **educ_max / parentesco_jefe categories incomplete**: GEIH-2 P3042 has values 1-13 but variable_map categories cover only 1-9; P6050 has values 11, 12, 13 not in the declared domain. Categorical validation skips these variables with a warning on production data. Curator must extend categories (see GitHub issue #11).

2. ~~Float-encoded integers in recode~~ — **FIXED** (see "Bug fixes" section below).

---

## Bug fixes (2026-04-29, end-to-end testing against real DANE 2024-06)

### Fix 1: merger drops duplicate non-key columns

**Problem**: iterative outer-joins between 3 modules suffixed shared identifier
columns (CLASE, DPTO, FEX_C18, MES, HOGAR) as `CLASE_caracteristicas_generales`,
`CLASE_ocupados`, `CLASE_no_ocupados`, etc. The harmonizer then couldn't find the
source column (e.g. `CLASE` for `area`) and silently skipped those variables.

**Fix**: before each join, columns already present in the running merged DataFrame
(excluding merge keys) are dropped from the incoming module. First module's copy of
shared columns wins; module-specific columns (OCI, DSI, INGLABO, P6040, …) are
unaffected.

**Impact**: `area`, `departamento`, `hogar_id`, `peso_expansion`, and any variable
whose source column also appears in a later module now harmonize correctly.

### Fix 2: float-to-string canonicalization for categorical variables

**Problem**: pandas reads CSV integer columns that contain NaN as float64 (int64
cannot represent NaN). Category codes like `1.0`, `2.0` were stringified as
`"1.0"`, `"2.0"`, failing recode lookups and domain checks whose keys are JSON
strings `"1"`, `"2"`.

**Fix**: `_to_canonical_string(series)` helper detects float64 columns where all
non-null values are whole numbers and converts via `Int64 → string` (1.0 → "1").
Used in `_apply_recode`, `_validate_categorical_domain`, and the categorical
post-transform normalisation step in `harmonize_variable`.

**Impact**: `estado_civil`, `parentesco_jefe`, `posicion_ocupacional`,
`tipo_contrato`, `educ_max`, and all other categorical variables that DANE stores
as float64-with-NaN now harmonize without raising or being skipped.

**Side effect**: categorical identity-transform columns now return `StringDtype`
("1", "2") instead of the original dtype (1.0, 2.0). This is the correct canonical
form for categoricals. See `test_categorical_validation_passes_for_valid_codes`
(updated).

---

## Phase 2 Debt — Module Validation & Auto-Inclusion (PR #16)

### Validation

`load_merged()` now validates every module in the `modules` parameter against
`sources.json` before any loading begins. Invalid module names raise
`ModuleNotAvailableError` immediately instead of being silently skipped by the
`if mod in record["modules"]` filter. This mirrors the existing behaviour of
`load()` (single-module).

### Auto-inclusion

A new private helper `_required_modules_for_variables(variable_map, sources,
epoch_key, requested_variables)` computes the set of modules required by
canonical variables for a given epoch. It filters to modules that (a) appear in
`sources["modules"]` and (b) list the epoch in their `available_in` field, so
epoch-specific modules are not accidentally requested for the wrong epoch.

When `harmonize=True` and the user provides an explicit `modules` list,
`load_merged()` calls this helper and appends any missing required modules to
the working list. Auto-included modules are logged at `DEBUG` level
(`pulso._core.loader` logger) for traceability without noisy warnings.

This means a user calling:

```python
pulso.load_merged(year=2024, month=6,
                  modules=["caracteristicas_generales", "ocupados",
                           "desocupados", "inactivos"],
                  harmonize=True)
```

now gets `vivienda_propia` (from `vivienda_hogares`) and `ingreso_total` (from
`otros_ingresos`) in the output without needing to name those modules explicitly.

When `harmonize=False`, the user's exact module list is respected (no
auto-inclusion). The `modules=None` case is unchanged: it falls back to
`list(record["modules"].keys())`, which already includes all modules registered
for that period.

### Closes Issue #12

---

## Phase 2 Debt — Multi-level Merger

### Bug
`merge_modules()` previously assumed all modules were persona-level. Including a hogar-level
module like `vivienda_hogares` triggered `MergeError: missing merge keys ['ORDEN']`.

### Fix
Merger now auto-detects each module's level by inspecting which merge_keys it has.

- **`_detect_module_level(df, epoch)`**: returns `"persona"` if ORDEN is present; `"hogar"` if
  HOGAR is present (without ORDEN); raises `MergeError` otherwise.
- **`_merge_within_level(dfs_dict, keys, how)`**: extracted helper that merges a dict of same-level
  DataFrames on the given keys, deduplicating shared non-key columns (same logic as before).

When `level="persona"` (default):
1. Auto-detect each module as persona or hogar
2. Merge all persona-level modules together (outer join on DIRECTORIO, SECUENCIA_P, ORDEN)
3. Merge all hogar-level modules together (outer join on DIRECTORIO, SECUENCIA_P, HOGAR)
4. LEFT JOIN persona ⟕ hogar on [DIRECTORIO, SECUENCIA_P, HOGAR]

This propagates hogar/vivienda info to each person in that household.

When `level="hogar"` (legacy): all modules are forced to merge on hogar keys (no ORDEN required);
backward-compatible with existing callers.

### Backward Compatibility
Persona-only merges produce identical results — all modules detected as "persona", merged as
before. The `level="hogar"` path is unchanged (legacy behavior preserved so existing tests pass).

### Tests Added
- `test_detect_persona_level`, `test_detect_hogar_level`: unit tests for the detector
- `test_merge_persona_and_hogar_propagates_hogar_info`: verifies hogar info propagates to persons
- `test_existing_persona_only_merge_still_works`: backward compat guard
- `test_load_merged_hogar_module_propagates_info`: integration test with synthetic fixture
