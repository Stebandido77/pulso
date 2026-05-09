"""Unit tests for pulso._core.loader: module validation and auto-inclusion."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from pulso._utils.exceptions import ModuleNotAvailableError

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_EPOCH_KEY = "geih_2021_present"

_MINIMAL_SOURCES: dict[str, Any] = {
    "metadata": {"schema_version": "1.1.0", "data_version": "2026.04"},
    "modules": {
        "caracteristicas_generales": {
            "level": "persona",
            "description_es": "CG",
            "description_en": "CG",
            "available_in": [_EPOCH_KEY],
        },
        "ocupados": {
            "level": "persona",
            "description_es": "Ocu",
            "description_en": "Ocu",
            "available_in": [_EPOCH_KEY],
        },
        "vivienda_hogares": {
            "level": "hogar",
            "description_es": "Viv",
            "description_en": "Viv",
            "available_in": [_EPOCH_KEY],
        },
    },
    "data": {
        "2024-06": {
            "epoch": _EPOCH_KEY,
            "download_url": "https://example.com/fake.zip",
            "checksum_sha256": "abc",
            "validated": True,
            "modules": {
                "caracteristicas_generales": {"file": "CSV/cg.CSV"},
                "ocupados": {"file": "CSV/ocu.CSV"},
                "vivienda_hogares": {"file": "CSV/viv.CSV"},
            },
        }
    },
}

_MINIMAL_VARIABLE_MAP: dict[str, Any] = {
    "metadata": {"schema_version": "1.0.0"},
    "variables": {
        "vivienda_propia": {
            "type": "boolean",
            "level": "vivienda",
            "module": "vivienda_hogares",
            "mappings": {
                _EPOCH_KEY: {
                    "source_variable": "P5090",
                    "transform": {"op": "compute", "expr": "P5090 <= 2"},
                }
            },
        },
        "edad": {
            "type": "numeric",
            "level": "persona",
            "module": "caracteristicas_generales",
            "mappings": {
                _EPOCH_KEY: {
                    "source_variable": "P6040",
                    "transform": "identity",
                }
            },
        },
    },
}


def _minimal_df() -> pd.DataFrame:
    return pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})


# ---------------------------------------------------------------------------
# _required_modules_for_variables — pure-function tests
# ---------------------------------------------------------------------------


def test_required_modules_returns_all_modules_for_epoch() -> None:
    from pulso._core.loader import _required_modules_for_variables

    result = _required_modules_for_variables(_MINIMAL_VARIABLE_MAP, _MINIMAL_SOURCES, _EPOCH_KEY)
    assert result == {"vivienda_hogares", "caracteristicas_generales"}


def test_required_modules_filters_by_requested_variables() -> None:
    from pulso._core.loader import _required_modules_for_variables

    result = _required_modules_for_variables(
        _MINIMAL_VARIABLE_MAP, _MINIMAL_SOURCES, _EPOCH_KEY, requested_variables=["edad"]
    )
    assert result == {"caracteristicas_generales"}
    assert "vivienda_hogares" not in result


def test_required_modules_skips_variable_without_epoch_mapping() -> None:
    from pulso._core.loader import _required_modules_for_variables

    vm: dict[str, Any] = {
        "variables": {
            "old_var": {
                "module": "old_module",
                "mappings": {"geih_2006_2020": {"source_variable": "X", "transform": "identity"}},
            }
        }
    }
    sources: dict[str, Any] = {"modules": {"old_module": {"available_in": ["geih_2006_2020"]}}}

    result = _required_modules_for_variables(vm, sources, "geih_2021_present")
    assert "old_module" not in result


def test_required_modules_skips_module_not_in_sources() -> None:
    from pulso._core.loader import _required_modules_for_variables

    vm: dict[str, Any] = {
        "variables": {
            "some_var": {
                "module": "phantom_module",
                "mappings": {_EPOCH_KEY: {"source_variable": "X", "transform": "identity"}},
            }
        }
    }
    sources: dict[str, Any] = {"modules": {}}

    result = _required_modules_for_variables(vm, sources, _EPOCH_KEY)
    assert "phantom_module" not in result


# ---------------------------------------------------------------------------
# load_merged: module validation (Issue 1)
# ---------------------------------------------------------------------------


def test_load_merged_raises_on_invalid_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid module names raise ModuleNotAvailableError before any loading."""
    import pulso
    import pulso._config.registry as reg

    monkeypatch.setattr(reg, "_SOURCES", _MINIMAL_SOURCES)

    with pytest.raises(ModuleNotAvailableError):
        pulso.load_merged(year=2024, month=6, modules=["no_ocupados"])


