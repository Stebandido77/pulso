"""Tests for module-aware variable filtering (Fix 3, variable_module_map).

The contract: when ``load(..., module=M)`` triggers harmonization, canonical
variables whose ``variable_module_map`` applicability does not intersect
``[M]`` are filtered out *before* harmonization is attempted. They never
appear in the aggregated 'skipped during harmonization' UserWarning. Only
canonicals that ARE applicable to M but whose source columns happen to be
missing in the parsed data show up in the warning.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pulso._config.registry import _load_variable_module_map
from pulso._core.harmonizer import _iter_relevant_variables, harmonize_dataframe

if TYPE_CHECKING:
    from pathlib import Path


# ---------------------------------------------------------------------------
# variable_module_map.json: shape and contents
# ---------------------------------------------------------------------------


def test_variable_module_map_loads_and_validates() -> None:
    """The map must load, validate against its schema, and contain
    every canonical defined in variable_map.json (so we don't silently
    skip a curated canonical via the fallback path)."""
    from pulso._config.registry import _load_variable_map

    vmm = _load_variable_module_map()
    assert "applicability" in vmm
    applicability = vmm["applicability"]

    vm = _load_variable_map()
    canonicals = set(vm["variables"].keys())
    mapped = set(applicability.keys())
    missing = canonicals - mapped
    assert missing == set(), f"Canonicals missing from applicability table: {missing}"


def test_applicability_modules_exist_in_sources() -> None:
    """Every module name in the applicability lists must exist in sources.json."""
    from pulso._config.registry import _load_sources

    vmm = _load_variable_module_map()
    sources = _load_sources()
    known_modules = set(sources["modules"].keys())
    for canonical, modules in vmm["applicability"].items():
        unknown = set(modules) - known_modules
        assert unknown == set(), f"Canonical {canonical!r} references unknown modules: {unknown}"


# ---------------------------------------------------------------------------
# _iter_relevant_variables: applicability filter
# ---------------------------------------------------------------------------


def _epoch(key: str = "geih_2021_present") -> Any:
    e = MagicMock()
    e.key = key
    return e


def test_iter_relevant_variables_no_modules_means_no_filtering() -> None:
    """When ``modules=None`` (legacy callers), every epoch-mapped canonical is
    yielded."""
    yielded = {name for name, _ in _iter_relevant_variables(_epoch(), variables=None)}
    # variable_map has 30 canonicals; for geih_2021_present most are mapped.
    assert len(yielded) >= 25


def test_iter_relevant_variables_module_ocupados_excludes_ingreso_total() -> None:
    """``ingreso_total`` lives in the ``otros_ingresos`` module, so for
    ``modules=['ocupados']`` it is filtered out before harmonization is
    attempted (and therefore cannot leak into the 'skipped' warning)."""
    yielded = {
        name for name, _ in _iter_relevant_variables(_epoch(), variables=None, modules=["ocupados"])
    }
    assert "ingreso_total" not in yielded


def test_iter_relevant_variables_module_ocupados_includes_cross_module_vars() -> None:
    """Variables that legitimately apply to multiple modules (peso_expansion,
    hogar_id) are kept for any module that's in their applicability list."""
    yielded = {
        name for name, _ in _iter_relevant_variables(_epoch(), variables=None, modules=["ocupados"])
    }
    # Cross-module canonicals must survive.
    assert "peso_expansion" in yielded
    assert "peso_expansion_persona" in yielded
    assert "hogar_id" in yielded
    # And ocupados-specific canonicals.
    assert "ocupacion" in yielded
    assert "ingreso_laboral" in yielded


def test_iter_relevant_variables_module_caracteristicas_excludes_ocupados_vars() -> None:
    """For ``modules=['caracteristicas_generales']``, ``ocupacion`` (an
    ocupados-only canonical) is filtered out."""
    yielded = {
        name
        for name, _ in _iter_relevant_variables(
            _epoch(), variables=None, modules=["caracteristicas_generales"]
        )
    }
    assert "ocupacion" not in yielded
    assert "sexo" in yielded
    assert "edad" in yielded


def test_iter_relevant_variables_module_ingresos_includes_ingreso_total() -> None:
    """``ingreso_total`` is applicable to ``otros_ingresos`` only — verify it
    IS yielded for that module so the harmonizer can attempt it."""
    yielded = {
        name
        for name, _ in _iter_relevant_variables(
            _epoch(), variables=None, modules=["otros_ingresos"]
        )
    }
    assert "ingreso_total" in yielded


def test_iter_relevant_variables_multiple_modules_unions_applicability() -> None:
    """When multiple modules are passed (load_merged path), the applicability
    is the union — variables that apply to ANY of the listed modules are
    yielded."""
    yielded = {
        name
        for name, _ in _iter_relevant_variables(
            _epoch(),
            variables=None,
            modules=["ocupados", "otros_ingresos"],
        )
    }
    assert "ocupacion" in yielded  # ocupados
    assert "ingreso_total" in yielded  # otros_ingresos
    assert "peso_expansion" in yielded  # cross-module


