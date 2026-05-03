"""Tests for load_merged module-handling fixes (Commit 6).

Covers:
- M-1: apply_smoothing=True respects the explicit `modules` argument.
- M-2: explicit `modules=[...]` raises ModuleNotAvailableError for any
       module missing from that period's registry record.
- M-2: `modules=None` keeps the existing auto-discovery (silent skip).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from pulso._utils.exceptions import ModuleNotAvailableError

_EPOCH_KEY = "geih_2021_present"

_SOURCES_2024_06: dict[str, Any] = {
    "metadata": {"schema_version": "1.1.0", "data_version": "2024.06"},
    "modules": {
        "ocupados": {
            "level": "persona",
            "description_es": "Ocu",
            "description_en": "Ocu",
            "available_in": [_EPOCH_KEY],
        },
        "inactivos": {
            "level": "persona",
            "description_es": "Inact",
            "description_en": "Inact",
            "available_in": [_EPOCH_KEY],
        },
        # 'migracion' is in the global registry but the period below
        # only ships ocupados/inactivos. Used in the M-2 test.
        "migracion": {
            "level": "persona",
            "description_es": "Mig",
            "description_en": "Mig",
            "available_in": [_EPOCH_KEY],
        },
    },
    "data": {
        "2024-06": {
            "epoch": _EPOCH_KEY,
            "download_url": "https://example.com/x.zip",
            "checksum_sha256": "a" * 64,
            "validated": True,
            "modules": {
                "ocupados": {"file": "CSV/o.CSV"},
                "inactivos": {"file": "CSV/i.CSV"},
                # NB: 'migracion' deliberately absent for this period.
            },
        }
    },
}


def _minimal_df() -> pd.DataFrame:
    return pd.DataFrame({"DIRECTORIO": ["1"], "SECUENCIA_P": ["1"], "ORDEN": ["1"]})


# ── M-2 ────────────────────────────────────────────────────────────────────


def test_load_merged_explicit_module_unavailable_for_period_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M-2: a module known globally but absent from the period record must raise."""
    import pulso
    import pulso._config.registry as reg

    monkeypatch.setattr(reg, "_SOURCES", _SOURCES_2024_06)

    with pytest.raises(ModuleNotAvailableError, match="migracion"):
        pulso.load_merged(
            year=2024,
            month=6,
            modules=["migracion", "ocupados"],
            harmonize=False,
        )


def test_load_merged_auto_discovery_silently_skips_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M-2: modules=None preserves silent auto-discovery (only loads what's there)."""
    import pulso
    import pulso._config.registry as reg
    import pulso._core.loader as loader_mod
    import pulso._core.merger as merger_mod

    monkeypatch.setattr(reg, "_SOURCES", _SOURCES_2024_06)

    loaded: list[str] = []

    def fake_load(year: int, month: int, module: str, **kwargs: Any) -> pd.DataFrame:
        loaded.append(module)
        return _minimal_df()

    monkeypatch.setattr(loader_mod, "load", fake_load)
    monkeypatch.setattr(merger_mod, "merge_modules", lambda *a, **kw: _minimal_df())

    pulso.load_merged(year=2024, month=6, modules=None, harmonize=False)

    # Only the modules registered for the period get loaded; no error for the
    # globally-known-but-period-absent 'migracion'.
    assert set(loaded) == {"ocupados", "inactivos"}


# ── M-1 ────────────────────────────────────────────────────────────────────


def test_load_merged_apply_smoothing_respects_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M-1: apply_smoothing=True with modules=['ocupados'] must NOT load every empalme module."""
    import pulso
    import pulso._config.registry as reg
    import pulso._core.empalme as empalme_mod

    # Source needs the year in EMPALME range so the smoothing branch is taken.
    sources = {
        "metadata": {"schema_version": "1.1.0", "data_version": "2015.06"},
        "modules": _SOURCES_2024_06["modules"],
        "data": {
            "2015-06": {
                "epoch": "geih_2006_2020",
                "download_url": "https://example.com/x.zip",
                "checksum_sha256": "a" * 64,
                "validated": True,
                "modules": {
                    "ocupados": {"cabecera": "Cab.CSV", "resto": "Res.CSV"},
                },
            }
        },
    }
    monkeypatch.setattr(reg, "_SOURCES", sources)

    captured: dict[str, Any] = {}

    def fake_loader(
        year: int,
        month: int,
        area: str = "total",
        harmonize: bool = True,
        variables: list[str] | None = None,
        modules: list[str] | None = None,
    ) -> pd.DataFrame:
        captured["modules"] = modules
        return _minimal_df()

    monkeypatch.setattr(empalme_mod, "_load_empalme_month_merged", fake_loader)

    pulso.load_merged(
        year=2015,
        month=6,
        modules=["ocupados"],
        apply_smoothing=True,
        harmonize=False,
    )

    assert captured["modules"] == ["ocupados"]


def test_load_merged_apply_smoothing_no_modules_passes_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M-1: apply_smoothing=True with modules=None still gets None (full auto)."""
    import pulso
    import pulso._config.registry as reg
    import pulso._core.empalme as empalme_mod

    sources = {
        "metadata": {"schema_version": "1.1.0", "data_version": "2015.06"},
        "modules": _SOURCES_2024_06["modules"],
        "data": {
            "2015-06": {
                "epoch": "geih_2006_2020",
                "download_url": "https://example.com/x.zip",
                "checksum_sha256": "a" * 64,
                "validated": True,
                "modules": {"ocupados": {"cabecera": "C.CSV", "resto": "R.CSV"}},
            }
        },
    }
    monkeypatch.setattr(reg, "_SOURCES", sources)

    captured: dict[str, Any] = {}

    def fake_loader(
        year: int,
        month: int,
        area: str = "total",
        harmonize: bool = True,
        variables: list[str] | None = None,
        modules: list[str] | None = None,
    ) -> pd.DataFrame:
        captured["modules"] = modules
        return _minimal_df()

    monkeypatch.setattr(empalme_mod, "_load_empalme_month_merged", fake_loader)

    pulso.load_merged(year=2015, month=6, apply_smoothing=True, harmonize=False)
    assert captured["modules"] is None


def test_load_empalme_month_merged_explicit_module_missing_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    """M-1: when modules=['x'] and 'x' isn't parseable, _load_empalme_month_merged must surface the error."""
    import zipfile

    from pulso._core import empalme as emp_mod

    # Build an annual ZIP whose June sub-ZIP only has Ocupados.CSV.
    inner_buf = b""
    import io as _io

    inner_io = _io.BytesIO()
    with zipfile.ZipFile(inner_io, "w") as zinner:
        zinner.writestr(
            "6. Junio/CSV/Ocupados.CSV",
            "DIRECTORIO;SECUENCIA_P;ORDEN;P6020;CLASE\n1;1;1;1;1\n".encode("latin-1"),
        )
    inner_buf = inner_io.getvalue()

    outer_path = tmp_path / "2015.zip"
    with zipfile.ZipFile(outer_path, "w") as zouter:
        zouter.writestr("GEIH_Empalme_2015/6. Junio.zip", inner_buf)

    monkeypatch.setattr(emp_mod, "download_empalme_zip", lambda *a, **kw: outer_path)

    # Asking for 'inactivos' which the sub-ZIP doesn't carry must raise, not silently drop.
    from pulso._utils.exceptions import ParseError

    with pytest.raises(ParseError, match="inactivos"):
        emp_mod._load_empalme_month_merged(
            2015, 6, area="total", harmonize=False, modules=["inactivos"]
        )
