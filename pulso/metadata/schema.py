"""TypedDicts mirroring ``pulso/data/schemas/dane_codebook.schema.json``.

These are advisory only — runtime validation is done with ``jsonschema``
against the JSON Schema. Use these in static type-checking and IDE
autocomplete.
"""

from __future__ import annotations

from typing import Literal, TypedDict

VariableType = Literal["categorical", "numeric", "character", "unknown"]


class ValueRange(TypedDict):
    """Numeric ``<valrng><range>`` from a DDI variable."""

    min: float
    max: float


class YearEntry(TypedDict, total=False):
    """One per-year record under ``variables[code].available_in[year]``."""

    epoch: str
    file_id_in_year: str | None
    var_id_in_year: str | None
    label: str | None
    type: VariableType
    question_text: str | None
    categories: dict[str, str] | None
    value_range: ValueRange | None


class Variable(TypedDict, total=False):
    """One entry under top-level ``variables[code]``."""

    code: str
    label: str
    type: VariableType
    question_text: str | None
    universe: str | None
    response_unit: str | None
    categories: dict[str, str] | None
    value_range: ValueRange | None
    notes: str | None
    available_in: dict[str, YearEntry]


class EpochSummary(TypedDict):
    years: list[int]
    variable_count: int


class DaneCodebook(TypedDict):
    """Top-level shape of ``pulso/data/dane_codebook.json``."""

    schema_version: str
    generated_at: str
    source: str
    coverage_years: list[int]
    epochs: dict[str, EpochSummary]
    variables: dict[str, Variable]


class ParsedYear(TypedDict):
    """Output of :func:`pulso.metadata.parser.parse_ddi`.

    A single year's worth of parsed metadata, before merge-by-code into
    the final :class:`DaneCodebook` shape.
    """

    year: int | None
    ddi_id: str | None
    file_descriptors: dict[str, str]
    variables: dict[str, Variable]
