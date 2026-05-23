# Bugs Log — Extended Pre-CRAN Testing (append-only)

**Started:** 2026-05-23

## Bugs conocidos del smoke test (referencia)

| Bug | Sev | Comp | Descripción |
|-----|-----|------|-------------|
| BUG-004 | Critical | R | rbind() sin fill — epoch1 completo inutilizable |
| BUG-003 | High | R | UTF-8 filenames crash en Windows |
| BUG-005 | High | R | 1-col result en 2022-01 (sep detection failure) |
| BUG-006 | High | R | Sin validation guard |
| BUG-011 | High | R | Vignette no pre-construida |
| BUG-001 | High | Py | TypeError allow_unvalidated (rc1, corregido en source) |
| BUG-008 | Medium | R | harmonize=TRUE incompleto |
| BUG-002 | Medium | Py | 32+ warnings por stdout |
| BUG-007 | Medium | Both | TypeError enmascara nested-zip |
| BUG-009 | Low | Py | list_variables/describe_variable no implementados |
| BUG-010 | Low | Both | ZIP structure cambió >= 2025-06 |
| BUG-SEGFAULT | ? | R | Posible segfault en llamada repetida |

---

## Nuevos bugs de extended testing

## Bug #13 — [HIGH] Python: BUG-001 scope mucho más amplio de lo documentado (2026-05-23 01:45)
**Severity:** high
**Component:** Python
**Phase:** 1
**Period:** 2007-06, 2008-06, 2009-06, 2010-06, 2011-06 (y potencialmente ~225 períodos)
**Module:** todos (caracteristicas_generales, ocupados, desocupados, inactivos, vivienda_hogares, otros_ingresos)
**Description:** BUG-001 (TypeError: 'NoneType' object is not subscriptable al usar allow_unvalidated=True) afecta a TODOS los períodos con checksum_sha256=null en sources.json. Solo 5 períodos tienen checksum no-nulo: 2007-12, 2015-06, 2021-12, 2022-01, 2024-06. Los otros 225 períodos en sources.json fallan con este TypeError. En epoch1 early, solo 2007-12 funciona; los 5 períodos de junio (2007-06, 2008-06, 2009-06, 2010-06, 2011-06) fallan con BUG-001.
**Evidence:**
```
2007-06 / ocupados: Python=ERR TypeError: 'NoneType' object is not subscriptable
Traceback: downloader.py line 84: short = checksum[:16]  -> TypeError: 'NoneType' object is not subscriptable
```
**Reproducible:** yes (todos los runs)
**Scope:** 5 períodos funcionales, ~225 períodos rotos. Epoch1 early: 5/6 períodos afectados.
**New or known:** extends BUG-001 scope — previamente se asumía corregido en source v1.0.0, pero el problema es que sources.json tiene checksum=null para la mayoría de períodos, no un bug de la versión de Python.

---

## Bug #14 — [CONFIRMED NOT A BUG] BUG-SEGFAULT — No reproducible (2026-05-23 01:50)
**Severity:** n/a — not a bug
**Component:** R
**Phase:** 1
**Period:** 2024-06 (test period)
**Module:** ocupados, desocupados
**Description:** El posible segfault al llamar pulso_load() dos veces en la misma sesión R NO se reproduce en R 4.5.2 / Windows 11. Todos los 9 tests (3 escenarios × 3 runs) completaron con exit code 0.
**Evidence:**
```
Test A (mismo período ×2): exit 0 × 3 runs; Call 1: OK 29925 x 200; Call 2: OK 29925 x 200
Test B (distintos módulos ×2): exit 0 × 3 runs
Test C (error luego éxito): exit 0 × 3 runs; Call1 error: numbers of columns...; Call2 OK: 29925 x 200
```
**Reproducible:** no — NOT a bug in current environment
**Scope:** R 4.5.2, Windows 11
**New or known:** closes BUG-SEGFAULT (not reproducible)

---

