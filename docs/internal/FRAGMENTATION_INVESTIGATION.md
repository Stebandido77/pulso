# Fragmentation investigation — pulso pipeline (read-only)

Triggered by the bug found in Commit 14: `df.assign(year=y, month=m)` raised
`pandas.errors.PerformanceWarning` ("DataFrame is highly fragmented") which
the project's `filterwarnings = ["error"]` config escalated to a real error.
The Commit 14 fix wraps that single call in a narrowly-scoped
`catch_warnings`. This report investigates whether that fix is local or
papers over a broader pattern.

**TL;DR**: there IS a broader pattern. Shape B (GEIH-2 / 2022+) parser
returns DataFrames with **one block per column** (e.g. 200 cols → 200
blocks). The Commit 14 fix is correct for the immediate symptom and
sufficient for v1.0.0rc2 release, but the root cause — `_parse_csv` not
consolidating like `parse_shape_a_module` does — is real technical debt
worth a follow-up commit (not blocking).

---

## 1. Inventory of operations that *could* fragment a DataFrame

### A. `df[col] = ...` (per-column setitem on a DataFrame)

| Location | Operation | Verdict |
|---|---|---|
| `pulso/_core/parser.py:213` | `df_cab["CLASE"] = 1` | **Safe.** Adds 1 column to a freshly-parsed (single-block-per-dtype) DataFrame in `parse_shape_a_module`. |
| `pulso/_core/parser.py:226` | `df_resto["CLASE"] = 2` | **Safe.** Same as above. |
| `pulso/_core/parser.py:318` | `df["_area"] = df["CLASE"].map({1: "cabecera", 2: "resto"})` | **Safe.** Single column on the just-parsed Shape A df. |
| `pulso/_core/parser.py:364` | `part["_area"] = label` | **Safe.** Single column on a freshly `_parse_fn`-returned df. |
| `pulso/_core/expander.py:81` | `result["_weight"] = result[weight]` | **Safe.** `result = df.copy()` runs first; `copy(deep=True)` consolidates. |
| `pulso/_core/harmonizer_funcs.py:115-117` | `result[mask] = value` on a `pd.Series` | **Safe.** Series, not DataFrame — no block-fragmentation concept. |

None of the per-column setitems happen on a wide harmonized DataFrame.

### B. `df.assign(...)`

| Location | Operation | Verdict |
|---|---|---|
| `pulso/_core/loader.py:288` | `df = df.assign(year=y, month=m)` | **Triggers warning.** Already wrapped in `catch_warnings(PerformanceWarning)` by Commit 14. |
| `pulso/_core/loader.py:435` | `merged = merged.assign(year=y, month=mo)` (apply_smoothing path, single-period) | **Safe in practice.** Smoothing path uses empalme data which is narrower; no observed warning. Not wrapped. |
| `pulso/_core/loader.py:520` | `merged = merged.assign(year=y, month=mo)` (load_merged main path) | **Triggers warning.** Wrapped by Commit 14. |
| `pulso/_core/empalme.py:445` | `frames.append(df.assign(year=year, month=detected_month))` | **Safe.** Per-month frames; df has not been merged with other modules yet, so still ~consolidated. Not wrapped. |

### C. `pd.concat(...)` (horizontal `axis=1` is the fragmentation source)

| Location | axis | Verdict |
|---|---|---|
| `pulso/_core/harmonizer.py:368` | `pd.concat(canonical_series_list, axis=1)` | **Fragmentation source.** Up to 30 Series concatenated; result has ~13–30 blocks (one per Series). |
| `pulso/_core/harmonizer.py:371` | `pd.concat([df, canonical_df], axis=1)` | **Compounds fragmentation.** Adds ~13–30 columns to the (possibly already 200-block) raw df. |
| `pulso/_core/empalme.py:449` / `:522` / `loader.py:312` / `:544` / `parser.py:229` / `:370` | All `axis=0` (vertical) | **Safe.** Vertical concat doesn't fragment columns. |

### D. `merge` (iterative joins in `_merge_within_level`)

