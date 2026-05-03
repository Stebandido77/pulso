"""Regression: ParseError must remain in the per-period skippable set
in both ``load`` and ``load_merged``.

If a refactor accidentally drops ParseError from the catch tuple, a
single corrupted month would once again abort an entire multi-period
range under ``strict=False`` (the original M-5 bug, fixed in Commit 14).

We assert membership via two complementary mechanisms:

1. AST introspection of the source — independent of which file the
   tuple actually lives in (module level, function local, or both).
2. Behavioural check — drive ``load`` with a stubbed parser that always
   raises ParseError and confirm the call returns under ``strict=False``
   while still propagating under ``strict=True``.
"""

from __future__ import annotations

import ast
import inspect
import warnings
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

if TYPE_CHECKING:
    from pathlib import Path


# ── 1. AST: ParseError appears in every function-local _SKIPPABLE ──


def _function_local_skippables() -> dict[str, list[str]]:
    """Return {function_name: [exception_names_in_local_SKIPPABLE]}."""
    import pulso._core.loader as loader_mod

    source = inspect.getsource(loader_mod)
    tree = ast.parse(source)

    out: dict[str, list[str]] = {}
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "_SKIPPABLE"
                and isinstance(node.value, ast.Tuple)
            ):
                out[fn.name] = [elt.id for elt in node.value.elts if isinstance(elt, ast.Name)]
    return out


def test_parse_error_in_skippable_in_load() -> None:
    """M-5 regression: ParseError must be in load()'s local _SKIPPABLE."""
    found = _function_local_skippables()
    assert "load" in found, "load() must define a local _SKIPPABLE tuple"
    assert "ParseError" in found["load"], (
        f"load() _SKIPPABLE must include ParseError so multi-period "
        f"strict=False skips a corrupted month instead of aborting. "
        f"Got: {found['load']}"
    )


def test_parse_error_in_skippable_in_load_merged() -> None:
    """M-5 regression: ParseError must be in load_merged()'s local _SKIPPABLE."""
    found = _function_local_skippables()
    assert "load_merged" in found, "load_merged() must define a local _SKIPPABLE tuple"
    assert "ParseError" in found["load_merged"], (
        f"load_merged() _SKIPPABLE must include ParseError so multi-period "
        f"strict=False skips a corrupted month. Got: {found['load_merged']}"
    )


# ── 2. Behavioural: a mocked ParseError IS swallowed under strict=False ──


def _registry_with_one_period() -> dict[str, Any]:
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
                "checksum_sha256": "a" * 64,
                "modules": {"ocupados": {"cabecera": "x.CSV"}},
                "validated": True,
            }
        },
    }


@pytest.fixture
def stubbed_pipeline_raising_parse_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mocker: Any,
):
    """Patch the pipeline so any parse_module call raises ParseError."""
    import pulso._config.registry as reg
    import pulso._core.downloader as dl_mod
    import pulso._core.parser as parser_mod
    from pulso._utils.exceptions import ParseError

    monkeypatch.setattr(reg, "_SOURCES", _registry_with_one_period())
    monkeypatch.setenv("PULSO_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(dl_mod, "verify_checksum", lambda *a, **kw: True)

    mock_response = MagicMock()
    mock_response.iter_content.return_value = [b"bytes"]
    mock_response.headers = {}
    mock_response.raise_for_status = MagicMock()
    mocker.patch("requests.get", return_value=mock_response)

    monkeypatch.setattr(
        parser_mod,
        "parse_module",
        MagicMock(side_effect=ParseError("simulated parser failure")),
    )


def test_parse_error_swallowed_under_strict_false(
    stubbed_pipeline_raising_parse_error,  # type: ignore[no-untyped-def]
) -> None:
    """Behavioural M-5 regression: with strict=False a ParseError MUST be
    caught and surfaced via the aggregated UserWarning, not propagated."""
    import pulso

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(year=2024, month=6, module="ocupados", strict=False)

    # Empty DataFrame because the only period failed, but no exception.
    assert isinstance(df, pd.DataFrame)
    assert df.empty

    # And we got an aggregated warning naming the failure.
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1
    msg = str(user_warnings[0].message)
    assert "failed to load" in msg
    assert "ParseError" in msg


def test_parse_error_propagated_under_strict_true(
    stubbed_pipeline_raising_parse_error,  # type: ignore[no-untyped-def]
) -> None:
    """Strict=True must keep the rc1 fail-fast contract for ParseError."""
    import pulso
    from pulso._utils.exceptions import ParseError

    with pytest.raises(ParseError, match="simulated"):
        pulso.load(year=2024, month=6, module="ocupados", strict=True)
