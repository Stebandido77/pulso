"""Unit tests for pulso._core.harmonizer."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pulso._core.harmonizer import (
    harmonize_dataframe,
    harmonize_variable,
)
from pulso._utils.exceptions import ConfigError, HarmonizationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _epoch(key: str = "geih_2021_present") -> MagicMock:
    e = MagicMock()
    e.key = key
    return e


def _var_entry(
    var_type: str = "numeric",
    source: str | list = "COL",
    transform: str | dict = "identity",
    categories: dict | None = None,
    epoch_key: str = "geih_2021_present",
) -> dict:
    entry: dict = {
        "type": var_type,
        "mappings": {
            epoch_key: {
                "source_variable": source,
                "transform": transform,
            }
        },
    }
    if categories:
        entry["categories"] = categories
    return entry


# ---------------------------------------------------------------------------
# identity / rename
# ---------------------------------------------------------------------------


def test_identity_basic() -> None:
    df = pd.DataFrame({"COL": [1, 2, 3]})
    entry = _var_entry(source="COL", transform="identity")
    s = harmonize_variable(df, "myvar", entry, _epoch())
    pd.testing.assert_series_equal(s, pd.Series([1, 2, 3], name="myvar"))


def test_identity_preserves_nulls() -> None:
    df = pd.DataFrame({"COL": [1.0, float("nan"), 3.0]})
    entry = _var_entry(source="COL", transform="identity")
    s = harmonize_variable(df, "myvar", entry, _epoch())
    assert s.isna().sum() == 1


def test_identity_rejects_list_source_variable() -> None:
    df = pd.DataFrame({"A": [1], "B": [2]})
    entry = _var_entry(source=["A", "B"], transform="identity")
    with pytest.raises(ConfigError, match="single source_variable"):
        harmonize_variable(df, "myvar", entry, _epoch())


def test_identity_raises_on_missing_column() -> None:
    df = pd.DataFrame({"OTHER": [1, 2]})
    entry = _var_entry(source="COL", transform="identity")
    with pytest.raises(HarmonizationError, match="source columns missing"):
        harmonize_variable(df, "myvar", entry, _epoch())


# ---------------------------------------------------------------------------
# recode
# ---------------------------------------------------------------------------


def test_recode_string_keys_with_int_source() -> None:
    df = pd.DataFrame({"CLASE": [1, 2, 3]})
    mapping = {"1": "cabecera", "2": "centro_poblado", "3": "rural_disperso"}
    entry = _var_entry(source="CLASE", transform={"op": "recode", "mapping": mapping})
    s = harmonize_variable(df, "area", entry, _epoch())
    assert list(s) == ["cabecera", "centro_poblado", "rural_disperso"]


def test_recode_preserves_nulls() -> None:
    df = pd.DataFrame({"CLASE": pd.array([1, None, 3], dtype="Int64")})
    mapping = {"1": "cabecera", "2": "cp", "3": "rural"}
    entry = _var_entry(source="CLASE", transform={"op": "recode", "mapping": mapping})
    s = harmonize_variable(df, "area", entry, _epoch())
    assert pd.isna(s.iloc[1])
    assert s.iloc[0] == "cabecera"
    assert s.iloc[2] == "rural"


def test_recode_raises_on_unmapped_value_when_no_default() -> None:
    df = pd.DataFrame({"CLASE": [1, 99]})
    mapping = {"1": "cabecera"}
    entry = _var_entry(source="CLASE", transform={"op": "recode", "mapping": mapping})
    with pytest.raises(HarmonizationError, match="recode mapping does not cover"):
        harmonize_variable(df, "area", entry, _epoch())


def test_recode_uses_default_when_provided() -> None:
    df = pd.DataFrame({"CLASE": [1, 99]})
    mapping = {"1": "cabecera"}
    entry = _var_entry(
        source="CLASE",
        transform={"op": "recode", "mapping": mapping, "default": "otro"},
    )
    s = harmonize_variable(df, "area", entry, _epoch())
    assert s.iloc[1] == "otro"


# ---------------------------------------------------------------------------
# compute
# ---------------------------------------------------------------------------


def test_compute_arithmetic_expression() -> None:
    df = pd.DataFrame({"A": [10, 20, 30], "B": [1, 2, 3]})
    entry = _var_entry(source=["A", "B"], transform={"op": "compute", "expr": "A + B"})
    s = harmonize_variable(df, "total", entry, _epoch())
    assert list(s) == [11, 22, 33]


def test_compute_boolean_expression() -> None:
    df = pd.DataFrame({"P6440": [1, 2, 1]})
    entry = _var_entry(
        var_type="boolean",
        source="P6440",
        transform={"op": "compute", "expr": "P6440 == 1"},
    )
    s = harmonize_variable(df, "tiene_contrato", entry, _epoch())
    assert s.dtype == pd.BooleanDtype()
    assert list(s) == [True, False, True]


def test_compute_string_concat_for_hogar_id() -> None:
    df = pd.DataFrame({"DIRECTORIO": [1], "SECUENCIA_P": [2], "HOGAR": [3]})
    expr = "DIRECTORIO.astype(str) + '_' + SECUENCIA_P.astype(str) + '_' + HOGAR.astype(str)"
    entry = _var_entry(
        var_type="string",
        source=["DIRECTORIO", "SECUENCIA_P", "HOGAR"],
        transform={"op": "compute", "expr": expr},
    )
    s = harmonize_variable(df, "hogar_id", entry, _epoch())
    assert s.iloc[0] == "1_2_3"


def test_compute_raises_on_invalid_expression() -> None:
    df = pd.DataFrame({"COL": [1, 2]})
    entry = _var_entry(source="COL", transform={"op": "compute", "expr": "NONEXISTENT_COL * 2"})
    with pytest.raises(HarmonizationError, match="compute expression"):
        harmonize_variable(df, "myvar", entry, _epoch())


# ---------------------------------------------------------------------------
# cast
# ---------------------------------------------------------------------------


def test_cast_to_int_uses_nullable_Int64() -> None:
    df = pd.DataFrame({"COL": [1.0, 2.0, float("nan")]})
    entry = _var_entry(source="COL", transform={"op": "cast", "to": "int"})
    s = harmonize_variable(df, "myvar", entry, _epoch())
    assert s.dtype == pd.Int64Dtype()
    assert pd.isna(s.iloc[2])


def test_cast_to_str() -> None:
    df = pd.DataFrame({"COL": [1, 2, 3]})
    entry = _var_entry(source="COL", transform={"op": "cast", "to": "str"})
    s = harmonize_variable(df, "myvar", entry, _epoch())
    assert s.dtype == pd.StringDtype()


def test_cast_raises_on_uncastable_value() -> None:
    df = pd.DataFrame({"COL": ["abc", "def"]})
    entry = _var_entry(source="COL", transform={"op": "cast", "to": "int"})
    with pytest.raises(HarmonizationError, match="cast to"):
        harmonize_variable(df, "myvar", entry, _epoch())


# ---------------------------------------------------------------------------
# coalesce
# ---------------------------------------------------------------------------


def test_coalesce_left_to_right() -> None:
    df = pd.DataFrame(
        {
            "A": [1, None, None],
            "B": [None, 2, None],
            "C": [None, None, 3],
        }
    )
    entry = _var_entry(source=["A", "B", "C"], transform={"op": "coalesce"})
    s = harmonize_variable(df, "myvar", entry, _epoch())
    assert list(s.fillna(-1)) == [1, 2, 3]


def test_coalesce_all_null_returns_null() -> None:
    df = pd.DataFrame(
        {
            "A": [None, None],
            "B": [None, None],
        }
    )
    entry = _var_entry(source=["A", "B"], transform={"op": "coalesce"})
    s = harmonize_variable(df, "myvar", entry, _epoch())
    assert s.isna().all()


# ---------------------------------------------------------------------------
# custom dispatch
# ---------------------------------------------------------------------------


def test_custom_dispatches_to_registered() -> None:
    from pulso._core.harmonizer_funcs import CUSTOM_FUNCTIONS

    assert "bin_edad_quinquenal" in CUSTOM_FUNCTIONS
    assert "merge_labor_status" in CUSTOM_FUNCTIONS
    assert "compute_ingreso_total" in CUSTOM_FUNCTIONS

    df = pd.DataFrame({"P6040": [0, 10, 20, 30, 70]})
    entry = _var_entry(source="P6040", transform={"op": "custom", "name": "bin_edad_quinquenal"})
    s = harmonize_variable(df, "grupo_edad", entry, _epoch())
    assert list(s) == ["0-4", "10-14", "20-24", "30-34", "65+"]


def test_custom_raises_on_unknown_name() -> None:
    df = pd.DataFrame({"COL": [1]})
    entry = _var_entry(source="COL", transform={"op": "custom", "name": "nonexistent_fn"})
    with pytest.raises(ConfigError, match="not registered"):
        harmonize_variable(df, "myvar", entry, _epoch())


# ---------------------------------------------------------------------------
# categorical validation
# ---------------------------------------------------------------------------


def test_categorical_validation_passes_for_valid_codes() -> None:
    df = pd.DataFrame({"P3271": [1, 2, 1]})
    entry = _var_entry(
        var_type="categorical",
        source="P3271",
        transform="identity",
        categories={"1": "hombre", "2": "mujer"},
    )
    s = harmonize_variable(df, "sexo", entry, _epoch())
    # Categorical identity results are normalised to canonical string form
    assert list(s) == ["1", "2", "1"]


def test_categorical_validation_raises_on_out_of_domain() -> None:
    df = pd.DataFrame({"P3271": [1, 2, 99]})
    entry = _var_entry(
        var_type="categorical",
        source="P3271",
        transform="identity",
        categories={"1": "hombre", "2": "mujer"},
    )
    with pytest.raises(HarmonizationError, match="out-of-domain"):
        harmonize_variable(df, "sexo", entry, _epoch())


# ---------------------------------------------------------------------------
# harmonize_dataframe
# ---------------------------------------------------------------------------


def test_harmonize_dataframe_skips_unavailable_variables(caplog: pytest.LogCaptureFixture) -> None:
    """Variables with missing source columns are skipped with a warning."""
    df = pd.DataFrame({"P6040": [25, 30, 45]})
    epoch = _epoch(key="geih_2021_present")

    with caplog.at_level(logging.WARNING, logger="pulso._core.harmonizer"):
        result = harmonize_dataframe(df, epoch)

    assert "P6040" in result.columns
    assert "edad" in result.columns
    skipped_vars = [rec.message for rec in caplog.records if "Skipping" in rec.message]
    assert len(skipped_vars) > 0


def test_harmonize_dataframe_named_variables_only() -> None:
    """When variables= is specified, only those are attempted."""
    df = pd.DataFrame({"P6040": [25, 30], "P3271": [1, 2]})
    epoch = _epoch(key="geih_2021_present")

    result = harmonize_dataframe(df, epoch, variables=["edad"])
    assert "edad" in result.columns
    assert "sexo" not in result.columns


def test_harmonize_dataframe_preserves_raw_columns_by_default() -> None:
    """Raw DANE columns must coexist with canonical columns (Decision 9)."""
    df = pd.DataFrame({"P6040": [25, 30, 45], "EXTRA_COL": ["a", "b", "c"]})
    epoch = _epoch(key="geih_2021_present")

    result = harmonize_dataframe(df, epoch)
    assert "P6040" in result.columns, "Raw column must be preserved"
    assert "EXTRA_COL" in result.columns, "Unrelated raw column must be preserved"
    assert "edad" in result.columns, "Canonical column must be added"


def test_harmonize_dataframe_keep_raw_false_returns_only_canonical() -> None:
    df = pd.DataFrame({"P6040": [25, 30, 45], "EXTRA_COL": ["a", "b", "c"]})
    epoch = _epoch(key="geih_2021_present")

    result = harmonize_dataframe(df, epoch, keep_raw=False)
    assert "P6040" not in result.columns
    assert "EXTRA_COL" not in result.columns
    assert "edad" in result.columns


def test_harmonize_variable_no_mapping_for_epoch_raises() -> None:
    df = pd.DataFrame({"COL": [1]})
    entry = _var_entry(source="COL", transform="identity", epoch_key="geih_2006_2020")
    with pytest.raises(ConfigError, match="no mapping for epoch"):
        harmonize_variable(df, "myvar", entry, _epoch("nonexistent_epoch"))


# ---------------------------------------------------------------------------
# Bug fixes: float-encoded integer handling (Bug 2, 2026-04-29)
# ---------------------------------------------------------------------------


def test_recode_handles_float_source() -> None:
    """Recode keys are JSON strings; source read by pandas as float64 must match."""
    import numpy as np

    df = pd.DataFrame({"CLASE": [1.0, 2.0, 3.0, np.nan]})
    mapping = {"1": "cabecera", "2": "centro_poblado", "3": "rural_disperso"}
    entry = _var_entry(source="CLASE", transform={"op": "recode", "mapping": mapping})
    s = harmonize_variable(df, "area", entry, _epoch())
    assert s.iloc[0] == "cabecera"
    assert s.iloc[1] == "centro_poblado"
    assert s.iloc[2] == "rural_disperso"
    assert pd.isna(s.iloc[3])


def test_categorical_validation_handles_float_source() -> None:
    """Float-encoded ints (pandas CSV-with-NaN artefact) pass categorical validation."""
    import numpy as np

    df = pd.DataFrame({"P6070": [1.0, 2.0, np.nan, 1.0, 2.0]})
    entry = _var_entry(
        var_type="categorical",
        source="P6070",
        transform="identity",
        categories={"1": "casado", "2": "union_libre"},
    )
    s = harmonize_variable(df, "estado_civil", entry, _epoch())
    assert s.notna().sum() == 4
    # Canonical form must be "1" / "2", not "1.0" / "2.0"
    valid = set(s.dropna().unique().tolist())
    assert valid.issubset({"1", "2"}), f"Expected canonical string codes, got {valid}"
