"""Tests for the new ``strict`` parameter (Commit 4) — replaces the deprecated
``allow_unvalidated``.

Covers:
- 4 quadrants of {strict True/False} x {validated True/False} (G-3)
- Backward compat: allow_unvalidated still works with DeprecationWarning
- ValueError when both kwargs are passed
- Default behaviour: strict=False (permissive)
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _make_sources(*, validated: bool, with_checksum: bool) -> dict[str, Any]:
    """Registry sample for strict-quadrant tests."""
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
            "2024-06": {
                "epoch": "geih_2021_present",
                "download_url": "https://example.com/x.zip",
                "checksum_sha256": ("a" * 64) if with_checksum else None,
                "modules": {"ocupados": {"cabecera": "x.CSV"}},
                "validated": validated,
            }
        },
    }


@pytest.fixture
def setup_load(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
):
    """Patch HTTP, parser, registry to a controllable in-memory pipeline."""

    def _setup(*, validated: bool, with_checksum: bool) -> None:
        import pulso._config.registry as reg
        import pulso._core.downloader as dl_mod
        import pulso._core.parser as parser_mod

        monkeypatch.setattr(
            reg, "_SOURCES", _make_sources(validated=validated, with_checksum=with_checksum)
        )
        monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))

        # Always-valid checksum so download path stays clean.
        if with_checksum:
            monkeypatch.setattr(dl_mod, "verify_checksum", lambda *a, **kw: True)

        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"bytes"]
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mocker.patch("requests.get", return_value=mock_response)

        sentinel = pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})
        monkeypatch.setattr(parser_mod, "parse_module", lambda *a, **kw: sentinel)

    return _setup


# ── G-3: 4 quadrants of strict x validated ─────────────────────────────────


def test_strict_true_validated_true_loads_silently(setup_load) -> None:  # type: ignore[no-untyped-def]
    import pulso

    setup_load(validated=True, with_checksum=True)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # any warning fails the test
        df = pulso.load(year=2024, month=6, module="ocupados", strict=True, harmonize=False)
    assert len(df) == 1


def test_strict_true_validated_false_raises(setup_load) -> None:  # type: ignore[no-untyped-def]
    import pulso

    setup_load(validated=False, with_checksum=False)
    with pytest.raises(pulso.DataNotValidatedError):
        pulso.load(year=2024, month=6, module="ocupados", strict=True, harmonize=False)


def test_strict_false_validated_true_loads_no_warning(setup_load) -> None:  # type: ignore[no-untyped-def]
    import pulso

    setup_load(validated=True, with_checksum=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=6, module="ocupados", strict=False, harmonize=False)
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert user_warnings == []
    assert len(df) == 1


def test_strict_false_validated_false_loads_with_warning(setup_load) -> None:  # type: ignore[no-untyped-def]
    import pulso

    setup_load(validated=False, with_checksum=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=6, module="ocupados", strict=False, harmonize=False)
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1
    assert "checksum-validated" in str(user_warnings[0].message)
    assert "2024-06" in str(user_warnings[0].message)
    assert len(df) == 1


# ── Default = strict=False ─────────────────────────────────────────────────


def test_default_strict_is_false(setup_load) -> None:  # type: ignore[no-untyped-def]
    """No `strict` kwarg → permissive load with warning, no DataNotValidatedError."""
    import pulso

    setup_load(validated=False, with_checksum=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=6, module="ocupados", harmonize=False)
    assert len(df) == 1
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1


# ── Backward compat: allow_unvalidated ─────────────────────────────────────


def test_allow_unvalidated_true_emits_deprecation_warning(setup_load) -> None:  # type: ignore[no-untyped-def]
    import pulso

    setup_load(validated=False, with_checksum=False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=2024,
            month=6,
            module="ocupados",
            allow_unvalidated=True,
            harmonize=False,
        )
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 1
    assert "allow_unvalidated" in str(deprecations[0].message)
    assert "strict" in str(deprecations[0].message)
    assert len(df) == 1


def test_allow_unvalidated_false_translates_to_strict_true(setup_load) -> None:  # type: ignore[no-untyped-def]
    """allow_unvalidated=False → strict=True → raise on validated=false."""
    import pulso

    setup_load(validated=False, with_checksum=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        with pytest.raises(pulso.DataNotValidatedError):
            pulso.load(
                year=2024,
                month=6,
                module="ocupados",
                allow_unvalidated=False,
                harmonize=False,
            )


def test_passing_both_strict_and_allow_unvalidated_raises(setup_load) -> None:  # type: ignore[no-untyped-def]
    import pulso

    setup_load(validated=True, with_checksum=True)
    with pytest.raises(ValueError, match="both"):
        pulso.load(
            year=2024,
            month=6,
            module="ocupados",
            strict=True,
            allow_unvalidated=False,
            harmonize=False,
        )


# ── Error message U-3: refers to `strict=False`, not `allow_unvalidated=True` ──


def test_data_not_validated_error_message_mentions_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """U-3: the DataNotValidatedError message points users at the new flag name."""
    import pulso
    import pulso._config.registry as reg
    from pulso._core.downloader import download_zip

    monkeypatch.setattr(reg, "_SOURCES", _make_sources(validated=False, with_checksum=False))

    with pytest.raises(pulso.DataNotValidatedError) as excinfo:
        download_zip(2024, 6, allow_unvalidated=False, show_progress=False)
    assert "strict=False" in str(excinfo.value)
    assert "allow_unvalidated" not in str(excinfo.value)