## Bug #15 — [LOW] R: allow_unvalidated no soportado en pulso_load() (2026-05-23 01:52)
**Severity:** low
**Component:** R
**Phase:** 1
**Period:** 2007-06 (test period)
**Module:** cualquiera
**Description:** R pulso_load() no tiene parámetro allow_unvalidated — llamar con ese argumento da "unused argument (allow_unvalidated = TRUE)". La firma es: pulso_load(year, month, module, area=NULL, harmonize=TRUE, cache=TRUE, metadata=FALSE). Esto es inconsistente con la API Python que sí tiene allow_unvalidated.
**Evidence:**
```
2007-06 / caracteristicas_generales: R=ERR: unused argument (allow_unvalidated = TRUE) [exit=0]
R args: function(year, month, module, area=NULL, harmonize=TRUE, cache=TRUE, metadata=FALSE)
```
**Reproducible:** yes
**Scope:** todos los períodos en R cuando se usa allow_unvalidated=TRUE
**New or known:** new — no estaba en smoke test (los tests R en smoke test no usaban allow_unvalidated)

---

## Bug #16 — [MEDIUM] R: BUG-004 tiene dos variantes de error message (2026-05-23 01:55)
**Severity:** medium (extension de BUG-004)
**Component:** R
**Phase:** 1
**Period:** 2007-06, 2007-12, 2009-06, 2010-06 vs 2008-06, 2011-06
**Module:** ocupados, desocupados, inactivos, vivienda_hogares, otros_ingresos
**Description:** BUG-004 (rbind sin fill) produce dos mensajes distintos según el período:
- Variante A: "numbers of columns of arguments do not match" — 2007-06, 2007-12, 2009-06, 2010-06
- Variante B: "names do not match previous names" — 2008-06, 2011-06
Ambas son manifestaciones del mismo problema raíz (rbind() sin fill=TRUE), pero el error exacto cambia según la estructura del ZIP. El diagnóstico del bug puede variar por período.
**Evidence:**
```
2007-06 / ocupados: ERR: numbers of columns of arguments do not match
2008-06 / ocupados: ERR: names do not match previous names
2011-06 / ocupados: ERR: names do not match previous names
```
**Reproducible:** yes
**Scope:** epoch1 early — 2007-2011 al menos
**New or known:** extends BUG-004 — el smoke test solo documentó variante A

---

## Bug #17 — [HIGH] R: "Shape A files not found" para 2013-06 — filenames con sufijo de mes (2026-05-23 02:45)
**Severity:** high
**Component:** R
**Phase:** 2
**Period:** 2013-06 (confirmed; scope unknown for other periods)
**Module:** ocupados, desocupados, inactivos, vivienda_hogares, otros_ingresos (NOT caracgen — BUG-003 intercede)
**Description:** El ZIP de 2013-06 tiene filenames con sufijo numérico de mes: e.g. `Ocupados06.csv` en lugar de `Ocupados.csv`. El matcher de keywords en R busca "Ocupados" sin sufijo y falla con "Shape A files for module 'X' (2013-06) not found in zip. Tried keywords: Y". Esto es un tercer tipo de falla de epoch1, distinto de BUG-004 (rbind) y BUG-003 (UTF-8 filenames). La causa raíz es que DANE cambió la convención de nombres de archivo para 2013, usando un sufijo de número de trimestre/mes en los CSVs.
**Evidence:**
```
ZIP contents (2013-06): 'Junio.csv/Cabecera - Ocupados06.csv' (vs 'Ocupados.csv' en otros)
2013-06 / ocupados: ERR: Shape A files for module 'ocupados' (2013-06) not found in zip. Tried keywords: Ocupados
2013-06 / desocupados: ERR: Shape A files for module 'desocupados' (2013-06) not found in zip. Tried keywords: Desocupados
2013-06 / inactivos: ERR: Shape A files for module 'inactivos' (2013-06) not found in zip. Tried keywords: Inactivos
2013-06 / vivienda_hogares: ERR: Shape A files for module 'vivienda_hogares' (2013-06) not found in zip. Tried keywords: Vivienda y Hogares
2013-06 / otros_ingresos: ERR: Shape A files for module 'otros_ingresos' (2013-06) not found in zip. Tried keywords: Otros ingresos
(caracgen gives BUG-003 instead — 'Área' UTF-8 filename intercedes before keyword check)
```
**Reproducible:** yes
**Scope:** 2013-06 confirmed. 2013-12 does NOT have the pattern (normal filenames). 2013-03 and 2013-09 not cached. Other periods checked: 2012-06, 2014-06, 2014-12 — all normal. BUG-017 appears isolated to 2013-06 only.
**New or known:** new — not documented in smoke test. Third distinct failure mode for epoch1 R loading.

---

