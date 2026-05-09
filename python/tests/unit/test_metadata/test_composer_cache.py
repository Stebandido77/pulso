"""Tests for the composer's codebook caching (Fix 5).

The codebook is ~6.7 MB; multi-period loads must not re-read it from
disk on every call. This test verifies the existing module-level cache
in ``pulso.metadata.composer._load_codebook`` returns the SAME object
identity on repeated calls, and that subsequent calls are essentially
free (sub-millisecond).
"""

from __future__ import annotations

import time

import pytest

from pulso.metadata import composer


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    """Force a cold load at the start of each test, but don't blow it
    away mid-test — that's the whole point of the cache!"""
    composer._reset_caches_for_tests()
    yield
    composer._reset_caches_for_tests()


def test_load_codebook_returns_same_object_on_repeated_calls() -> None:
    """``_load_codebook`` is cached at module level; calling it twice
    must return the SAME dict instance, not a fresh deserialisation."""
    first = composer._load_codebook()
    second = composer._load_codebook()
    assert first is second, "Codebook cache must return identical object across calls"


def test_load_codebook_first_call_is_slower_than_subsequent() -> None:
    """The first call deserialises ~6.7 MB of JSON; subsequent calls
    should be sub-millisecond. We require at least an order of
    magnitude difference rather than a hard threshold to keep the
    test resilient against fast/slow CI hardware.
    """
    # Cold call.
    t0 = time.perf_counter()
    _ = composer._load_codebook()
    cold_dt = time.perf_counter() - t0

    # Hot calls — pick the median of several runs to avoid GC noise.
    hot_times: list[float] = []
    for _ in range(50):
        t = time.perf_counter()
        _ = composer._load_codebook()
        hot_times.append(time.perf_counter() - t)
    hot_times.sort()
    hot_median = hot_times[len(hot_times) // 2]

    # Cache hit must be at least 10x faster than the cold load.
    assert hot_median * 10 < cold_dt, (
        f"Cache appears ineffective: cold={cold_dt:.4f}s, hot_median={hot_median:.6f}s"
    )
    # And in absolute terms the hot call should be well under a millisecond.
    assert hot_median < 0.001, f"Hot codebook lookup unexpectedly slow: {hot_median:.6f}s"


def test_compose_dataframe_metadata_does_not_rebuild_codebook() -> None:
    """Calling the dataframe-level helper many times must not deserialise
    the codebook each time. We assert by reference identity again, this
    time threading through ``compose_column_metadata``."""
    import pandas as pd

    df = pd.DataFrame({"sexo": [1], "P6020": [1]})

    # Trigger first compose to warm the caches.
    composer.compose_dataframe_metadata(df, year=2024, month=6, module="ocupados")
    cb_after_first = composer._load_codebook()

    # 99 more calls.
    for _ in range(99):
        composer.compose_dataframe_metadata(df, year=2024, month=6, module="ocupados")

    cb_after_hundred = composer._load_codebook()
    assert cb_after_first is cb_after_hundred
