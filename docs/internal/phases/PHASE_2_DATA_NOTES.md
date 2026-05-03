# Phase 2 — Data Notes (variable_map)

**Status:** Complete  
**Date:** 2026-04-29  
**Branch:** `feat/data-variable-map`  
**Curator:** Claude Code (Sonnet 4.6)

---

## Summary

Populated `variable_map.json` with 30 canonical variables per the Phase 2 specification.
All entries validate against `variable_map.schema.json` (`python scripts/validate_sources.py` → 3 ✅).
All 7 schema unit tests pass; full suite: 80 passed, 9 skipped.

GEIH-2 column names were verified by direct inspection of the cached June 2024 ZIP at
`%LOCALAPPDATA%\pulso\pulso\Cache\raw\2024\06\c5799177604b0e08.zip`.
GEIH-1 column names are taken from the Phase 2 specification (best-effort) and flagged where uncertain.

---

## Source

- DANE GEIH methodology documentation (URLs in `epochs.json`)
- Direct inspection of the cached June 2024 ZIP (GEIH-2 epoch)
- Phase 2 specification variable suggestions
- General Colombian household survey conventions (CIIU, CIUO codes)

---

## Coverage by epoch

| Variable | geih_2006_2020 | geih_2021_present | Notes |
|---|---|---|---|
| sexo | P6020 | P3271 | Renamed; P6016 was incorrect (see below) |
| edad | P6040 | P6040 | Stable across epochs |
| grupo_edad | P6040 (compute) | P6040 (compute) | Derived via `bin_edad_quinquenal` |
| parentesco_jefe | P6051 | P6050 | Minor code change; GEIH-1 unverified |
| estado_civil | P6070 | P6070 | Stable |
| grupo_etnico | P6080 | P6080 | Stable code; not all months in GEIH-1 |
| area | CLASE (recode) | CLASE (recode) | GEIH-1: may be implicit via directory split |
| departamento | DPTO | DPTO | Stable |
| educ_max | P6210 | P3042 | Major rename in redesign |
| anios_educ | P6210S1 | P3042S1 | Major rename in redesign |
| asiste_educ | P6170 (compute) | P6170 (compute) | Stable code |
| alfabetiza | P6160 (compute) | P6160 (compute) | Stable code |
| condicion_actividad | OCI | OCI + DSI (custom) | Cross-module in GEIH-2 |
| tipo_desocupacion | P7240 | DSCY | Renamed; P7240 in GEIH-2 is unrelated |
| tipo_inactividad | P7160 | P7430 | Uncertain; see below |
| busco_trabajo | P6240 (compute) | DSI (compute) | Different approach per epoch |
| disponible | P7290 (compute) | P7280 (compute) | Code change; P7290 absent in GEIH-2 |
| posicion_ocupacional | P6430 | P6430 | Stable; spec said P6435 (not found) |
| rama_actividad | RAMA2D | RAMA2D_R4 | CIIU Rev.3 → Rev.4 |
| ocupacion | OFICIO | OFICIO_C8 | Renamed; CIUO-88 → CIUO-08 |
| horas_trabajadas_sem | P6800 | P6800 | Stable |
| ingreso_laboral | INGLABO | INGLABO | Stable |
| tiene_contrato | P6440 (compute) | P6440 (compute) | Stable |
| tipo_contrato | P6450 | P6450 | Stable |
| cotiza_pension | P6920 (compute) | P6920 (compute) | Stable |
| ingreso_total | INGTOT | compute (custom) | INGTOT absent in GEIH-2 microdata |
| hogar_id | DIRECTORIO+SECUENCIA_P+HOGAR | same | Computed string ID |
| vivienda_propia | P5090 (compute) | P5090 (compute) | Stable; P5090<=2 → own |
| peso_expansion | fex_c_2011 | FEX_C18 | Renamed; not comparable across epochs |
| peso_expansion_persona | fex_c_2011 | FEX_C18 | Same source as peso_expansion |

---

## Variables with uncertainty

### 1. `sexo` — Phase 1 Curator error on P6016

