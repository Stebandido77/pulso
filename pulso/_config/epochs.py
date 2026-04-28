"""Read-only access to epoch definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Epoch:
    """Frozen representation of an epoch's parsing rules.

    Attributes:
        key: Epoch identifier (e.g., 'geih_2021_present').
        label: Human-readable Spanish label.
        merge_keys_persona: Keys for person-level merges.
        merge_keys_hogar: Keys for household-level merges.
        encoding: File encoding.
        file_format: 'csv', 'sav', or 'dta'.
        separator: CSV separator or None.
        decimal: Decimal mark.
        folder_pattern: Subfolder names inside the ZIP.
        weight_variable: Default expansion weight.
    """

    key: str
    label: str
    label_en: str
    date_range: tuple[str, str | None]
    merge_keys_persona: tuple[str, ...]
    merge_keys_hogar: tuple[str, ...]
    encoding: str
    file_format: str
    separator: str | None
    decimal: str
    folder_pattern: tuple[str, ...]
    weight_variable: str
    notes_es: str | None
    methodology_url: str | None


def get_epoch(key: str) -> Epoch:
    """Return the Epoch object for a given key."""
    raise NotImplementedError("Phase 1: Claude Code")


def epoch_for_month(year: int, month: int) -> Epoch:
    """Return the Epoch that contains the given (year, month).

    Raises:
        ConfigError: If no epoch covers the date.
    """
    raise NotImplementedError("Phase 1: Claude Code")


def list_epochs() -> list[Epoch]:
    """Return all defined epochs."""
    raise NotImplementedError("Phase 1: Claude Code")
