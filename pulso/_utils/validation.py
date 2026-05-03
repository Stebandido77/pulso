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


def _normalize_int_arg(
    value: object,
    name: str,
    *,
    valid_range: tuple[int, int],
    none_default: list[int] | None = None,
) -> list[int]:
    """Normalize ``year`` or ``month`` arguments into a sorted list of ints.

    Accepts ``int``, ``range``, or any iterable of ints (list, tuple, set,
    generator). Rejects ``bool`` and ``str`` upfront with a clear error.
    """
    # ``bool`` is a subclass of ``int`` in Python — reject it explicitly so
    # that ``validate_year_month(True, 6)`` does not silently load year=1.
    if isinstance(value, bool):
        raise TypeError(
            f"{name} must be int, range, or iterable of ints, not bool (got {value!r})."
        )
    if isinstance(value, str):
        raise TypeError(f"{name} must be int, range, or iterable of ints, not str (got {value!r}).")

    if value is None:
        if none_default is None:
            raise TypeError(f"{name} cannot be None.")
        return list(none_default)

    if isinstance(value, int):
        values = [value]
    elif isinstance(value, range):
        values = list(value)
    else:
        try:
            values = sorted({int(v) for v in value})  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise TypeError(
                f"{name} must be int, range, or iterable of ints " f"(got {type(value).__name__})."
            ) from exc

    if not values:
        raise ValueError(f"{name} cannot be empty (got {value!r}).")

    for v in values:
        if not (valid_range[0] <= v <= valid_range[1]):
            raise PulsoError(
                f"{name}={v} is out of supported range {valid_range[0]}-{valid_range[1]}."
            )

    return sorted(values)


def validate_year_month(
    year: int | range | Iterable[int],
    month: int | range | list[int] | tuple[int, ...] | Iterable[int] | None,
) -> list[tuple[int, int]]:
    """Validate and normalize (year, month) inputs into a sorted list of tuples.

    Valida y normaliza los inputs de año/mes en una lista de tuplas ordenadas.

    Args:
        year: Single ``int``, a ``range`` (e.g. ``range(2007, 2025)``), or any
            iterable of ints (list, tuple, set). ``bool`` and ``str`` are
            rejected explicitly with a clear error.
        month: Single ``int``, a ``range`` (e.g. ``range(1, 13)``), any
            iterable of ints, or ``None`` (= all 12 months — the legacy
            convenience). Like ``year``, ``bool`` and ``str`` are rejected.

    Returns:
        Sorted list of (year, month) tuples covering the cartesian product
        of the normalised ``year`` and ``month`` inputs.

    Raises:
        TypeError: ``year`` or ``month`` is of an unsupported type (str, bool,
            non-iterable object, iterable of non-ints).
        ValueError: ``year`` or ``month`` is an empty iterable (e.g.
            ``range(2025, 2025)``).
        PulsoError: A specific year or month value is out of range
            (year: 2006-2100, month: 1-12).

    Examples:
        >>> validate_year_month(2024, 6)
        [(2024, 6)]
        >>> validate_year_month(range(2023, 2025), range(1, 4))
        [(2023, 1), (2023, 2), (2023, 3), (2024, 1), (2024, 2), (2024, 3)]
        >>> validate_year_month([2023, 2024], [6, 12])
        [(2023, 6), (2023, 12), (2024, 6), (2024, 12)]
        >>> validate_year_month(2024, None)  # all 12 months
        [(2024, 1), (2024, 2), ..., (2024, 12)]
    """
    years = _normalize_int_arg(year, "year", valid_range=(2006, 2100))
    months = _normalize_int_arg(
        month, "month", valid_range=(1, 12), none_default=list(range(1, 13))
    )
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