The Phase 1 Data Notes stated: *"The sex variable is now coded P6016 (values: 1=Hombre, 2=Mujer)"*.
Inspection of the June 2024 ZIP shows **P6016 has values 1–17** (not binary). It appears to be a
sequential enumeration variable correlated with ORDEN but not identical to it.

**P3271** (binary: value=1 → 32,659 records, value=2 → 37,361 records, total = 70,020) is the
confirmed sex variable in GEIH-2 June 2024. The GEIH-2 mapping in `variable_map.json` uses P3271.

**Action required:** Human verification against the DANE GEIH-2 questionnaire PDF to confirm P3271 is sex.
If P3271 is not sex, open a GitHub issue and update the mapping.

### 2. `condicion_actividad` — cross-module in GEIH-2

In GEIH-1, `OCI` was a single unified indicator per person (likely in a "fuerza de trabajo" aggregate
module or `caracteristicas_generales`). In GEIH-2 (June 2024), `OCI` only appears in `ocupados.CSV`
(200 columns), always = 1 (all records are employed by definition of that module). For non-occupied
persons, `DSI` in `no_ocupados.CSV` provides the desocupado (=1) / inactivo (=NaN) distinction.

**Implication for Phase 2 Builder:** `merge_labor_status` custom function must join:
- `OCI=1` from `ocupados.CSV` → condicion=1 (ocupado)
- `DSI=1` from `no_ocupados.CSV` → condicion=2 (desocupado)
- `no_ocupados` rows where `DSI=NaN` → condicion=3 (inactivo)

### 3. `tipo_desocupacion` — P7240 is not cesante/aspirante in GEIH-2

The Phase 2 spec suggests `P7240` for both epochs. However, `P7240` appears in `ocupados.CSV` in
GEIH-2 (not `no_ocupados.CSV`) with values 2, 2, 3, 3, 3 in the first rows — this is not
the cesante/aspirante distinction.

`DSCY` in `no_ocupados.CSV` (values 1=cesante, 2=aspirante) is the correct GEIH-2 variable.
For GEIH-1, `P7240` in the desocupados module is maintained as the spec suggests; requires
verification against GEIH-1 data.

### 4. `tipo_inactividad` — P7430 not confirmed

In GEIH-2, `no_ocupados.CSV` does not contain `P7160` (the GEIH-1 code). The variable `P7430`
is present for all 25,605 non-occupied persons (values 1 and 2). The meaning of P7430 —
whether it is "razón de inactividad" or "desea trabajar" — could not be confirmed without the
DANE questionnaire PDF. Mapped as best-guess; verify against DANE documentation.

### 5. `busco_trabajo` — different approaches by epoch

- GEIH-1: `P6240` (binary question: "¿Buscó trabajo la semana pasada?") — standard.
- GEIH-2: No direct binary "searched for work" question was found in `no_ocupados.CSV`. `DSI=1`
  (desocupado indicator) is used as a proxy, since desocupado status requires having searched.
  `P7250` in `no_ocupados.CSV` appears to be a duration variable (value 52.0 = 52 weeks) rather
  than a binary question.

### 6. `disponible` — P7290 not found in GEIH-2

The Phase 2 spec gives `P7290` for both epochs. `P7290` does not appear in any GEIH-2 module
in June 2024. `P7280` is present in `no_ocupados.CSV` and is used as the best-guess replacement.
Verify against DANE questionnaire.

### 7. `educ_max` — category count expansion

GEIH-1 `P6210` typically has 9 categories. GEIH-2 `P3042` has 13 observed categories in June 2024
(values 1–13). Categories in `variable_map.json` reflect the GEIH-2 structure; the Phase 2 Builder
will need a crosswalk table for comparable analysis across epochs.

### 8. `ingreso_total` — INGTOT absent in GEIH-2 microdata

`INGTOT` does not appear in any module of the June 2024 ZIP. The `compute_ingreso_total` custom
function must sum: `INGLABO` (from `ocupados`) + non-labor income components from `otros_ingresos`
(P7500S1A1, P7500S2A1, P7500S3A1, P750S1A1, P750S2A1, P750S3A1, and likely others). The full
list of components should be verified against DANE methodology documentation.

