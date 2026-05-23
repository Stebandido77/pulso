# Bugs Found — pulso-co v1.0.0

## rc1 bugs resolved

### BUG-001: FIXED
- **rc1 symptom:** `allow_unvalidated=True` raised `TypeError: 'NoneType' not subscriptable` at `downloader.py:84` for any period where `checksum_sha256=null` in the registry (~225 of 230 periods).
- **v1.0.0 status:** FIXED. `pulso.load(year=2025, month=6, module='ocupados', allow_unvalidated=True)` returns `(29706, 213)` without error. All 10 tested unvalidated periods complete without TypeError.

---

## New bugs found in v1.0.0

### BUG-002 — Silent empty DataFrame on ParseError for certain unvalidated periods

**Severity:** MEDIUM

**Affected versions:** Likely pre-existing; confirmed present in v1.0.0.

**Affected periods confirmed:** 2008-06, 2013-06, 2020-06 (module: `ocupados`).
Also affects `caracteristicas_generales` and `inactivos` in 2008-06; `desocupados`, `vivienda_hogares`, `otros_ingresos` in 2008-06 load correctly.

**Symptom:**

```python
df = pulso.load(2008, 6, "ocupados", allow_unvalidated=True)
print(df.shape)   # -> (0, 0)
```

The call succeeds (no exception), but returns an empty DataFrame with zero rows AND zero columns. The actual error is emitted only as a `UserWarning`:

```
UserWarning: Loaded 0 of 1 months from registry. 1 months had not been
checksum-validated (e.g., 2008-06). 1 months failed to load and were skipped
(e.g., 2008-06: ParseError: Failed to parse 'Junio_csv/Cabecera - Ocupados (6).csv'
in unvalidated_2008-06.zip: Expected 177 fields in line 38, saw 178).
```

**Root cause (three distinct sub-cases):**

| Period  | ParseError detail |
|---------|-------------------|
| 2008-06 | Malformed CSV: `Expected 177 fields in line 38, saw 178` in `Junio_csv/Cabecera - Ocupados (6).csv` |
| 2013-06 | ZIP uses `Junio.csv/` subfolder structure; file-pattern matcher finds no `Cabecera` or `Resto` file at root level |
| 2020-06 | Expected file `Cabecera - Ocupados.csv` not present inside ZIP (different naming convention) |

**Expected behavior:** Either raise `ParseError` so callers can handle it explicitly, or return the empty DataFrame but also set a programmatic flag/attribute so callers can detect the failure without parsing warning strings.

**Impact:** Code that does `df = pulso.load(..., allow_unvalidated=True)` and then immediately uses `df` (e.g., `df['column']`) will get a `KeyError` or silent wrong results. `df.shape == (0,0)` is the only detectable signal.

**Workaround:** Check `df.shape[0] > 0` or `df.shape != (0, 0)` before using the returned DataFrame. Also consider filtering `warnings` to catch `UserWarning` from pulso.

**Is this a v1.0.0 regression?** Unlikely. The DANE source ZIPs for these specific months have had non-standard structure since they were uploaded. This is a data-quality issue upstream combined with a missing error-propagation design in the parser.

**Recommendation for future version:** When `allow_unvalidated=True` (or `strict=False`) and a month fails to parse, either:
1. Raise `ParseError` (strict behavior even in lax mode), OR
2. Return a clearly-typed `EmptyResult` or raise `DataNotAvailableError`, OR
3. At minimum, ensure the warning message contains enough info for programmatic detection.

---

## Summary

| Bug | Status in v1.0.0 |
|-----|-----------------|
| BUG-001 (TypeError on null checksum) | **FIXED** |
| BUG-002 (Silent empty DF on ParseError) | **NEW / pre-existing** — MEDIUM severity |