def test_load_merged_valid_modules_pass_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid module names pass validation; no ModuleNotAvailableError is raised."""
    import pulso
    import pulso._config.registry as reg
    import pulso._core.loader as loader_mod
    import pulso._core.merger as merger_mod

    monkeypatch.setattr(reg, "_SOURCES", _MINIMAL_SOURCES)
    monkeypatch.setattr(reg, "_VARIABLE_MAP", _MINIMAL_VARIABLE_MAP)
    monkeypatch.setattr(loader_mod, "load", lambda *a, **kw: _minimal_df())
    monkeypatch.setattr(merger_mod, "merge_modules", lambda *a, **kw: _minimal_df())

    df = pulso.load_merged(
        year=2024, month=6, modules=["caracteristicas_generales"], harmonize=False
    )
    assert df is not None


# ---------------------------------------------------------------------------
# load_merged: auto-inclusion (Issue 2)
# ---------------------------------------------------------------------------


def test_load_merged_auto_includes_required_modules_when_harmonize_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When harmonize=True and user provides explicit modules, required modules are auto-included."""
    import pulso
    import pulso._config.registry as reg
    import pulso._core.harmonizer as harm_mod
    import pulso._core.loader as loader_mod
    import pulso._core.merger as merger_mod

    monkeypatch.setattr(reg, "_SOURCES", _MINIMAL_SOURCES)
    monkeypatch.setattr(reg, "_VARIABLE_MAP", _MINIMAL_VARIABLE_MAP)

    loaded_modules: list[str] = []

    def fake_load(year: int, month: int, module: str, **kwargs: Any) -> pd.DataFrame:
        loaded_modules.append(module)
        return _minimal_df()

    monkeypatch.setattr(loader_mod, "load", fake_load)
    monkeypatch.setattr(merger_mod, "merge_modules", lambda *a, **kw: _minimal_df())
    monkeypatch.setattr(harm_mod, "harmonize_dataframe", lambda df, *a, **kw: df)

    # User specifies only caracteristicas_generales — vivienda_hogares is NOT in list.
    pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales"],
        harmonize=True,
    )

    # vivienda_propia requires vivienda_hogares → must be auto-included.
    assert "vivienda_hogares" in loaded_modules


def test_load_merged_no_auto_inclusion_when_harmonize_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When harmonize=False, user's exact module list is respected; no auto-inclusion."""
    import pulso
    import pulso._config.registry as reg
    import pulso._core.loader as loader_mod
    import pulso._core.merger as merger_mod

    monkeypatch.setattr(reg, "_SOURCES", _MINIMAL_SOURCES)
    monkeypatch.setattr(reg, "_VARIABLE_MAP", _MINIMAL_VARIABLE_MAP)

    loaded_modules: list[str] = []

    def fake_load(year: int, month: int, module: str, **kwargs: Any) -> pd.DataFrame:
        loaded_modules.append(module)
        return _minimal_df()

    monkeypatch.setattr(loader_mod, "load", fake_load)
    monkeypatch.setattr(merger_mod, "merge_modules", lambda *a, **kw: _minimal_df())

    pulso.load_merged(
        year=2024,
        month=6,
        modules=["caracteristicas_generales"],
        harmonize=False,
    )

    assert "vivienda_hogares" not in loaded_modules
    assert loaded_modules == ["caracteristicas_generales"]


def test_load_merged_auto_inclusion_restricted_by_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When variables=[edad], only modules needed for edad are auto-included."""
    import pulso
    import pulso._config.registry as reg
    import pulso._core.harmonizer as harm_mod
    import pulso._core.loader as loader_mod
    import pulso._core.merger as merger_mod

    monkeypatch.setattr(reg, "_SOURCES", _MINIMAL_SOURCES)
    monkeypatch.setattr(reg, "_VARIABLE_MAP", _MINIMAL_VARIABLE_MAP)

    loaded_modules: list[str] = []

    def fake_load(year: int, month: int, module: str, **kwargs: Any) -> pd.DataFrame:
        loaded_modules.append(module)
        return _minimal_df()

    monkeypatch.setattr(loader_mod, "load", fake_load)
    monkeypatch.setattr(merger_mod, "merge_modules", lambda *a, **kw: _minimal_df())
    monkeypatch.setattr(harm_mod, "harmonize_dataframe", lambda df, *a, **kw: df)

    # User requests only edad; edad only needs caracteristicas_generales.
    pulso.load_merged(
        year=2024,
        month=6,
        modules=["ocupados"],
        harmonize=True,
        variables=["edad"],
    )

    assert "caracteristicas_generales" in loaded_modules
    assert "vivienda_hogares" not in loaded_modules