## Bug #18 — [HIGH] R+Python: 2020-06 and 2020-12 have unrecognized ZIP shape — no Cabecera/Resto split (2026-05-23 05:00)
**Severity:** high
**Component:** R, Python
**Phase:** 3
**Period:** 2020-06, 2020-12 (COVID-year data; others not cached)
**Module:** all (ocupados, desocupados, vivienda_hogares, inactivos, otros_ingresos, caracteristicas_generales)
**Description:** The 2020 GEIH ZIPs published by DANE have a fundamentally different structure from all other epoch1 periods. Instead of `Month.csv/Cabecera - Module.csv` + `Month.csv/Resto - Module.csv` layout (Shape A), 2020 periods use `N.Month/CSV/Module.CSV` with a single flat file per module — no Cabecera/Resto split. R fails with "Shape A files for module 'X' (2020-0Y) not found in zip. Tried keywords: Z". Python fails with BUG-001 (neither 2020-06 nor 2020-12 has a checksum so allow_unvalidated cannot be tested). ZIP folder comparison: 2019-06 = `Junio.csv/` (Cabecera/Resto), 2020-06 = `6.Junio/CSV/` (flat, uppercase .CSV), 2021-06 = `Junio.csv/` (Cabecera/Resto). The shape reverts to normal in 2021.
**Evidence:**
```
=== 2020-06 ZIP contents ===
  6.Junio/CSV/Características generales (personas).CSV
  6.Junio/CSV/Desocupados.CSV
  6.Junio/CSV/Fuerza de trabajo.CSV
  6.Junio/CSV/Inactivos.CSV
  6.Junio/CSV/Ocupados.CSV
  [no Cabecera/Resto split; no Vivienda y Hogares file]

2020-06 / ocupados: ERR pulso_parse_error - Shape A files for module 'ocupados' (2020-06) not found in zip. Tried keywords: Ocupados
2020-06 / vivienda_hogares: ERR pulso_parse_error - Shape A files for module 'vivienda_hogares' (2020-06) not found in zip. Tried keywords: Vivienda y Hogares
2020-06 / caracteristicas_generales: ERR pulso_parse_error - Shape A files for module 'caracteristicas_generales' (2020-06) not found in zip. Tried keywords: Características generales, Caracteristicas generales, Caractericas generales
2020-12: same pattern (12.Diciembre/CSV/*)
Python 2020-06: TypeError: 'NoneType' object is not subscriptable (BUG-001 — not validated)
```
**Reproducible:** yes
**Scope:** 2020-06 and 2020-12 confirmed. 2020-03 and 2020-09 not cached. 2019-06, 2019-12, 2021-06, 2021-12 all normal (Cabecera/Resto). Pattern likely affects all 2020 periods.
**New or known:** new — fourth distinct failure mode for epoch1-area R loading. Shape not handled by current parser. This is a COVID-year exception where DANE changed publication format.

---

## Bug #19 — [CONFIRMED] BUG-005 scope: isolated to 2022-01 only (2026-05-23 05:15)
**Severity:** medium (scope clarification)
**Component:** R
**Phase:** 3
**Period:** 2022-01 (1-col bug), 2022-06 (OK), 2022-12 (OK)
**Module:** ocupados, desocupados, inactivos, otros_ingresos, otras_formas_trabajo (all 1-col); vivienda_hogares (OK, 48 cols)
**Description:** BUG-005 (separator detection failure → 1-col result in R) is isolated to 2022-01 only. 2022-06 and 2022-12 load correctly. The root cause is that the three 2022 periods have different ZIP folder structures: 2022-01 = `GEIH_Enero_2022_Marco_2018/CSV/` (flat CSV folder), 2022-06 = `GEIH_Junio_2022_Marco_2018/CSV(1)/CSV/` (double-nested with parenthesized suffix), 2022-12 = `GEIH_Diciembre_2022_Marco_2018/CVS/` (typo: "CVS" not "CSV"). The parser somehow handles 2022-06 and 2022-12 correctly but fails for 2022-01. In 2022-01 R: vivienda_hogares returns 48 cols (OK), but ocupados/desocupados/inactivos/otros_ingresos/otras_formas_trabajo all return 1 col (BUG-005). Python 2022-01 loads correctly (31819, 212 cols) — confirms the data is fine, the issue is R's CSV parsing.
**Evidence:**
```
2022-01 ocupados: OK 31819 x 1 (BUG-005!)
2022-01 vivienda_hogares: OK 26098 x 48 (OK — only module working correctly)
2022-01 desocupados: OK 30378 x 1 (BUG-005!)
2022-01 inactivos: OK 30378 x 1 (BUG-005!)
2022-01 otros_ingresos: OK 62197 x 1 (BUG-005!)
2022-01 otras_formas_trabajo: OK 62197 x 1 (BUG-005!)
2022-01 caracteristicas_generales: ERR invalid multibyte string (BUG-003)
2022-01 migracion: ERR invalid multibyte string (BUG-003)
2022-06 ocupados: OK 32522 x 200 (OK)
2022-06 vivienda_hogares: OK 25822 x 48 (OK)
2022-06 desocupados: OK 28114 x 38 (OK)
2022-12 ocupados: OK 30505 x 200 (OK)
2022-12 vivienda_hogares: OK 24294 x 48 (OK)
2022-12 desocupados: OK 26160 x 38 (OK)
Python 2022-01 ocupados: OK (31819, 212) — data is fine, R parsing fails
```
**Reproducible:** yes
**Scope:** BUG-005 = 2022-01 only (not 2022-06, not 2022-12). In 2022-01: 5/8 modules get 1-col result; vivienda_hogares OK; caracgen/migracion hit BUG-003 first.
**New or known:** scope clarification of BUG-005 from smoke test (which only tested 2022-01).

