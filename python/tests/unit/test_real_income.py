"""IPC, minimum wage and deflation (W6, #89). Offline except where mocked."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

import pulso
from pulso._core import real_income as ri


def test_ipc_fixture_is_monthly_with_base_dec_2018() -> None:
    t = pulso.ipc(use_fixture=True)
    assert t["periodo"].iloc[0] == "2003-01"
    assert t["periodo"].iloc[-1] == "2026-10"
    assert len(t) == 286
    assert t.loc[t.periodo == "2018-12", "indice"].item() == 100.0
    assert t["periodo"].is_monotonic_increasing


def test_ipc_falls_back_with_warning(mocker: Any) -> None:
    mocker.patch("requests.get", side_effect=OSError("down"))
    with pytest.warns(UserWarning, match="bundled snapshot"):
        t = pulso.ipc()
    assert t["periodo"].iloc[-1] == "2026-10"
    with pytest.raises(OSError, match="down"):
        pulso.ipc(use_fixture=False)


def test_ipc_live_parses_the_linked_annex(mocker: Any) -> None:
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Total, índice"])
    ws.append(["Mes", 2025, 2026])
    for mes in ["Enero", "Febrero"]:
        ws.append([mes, 150.0, 160.0])
    buf = io.BytesIO()
    wb.save(buf)
    page = MagicMock(
        text='<a href="/files/operaciones/IPC/feb2026/anex-IPC-Indices-feb2026.xlsx">x</a>'
    )
    xlsx = MagicMock(content=buf.getvalue())
    get = mocker.patch("requests.get", side_effect=[page, xlsx])
    t = pulso.ipc(use_fixture=False)
    assert t["periodo"].tolist() == ["2025-01", "2025-02", "2026-01", "2026-02"]
    assert get.call_args_list[1].args[0].endswith("anex-IPC-Indices-feb2026.xlsx")


def test_salario_minimo_table() -> None:
    t = pulso.salario_minimo()
    assert t["anio"].tolist() == list(range(2007, 2027))
    assert t.loc[t.anio == 2026, "smmlv"].item() == 1750905
    assert t.loc[t.anio == 2011, "smmlv"].item() == 535600  # Decreto 33 de 2011
    assert t["fuente"].str.startswith("https://").all()


def test_deflactar() -> None:
    table = pulso.ipc(use_fixture=True)
    df = pd.DataFrame({"periodo": ["2018-12", "2026-09"], "x": [1000.0, "1000"]})
    out = pulso.deflactar(df, ["x"], "2026-09", ipc_table=table)
    assert out["x_real"].tolist() == pytest.approx([1610.0, 1000.0])
    with pytest.raises(KeyError, match="deflate_to"):
        pulso.deflactar(df, ["x"], "2030-01", ipc_table=table)
    with pytest.raises(KeyError, match="No IPC"):
        pulso.deflactar(
            pd.DataFrame({"periodo": ["1999-01"], "x": [1]}), ["x"], "2026-09", ipc_table=table
        )


def test_load_range_deflate_to(monkeypatch: pytest.MonkeyPatch) -> None:
    import pulso._core.loader as loader_mod

    def fake_load(year: int, month: Any, **kwargs: Any) -> pd.DataFrame:
        return pd.DataFrame({"INGLABO": [1000.0]})

    monkeypatch.setattr(loader_mod, "load", fake_load)
    monkeypatch.setattr(ri, "ipc", lambda use_fixture=None: ri._ipc_from_fixture())
    df = pulso.load_range("2018-12", "2018-12", "ocupados", harmonize=False, deflate_to="2026-09")
    assert df["INGLABO_real"].tolist() == pytest.approx([1610.0])
