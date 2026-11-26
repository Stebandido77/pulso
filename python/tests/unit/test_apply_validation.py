"""Unit tests for python/scripts/apply_validation.py."""

from __future__ import annotations

import copy
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from apply_validation import (  # noqa: E402
    VALIDATED_BY,
    apply_results,
    entry_changes,
    main,
    patch_sources_text,
    write_patched,
    write_sources,
)

DATA = Path(__file__).resolve().parents[3] / "data"
NOW = dt.datetime(2026, 11, 26, 12, 0, 0, tzinfo=dt.UTC)


def _sources() -> dict:
    return {
        "metadata": {"schema_version": "1.1.0"},
        "data": {
            "2024-05": {
                "validated": False,
                "validated_by": None,
                "validated_at": None,
                "notes": None,
            },
            "2024-06": {
                "validated": True,
                "validated_by": "manual",
                "validated_at": "2026-05-02T02:49:04+00:00",
                "notes": "manual",
            },
            "2024-07": {
                "validated": False,
                "validated_by": None,
                "validated_at": None,
                "notes": "x",
            },
            "2024-08": {
                "validated": False,
                "validated_by": None,
                "validated_at": None,
                "notes": None,
            },
        },
    }


def _row(period: str, status: str, d: float = 0.0) -> dict[str, str]:
    return {
        "period": period,
        "td_pulso": f"{10 + d:.6f}",
        "td_dane": "10.000000",
        "to_pulso": "57.000000",
        "to_dane": "57.000000",
        "tgp_pulso": "63.000000",
        "tgp_dane": "63.000000",
        "max_abs_diff_pp": f"{abs(d):.6f}",
        "status": status,
        "notes": "",
    }


def test_pass_marks_period_validated_with_audit_fields() -> None:
    s = _sources()
    report = apply_results(s, [_row("2024-05", "pass", 0.02)], now=NOW)
    e = s["data"]["2024-05"]
    assert e["validated"] is True
    assert e["validated_by"] == VALIDATED_BY == "auto:validate_periods.py"
    assert e["validated_at"] == "2026-11-26T12:00:00+00:00"
    assert (
        e["notes"] == "Validacion automatica vs anexo DANE (pp): TD +0.020, TO +0.000, TGP +0.000"
    )
    assert report["validated_now"] == ["2024-05"]


def test_existing_notes_are_kept() -> None:
    s = _sources()
    apply_results(s, [_row("2024-07", "pass")], now=NOW)
    assert s["data"]["2024-07"]["notes"].startswith("x | Validacion automatica")


@pytest.mark.parametrize("status", ["review", "fail", "pending", "error"])
def test_non_pass_never_changes_the_flag(status: str) -> None:
    s = _sources()
    before = copy.deepcopy(s)
    report = apply_results(s, [_row("2024-08", status, 0.3)], now=NOW)
    assert s == before
    assert report["not_changed"] == [f"2024-08 ({status}, 0.300000 pp)"]


@pytest.mark.parametrize("status", ["pass", "review", "fail", "pending", "error"])
def test_already_validated_period_is_never_modified(status: str) -> None:
    """A validated period is never downgraded nor re-stamped, whatever the result."""
    s = _sources()
    before = copy.deepcopy(s["data"]["2024-06"])
    report = apply_results(s, [_row("2024-06", status, 2.0)], now=NOW)
    assert s["data"]["2024-06"] == before
    if status == "pass":
        assert report["already_validated_ok"]
        assert not report["regressions"]
    else:
        assert report["regressions"] == [f"2024-06 ({status}, 2.000000 pp)"]


def test_unknown_period_is_reported() -> None:
    s = _sources()
    report = apply_results(s, [_row("1999-01", "pass")], now=NOW)
    assert report["unknown_period"] == ["1999-01"]


def test_applied_real_catalog_still_matches_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    schema = json.loads((DATA / "schemas" / "sources.schema.json").read_text(encoding="utf-8"))
    period = next(p for p, e in sources["data"].items() if not e["validated"])
    apply_results(sources, [_row(period, "pass")], now=NOW)
    jsonschema.validate(sources, schema)


def test_patch_on_real_catalog_touches_only_the_four_fields(tmp_path: Path) -> None:
    """Only validated/validated_by/validated_at/notes lines change; LF kept; ASCII values."""
    src = DATA / "sources.json"
    out = tmp_path / "sources.json"
    out.write_bytes(src.read_bytes())
    before = json.loads(src.read_text(encoding="utf-8"))
    after = copy.deepcopy(before)
    periods = [p for p, e in before["data"].items() if not e["validated"]][:3]
    apply_results(after, [_row(p, "pass", 0.05) for p in periods], now=NOW)
    changes = entry_changes(before, after)
    assert set(changes) == set(periods)

    write_patched(out, changes)

    assert json.loads(out.read_text(encoding="utf-8")) == after
    old_lines = src.read_bytes().split(b"\n")
    new_lines = out.read_bytes().split(b"\n")
    assert len(old_lines) == len(new_lines)
    assert b"\r" not in out.read_bytes()
    changed = [n for o, n in zip(old_lines, new_lines, strict=True) if o != n]
    assert len(changed) == 4 * len(periods)
    fields = {c.strip().split(b":")[0] for c in changed}
    assert fields == {b'"validated"', b'"validated_by"', b'"validated_at"', b'"notes"'}
    assert all(c.isascii() for c in changed)


def test_patch_refuses_unknown_entry() -> None:
    text = json.dumps(_sources(), ensure_ascii=True, indent=2) + "\n"
    with pytest.raises(ValueError, match="not found"):
        patch_sources_text(text, {"1999-01": {"validated": True}})


def test_main_writes_both_copies_and_exits_nonzero_on_regression(tmp_path: Path) -> None:
    sources = tmp_path / "sources.json"
    r_copy = tmp_path / "r_sources.json"
    results = tmp_path / "results.csv"
    write_sources(_sources(), sources)
    write_sources(_sources(), r_copy)
    header = ",".join(_row("x", "pass"))
    lines = [header] + [
        ",".join(_row(*a).values()) for a in [("2024-05", "pass"), ("2024-06", "fail", 1.0)]
    ]
    results.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rc = main(["--results", str(results), "--sources", str(sources), "--r-copy", str(r_copy)])
    assert rc == 1  # 2024-06 regressed
    assert sources.read_bytes() == r_copy.read_bytes()
    data = json.loads(sources.read_text(encoding="utf-8"))["data"]
    assert data["2024-05"]["validated"] is True
    assert data["2024-06"]["validated_by"] == "manual"
