"""Unit tests for pulso._utils.exceptions."""

from __future__ import annotations

from pulso._utils.exceptions import (
    CacheError,
    ChecksumMismatchError,
    ConfigError,
    DataNotAvailableError,
    DataNotValidatedError,
    DownloadError,
    HarmonizationError,
    MergeError,
    ModuleNotAvailableError,
    ParseError,
    PulsoError,
)


def test_harmonization_error_is_pulso_error() -> None:
    err = HarmonizationError("recode failed")
    assert isinstance(err, PulsoError)
    assert isinstance(err, Exception)
    assert str(err) == "recode failed"


def test_merge_error_is_pulso_error() -> None:
    err = MergeError("missing key ORDEN")
    assert isinstance(err, PulsoError)
    assert isinstance(err, Exception)
    assert str(err) == "missing key ORDEN"


def test_harmonization_error_distinct_from_config_error() -> None:
    assert not issubclass(HarmonizationError, ConfigError)


def test_harmonization_error_distinct_from_parse_error() -> None:
    assert not issubclass(HarmonizationError, ParseError)


def test_merge_error_distinct_from_harmonization_error() -> None:
    assert not issubclass(MergeError, HarmonizationError)


def test_all_errors_are_catchable_as_pulso_error() -> None:
    errors = [
        ConfigError("c"),
        DataNotAvailableError(2024, 1),
        DataNotValidatedError("v"),
        ModuleNotAvailableError("m"),
        DownloadError("d"),
        ChecksumMismatchError("cm"),
        ParseError("p"),
        HarmonizationError("h"),
        MergeError("e"),
        CacheError("ca"),
    ]
    for err in errors:
        assert isinstance(err, PulsoError), f"{type(err)} not a PulsoError"


def test_checksum_mismatch_is_download_error() -> None:
    """ChecksumMismatchError must remain catchable via the broader DownloadError."""
    err = ChecksumMismatchError("hash differs")
    assert isinstance(err, DownloadError)
    assert isinstance(err, PulsoError)


def test_harmonization_error_can_chain_cause() -> None:
    original = ValueError("bad cast")
    err = HarmonizationError("cast failed")
    err.__cause__ = original
    assert err.__cause__ is original


def test_merge_error_message_preserved() -> None:
    msg = "Module 'ocupados' missing merge key: ORDEN"
    err = MergeError(msg)
    assert msg in str(err)
