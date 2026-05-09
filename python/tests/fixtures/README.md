# Test fixtures

This directory holds synthetic data used by tests so they run without network access.

## `zips/`

Tiny synthetic ZIPs that mimic the structure of real DANE GEIH ZIPs:

- `geih1_sample.zip` — represents an `geih_2006_2020` epoch month (latin-1, semicolon CSV)
- `geih2_sample.zip` — represents a `geih_2021_present` epoch month (utf-8, semicolon CSV)

Each contains a handful of synthetic rows per module so the parser can be exercised end-to-end. **Do not commit real DANE data here.** These ZIPs are constructed by the test setup and committed for reproducibility.

Built in Phase 1 by Claude Code. The construction script (if any) lives at `tests/_build_fixtures.py`.

## `expected_outputs/`

Snapshots of the DataFrames produced by loading each fixture ZIP, stored as Parquet. Used in regression tests: if the parser, harmonizer, or merger changes its output for the same input, the test fails and the developer either fixes the regression or knowingly updates the snapshot.
