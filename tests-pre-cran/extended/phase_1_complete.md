# Phase 1 Complete — SEGFAULT + ECH + Epoch1 Early

**Completed:** 2026-05-23 ~02:00 UTC
**Duration:** ~45 min
**Periods tested:** 6 (2007-06, 2007-12, 2008-06, 2009-06, 2010-06, 2011-06)
**Modules tested:** 36 (6 periods × 6 modules)
**New findings:** 4 (1 bug closed, 2 new bugs, 1 scope extension)

---

## TAREA 1: SEGFAULT Investigation

**Result: NOT REPRODUCIBLE**

Tested 3 scenarios × 3 repetitions each = 9 runs total. All exit codes: 0.

| Test | Scenario | Runs | Exit codes |
|------|----------|------|------------|
| A | Same period (2024-06 ocupados), two calls | 3 | 0, 0, 0 |
| B | Different modules (ocupados + desocupados), two calls | 3 | 0, 0, 0 |
| C | Error (2007-12 fails) then success (2024-06 ok) | 3 | 0, 0, 0 |

Test C output confirms R recovers cleanly from BUG-004 errors:
```
Call1 error: numbers of columns of arguments do not match
Call2 OK: 29925 x 200
```

**CONCLUSION:** BUG-SEGFAULT is CLOSED — not reproducible on R 4.5.2 / Windows 11. May have been a platform-specific or version-specific issue.

Also noted: Test A produces a benign warning on both calls:
```
Warning message: Unknown or uninitialised column: `err`.
```
This comes from `r1$err` access on a data.frame — not a bug in pulso, just the test script's tryCatch pattern.

---

## TAREA 2: ECH Error Test

### Python

| Year | Error type | Message | Clear? |
|------|-----------|---------|--------|
| 2005 | PulsoError | "Year 2005 is out of supported range 2006-2100." | Yes — but message says 2006, not 2007 |
| 2006 | DataNotAvailableError | "Data for 2006-06 is not available in the registry." | OK |
| 2007 | TypeError | 'NoneType' object is not subscriptable (BUG-001) | No — misleading error |

**Note:** Python says "supported range 2006-2100" for year < 2006, but actual data starts 2007. This is a minor inconsistency in the error message range bound.

**Note:** For 2007, Python gives BUG-001 TypeError instead of a clean error — because 2007-06 has checksum=null and the downloader crashes before reaching validation.

### R

| Year | Error class | Message | Clear? |
|------|------------|---------|--------|
| 2005 | pulso_validation_error | "Year 2005 is before pulso coverage starts (2007)" | Yes |
| 2006 | pulso_validation_error | "Year 2006 is before pulso coverage starts (2007)" | Yes |

**CONCLUSION:** R error messages are clear and correct. Python's error handling for pre-2007 periods is mixed — clear for 2005, misleading for 2007 (BUG-001 triggers first). Neither Python nor R mentions "ECH" by name in the error — they say "coverage starts (2007)" which is acceptable (no need to mention ECH by name to users).

---

## TAREA 3: Epoch1 Early (2007-2011) Results

### Python Results

| Period | caracgen | ocupados | desocupados | inactivos | vivienda | otros_ingresos |
|--------|----------|----------|-------------|-----------|----------|----------------|
| 2007-06 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 |
| 2007-12 | OK(65765,50) | OK(26472,194) | OK(3445,46) | OK(21502,28) | OK(17324,62) | OK(51419,34) |
| 2008-06 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 |
| 2009-06 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 |
| 2010-06 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 |
| 2011-06 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 | ERR-001 |

**ERR-001:** `TypeError: 'NoneType' object is not subscriptable` (checksum=null in sources.json)

Only 5 periods in the entire registry have checksum_sha256 set: `2007-12, 2015-06, 2021-12, 2022-01, 2024-06`. All others (~225 periods) fail BUG-001.

### R Results

