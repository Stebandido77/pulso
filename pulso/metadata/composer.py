"""Compose per-column metadata by merging Curator + DANE codebook.

This module is pure stdlib + pandas. It must NOT import :mod:`lxml`; the
DDI parser lives next to it but is opt-in via the ``[scraper]`` extra.

Two artefacts feed this module (both bundled in :mod:`pulso.data`):

* ``variable_map.json`` — Curator harmonisation contract, keyed by
  canonical Spanish names (``sexo``, ``edad``, ...). Each canonical entry
  has ``mappings.{epoch}.source_variable`` pointing at the raw DANE code
  (or a list of codes for derived variables).
* ``dane_codebook.json`` — auto-generated codebook, keyed by raw DANE
  codes (``P6020``, ``P3271``, ``OCI``, ...). Contains DANE-published
  ``label``, ``question_text``, ``universe``, ``categories``, etc.,
  versioned per-year under ``available_in[year]``.

Compose precedence (already established in the project decisions):

* ``categories``        : Curator > codebook
* ``description``/label : Curator > codebook
* ``module``/``type``   : Curator > codebook
* ``question_text``     : codebook only (Curator does not have it)
* ``universe``          : codebook only
* ``value_range``       : codebook only

The composer also exposes a ``source`` field on each result indicating
which artefact contributed:

* ``"curator"``  — Curator-only (column is a canonical Spanish name).
* ``"codebook"`` — codebook-only (raw DANE code that no Curator entry
  references).
* ``"merged"``   — both contributed (raw DANE code that IS referenced
  by some Curator mapping for the relevant epoch).
* ``"missing"``  — column absent from both artefacts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    import pandas as pd


class ColumnMetadata(TypedDict, total=False):
    """Composed metadata for one DataFrame column.

    Every field is optional in the TypedDict sense — the composer always
    sets ``source`` and the column key, but the rest are present only
    when an underlying artefact provided them. Consumers should use
    ``.get(...)`` rather than direct subscripting.
    """

    label: str | None
    description_es: str | None
    description_en: str | None
    question_text: str | None
    universe: str | None
    categories: dict[str, str] | None
    type: str | None
    module: str | None
    epoch: str | None
    source: str  # 'curator' | 'codebook' | 'merged' | 'missing'
    notes: str | None
    value_range: dict[str, float] | None
    canonical_name: str | None
    dane_code: str | None


# ─── Cached singletons ────────────────────────────────────────────────

# Loaded lazily on first call to keep import-time cost trivial.
_CODEBOOK: dict[str, Any] | None = None
_REVERSE_INDEX: dict[tuple[str, str], str] | None = None
_CODEBOOK_LOWERCASE_INDEX: dict[str, str] | None = None


def _load_codebook() -> dict[str, Any]:
    """Load and memoise ``pulso/data/dane_codebook.json`` (UTF-8)."""
    global _CODEBOOK
    if _CODEBOOK is None:
        import json
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "data" / "dane_codebook.json"
        with path.open(encoding="utf-8") as f:
            _CODEBOOK = json.load(f)
    return _CODEBOOK


def _build_reverse_index() -> dict[tuple[str, str], str]:
    """Build ``(epoch, dane_code) -> canonical_name`` lookup from Curator.

    A Curator entry whose ``source_variable`` is a list of codes (e.g.
    ``ingreso_total = [INGLABO, P7500S1A1, ...]``) registers an entry
    for each code. If two canonical names map to the same code in the
    same epoch (rare), the first one wins — Curator entries are iterated
    in file order, which is stable across reloads.
    """
    global _REVERSE_INDEX
    if _REVERSE_INDEX is None:
        from pulso._config.registry import _load_variable_map

        var_map = _load_variable_map()
        index: dict[tuple[str, str], str] = {}
        for canonical, entry in var_map["variables"].items():
            mappings = entry.get("mappings", {})
            for epoch_key, mp in mappings.items():
                source = mp.get("source_variable")
                if source is None:
                    continue
                codes = source if isinstance(source, list) else [source]
                for code in codes:
                    key = (epoch_key, str(code))
                    index.setdefault(key, canonical)
        _REVERSE_INDEX = index
    return _REVERSE_INDEX


def _build_codebook_lowercase_index() -> dict[str, str]:
    """Map ``lowercase_code -> real_codebook_key`` for case-insensitive AREA/CLASE.

    The raw codebook contains both ``AREA`` and ``Area`` (and similarly
    for CLASE) verbatim, because that's what DANE publishes in different
    years. The public composer treats them as the same column. If both
    keys exist we prefer the all-uppercase one (canonical form), which
    matches what the harmoniser ultimately exposes.
    """
    global _CODEBOOK_LOWERCASE_INDEX
    if _CODEBOOK_LOWERCASE_INDEX is None:
        cb = _load_codebook()
        index: dict[str, str] = {}
        for code in cb["variables"]:
            lower = code.lower()
            if lower in index:
                # Prefer all-uppercase canonical form when collision.
                if code.isupper() and not index[lower].isupper():
                    index[lower] = code
            else:
                index[lower] = code
        _CODEBOOK_LOWERCASE_INDEX = index
    return _CODEBOOK_LOWERCASE_INDEX


def _reset_caches_for_tests() -> None:
    """Reset module-level caches. Test-only hook."""
    global _CODEBOOK, _REVERSE_INDEX, _CODEBOOK_LOWERCASE_INDEX
    _CODEBOOK = None
    _REVERSE_INDEX = None
    _CODEBOOK_LOWERCASE_INDEX = None


def _epoch_key_for(year: int, month: int) -> str:
    """Resolve epoch key for a (year, month). Reuses :mod:`pulso._config`."""
    from pulso._config.epochs import epoch_for_month

    return epoch_for_month(year, month).key


def _get_codebook_entry(code: str) -> tuple[str | None, dict[str, Any] | None]:
    """Return ``(real_key, entry)`` or ``(None, None)``.

    Tries an exact match first, then a case-insensitive match (which is
    where ``AREA``/``Area`` and ``CLASE``/``Clase`` get collapsed in the
    public API).
    """
    cb = _load_codebook()
    variables: dict[str, Any] = cb["variables"]
    if code in variables:
        return code, variables[code]
    ci = _build_codebook_lowercase_index().get(code.lower())
    if ci is not None and ci in variables:
        return ci, variables[ci]
    return None, None


def _pick_year_entry(var_entry: dict[str, Any], year: int, epoch_key: str) -> dict[str, Any] | None:
    """Choose the best ``available_in`` entry for the requested year.

    Preference order:
    1. Exact year match.
    2. Most-recent year that shares the same epoch.
    3. Most-recent year overall (fall back to the top-level snapshot
       fields by returning ``None``).
    """
    available = var_entry.get("available_in") or {}
    if not isinstance(available, dict):
        return None
    str_year = str(year)
    if str_year in available:
        return available[str_year]

    same_epoch_years = sorted(
        (int(y) for y, e in available.items() if e.get("epoch") == epoch_key),
        reverse=True,
    )
    if same_epoch_years:
        return available[str(same_epoch_years[0])]

    return None


def _curator_entry_for(canonical: str) -> dict[str, Any] | None:
    """Return the Curator entry for a canonical name, or ``None``."""
    from pulso._config.registry import _load_variable_map

    var_map = _load_variable_map()
    variables: dict[str, Any] = var_map["variables"]
    return variables.get(canonical)


def _curator_payload(curator_entry: dict[str, Any], epoch_key: str) -> dict[str, Any]:
    """Extract fields contributed by Curator (Spanish-canonical layer)."""
    mappings = curator_entry.get("mappings", {})
    epoch_mapping = mappings.get(epoch_key) or {}
    source_variable = epoch_mapping.get("source_variable")
    return {
        "description_es": curator_entry.get("description_es"),
        "description_en": curator_entry.get("description_en"),
        "categories": curator_entry.get("categories"),
        "type": curator_entry.get("type"),
        "module": curator_entry.get("module"),
        "notes": curator_entry.get("comparability_warning"),
        "dane_code": source_variable,
    }


def _codebook_payload(
    real_code: str, var_entry: dict[str, Any], year: int, epoch_key: str
) -> dict[str, Any]:
    """Extract fields contributed by the DANE codebook for ``year``."""
    year_entry = _pick_year_entry(var_entry, year, epoch_key) or {}
    label = year_entry.get("label", var_entry.get("label"))
    question_text = year_entry.get("question_text", var_entry.get("question_text"))
    categories = year_entry.get("categories", var_entry.get("categories"))
    var_type = year_entry.get("type", var_entry.get("type"))
    value_range = year_entry.get("value_range", var_entry.get("value_range"))
    universe = var_entry.get("universe")
    notes = var_entry.get("notes")
    return {
        "label": label,
        "question_text": question_text,
        "categories": categories,
        "type": var_type,
        "value_range": value_range,
        "universe": universe,
        "notes": notes,
        "dane_code": real_code,
    }


def compose_column_metadata(
    column_name: str,
    year: int,
    month: int,
    module: str,  # noqa: ARG001 — reserved for future module-specific overrides
) -> ColumnMetadata:
    """Compose metadata for ``column_name`` at the given period and module.

    The function is the heart of ``metadata=True``:

    1. Determine the epoch from ``(year, month)``.
    2. If ``column_name`` matches a Curator canonical name, the result is
       sourced from Curator alone; we still mark ``dane_code`` from the
       Curator mapping so consumers can chase the raw value if needed.
    3. Otherwise look ``column_name`` up in the codebook (case-insensitive
       for AREA/CLASE-style duplicates). If a Curator entry references it
       for this epoch, merge the two (Curator wins on the fields named in
       the precedence rule above).
    4. If neither artefact knows about ``column_name``, return
       ``{"source": "missing"}`` plus the bare column key.

    The ``module`` argument is currently informational (added to
    ``column_metadata[col]["module"]`` when Curator supplies it). It's
    included in the signature so that future enrichments — e.g. module-
    specific overrides — don't require an API break.
    """
    epoch_key = _epoch_key_for(year, month)

    # Path 1: column matches a Curator canonical name directly.
    curator_entry = _curator_entry_for(column_name)
    if curator_entry is not None:
        curator = _curator_payload(curator_entry, epoch_key)
        result: ColumnMetadata = {
            "source": "curator",
            "epoch": epoch_key,
            "canonical_name": column_name,
            "dane_code": curator["dane_code"],
            "label": curator["description_es"],
            "description_es": curator["description_es"],
            "description_en": curator["description_en"],
            "categories": curator["categories"],
            "type": curator["type"],
            "module": curator["module"],
            "notes": curator["notes"],
            "question_text": None,
            "universe": None,
            "value_range": None,
        }
        return result

    # Path 2/3: column is (or might be) a raw DANE code.
    real_code, var_entry = _get_codebook_entry(column_name)
    if var_entry is None:
        return {
            "source": "missing",
            "epoch": epoch_key,
            "canonical_name": None,
            "dane_code": None,
            "label": None,
            "description_es": None,
            "description_en": None,
            "categories": None,
            "type": None,
            "module": None,
            "notes": None,
            "question_text": None,
            "universe": None,
            "value_range": None,
        }

    codebook = _codebook_payload(real_code or column_name, var_entry, year, epoch_key)

    # Reverse-lookup: does any Curator canonical entry point at this code
    # for this epoch?
    reverse = _build_reverse_index()
    canonical = reverse.get((epoch_key, real_code or column_name))

    if canonical is None:
        # Pure codebook path.
        return {
            "source": "codebook",
            "epoch": epoch_key,
            "canonical_name": None,
            "dane_code": codebook["dane_code"],
            "label": codebook["label"],
            "description_es": None,
            "description_en": None,
            "categories": codebook["categories"],
            "type": codebook["type"],
            "module": None,
            "notes": codebook["notes"],
            "question_text": codebook["question_text"],
            "universe": codebook["universe"],
            "value_range": codebook["value_range"],
        }

    # Merged path — Curator wins on description/categories/type/module,
    # codebook supplies question_text/universe/value_range.
    curator_entry = _curator_entry_for(canonical) or {}
    curator = _curator_payload(curator_entry, epoch_key)
    return {
        "source": "merged",
        "epoch": epoch_key,
        "canonical_name": canonical,
        "dane_code": codebook["dane_code"],
        "label": curator["description_es"] or codebook["label"],
        "description_es": curator["description_es"],
        "description_en": curator["description_en"],
        "categories": curator["categories"] or codebook["categories"],
        "type": curator["type"] or codebook["type"],
        "module": curator["module"],
        "notes": curator["notes"] or codebook["notes"],
        "question_text": codebook["question_text"],
        "universe": codebook["universe"],
        "value_range": codebook["value_range"],
    }


def compose_dataframe_metadata(
    df: pd.DataFrame, year: int, month: int, module: str
) -> dict[str, ColumnMetadata]:
    """Compose metadata for every column in ``df``.

    The result maps each column name in ``df.columns`` (preserving order)
    to its :class:`ColumnMetadata`. Use it directly via
    ``df.attrs["column_metadata"]`` when ``metadata=True`` is passed to
    :func:`pulso.load`.
    """
    return {str(col): compose_column_metadata(str(col), year, month, module) for col in df.columns}
