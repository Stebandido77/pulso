# Pulso Extended Testing Pre-CRAN — Status

**Updated:** 2026-05-23 07:30 UTC
**Phase actual:** 4 — COMPLETA (TODAS LAS FASES COMPLETAS)
**Phase progreso:** 100% (Fase 1) | 100% (Fase 2) | 100% (Fase 3) | 100% (Fase 4)
**Sub-agent activo:** ninguno (Fase 4 finalizada — testing completo)
**Tiempo transcurrido:** ~90min total
**Bugs nuevos descubiertos:** 3 nuevos [Fases 1-2] + 1 nuevo [Fase 3: BUG-018] + 2 scope clarifications

## Resumen por fase
- Fase 1: ✅ COMPLETA — SEGFAULT + ECH + epoch1 early (2007-2011)
- Fase 2: ✅ COMPLETA — epoch1 middle (2012-2017) — 1 new bug (BUG-017)
- Fase 3: ✅ COMPLETA — epoch1 late + transición (2018-2022)
- Fase 4: ✅ COMPLETA — epoch2 comprehensive (2023-2025) + canonical variables + BUG-008/009/010

## Resumen Fase 1

### TAREA 1: SEGFAULT — NO REPRODUCIBLE
- 9 runs (3 escenarios × 3 repeticiones), todos exit code 0
- BUG-SEGFAULT CERRADO — no existe en R 4.5.2 / Windows 11

### TAREA 2: ECH error
- Python 2005: PulsoError "Year 2005 is out of supported range 2006-2100" (claro)
- Python 2006: DataNotAvailableError (no en registry)
- Python 2007: TypeError/BUG-001 (checksum=null, no llega a validar)
- R 2005/2006: pulso_validation_error "Year X is before pulso coverage starts (2007)" (claro)
- OBSERVACIÓN: Mensaje en Python dice "2006-2100" pero datos empiezan en 2007 — leve inconsistencia

### TAREA 3 + 4: Epoch1 early — TODOS FALLAN en R
- Python: 6/6 módulos de 2007-12 OK; 30/36 restantes = ERR BUG-001 (checksum=null)
- R: 36/36 combinaciones = ERR (BUG-003 para caracgen, BUG-004 para el resto)
- BUG-004 tiene DOS variantes de error message (descubierto ahora)

## Bugs nuevos encontrados en Fase 1
- **BUG-013** [HIGH, Py]: BUG-001 afecta ~225 períodos (todos con checksum=null). Solo 5 períodos tienen checksum: 2007-12, 2015-06, 2021-12, 2022-01, 2024-06
- **BUG-015** [LOW, R]: allow_unvalidated no soportado en pulso_load() → "unused argument" error
- **BUG-016** [MEDIUM, R]: BUG-004 tiene dos variantes: "numbers of columns" (2007-06/12, 2009-06, 2010-06) vs "names do not match" (2008-06, 2011-06)

## Bugs conocidos del smoke test
1. [CRIT] BUG-004: rbind() epoch1 falla — UNIVERSAL en epoch1 (confirmado)
2. [HIGH] BUG-003: UTF-8 ZIP filenames crash en Windows (confirmado en caracgen)
3. [HIGH] BUG-005: 1-col result en 2022-01 (pendiente fase 4)
4. [HIGH] BUG-006: Sin validation guard en R (pendiente)
5. [HIGH] BUG-011: Vignette no pre-construida (pendiente)
6. [HIGH] BUG-001: Python TypeError en allow_unvalidated — scope: ~225 períodos (extendido)
7. [MED]  BUG-008: harmonize=TRUE incompleto (pendiente)
8. [MED]  BUG-002: 32+ warnings por stdout (confirmado en todos los loads exitosos)
9. [MED]  BUG-007: TypeError enmascara nested-zip (pendiente)
10. [LOW]  BUG-009: list_variables/describe_variable → "Phase 2" (pendiente)
11. [LOW]  BUG-010: ZIP structure cambió >= 2025-06 (pendiente)
12. [CLOSED] BUG-SEGFAULT: No reproducible en R 4.5.2/Win11

## Bugs nuevos encontrados en Fase 2
- **BUG-017** [HIGH, R]: 2013-06 ZIP has filenames with month-number suffix (`Ocupados06.csv` instead of `Ocupados.csv`). R keyword matcher fails: "Shape A files not found in zip." Only 2013-06 confirmed (all other cached periods do not have this pattern). Third distinct failure mode for epoch1 R loading.

---

## Resumen Fase 2

### TAREA 1: Anomalía 2010-06 caracgen — RESUELTA
- Anomalía era error de documentación en phase_1: 2010-06 caracgen = BUG-003 (idéntico a todos los otros períodos)
- ZIP 2009-06 y 2010-06 son structuralmente idénticos: `Junio.csv/` folder, `Área` en CP437 encoding
- BUG-004 variante se determina por folder name: `Junio.csv/` → ERR-004A; `Junio_csv/` → ERR-004B

