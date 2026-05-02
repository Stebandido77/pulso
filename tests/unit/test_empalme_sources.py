"""Unit tests for pulso/data/empalme_sources.json and its schema.

Validates catalog coverage, IDNO patterns, the 2020 anomaly, and
the 2013 filename typo.  The integration-marked test verifies that all
active download URLs are still reachable via HTTP HEAD.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import jsonschema
import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(scope="module")
def empalme_data(data_dir: Path) -> dict:
    with (data_dir / "empalme_sources.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def empalme_schema(schemas_dir: Path) -> dict:
    with (schemas_dir / "empalme_sources.schema.json").open(encoding="utf-8") as f:
        return json.load(f)


def test_schema_validates_empalme_sources(empalme_data: dict, empalme_schema: dict) -> None:
    """empalme_sources.json must validate against empalme_sources.schema.json."""
    jsonschema.validate(instance=empalme_data, schema=empalme_schema)


def test_all_11_years_present(empalme_data: dict) -> None:
    """All years 2010-2020 must be present as keys under data."""
    expected = {str(y) for y in range(2010, 2021)}
    actual = set(empalme_data["data"].keys())
    assert actual == expected, (
        f"Missing years: {expected - actual}, unexpected: {actual - expected}"
    )


def test_idno_2020_anomaly(empalme_data: dict) -> None:
    """2020 IDNO must be the truncated variant (missing 'ME')."""
    assert empalme_data["data"]["2020"]["idno"] == "DANE-DIMPE-GEIH-EMPAL-2020"


def test_idno_pattern_other_years(empalme_data: dict) -> None:
    """2010-2019 IDNOs must follow DANE-DIMPE-GEIH-EMPALME-{year}."""
    for year in range(2010, 2020):
        entry = empalme_data["data"][str(year)]
        expected = f"DANE-DIMPE-GEIH-EMPALME-{year}"
        assert entry["idno"] == expected, (
            f"Year {year}: expected {expected!r}, got {entry['idno']!r}"
        )


def test_2020_not_downloadable(empalme_data: dict) -> None:
    """2020 must have downloadable=False, null download_url, and null zip_filename."""
    entry = empalme_data["data"]["2020"]
    assert entry["downloadable"] is False
    assert entry["download_url"] is None
    assert entry["zip_filename"] is None
    assert entry["size_bytes"] is None


def test_2010_to_2019_downloadable(empalme_data: dict) -> None:
    """Entries 2010-2019 must all be downloadable with non-null URLs and sizes."""
    for year in range(2010, 2020):
        entry = empalme_data["data"][str(year)]
        assert entry["downloadable"] is True, f"Year {year}: expected downloadable=True"
        assert entry["download_url"] is not None, f"Year {year}: download_url must not be null"
        assert entry["size_bytes"] is not None, f"Year {year}: size_bytes must not be null"
        assert entry["size_bytes"] > 0, f"Year {year}: size_bytes must be positive"


def test_download_url_pattern(empalme_data: dict) -> None:
    """Active download URLs must follow the expected DANE catalog/download pattern."""
    base = "https://microdatos.dane.gov.co/index.php/catalog/"
    for year in range(2010, 2020):
        url = empalme_data["data"][str(year)]["download_url"]
        assert url.startswith(base), f"Year {year}: unexpected URL prefix: {url}"
        assert "/download/" in url, f"Year {year}: URL missing /download/ segment: {url}"


def test_2013_typo_documented(empalme_data: dict) -> None:
    """2013 ZIP filename must preserve DANE's typo and document it in notes."""
    entry = empalme_data["data"]["2013"]
    assert entry["zip_filename"] == "GEIH_Emplame_2013.zip", (
        "2013 filename must keep DANE's typo ('Emplame' not 'Empalme')"
    )
    assert entry["notes"] is not None, "2013 notes must not be null"
    assert "typo" in entry["notes"].lower(), "2013 notes must document the filename typo"


def test_schema_version(empalme_data: dict) -> None:
    """Schema version must start at 1.0."""
    assert empalme_data["metadata"]["schema_version"] == "1.0"


def test_catalog_ids_are_unique(empalme_data: dict) -> None:
    """Each year must have a distinct catalog_id."""
    ids = [entry["catalog_id"] for entry in empalme_data["data"].values()]
    assert len(ids) == len(set(ids)), f"Duplicate catalog_ids: {ids}"


@pytest.mark.integration
def test_download_urls_resolvable(empalme_data: dict) -> None:
    """All active download URLs must return HTTP 200 with Content-Length > 0."""
    import urllib.request

    for year in range(2010, 2020):
        entry = empalme_data["data"][str(year)]
        url = entry["download_url"]
        req = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "pulso-curator/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            assert resp.status == 200, f"Year {year}: expected 200, got {resp.status} for {url}"
            content_length = int(resp.headers.get("Content-Length", 0))
            assert content_length == entry["size_bytes"], (
                f"Year {year}: Content-Length {content_length} != "
                f"recorded size_bytes {entry['size_bytes']}"
            )
