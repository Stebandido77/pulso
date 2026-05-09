"""Tests for the year/month iterable contract (Commit 13).

The runtime already accepted iterables in rc2 (validate_year_month
normalised via ``sorted(set(month))``), but the type hints were narrow
and edge cases (empty iterables, non-int iterables) were under-tested.

This file pins down:
- year and month each accept int, range, list, tuple, set, generator
- bool is rejected (it's an int subclass — sneaks through otherwise)
- str is rejected (pandas-style "2024" gets iterated char by char)
- empty iterables raise ValueError
- non-int iterables raise TypeError
- year x month is a cartesian product
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _make_full_grid_sources() -> dict[str, Any]:
    """Registry covering 2007-01 through 2026-12 with everything validated."""
    return {
        "metadata": {"schema_version": "1.0.0", "data_version": "2026.12"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Ocu",
                "description_en": "Ocu",
                "available_in": ["geih_2006_2020", "geih_2021_present"],
            }
        },
        "data": {
            f"{y}-{m:02d}": {
                "epoch": "geih_2021_present" if y >= 2022 else "geih_2006_2020",
                "download_url": f"https://example.com/{y}-{m:02d}.zip",
                "checksum_sha256": "a" * 64,
                "modules": {"ocupados": {"cabecera": f"{y}-{m:02d}.CSV"}},
                "validated": True,
            }
            for y in range(2007, 2027)
            for m in range(1, 13)
        },
    }


@pytest.fixture
def offline_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
):
    """Patch HTTP/parser/registry so any signature-valid call succeeds."""
    import pulso._config.registry as reg
    import pulso._core.downloader as dl_mod
    import pulso._core.parser as parser_mod

    monkeypatch.setattr(reg, "_SOURCES", _make_full_grid_sources())
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(dl_mod, "verify_checksum", lambda *a, **kw: True)

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"bytes"]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    sentinel = pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})
    monkeypatch.setattr(parser_mod, "parse_module", lambda *a, **kw: sentinel.copy())


# ── Iterable inputs accepted ───────────────────────────────────────────────


class TestMonthAsRange:
    def test_year_int_month_range(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        df = pulso.load(year=2024, month=range(1, 4), module="ocupados", harmonize=False)
        assert len(df) == 3
        assert sorted(df["month"].unique().tolist()) == [1, 2, 3]
        assert df["year"].unique().tolist() == [2024]

    def test_year_range_month_range_cartesian(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        df = pulso.load(
            year=range(2023, 2025),
            month=range(1, 4),
            module="ocupados",
            harmonize=False,
        )
        assert len(df) == 6  # 2 years x 3 months
        assert sorted(df["year"].unique().tolist()) == [2023, 2024]
        assert sorted(df["month"].unique().tolist()) == [1, 2, 3]

    def test_year_list_month_list(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        df = pulso.load(
            year=[2023, 2024],
            month=[6, 12],
            module="ocupados",
            harmonize=False,
        )
        assert len(df) == 4
        assert sorted(df["year"].unique().tolist()) == [2023, 2024]
        assert sorted(df["month"].unique().tolist()) == [6, 12]

    def test_month_tuple_accepted(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        df = pulso.load(year=2024, month=(1, 6, 12), module="ocupados", harmonize=False)
        assert len(df) == 3

    def test_month_set_accepted(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        df = pulso.load(year=2024, month={3, 6, 9}, module="ocupados", harmonize=False)
        assert len(df) == 3

    def test_month_range_full_year(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        df = pulso.load(year=2024, month=range(1, 13), module="ocupados", harmonize=False)
        assert len(df) == 12
        assert sorted(df["month"].unique().tolist()) == list(range(1, 13))


# ── Bad types rejected ─────────────────────────────────────────────────────


class TestRejectsBadTypes:
    def test_month_string_rejected(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(TypeError, match="month must be int, range"):
            pulso.load(year=2024, month="6", module="ocupados", harmonize=False)

    def test_year_string_rejected(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(TypeError, match="year must be int, range"):
            pulso.load(year="2024", month=6, module="ocupados", harmonize=False)

    def test_year_bool_rejected(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(TypeError, match="bool"):
            pulso.load(year=True, month=6, module="ocupados", harmonize=False)

    def test_month_bool_rejected(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(TypeError, match="bool"):
            pulso.load(year=2024, month=True, module="ocupados", harmonize=False)

    def test_month_iterable_of_garbage_rejected(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        """Iterables whose elements ``int()`` cannot coerce raise a clear TypeError.

        Note: numeric strings like ``["6", "12"]`` ARE accepted because
        ``int("6") == 6``. Only truly non-coercible elements fail.
        """
        import pulso

        with pytest.raises(TypeError, match="iterable of ints"):
            pulso.load(
                year=2024,
                month=[object(), object()],
                module="ocupados",
                harmonize=False,
            )


# ── Edge cases ─────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_year_range_rejected(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(ValueError, match="year cannot be empty"):
            pulso.load(year=range(2025, 2025), month=6, module="ocupados", harmonize=False)

    def test_empty_month_range_rejected(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(ValueError, match="month cannot be empty"):
            pulso.load(year=2024, month=range(6, 6), module="ocupados", harmonize=False)

    def test_empty_month_list_rejected(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(ValueError, match="month cannot be empty"):
            pulso.load(year=2024, month=[], module="ocupados", harmonize=False)

    def test_single_period_via_range_of_one(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        """range(2024, 2025) collapses to year=2024 internally; result equivalent."""
        import pulso

        df_range = pulso.load(year=range(2024, 2025), month=6, module="ocupados", harmonize=False)
        df_int = pulso.load(year=2024, month=6, module="ocupados", harmonize=False)
        # Same single row in both. (Range form is single-period so no
        # year/month columns are added — behaviour matches int form.)
        assert df_range.shape == df_int.shape

    def test_out_of_range_year_raises(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(pulso.PulsoError, match="2005"):
            pulso.load(year=2005, month=6, module="ocupados", harmonize=False)

    def test_out_of_range_month_raises(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        import pulso

        with pytest.raises(pulso.PulsoError, match="13"):
            pulso.load(year=2024, month=13, module="ocupados", harmonize=False)

    def test_month_none_loads_all_12(self, offline_pipeline) -> None:  # type: ignore[no-untyped-def]
        """Legacy: month=None → all 12 months. Must keep working."""
        import pulso

        df = pulso.load(year=2024, month=None, module="ocupados", harmonize=False)
        assert len(df) == 12


# ── load_empalme also accepts iterable years ──────────────────────────────


class TestLoadEmpalmeIterableYear:
    def test_load_empalme_year_int_accepted(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Sanity check: rc1 single-int signature still works."""
        import pandas as pd

        from pulso._core import empalme as emp_mod

        sentinel = pd.DataFrame({"DIRECTORIO": [1], "year": [2015], "month": [6]})
        monkeypatch.setattr(emp_mod, "_load_empalme_single_year", lambda *a, **kw: sentinel.copy())

        out = emp_mod.load_empalme(2015, module="ocupados", harmonize=False)
        assert len(out) == 1

    def test_load_empalme_year_range_accepted(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """range(2015, 2018) → 3 single-year calls, results stacked."""
        import pandas as pd

        from pulso._core import empalme as emp_mod

        called_years: list[int] = []

        def fake_single_year(year, module, area, harmonize):
            called_years.append(year)
            return pd.DataFrame({"x": [year]})

        monkeypatch.setattr(emp_mod, "_load_empalme_single_year", fake_single_year)

        out = emp_mod.load_empalme(range(2015, 2018), module="ocupados", harmonize=False)
        assert called_years == [2015, 2016, 2017]
        assert sorted(out["x"].tolist()) == [2015, 2016, 2017]

    def test_load_empalme_empty_year_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pulso._core import empalme as emp_mod

        with pytest.raises(ValueError, match="cannot be empty"):
            emp_mod.load_empalme(range(2015, 2015), module="ocupados", harmonize=False)

    def test_load_empalme_year_list_with_out_of_range_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pulso._core import empalme as emp_mod

        with pytest.raises(ValueError, match="2010-2020"):
            emp_mod.load_empalme([2015, 2009], module="ocupados", harmonize=False)
