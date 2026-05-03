"""Integration tests parameterised over every validated month (Commit 11, G-8).

These exercise the full ``pulso.load`` and ``pulso.load_merged`` pipelines
end-to-end against real DANE data. Skipped by default (run with
``pytest --run-integration``).

The list of validated months is read from ``sources.json`` so the test set
stays in sync with the registry — when a new month is validated, it
automatically becomes part of this matrix.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

_SOURCES_PATH = Path(__file__).parent.parent.parent / "pulso" / "data" / "sources.json"


def _validated_months() -> list[tuple[int, int]]:
    sources = json.loads(_SOURCES_PATH.read_text(encoding="utf-8"))
    return sorted(
        (int(k[:4]), int(k[5:7])) for k, v in sources["data"].items() if v.get("validated")
    )


VALIDATED_MONTHS = _validated_months()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("year", "month"),
    VALIDATED_MONTHS,
    ids=[f"{y}-{m:02d}" for y, m in VALIDATED_MONTHS],
)
def test_load_works_for_validated_month(year: int, month: int) -> None:
    """G-8: every validated month must load via pulso.load() without errors."""
    import pulso

    df = pulso.load(year=year, month=month, module="ocupados", show_progress=False)
    assert len(df) > 0
    assert "FEX_C" in df.columns
    assert df["FEX_C"].sum() > 0


@pytest.mark.integration
@pytest.mark.parametrize(
    ("year", "month"),
    VALIDATED_MONTHS,
    ids=[f"{y}-{m:02d}" for y, m in VALIDATED_MONTHS],
)
def test_load_merged_works_for_validated_month(year: int, month: int) -> None:
    """G-8: load_merged must succeed for every validated month."""
    import pulso

    df = pulso.load_merged(year=year, month=month, modules=["ocupados"], show_progress=False)
    assert len(df) > 0


@pytest.mark.integration
def test_load_range_validated_only() -> None:
    """range(2018, 2025) with month=6 — covers a mix of validated and not."""
    import pulso

    with warnings.catch_warnings():
        # Multi-period mixed validation status will emit one aggregated warning.
        warnings.simplefilter("ignore", UserWarning)
        df = pulso.load(year=range(2018, 2025), month=6, module="ocupados", show_progress=False)
    assert len(df) > 0
    assert "year" in df.columns
    assert "month" in df.columns


@pytest.mark.integration
def test_load_range_full_history_with_strict_false() -> None:
    """The case the user reported that triggered this whole audit:
    pulso.load(year=range(2007, 2025), month=6, module='ocupados').

    Default strict=False must:
    - return a non-empty DataFrame,
    - emit exactly ONE aggregated UserWarning (not N),
    - mention the unvalidated count in that single warning.
    """
    import pulso

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=range(2007, 2025),
            month=6,
            module="ocupados",
            strict=False,
            show_progress=False,
        )

    assert len(df) > 0
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1, (
        f"Expected exactly 1 aggregated UserWarning, got {len(user_warnings)}: "
        f"{[str(w.message) for w in user_warnings]}"
    )
    msg = str(user_warnings[0].message)
    assert "checksum-validated" in msg or "failed to load" in msg
