"""Read-only access to the variable map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VariableMapping:
    """A single (variable, epoch) mapping spec."""

    canonical_name: str
    epoch: str
    source_variable: str | tuple[str, ...]
    transform: str | dict[str, Any]
    source_doc: str | None


@dataclass(frozen=True)
class Variable:
    """Full definition of a harmonized variable."""

    canonical_name: str
    type: str  # numeric|categorical|string|boolean|date
    level: str  # persona|hogar|vivienda
    module: str
    description_es: str | None
    description_en: str | None
    unit: str | None
    categories: dict[str, str] | None
    comparability_warning: str | None
    mappings: dict[str, VariableMapping]


def get_variable(name: str) -> Variable:
    """Return the Variable definition for a canonical name."""
    raise NotImplementedError("Phase 2: Claude Code")


def get_mapping(name: str, epoch: str) -> VariableMapping:
    """Return the (variable, epoch) mapping spec.

    Raises:
        ConfigError: If the variable or epoch isn't defined.
    """
    raise NotImplementedError("Phase 2: Claude Code")


def variables_for_module(module: str) -> list[Variable]:
    """Return all harmonized variables that belong to a module."""
    raise NotImplementedError("Phase 2: Claude Code")
