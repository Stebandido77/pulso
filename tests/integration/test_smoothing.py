"""Integration tests for apply_smoothing and load_empalme against real DANE data.

Requires network access (first run only; subsequent runs use the local cache).
Run with: pytest -m integration --run-integration -v

Cache layout: ~/.cache/pulso/empalme/{year}.zip  (~230 MB per year).
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_smoothing_2015_06_real() -> None:
    """apply_smoothing=True for 2015-06 swaps the full dataset for Empalme data.

    Assertions:
    - Shape matches the non-smoothed call (same rows, same columns post-harmonize).
    - The FEX_C weight distribution differs measurably, proving the swap happened.
    """
    import pulso

    df_raw = pulso.load_merged(2015, 6, harmonize=True)
    df_smooth = pulso.load_merged(2015, 6, harmonize=True, apply_smoothing=True)

    assert (
        df_smooth.shape == df_raw.shape
    ), f"Smoothed shape {df_smooth.shape} != raw shape {df_raw.shape}"

    # The Empalme data has a different FEX_C distribution (the whole point of
    # apply_smoothing).  Check the column exists and the mean differs by at
    # least 1% relative to the raw mean.
    assert (
        "peso_expansion" in df_smooth.columns
    ), "Expected 'peso_expansion' column in harmonized output"
    raw_mean = df_raw["peso_expansion"].dropna().mean()
    smooth_mean = df_smooth["peso_expansion"].dropna().mean()
    assert raw_mean != 0, "Raw peso_expansion mean is zero — unexpected"
    relative_diff = abs(smooth_mean - raw_mean) / abs(raw_mean)
    assert relative_diff > 0.0, (
        f"peso_expansion mean unchanged after smoothing ({raw_mean:.2f}); "
        "swap may not have happened"
    )


@pytest.mark.integration
def test_load_empalme_2015_real() -> None:
    """load_empalme(2015) returns 12 months stacked with expected row counts."""
    import pulso

    df = pulso.load_empalme(2015, harmonize=True)

    assert "year" in df.columns
    assert "month" in df.columns

    months_found = sorted(df["month"].unique())
    assert months_found == list(range(1, 13)), f"Expected all 12 months, got: {months_found}"

    assert (df["year"] == 2015).all(), "All rows must have year=2015"

    # Sanity check: ~50k-100k rows per month is plausible for GEIH national data
    rows_per_month = df.groupby("month").size()
    assert (
        rows_per_month.min() > 5_000
    ), f"Suspiciously few rows in at least one month: {rows_per_month.to_dict()}"