# ---------------------------------------------------------------------------
# harmonize_dataframe: applicability filter prevents non-applicable canonicals
# from appearing in the skipped list
# ---------------------------------------------------------------------------


def test_harmonize_dataframe_with_module_filters_non_applicable() -> None:
    """When ``modules=['ocupados']`` is passed and the parsed DF has only
    merge keys + age, ``ingreso_total`` (otros_ingresos) is NOT in the
    skipped-variables list because it never reached the harmonization step.
    """
    epoch = _epoch()
    df = pd.DataFrame(
        {
            "DIRECTORIO": ["1"],
            "SECUENCIA_P": ["1"],
            "ORDEN": ["1"],
            "P6040": [25],
        }
    )

    result = harmonize_dataframe(df, epoch, modules=["ocupados"])
    skipped = result.attrs.get("_skipped_variables", [])

    # `ingreso_total` is otros_ingresos-only — should not be enumerated.
    assert "ingreso_total" not in skipped
    # `sexo` is caracteristicas_generales-only — should not be enumerated.
    assert "sexo" not in skipped
    # But `ocupacion` (ocupados-applicable, source col P6020 absent) IS in skipped.
    assert "ocupacion" in skipped


# ---------------------------------------------------------------------------
# Public load() integration: ingreso_total never appears in the warning when
# loading module='ocupados'
# ---------------------------------------------------------------------------


def _make_sources(*, all_keys: list[str]) -> dict[str, Any]:
    return {
        "metadata": {"schema_version": "1.0.0", "data_version": "2024.06"},
        "modules": {
            "ocupados": {
                "level": "persona",
                "description_es": "Ocu",
                "description_en": "Ocu",
                "available_in": ["geih_2021_present"],
            },
            "otros_ingresos": {
                "level": "persona",
                "description_es": "Otros",
                "description_en": "Other",
                "available_in": ["geih_2021_present"],
            },
        },
        "data": {
            key: {
                "epoch": "geih_2021_present",
                "download_url": f"https://example.com/{key}.zip",
                "checksum_sha256": "a" * 64,
                "modules": {
                    "ocupados": {"file": f"{key}.CSV"},
                    "otros_ingresos": {"file": f"{key}_oi.CSV"},
                },
                "validated": True,
            }
            for key in all_keys
        },
    }


@pytest.fixture
def setup_load_ocupados(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
):
    def _setup() -> None:
        import pulso._config.registry as reg
        import pulso._core.downloader as dl_mod
        import pulso._core.parser as parser_mod

        sources = _make_sources(all_keys=["2024-06"])
        monkeypatch.setattr(reg, "_SOURCES", sources)
        monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setattr(dl_mod, "verify_checksum", lambda *a, **kw: True)

        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"bytes"]
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()
        mocker.patch("requests.get", return_value=mock_response)

        sentinel = pd.DataFrame(
            {
                "DIRECTORIO": ["1", "2"],
                "SECUENCIA_P": ["1", "1"],
                "ORDEN": ["1", "1"],
                "P6040": [25, 30],
            }
        )
        monkeypatch.setattr(parser_mod, "parse_module", lambda *a, **kw: sentinel)

    return _setup


def test_load_ocupados_excludes_ingreso_total_from_skip_warning(
    setup_load_ocupados,  # type: ignore[no-untyped-def]
) -> None:
    """Public-API regression: pulso.load(2024, 6, 'ocupados') must NOT
    list ``ingreso_total`` in the aggregated skipped-variables warning,
    because it's an ``otros_ingresos`` canonical."""
    import pulso

    setup_load_ocupados()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pulso.load(year=2024, month=6, module="ocupados", harmonize=True)

    skipping_warnings = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "skipped during harmonization" in str(w.message)
    ]
    # There may or may not be a warning depending on how many ocupados-applicable
    # canonicals fail. Either way, `ingreso_total` must not appear.
    for w in skipping_warnings:
        assert "ingreso_total" not in str(w.message), (
            f"ingreso_total leaked into ocupados warning: {w.message}"
        )
        assert "sexo" not in str(w.message), (
            f"sexo (caracteristicas_generales-only) leaked into ocupados warning: {w.message}"
        )


def test_load_otros_ingresos_attempts_ingreso_total(
    setup_load_ocupados,  # type: ignore[no-untyped-def]
) -> None:
    """When the user loads ``module='otros_ingresos'`` and the source
    column is absent, ``ingreso_total`` IS attempted and IS in the
    aggregated warning — Fix 3 must not over-filter."""
    import pulso

    setup_load_ocupados()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        pulso.load(year=2024, month=6, module="otros_ingresos", harmonize=True)

    skipping_warnings = [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "skipped during harmonization" in str(w.message)
    ]
    # Source column for ingreso_total is absent in the synthetic frame, so
    # it WILL fail to harmonize and surface in the warning.
    combined = " ".join(str(w.message) for w in skipping_warnings)
    assert "ingreso_total" in combined, (
        f"Expected ingreso_total to appear in otros_ingresos skip warning, got: {combined}"
    )