### TAREA 2: BUG-004 scope 2012-2017 — CONFIRMADO UNIVERSAL
- 2012, 2014, 2015, 2016, 2017: todos ERR-004A (numbers of columns)
- 2013-06: ERR-017 (nuevo bug — filenames con sufijo)
- vivienda_hogares en 2012-06 y 2016-06: ERR-004A (sin BUG-003, con BUG-004)

### TAREA 3: Python 2015-06 — TODOS OK
- 6/6 módulos cargan correctamente en Python
- Python emite ~100 "Skipping variable" warnings (BUG-002) — indica que harmonize=True produce output muy degradado para epoch1
- Shapes: caracgen(64785,44), ocupados(30136,169), desocupados(3231,46), inactivos(19035,30), vivienda(19032,68), otros_ingresos(52402,43)

### TAREA 4: BUG-003 scope en epoch1 middle — UNIVERSAL
- caracgen 2012-2017: TODOS ERR-003 sin excepción
- Patrón total confirmado: BUG-003 afecta caracgen en TODA epoch1 (2007-2017)

### TAREA 5: Modules en epoch1 — 6 módulos confirmado
- epoch1 (2007-2017): 6 módulos
- epoch2 (2022+): 8 módulos (+ migracion + otras_formas_trabajo)

## Resumen Fase 3

### TAREA 1: Python 2021-12 — TODOS OK
- 6/6 módulos cargan correctamente en Python 2021-12
- Epoch detectado correctamente: geih_2006_2020 (epoch1)
- Shapes: caracgen(56454,68), ocupados(23745,180), desocupados(3428,49), inactivos(20085,34), vivienda(18139,67), otros_ingresos(47258,52)
- p-coded columns count confirms harmonization active

### TAREA 2: 2020-06 — Shape C (COVID year) — NUEVO BUG-018
- Python: BUG-001 (no checksum) — cannot test
- R: "Shape A files not found" — all modules fail
- ZIP structure DIFFERENT from all other epoch1: `6.Junio/CSV/Module.CSV` (flat, no Cabecera/Resto)
- 2020-12 same pattern; 2019 and 2021 normal Cabecera/Resto structure
- BUG-018 [HIGH]: COVID-year (2020) ZIP format not recognized — affects all 2020 modules in R

### TAREA 3: BUG-005 scope — ISOLATED TO 2022-01 ONLY
- 2022-01: 5/8 modules return 1 col (BUG-005); vivienda_hogares OK (48 cols); caracgen/migracion BUG-003
- 2022-06: ALL OK (200, 48, 38 cols); only caracgen hits BUG-003
- 2022-12: ALL OK (200, 48, 38 cols)
- Python 2022-01: OK (31819, 212) — confirms data fine, R parsing fails
- ZIP structures differ: 2022-01=flat, 2022-06=double-nested CSV(1)/CSV/, 2022-12="CVS" typo folder

### TAREA 4: Nested-zip 2024-03/04 — CLEAR ERROR IN R
- R gives excellent error: "Period 2024-0X uses a nested-zip layout (CSV.zip wrapper) that is not yet supported in pulso v0.1.0. Planned for v0.2.0. See https://github.com/Stebandido77/pulso/issues/61"
- NOT a bug — properly handled with informative message
- BUG-007 (TypeError masking) applies to Python only, not R

### TAREA 5: BUG-017 scope — CONFIRMED 2013-06 ONLY
- 2012-06: normal filenames (Ocupados.csv)
- 2013-06: suffix pattern (Ocupados06.csv) — BUG-017
- 2013-12: normal filenames (no suffix)
- 2014-06, 2014-12: normal filenames
- BUG-017 isolated to 2013-06 among cached periods

### BONUS: BUG-004 scope through epoch1 late
- 2018-06, 2018-12, 2019-06, 2019-12, 2021-06, 2021-12: ALL "numbers of columns do not match" (Variant A)
- BUG-004 = universal across entire epoch1 (2007-2021, all variants)

## Próximo paso recomendado (Fase 4)
Fase 4 debe concentrarse en:
- epoch2 comprehensive: 2022-06 full module set, 2023 periods, 2024-06 (validated epoch2 period)
- BUG-008: harmonize=TRUE behavior in epoch2
- BUG-009: list_variables/describe_variable
- BUG-010: ZIP structure >= 2025-06
- Python 2024-03/04: nested-zip TypeError masking (BUG-007) — confirm Python error message
- Canonical variables: test that epoch2 variables are accessible

## Kill-switch
Crear archivo `tests-pre-cran/extended/KILL_SWITCH` para detener el testing limpiamente.
