"""Integration tests for the use cases users actually reported.

Run with: ``pytest tests/integration/test_user_use_cases.py --run-integration -v``

These hit real DANE URLs (through the pulso downloader cache, so a
fully-warm cache makes them fast). They are skipped by default — opt
in with ``--run-integration``.

The full-history matrix tests are also marked ``slow`` so a
network-cold run can be limited to the lighter cases via
``-m "integration and not slow"``.
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

import pulso

# ---------------------------------------------------------------------------
# CASO 1 — June 2007 through 2024 (the case that triggered the audit)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
def test_june_full_history_2007_2024() -> None:
    """User Case 1: June across 18 years (2007-2024).

    Must return a non-empty DataFrame, emit ONE aggregated UserWarning
    (not N), and stack via the year/month columns.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=range(2007, 2025),
            month=6,
            module="ocupados",
            strict=False,
            show_progress=False,
        )

    assert len(df) > 0, "Empty DataFrame for full June history"
    assert "year" in df.columns
    assert "month" in df.columns
    assert df["month"].unique().tolist() == [6]
    assert df["year"].nunique() >= 10

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1, (
        f"Expected 1 aggregated warning, got {len(user_warnings)}: "
        f"{[str(w.message) for w in user_warnings]}"
    )
    msg = str(user_warnings[0].message)
    assert "checksum-validated" in msg or "failed to load" in msg


# ---------------------------------------------------------------------------
# CASO 2 — Every month from 2007 through 2026 (the ambitious one)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
def test_all_months_full_history_2007_2026() -> None:
    """User Case 2: every month in 2007-2026 (year x month cartesian).

    Loads ~240 periods. Definitely slow. Marked @slow so opt-in is
    explicit; run with: ``pytest -m "integration and slow" --run-integration``.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=range(2007, 2027),
            month=range(1, 13),
            module="ocupados",
            strict=False,
            show_progress=False,
        )

    assert len(df) > 0
    assert "year" in df.columns
    assert "month" in df.columns
    assert df["year"].nunique() >= 15
    assert df["month"].nunique() == 12

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
def test_includes_unreleased_year_2027() -> None:
    """range(2007, 2028) including 2027 (no data published).

    Expected: no crash, warning lists missing periods, 2027 rows absent.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=range(2007, 2028),
            month=6,
            module="ocupados",
            strict=False,
            show_progress=False,
        )

    assert len(df) > 0
    assert 2027 not in df["year"].values

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) >= 1
    combined = " ".join(str(w.message) for w in user_warnings)
    # Either the unreleased month is in the failures list explicitly
    # or the warning generally mentions failed loads.
    assert "2027" in combined or "failed to load" in combined


@pytest.mark.integration
def test_only_unreleased_years_returns_empty_with_warning() -> None:
    """range(2026, 2030) — every year past current registry coverage.

    Expected: empty DataFrame (not None), single warning summarising
    that nothing loaded.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=range(2026, 2030),
            month=6,
            module="ocupados",
            strict=False,
            show_progress=False,
        )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) >= 1


@pytest.mark.integration
@pytest.mark.slow
def test_partial_release_year_2025() -> None:
    """2025 may have only some months published.

    Loads what's available, warns about what isn't.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=2025,
            month=range(1, 13),
            module="ocupados",
            strict=False,
            show_progress=False,
        )

    if len(df) > 0:
        # Single year — no year column added unless multi-period.
        # Multi-month is multi-period, so we expect year/month cols.
        assert df["year"].unique().tolist() == [2025]
        if df["month"].nunique() < 12:
            user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
            assert len(user_warnings) >= 1


# ---------------------------------------------------------------------------
# Regression: the EXACT command the user reported
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.slow
def test_exact_user_reported_case() -> None:
    """rc1: TypeError at downloader.py:84. rc2: works.

    The default strict=False emits the aggregated UserWarning we test
    elsewhere; here we just want to confirm the call completes and
    returns data (the regression contract).
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        df = pulso.load(year=range(2007, 2025), month=6, module="ocupados", show_progress=False)
    assert len(df) > 0
    # The DataFrame should have at least the standard merge keys plus
    # year/month from the multi-period stack.
    assert "year" in df.columns
    assert "month" in df.columns


# ---------------------------------------------------------------------------
# strict=True paths
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_strict_true_aborts_on_unvalidated() -> None:
    """strict=True must abort on the first unvalidated period."""
    with pytest.raises(pulso.DataNotValidatedError):
        pulso.load(
            year=range(2007, 2025),
            month=6,
            module="ocupados",
            strict=True,
            show_progress=False,
        )


@pytest.mark.integration
def test_strict_true_validated_only_succeeds() -> None:
    """strict=True with a single validated period must succeed."""
    df = pulso.load(
        year=2024,
        month=6,
        module="ocupados",
        strict=True,
        show_progress=False,
    )
    assert len(df) > 0
