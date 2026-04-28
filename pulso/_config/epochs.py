"""Read-only access to epoch definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from pulso._config.registry import _load_epochs
from pulso._utils.exceptions import ConfigError


@dataclass(frozen=True)
class Epoch:
    """Frozen representation of an epoch's parsing rules.

    Attributes:
        key: Epoch identifier (e.g., 'geih_2021_present').
        label: Human-readable Spanish label.
        label_en: Human-readable English label.
        date_range: Inclusive [start, end]; end is None if open-ended.
        merge_keys_persona: Keys for person-level merges.
        merge_keys_hogar: Keys for household-level merges.
        encoding: File encoding.
        file_format: 'csv', 'sav', or 'dta'.
        separator: CSV separator or None.
        decimal: Decimal mark.
        folder_pattern: Subfolder names inside the ZIP.
        weight_variable: Default expansion weight.
        notes_es: Spanish methodological notes.
        methodology_url: Link to DANE methodology docs.
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


def _epoch_from_raw(key: str, raw: dict[str, Any]) -> Epoch:
    dr: list[Any] = raw["date_range"]
    mk: dict[str, Any] = raw["merge_keys"]
    fp: list[Any] = raw.get("folder_pattern", ["Cabecera/", "Resto/"])
    sep = raw.get("separator")
    mu = raw.get("methodology_url")
    ne = raw.get("notes_es")
    return Epoch(
        key=key,
        label=str(raw["label"]),
        label_en=str(raw["label_en"]),
        date_range=(str(dr[0]), str(dr[1]) if dr[1] is not None else None),
        merge_keys_persona=tuple(str(k) for k in mk["persona"]),
        merge_keys_hogar=tuple(str(k) for k in mk["hogar"]),
        encoding=str(raw["encoding"]),
        file_format=str(raw["file_format"]),
        separator=str(sep) if sep is not None else None,
        decimal=str(raw.get("decimal", ".")),
        folder_pattern=tuple(str(p) for p in fp),
        weight_variable=str(raw["weight_variable"]),
        notes_es=str(ne) if ne is not None else None,
        methodology_url=str(mu) if mu is not None else None,
    )


def get_epoch(key: str) -> Epoch:
    """Return the Epoch object for a given key.

    Retorna el objeto Epoch para una clave dada.

    Raises:
        ConfigError: If the key is not found in epochs.json.
    """
    data = _load_epochs()
    epochs: dict[str, Any] = data["epochs"]
    if key not in epochs:
        raise ConfigError(f"Epoch {key!r} not found in epochs.json.")
    return _epoch_from_raw(key, epochs[key])


def epoch_for_month(year: int, month: int) -> Epoch:
    """Return the Epoch that contains the given (year, month).

    Retorna la época que cubre el mes dado.

    Raises:
        ConfigError: If no epoch covers the requested date.
    """
    target = date(year, month, 1)
    data = _load_epochs()
    epochs: dict[str, Any] = data["epochs"]

    for key in epochs:
        epoch = _epoch_from_raw(key, epochs[key])
        start_str, end_str = epoch.date_range
        start = date(int(start_str[:4]), int(start_str[5:7]), 1)
        end = date(int(end_str[:4]), int(end_str[5:7]), 1) if end_str is not None else None
        if start <= target and (end is None or target <= end):
            return epoch

    raise ConfigError(f"No epoch found covering {year}-{month:02d}.")


def list_epochs() -> list[Epoch]:
    """Return all defined epochs.

    Retorna todas las épocas definidas en epochs.json.
    """
    data = _load_epochs()
    epochs: dict[str, Any] = data["epochs"]
    return [_epoch_from_raw(key, epochs[key]) for key in epochs]
