"""Tests for the new validation helpers (Commit 9).

- list_validated_range() → sorted list[(year, month)] for validated entries
- validation_status() → DataFrame with full registry status
"""

from __future__ import annotations

import pandas as pd


def test_list_validated_range_returns_sorted_tuples() -> None:
    import pulso

    pairs = pulso.list_validated_range()
    assert isinstance(pairs, list)
    for p in pairs:
        assert isinstance(p, tuple)
        assert len(p) == 2
        assert isinstance(p[0], int)
        assert isinstance(p[1], int)
    assert pairs == sorted(pairs)


def test_list_validated_range_returns_only_validated_entries() -> None:
    """Every (y, m) returned must have validated=true in sources.json."""
    import json
    from pathlib import Path

    import pulso

    sources_path = Path(__file__).parent.parent.parent / "pulso" / "data" / "sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    expected = sorted(
        (int(k[:4]), int(k[5:7])) for k, v in sources["data"].items() if v.get("validated")
    )
    assert pulso.list_validated_range() == expected


def test_validation_status_dataframe_columns() -> None:
    import pulso

    df = pulso.validation_status()
    assert isinstance(df, pd.DataFrame)
    expected = {
        "year",
        "month",
        "validated",
        "checksum_sha256",
        "validated_at",
        "modules",
    }
    assert expected.issubset(set(df.columns))


def test_validation_status_total_count_matches_sources() -> None:
    """validation_status() row count equals the number of entries in sources.json."""
    import json
    from pathlib import Path

    import pulso

    sources_path = Path(__file__).parent.parent.parent / "pulso" / "data" / "sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    expected_n = len(sources["data"])
    assert len(pulso.validation_status()) == expected_n


def test_validation_status_validated_count_matches_listing() -> None:
    """sum(df.validated) must equal len(list_validated_range())."""
    import pulso

    df = pulso.validation_status()
    assert int(df["validated"].sum()) == len(pulso.list_validated_range())


def test_validation_status_uses_validated_at_field_name() -> None:
    """The column is `validated_at` to match sources.schema.json (not `last_validated_at`)."""
    import pulso

    df = pulso.validation_status()
    assert "validated_at" in df.columns
    assert "last_validated_at" not in df.columns


def test_validation_status_unvalidated_entries_have_null_checksum() -> None:
    """Spot check: rows where validated=False must have checksum=None in production."""
    import pulso

    df = pulso.validation_status()
    unvalidated = df[~df["validated"]]
    if len(unvalidated) > 0:
        # In production every unvalidated row has checksum=None
        assert all(unvalidated["checksum_sha256"].isna())


def test_helpers_exported_at_top_level() -> None:
    import pulso

    assert "list_validated_range" in pulso.__all__
    assert "validation_status" in pulso.__all__
    assert callable(pulso.list_validated_range)
    assert callable(pulso.validation_status)
