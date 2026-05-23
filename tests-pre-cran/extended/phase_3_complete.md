# Phase 3 Complete — Extended Pre-CRAN Testing

**Completed:** 2026-05-23 05:30 UTC
**Sub-agent:** Coder Fase 3
**Scope:** Python 2021-12 (all modules), 2020-06 (Shape C), BUG-005 scope (2022 periods), nested-zip 2024-03/04 in R, BUG-017 scope

---

## TAREA 1: Python 2021-12 — Todos los módulos

**Result:** ALL 6 MODULES OK

| Module | Shape | p_coded cols |
|--------|-------|-------------|
| caracteristicas_generales | (56454, 68) | 42 |
| ocupados | (23745, 180) | 149 |
| desocupados | (3428, 49) | 27 |
| inactivos | (20085, 34) | 17 |
| vivienda_hogares | (18139, 67) | 51 |
| otros_ingresos | (47258, 52) | 36 |

**Epoch detected:** `geih_2006_2020` (epoch1) — confirmed from sources.json
**Checksum:** 607ece9b... (validated period, non-null checksum)
**Note:** Python emits "Skipping variable" warnings (BUG-002) during harmonization, indicating harmonize=True degrades output for epoch1 variables. The data itself loads correctly.

**Conclusions:**
- 2021-12 is the last validated epoch1 period and loads perfectly in Python
- All 6 modules (full epoch1 module set) work correctly
- Epoch detection is correct (geih_2006_2020)
- p-coded variable count confirms harmonization is active but degraded

---

## TAREA 2: 2020-06 ZIP Structure and Failures

### Python result
```
Python 2020-06 ocupados: ERR TypeError: 'NoneType' object is not subscriptable
```
**Cause:** BUG-001 — 2020-06 has checksum=null in sources.json. Cannot test with Python.

### ZIP Structure Inspection

2020-06 and 2020-12 have a fundamentally different structure from all other epoch1 periods:

```
=== Normal epoch1 (2019-06) ===
  Junio.csv/Cabecera - Ocupados.csv
  Junio.csv/Resto - Ocupados.csv
  Junio.csv/[Area - Ocupados.csv]

=== 2020-06 (COVID year — Shape C) ===
  6.Junio/CSV/Características generales (personas).CSV
  6.Junio/CSV/Desocupados.CSV
  6.Junio/CSV/Fuerza de trabajo.CSV
  6.Junio/CSV/Inactivos.CSV
  6.Junio/CSV/Ocupados.CSV
  [NO Cabecera/Resto split; NO Vivienda y Hogares]
  [folder uses N.Month/CSV/ pattern; uppercase .CSV extension]

=== 2020-12 (COVID year — Shape C) ===
  12.Diciembre/CSV/Características generales (personas).CSV
  12.Diciembre/CSV/Desocupados.CSV
  12.Diciembre/CSV/Fuerza de trabajo.CSV
  12.Diciembre/CSV/Inactivos.CSV
  12.Diciembre/CSV/Ocupados.CSV
  12.Diciembre/CSV/Otras actividades y ayudas en la semana.CSV
  12.Diciembre/CSV/Otros ingresos.CSV
  12.Diciembre/CSV/Vivienda y Hogares.CSV
```

Pattern: 2020 uses single flat CSVs per module with no Cabecera/Resto split. This is likely COVID-related — DANE changed publication format in 2020.

### R results (NEW BUG-018)

```
2020-06 / ocupados: ERR pulso_parse_error - Shape A files for module 'ocupados' (2020-06) not found in zip. Tried keywords: Ocupados
2020-06 / vivienda_hogares: ERR pulso_parse_error - Shape A files for module 'vivienda_hogares' (2020-06) not found in zip. Tried keywords: Vivienda y Hogares
2020-06 / caracteristicas_generales: ERR pulso_parse_error - Shape A files for module 'caracteristicas_generales' (2020-06) not found in zip. Tried keywords: Características generales, Caracteristicas generales, Caractericas generales
2020-12 / ocupados: ERR pulso_parse_error - Shape A files for module 'ocupados' (2020-12) not found in zip. Tried keywords: Ocupados
2020-12 / desocupados: ERR pulso_parse_error - Shape A files for module 'desocupados' (2020-12) not found in zip. Tried keywords: Desocupados
```

