"""Apply validate_periods.py results to sources.json (canonical copy and R copy).

Aplica ``data/reference/validation_results.csv`` a ``data/sources.json`` y a
``r/inst/extdata/sources.json``:

* ``pass`` on a period with ``validated: false`` -> ``validated: true``,
  ``validated_by: "auto:validate_periods.py"``, ``validated_at`` (ISO UTC) and
  the pp differences appended to ``notes``.
* ``review`` / ``fail`` / ``pending`` / ``error`` never change the flag; they
  are listed in the report.
* A period already ``validated: true`` is never modified (never downgraded).
  If its new status is not ``pass`` it is flagged as a regression in the
  report instead.

Writing: values are serialized like ``agent_scraper.py`` (``ensure_ascii=True``,
``indent=2``), but only the four touched lines of each validated entry are
rewritten. The committed file mixes raw UTF-8 (``modules`` section) with
``\\uXXXX`` escapes (``data`` section), so a full ``json.dumps`` would also
rewrite ~480 unrelated lines. After patching, the text is re-parsed and must
equal the intended object exactly, otherwise nothing is written.

Usage:
    python python/scripts/apply_validation.py --dry-run
    python python/scripts/apply_validation.py --report validation_report.md
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = REPO_ROOT / "data" / "reference" / "validation_results.csv"
DEFAULT_SOURCES = REPO_ROOT / "data" / "sources.json"
DEFAULT_R_COPY = REPO_ROOT / "r" / "inst" / "extdata" / "sources.json"
VALIDATED_BY = "auto:validate_periods.py"


def _diff_note(row: dict[str, str]) -> str:
    parts = []
    for k in ("td", "to", "tgp"):
        d = float(row[f"{k}_pulso"]) - float(row[f"{k}_dane"])
        parts.append(f"{k.upper()} {d:+.3f}")
    return "Validacion automatica vs anexo DANE (pp): " + ", ".join(parts)


def apply_results(
    sources: dict[str, Any],
    results: list[dict[str, str]],
    now: dt.datetime | None = None,
) -> dict[str, list[str]]:
    """Mutate ``sources`` in place. Returns the report buckets."""
    stamp = (now or dt.datetime.now(dt.timezone.utc)).replace(microsecond=0).isoformat()
    report: dict[str, list[str]] = {
        "validated_now": [],
        "already_validated_ok": [],
        "regressions": [],
        "not_changed": [],
        "unknown_period": [],
    }
    for row in results:
        period, status = row["period"], row["status"]
        entry = sources["data"].get(period)
        if entry is None:
            report["unknown_period"].append(period)
            continue
        if entry.get("validated") is True:
            bucket = "already_validated_ok" if status == "pass" else "regressions"
            report[bucket].append(f"{period} ({status}, {row.get('max_abs_diff_pp') or '-'} pp)")
            continue
        if status != "pass":
            report["not_changed"].append(
                f"{period} ({status}, {row.get('max_abs_diff_pp') or '-'} pp)"
            )
            continue
        note = _diff_note(row)
        entry["validated"] = True
        entry["validated_by"] = VALIDATED_BY
        entry["validated_at"] = stamp
        entry["notes"] = f"{entry['notes']} | {note}" if entry.get("notes") else note
        report["validated_now"].append(period)
    return report


def render_report(report: dict[str, list[str]]) -> str:
    titles = {
        "validated_now": "Marcados como validados ahora",
        "already_validated_ok": "Ya validados, siguen en pass",
        "regressions": "REGRESIONES: ya validados que ya no pasan (flag sin cambios)",
        "not_changed": "Sin cambio de flag (review / fail / pending / error)",
        "unknown_period": "Periodos del CSV que no existen en sources.json",
    }
    lines = ["# Reporte de apply_validation", ""]
    for key, title in titles.items():
        items = report[key]
        lines.append(f"## {title} ({len(items)})")
        lines.extend(f"- {i}" for i in items)
        lines.append("")
    return "\n".join(lines)


def read_results(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


PATCHED_FIELDS = ("validated", "validated_by", "validated_at", "notes")


def write_sources(sources: dict[str, Any], path: Path) -> None:
    """Full rewrite, same serializer as agent_scraper.write_sources (LF forced on Windows)."""
    path.write_text(
        json.dumps(sources, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def entry_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per period, the PATCHED_FIELDS whose value differs between two catalogs."""
    out: dict[str, dict[str, Any]] = {}
    for period, new in after["data"].items():
        old = before["data"][period]
        diff = {f: new.get(f) for f in PATCHED_FIELDS if old.get(f) != new.get(f)}
        if diff:
            out[period] = diff
    return out


def patch_sources_text(text: str, changes: dict[str, dict[str, Any]]) -> str:
    """Rewrite only the touched field lines of each changed ``data`` entry.

    Expects the ``indent=2`` layout: entries at 4 spaces, fields at 6. Each
    field must appear exactly once in its entry, otherwise ValueError.
    """
    lines = text.splitlines(keepends=True)
    try:
        data_idx = lines.index('  "data": {\n')
    except ValueError as exc:
        raise ValueError('no top-level "data" object at indent 2') from exc
    starts = {
        line.strip()[1:8]: i
        for i, line in enumerate(lines)
        if i > data_idx and line.startswith('    "') and line.rstrip().endswith("{")
    }
    for period, fields in changes.items():
        if period not in starts:
            raise ValueError(f"entry {period} not found in data section")
        i = starts[period] + 1
        seen: set[str] = set()
        while not lines[i].startswith("    }"):
            for f, value in fields.items():
                prefix = f"      {json.dumps(f)}: "
                if lines[i].startswith(prefix):
                    if f in seen:
                        raise ValueError(f"{period}: field {f} appears twice")
                    comma = "," if lines[i].rstrip("\r\n").endswith(",") else ""
                    lines[i] = f"{prefix}{json.dumps(value, ensure_ascii=True)}{comma}\n"
                    seen.add(f)
            i += 1
        missing = set(fields) - seen
        if missing:
            raise ValueError(f"{period}: fields {sorted(missing)} not found on their own line")
    return "".join(lines)


def write_patched(path: Path, changes: dict[str, dict[str, Any]]) -> None:
    """Patch ``path`` in place; refuse to write unless the result parses to the intent."""
    text = path.read_text(encoding="utf-8")
    expected = json.loads(text)
    for period, fields in changes.items():
        expected["data"][period].update(fields)
    new_text = patch_sources_text(text, changes)
    if json.loads(new_text) != expected:
        raise RuntimeError(f"patched {path} does not round-trip to the intended catalog")
    path.write_text(new_text, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--r-copy", type=Path, default=DEFAULT_R_COPY)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    before = json.loads(args.sources.read_text(encoding="utf-8"))
    sources = copy.deepcopy(before)
    report = apply_results(sources, read_results(args.results))
    changes = entry_changes(before, sources)
    text = render_report(report)
    print(text)
    if args.report:
        args.report.write_text(text, encoding="utf-8", newline="\n")
    if not args.dry_run and changes:
        write_patched(args.sources, changes)
        if args.r_copy:
            write_patched(args.r_copy, changes)
    return 1 if report["regressions"] else 0


if __name__ == "__main__":
    sys.exit(main())
