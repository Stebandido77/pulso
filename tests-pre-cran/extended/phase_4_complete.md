# Phase 4 Complete — Extended Pre-CRAN Testing

**Date:** 2026-05-23
**Phase:** 4 (FINAL)
**Focus:** epoch2 comprehensive (2022-2025) + BUG-003/006/008/010 + canonical variables
**Status:** COMPLETE

---

## Task Results

### TASK 1: BUG-003 scope — migracion in epoch2 (RESULT: UNIVERSAL)

**Question:** Does `migracion` fail in ALL epoch2 periods or only some?

**Answer:** BUG-003 ("invalid multibyte string at '<a2>n.C'") affects `migracion` in EVERY epoch2 period tested. There is no epoch2 period where `migracion` loads successfully in R (except 2025-06 which fails differently).

```
2022-06  migracion: ERR invalid multibyte string at '<a2>n.C'
2022-12  migracion: ERR invalid multibyte string at '<a2>n.C'
2023-06  migracion: ERR invalid multibyte string at '<a2>n.C'
2023-12  migracion: ERR invalid multibyte string at '<a2>n.C'
2024-01  migracion: ERR invalid multibyte string at '<a2>n.C'
2024-06  migracion: ERR invalid multibyte string at '<a2>n.C'
2025-01  migracion: ERR invalid multibyte string at '<a2>n.C'
2025-06  migracion: ERR Expected file 'CSV/Migración.CSV' not found inside zip 06.zip
```

**BUG-003 revised scope:** UNIVERSAL across ALL epochs and ALL periods where:
- Module filename contains accented characters (ó in "Migración", í/ó in "Características")
- ZIP's UTF-8 flag bit is NOT set (flag_bits & 0x800 == 0)
- For 2025-06 (UTF-8 flag IS set): different error via sources.json Mojibake — see BUG-023

**New bug logged:** BUG-020 (scope extension of BUG-003 to all epoch2)

---

### TASK 2: BUG-008 — harmonize=TRUE deep dive (RESULT: EXACT BEHAVIOR DOCUMENTED)

**Python (2024-06 ocupados):**
```
harmonize=False: (29925, 200)
harmonize=True:  (29925, 213)  ← +13 canonical columns
Added cols (13): area, departamento, posicion_ocupacional, rama_actividad, ocupacion,
                 horas_trabajadas_sem, ingreso_laboral, tiene_contrato, tipo_contrato,
                 cotiza_pension, hogar_id, peso_expansion, peso_expansion_persona
Non-null: all 29925/29925 except ingreso_laboral (28498) and tipo_contrato (18321)
```

**Python (2021-12 epoch1 ocupados):**
```
Shape: (23745, 180)
Non-P-coded cols (31): DIRECTORIO, SECUENCIA_P, ORDEN, HOGAR, REGIS, AREA, CLASE,
  OFICIO, RAMA2D_R4, OCI, MES, RAMA4D_R4, INGLABO, DPTO, FEX_C, RAMA4DP8_R4,
  _area, area, departamento, condicion_actividad
```
Python harmonize ALSO attempts canonical mapping for epoch1 (emits ~100 "Skipping variable" warnings for epoch1 as source columns have different names — BUG-002 manifestation).

**R (2024-06 ocupados):**
```
harmonize=FALSE: (29925, 200), col[1]="PERIODO"
harmonize=TRUE:  (29925, 200), col[1]="periodo"
Cols added (canonical): 0
```
R harmonize=TRUE ONLY lowercases/normalizes column names via `tolower(gsub("[^[:alnum:]_]", "_", names(df)))`. No canonical variable derivation occurs.

**Conclusion — BUG-008:** Confirmed "incompletely implemented" in R. Python adds 13 canonical cols with harmonize=TRUE. R adds 0. The R source code (load.R line 61-63) confirms this: `if (harmonize) names(df) <- tolower(gsub(...))`.

**New bug logged:** BUG-021 (exact quantification of BUG-008)

---

### TASK 3: BUG-006 scope — epoch2 periods loading without validation (RESULT: 16/16 CONFIRMED)

**Question:** How many unvalidated epoch2 periods load silently in R?

