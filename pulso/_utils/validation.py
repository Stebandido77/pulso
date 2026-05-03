"""Input validation helpers.

These functions validate user-facing API parameters and raise typed errors
with helpful messages. They do NOT validate JSON files (that's in _config).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pulso._utils.exceptions import ModuleNotAvailableError, PulsoError

if TYPE_CHECKING:
    from collections.abc import Iterable

VALID_AREAS = ("cabecera", "resto", "total")
Area = Literal["cabecera", "resto", "total"]


def validate_year_month(
    year: int | range | Iterable[int],
    month: int | list[int] | None,
) -> list[tuple[int, int]]:
    """Validate and normalize (year, month) inputs into a sorted list of tuples.

    Valida y normaliza los inputs de año/mes en una lista de tuplas ordenadas.

    Args:
        year: Single int, a range, or an iterable of ints. ``bool`` is
            rejected explicitly (Python treats True/False as 1/0).
        month: Single int, a list of ints, or None (= all 12 months).
            ``str`` and ``bool`` are rejected explicitly.

    Returns:
        Sorted list of (year, month) tuples.

    Raises:
        TypeError: If ``year`` or ``month`` is of an unsupported type
            (str, bool, ...).
        PulsoError: If any year or month value is out of range.
    """
    # ── Type validation upfront so cryptic mid-iteration errors are avoided ──
    # Note: bool is a subclass of int in Python; reject it explicitly so that
    # `validate_year_month(True, 6)` does not silently load year=1.
    if isinstance(year, bool):
        raise TypeError("year must be int, range, or iterable of ints, not bool.")
    if isinstance(year, str):
        raise TypeError(f"year must be int, range, or iterable of ints, not str (got {year!r}).")
    if isinstance(month, bool):
        raise TypeError("month must be int, list[int], or None, not bool.")
    if isinstance(month, str):
        raise TypeError(f"month must be int, list[int], or None, not str (got {month!r}).")

    if isinstance(year, int):
        years = [year]
    elif isinstance(year, range):
        years = list(year)
    else:
        years = sorted({int(y) for y in year})

    if month is None:
        months = list(range(1, 13))
    elif isinstance(month, int):
        months = [month]
    else:
        months = sorted(set(month))

    for y in years:
        if y < 2006 or y > 2100:
            raise PulsoError(f"Year {y} is out of supported range 2006-2100.")

    for m in months:
        if m < 1 or m > 12:
            raise PulsoError(f"Month {m} is invalid; must be 1-12.")

    return sorted((y, m) for y in years for m in months)


def validate_area(area: str) -> Area:
    """Validate the `area` parameter and return as a typed literal.

    Valida el parámetro de área geográfica.

    Raises:
        PulsoError: If the area is not one of 'cabecera', 'resto', 'total'.
    """
    if area not in VALID_AREAS:
        raise PulsoError(f"Invalid area {area!r}. Must be one of: {', '.join(VALID_AREAS)}.")
    return area  # type: ignore[return-value]


def validate_module(module: str, available_modules: Iterable[str]) -> str:
    """Validate that `module` exists in the registry.

    Valida que el módulo exista en la lista de módulos disponibles.

    Raises:
        ModuleNotAvailableError: If the module is not in available_modules.
    """
    available = list(available_modules)
    if module not in available:
        raise ModuleNotAvailableError(
            f"Module {module!r} is not available. Available modules: {available}."
        )
    return module
