# Phase 2 Complete — epoch1 middle (2012-2017)

**Completed:** 2026-05-23 ~03:00 UTC
**Duration:** ~30 min
**New bugs found:** 1 (BUG-017)
**Periods tested:** 6 (2012-06 through 2017-06) + follow-up on 2009-06, 2010-06, 2013-06 all modules
**Modules tested:** 36 (6 periods × 6 modules for R caracteristicas_generales) + targeted tests

---

## Anomalía 2010-06 caracgen

**Conclusion: The phase_1 anomaly note was a documentation error. 2010-06 caracgen = BUG-003 (consistent).**

Re-tested 2010-06 `caracteristicas_generales` in R: consistently gives **ERR-003** ("invalid multibyte string at '<a1>sti'"), not ERR-004A as the phase_1 table indicated. The phase_1 report text had a caveat note saying "2010-06 caracgen shows ERR-004A instead of ERR-003 — zip structure may differ" but repeated testing confirms this is incorrect.

**ZIP structure analysis (2009-06 vs 2010-06):**
- Both ZIPs have folder `Junio.csv/` (with dot)
- Both have filenames like `Cabecera - Características generales (Personas) (6).csv`
- Both have `╡rea -` prefix (CP437/Latin-1 encoded "Área") — NOT UTF-8 flag (bit11=False)
- Filename encoding: raw bytes `╡rea` (Python decoding artifact), stored in legacy CP437 encoding
- 2011-06 uses `Junio_csv/` (underscore, no number suffix) — explains BUG-004B variant (different column structure)

**BUG-003 triggers BEFORE BUG-004** for `caracteristicas_generales` because the R module reads CSV headers using `read.csv()` which hits the invalid multibyte "Ã¡" sequence in column names before rbind() can fail. This is why caracgen always gives BUG-003, not BUG-004.

**ZIP sub-folder naming explains BUG-004 variants:**
| Folder name | Example periods | BUG-004 variant |
|------------|-----------------|-----------------|
| `Junio_csv/` (underscore) | 2008-06, 2011-06 | ERR-004B: "names do not match" |
| `Junio.csv/` (dot) | 2007-06, 2009-06, 2010-06, 2012-06+ | ERR-004A: "numbers of columns" |

---

## BUG-004 scope en epoch1 middle

**Conclusion: BUG-004 is universal in 2012-2017, with one important exception.**

| Period | ocupados | vivienda_hogares | Notes |
|--------|----------|------------------|-------|
| 2012-06 | ERR-004A | ERR-004A | Folder: `Junio.csv/` |
| 2013-06 | ERR-017* | ERR-017* | NEW BUG — filenames have `06` suffix |
| 2014-06 | ERR-004A | — | Folder: `Junio.csv/` |
| 2015-06 | ERR-004A | — | Folder: `Junio.csv/` (validated ZIP) |
| 2016-06 | ERR-004A | ERR-004A | Folder: `Junio.csv/` |
| 2017-06 | ERR-004A | — | Folder: `Junio.csv/` |

*ERR-017: "Shape A files for module 'X' not found in zip. Tried keywords: Y"*

All non-2013 periods fail with BUG-004 variant A. Variant B (names do not match) not seen in 2012-2017 — the `Junio_csv/` folder format was only in 2008 and 2011.

