"""Tests for the aggregated harmonization-skipping warning (Fix 2).

The contract: when ``load`` / ``load_merged`` harmonizes data and one or
more canonical variables fail to harmonize across one or more periods,
exactly ONE ``UserWarning`` is emitted at the end — not N (one per
variable per period). The transient ``df.attrs['_skipped_variables']``
key is removed before returning.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _make_sources(*, all_keys: list[str]) -> dict[str, Any]:
    """All entries validated so the unvalidated-warning path is silent."""
    return {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Ocu",
                "description_en": "Ocu",
                "available_in": ["geih_2021_present"],
            }
        },
        "data": {
            key: {
                "epoch": "geih_2021_present",
                "download_url": f"https://example.com/{key}.zip",
                "checksum_sha256": "a" * 64,
                "modules": {"ocupados": {"file": f"{key}.CSV"}},
                "validated": True,
            }
            for key in all_keys
        },
    }


@pytest.fixture
def setup_harmonize_load(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
):
    """Pipeline factory: stubs everything below ``harmonize_dataframe``.

    The synthetic parsed DataFrame has only a couple of source columns,
    so most canonical variables fail to harmonize (their source vars are
    missing). That's the trigger for the aggregated skip warning.
    """

    def _setup(*, all_keys: list[str]) -> None:
        import pulso._config.registry as reg
        import pulso._core.downloader as dl_mod
        import pulso._core.parser as parser_mod

        sources = _make_sources(all_keys=all_keys)
        monkeypatch.setattr(reg, "_SOURCES", sources)
        monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setattr(dl_mod, "verify_checksum", lambda *a, **kw: True)

        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"bytes"]
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mocker.patch("requests.get", return_value=mock_response)

        # Synthetic parsed module: only has the merge keys + age column.
        # Most canonical variables in variable_map.json will fail to
        # harmonize because their source columns are absent.
        sentinel = pd.DataFrame(
            {
                "DIRECTORIO": ["1", "2"],
                "SECUENCIA_P": ["1", "1"],
                "ORDEN": ["1", "1"],
                "P6040": [25, 30],  # source for `edad`
            }
        )
        monkeypatch.setattr(parser_mod, "parse_module", lambda *a, **kw: sentinel)

    return _setup


# ---------------------------------------------------------------------------
# load() aggregation
# ---------------------------------------------------------------------------


def test_load_single_period_emits_one_aggregated_skip_warning(
    setup_harmonize_load,  # type: ignore[no-untyped-def]
) -> None:
    """A single-period load with many missing source vars emits exactly ONE
    aggregated UserWarning (not one per skipped canonical)."""
    import pulso

    setup_harmonize_load(all_keys=["2024-06"])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=6, module="ocupados", harmonize=True)

    skipping_warnings = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "skipped during harmonization" in str(w.message)
    ]
    assert len(skipping_warnings) == 1, (
        f"Expected 1 aggregated skip warning, got {len(skipping_warnings)}: "
        f"{[str(w.message) for w in skipping_warnings]}"
    )
    msg = str(skipping_warnings[0].message)
    # Message contains the count and the suggested follow-up.
    assert "canonical variable(s) skipped" in msg
    assert "1 period(s)" in msg
    assert "list_variables" in msg

    # Transient channel must NOT leak to the user.
    assert "_skipped_variables" not in df.attrs


def test_load_multi_period_aggregates_to_one_warning(
    setup_harmonize_load,  # type: ignore[no-untyped-def]
) -> None:
    """10-period load → 1 aggregated UserWarning (not 10)."""
    import pulso

    keys = [f"2024-{m:02d}" for m in range(1, 11)]
    setup_harmonize_load(all_keys=keys)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=range(1, 11), module="ocupados", harmonize=True)

    skipping_warnings = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "skipped during harmonization" in str(w.message)
    ]
    assert len(skipping_warnings) == 1, (
        f"Expected 1 aggregated warning across 10 periods, got {len(skipping_warnings)}"
    )
    assert "10 period(s)" in str(skipping_warnings[0].message)
    assert "_skipped_variables" not in df.attrs


def test_load_aggregated_message_truncates_examples(
    setup_harmonize_load,  # type: ignore[no-untyped-def]
) -> None:
    """The aggregated message lists at most 5 example variables, then '... and N more'."""
    import pulso

    setup_harmonize_load(all_keys=["2024-06"])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pulso.load(year=2024, month=6, module="ocupados", harmonize=True)

    skipping_warnings = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "skipped during harmonization" in str(w.message)
    ]
    msg = str(skipping_warnings[0].message)
    # variable_map has 30 canonicals; 1 (edad) succeeds → ~29 skipped.
    # That's >>5, so the truncation suffix must be present.
    assert "and " in msg
    assert "more" in msg


def test_load_no_skip_when_harmonize_false(
    setup_harmonize_load,  # type: ignore[no-untyped-def]
) -> None:
    """harmonize=False → no harmonization → no aggregated skip warning."""
    import pulso

    setup_harmonize_load(all_keys=["2024-06"])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=6, module="ocupados", harmonize=False)

    skipping_warnings = [w for w in caught if "skipped during harmonization" in str(w.message)]
    assert skipping_warnings == []
    assert "_skipped_variables" not in df.attrs


# ---------------------------------------------------------------------------
# load_merged() aggregation
# ---------------------------------------------------------------------------


def test_load_merged_aggregates_skipped_variables(
    setup_harmonize_load,  # type: ignore[no-untyped-def]
) -> None:
    """load_merged emits exactly ONE aggregated skip warning per call."""
    import pulso

    setup_harmonize_load(all_keys=["2024-06"])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load_merged(year=2024, month=6, modules=["ocupados"], harmonize=True)

    skipping_warnings = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "skipped during harmonization" in str(w.message)
    ]
    assert len(skipping_warnings) == 1
    assert "_skipped_variables" not in df.attrs


# ---------------------------------------------------------------------------
# harmonize_dataframe direct: only sets attrs, never warns
# ---------------------------------------------------------------------------


def test_harmonize_dataframe_does_not_emit_warnings_directly() -> None:
    """The harmonizer itself never emits per-variable warnings; it only
    populates the transient ``_skipped_variables`` channel.
    """
    from unittest.mock import MagicMock

    from pulso._core.harmonizer import harmonize_dataframe

    epoch = MagicMock()
    epoch.key = "geih_2021_present"
    df = pd.DataFrame({"P6040": [25, 30]})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = harmonize_dataframe(df, epoch)

    assert caught == []
    # But the transient channel is populated.
    assert "_skipped_variables" in result.attrs
    skipped = result.attrs["_skipped_variables"]
    assert isinstance(skipped, list)
    assert len(skipped) > 0