### 9. `posicion_ocupacional` — P6435 not found

The Phase 2 spec suggests `P6435` or `P6450`. `P6435` does not appear in `ocupados.CSV` of June 2024.
`P6450` is `tipo_contrato`. `P6430` (confirmed in the data) is the standard position variable.
Used `P6430` for both epochs; verify for GEIH-1.

### 10. `anios_educ` naming — `ñ` rejected by schema

The spec calls for `años_educ`. The schema pattern `^[a-z][a-z0-9_]*$` rejects the `ñ` character.
Used `anios_educ` (ASCII). Recommendation: Architect should consider updating the schema pattern to
`^[a-zà-ɏ][a-z0-9_à-ɏ]*$` to allow Latin Extended characters, or accept the
ASCII transliteration.

### 11. `condicion_actividad` in GEIH-1 — module uncertain

OCI in GEIH-1 was available in the "fuerza de trabajo" aggregate module (not one of the 6 canonical
modules). It may also appear in a Cabecera or Resto version of `caracteristicas_generales`. Mapped
with identity transform but module assignment (canonical `caracteristicas_generales`) may not match
the actual source file. Verify with real GEIH-1 data.

---

## Quirks discovered

1. **P6016 is not sex in GEIH-2** — this contradicts Phase 1 Data Notes. See Variable 1 above.
   GitHub issue recommended: close/correct issue #3 with updated findings.

