"""pulso.indicadores() (W5, #88). Offline: the monthly loader is stubbed."""

from __future__ import annotations

import pandas as pd
import pytest

import pulso._core.indicadores as ind


def _month(oc_w: float, ds_w: float, fft_w: float, child_w: float = 50.0) -> pd.DataFrame:
    """4 persons: employed, unemployed, inactive, child outside the PET (AREA 11, CLASE 1)."""
    return pd.DataFrame(
        {
            "pet": [True, True, True, False],
            "fuerza_trabajo": pd.array([True, True, False, pd.NA], dtype="boolean"),
            "condicion_actividad": pd.array(["1", "2", "3", pd.NA], dtype="string"),
            "peso_expansion": [oc_w, ds_w, fft_w, child_w],
            "CLASE": [1, 1, 2, 1],
            "AREA": [11, 5, 99, 11],
            "DPTO": [11, 5, 99, 11],
        }
    )


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> dict[tuple[int, int], pd.DataFrame]:
    data = {
        (2026, 7): _month(80, 20, 100),
        (2026, 8): _month(70, 30, 100),
        (2026, 9): _month(90, 10, 100),
    }

    def fake(year: int, month: int, strict: object, cache: object) -> pd.DataFrame:
        if (year, month) not in data:
            raise RuntimeError(f"{year}-{month:02d}: not published")
        return data[(year, month)].copy()

    monkeypatch.setattr(ind, "_load_month", fake)
    return data


def test_monthly_national_rates(stub: dict) -> None:
    out = ind.indicadores("2026-09")
    r = out.iloc[0]
    assert (r.periodo, r.meses, r.dominio, r.grupo) == ("2026-09", 1, "nacional", "total")
    assert (r.pet, r.ft, r.oc, r.ds) == (200.0, 100.0, 90.0, 10.0)
    assert r.td == pytest.approx(10.0)
    assert r.to == pytest.approx(45.0)
    assert r.tgp == pytest.approx(50.0)
    assert pd.isna(r.se)


def test_moving_quarter_averages_levels(stub: dict) -> None:
    r = ind.indicadores("2026-09", trimestre_movil=True).iloc[0]
    assert r.meses == 3
    # Levels are the average of the three months (factor / 3).
    assert r.oc == pytest.approx((80 + 70 + 90) / 3)
    assert r.ds == pytest.approx((20 + 30 + 10) / 3)
    assert r.td == pytest.approx(100 * 60 / 300)


def test_domains(stub: dict) -> None:
    cab = ind.indicadores("2026-09", dominio="cabeceras").iloc[0]
    assert (cab.oc, cab.ds, cab.pet) == (90.0, 10.0, 100.0)
    rural = ind.indicadores("2026-09", dominio="centros_poblados_rural").iloc[0]
    assert rural.pet == 100.0
    assert rural.ft == 0.0
    assert pd.isna(rural.td)
    cities = ind.indicadores("2026-09", dominio="ciudad")
    assert cities["grupo"].tolist() == ["05", "11", "99"]
    c13 = ind.indicadores("2026-09", dominio="13_ciudades").iloc[0]
    assert (c13.oc, c13.ds) == (90.0, 10.0)  # AREA 99 is not one of the 13 cities


def test_missing_month_is_skipped_with_warning(stub: dict) -> None:
    with pytest.warns(UserWarning, match="2026-06: not published"):
        out = ind.indicadores("2026-08", trimestre_movil=True)
    assert out.empty  # the Jun-Aug window lacks June


def test_bad_domain() -> None:
    with pytest.raises(ValueError, match="dominio"):
        ind.indicadores("2026-09", dominio="pais")


def test_frame_mix_warns(stub: dict) -> None:
    stub[(2021, 12)] = _month(80, 20, 100)
    stub[(2022, 1)] = _month(80, 20, 100)
    with pytest.warns(UserWarning, match="census frames"):
        out = ind.indicadores("2021-12", "2022-01")
    assert out["periodo"].tolist() == ["2021-12", "2022-01"]