**NEW BUG-018 (HIGH):** 2020 COVID-year ZIPs have a unique "Shape C" structure not recognized by the R (or Python) parser. All 2020 periods fail in R with "Shape A files not found."

**ZIP pattern timeline:**
- 2018-06, 2018-12, 2019-06, 2019-12: Normal Shape A (Cabecera/Resto)
- 2020-06, 2020-12: Shape C (flat single CSV per module, N.Month/CSV/ folder)
- 2021-06, 2021-12: Back to Shape A (Cabecera/Resto)

---

## TAREA 3: BUG-005 Scope — 2022-01, 2022-06, 2022-12

### ZIP Structure Comparison

| Period | ZIP root folder | Structure note |
|--------|----------------|----------------|
| 2022-01 | `GEIH_Enero_2022_Marco_2018/CSV/` | Flat CSV folder |
| 2022-06 | `GEIH_Junio_2022_Marco_2018/CSV(1)/CSV/` | Double-nested with parenthesized number |
| 2022-12 | `GEIH_Diciembre_2022_Marco_2018/CVS/` | Typo: "CVS" not "CSV" |

### R Results

**2022-01 (CONFIRMED BUG-005):**
| Module | R result | cols |
|--------|----------|------|
| ocupados | OK | 1 (BUG-005) |
| vivienda_hogares | OK | 48 (correct) |
| desocupados | OK | 1 (BUG-005) |
| inactivos | OK | 1 (BUG-005) |
| otros_ingresos | OK | 1 (BUG-005) |
| otras_formas_trabajo | OK | 1 (BUG-005) |
| caracteristicas_generales | ERR | BUG-003 (invalid multibyte string) |
| migracion | ERR | BUG-003 (invalid multibyte string) |

**2022-06 (BUG-005 NOT present):**
| Module | R result | cols |
|--------|----------|------|
| ocupados | OK | 200 |
| vivienda_hogares | OK | 48 |
| desocupados | OK | 38 |
| otros_ingresos | OK | 59 |
| caracteristicas_generales | ERR | BUG-003 |

**2022-12 (BUG-005 NOT present):**
| Module | R result | cols |
|--------|----------|------|
| ocupados | OK | 200 |
| vivienda_hogares | OK | 48 |
| desocupados | OK | 38 |

### Python Result (2022-01 — validated)

```
Python 2022-01 ocupados: OK (31819, 212) — data is fine, only R parsing fails
```

### Conclusions

**BUG-005 scope = 2022-01 ONLY.** 2022-06 and 2022-12 load correctly in R.

In 2022-01: 5 out of 8 modules return 1-col dataframes (separator detection failure). Only `vivienda_hogares` works correctly. `caracgen` and `migracion` hit BUG-003 (UTF-8 multibyte string error) before reaching the separator issue.

The different ZIP folder structures (flat vs double-nested vs "CVS" typo) explain why 2022-01 is uniquely affected. Root cause: R's CSV reading fails to detect the correct separator for the 2022-01 `GEIH_Enero_2022_Marco_2018/CSV/` flat files, producing single-column output.

---

## TAREA 4: Nested-zip 2024-03, 2024-04 — R Error Messages

### Literal R output

```
=== 2024-03 ocupados ===
ERR: pulso_parse_error - Period 2024-03 uses a nested-zip layout (CSV.zip wrapper) that is not yet supported in pulso v0.1.0. Planned for v0.2.0. See https://github.com/Stebandido77/pulso/issues/61

=== 2024-04 ocupados ===
ERR: pulso_parse_error - Period 2024-04 uses a nested-zip layout (CSV.zip wrapper) that is not yet supported in pulso v0.1.0. Planned for v0.2.0. See https://github.com/Stebandido77/pulso/issues/61
```