| Location | Operation | Verdict |
|---|---|---|
| `pulso/_core/merger.py:53` | `merged = merged.merge(df_to_merge, on=keys, how=how)` in a loop | **Mild fragmentation.** Each `merge()` returns a new DataFrame; pandas' merge may produce many small blocks when joining wide frames. Not the dominant source — `harmonize_dataframe` afterward concats more cols anyway. |

### E. Other warning suppressions in `pulso/`

| Location | Suppressed | Justification |
|---|---|---|
| `pulso/_core/loader.py:286-287` | `pd.errors.PerformanceWarning` | The Commit 14 fix. Scoped to the `df.assign(year, month)` call. |
| `pulso/_core/loader.py:518-519` | `pd.errors.PerformanceWarning` | Same fix in `load_merged`. |
| `pulso/_utils/columns.py:36, 46` | (emits `UserWarning`, doesn't suppress) | Operator-facing warning about duplicate / multiple FEX_C columns. Legitimate. |
| `pulso/_core/loader.py:48` | (emits `DeprecationWarning`, doesn't suppress) | Legitimate `allow_unvalidated` deprecation. |
| `pulso/_core/loader.py:105` | (emits aggregated `UserWarning`) | Multi-period summary warning. Legitimate. |
| `pulso/_core/loader.py:440` | (emits `UserWarning`) | apply_smoothing fallback for year=2020. Legitimate. |

No silent suppression of any other pandas/numpy warnings outside of the
two PerformanceWarning sites added by Commit 14.

---

## 2. Empirical measurements (real 2024-06 ocupados, `parse_module` + harmonize)

```
pd.read_csv (low_memory=False), 200 cols  → 200 blocks  ← raw fragmentation
After _normalize_dane_columns (Shape A only)            →  12 blocks   ← copy() consolidates!
After parse_module (Shape B path, 2024-06, total area)  → 200 blocks   ← no normalize_dane_columns call
After harmonize_dataframe (+13 canonical cols)          → 213 blocks
After df.assign(year=y, month=m)                        → 215 blocks
                                                          ^ pd.errors.PerformanceWarning fires here
After df.copy()                                         →  23 blocks   ← deep copy consolidates per-dtype
```

**Key finding:** `_normalize_dane_columns` (Shape A path) calls `df.copy()`,
which collapses 200 single-column blocks into ~12 dtype-keyed blocks.
`_parse_csv` (Shape B path) does NOT call `_normalize_dane_columns` and
returns the fragmented frame as-is. That is why Commit 14's bug only
manifested for GEIH-2 multi-period loads — every Shape B period inherits
200+ blocks all the way through the pipeline.

---

## 3. Impact analysis

| Issue | Path | Severity | Fixed by |
|---|---|---|---|
| `df.assign(year, month)` triggers warning on wide frames | `load`, `load_merged` main path | **Was critical** (every multi-period real-data load failed). | Commit 14 (band-aid, narrow `catch_warnings`). |
| `_parse_csv` returns 200-block DataFrames for Shape B | All Shape B (2022+) loads | **Latent.** Causes the warning above; would also cause warnings in any *user* code that does `df["new_col"] = ...` on the result if they have strict warning filters. | NOT FIXED. Root cause. |
| `harmonize_dataframe` concats 13–30 Series → up to 30 blocks added | All harmonized loads | **Mild.** Compounds fragmentation but is the natural way to assemble harmonized columns. | NOT FIXED. |
| `_merge_within_level` iterative merges | `load_merged` | **Mild.** Could be replaced with a multi-DataFrame merge, but pandas doesn't provide one. | NOT FIXED. |

The Commit 14 fix prevents the symptom *inside pulso*. Outside pulso —
e.g. a notebook user who runs `pulso.load(...)` with strict warning
filters and then does `df["new"] = something` — the warning would still
fire. That is acceptable behaviour for a data-loading library (the warning
isn't a bug; it's pandas suggesting a defrag), but documenting the
returned DataFrame's block count would be honest.

---

## 4. Proposed fixes (NOT implemented)

Three options, smallest to largest:

### Option A — defrag `_parse_csv` output (smallest, root-cause fix)

```python
# pulso/_core/parser.py, end of _parse_csv (line ~255)
if columns is not None:
    available = [c for c in columns if c in df.columns]
    df = df[available]

return df.copy()  # ← single-line fix: consolidate before returning
```

This brings Shape B in line with what Shape A already does (via
`_normalize_dane_columns`). Cost: one full-data copy per parse — same
memory bump that Shape A already pays. Removes the need for Commit 14's
`catch_warnings` wrappers, but keeping them as belt-and-suspenders is
also reasonable.

### Option B — defrag at the end of `harmonize_dataframe`

```python
# pulso/_core/harmonizer.py, line ~371
if keep_raw:
    return pd.concat([df, canonical_df], axis=1).copy()  # ← consolidate
return canonical_df.copy()
```

Defrags the moment user-visible data is finalised. Cost: same memory bump
but at a later stage. Less surgical than Option A.

### Option C — bulk-build year/month + do single concat in loader

```python
# pulso/_core/loader.py, line ~288
if multi:
    extras = pd.DataFrame({"year": y, "month": m}, index=df.index)
    df = pd.concat([df, extras], axis=1)
```

Avoids `df.assign` entirely. But because the underlying df is still
fragmented, downstream user code still hits the warning the moment they
do `df["my_var"] = ...`. Doesn't fix the root cause.

**Recommended ordering:** Option A first (one-line fix, addresses root
cause), then remove Commit 14's `catch_warnings` wrappers if Option A
proves sufficient.

### Verification check that would gate the fix

```python
def test_parse_csv_returns_consolidated_frame(...):
    df = parse_module(...)
    # Assert nblocks roughly equals number of distinct dtypes (not n_cols)
    n_dtypes = len(df.dtypes.unique())
    assert df._mgr.nblocks <= n_dtypes * 2, (
        f"Parser returned fragmented DataFrame: {df._mgr.nblocks} blocks "
        f"for {df.shape[1]} columns / {n_dtypes} dtypes"
    )
```

---

## 5. Recommendation: BLOCKING for rc2? Or v1.1.0?

**Not blocking.** Ship rc2 with the Commit 14 fix as-is.

Reasoning:
1. The Commit 14 fix is **correct and safe**: it preserves the
   `filterwarnings = ["error"]` policy everywhere except two narrowly-
   scoped lines, and integration tests confirm both `load` and
   `load_merged` work end-to-end on real DANE data after the fix.
2. Option A would be a one-line change but it touches the parser, which
   handles dozens of edge cases (BOM, mojibake, separator fallback,
   merge-key normalization). Adding a `.copy()` at the end is unlikely
   to break anything, but "unlikely" before a release candidate isn't
   "audited and tested".
3. The latent issue only causes a *warning* in user code, not an error.
   Users without `filterwarnings = ["error"]` (i.e. the vast majority)
   will not notice.

**Defer to v1.1.0:**
- Implement Option A (`return df.copy()` in `_parse_csv`).
- Add the verification test above.
- Remove Commit 14's `catch_warnings` wrappers if Option A proves
  sufficient.
- Document the DataFrame block layout in `harmonize_dataframe`'s
  docstring (so power-users know what to expect).

---

## 6. Honest answer to the prompt's last question

**Was the Commit 14 fix puntual or did it hide a problem más amplio?**

It was **puntual**. The deeper problem is real but not severe:
`_parse_csv` returns a fragmented DataFrame because it skips the
`df.copy()`-via-`_normalize_dane_columns` defragmentation that Shape A
gets for free. That fragmentation propagates through harmonization and
makes any `df.assign` / `df[col]=...` on the result emit
`pandas.errors.PerformanceWarning`.

Inside pulso, only two call sites do that (year/month assignment in
`load` and `load_merged`), and Commit 14 fixed both. **No other call
site in pulso/ has the same issue**, so the band-aid is sufficient
coverage. Outside pulso (user code), the warning may still fire on the
returned DataFrame — acceptable for a data-loading library, especially
because the message itself is informative ("call `.copy()` to defrag").

The cleanest follow-up is a v1.1.0 commit:
1. Add `return df.copy()` at the end of `_parse_csv` (Option A).
2. Add a regression test asserting `nblocks ≤ 2 × n_dtypes` after
   `parse_module`.
3. Remove the two `catch_warnings(PerformanceWarning)` wrappers if step
   1 makes them redundant.

That commit is small, localised, and has a clear gating test. It belongs
in v1.1.0, not blocking v1.0.0rc2.
