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
