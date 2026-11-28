"""pulso.load_range() and pooled weights (W4, #87). Offline: pulso.load is stubbed."""

from __future__ import annotations

import warnings
from typing import Any

import pandas as pd
import pytest

from pulso._core.range import period_range, sampling_frame


def test_period_range_crosses_years() -> None:
    assert period_range("2021-11", "2022-02") == [(2021, 11), (2021, 12), (2022, 1), (2022, 2)]
    assert period_range("2026-09", "2026-09") == [(2026, 9)]


@pytest.mark.parametrize(
    ("start", "end"), [("2026-10", "2026-09"), ("2026-13", "2026-12"), ("26-1", "2026-02")]
)
def test_period_range_rejects_bad_input(start: str, end: str) -> None:
    with pytest.raises(ValueError, match=r"YYYY-MM|after"):
        period_range(start, end)


@pytest.mark.parametrize(
    ("y", "m", "frame"),
    [
        (2019, 12, "2005"),
        (2020, 1, "2018"),
        (2020, 12, "2018"),
        (2021, 12, "2005"),
        (2022, 1, "2018"),
    ],
)
def test_sampling_frame(y: int, m: int, frame: str) -> None:
    assert sampling_frame(y, m) == frame


@pytest.fixture
def stub_load(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, Any]]:
    """pulso.load returning 2 rows per month with FEX_C18 = 30 (2018-frame layout)."""
    import pulso._core.loader as loader_mod

    calls: list[tuple[int, Any]] = []

    def fake_load(year: int, month: Any, **kwargs: Any) -> pd.DataFrame:
        months = list(month) if not isinstance(month, int) else [month]
        calls.append((year, months))
        frames = [
            pd.DataFrame(
                {"DIRECTORIO": [1, 2], "FEX_C18": [30.0, 30.0], "FEX_C": [30.0, 30.0]}
            ).assign(year=year, month=mo)
            for mo in months
        ]
        df = pd.concat(frames, ignore_index=True)
        return df if len(months) > 1 else df.drop(columns=["year", "month"])

    monkeypatch.setattr(loader_mod, "load", fake_load)
    return calls


def test_load_range_stacks_months_with_periodo(stub_load: list[tuple[int, Any]]) -> None:
    import pulso

    with warnings.catch_warnings():
        warnings.simplefilter("error")  # no frame warning inside 2026
        df = pulso.load_range("2026-07", "2026-09", "ocupados", harmonize=False)
    assert df["periodo"].tolist() == ["2026-07"] * 2 + ["2026-08"] * 2 + ["2026-09"] * 2
    assert list(df.columns[:1]) == ["periodo"]
    assert stub_load == [(2026, [7, 8, 9])]


def test_average_weights_divide_by_the_months_pooled(stub_load: list[tuple[int, Any]]) -> None:
    import pulso

    df = pulso.load_range("2026-07", "2026-09", "ocupados", harmonize=False, average_weights=True)
    assert df["peso_expansion_promedio"].tolist() == [10.0] * 6
    # Pooled total = average of the monthly totals (DANE moving-quarter levels).
    assert df["peso_expansion_promedio"].sum() == pytest.approx(60.0)


def test_single_month_gets_year_month(stub_load: list[tuple[int, Any]]) -> None:
    import pulso

    df = pulso.load_range("2026-09", "2026-09", "ocupados", harmonize=False)
    assert set(df["periodo"]) == {"2026-09"}
    assert df["year"].tolist() == [2026, 2026]


def test_range_across_frames_warns(stub_load: list[tuple[int, Any]]) -> None:
    import pulso

    with pytest.warns(UserWarning, match="2005 and 2018 census frames"):
        df = pulso.load_range("2021-12", "2022-01", "ocupados", harmonize=False)
    assert stub_load == [(2021, [12]), (2022, [1])]
    assert df["periodo"].tolist() == ["2021-12"] * 2 + ["2022-01"] * 2
