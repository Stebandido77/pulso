"""Integration tests for apply_smoothing and load_empalme against real DANE data.

Requires network access (first run only; subsequent runs use the local cache).
Run with: pytest -m integration --run-integration -v

Cache layout: ~/.cache/pulso/empalme/{year}.zip  (~230 MB per year).
"""

from __future__ import annotations

import warnings

import pytest


@pytest.mark.integration
def test_smoothing_2015_06_real() -> None:
    """apply_smoothing=True for 2015-06 swaps the full dataset for Empalme data.

    Regression guards:
    - Shape matches the non-smoothed call (same rows, same columns post-harmonize).
    - FEX_C canonical column is present (Bug 1 regression: column normalization).
    - fex_c_2011 raw name is not present (rename to FEX_C must have happened).
    - HOGAR is uppercase (Bug 1 regression: merger key case normalization).
    - No case-insensitive duplicate column names.
    - No Python warnings.warn() about fex_c_2011 or peso_expansion.
    """
    import pulso

    df_raw = pulso.load_merged(2015, 6, harmonize=True)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df_smooth = pulso.load_merged(2015, 6, harmonize=True, apply_smoothing=True)

    assert (
        df_smooth.shape == df_raw.shape
    ), f"Smoothed shape {df_smooth.shape} != raw shape {df_raw.shape}"

    # Bug 1 regressions: column normalization
    assert (
        "FEX_C" in df_smooth.columns
    ), "Smoothed DataFrame must expose canonical FEX_C column (empalme column normalizer)"
    assert "fex_c_2011" not in {
        c.lower() for c in df_smooth.columns
    }, "fex_c_2011 must have been renamed to FEX_C by _normalize_empalme_columns"
    assert (
        "HOGAR" in df_smooth.columns
    ), "HOGAR must be uppercase — merger key normalization required"
    col_lower = [c.lower() for c in df_smooth.columns]
    assert len(set(col_lower)) == len(
        col_lower
    ), "Columns must not have case-insensitive duplicates after normalization"

    # No Python warnings.warn() about these strings (harmonizer uses logger.warning,
    # not warnings.warn, so this is a guard against accidental warnings.warn calls).
    fex_warns = [w for w in caught if "fex_c_2011" in str(w.message).lower()]
    peso_warns = [w for w in caught if "peso_expansion" in str(w.message).lower()]
    assert not fex_warns, f"Unexpected warnings.warn about fex_c_2011: {fex_warns}"
    assert not peso_warns, f"Unexpected warnings.warn about peso_expansion: {peso_warns}"


@pytest.mark.integration
def test_load_empalme_2015_real() -> None:
    """load_empalme(2015) returns 12 months stacked with expected structure.

    Regression guards:
    - All 12 months present with correct year tag.
    - FEX_C column is present and populated (column normalization worked).
    - No Python warnings.warn() about fex_c_2011 or peso_expansion.
    - Row counts per month are plausible for national GEIH microdata.
    """
    import pulso

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load_empalme(2015, harmonize=True)

    # Year / month structure
    assert "year" in df.columns
    assert df["year"].nunique() == 1, "All rows must have the same year"
    assert df["year"].iloc[0] == 2015, "year column must equal 2015"
    assert "month" in df.columns
    assert set(df["month"].unique()) == set(
        range(1, 13)
    ), f"Expected all 12 months, got: {sorted(df['month'].unique())}"

    # Bug 1 regression: FEX_C column present and non-null
    assert (
        "FEX_C" in df.columns
    ), "FEX_C must be present — empalme column normalizer must rename fex_c_2011 → FEX_C"
    assert df["FEX_C"].notna().sum() > 0, "FEX_C must have at least some non-null values"

    # Row count sanity: ~50k-100k rows per month plausible for national GEIH data
    rows_per_month = df.groupby("month").size()
    assert (
        rows_per_month.min() > 5_000
    ), f"Suspiciously few rows in at least one month: {rows_per_month.to_dict()}"

    # No Python warnings.warn() calls about these strings
    fex_warns = [w for w in caught if "fex_c_2011" in str(w.message).lower()]
    peso_warns = [w for w in caught if "peso_expansion" in str(w.message).lower()]
    assert not fex_warns, f"Unexpected warnings.warn about fex_c_2011: {fex_warns}"
    assert not peso_warns, f"Unexpected warnings.warn about peso_expansion: {peso_warns}"
