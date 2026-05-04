"""User-facing helpers for inspecting metadata on a loaded DataFrame.

These functions assume the caller passed ``metadata=True`` to
:func:`pulso.load` (or :func:`pulso.load_merged`), which attaches the
composed metadata under ``df.attrs["column_metadata"]``. If it isn't
attached they return / raise a helpful hint pointing the caller back to
``metadata=True``.

Two known limitations of ``df.attrs``:

* ``df.attrs`` is preserved across slicing (``df[cols]``, ``df.head()``)
  but pandas does not propagate it across :meth:`pandas.DataFrame.merge`,
  :meth:`pandas.DataFrame.groupby`, :meth:`pandas.concat`, etc. Re-call
  :func:`pulso.load` (or copy the attrs manually) if you need it after
  those operations.
* For variables where DANE publishes only a near-empty DDI entry
  (typically conditional sub-questions like ``P3044S2`` or ``P3057``)
  :func:`describe_column` falls back to a "skeletal" rendering that
  points users at the project issue tracker. The detection rule is
  documented in the function body.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


_NO_METADATA_HINT = "No metadata loaded. Re-call pulso.load(..., metadata=True) to attach metadata."
_FEEDBACK_URL = "https://github.com/Stebandido77/pulso/issues"


def _is_skeletal(meta: dict[str, Any], column: str) -> bool:
    """Return True iff ``meta`` is a codebook-skeletal entry.

    Detection rule (codified per Phase 2 spec):

    * source is exactly ``"codebook"`` (not Curator, not merged).
    * label is None OR equals the column name (DANE label = the variable
      code itself, which carries no semantic content).
    * categories, question_text, and universe are all None / absent.
    """
    if meta.get("source") != "codebook":
        return False
    label = meta.get("label")
    label_is_self = label is None or (isinstance(label, str) and label.strip() == column)
    if not label_is_self:
        return False
    if meta.get("categories"):
        return False
    if meta.get("question_text"):
        return False
    return not meta.get("universe")


def _format_categories(categories: dict[str, str] | None) -> list[str]:
    """Render a categories mapping as indented value=label lines."""
    if not categories:
        return []
    lines = ["Categories:"]
    for value, label in categories.items():
        lines.append(f"  {value} = {label}")
    return lines


def _render_skeletal(column: str, meta: dict[str, Any]) -> str:
    """Render the §B-defined block for skeletal metadata."""
    type_str = meta.get("type") or "unknown"
    module_str = meta.get("module") or "unknown"
    return (
        f"{column} (sub-question, skeletal metadata)\n"
        f"Type: {type_str}\n"
        f"Module: {module_str}\n"
        f"Source: codebook (skeletal)\n"
        f"Note: Full metadata available on DANE catalog HTML, not yet integrated.\n"
        f"      Open issue at {_FEEDBACK_URL} if you\n"
        f"      need this for your analysis."
    )


def _render_full(column: str, meta: dict[str, Any]) -> str:
    """Render the canonical / merged / codebook full-format description."""
    source = meta.get("source", "unknown")
    label = meta.get("label") or column
    lines: list[str] = [f"{column}: {label}"]

    if meta.get("canonical_name") and meta["canonical_name"] != column:
        lines.append(f"Canonical name: {meta['canonical_name']}")
    if meta.get("dane_code") and meta["dane_code"] != column:
        dane_code = meta["dane_code"]
        if isinstance(dane_code, list):
            dane_code = ", ".join(str(c) for c in dane_code)
        lines.append(f"DANE code: {dane_code}")

    if meta.get("description_es"):
        lines.append(f"Description (es): {meta['description_es']}")
    if meta.get("description_en"):
        lines.append(f"Description (en): {meta['description_en']}")

    if meta.get("type"):
        lines.append(f"Type: {meta['type']}")
    if meta.get("module"):
        lines.append(f"Module: {meta['module']}")
    if meta.get("epoch"):
        lines.append(f"Epoch: {meta['epoch']}")

    if meta.get("question_text"):
        lines.append(f"Question text: {meta['question_text']}")
    if meta.get("universe"):
        lines.append(f"Universe: {meta['universe']}")

    value_range = meta.get("value_range")
    if value_range:
        lo = value_range.get("min")
        hi = value_range.get("max")
        lines.append(f"Value range: [{lo}, {hi}]")

    lines.extend(_format_categories(meta.get("categories")))

    if meta.get("notes"):
        lines.append(f"Notes: {meta['notes']}")

    lines.append(f"Source: {source}")
    if source == "merged":
        lines.append(
            "  (categories/description from Curator's variable_map.json; "
            "question_text/universe from DANE codebook.)"
        )
    return "\n".join(lines)


def describe_column(df: pd.DataFrame, column: str) -> str:
    """Pretty-print metadata for ``column`` of ``df``.

    Args:
        df: A DataFrame returned by ``pulso.load(..., metadata=True)`` or
            ``pulso.load_merged(..., metadata=True)``.
        column: A column name present in ``df.columns``.

    Returns:
        A multi-line human-readable string. For skeletal codebook
        entries (DANE sub-questions with empty DDI metadata) it returns
        the §B "skeletal" format pointing users at ``{_FEEDBACK_URL}``.
        If metadata is not attached, returns a hint to re-call ``load``.

    Raises:
        ValueError: ``column`` is not in ``df.columns``.
    """
    if column not in df.columns:
        raise ValueError(
            f"Column {column!r} is not in the DataFrame "
            f"(have {len(df.columns)} columns; first few: {list(df.columns[:5])})."
        )

    column_metadata = df.attrs.get("column_metadata") or {}
    meta = column_metadata.get(column)
    if not meta:
        return _NO_METADATA_HINT

    if _is_skeletal(meta, column):
        return _render_skeletal(column, meta)
    return _render_full(column, meta)


def list_columns_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Return a summary DataFrame describing every column in ``df``.

    The result has one row per column in ``df`` and the columns
    ``['column', 'label', 'type', 'module', 'source', 'has_categories']``.
    Works even when ``df.attrs["column_metadata"]`` is missing — every
    row will then have ``source='missing'`` and the remaining fields
    ``None``.
    """
    import pandas as pd

    column_metadata: dict[str, Any] = df.attrs.get("column_metadata") or {}
    rows: list[dict[str, Any]] = []
    for col in df.columns:
        meta = column_metadata.get(str(col)) or {}
        rows.append(
            {
                "column": str(col),
                "label": meta.get("label"),
                "type": meta.get("type"),
                "module": meta.get("module"),
                "source": meta.get("source", "missing"),
                "has_categories": bool(meta.get("categories")),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["column", "label", "type", "module", "source", "has_categories"],
    )
