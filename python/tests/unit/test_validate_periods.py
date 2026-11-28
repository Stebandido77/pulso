"""Unit tests for python/scripts/validate_periods.py (synthetic microdata, no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_periods import (  # noqa: E402
    HARMONIZED_VARIABLES,
    MappingGapError,
    classify_status,
    compare,
    compute_indicators,
    parse_period_range,
    read_results,
    write_results,
)

VARIABLE_MAP = Path(__file__).resolve().parents[3] / "data" / "variable_map.json"

# Ten persons in the PET with known weights, plus two children outside it:
#   6 employed      -> OC  = 100+200+150+50+300+200 = 1000
#   2 unemployed    -> DS  = 100+150               =  250
#   2 out of the FT -> FFT = 400+350               =  750
#   FT = 1250, PET = 2000  =>  TD = 20.0, TO = 50.0, TGP = 62.5 (exact)
OC_W = [100.0, 200.0, 150.0, 50.0, 300.0, 200.0]
DS_W = [100.0, 150.0]
FFT_W = [400.0, 350.0]
CHILD_W = [500.0, 500.0]


@pytest.fixture(scope="module")
def var_map() -> dict:
    return json.loads(VARIABLE_MAP.read_text(encoding="utf-8"))


def _merged(epoch_key: str, ages: list[int], clase: list[int], weights_as_text: bool = False):
    """A load_merged-like frame (Características generales + labor modules)."""
    n_pet = 10
    df = pd.DataFrame(
        {
            "DIRECTORIO": range(1, 13),
            "SECUENCIA_P": 1,
            "ORDEN": 1,
            "P6040": ages,
            "CLASE": clase,
        }
    )
    w = OC_W + DS_W + FFT_W + CHILD_W
    wcol = "FEX_C18" if epoch_key == "geih_2021_present" else "FEX_C"
    df[wcol] = [str(v).replace(".", ",") for v in w] if weights_as_text else w
    df["OCI"] = [1] * 6 + [np.nan] * 6
    df["DSI"] = [np.nan] * 6 + [1, 1] + [np.nan] * 4
    out_col = "FFT" if epoch_key == "geih_2021_present" else "INI"
    df[out_col] = [np.nan] * 8 + [1, 1] + [np.nan] * 2
    assert len(df) == n_pet + 2
    return df


def _harmonized(df: pd.DataFrame, epoch_key: str, period: str) -> pd.DataFrame:
    from pulso._config.epochs import get_epoch
    from pulso._core.harmonizer import harmonize_dataframe

    df.attrs["pulso_period"] = period
    return harmonize_dataframe(df, get_epoch(epoch_key), variables=HARMONIZED_VARIABLES)


def test_frame_2018_exact_rates_through_variable_map() -> None:
    ages = [30] * 10 + [14, 8]
    df = _harmonized(_merged("geih_2021_present", ages, [1] * 12), "geih_2021_present", "2024-06")
    vals, notes = compute_indicators(df)
    assert vals["td"] == pytest.approx(20.0, abs=1e-12)
    assert vals["to"] == pytest.approx(50.0, abs=1e-12)
    assert vals["tgp"] == pytest.approx(62.5, abs=1e-12)
    assert (vals["pet"], vals["ft"], vals["oc"], vals["ds"]) == (2000.0, 1250.0, 1000.0, 250.0)
    assert notes == ["definiciones=variable_map(pet, fuerza_trabajo, condicion_actividad)"]


def test_frame_2005_pet_is_12_urban_10_rural() -> None:
    # Child 1: 11 years, urban -> outside PET. Child 2: 10 years, rural -> in PET
    # but in no labor module: a definition inconsistency that must be reported.
    ages = [30] * 10 + [11, 10]
    clase = [1] * 10 + [1, 2]
    df = _harmonized(_merged("geih_2006_2020", ages, clase), "geih_2006_2020", "2015-06")
    assert df["pet"].tolist() == [True] * 10 + [False, True]
    vals, notes = compute_indicators(df)
    assert vals["pet"] == 2500.0
    assert "1 personas de la PET sin condicion_actividad" in notes


def test_2020_uses_the_2018_frame_threshold() -> None:
    # 2020 microdata are retro-projected to the 2018 frame: PET is 15+ there.
    ages = [30] * 10 + [14, 12]
    df = _harmonized(_merged("geih_2006_2020", ages, [1] * 12), "geih_2006_2020", "2020-06")
    assert df["pet"].tolist() == [True] * 10 + [False, False]
    vals, notes = compute_indicators(df)
    assert vals["tgp"] == pytest.approx(62.5, abs=1e-12)
    assert notes == ["definiciones=variable_map(pet, fuerza_trabajo, condicion_actividad)"]
    df19 = _harmonized(_merged("geih_2006_2020", ages, [1] * 12), "geih_2006_2020", "2019-12")
    assert df19["pet"].tolist() == [True] * 12


def test_text_weights_with_decimal_comma_are_coerced() -> None:
    ages = [30] * 10 + [14, 8]
    raw = _merged("geih_2021_present", ages, [1] * 12, weights_as_text=True)
    vals, notes = compute_indicators(_harmonized(raw, "geih_2021_present", "2024-06"))
    assert vals["td"] == pytest.approx(20.0)
    assert any(n.startswith("weight_coerced_from_text (") for n in notes)


def test_missing_canonical_variable_is_a_mapping_gap() -> None:
    ages = [30] * 10 + [14, 8]
    raw = _merged("geih_2021_present", ages, [1] * 12).drop(columns=["FFT"])
    df = _harmonized(raw, "geih_2021_present", "2024-06")
    with pytest.raises(MappingGapError, match="fuerza_trabajo"):
        compute_indicators(df)


@pytest.mark.parametrize(
    ("diff", "expected"),
    [
        (None, "pending"),
        (0.0, "pass"),
        (0.1, "pass"),
        (0.1001, "review"),
        (0.5, "review"),
        (0.5001, "fail"),
        (3.0, "fail"),
    ],
)
def test_classify_status_thresholds(diff: float | None, expected: str) -> None:
    assert classify_status(diff) == expected


def test_compare_reports_max_abs_diff_and_signed_note() -> None:
    row = compare(
        {"td": 20.0, "to": 50.0, "tgp": 62.5},
        {"td": 20.05, "to": 50.0, "tgp": 62.2},
    )
    assert row["max_abs_diff_pp"] == pytest.approx(0.3)
    assert row["status"] == "review"
    assert row["_diff_note"] == "diff_pp TD=-0.050 TO=+0.000 TGP=+0.300"


def test_compare_without_reference_is_pending() -> None:
    row = compare({"td": 20.0, "to": 50.0, "tgp": 62.5}, None)
    assert row["status"] == "pending"
    assert row["td_dane"] is None


def test_parse_period_range() -> None:
    avail = ["2023-12", "2024-01", "2024-02", "2026-09"]
    assert parse_period_range("2024-01:2026-09", avail) == ["2024-01", "2024-02", "2026-09"]
    assert parse_period_range("2024-02", avail) == ["2024-02"]
    assert parse_period_range(":2023-12", avail) == ["2023-12"]
    assert parse_period_range(None, avail) == sorted(avail)


def test_results_roundtrip_is_sorted_and_resumable(tmp_path: Path) -> None:
    out = tmp_path / "results.csv"
    rows = {
        "2024-02": {"period": "2024-02", "status": "pass", "max_abs_diff_pp": 1e-6},
        "2024-01": {"period": "2024-01", "status": "error", "notes": "boom"},
    }
    write_results(rows, out)
    text = out.read_text(encoding="utf-8").splitlines()
    assert text[0].startswith("period,td_pulso,td_dane")
    assert text[1].startswith("2024-01,")
    assert "0.000001" in text[2]  # fixed-point, never scientific notation
    back = read_results(out)
    assert back["2024-02"]["status"] == "pass"
