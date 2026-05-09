"""Smoke tests: package is importable and exports the public API."""

from __future__ import annotations


def test_import_pulso() -> None:
    import pulso

    assert hasattr(pulso, "__version__")
    assert isinstance(pulso.__version__, str)


def test_public_api_exports() -> None:
    """All names in __all__ must be importable."""
    import pulso

    expected = {
        "load",
        "load_merged",
        "load_empalme",
        "list_available",
        "list_modules",
        "list_variables",
        "describe",
        "describe_variable",
        "describe_harmonization",
        "expand",
        "cache_info",
        "cache_clear",
        "cache_path",
        "data_version",
    }
    assert expected.issubset(set(pulso.__all__))
    for name in expected:
        assert hasattr(pulso, name), f"pulso.{name} is not exported"


def test_top_level_exception_imports() -> None:
    """C-2: every exception class is reachable at the top level."""
    import pulso

    expected = (
        "PulsoError",
        "ConfigError",
        "DataNotAvailableError",
        "DataNotValidatedError",
        "ModuleNotAvailableError",
        "DownloadError",
        "ChecksumMismatchError",
        "ParseError",
        "HarmonizationError",
        "MergeError",
        "CacheError",
    )
    for name in expected:
        assert hasattr(pulso, name), f"pulso.{name} is not exported"
        assert name in pulso.__all__, f"{name} missing from pulso.__all__"


def test_top_level_exception_hierarchy() -> None:
    """C-2: exception hierarchy is preserved under the top-level alias."""
    import pulso

    assert issubclass(pulso.DataNotValidatedError, pulso.PulsoError)
    assert issubclass(pulso.DataNotAvailableError, pulso.PulsoError)
    assert issubclass(pulso.ChecksumMismatchError, pulso.DownloadError)
    assert issubclass(pulso.DownloadError, pulso.PulsoError)
    assert issubclass(pulso.HarmonizationError, pulso.PulsoError)
    assert issubclass(pulso.MergeError, pulso.PulsoError)
