"""Tests for the aggregated unvalidated-period warning (Commit 5).

The contract: when ``strict=False`` and one or more periods loaded had
``validated=false``, exactly ONE ``UserWarning`` is emitted at the end
of the load — not N warnings (one per period).
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _make_multi_period_sources(*, validated_keys: set[str], all_keys: list[str]) -> dict[str, Any]:
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
                "checksum_sha256": ("a" * 64) if (key in validated_keys) else None,
                "modules": {"ocupados": {"cabecera": f"{key}.CSV"}},
                "validated": key in validated_keys,
            }
            for key in all_keys
        },
    }


@pytest.fixture
def setup_multi(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
):
    """Pipeline factory for multi-period unvalidated tests."""

    def _setup(*, validated_keys: set[str], all_keys: list[str]) -> None:
        import pulso._config.registry as reg
        import pulso._core.downloader as dl_mod
        import pulso._core.parser as parser_mod

        sources = _make_multi_period_sources(validated_keys=validated_keys, all_keys=all_keys)
        monkeypatch.setattr(reg, "_SOURCES", sources)
        monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setattr(dl_mod, "verify_checksum", lambda *a, **kw: True)

        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"bytes"]
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mocker.patch("requests.get", return_value=mock_response)

        sentinel = pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})
        monkeypatch.setattr(parser_mod, "parse_module", lambda *a, **kw: sentinel)

    return _setup


def test_aggregated_warning_for_multi_period(setup_multi) -> None:  # type: ignore[no-untyped-def]
    """U-1: 12 unvalidated periods → exactly 1 UserWarning, not 12."""
    import pulso

    keys = [f"2024-{m:02d}" for m in range(1, 13)]
    setup_multi(validated_keys=set(), all_keys=keys)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=None, module="ocupados", harmonize=False)

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1, (
        f"Expected exactly 1 aggregated UserWarning, got {len(user_warnings)}: "
        f"{[str(w.message) for w in user_warnings]}"
    )
    assert "12" in str(user_warnings[0].message)
    assert len(df) == 12  # one row per period


def test_aggregated_warning_message_includes_examples_and_count(setup_multi) -> None:  # type: ignore[no-untyped-def]
    """U-1: the warning message lists example periods and the unvalidated count."""
    import pulso

    keys = [f"2024-{m:02d}" for m in range(1, 13)]
    setup_multi(validated_keys=set(), all_keys=keys)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pulso.load(year=2024, month=None, module="ocupados", harmonize=False)

    msg = str(caught[-1].message)
    assert "2024-01" in msg
    assert "checksum-validated" in msg
    assert "strict=True" in msg
    assert "list_validated_range" in msg


def test_no_warning_when_all_validated(setup_multi) -> None:  # type: ignore[no-untyped-def]
    """U-1: every period validated → zero UserWarnings."""
    import pulso

    keys = [f"2024-{m:02d}" for m in range(1, 13)]
    setup_multi(validated_keys=set(keys), all_keys=keys)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=None, module="ocupados", harmonize=False)

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert user_warnings == []
    assert len(df) == 12


def test_aggregated_warning_truncates_examples(setup_multi) -> None:  # type: ignore[no-untyped-def]
    """U-1: when more than 10 unvalidated periods, message says '... and N more'."""
    import pulso

    # 24 unvalidated months across 2023-2024.
    keys = [f"{y}-{m:02d}" for y in (2023, 2024) for m in range(1, 13)]
    setup_multi(validated_keys=set(), all_keys=keys)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pulso.load(year=[2023, 2024], month=None, module="ocupados", harmonize=False)

    msg = str(caught[-1].message)
    assert "and 14 more" in msg, msg


def test_load_merged_aggregates_only_outer(setup_multi) -> None:  # type: ignore[no-untyped-def]
    """U-1: load_merged emits exactly 1 warning despite N inner load() calls per module."""
    import pulso

    # One unvalidated period, one module.
    setup_multi(validated_keys=set(), all_keys=["2024-06"])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pulso.load_merged(year=2024, month=6, modules=["ocupados"], harmonize=False)

    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1