**Answer:** ALL 16 tested periods load silently with no warning or error.

```
2023-06:  OK 30535 x 200    2024-07:  OK 29929 x 200    2025-01: OK 28317 x 202
2023-12:  OK 29717 x 200    2024-08:  OK 29951 x 200    2025-02: OK 29211 x 202
2024-01:  OK 28815 x 200    2024-09:  OK 29383 x 200    2025-03: OK 29471 x 202
2024-02:  OK 29943 x 200    2024-10:  OK 29127 x 200    2025-04: OK 29514 x 202
2024-05:  OK 30142 x 200    2024-11:  OK 28924 x 200    2025-05: OK 29957 x 202
2024-12:  OK 28154 x 200    (all silently, no warning)
```

**Additional discovery:** 2025-01 through 2025-05 have 202 columns (vs 200 for 2023-2024). DANE added 2 new variables in early 2025. R loads these with no issue (no schema validation).

**BUG-006 confirmed:** 100% of unvalidated epoch2 periods (16/16) load without restriction.

**New bug logged:** BUG-022 (full scope confirmation of BUG-006 + 202-col discovery)

---

### TASK 4: BUG-010 scope — ZIP structure >= 2025-06 (RESULT: NOT STRUCTURE CHANGE — ENCODING BUG)

**Question:** Does ZIP structure change >= 2025-06? Which modules fail?

**Finding 1 — ZIP structure is NOT the root cause:**
The ZIP structure for 2024-12, 2025-01, and 2025-06 is IDENTICAL:
```
CSV/
CSV/Características generales, seguridad social en salud y educación.CSV
CSV/Datos del hogar y la vivienda.CSV
CSV/Fuerza de trabajo.CSV
CSV/Migración.CSV
CSV/No ocupados.CSV
CSV/Ocupados.CSV
CSV/Otras formas de trabajo.CSV
CSV/Otros ingresos e impuestos.CSV
DTA/ [same files with .DTA extension]
SAV/ [same files with .SAV extension]
```
(27 total entries each)

**Finding 2 — Root cause is sources.json Mojibake:**
sources.json stores paths for epoch2 modules with accented characters DOUBLE-ENCODED:
```
sources.json bytes: b'CSV/Migraci\xc3\x83\xc2\xb3n.CSV'  (double UTF-8 of ó)
ZIP actual bytes:   b'CSV/Migraci\xc3\xb3n.CSV'           (correct UTF-8 of ó)
```

**Finding 3 — Two failure modes based on ZIP UTF-8 flag:**
- 2025-06 (UTF-8 flag=2056, set): R skips CP437 iconv, gets correct UTF-8 from ZIP, but Mojibake in sources.json doesn't match → "Expected file 'CSV/Migración.CSV' not found"
- 2025-01 (UTF-8 flag=0, not set): R applies iconv(CP437→UTF-8) to correct UTF-8 bytes → corruption → "invalid multibyte string" (BUG-003 pathway)

**R results for 2025-06 (8 modules):**
```
ocupados:              OK 29706 x 202
desocupados:           OK 24744 x 37
inactivos:             OK 24744 x 37
vivienda_hogares:      OK 24337 x 49
otros_ingresos:        OK 54450 x 59
otras_formas_trabajo:  OK 54450 x 112
migracion:             ERR Expected file 'CSV/Migración.CSV' not found inside zip 06.zip
caracteristicas_generales: ERR Expected file 'CSV/Características generales...CSV' not found
```
**6/8 modules OK, 2/8 fail (both have accented filenames in sources.json)**

**Python 2025-06:** ALL 8 modules fail with TypeError (BUG-001 — unvalidated, checksum=null)

**New bug logged:** BUG-023 (root cause of BUG-010 identified — Mojibake in sources.json)

---

### TASK 5: Canonical variables — Python vs R (RESULT: PARTIALLY FUNCTIONAL)

**Python:**
```
list_variables():    ERR NotImplementedError: Phase 2  (BUG-009)
list_available():    (230, 5) — WORKS
  columns: year, month, epoch, validated, modules_available
  230 periods, with modules_available listing 6 or 8 module names per period
describe('ocupados'):  WORKS — returns dict with level, description_es, description_en, available_in, module
describe('migracion'): WORKS — available_in: ['geih_2021_present']
describe('caracteristicas_generales'): WORKS
```

