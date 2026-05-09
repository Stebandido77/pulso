"""Metadata subpackage.

Public runtime API (no lxml required):

* :func:`pulso.metadata.composer.compose_column_metadata`
* :func:`pulso.metadata.composer.compose_dataframe_metadata`
* :func:`pulso.metadata.api.describe_column`
* :func:`pulso.metadata.api.list_columns_metadata`

Build-time helpers (require ``pulso-co[scraper]`` for ``lxml``):

* :func:`pulso.metadata.parser.parse_ddi`
* :class:`pulso.metadata.parser.DDIParseError`

The build-time helpers are exposed lazily via :pep:`562` ``__getattr__``
so that ``import pulso.metadata`` (or anything that imports
``pulso.metadata.composer``) does NOT pull in :mod:`lxml`. lxml is moved
to the ``[scraper]`` optional extra in :file:`pyproject.toml`; the
runtime metadata path uses only the bundled JSON artifact and
:mod:`json` from the standard library.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pulso.metadata.parser import DDIParseError, parse_ddi

__all__ = ["DDIParseError", "parse_ddi"]


def __getattr__(name: str) -> Any:
    """Lazy-import lxml-dependent symbols (PEP 562)."""
    if name in {"DDIParseError", "parse_ddi"}:
        from pulso.metadata import parser

        return getattr(parser, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
