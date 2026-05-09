"""Unit tests for ``pulso.metadata.composer``.

Covers Curator-only / codebook-only / merged / missing paths plus the
case-insensitive AREA-vs-Area lookup and the dataframe-level helper.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pulso.metadata import composer
from pulso.metadata.composer import (
    compose_column_metadata,
    compose_dataframe_metadata,
)


@pytest.fixture(autouse=True)
def _reset_composer_caches() -> None:
    """Force the composer to reload its JSON inputs for each test."""
    composer._reset_caches_for_tests()
    yield
    composer._reset_caches_for_tests()


def test_compose_curator_only_canonical_name() -> None:
    """Canonical Spanish name like ``sexo`` resolves Curator-only."""
    meta = compose_column_metadata("sexo", year=2024, month=6, module="ocupados")
    assert meta["source"] == "curator"
    assert meta["canonical_name"] == "sexo"
    assert meta["dane_code"] == "P3271"
    cats = meta.get("categories")
    assert isinstance(cats, dict)
    assert cats.get("1") == "hombre"
    assert cats.get("2") == "mujer"
    assert meta["module"] == "caracteristicas_generales"
    # Curator path must NOT inject codebook-only fields.
    assert meta["question_text"] is None
    assert meta["universe"] is None


def test_compose_codebook_only_dane_code() -> None:
    """``FT`` (Fuerza de trabajo) is in the codebook but not in any Curator mapping."""
    meta = compose_column_metadata("FT", year=2024, month=6, module="ocupados")
    assert meta["source"] == "codebook"
    assert meta["canonical_name"] is None
    assert meta["dane_code"] == "FT"
    assert meta["label"] is not None
    assert meta["label"] != ""


def test_compose_merged_p3271_curator_wins_categories() -> None:
    """``P3271`` (sex in GEIH-2) is referenced by Curator → merged path."""
    meta = compose_column_metadata("P3271", year=2024, month=6, module="ocupados")
    assert meta["source"] == "merged"
    assert meta["canonical_name"] == "sexo"
    assert meta["dane_code"] == "P3271"
    cats = meta.get("categories") or {}
    # Curator categories win, lower-case "hombre"/"mujer".
    assert cats.get("1") == "hombre"
    assert cats.get("2") == "mujer"
    # Codebook still supplies question_text/universe.
    assert meta["question_text"] is not None


def test_compose_merged_p6020_curator_wins_categories() -> None:
    """``P6020`` is the GEIH-1 sex code; Curator's mapping covers 2018."""
    meta = compose_column_metadata("P6020", year=2018, month=6, module="ocupados")
    assert meta["source"] == "merged"
    assert meta["canonical_name"] == "sexo"
    cats = meta.get("categories") or {}
    assert cats.get("1") == "hombre"
    assert cats.get("2") == "mujer"


def test_compose_missing_unknown_column() -> None:
    """A wholly unknown column is ``source='missing'`` with empty fields."""
    meta = compose_column_metadata("FOOBAR", year=2024, month=6, module="ocupados")
    assert meta["source"] == "missing"
    assert meta["canonical_name"] is None
    assert meta["dane_code"] is None
    assert meta["label"] is None
    assert meta["categories"] is None


def test_compose_case_insensitive_area() -> None:
    """``Area`` and ``AREA`` resolve to the same codebook entry."""
    meta_upper = compose_column_metadata("AREA", year=2024, month=6, module="ocupados")
    meta_mixed = compose_column_metadata("Area", year=2024, month=6, module="ocupados")
    # Both must yield a present codebook entry (source codebook OR merged).
    assert meta_upper["source"] in {"codebook", "merged"}
    assert meta_mixed["source"] in {"codebook", "merged"}
    # The label should be present for both lookups.
    assert meta_upper.get("label") is not None
    assert meta_mixed.get("label") is not None


def test_compose_case_insensitive_clase() -> None:
    """``CLASE`` (canonical Curator) maps; ``Clase`` resolves via case-insensitive lookup."""
    meta_upper = compose_column_metadata("CLASE", year=2024, month=6, module="ocupados")
    meta_mixed = compose_column_metadata("Clase", year=2024, month=6, module="ocupados")
    assert meta_upper["source"] in {"codebook", "merged"}
    assert meta_mixed["source"] in {"codebook", "merged"}


def test_compose_skeletal_variable() -> None:
    """``P3044S2`` is skeletal: label == code, no categories, no question_text."""
    meta = compose_column_metadata("P3044S2", year=2024, month=6, module="ocupados")
    assert meta["source"] == "codebook"
    label = meta.get("label")
    # Either None or literally the column name itself — both qualify as
    # "skeletal" for the API renderer.
    assert label is None or label == "P3044S2"
    assert meta.get("categories") is None
    assert meta.get("question_text") is None
    assert meta.get("universe") is None


def test_compose_dataframe_metadata_realistic_columns() -> None:
    """``compose_dataframe_metadata`` covers each path on a synthetic frame."""
    df = pd.DataFrame(
        {
            "sexo": [1, 2, 1],
            "P6020": [1, 2, 1],
            "P3044S2": [10, 20, 30],
            "FOOBAR": ["x", "y", "z"],
        }
    )
    meta = compose_dataframe_metadata(df, year=2018, month=6, module="ocupados")
    assert set(meta) == {"sexo", "P6020", "P3044S2", "FOOBAR"}
    assert meta["sexo"]["source"] == "curator"
    assert meta["P6020"]["source"] == "merged"
    assert meta["P3044S2"]["source"] == "codebook"
    assert meta["FOOBAR"]["source"] == "missing"


def test_compose_preserves_tildes() -> None:
    """The composer must not strip non-ASCII characters from labels/text."""
    # OCI is merged (Curator references it). Verify tildes survive in the
    # merged output's question_text (codebook contribution).
    meta = compose_column_metadata("OCI", year=2024, month=6, module="ocupados")
    text = (meta.get("question_text") or "") + " " + (meta.get("label") or "")
    text += " " + (meta.get("description_es") or "")
    text += " " + (meta.get("universe") or "")
    assert any(ch in text for ch in "óíáéúñ"), (
        f"Expected non-ASCII Spanish char somewhere in OCI metadata: {meta!r}"
    )


def test_compose_module_argument_preserved_for_curator() -> None:
    """Curator path always reports ``module`` from ``variable_map.json``."""
    # Even if caller asks 'ocupados', sexo's curator entry says
    # 'caracteristicas_generales'. We surface Curator's value, not the
    # caller's, because that's the canonical answer.
    meta = compose_column_metadata("sexo", year=2024, month=6, module="ocupados")
    assert meta["module"] == "caracteristicas_generales"


def test_compose_epoch_resolution() -> None:
    """The composer reuses the existing epoch resolver."""
    meta_old = compose_column_metadata("P6020", year=2018, month=6, module="ocupados")
    meta_new = compose_column_metadata("P3271", year=2024, month=6, module="ocupados")
    assert meta_old["epoch"] == "geih_2006_2020"
    assert meta_new["epoch"] == "geih_2021_present"