**R:**
```
pulso_list_variables(): WORKS — 30 rows, 6 cols
  columns: canonical_name, module, description_es, comparability, has_warning, num_epochs
  30 canonical variables
  18/30 have warnings (has_warning=TRUE)
  ALL 30 are multi-epoch (num_epochs=2)
  Modules: caracteristicas_generales, desocupados, ocupados, otros_ingresos, inactivos, vivienda_hogares
  NOTE: migracion and otras_formas_trabajo NOT in canonical variables list

pulso_describe_variable("sexo"):  WORKS — returns text with epoch source columns
pulso_describe_variable("ingreso_laboral"):  WORKS
pulso_describe("ocupados"):  WORKS — "Harmonized variables (11): cotiza_pension, hogar_id, ..."
pulso_list_validated_range():  WORKS — 5 rows (validated periods: 2007-12, 2015-06, 2021-12, 2022-01, 2024-06)
pulso_list_available():  NOT FOUND ("could not find function")
```

**Python vs R canonical variables comparison:**
- Python: 0 accessible (list_variables NotImplementedError)
- R: 30 variables accessible via pulso_list_variables()
- R has 11 harmonized variables in ocupados module
- Python adds 13 canonical columns via harmonize=TRUE
- The 13 Python cols and 11 R harmonized vars overlap but differ (R includes hogar_id, Python includes hogar_id too; R list includes some not in Python's harmonize output)

---

### TASK 6: 2022-12 "CVS" typo investigation (RESULT: CONFIRMED TYPO, PARSER CASE-INSENSITIVE)

**Finding:** The ZIP for 2022-12 DOES have folder named "CVS" (not "CSV") — this is a real DANE typo.

**Full ZIP structure:**
```
GEIH_Diciembre_2022_Marco_2018/
GEIH_Diciembre_2022_Marco_2018/CVS/     ← TYPO: "CVS" not "CSV"
GEIH_Diciembre_2022_Marco_2018/CVS/Características generales...CSV
GEIH_Diciembre_2022_Marco_2018/CVS/Datos del hogar y la vivienda.CSV
GEIH_Diciembre_2022_Marco_2018/CVS/Fuerza de trabajo.CSV
GEIH_Diciembre_2022_Marco_2018/CVS/Migración.CSV
GEIH_Diciembre_2022_Marco_2018/CVS/No ocupados.CSV
GEIH_Diciembre_2022_Marco_2018/CVS/Ocupados.CSV
GEIH_Diciembre_2022_Marco_2018/CVS/Otras formas de trabajo.CSV
GEIH_Diciembre_2022_Marco_2018/CVS/Otros ingresos e impuestos.CSV
GEIH_Diciembre_2022_Marco_2018/CVS/Tipo de investigación.CSV
+ DTA/ and SAV/ subdirs
```

**Why R loads 2022-12 correctly despite the typo:**
R's `.resolve_zip_path()` uses a case-insensitive PCRE pattern (`(?i)\Q...\E`) to match just the BASENAME of the file. The sources.json path includes "CVS/Ocupados.CSV" (already written with the correct typo). The parser does case-insensitive matching on basename only (e.g., "Ocupados.CSV"), ignoring the parent folder name ("CVS" vs "CSV"). So the CVS typo is transparent to the parser.

**Note:** sources.json for 2022-12 already stores the path with "CVS" (not "CSV") so the sources.json was correctly scraped to reflect the actual typo. This is NOT a bug — it's correctly handled.

---

### ADDITIONAL FINDINGS

**Testing artifact — false SEGFAULT (BUG-024):**
During Phase 4 testing, passing multi-line R code via bash single-quoted heredoc to Rscript.exe on Windows causes exit 139 (SEGFAULT). This is a bash-on-Windows interop issue. When using semicolons on a single line, everything works correctly. This explains why some earlier test attempts appeared to SEGFAULT on multiple loads — they actually segfaulted due to the multi-line string passing. BUG-SEGFAULT remains CLOSED for the pulso package itself.

---

## Consolidated Bug Table — All 4 Phases

### Confirmed Bugs (Active)

| Bug | Sev | Comp | Status | Scope | Description |
|-----|-----|------|--------|-------|-------------|
| BUG-001 | HIGH | Py | OPEN | ~225 periods | TypeError on allow_unvalidated when checksum=null |
| BUG-002 | MED | Py | OPEN | All loads | 32+ "Skipping variable" warnings to stdout |
| BUG-003 | HIGH | R | OPEN | ALL epochs/periods with accented module filenames (UTF-8 flag=0) | invalid multibyte string crash |
| BUG-004 | CRIT | R | OPEN | ALL epoch1 (2007-2021) | rbind() without fill — all epoch1 modules fail |
| BUG-005 | HIGH | R | OPEN | 2022-01 ONLY | Separator detection failure → 1-col result (5/8 modules) |
| BUG-006 | HIGH | R | OPEN | ALL unvalidated epoch2 | No validation guard — silent load of any period |
| BUG-007 | MED | Py | OPEN | 2024-03, 2024-04 | TypeError masks nested-zip error (root: BUG-001) |
| BUG-008 | MED | R | OPEN | All epoch2 loads | harmonize=TRUE only lowercases, adds 0 canonical cols |
| BUG-009 | LOW | Py | OPEN | Always | list_variables() → NotImplementedError: Phase 2 |
| BUG-010 | HIGH | Both | OPEN | 2025-06+ (UTF-8 flag set); 2024-12/2025-01 etc via BUG-003 | sources.json Mojibake in accented paths |
| BUG-011 | HIGH | R | OPEN | vignette | Vignette not pre-built |
| BUG-017 | HIGH | R | OPEN | 2013-06 ONLY | Numeric suffix in filenames (Ocupados06.csv) |
| BUG-018 | HIGH | Both | OPEN | 2020-06, 2020-12 (COVID-year) | Shape C: flat CSV without Cabecera/Resto |

### Closed / Not Bugs

| Bug | Status | Notes |
|-----|--------|-------|
| BUG-SEGFAULT | CLOSED | Not reproducible in R 4.5.2/Win11. Multi-line bash → false alarm |
| BUG-019 | CLOSED | Scope clarification of BUG-005 (was not a new bug) |

### New Bugs Found in Phase 4

| Bug | Sev | Comp | Description |
|-----|-----|------|-------------|
| BUG-020 | HIGH | R | BUG-003 confirmed universal across ALL epoch2 (migracion in all periods) |
| BUG-021 | MED | R | BUG-008 exact: harmonize adds 0 canonical cols in R (vs 13 in Python) |
| BUG-022 | HIGH | R | BUG-006 exact: 16/16 unvalidated epoch2 periods load silently; 2025 has 202 cols |
| BUG-023 | HIGH | R | BUG-010 root cause: sources.json Mojibake in accented paths |
| BUG-024 | N/A | Test | Bash multi-line to Rscript.exe = false SEGFAULT (test artifact, not pulso bug) |

### Scope Clarifications from Phases 1-4

| Bug | Original Scope | Confirmed Scope |
|-----|---------------|-----------------|
| BUG-001 | "rc1 period" | ~225 periods (all checksum=null) |
| BUG-003 | epoch1 + caracgen | ALL epochs, ALL modules with accented filenames |
| BUG-004 | epoch1 | ALL epoch1, ALL periods 2007-2021 |
| BUG-005 | 2022 transition | 2022-01 ONLY |
| BUG-006 | "some epoch2" | ALL 16 unvalidated epoch2 tested |
| BUG-017 | unknown | 2013-06 ONLY |
| BUG-018 | unknown | 2020-06 and 2020-12 (COVID-year) |

---

## Final Functional Matrix

### Python Loading Status

| Period Type | Example | Status | Notes |
|-------------|---------|--------|-------|
| Validated epoch1 | 2007-12, 2015-06, 2021-12 | OK | 6 modules |
| Validated epoch2 | 2022-01, 2024-06 | OK | 8 modules |
| Unvalidated epoch1 | 2008-06, 2019-06, etc. | ERR-BUG-001 | ~220 periods fail |
| Unvalidated epoch2 | 2023-06, 2024-12, 2025-06 | ERR-BUG-001 | All fail (checksum=null) |
| Nested-zip | 2024-03, 2024-04 | ERR-BUG-001+007 | TypeError masks nested-zip error |
| COVID-year | 2020-06, 2020-12 | ERR-BUG-001 | Cannot test (no checksum) |

### R Loading Status

| Period Type | Module | Status | Notes |
|-------------|--------|--------|-------|
| epoch1 (2007-2021) | caracgen | ERR-BUG-003 | invalid multibyte string |
| epoch1 (2007-2021) | ocupados etc. | ERR-BUG-004 | rbind() mismatch |
| epoch1 2013-06 | ocupados etc. | ERR-BUG-017 | numeric suffix in filename |
| epoch1 2020-06/12 | all | ERR-BUG-018 | Shape C (no Cabecera/Resto) |
| epoch2 transition 2022-01 | 5/8 modules | ERR-BUG-005 | 1-col result |
| epoch2 transition 2022-01 | vivienda_hogares | OK | 48 cols |
| epoch2 2022-06 to 2024-06 | ocupados/desocupados/etc | OK | 200 cols |
| epoch2 2022-06 onwards | migracion | ERR-BUG-003 | UTF-8 flag=0, accented |
| epoch2 2022-06 onwards | caracgen | ERR-BUG-003 | UTF-8 flag=0, accented |
| epoch2 2025-01 to 2025-05 | all except mig/caracgen | OK | 202 cols |
| epoch2 2025-06 | all except mig/caracgen | OK | 202 cols |
| epoch2 2025-06 | migracion, caracgen | ERR-BUG-023 | UTF-8 flag=2056, Mojibake path |
| epoch2 unvalidated | all | Silent load | BUG-006: no validation guard |
| nested-zip 2024-03/04 | all | Clear error message | NOT a bug in R |

### What Works in R (epoch2, non-accented modules)
All these modules load correctly in all epoch2 periods (2022-06 through 2025-06):
- `ocupados` (200 cols in 2022-2024; 202 in 2025)
- `desocupados` (37-38 cols)
- `inactivos` (37-38 cols)
- `vivienda_hogares` (48-49 cols)
- `otros_ingresos` (59 cols)
- `otras_formas_trabajo` (112 cols)

### What Fails in R (all epochs)
- `migracion` — fails in ALL periods (BUG-003 for UTF-8 flag=0; BUG-023 for UTF-8 flag=2056)
- `caracteristicas_generales` — fails in ALL epochs (BUG-003 or BUG-023)

### Canonical Variables
- R `pulso_list_variables()`: 30 variables, 6 modules (excludes migracion and otras_formas_trabajo)
- Python `list_variables()`: NotImplementedError (BUG-009)
- Python `describe()`: WORKS for all modules
- Python `list_available()`: (230, 5) WORKS
- R `pulso_list_available()`: function does not exist

---

## Key Statistics

- **Total bugs logged:** 24 (BUG-001 to BUG-024)
- **Active bugs:** 13
- **Closed/artifacts:** 3 (BUG-SEGFAULT, BUG-019, BUG-024)
- **Scope clarifications:** 7
- **Phases completed:** 4/4
- **Periods tested:** ~40+ unique periods
- **Modules tested:** 8 modules × multiple periods × Python + R

## Critical for CRAN

1. **BUG-003 + BUG-023** (HIGH): `migracion` and `caracteristicas_generales` fail in ALL R sessions. 2 of 8 modules completely broken.
2. **BUG-004** (CRITICAL): ALL epoch1 (2007-2021) fails in R — 14 years of data inaccessible.
3. **BUG-008** (MED): harmonize=TRUE in R only lowercases. Python adds 13 canonical cols. Core API inconsistency.
4. **BUG-006** (HIGH): No validation guard in R — loads any period silently, including unvalidated ones.
5. **BUG-011** (HIGH): Vignette not pre-built — CRAN check will fail.
