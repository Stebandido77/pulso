"""PET, FT and condicion_actividad from DANE's own flags (#79)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pulso._config.epochs import get_epoch
from pulso._core.harmonizer_funcs import (
    labor_force_from_flags,
    labor_status_from_flags,
    merge_labor_status,
    pet_by_age_zone,
)
from pulso._utils.exceptions import ConfigError, HarmonizationError

FLAGS = pd.DataFrame(
    {
        "OCI": [1, np.nan, np.nan, np.nan],
        "DSI": [np.nan, 1, np.nan, 0],
        "INI": [np.nan, np.nan, 1, np.nan],
    }
)


def test_labor_status_from_flags() -> None:
    out = labor_status_from_flags(FLAGS, ["OCI", "DSI", "INI"], {}, None)
    assert out.tolist() == ["1", "2", "3", pd.NA]


def test_labor_force_from_flags() -> None:
    out = labor_force_from_flags(FLAGS, ["OCI", "DSI", "INI"], {}, None)
    assert out.tolist() == [True, True, False, pd.NA]


def test_flag_functions_require_three_columns() -> None:
    with pytest.raises(ConfigError):
        labor_status_from_flags(FLAGS, ["OCI", "DSI"], {}, None)
    with pytest.raises(HarmonizationError, match="FFT"):
        labor_status_from_flags(FLAGS, ["OCI", "DSI", "FFT"], {}, None)


def test_merge_labor_status_uses_fft_when_present() -> None:
    df = pd.DataFrame(
        {
            "OCI": [1, np.nan, np.nan, np.nan],
            "DSI": [np.nan, 1, np.nan, np.nan],
            "FFT": [np.nan, np.nan, 1, np.nan],  # last row: child, in no module
        }
    )
    assert merge_labor_status(df, ["OCI", "DSI"], {}, None).tolist() == ["1", "2", "3", pd.NA]
    # Without FFT the old heuristic stays (the child is coded inactive).
    legacy = merge_labor_status(df.drop(columns="FFT"), ["OCI", "DSI"], {}, None)
    assert legacy.tolist() == ["1", "2", "3", "3"]


def _entry(params: dict, epoch_key: str) -> dict:
    return {
        "mappings": {
            epoch_key: {
                "source_variable": ["P6040", "CLASE"],
                "transform": {"op": "custom", "name": "pet_by_age_zone", "params": params},
            }
        }
    }


FRAME_2005 = {
    "min_age_urban": 12,
    "min_age_rural": 10,
    "frame_2018_periods": [["2020-01", "2020-12"]],
    "frame_2018_min_age": 15,
}


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        ("2015-06", [False, True, False, True, True, pd.NA]),
        ("2020-06", [False, False, False, False, True, pd.NA]),
        (None, [False, True, False, True, True, pd.NA]),
    ],
)
def test_pet_by_age_zone_frame_2005(period: str | None, expected: list) -> None:
    df = pd.DataFrame(
        {
            "P6040": [11, 12, 9, 10, 15, np.nan],
            "CLASE": [1, 1, 2, 3, 1, 1],
        }
    )
    if period is not None:
        df.attrs["pulso_period"] = period
    epoch = get_epoch("geih_2006_2020")
    out = pet_by_age_zone(df, ["P6040", "CLASE"], _entry(FRAME_2005, epoch.key), epoch)
    assert out.tolist() == expected


def test_pet_by_age_zone_frame_2018_ignores_zone() -> None:
    df = pd.DataFrame({"P6040": [14, 15, 14, 15], "CLASE": [1, 1, 2, np.nan]})
    epoch = get_epoch("geih_2021_present")
    params = {"min_age_urban": 15, "min_age_rural": 15}
    out = pet_by_age_zone(df, ["P6040", "CLASE"], _entry(params, epoch.key), epoch)
    assert out.tolist() == [False, True, False, True]