---

## Bug #20 — [CONFIRMED SCOPE] BUG-003 universal in ALL epoch2 (migracion) (2026-05-23 06:30)
**Severity:** high (scope extension)
**Component:** R
**Phase:** 4
**Period:** ALL epoch2 periods (2022-06, 2022-12, 2023-06, 2023-12, 2024-01, 2024-06, 2025-01)
**Module:** migracion (and caracteristicas_generales — already confirmed)
**Description:** BUG-003 ("invalid multibyte string at '<a2>n.C'") affects `migracion` in EVERY epoch2 period tested. The error is identical across all periods. The ZIP filename contains UTF-8 bytes that R's utils::unzip cannot process when the ZIP lacks the UTF-8 flag bit. This is NOT limited to epoch1; BUG-003 is UNIVERSAL across all epochs for any module with accented characters in filenames (where UTF-8 flag is not set).
**Evidence:**
```
2022-06 migracion: ERR: invalid multibyte string at '<a2>n.C'
2022-12 migracion: ERR: invalid multibyte string at '<a2>n.C'
2023-06 migracion: ERR: invalid multibyte string at '<a2>n.C'
2023-12 migracion: ERR: invalid multibyte string at '<a2>n.C'
2024-01 migracion: ERR: invalid multibyte string at '<a2>n.C'
2024-06 migracion: ERR: invalid multibyte string at '<a2>n.C'
2025-01 migracion: ERR: invalid multibyte string at '<a2>n.C'
```
**Note:** 2025-06 migracion fails differently (BUG-023 "Expected file not found") because 2025-06 ZIP HAS the UTF-8 flag set — different failure mode, same root issue of encoding mismatch.
**New or known:** extends BUG-003 scope — previously documented as epoch1-specific. Now confirmed UNIVERSAL for all periods with UTF-8 flag=0 and accented filenames.

---

## Bug #21 — [MEDIUM CLARIFIED] BUG-008: harmonize=TRUE in R only lowercases column names (2026-05-23 06:45)
**Severity:** medium (behavior clarification)
**Component:** R, Python (asymmetric behavior)
**Phase:** 4
**Period:** 2024-06 (test period)
**Module:** ocupados
**Description:** harmonize=TRUE behavior is fundamentally different between Python and R:
- Python harmonize=TRUE: adds 13 NEW canonical columns (area, departamento, posicion_ocupacional, rama_actividad, ocupacion, horas_trabajadas_sem, ingreso_laboral, tiene_contrato, tipo_contrato, cotiza_pension, hogar_id, peso_expansion, peso_expansion_persona). Shape goes from (29925, 200) to (29925, 213).
- R harmonize=TRUE: ONLY lowercases column names. Shape stays (29925, 200). No canonical columns added.
This is the root of BUG-008: the R implementation of harmonize is incomplete.
**Evidence:**
```
Python 2024-06 ocupados harmonize=False: (29925, 200)
Python 2024-06 ocupados harmonize=True: (29925, 213) — +13 canonical cols with ~100% non-null
R harmonize=FALSE: (29925, 200), col[1]="PERIODO"
R harmonize=TRUE: (29925, 200), col[1]="periodo"
R added canonical cols (case-normalized): 0
```
**New or known:** confirms BUG-008 with exact column counts. R does do SOMETHING (lowercase) but misses canonical variable derivation.