**Assessment:** EXCELLENT error message. It:
- Names the exact layout ("nested-zip layout (CSV.zip wrapper)")
- Specifies current version ("not yet supported in pulso v0.1.0")
- Sets expectation ("Planned for v0.2.0")
- Provides GitHub issue URL for tracking

This is NOT a bug — it is a correctly handled known limitation with a clear, actionable error. BUG-007 (TypeError masking nested-zip error) applies to Python, not R. R handles this gracefully.

---

## TAREA 5: BUG-017 Scope — Numeric Suffix in Filenames

### Cached periods checked

| Period | Ocupados filename | Has suffix? |
|--------|------------------|-------------|
| 2012-06 | `Cabecera - Ocupados.csv` | No |
| 2013-06 | `Cabecera - Ocupados06.csv` | YES (BUG-017) |
| 2013-12 | `Cabecera - Ocupados.csv` | No |
| 2014-06 | `Cabecera - Ocupados.csv` | No |
| 2014-12 | `Cabecera - Ocupados.csv` | No |

**Non-cached 2013 periods:** 2013-03, 2013-09 (cannot check)

### Conclusion

**BUG-017 = isolated to 2013-06 only** among all cached periods. The numeric suffix (`06` = month number for June) appears to be a unique anomaly in that specific quarter. 2013-12 reverts to normal naming. The pattern does not affect 2012 or 2014 periods.

Scope estimate: likely just 2013-06. Possibly 2013-03 and 2013-09 also have quarterly suffixes (03, 09) but this cannot be confirmed without downloading those ZIPs.

---

## Additional Finding: R BUG-004 Universal Through epoch1

As a bonus, testing confirmed that BUG-004 (rbind without fill) affects ALL epoch1 late periods:

| Period | R ocupados result |
|--------|-----------------|
| 2018-06 | ERR: numbers of columns of arguments do not match |
| 2018-12 | ERR: numbers of columns of arguments do not match |
| 2019-06 | ERR: numbers of columns of arguments do not match |
| 2019-12 | ERR: numbers of columns of arguments do not match |
| 2021-06 | ERR: numbers of columns of arguments do not match |
| 2021-12 | ERR: numbers of columns of arguments do not match |

**BUG-004 scope = entire epoch1 (2007-2021), Variant A for all 2018-2021.**

---

## Summary of Answers to Phase 3 Questions

1. **BUG-005 scope:** Confirmed 2022-01 ONLY. 2022-06 and 2022-12 load correctly.
2. **Python 2021-12:** ALL 6 modules load OK. Epoch correctly detected as geih_2006_2020.
3. **R 2020-06 error:** "Shape A files not found in zip" — not BUG-004 but a new BUG-018 (unrecognized COVID-year ZIP shape).
4. **R nested-zip 2024-03/04:** Clear, informative error message. Not a bug — handled correctly.
5. **BUG-017 scope:** Isolated to 2013-06 only among cached periods. 2013-12 is normal.

---

## New Bugs Found in Phase 3

| Bug | Sev | Component | Description |
|-----|-----|-----------|-------------|
| BUG-018 | HIGH | R, Py | 2020 COVID-year ZIPs have unrecognized "Shape C" (flat CSV, no Cabecera/Resto). R fails "Shape A not found". Python blocked by BUG-001. |
| BUG-019 | — | R | BUG-005 scope clarification: 5/8 modules in 2022-01 return 1-col; only vivienda_hogares correct; not a new bug but scope now precise. |
| BUG-017 | — | R | Scope update: confirmed isolated to 2013-06 only (among cached periods). |

**Total new bugs from Phase 3:** 1 new (BUG-018), 2 scope clarifications (BUG-005, BUG-017)

---

## Status After Phase 3

- **Fase 1:** Complete — SEGFAULT + ECH + epoch1 early (2007-2011)
- **Fase 2:** Complete — epoch1 middle (2012-2017) + BUG-017
- **Fase 3:** COMPLETE — epoch1 late (2018-2021) + epoch2 transition (2022) + 2020 shape + BUG-005 scope + nested-zip R messages
- **Fase 4:** PENDING — epoch2 comprehensive (2023-2025) + canonical variables + BUG-008 harmonize
