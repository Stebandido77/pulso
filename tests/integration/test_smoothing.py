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
    """apply_smoothing=True for 2015-06 returns correctly normalised Empalme data.

    NOTE: We do not compare against load_merged(2015, 6, harmonize=True) raw
    baseline because there is a known pre-existing parser bug for 2015-06
    (issue #42, tracked separately) where the vivienda_hogares module returns
    mixed-case columns ('Hogar', 'Area') that the merger rejects with a
    MergeError.  The empalme path is independent and produces correctly
    normalised columns.  This test validates only the empalme contract.

    Regression guards:
    - Plausible row count for national GEIH 2015-06.
    - >=300 columns post-harmonize (full merge of all modules).
    - FEX_C canonical column present (Bug 1 regression: column normalisation).
    - fex_c_2011 raw name absent (rename to FEX_C must have happened).
    - HOGAR uppercase (Bug 1 regression: merger key case normalisation).
    - No case-insensitive duplicate column names.
    - No Python warnings.warn() about fex_c_2011 or peso_expansion.
    """
    import pulso

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df_smooth = pulso.load_merged(2015, 6, harmonize=True, apply_smoothing=True)

    # Plausible shape for national GEIH 2015-06 (no raw baseline available)
    assert df_smooth.shape[0] > 50_000, (
        f"Smoothed 2015-06 must have plausible row count for national GEIH, got {df_smooth.shape[0]}"
    )
    assert df_smooth.shape[0] < 100_000, (
        f"Smoothed 2015-06 row count suspiciously high (likely duplicated): {df_smooth.shape[0]}"
    )
    assert df_smooth.shape[1] >= 300, (
        f"Smoothed dataframe must have >=300 columns post-harmonize, got {df_smooth.shape[1]}"
    )

    # Bug 1 regressions: column normalisation
    assert "FEX_C" in df_smooth.columns, (
        "Smoothed DataFrame must expose canonical FEX_C column (empalme column normaliser)"
    )
    assert "fex_c_2011" not in {c.lower() for c in df_smooth.columns}, (
        "fex_c_2011 must have been renamed to FEX_C by _normalize_empalme_columns"
    )
    assert "HOGAR" in df_smooth.columns, (
        "HOGAR must be uppercase — merger key normalisation required"
    )
    # Normalised raw DANE columns are all-uppercase; canonical harmonised columns are
    # lowercase snake_case.  Check only the uppercase set for duplicates — the
    # harmonizer intentionally adds a canonical 'area' alongside the raw 'AREA'.
    raw_cols = [c for c in df_smooth.columns if c == c.upper()]
    raw_lower = [c.lower() for c in raw_cols]
    assert len(set(raw_lower)) == len(raw_lower), (
        "Normalised DANE columns must have no case-insensitive duplicates"
    )

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
    - FEX_C column is present and populated (column normalisation worked).
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
    assert set(df["month"].unique()) == set(range(1, 13)), (
        f"Expected all 12 months, got: {sorted(df['month'].unique())}"
    )

    # Bug 1 regression: FEX_C column present and non-null
    assert "FEX_C" in df.columns, (
        "FEX_C must be present — empalme column normaliser must rename fex_c_2011 → FEX_C"
    )
    assert df["FEX_C"].notna().sum() > 0, "FEX_C must have at least some non-null values"

    # Row count sanity: ~50k-100k rows per month plausible for national GEIH data
    rows_per_month = df.groupby("month").size()
    assert rows_per_month.min() > 5_000, (
        f"Suspiciously few rows in at least one month: {rows_per_month.to_dict()}"
    )

    # No Python warnings.warn() calls about these strings
    fex_warns = [w for w in caught if "fex_c_2011" in str(w.message).lower()]
    peso_warns = [w for w in caught if "peso_expansion" in str(w.message).lower()]
    assert not fex_warns, f"Unexpected warnings.warn about fex_c_2011: {fex_warns}"
    assert not peso_warns, f"Unexpected warnings.warn about peso_expansion: {peso_warns}"
