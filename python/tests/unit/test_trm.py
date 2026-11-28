"""pulso.trm(): TRM from the Superfinanciera (W7, #90). Offline except one live test."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pulso._core.trm import _expand_daily, _trm_from_fixture


def test_expand_daily_covers_the_validity_window() -> None:
    windows = pd.DataFrame(
        {
            "vigenciadesde": ["2026-11-26T00:00:00.000", "2026-11-28T00:00:00.000"],
            "vigenciahasta": ["2026-11-27T00:00:00.000", "2026-11-30T00:00:00.000"],
            "valor": ["3630.89", "3498.46"],
        }
    )
    df = _expand_daily(windows)
    assert df["fecha"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-11-26",
        "2026-11-27",
        "2026-11-28",
        "2026-11-29",
        "2026-11-30",
    ]
    assert df["valor"].tolist() == [3630.89, 3630.89, 3498.46, 3498.46, 3498.46]
    assert set(df["serie"]) == {"trm"}


def test_fixture_is_daily_and_filtered() -> None:
    import datetime as dt

    df = _trm_from_fixture(dt.date(2007, 1, 1), dt.date(2007, 1, 3))
    assert df["valor"].tolist() == [2238.79, 2238.79, 2231.42]
    full = _trm_from_fixture()
    assert full["fecha"].is_monotonic_increasing
    assert not full["fecha"].duplicated().any()
    assert full["fecha"].max() == pd.Timestamp("2026-11-30")


def test_trm_use_fixture_warns() -> None:
    import pulso

    with pytest.warns(UserWarning, match="bundled TRM snapshot"):
        df = pulso.trm("2026-11-28", "2026-11-30", use_fixture=True)
    assert df["valor"].tolist() == [3498.46] * 3


def test_trm_api_is_parsed_and_falls_back(monkeypatch: pytest.MonkeyPatch, mocker: Any) -> None:
    import pulso

    payload = [
        {
            "vigenciadesde": "2026-11-28T00:00:00.000",
            "vigenciahasta": "2026-11-30T00:00:00.000",
            "valor": "3498.46",
        }
    ]
    resp = MagicMock()
    resp.text = json.dumps(payload)
    resp.raise_for_status = MagicMock()
    get = mocker.patch("requests.get", return_value=resp)
    df = pulso.trm("2026-11-29", "2026-11-30", use_fixture=False)
    assert df["valor"].tolist() == [3498.46, 3498.46]
    params = get.call_args.kwargs["params"]
    assert "vigenciahasta >= '2026-11-29T00:00:00'" in params["$where"]

    mocker.patch("requests.get", side_effect=OSError("network down"))
    with pytest.warns(UserWarning, match="Falling back to bundled snapshot"):
        fb = pulso.trm("2026-11-29", "2026-11-30")
    assert fb["valor"].tolist() == [3498.46, 3498.46]
    with pytest.raises(OSError, match="network down"):
        pulso.trm("2026-11-29", "2026-11-30", use_fixture=False)


def test_trm_rejects_inverted_range() -> None:
    import pulso

    with pytest.raises(ValueError, match="must be <="):
        pulso.trm("2026-11-30", "2026-11-01", use_fixture=True)