2. **`no_ocupados.CSV` combines desocupados + inactivos** (Quirk #3 from Phase 1) — this affects
   `tipo_desocupacion`, `tipo_inactividad`, `busco_trabajo`, and `disponible`, all of which must
   filter within this combined module.

3. **INGTOT not in GEIH-2 monthly microdata** — total income must be constructed from components.
   This significantly increases the complexity of `ingreso_total` harmonization.

4. **CIIU revision change** — `rama_actividad` uses CIIU Rev.3 (GEIH-1) vs. Rev.4 (GEIH-2).
   Codes for the same industries can differ. Comparability analysis needed.

5. **CIUO revision change** — `ocupacion` uses CIUO-88 (GEIH-1) vs. CIUO-08 (GEIH-2). Same issue.

6. **OCI cross-module join in GEIH-2** — a fundamental change in how labor force status is stored.
   Affects not just `condicion_actividad` but any downstream filter (e.g., loading only desocupados).

---

## Recommendations for Phase 2 Builder

1. **Implement `merge_labor_status`** first — it is a prerequisite for any person-level harmonization
   in GEIH-2. The function should join `ocupados.CSV` (OCI) and `no_ocupados.CSV` (DSI) against
   `caracteristicas_generales.CSV` on (DIRECTORIO, SECUENCIA_P, ORDEN).

2. **Implement `bin_edad_quinquenal`** as a simple pd.cut on P6040 with the 14 bins defined in
   `variable_map.json → grupo_edad.categories`.

3. **Implement `compute_ingreso_total`** by summing the income sub-variables from `otros_ingresos`
   plus `INGLABO` from `ocupados`. Use coalesce logic (fillna=0 for NaN sub-variables before sum).

4. **For boolean variables**, the `compute` transform `expr` uses Python/pandas syntax (e.g.,
   `P6440 == 1`). The harmonizer should evaluate this expression in the context of the loaded
   DataFrame.

5. **For `area` in GEIH-1**, the CLASE column might not exist or might be constant within each
   file (all Cabecera/ files → CLASE=1). Consider inferring from the source file path if CLASE is
   absent.

6. **Recode key types**: The `mapping` keys in recode transforms are JSON strings (e.g., `"1"`,
   `"2"`, `"3"`). The source data has integer values. The harmonizer must cast the source column
   to string before applying the recode mapping, or implement integer-key lookup.

7. **P3271 (sexo GEIH-2)** — verify against the DANE GEIH-2 questionnaire before implementing.
   If wrong, the mapping needs updating.

---

## Verification checklist

- [x] All 30 variables present in variable_map.json
- [x] Schema validation passes (`scripts/validate_sources.py` returns 3 ✅)
- [x] All 7 schema unit tests pass (`pytest tests/unit/test_schemas.py -v`)
- [x] Full test suite passes (80 passed, 9 skipped)
- [x] Each variable has mappings for both epochs (geih_2006_2020 AND geih_2021_present)
- [x] GEIH-2 variable codes verified against June 2024 ZIP where possible
- [x] Uncertainties documented in this file
- [ ] Human verification of P3271 as sex variable in GEIH-2 (requires DANE questionnaire PDF)
- [ ] Human verification of P7430 as tipo_inactividad in GEIH-2
- [ ] Verification of GEIH-1 column codes against real data (P6051, OCI location, INGTOT availability)

---

## Phase 2 debt — domain fixes (branch `feat/data-domain-fixes`, 2026-04-29)

End-to-end testing against real DANE 2024-06 data revealed three domain gaps in `variable_map.json`
that were not visible during Phase 2 code review. Fixed in PR #11/#13.

### Fix 1: `educ_max` — replaced GEIH-1 categories with official GEIH-2 categories

**Problem:** The Phase 2 Curator populated `educ_max.categories` with 9 codes that reflect the
GEIH-1 (P6210) codification. Real June 2024 data shows values 1–13 for P3042, not 1–9.

**Fix:** Replaced all 9 categories with the 13 official DANE GEIH-2 categories plus code 99
("No sabe, no informa"), as verified against **DANE catálogo 819, variable F63 (P3042)**:
`https://microdatos.dane.gov.co/index.php/catalog/819/variable/F63/V4044?name=P3042`

**Comparability note:** The GEIH-1 codification (P6210, 9 codes) collapses levels that GEIH-2 (P3042)
distinguishes separately (e.g., code 1 = "Ninguno/Preescolar" in GEIH-1 corresponds to codes 1 and 2
in GEIH-2; code 5 = "Técnica/Tecnológica" in GEIH-1 corresponds to codes 8 and 9 in GEIH-2). A
crosswalk table is required for any longitudinal comparison across epochs. Documented in
`comparability_warning`.

### Fix 2: `parentesco_jefe` — added codes 11, 12, 13

**Problem:** Variable map declared 10 categories (1–10). Real June 2024 data shows values 11
(10 persons), 12 (4 persons), and 13 (780 persons, significant) that were missing from the domain.

**Fix:** Extended `categories` to include:
- `"11"`: `"Suegro/a (padre/madre del cónyuge)"` — best-guess label
- `"12"`: `"Yerno/Nuera (cónyuge del hijo/a)"` — best-guess label
- `"13"`: `"Hermano/a"` — best-guess label (780 persons make this category non-trivial)

**Open uncertainty:** The exact DANE labels for codes 11, 12, 13 could not be confirmed against the
GEIH-2 questionnaire PDF or DANE microdata catalog. The labels are conservative guesses based on
typical family-relationship expansions in the 2021 redesign. **REQUIRES HUMAN VERIFICATION** against
the official DANE GEIH-2 questionnaire or the microdatos catalog before using these codes in
published analysis. Documented in `comparability_warning`.

### Fix 3: `tipo_contrato` — added code 9 (No sabe / No informa)

**Problem:** Variable map declared categories 1–4. Real data contains value 9 (7 persons).

**Fix:** Added `"9"`: `"No sabe / No informa"`. Standard DANE convention for categorical variables;
no special verification required.

### Variables intentionally NOT touched

- **`vivienda_propia`** and **`ingreso_total`**: Their `module` field is correct in `variable_map.json`.
  The issue is that `load_merged` does not auto-include the required modules (`vivienda_hogares`,
  `otros_ingresos`) when these variables are requested. This is a Builder/code problem, tracked as
  **Issue #14** (Builder territory). No changes to `variable_map.json` needed for these variables.
