"""Unit tests for pulso._core.harmonizer_funcs."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from pulso._core.harmonizer_funcs import (
    bin_edad_quinquenal,
    compute_ingreso_total,
    get_custom,
    merge_labor_status,
)
from pulso._utils.exceptions import ConfigError, HarmonizationError


def _epoch() -> MagicMock:
    e = MagicMock()
    e.key = "geih_2021_present"
    return e


# ---------------------------------------------------------------------------
# bin_edad_quinquenal
# ---------------------------------------------------------------------------


def test_bin_edad_quinquenal_correct_bins() -> None:
    df = pd.DataFrame({"P6040": [0, 4, 5, 14, 15, 24, 64, 65, 99]})
    result = bin_edad_quinquenal(df, "P6040", {}, _epoch())
    assert result.iloc[0] == "0-4"
    assert result.iloc[1] == "0-4"
    assert result.iloc[2] == "5-9"
    assert result.iloc[3] == "10-14"
    assert result.iloc[4] == "15-19"
    assert result.iloc[5] == "20-24"
    assert result.iloc[6] == "60-64"
    assert result.iloc[7] == "65+"
    assert result.iloc[8] == "65+"


def test_bin_edad_quinquenal_handles_nulls() -> None:
    df = pd.DataFrame({"P6040": pd.array([25, None, 40], dtype="Int64")})
    result = bin_edad_quinquenal(df, "P6040", {}, _epoch())
    assert result.iloc[0] == "25-29"
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == "40-44"


# ---------------------------------------------------------------------------
# merge_labor_status
# ---------------------------------------------------------------------------


def test_merge_labor_status_three_categories() -> None:
    """OCI=1 → ocupado, DSI=1 → desocupado, both NA → inactivo."""
    df = pd.DataFrame(
        {
            "OCI": pd.array([1, None, None], dtype="Int64"),
            "DSI": pd.array([None, 1, None], dtype="Int64"),
        }
    )
    result = merge_labor_status(df, ["OCI", "DSI"], {}, _epoch())
    assert result.iloc[0] == "1"
    assert result.iloc[1] == "2"
    assert result.iloc[2] == "3"


def test_merge_labor_status_raises_when_columns_missing() -> None:
    df = pd.DataFrame({"OCI": [1, None]})
    with pytest.raises(HarmonizationError, match="not found in DataFrame"):
        merge_labor_status(df, ["OCI", "DSI"], {}, _epoch())


def test_merge_labor_status_raises_on_non_list_source() -> None:
    df = pd.DataFrame({"OCI": [1]})
    with pytest.raises(ConfigError, match="requires source_variable as a list"):
        merge_labor_status(df, "OCI", {}, _epoch())


# ---------------------------------------------------------------------------
# compute_ingreso_total
# ---------------------------------------------------------------------------


def test_compute_ingreso_total_sums_components() -> None:
    df = pd.DataFrame(
        {
            "INGLABO": [1_000_000, 2_000_000],
            "P7500S1A1": [100_000, 200_000],
            "P7500S2A1": [50_000, 0],
        }
    )
    cols = ["INGLABO", "P7500S1A1", "P7500S2A1"]
    result = compute_ingreso_total(df, cols, {}, _epoch())
    assert result.iloc[0] == pytest.approx(1_150_000)
    assert result.iloc[1] == pytest.approx(2_200_000)


def test_compute_ingreso_total_handles_partial_columns() -> None:
    """When only some declared columns exist, sums those; does not raise."""
    df = pd.DataFrame(
        {
            "INGLABO": [500_000, 1_000_000],
        }
    )
    cols = ["INGLABO", "P7500S1A1", "P750S1A1"]
    result = compute_ingreso_total(df, cols, {}, _epoch())
    assert result.iloc[0] == pytest.approx(500_000)
    assert result.iloc[1] == pytest.approx(1_000_000)


def test_compute_ingreso_total_raises_when_no_columns_available() -> None:
    df = pd.DataFrame({"OTHER": [1, 2]})
    with pytest.raises(HarmonizationError, match="none of the declared source columns"):
        compute_ingreso_total(df, ["INGLABO", "P7500S1A1"], {}, _epoch())


def test_get_custom_raises_on_unknown() -> None:
    with pytest.raises(ConfigError, match="not registered"):
        get_custom("nonexistent_fn_xyz")
