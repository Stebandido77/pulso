"""Decimal-mark detection for DANE CSVs (#77)."""

from __future__ import annotations

import pandas as pd

from pulso._core.parser import _sniff_decimal

POINT = b"DIRECTORIO;DPTO;FEX_C18\n8713327;08;43.55418099\n8713328;08;34.68595437\n"
COMMA = b"DIRECTORIO;DPTO;FEX_C18\n8713327;08;43,55418099\n8713328;08;34,68595437\n"


def test_point_decimal_with_semicolon_sep() -> None:
    assert _sniff_decimal(POINT, ";", ",") == "."


def test_comma_decimal_with_semicolon_sep() -> None:
    assert _sniff_decimal(COMMA, ";", ".") == ","


def test_no_decimals_falls_back_to_epoch_default() -> None:
    assert _sniff_decimal(b"A;B\n1;2\n", ";", ",") == ","


def test_comma_separator_always_uses_point() -> None:
    assert _sniff_decimal(b"A,B\n1,2\n", ",", ",") == "."


def test_point_file_parses_numeric_weight() -> None:
    import io

    df = pd.read_csv(io.BytesIO(POINT), sep=";", decimal=_sniff_decimal(POINT, ";", ","))
    assert pd.api.types.is_float_dtype(df["FEX_C18"])
