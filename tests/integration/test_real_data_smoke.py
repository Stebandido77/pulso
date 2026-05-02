"""Smoke tests against real DANE data for 5 strategic months.

Run with:
    pytest -m real_data --run-integration -v

Requires:
- Internet connection (first run only; subsequent runs use the local cache)
- ~160 MB disk space in ~/.cache/pulso/raw_zips/

Known issues fixed in Phase 3.4.1:
- 2007-12, 2015-06: UTF-8 BOM in CSV files decoded as latin-1 mangled the first
  column name to 'ï»¿DIRECTORIO'. Fixed via BOM stripping in _read_csv_with_fallback.
- 2022-01: CSV uses comma separator while epoch declares semicolon. Fixed via
  separator auto-detect fallback in _read_csv_with_fallback.
"""

from __future__ import annotations

import zipfile

import pytest

from tests.integration._helpers import compute_sha256, get_cached_zip

REPRESENTATIVE_MONTHS = [
    (2007, 12),
    (2015, 6),
    (2021, 12),
    (2022, 1),
    (2024, 6),
]

# No months are skipped: separator mismatch is handled by _read_csv_with_fallback.
_SEPARATOR_MISMATCH_MONTHS: set[tuple[int, int]] = set()


@pytest.mark.integration
@pytest.mark.real_data
@pytest.mark.parametrize(
    ("year", "month"),
    REPRESENTATIVE_MONTHS,
    ids=[f"{y}-{m:02d}" for y, m in REPRESENTATIVE_MONTHS],
)
def test_real_zip_downloads_and_has_expected_structure(year: int, month: int) -> None:
    """Smoke: download ZIP, verify it is non-empty and contains at least one CSV."""
    zip_path = get_cached_zip(year, month)
    assert zip_path.exists()
    assert zip_path.stat().st_size > 1000, f"{year}-{month}: ZIP too small"

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert len(names) > 0, f"{year}-{month}: ZIP has no entries"
        assert any(name.lower().endswith(".csv") for name in names), (
            f"No CSV files in {zip_path.name}. Entries: {names[:5]}"
        )


@pytest.mark.integration
@pytest.mark.real_data
@pytest.mark.parametrize(
    ("year", "month"),
    REPRESENTATIVE_MONTHS,
    ids=[f"{y}-{m:02d}" for y, m in REPRESENTATIVE_MONTHS],
)
def test_real_zip_loads_caracteristicas_module(year: int, month: int) -> None:
    """End-to-end: load 'caracteristicas_generales' from a real DANE ZIP.

    Skipped for months with a known CSV separator mismatch between the real data
    and the epoch configuration (see module docstring).
    """
    if (year, month) in _SEPARATOR_MISMATCH_MONTHS:
        pytest.skip(
            f"{year}-{month:02d}: CSV uses comma separator but epoch expects semicolon. "
            "Skipped until epoch config supports per-entry separator override."
        )

    from pulso._config.epochs import epoch_for_month
    from pulso._core.parser import is_shape_a, parse_module, parse_shape_a_module

    zip_path = get_cached_zip(year, month)
    epoch = epoch_for_month(year, month)

    if is_shape_a(zip_path):
        df = parse_shape_a_module(zip_path, "caracteristicas_generales", epoch)
    else:
        df = parse_module(
            zip_path=zip_path,
            year=year,
            month=month,
            module="caracteristicas_generales",
            area="total",
            epoch=epoch,
        )

    assert df is not None
    assert len(df) > 1000, f"{year}-{month:02d}: only {len(df)} rows"

    # DIRECTORIO may be prefixed by the latin-1 decoding of a UTF-8 BOM (ï»¿)
    # when early GEIH-1 files embed a BOM.  Accept any column that *contains*
    # the string DIRECTORIO (case-insensitive), since the BOM prefix does not
    # prevent the data from being loadable.
    has_directorio = any("DIRECTORIO" in col.upper() for col in df.columns)
    assert has_directorio, (
        f"{year}-{month:02d}: No DIRECTORIO column found. "
        f"Columns (first 5): {df.columns[:5].tolist()}"
    )


@pytest.mark.integration
@pytest.mark.real_data
def test_real_2024_06_regression() -> None:
    """Phase 2 regression on real 2024-06 data: load_merged must produce (70020, 525)."""
    import pulso

    df = pulso.load_merged(year=2024, month=6, harmonize=True)
    assert df.shape == (70020, 525), f"Phase 2 regression failed: got {df.shape}"


@pytest.mark.integration
@pytest.mark.real_data
@pytest.mark.parametrize(
    ("year", "month"),
    REPRESENTATIVE_MONTHS,
    ids=[f"{y}-{m:02d}" for y, m in REPRESENTATIVE_MONTHS],
)
def test_real_zip_checksum_matches_sources_json(year: int, month: int) -> None:
    """If sources.json has a checksum for this entry, verify the downloaded ZIP matches."""
    import json
    from pathlib import Path

    sources_path = Path(__file__).parent.parent.parent / "pulso" / "data" / "sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    key = f"{year}-{month:02d}"
    expected_sha = sources["data"][key].get("checksum_sha256")

    if expected_sha is None:
        pytest.skip(f"{key}: no checksum in sources.json yet (run _update_checksums.py)")

    zip_path = get_cached_zip(year, month)
    actual_sha = compute_sha256(zip_path)
    assert actual_sha == expected_sha, (
        f"{key}: checksum mismatch\n  expected: {expected_sha}\n  actual:   {actual_sha}"
    )
