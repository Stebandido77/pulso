# Performance: consolidate Shape B DataFrames in `_parse_csv`

**Type:** Performance
**Severity:** Medium (affects perceived speed in wide DataFrames, no correctness impact)
**Target version:** v1.1.0
**Found in:** v1.0.0rc2 audit

## Background

During Commit 14 of v1.0.0rc2, integration tests revealed that wide
GEIH-2 DataFrames (post-2022 epoch) trigger a pandas `PerformanceWarning`
about fragmentation. The Commit 14 fix wraps the affected `df.assign()`
calls in `catch_warnings`, which solves the symptom but not the root cause.

## Root cause analysis

The two parsing paths handle DataFrame consolidation asymmetrically:

| Path | Function | Calls `_normalize_dane_columns`? | Block count for 2024-06 ocupados |
|------|----------|----------------------------------|----------------------------------|
| Shape A (GEIH-1, pre-2022) | `parse_shape_a_module` | Yes | 12 blocks |
| Shape B (GEIH-2, post-2022) | `_parse_csv` | **No** | 200 blocks |

`_normalize_dane_columns` calls `df.copy()` internally, which consolidates
fragmented blocks into contiguous memory. Shape A gets this for free;
Shape B doesn't.

## Empirical measurements (2024-06 ocupados)

```
pd.read_csv(low_memory=False)          → 200 cols / 200 blocks
parse_shape_a_module + normalize       → 12 blocks
_parse_csv (Shape B, no normalize)     → 200 blocks (no consolidation)
After harmonize_dataframe              → 213 blocks
After df.assign(year, month)           → 215 blocks + PerformanceWarning
```

## Proposed fix

Add `df = df.copy()` at the end of `_parse_csv` (or equivalent
consolidation step). This mirrors what `_normalize_dane_columns`
implicitly does for Shape A.

```python
# pulso/_core/parser.py
def _parse_csv(...):
    # ... existing logic ...
    return df.copy()  # consolidate before returning
```

## Verification

After fix, the following should hold:

```python
def test_parse_csv_returns_consolidated_dataframe():
    """Regression: _parse_csv should return DataFrames with low fragmentation."""
    df = _parse_csv(...)
    assert df._mgr.nblocks <= 2 * len(df.dtypes.unique()), (
        f"DataFrame is fragmented: {df._mgr.nblocks} blocks for "
        f"{len(df.dtypes.unique())} dtypes"
    )
```

## Cleanup after fix

After the root cause is fixed, the two `catch_warnings(PerformanceWarning)`
blocks introduced in Commit 14 (rc2) can be removed:

- `pulso/_core/loader.py` (around line 286–288) — `load` multi-period assign
- `pulso/_core/loader.py` (around line 518–520) — `load_merged` multi-period assign

A regression test should ensure no new `PerformanceWarning` is silently
escalated to error.

## Why this is deferred to v1.1.0 (not blocking rc2)

1. The fix touches `parser.py`, which has many edge cases (latin1 encoding,
   separators, Cabecera/Resto for Shape A, etc). Any change there merits
   its own RC for validation.
2. No correctness impact: data loaded is identical, just slower in wide
   DataFrames.
3. The Commit 14 mitigation is sufficient for the user-visible symptom.
4. v1.0.0rc2 fixes a critical bug (C-1) affecting users *now*. Delaying
   release for a non-blocking optimization would prolong exposure.

## References

- `FRAGMENTATION_INVESTIGATION.md` (full audit report in the repo)
- Commit 14: PerformanceWarning fix (band-aid)
- pandas docs on DataFrame fragmentation: https://pandas.pydata.org/docs/user_guide/scale.html