---

## Bug #22 — [CONFIRMED] BUG-006 scope: ALL 16 tested epoch2 periods load silently in R (2026-05-23 06:50)
**Severity:** high
**Component:** R
**Phase:** 4
**Period:** 2023-06 through 2025-05 (16 periods tested, all unvalidated)
**Module:** ocupados
**Description:** ALL 16 unvalidated epoch2 periods load silently in R with no warning or error. R has no validation guard — any period in sources.json loads without restriction. 100% confirmation of BUG-006. Additional discovery: 2025-01 through 2025-05 return 202 columns (vs 200 for 2023-2024) indicating DANE added 2 new variables in 2025.
**Evidence:**
```
2023-06: OK 30535 x 200   2024-07: OK 29929 x 200   2025-01: OK 28317 x 202
2023-12: OK 29717 x 200   2024-08: OK 29951 x 200   2025-02: OK 29211 x 202
2024-01: OK 28815 x 200   2024-09: OK 29383 x 200   2025-03: OK 29471 x 202
2024-02: OK 29943 x 200   2024-10: OK 29127 x 200   2025-04: OK 29514 x 202
2024-05: OK 30142 x 200   2024-11: OK 28924 x 200   2025-05: OK 29957 x 202
2024-12: OK 28154 x 200
```
No warnings, no validation messages.
**New or known:** confirms BUG-006. +DISCOVERY: 2025 periods have 202 cols (2 extra vs 200 in 2024).

---

## Bug #23 — [HIGH, R] BUG-010 root cause: sources.json double-encodes accented filenames (2026-05-23 07:00)
**Severity:** high
**Component:** R (and Python for unvalidated periods)
**Phase:** 4
**Period:** 2025-06 (confirmed for "Expected file not found" error); 2025-01 and earlier for "invalid multibyte string" (BUG-003 pathway)
**Module:** migracion, caracteristicas_generales (any module with accented filename in sources.json)
**Description:** sources.json stores paths for Shape B (epoch2) modules with accented characters DOUBLE-ENCODED as Mojibake. Example for `migracion` in 2025-06:
- sources.json bytes: `b'CSV/Migraci\xc3\x83\xc2\xb3n.CSV'` (double UTF-8 encoding of ó)
- ZIP actual bytes: `b'CSV/Migraci\xc3\xb3n.CSV'` (correct UTF-8 of ó)
For 2025-06 (ZIP has UTF-8 flag=2056): R skips iconv, keeps correct UTF-8 from ZIP, but Mojibake sources.json path doesn't match -> "Expected file not found."
For 2025-01 (ZIP has UTF-8 flag=0): R applies iconv(CP437->UTF-8) to correct UTF-8 bytes -> different corruption -> "invalid multibyte string."
**Evidence:**
```
2025-06 migracion: ERR Expected file 'CSV/Migración.CSV' not found inside zip 06.zip
2025-06 caracgen: ERR Expected file 'CSV/Características generales...CSV' not found inside zip 06.zip
2025-06 other 6 modules (plain ASCII filenames): ALL OK

2025-06: 6/8 modules OK, 2/8 fail (migracion, caracgen)
ZIP 2025-06 structure: identical to 2024-12 (CSV/ folder, same filenames)
Root cause: Mojibake in sources.json, NOT a ZIP structure change
```
**New or known:** new — identifies root cause of BUG-010. The ZIP structure did NOT change; the Mojibake encoding in sources.json is the culprit.

---

## Bug #24 — [TESTING ARTIFACT] Multi-line -e strings to Rscript.exe via bash cause false SEGFAULT (2026-05-23 07:10)
**Severity:** TESTING ARTIFACT — not a bug in pulso package
**Component:** Test harness (bash-on-Windows)
**Phase:** 4
**Description:** Passing multi-line R code to Rscript.exe via bash single-quoted heredoc with actual newlines in the -e argument causes exit 139 (SEGFAULT) on Windows. Single-line semicolon-separated code works correctly. This is a bash/Windows interop artifact.
**Evidence:**
```
# FAILS exit 139: "$RSCRIPT" -e '\nlibrary(pulso)\ndf <- pulso_load(...)\n'
# Works exit 0: "$RSCRIPT" -e 'library(pulso); df <- pulso_load(...)'
Two loads in same R session (single-line format): WORKS fine
```
**Impact:** NO impact on pulso package. BUG-SEGFAULT remains CLOSED.

---