| Period | caracgen | ocupados | desocupados | inactivos | vivienda | otros_ingresos |
|--------|----------|----------|-------------|-----------|----------|----------------|
| 2007-06 | ERR-003 | ERR-004A | ERR-004A | ERR-004A | ERR-004A | ERR-004A |
| 2007-12 | ERR-004A | ERR-004A | ERR-004A | ERR-004A | ERR-004A | ERR-004A |
| 2008-06 | ERR-003 | ERR-004B | ERR-004B | ERR-004B | ERR-004B | ERR-004B |
| 2009-06 | ERR-003* | ERR-004A | ERR-004A | ERR-004A | ERR-004A | ERR-004A |
| 2010-06 | ERR-004A | ERR-004A | ERR-004A | ERR-004A | ERR-004A | ERR-004A |
| 2011-06 | ERR-003 | ERR-004B | ERR-004B | ERR-004B | ERR-004B | ERR-004B |

**ERR-003:** `invalid multibyte string at '<a1>sti'` (UTF-8 filename crash — BUG-003)
**ERR-004A:** `numbers of columns of arguments do not match` (rbind without fill)
**ERR-004B:** `names do not match previous names` (rbind variant)

*2009-06 caracgen also tried to download from remote before failing with UTF-8 error*
*2010-06 caracgen shows ERR-004A instead of ERR-003 — zip structure may differ*

Note: `allow_unvalidated=TRUE` was NOT tested in R since `pulso_load()` does not support this argument (gives "unused argument" error — new bug BUG-015).

---

## TAREA 4: BUG-004 Scope Confirmation

**CONCLUSION: Universal in epoch1 — R cannot load ANY epoch1 module, ANY period tested.**

### Is it universal?
- All 36 R combinations tested (6 periods × 6 modules) → ALL FAIL
- Zero exceptions found

### Error message variants
BUG-004 has two manifestations depending on the ZIP file structure:
- **Variant A** (`numbers of columns of arguments do not match`): 2007-06, 2007-12, 2009-06, 2010-06
- **Variant B** (`names do not match previous names`): 2008-06, 2011-06
- Both are caused by the same root: `rbind()` without `fill=TRUE` when rbinding DataFrames from different regional CSV files that have different column structures

### Does allow_unvalidated=TRUE help for R epoch1?
No — pulso_load() in R does NOT accept allow_unvalidated parameter (BUG-015).

---

## Bugs encontrados / confirmados en esta fase

| # | Severity | Component | Description |
|---|----------|-----------|-------------|
| BUG-SEGFAULT | CLOSED | R | Not reproducible in R 4.5.2/Win11 (exit 0 in all 9 runs) |
| BUG-013 (new) | High | Python | BUG-001 scope: affects ~225 periods (all with checksum=null); only 5 periods work |
| BUG-015 (new) | Low | R | allow_unvalidated not in pulso_load() signature → "unused argument" error |
| BUG-016 (new) | Medium | R | BUG-004 has two error variants: "numbers of columns" vs "names do not match" |

### Confirmed pre-existing bugs
- **BUG-004 (Critical, R):** Confirmed universal for epoch1 early (2007-2011) — zero exceptions
- **BUG-003 (High, R):** Confirmed for caracteristicas_generales in 2007-06, 2008-06, 2009-06, 2011-06 (and possibly others)

---

## Key findings for next phases

1. **Python testing protocol:** Only 5 validated periods will work with allow_unvalidated=True. For all other periods, Python testing should test the cache-only path (without allow_unvalidated, expecting ValidationError) OR use validated periods.
2. **R epoch1 is uniformly broken:** No need to test all 25 epoch1 periods in R — they will all fail with BUG-004 or BUG-003.
3. **BUG-003 pattern:** Not all period/module combos hit BUG-003 — vivienda_hogares and otros_ingresos seem to avoid it in some periods (they get BUG-004 instead).
4. **SEGFAULT:** Can be de-prioritized in subsequent phases.
