# 0005 — Phase 4 Roadmap: Technical Debt and Feature Completion

**Status:** Proposed  
**Date:** 2026-05-02  
**Author:** Architect  
**Scope:** `pulso/_core/`, `pulso/data/`, `tests/`

---

## Context

Phase 3.5 (Empalme loader + `apply_smoothing`) closed the main data-coverage gap. The library now loads GEIH from 2006-01 to present, handles the epoch boundary at 2022-01, and exposes the Empalme smoothing series for 2010–2019.

Three categories of technical debt and planned features remain before a PyPI release (Phase 5):

- **Line A** — Parser correctness: Shape A mixed-case columns (issue #42)
- **Line B** — Variable introspection API (four `NotImplementedError` functions)
- **Line C** — Formal architecture documentation

This RFC documents each line, proposes an execution order, and records open questions that require human input before implementation starts.

---

## Lines of Work

### Line A — Shape A parser: column case normalization (issue #42)

**Problem confirmed.**  
`load_merged(2015, 6)` fails with `MergeError` because the `vivienda_hogares` module CSV for some GEIH-1 months delivers mixed-case columns (`Hogar`, `Area`, `Fex_c_2011`). The merger performs case-sensitive key lookup and rejects the DataFrame. This is a latent bug: no existing test exercised `load_merged` for a pre-2022 month end-to-end until Phase 3.5 exposed it.

**Scope of impact.**  
Likely affects multiple GEIH-1 months (2006–2021), all modules — not just `vivienda_hogares`. A survey of `~180 Shape A entries × 8 modules` is needed to establish full extent. Severity is HIGH because `load_merged` for affected months raises an exception instead of returning data.

**Proposed fix.**  
Apply the same column normalization already implemented in `_normalize_empalme_columns()` (empalme.py) to the Shape A parse path:

1. Uppercase all column names after `_read_csv_with_fallback()` in `parse_shape_a_module()`.
2. Rename `FEX_C_XXXX` → `FEX_C` for GEIH-1 weight columns.
3. Extract a shared helper (e.g. `_normalize_dane_columns(df, epoch)` in `parser.py`) reused by both Shape A and Shape C paths.

**Why not done in Phase 3.5.**  
Phase 3.5 fixed only the Empalme (Shape C) path, which was in scope. Touching `parse_shape_a_module()` would require re-validating all 180+ Shape A entries and is a separate risk surface.

**Owner:** Builder  
**Suggested branch:** `fix/code-shape-a-column-normalization`  
**Acceptance criteria:**
- `load_merged(2015, 6)` completes without error.
- Survey of all 5 validated months: `load_merged(year, month)` returns data for all.
- Existing 433-test suite continues to pass.
- Integration test for `load_merged(year, month)` added for at least 3 pre-2022 months.

---

### Line B — Variable introspection API

**Problem.**  
Four public functions have been stubs since Phase 2:

```python
pulso.list_variables()          # → NotImplementedError("Phase 2")
pulso.describe_variable(name)   # → NotImplementedError("Phase 2")
pulso.describe_harmonization(v) # → NotImplementedError("Phase 2")
pulso.describe(module, year)    # → ConfigError (wrong error type)
```

These functions are documented in the README as 🚧 planned and are important for researcher discoverability (understanding which variables are available and how they're harmonized across epochs).

**Implementation notes.**  
All four functions read from `variable_map.json` and `epochs.json`, which are already loaded and validated. No new data files are needed. The main design question is the **output schema** for each function (see Open Questions).

**Rough scope:**
- `list_variables()` → DataFrame: canonical name, type, level (persona/hogar), module, available epochs, comparability warning flag.
- `describe_variable(name)` → dict: definition (ES + EN), type, unit, epoch mappings, comparability warning.
- `describe_harmonization(variable)` → DataFrame: one row per epoch, columns = source_variable, transform, source_doc, notes.
- `describe(module, year)` → dict: module metadata + epoch key + available variables for that (module, epoch) combination.

**Owner:** Builder + Curator (Builder implements, Curator adds descriptive fields to variable_map.json if needed)  
**Suggested branch:** `feat/code-variable-introspection`  
**Acceptance criteria:**
- All four functions return data without raising.
- Unit tests for each function with fixture data.
- README 🚧 → ✅ for all four.
- `describe_variable("sexo")` returns a dict with `"mappings"` key covering both epochs.

---

### Line C — Architecture documentation

**Problem.**  
The repository has `PHASE_*_NOTES.md` (development logs) and individual ADRs, but no single document explaining:

- The three data shapes (A, B, C) and how they're detected and parsed.
- The full pipeline: `download → parse → merge → harmonize`.
- How `pulso/_core/` is organized and why modules are separated the way they are.
- The Builder/Curator split and branch enforcement conventions.
- Active architectural decisions (epoch boundary, checksum verification, cache layout).

New contributors and reviewers cannot understand the codebase without reconstructing this from scattered files. This is especially important before a public release.

**Deliverable.**  
`docs/architecture.md` covering:

1. **Overview diagram** (ASCII or Mermaid) of the package layers.
2. **Data shapes** — A (Cabecera+Resto), B (unified GEIH-2), C (Empalme) — with detection logic and parser entry points.
3. **Pipeline walkthrough** — `download_zip()` → `parse_module()` → `merge_modules()` → `harmonize_dataframe()` → user-facing `load_merged()`.
4. **Module map** — one paragraph per `_core/` file explaining its responsibility.
5. **Registry files** — what each file in `pulso/data/` contains and who owns it.
6. **Builder/Curator split** — definition, branch conventions, CI enforcement.
7. **Epoch contract** — why the boundary is 2022-01 and what "epoch-aware" means in practice.

**Owner:** Architect  
**Suggested branch:** `docs/shapes-architecture` (this branch)  
**Acceptance criteria:**
- `docs/architecture.md` exists and is accurate to the current codebase.
- No code changes in this line.
- Reviewed and approved by human (@Stebandido77) before merge.

---

## Proposed Execution Order

```
C (Architecture docs) → A (Shape A normalization) → B (Variable introspection)
```

**Rationale:**

1. **C first** — Architecture documentation stabilizes the shared mental model before making code changes. The Shape A fix (A) and the introspection API (B) both touch `parser.py` and `_core/`; having documented contracts reduces the risk of conflicting assumptions.

2. **A before B** — Shape A normalization is a **correctness bug** (raises exceptions on valid inputs). It should be fixed before adding new features. It also potentially informs the column normalization story for Line C's architecture docs.

3. **B last** — Variable introspection is a feature addition (no existing code breaks without it). It depends on having a stable `variable_map.json` (Curator-owned) and clear API contracts (stabilized by C).

**Estimated effort:**

| Line | Effort | Risk |
|------|--------|------|
| C | 1–2 days (Architect) | Low |
| A | 2–4 days (Builder) + integration test run | Medium |
| B | 3–5 days (Builder) | Low–Medium |

---

## Decisions — All Resolved (2026-05-02)

The four open questions from the original RFC have been answered. Decisions are recorded below with justification.

### Decision OQ-1: Shape A normalization — **Option 3 (broad + rename)**

**Chosen:** Uppercase ALL columns in `parse_shape_a_module()` + rename `FEX_C_XXXX → FEX_C`.

**Justification:** Option 3 produces full consistency across all three shapes (A, B, C). Shape C already does this via `_normalize_empalme_columns()`; Shape A must match so that downstream code (merger, harmonizer, user code) sees identical column conventions regardless of the data source. The `variable_map.json` entry for `geih_2006_2020` must be updated from `source_variable: "fex_c_2011"` to `source_variable: "FEX_C"` as part of this change (coordinated Builder + Curator PRs).

**Consequence:** A shared helper `_normalize_dane_columns()` in `parser.py` replaces the duplicated logic in `empalme.py::_normalize_empalme_columns()`. Column name `fex_c_2011` is no longer exposed to users; `FEX_C` is the canonical name. Any user code checking for `fex_c_2011` directly must be updated — this is acceptable because the library is pre-v1.0.

---

### Decision OQ-2: `describe_variable()` output format — **dict**

**Chosen:** `describe_variable(name)` returns a Python `dict`.

**Justification:** Researchers coming from JSON APIs and REPL-driven workflows find dicts easier to inspect than dataclasses. The nested structure of epoch mappings (`{"geih_2006_2020": {"source_variable": ...}, ...}`) maps naturally to a dict; flattening it into a DataFrame would require awkward multi-level indexing. The return value mirrors the structure already present in `variable_map.json`, minimizing transformation overhead.

`describe_harmonization(variable)` returns a `pd.DataFrame` (one row per epoch) — consistent with `list_variables()` and easy to display in notebooks.

---

### Decision OQ-3: `describe(module, year)` scope — **combined view**

**Chosen:** Returns a combined dict with `{module_metadata, available_periods, harmonized_variables, raw_columns}`. `year` is optional; if provided, filters to that epoch.

**Justification:** Researchers want to know both _what modules exist_ and _which harmonized variables they feed_. A combined view answers "what can I get from `ocupados` in 2015?" without chaining multiple calls. The `year` filter maps to an epoch key, so the implementation reuses the existing epoch-resolution logic.

**Shape:**
```python
{
    "module": "ocupados",
    "level": "persona",
    "description_es": "...",
    "available_epochs": ["geih_2006_2020", "geih_2021_present"],
    "harmonized_variables": ["sexo", "edad", "condicion_actividad", ...],
    "raw_columns_sample": ["P6020", "P6040", "FEX_C", ...],  # from variable_map
}
```

---

### Decision OQ-4: PyPI v1.0 prerequisites — **Line C + Line A required; Line B deferred to v1.1**

**Chosen execution order: C → A → v1.0 → B → v1.1**

| Milestone | Required lines | Rationale |
|-----------|---------------|-----------|
| v1.0 (PyPI first release) | C (architecture docs) + A (parser fix) | Correctness bug (#42) and undocumented architecture are blocking for a public release |
| v1.1 | B (variable introspection) | Feature addition, not a correctness issue; `list_variables()` etc. can be 🚧 planned at v1.0 |

**Justification:** A PyPI release with a known `MergeError` on valid inputs (issue #42) is unacceptable. Architecture docs (Line C) stabilize the codebase contract before the parser surgery of Line A. Line B is a pure feature addition — researchers can use the library productively at v1.0 without it.

---

## Decisions Already Taken (from Phase 3 / 3.5)

The following design choices were settled before this RFC and are recorded here for completeness:

- **Epoch boundary = 2022-01.** Confirmed empirically via `epoch_for_month()`. The old README said 2020→2021; this is corrected.
- **Shape C (Empalme) normalizes to uppercase.** `_normalize_empalme_columns()` uppercases all columns and renames `FEX_C_XXXX → FEX_C`. This decision is local to the Empalme path.
- **Checksums for Empalme entries are computed offline by the Curator.** The Builder's `download_empalme_zip()` does not verify checksums yet (PR #43 filled the checksums; future PR to wire verification).
- **`apply_smoothing=True` for year=2020 warns and falls back.** Year 2020 Empalme ZIP is not published; the smoothing path degrades gracefully.
- **Builder/Curator split is enforced by CI.** Branch `feat/code-*` cannot touch `pulso/data/`; branch `feat/data-*` cannot touch `pulso/_core/`. This constraint is intentional and documented in [`CONTRIBUTING.md`](../../CONTRIBUTING.md).
