"""Unit tests for pulso._utils.validation."""

from __future__ import annotations

import pytest


def test_single_year_month() -> None:
    from pulso._utils.validation import validate_year_month

    result = validate_year_month(2024, 6)
    assert result == [(2024, 6)]


def test_year_with_list_of_months() -> None:
    from pulso._utils.validation import validate_year_month

    result = validate_year_month(2024, [1, 2, 3])
    assert result == [(2024, 1), (2024, 2), (2024, 3)]


def test_range_year_single_month() -> None:
    from pulso._utils.validation import validate_year_month

    result = validate_year_month(range(2018, 2020), 6)
    assert result == [(2018, 6), (2019, 6)]


def test_year_with_none_month_returns_all_12() -> None:
    from pulso._utils.validation import validate_year_month

    result = validate_year_month(2024, None)
    assert len(result) == 12
    assert result[0] == (2024, 1)
    assert result[-1] == (2024, 12)


def test_range_year_list_months() -> None:
    from pulso._utils.validation import validate_year_month

    result = validate_year_month(range(2018, 2020), [3, 6])
    assert result == [(2018, 3), (2018, 6), (2019, 3), (2019, 6)]


def test_result_is_sorted() -> None:
    from pulso._utils.validation import validate_year_month

    result = validate_year_month([2022, 2020, 2021], [12, 1])
    assert result == sorted(result)


def test_duplicate_years_deduplicated() -> None:
    from pulso._utils.validation import validate_year_month

    result = validate_year_month([2024, 2024], 6)
    assert result == [(2024, 6)]


def test_duplicate_months_deduplicated() -> None:
    from pulso._utils.validation import validate_year_month

    result = validate_year_month(2024, [6, 6, 6])
    assert result == [(2024, 6)]


def test_invalid_year_too_early_raises() -> None:
    from pulso._utils.exceptions import PulsoError
    from pulso._utils.validation import validate_year_month

    with pytest.raises(PulsoError, match="2005"):
        validate_year_month(2005, 6)


def test_invalid_month_zero_raises() -> None:
    from pulso._utils.exceptions import PulsoError
    from pulso._utils.validation import validate_year_month

    with pytest.raises(PulsoError, match="0"):
        validate_year_month(2024, 0)


def test_invalid_month_13_raises() -> None:
    from pulso._utils.exceptions import PulsoError
    from pulso._utils.validation import validate_year_month

    with pytest.raises(PulsoError, match="13"):
        validate_year_month(2024, 13)


def test_validate_area_cabecera() -> None:
    from pulso._utils.validation import validate_area

    assert validate_area("cabecera") == "cabecera"


def test_validate_area_resto() -> None:
    from pulso._utils.validation import validate_area

    assert validate_area("resto") == "resto"


def test_validate_area_total() -> None:
    from pulso._utils.validation import validate_area

    assert validate_area("total") == "total"


def test_validate_area_invalid_raises() -> None:
    from pulso._utils.exceptions import PulsoError
    from pulso._utils.validation import validate_area

    with pytest.raises(PulsoError, match="invalid_area"):
        validate_area("invalid_area")


def test_validate_module_valid() -> None:
    from pulso._utils.validation import validate_module

    result = validate_module("ocupados", ["ocupados", "inactivos"])
    assert result == "ocupados"


def test_validate_module_missing_raises() -> None:
    from pulso._utils.exceptions import ModuleNotAvailableError
    from pulso._utils.validation import validate_module

    with pytest.raises(ModuleNotAvailableError, match="nonexistent"):
        validate_module("nonexistent", ["ocupados", "inactivos"])


# ── Commit 10: type validation (m-2, m-3) ──────────────────────────────


def test_validate_year_month_rejects_bool_year() -> None:
    """m-2: bool is not a valid year (Python treats True/False as 1/0)."""
    from pulso._utils.validation import validate_year_month

    with pytest.raises(TypeError, match="bool"):
        validate_year_month(True, 6)  # type: ignore[arg-type]


def test_validate_year_month_rejects_bool_month() -> None:
    from pulso._utils.validation import validate_year_month

    with pytest.raises(TypeError, match="bool"):
        validate_year_month(2024, True)  # type: ignore[arg-type]


def test_validate_year_month_rejects_str_year() -> None:
    """m-3: str must fail upfront with a clear message, not crash mid-iteration."""
    from pulso._utils.validation import validate_year_month

    with pytest.raises(TypeError, match="str"):
        validate_year_month("2024", 6)  # type: ignore[arg-type]


def test_validate_year_month_rejects_str_month() -> None:
    from pulso._utils.validation import validate_year_month

    with pytest.raises(TypeError, match="str"):
        validate_year_month(2024, "6")  # type: ignore[arg-type]
