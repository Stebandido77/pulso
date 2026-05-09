"""Unit tests for pulso._config.epochs."""

from __future__ import annotations

import pytest


def test_get_epoch_geih_2021_present() -> None:
    from pulso._config.epochs import Epoch, get_epoch

    e = get_epoch("geih_2021_present")
    assert isinstance(e, Epoch)
    assert e.key == "geih_2021_present"
    assert e.encoding == "latin-1"
    assert e.file_format == "csv"
    assert e.separator == ";"
    assert e.decimal == ","
    assert e.date_range[0] == "2022-01"
    assert e.date_range[1] is None  # open-ended


def test_get_epoch_geih_2006_2020() -> None:
    from pulso._config.epochs import Epoch, get_epoch

    e = get_epoch("geih_2006_2020")
    assert isinstance(e, Epoch)
    assert e.key == "geih_2006_2020"
    assert e.encoding == "latin-1"
    assert e.date_range[0] == "2006-01"
    assert e.date_range[1] == "2021-12"


def test_get_epoch_unknown_raises_config_error() -> None:
    from pulso._config.epochs import get_epoch
    from pulso._utils.exceptions import ConfigError

    with pytest.raises(ConfigError, match="not found"):
        get_epoch("nonexistent_epoch_xyz")


def test_epoch_merge_keys() -> None:
    from pulso._config.epochs import get_epoch

    e = get_epoch("geih_2021_present")
    assert "DIRECTORIO" in e.merge_keys_persona
    assert "SECUENCIA_P" in e.merge_keys_persona
    assert "ORDEN" in e.merge_keys_persona
    assert "DIRECTORIO" in e.merge_keys_hogar
    assert "SECUENCIA_P" in e.merge_keys_hogar


def test_epoch_folder_pattern_geih1() -> None:
    """GEIH-1 (2006-2020) uses physical Cabecera/Resto folders."""
    from pulso._config.epochs import get_epoch

    e = get_epoch("geih_2006_2020")
    assert "Cabecera/" in e.folder_pattern
    assert "Resto/" in e.folder_pattern
    assert e.area_filter is None


def test_epoch_folder_pattern_geih2() -> None:
    """GEIH-2 (2021-present) uses unified files; area split via CLASE column."""
    from pulso._config.epochs import get_epoch

    e = get_epoch("geih_2021_present")
    assert "CSV/" in e.folder_pattern
    assert e.area_filter is not None
    assert e.area_filter.column == "CLASE"
    assert 1 in e.area_filter.cabecera_values
    assert 2 in e.area_filter.resto_values
    assert 3 in e.area_filter.resto_values


def test_epoch_for_month_2024_06_is_geih2021() -> None:
    from pulso._config.epochs import epoch_for_month

    e = epoch_for_month(2024, 6)
    assert e.key == "geih_2021_present"


def test_epoch_for_month_2020_12_is_geih2006() -> None:
    from pulso._config.epochs import epoch_for_month

    e = epoch_for_month(2020, 12)
    assert e.key == "geih_2006_2020"


def test_epoch_for_month_2022_01_boundary() -> None:
    """2022-01 is the first month of the new epoch (file format break with Marco 2018)."""
    from pulso._config.epochs import epoch_for_month

    e = epoch_for_month(2022, 1)
    assert e.key == "geih_2021_present"


def test_epoch_for_month_2021_12_is_geih2006() -> None:
    """2021-12 is still in the old epoch (file format break is 2022-01, not 2021-01)."""
    from pulso._config.epochs import epoch_for_month

    e = epoch_for_month(2021, 12)
    assert e.key == "geih_2006_2020"


def test_epoch_for_month_2021_06_is_geih2006() -> None:
    """Regression: 2021-06 must fall in geih_2006_2020 (old format ~6MB), not geih_2021_present.

    Empirically validated in Phase 3.2 spike: 2021-06 ZIP is 6.2 MB (Shape A old format),
    while 2022-01 is 77 MB (Shape B Marco 2018 redesign).
    """
    from pulso._config.epochs import epoch_for_month

    e = epoch_for_month(2021, 6)
    assert e.key == "geih_2006_2020"


def test_epoch_for_month_2006_01_boundary() -> None:
    """2006-01 is the first month of the old epoch."""
    from pulso._config.epochs import epoch_for_month

    e = epoch_for_month(2006, 1)
    assert e.key == "geih_2006_2020"


def test_epoch_for_month_2005_12_raises() -> None:
    """2005-12 is before any defined epoch."""
    from pulso._config.epochs import epoch_for_month
    from pulso._utils.exceptions import ConfigError

    with pytest.raises(ConfigError):
        epoch_for_month(2005, 12)


def test_epoch_for_month_recent_open_ended() -> None:
    """Recent months fall in the open-ended geih_2021_present epoch."""
    from pulso._config.epochs import epoch_for_month

    e = epoch_for_month(2025, 12)
    assert e.key == "geih_2021_present"


def test_list_epochs_returns_two() -> None:
    from pulso._config.epochs import list_epochs

    epochs = list_epochs()
    assert len(epochs) == 2
    keys = {e.key for e in epochs}
    assert "geih_2006_2020" in keys
    assert "geih_2021_present" in keys


def test_epoch_is_frozen() -> None:
    from pulso._config.epochs import get_epoch

    e = get_epoch("geih_2021_present")
    with pytest.raises((AttributeError, TypeError)):
        e.encoding = "ascii"  # type: ignore[misc]
