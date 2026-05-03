"""Tests for the continue-on-failure semantics under strict=False (Commit 7, M-5).

When ``strict=False`` (default) and a per-period error occurs in a multi-period
load, the loader records the failure, continues, and emits ONE aggregated
warning at the end. When ``strict=True`` it aborts on first failure (rc1
behaviour).
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _make_partial_sources(*, missing_keys: list[str], present_keys: list[str]) -> dict[str, Any]:
    """Sources where some keys are completely absent from the registry."""
    return {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Ocu",
                "description_en": "Ocu",
                "available_in": ["geih_2021_present"],
            }
        },
        "data": {
            key: {
                "epoch": "geih_2021_present",
                "download_url": f"https://example.com/{key}.zip",
                "checksum_sha256": "a" * 64,
                "modules": {"ocupados": {"cabecera": f"{key}.CSV"}},
                "validated": True,
            }
            for key in present_keys
            # missing_keys deliberately not included
        },
    }


@pytest.fixture
def setup_partial(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
):
    """Pipeline factory for partial-registry tests."""

    def _setup(*, missing_keys: list[str], present_keys: list[str]) -> None:
        import pulso._config.registry as reg
        import pulso._core.downloader as dl_mod
        import pulso._core.parser as parser_mod

        sources = _make_partial_sources(missing_keys=missing_keys, present_keys=present_keys)
        monkeypatch.setattr(reg, "_SOURCES", sources)
        monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setattr(dl_mod, "verify_checksum", lambda *a, **kw: True)

        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"bytes"]
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mocker.patch("requests.get", return_value=mock_response)

        sentinel = pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})
        # Return a copy so per-period year/month assignments don't mutate the
        # shared DataFrame reference (otherwise concat would show last-write-wins).
        monkeypatch.setattr(parser_mod, "parse_module", lambda *a, **kw: sentinel.copy())

    return _setup


def test_load_range_with_missing_period_strict_false_continues(setup_partial) -> None:  # type: ignore[no-untyped-def]
    """M-5: range(2022, 2026) with 2005 absent → loads 2006-2008, warning."""
    import pulso

    setup_partial(
        missing_keys=["2022-06"],
        present_keys=["2023-06", "2024-06", "2025-06"],
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=range(2022, 2026),
            month=6,
            module="ocupados",
            harmonize=False,
        )

    assert len(df) == 3  # one row per loaded period (2006, 2007, 2008)
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1
    msg = str(user_warnings[0].message)
    assert "1 months failed to load" in msg
    assert "2022-06" in msg


def test_load_range_with_missing_period_strict_true_aborts(setup_partial) -> None:  # type: ignore[no-untyped-def]
    """M-5: range with strict=True still raises on first failure (rc1 behaviour)."""
    import pulso

    setup_partial(
        missing_keys=["2022-06"],
        present_keys=["2023-06", "2024-06", "2025-06"],
    )

    with pytest.raises(pulso.DataNotAvailableError):
        pulso.load(
            year=range(2022, 2026),
            month=6,
            module="ocupados",
            strict=True,
            harmonize=False,
        )


def test_load_range_stacks_dataframes_with_year_month_columns(setup_partial) -> None:  # type: ignore[no-untyped-def]
    """G-9: multi-period load adds year/month columns and concats correctly."""
    import pulso

    setup_partial(
        missing_keys=[],
        present_keys=["2022-06", "2023-06", "2024-06"],
    )

    df = pulso.load(year=range(2022, 2025), month=6, module="ocupados", harmonize=False)
    assert "year" in df.columns
    assert "month" in df.columns
    assert sorted(df["year"].unique().tolist()) == [2022, 2023, 2024]


def test_module_not_available_error_is_NOT_skipped_under_strict_false(setup_partial) -> None:  # type: ignore[no-untyped-def]
    """Usage errors (ModuleNotAvailableError) must surface even under strict=False.

    Continue-on-failure is for transient/data issues, not for the user typing
    a module name that doesn't exist in the period.
    """
    import pulso

    setup_partial(missing_keys=[], present_keys=["2024-06"])

    with pytest.raises(pulso.ModuleNotAvailableError):
        # 'inactivos' is not in the period's modules dict
        pulso.load(
            year=2024,
            month=6,
            module="inactivos",
            harmonize=False,
            strict=False,
        )


def test_aggregated_warning_includes_both_unvalidated_and_failures(  # type: ignore[no-untyped-def]
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
) -> None:
    """When both classes of issues happen, one warning summarises both."""
    import pulso
    import pulso._config.registry as reg
    import pulso._core.downloader as dl_mod
    import pulso._core.parser as parser_mod

    # 2024-06 unvalidated, 2024-07 missing entirely
    sources = {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Ocu",
                "description_en": "Ocu",
                "available_in": ["geih_2021_present"],
            }
        },
        "data": {
            "2024-06": {
                "epoch": "geih_2021_present",
                "download_url": "https://example.com/x.zip",
                "checksum_sha256": None,
                "modules": {"ocupados": {"cabecera": "x.CSV"}},
                "validated": False,
            }
        },
    }
    monkeypatch.setattr(reg, "_SOURCES", sources)
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(dl_mod, "verify_checksum", lambda *a, **kw: True)

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"bytes"]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    sentinel = pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})
    monkeypatch.setattr(parser_mod, "parse_module", lambda *a, **kw: sentinel)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=[6, 7], module="ocupados", harmonize=False, strict=False)

    assert len(df) == 1  # only 2024-06 loaded
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1
    msg = str(user_warnings[0].message)
    assert "checksum-validated" in msg
    assert "failed to load" in msg
