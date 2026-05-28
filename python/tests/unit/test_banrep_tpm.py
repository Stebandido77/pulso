import pandas as pd
import pytest

import pulso


def test_tpm_fixture_structure():
    with pytest.warns(UserWarning, match="bundled TPM snapshot"):
        df = pulso.tpm(use_fixture=True)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["fecha", "valor", "serie"]
    assert pd.api.types.is_datetime64_any_dtype(df["fecha"])
    assert pd.api.types.is_float_dtype(df["valor"])
    assert df["serie"].unique().tolist() == ["tpm"]
    assert len(df) > 5000


def test_tpm_filter_start():
    with pytest.warns(UserWarning, match="bundled TPM snapshot"):
        df = pulso.tpm(start="2020-01-01", use_fixture=True)
    assert (df["fecha"] >= pd.Timestamp("2020-01-01")).all()
    assert len(df) > 0


def test_tpm_filter_end():
    with pytest.warns(UserWarning, match="bundled TPM snapshot"):
        df = pulso.tpm(end="2015-12-31", use_fixture=True)
    assert (df["fecha"] <= pd.Timestamp("2015-12-31")).all()
    assert len(df) > 0


def test_tpm_filter_start_and_end():
    with pytest.warns(UserWarning, match="bundled TPM snapshot"):
        df = pulso.tpm(start="2022-01-01", end="2022-12-31", use_fixture=True)
    assert (df["fecha"] >= pd.Timestamp("2022-01-01")).all()
    assert (df["fecha"] <= pd.Timestamp("2022-12-31")).all()


def test_tpm_invalid_date_raises():
    with pytest.raises(ValueError, match="must be a YYYY-MM-DD string"):
        pulso.tpm(start="not-a-date", use_fixture=True)


def test_tpm_start_after_end_raises():
    with pytest.raises(ValueError, match="must be <= end"):
        pulso.tpm(start="2024-12-31", end="2024-01-01", use_fixture=True)


def test_tpm_full_range_dates():
    with pytest.warns(UserWarning, match="bundled TPM snapshot"):
        df = pulso.tpm(use_fixture=True)
    assert df["fecha"].dt.year.min() >= 2010
    assert df["fecha"].dt.year.max() >= 2025


def test_tpm_valores_positive():
    with pytest.warns(UserWarning, match="bundled TPM snapshot"):
        df = pulso.tpm(start="2023-01-01", end="2023-12-31", use_fixture=True)
    assert (df["valor"] > 0).all()
    assert df["valor"].notna().all()
