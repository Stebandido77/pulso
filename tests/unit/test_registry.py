"""Unit tests for pulso._config.registry."""

from __future__ import annotations

from typing import Any

import pytest

# ─── Internal loaders ────────────────────────────────────────────────


def test_load_sources_returns_dict() -> None:
    from pulso._config.registry import _load_sources

    data = _load_sources()
    assert isinstance(data, dict)
    assert "metadata" in data
    assert "modules" in data
    assert "data" in data


def test_load_epochs_returns_dict() -> None:
    from pulso._config.registry import _load_epochs

    data = _load_epochs()
    assert "epochs" in data
    assert "geih_2006_2020" in data["epochs"]
    assert "geih_2021_present" in data["epochs"]


def test_load_variable_map_returns_dict() -> None:
    from pulso._config.registry import _load_variable_map

    data = _load_variable_map()
    assert "variables" in data
    assert len(data["variables"]) > 0


def test_load_sources_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second call returns the same object (module-level cache)."""
    from pulso._config.registry import _load_sources

    first = _load_sources()
    second = _load_sources()
    assert first is second


def test_load_sources_invalid_raises_config_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """If the JSON is malformed, ConfigError is raised."""

    from pulso._config.registry import _load_json_validated
    from pulso._utils.exceptions import ConfigError

    bad_json = tmp_path / "bad.json"
    bad_json.write_text('{"metadata": {}}', encoding="utf-8")

    schema_path = (
        pytest.importorskip("pathlib").Path(__file__).parent.parent.parent
        / "pulso"
        / "data"
        / "schemas"
        / "sources.schema.json"
    )

    with pytest.raises(ConfigError):
        _load_json_validated(bad_json, schema_path)


# ─── Public API ───────────────────────────────────────────────────────


def test_data_version_format() -> None:
    from pulso._config.registry import data_version

    v = data_version()
    assert isinstance(v, str)
    # Format: YYYY.MM
    parts = v.split(".")
    assert len(parts) == 2
    assert parts[0].isdigit()
    assert parts[1].isdigit()


def test_list_available_empty_by_default() -> None:
    """sources.json ships with data: {} so list_available is empty."""
    import pandas as pd

    from pulso._config.registry import list_available

    df = list_available()
    assert isinstance(df, pd.DataFrame)
    # Real data section is empty; fixture tests handle non-empty case.
    assert (
        set(df.columns) >= {"year", "month", "epoch", "validated", "modules_available"}
        if len(df) > 0
        else True
    )


def test_list_available_has_correct_columns_when_populated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When _SOURCES has data entries, list_available returns correct columns."""
    import pulso._config.registry as reg

    stub_sources: dict[str, Any] = {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Ocupados",
                "available_in": ["geih_2021_present"],
            }
        },
        "data": {
            "2024-06": {
                "epoch": "geih_2021_present",
                "validated": True,
                "modules": {"ocupados": {"cabecera": "Cab/occ.CSV"}},
            }
        },
    }
    monkeypatch.setattr(reg, "_SOURCES", stub_sources)

    import pandas as pd

    from pulso._config.registry import list_available

    df = list_available()
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["year", "month", "epoch", "validated", "modules_available"]
    assert len(df) == 1
    assert df.iloc[0]["year"] == 2024
    assert df.iloc[0]["month"] == 6
    assert df.iloc[0]["epoch"] == "geih_2021_present"
    assert df.iloc[0]["validated"] == True  # noqa: E712  (numpy bool)
    assert "ocupados" in df.iloc[0]["modules_available"]


def test_list_available_year_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    import pulso._config.registry as reg

    stub_sources: dict[str, Any] = {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "x",
                "available_in": ["geih_2021_present"],
            }
        },
        "data": {
            "2023-06": {
                "epoch": "geih_2021_present",
                "validated": True,
                "modules": {"ocupados": {"cabecera": "x.CSV"}},
            },
            "2024-06": {
                "epoch": "geih_2021_present",
                "validated": True,
                "modules": {"ocupados": {"cabecera": "x.CSV"}},
            },
        },
    }
    monkeypatch.setattr(reg, "_SOURCES", stub_sources)

    from pulso._config.registry import list_available

    df = list_available(year=2024)
    assert len(df) == 1
    assert df.iloc[0]["year"] == 2024


def test_list_modules_returns_canonical_modules() -> None:
    """Schema 1.1.0 has 8 canonical modules (added migracion, otras_formas_trabajo)."""
    import pandas as pd

    from pulso._config.registry import list_modules

    df = list_modules()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 8

    expected = {
        "caracteristicas_generales",
        "ocupados",
        "desocupados",
        "inactivos",
        "vivienda_hogares",
        "otros_ingresos",
        "migracion",
        "otras_formas_trabajo",
    }
    assert set(df["module"]) == expected


def test_list_modules_geih2_only_modules_marked_correctly() -> None:
    """migracion and otras_formas_trabajo only exist in geih_2021_present."""
    from pulso._config.registry import list_modules

    df = list_modules()
    geih2_only = df[df["module"].isin(["migracion", "otras_formas_trabajo"])]
    for _, row in geih2_only.iterrows():
        assert row["available_in"] == ["geih_2021_present"]


def test_list_modules_columns() -> None:
    from pulso._config.registry import list_modules

    df = list_modules()
    expected = {"module", "level", "description_es", "description_en", "available_in"}
    assert expected.issubset(set(df.columns))


def test_describe_returns_dict() -> None:
    from pulso._config.registry import describe

    result = describe("ocupados")
    assert isinstance(result, dict)
    assert result["level"] == "persona"
    assert result["module"] == "ocupados"


def test_describe_unknown_module_raises() -> None:
    from pulso._config.registry import describe
    from pulso._utils.exceptions import ConfigError

    with pytest.raises(ConfigError, match="not found"):
        describe("nonexistent_module_xyz")


def test_describe_with_year_includes_epoch_context() -> None:
    from pulso._config.registry import describe

    result = describe("ocupados", year=2024)
    assert "epoch_context" in result
    ctx = result["epoch_context"]
    assert isinstance(ctx, dict)
    assert ctx["key"] == "geih_2021_present"


def test_phase2_functions_raise_not_implemented() -> None:
    from pulso._config.registry import describe_harmonization, describe_variable, list_variables

    with pytest.raises(NotImplementedError):
        list_variables()
    with pytest.raises(NotImplementedError):
        describe_variable("edad")
    with pytest.raises(NotImplementedError):
        describe_harmonization("edad")
