"""Input validation helpers.

These functions validate user-facing API parameters and raise typed errors
with helpful messages. They do NOT validate JSON files (that's in _config).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

VALID_AREAS = ("cabecera", "resto", "total")
Area = Literal["cabecera", "resto", "total"]


def validate_year_month(
    year: int | range | Iterable[int],
    month: int | list[int] | None,
) -> list[tuple[int, int]]:
    """Validate and normalize (year, month) inputs into a list of (year, month) tuples.

    Args:
        year: Single int, a range, or an iterable of ints.
        month: Single int, a list of ints, or None (= all 12 months).

    Returns:
        List of (year, month) tuples in chronological order.

    Raises:
        PulsoError: If inputs are invalid.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def validate_area(area: str) -> Area:
    """Validate the `area` parameter."""
    raise NotImplementedError("Phase 1: Claude Code")


def validate_module(module: str, available_modules: Iterable[str]) -> str:
    """Validate that `module` exists in the registry."""
    raise NotImplementedError("Phase 1: Claude Code")
