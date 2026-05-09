"""Tests for the extended describe(module, year, month) (Commit 13.5).

The function has three call shapes, all backed entirely by JSON files
already loaded by the package — no schemas changed, no I/O outside
``importlib.resources``.
"""

from __future__ import annotations

import pytest


def test_describe_catalog_mode_for_known_module() -> None:
    import pulso

    info = pulso.describe("ocupados")
    assert info["module"] == "ocupados"
    assert "available_for_periods" in info
    assert "epochs_covering" in info
    assert info["total_periods_in_registry"] >= 1
    assert info["validated_periods"] >= 0
    assert info["variables_harmonized"] >= 0


def test_describe_year_mode() -> None:
    import pulso

    info = pulso.describe("ocupados", year=2024)
    assert info["module"] == "ocupados"
    assert info["year"] == 2024
    assert "epoch" in info
    assert "available_months" in info
    assert "validated_months" in info


def test_describe_period_mode_validated() -> None:
    """2024-06 is in the production validated set; full record must come back."""
    import pulso

    info = pulso.describe("ocupados", year=2024, month=6)
    assert info["module"] == "ocupados"
    assert info["year"] == 2024
    assert info["month"] == 6
    assert info["epoch"] == "geih_2021_present"
    assert info["validated"] is True
    assert info["checksum_sha256"] is not None
    assert info["file_url"] is not None


def test_describe_period_mode_unvalidated_returns_null_checksum() -> None:
    """An entry with validated=false (one of the 225 in production) returns None checksum."""
    import pulso

    # 2007-01 is in the registry but not validated end-to-end.
    info = pulso.describe("ocupados", year=2007, month=1)
    assert info["validated"] is False
    assert info["checksum_sha256"] is None


def test_describe_unknown_module_raises_with_suggestion() -> None:
    """Typo in module name surfaces a difflib 'did you mean ...?' hint."""
    import pulso

    with pytest.raises(pulso.ConfigError, match="ocupados"):
        # 'ocupado' is one letter off; difflib should propose 'ocupados'.
        pulso.describe("ocupado")


def test_describe_unknown_module_lists_available() -> None:
    import pulso

    with pytest.raises(pulso.ConfigError, match="Available modules"):
        pulso.describe("definitely_not_a_real_module_xyz")


def test_describe_month_without_year_raises() -> None:
    import pulso

    with pytest.raises(ValueError, match="requires year"):
        pulso.describe("ocupados", month=6)


def test_describe_period_not_in_registry_raises() -> None:
    """A period absent from sources.json raises DataNotAvailableError."""
    import pulso

    with pytest.raises(pulso.DataNotAvailableError):
        # 2030-06 is well past the current registry coverage.
        pulso.describe("ocupados", year=2030, month=6)


def test_describe_module_not_in_period_raises() -> None:
    """A module that isn't in the period's `modules` dict raises ModuleNotAvailableError.

    'migracion' only exists in the post-2022 registry rows, so 2007-12
    (which IS in the registry, validated) does NOT include it.
    """
    import pulso

    with pytest.raises(pulso.ModuleNotAvailableError):
        pulso.describe("migracion", year=2007, month=12)


def test_describe_returns_native_dict() -> None:
    """The result should be a plain dict for easy json.dumps / pprint."""
    import pulso

    info = pulso.describe("ocupados")
    assert isinstance(info, dict)
