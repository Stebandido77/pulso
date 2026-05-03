"""Metadata subpackage: DANE DDI-XML parser and codebook schema.

This package is internal in v1.0.0. Public API is added in a later phase
once Agente 3 wires `dane_codebook.json` into ``pulso.load(metadata=True)``.

Modules:
    parser: ``parse_ddi(path) -> dict`` for a single DDI-XML codeBook.
    schema: ``TypedDict`` definitions matching ``dane_codebook.schema.json``.
"""

from __future__ import annotations

from pulso.metadata.parser import DDIParseError, parse_ddi

__all__ = ["DDIParseError", "parse_ddi"]