**2013-06 is special:** fails with a completely different error (BUG-017 — keyword matcher can't find files with `06` suffix). Only 1 out of all cached periods has this pattern.

---

## Python 2015-06 results

**Conclusion: Python 2015-06 loads all 6 modules correctly — this is the only working epoch1 middle period.**

| Module | Shape | p_coded columns | Status |
|--------|-------|-----------------|--------|
| caracteristicas_generales | (64785, 44) | 21 | OK |
| ocupados | (30136, 169) | 138 | OK |
| desocupados | (3231, 46) | 24 | OK |
| inactivos | (19035, 30) | 13 | OK |
| vivienda_hogares | (19032, 68) | 52 | OK |
| otros_ingresos | (52402, 43) | 27 | OK |

**Note:** Python produces many "Skipping variable" warnings to stderr during harmonization (columns like P6020, P6040, RAMA2D, etc. missing from the epoch1 data). These are NOT errors — harmonize=True silently skips variables that can't be computed. This constitutes BUG-002 (warnings to stdout/stderr polluting output) in a new context.

The warnings reveal that harmonization for epoch1 is significantly degraded: most harmonized variables (sexo, edad, rama_actividad, ocupacion, ingreso_laboral, etc.) are skipped because epoch1 CSVs have different column naming conventions.

---

## BUG-003 en epoch1 middle

**Conclusion: BUG-003 (UTF-8 filenames crash) is UNIVERSAL for `caracteristicas_generales` across ALL epoch1 periods.**

| Period | caracgen error |
|--------|---------------|
| 2012-06 | BUG-003 (invalid multibyte string at '<a1>sti') |
| 2013-06 | BUG-003 (invalid multibyte string at '<a1>sti') |
| 2014-06 | BUG-003 (invalid multibyte string at '<a1>sti') |
| 2015-06 | BUG-003 (invalid multibyte string at '<a1>sti') |
| 2016-06 | BUG-003 (invalid multibyte string at '<a1>sti') |
| 2017-06 | BUG-003 (invalid multibyte string at '<a1>sti') |

Combined with phase_1 results: BUG-003 hits `caracteristicas_generales` for every epoch1 period tested (2007-2017 inclusive). The "Área" folder in all epoch1 ZIPs uses non-UTF-8 encoding (CP437/Latin-1), and R's `read.csv()` chokes on the column header containing "ó" in "Características".

Modules WITHOUT "Características" in their CSV column headers (ocupados, desocupados, etc.) do NOT hit BUG-003 — they reach BUG-004 or BUG-017 instead.

**Vivienda_hogares verification:** 2012-06 and 2016-06 both give BUG-004A — confirming vivienda_hogares avoids BUG-003 (no "Características" in its headers) but hits BUG-004 instead.

---

## Modules disponibles en epoch1

**Conclusion: epoch1 = 6 modules, epoch2 = 8 modules. Confirmed.**

| Period | Modules | Count |
|--------|---------|-------|
| 2012-06 | caracteristicas_generales, ocupados, desocupados, inactivos, vivienda_hogares, otros_ingresos | 6 |
| 2013-06 | (same 6) | 6 |
| 2015-06 | (same 6) | 6 |
| 2017-06 | (same 6) | 6 |
| 2022-01 | + migracion, otras_formas_trabajo | 8 |
| 2023-06 | (same 8) | 8 |
| 2024-06 | (same 8) | 8 |

Modules `migracion` and `otras_formas_trabajo` are epoch2-only (first appear in 2022-01 or earlier, but not in 2017-06 or before). This is consistent with the smoke test documentation.

---

## New Bug Discovered: BUG-017

**BUG-017 [HIGH, R]: 2013-06 filenames have month-number suffix**

ZIP for 2013-06 has files like `Ocupados06.csv` instead of `Ocupados.csv`. The R keyword matcher looks for "Ocupados" (without suffix) and fails: "Shape A files for module 'X' (2013-06) not found in zip. Tried keywords: Y".

- Affects: ALL modules in 2013-06 (except caracgen, which is intercepted first by BUG-003)
- Scope: Only 2013-06 among all cached periods (scan of all ZIPs confirmed this is unique to 2013-06)
- Root cause: DANE used month-numbered CSV filenames in this particular release
- Fix needed: Keyword matcher in R should also try `{keyword}{month:02d}` variants

---

## Conclusión para Fase 3

**Priority items for epoch1 late + transition (2018-2022):**

1. **Identify epoch1-to-epoch2 transition boundary** — when does the ZIP format change from Cabecera/Resto/Área to a simpler structure? The 2022-01 validated period works in Python; what year does BUG-004 stop?

2. **BUG-004 persistence in 2018-2021** — all tested epoch1 periods (2007-2017) fail in R. Does this continue through 2018-2021? The transition is likely to be abrupt (a format change in DANE's releases).

3. **Python 2021-12 validation** — this is one of the 5 validated periods (checksum not null). Test all 6 modules in Python.

4. **2022-01 in R** — this is a validated period with 8 modules; known BUG-005 (1-col result). Re-confirm shape and test all 8 modules.

5. **BUG-017 scope in 2013** — only June confirmed; other 2013 quarters not cached. If 2013-03, 2013-09, 2013-12 are cached, check them.

6. **Harmonization warnings in epoch1** — the 100+ "Skipping variable" warnings for 2015-06 Python indicate harmonize=True produces near-empty harmonized output for epoch1. Should be flagged as known limitation.

**What is NOT needed in Phase 3:**
- Testing R caracgen in epoch1 (BUG-003 universal — confirmed)
- Testing R non-caracgen in epoch1 pre-2018 (BUG-004 universal — confirmed)
- Testing Python for unvalidated periods (BUG-001 universal — confirmed)
