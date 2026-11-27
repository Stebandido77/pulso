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
    MappingGapError,
    classify_status,
    compare,
    compute_indicators,
    parse_period_range,
    read_results,
    write_results,
)

VARIABLE_MAP = Path(__file__).resolve().parents[3] / "data" / "variable_map.json"
KEYS = ("DIRECTORIO", "SECUENCIA_P", "ORDEN")

# Ten persons with known weights:
#   6 employed      -> OC  = 100+200+150+50+300+200 = 1000
#   2 unemployed    -> DS  = 100+150               =  250
#   2 out of the FT -> FFT = 400+350               =  750
#   FT = 1250, PET = 2000  =>  TD = 20.0, TO = 50.0, TGP = 62.5 (exact)
OC_W = [100.0, 200.0, 150.0, 50.0, 300.0, 200.0]
DS_W = [100.0, 150.0]
FFT_W = [400.0, 350.0]


@pytest.fixture(scope="module")
def var_map() -> dict:
    return json.loads(VARIABLE_MAP.read_text(encoding="utf-8"))


def _keys(start: int, n: int) -> dict[str, list[int]]:
    return {
        "DIRECTORIO": list(range(start, start + n)),
        "SECUENCIA_P": [1] * n,
        "ORDEN": [1] * n,
    }


def _redesign_frames(weights_as_text: bool = False) -> dict[str, pd.DataFrame]:
    """geih_2021_present layout: Ocupados.csv + one shared 'No ocupados.csv'."""

    def w(vals: list[float]) -> list[float] | list[str]:
        return [str(v).replace(".", ",") for v in vals] if weights_as_text else vals

    ocupados = pd.DataFrame({**_keys(1, 6), "OCI": [1] * 6, "FEX_C18": w(OC_W)})
    no_ocupados = pd.DataFrame(
        {
            **_keys(7, 4),
            "DSI": [1, 1, np.nan, np.nan],
            "FEX_C18": w(DS_W + FFT_W),
        }
    )
    return {"ocupados": ocupados, "desocupados": no_ocupados, "inactivos": no_ocupados}


def _frame_2005_frames() -> dict[str, pd.DataFrame]:
    """geih_2006_2020 layout: separate Ocupados / Desocupados / Inactivos files."""
    return {
        "ocupados": pd.DataFrame({**_keys(1, 6), "OCI": [1] * 6, "FEX_C": OC_W}),
        "desocupados": pd.DataFrame({**_keys(7, 2), "DSI": [1, 1], "FEX_C": DS_W}),
        "inactivos": pd.DataFrame({**_keys(9, 2), "INI": [1, 1], "FEX_C": FFT_W}),
    }


def test_redesign_epoch_exact_rates(var_map: dict) -> None:
    vals, notes = compute_indicators(
        _redesign_frames(), "geih_2021_present", var_map, KEYS, shared_file=True
    )
    assert vals["td"] == pytest.approx(20.0, abs=1e-12)
    assert vals["to"] == pytest.approx(50.0, abs=1e-12)
    assert vals["tgp"] == pytest.approx(62.5, abs=1e-12)
    assert (vals["oc"], vals["ds"], vals["fft"]) == (1000.0, 250.0, 750.0)
    assert any("merge_labor_status(OCI,DSI)" in n for n in notes)
    assert "weight=FEX_C18" in notes


def test_frame_2005_epoch_uses_module_membership_and_reports_gap(var_map: dict) -> None:
    vals, notes = compute_indicators(
        _frame_2005_frames(), "geih_2006_2020", var_map, KEYS, shared_file=False
    )
    assert vals["td"] == pytest.approx(20.0, abs=1e-12)
    assert vals["to"] == pytest.approx(50.0, abs=1e-12)
    assert vals["tgp"] == pytest.approx(62.5, abs=1e-12)
    assert any(n.startswith("labor_status=module_membership (gap:") for n in notes)
    assert any("variable_map no define PET/FT" in n for n in notes)
    assert "weight=FEX_C" in notes


def test_text_weights_with_decimal_comma_are_coerced(var_map: dict) -> None:
    vals, notes = compute_indicators(
        _redesign_frames(weights_as_text=True),
        "geih_2021_present",
        var_map,
        KEYS,
        shared_file=True,
    )
    assert vals["td"] == pytest.approx(20.0)
    assert any(n.startswith("weight_coerced_from_text (ocupados:") for n in notes)


def test_missing_weight_column_is_a_mapping_gap(var_map: dict) -> None:
    frames = _redesign_frames()
    frames["ocupados"] = frames["ocupados"].rename(columns={"FEX_C18": "FEX_X"})
    with pytest.raises(MappingGapError, match="FEX_C18"):
        compute_indicators(frames, "geih_2021_present", var_map, KEYS, shared_file=True)


def test_identity_mapping_cannot_split_a_shared_file(var_map: dict) -> None:
    frames = {m: f.rename(columns={"FEX_C18": "FEX_C"}) for m, f in _redesign_frames().items()}
    with pytest.raises(MappingGapError, match="shared"):
        compute_indicators(frames, "geih_2006_2020", var_map, KEYS, shared_file=True)


def test_duplicate_person_across_modules_is_noted(var_map: dict) -> None:
    frames = _frame_2005_frames()
    frames["inactivos"].loc[0, "DIRECTORIO"] = 1  # same person as first employed
    _, notes = compute_indicators(frames, "geih_2006_2020", var_map, KEYS, shared_file=False)
    assert "1 personas repetidas entre modulos" in notes


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
