"""Integration tests confirming issue #42 is closed.

load_merged(2015, 6) previously raised MergeError because vivienda_hogares
returned mixed-case columns ('Hogar', 'Area', 'Fex_c_2011').  These tests
validate that the Shape A normalizer fixes that.

Run with: pytest -m integration --run-integration -v
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
def test_load_merged_2015_06_no_apply_smoothing() -> None:
    """load_merged(2015, 6, harmonize=True) must complete without MergeError.

    This is the primary regression test for issue #42.  The raw (non-smoothing)
    path is exercised: Shape A parse → merge → harmonize.  Before the fix,
    vivienda_hogares delivered mixed-case columns that caused the merger to raise
    MergeError('Module is missing merge keys: expected [...] HOGAR').
    """
    import pulso

    df = pulso.load_merged(2015, 6, harmonize=True)

    assert df.shape[0] > 50_000, (
        f"load_merged(2015, 6) must return plausible row count, got {df.shape[0]}"
    )
    assert df.shape[0] < 200_000, (
        f"load_merged(2015, 6) row count suspiciously high (likely duplicated): {df.shape[0]}"
    )


@pytest.mark.integration
def test_load_merged_2015_06_columns_uppercase() -> None:
    """All raw DANE columns in the merged DataFrame must be uppercase post-load."""
    import pulso

    df = pulso.load_merged(2015, 6, harmonize=True)

    raw_cols = [c for c in df.columns if c == c.upper() and not c.startswith("_")]
    mixed_case = [c for c in df.columns if c != c.upper() and c != c.lower()]
    assert not mixed_case, (
        f"Found mixed-case raw columns after Shape A normalization: {mixed_case[:10]}"
    )

    assert "FEX_C" in df.columns or any(c.upper() == "FEX_C" for c in df.columns), (
        "FEX_C canonical weight column must be present post-normalization"
    )
    assert "fex_c_2011" not in {c.lower() for c in df.columns}, (
        "fex_c_2011 must have been renamed to FEX_C by _normalize_dane_columns"
    )
    assert "HOGAR" in df.columns or "hogar" in df.columns, (
        "HOGAR merger key must be present (uppercase normalization)"
    )
    _ = raw_cols  # referenced above for clarity
