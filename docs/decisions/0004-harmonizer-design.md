# ADR 0004: Harmonizer Design

**Status:** Accepted  
**Date:** 2026-04-29  
**Author:** Builder (Claude Code)

---

## Context

Phase 2 requires converting raw DANE column names and encodings into 30
canonical variables defined in `variable_map.json`. Three non-trivial design
decisions were made. All other implementation choices follow the spec in the
Phase 2 task description.

---

## Decision 1: Preserve raw columns alongside canonical (keep_raw=True)

**Decision**: `harmonize_dataframe` defaults to `keep_raw=True`, returning ALL
original DANE columns alongside the 30 canonical columns in the same DataFrame.

**Alternatives considered**:
- Return only canonical columns (drop raw). Simpler output but loses access to
  the ~200 DANE variables not covered by the canonical set.
- Return a separate `(raw_df, canonical_df)` tuple. Avoids column pollution but
  makes downstream usage awkward (users must join them back).

**Rationale**: pulso is a research facilitation tool. Economists need access to
any DANE variable, not just the 30 curated ones. A researcher studying a
specific question (e.g., migration, housing tenure) will need columns outside the
canonical set. By keeping raw columns, the output of `load(harmonize=True)` is
a superset that supports any downstream analysis without additional loading.

The 30 canonical columns are guaranteed cross-epoch comparable. Raw columns are
epoch-specific. Both are present and clearly distinguishable by name convention
(canonical names use snake_case Spanish; raw DANE names use uppercase codes like
P6040, INGLABO).

---

## Decision 2: Option A for condicion_actividad — pre-merge before custom function

**Decision**: `merge_labor_status` expects a pre-merged DataFrame containing
both OCI and DSI columns. The merger is responsible for the outer join; the
custom function only reads columns.

**Alternatives considered**:
- Option B: `merge_labor_status` receives the individual module DataFrames and
  performs the join itself. More self-contained but mixes merger semantics into
  the harmonizer layer.
- Option C: Add a special "cross_module" transform type in the schema. Cleaner
  schema but requires Architect involvement and a schema version bump.

**Rationale**: Separation of concerns. The merger knows how to join on epoch
merge keys. The custom function knows the domain semantics (OCI=1 → ocupado,
DSI=1 → desocupado, both NA → inactivo). Each layer does one thing. The
pre-merge pattern generalizes to any future variable that requires data from
multiple modules (e.g., `ingreso_total` which spans `ocupados` +
`otros_ingresos`).

---

## Decision 3: pd.DataFrame.eval() with manual fallback for .astype(str)

**Decision**: The `compute` transform uses `pd.DataFrame.eval(expr, engine='python')`
for arithmetic and boolean expressions. For expressions containing `.astype(str)`,
a dedicated manual parser splits on ` + ` and constructs the result from
`df[col].astype(str)` calls.

**Rationale**: `pd.eval` does not support `.astype()` method calls on columns.
Python's builtin `eval()` is off-limits (security: arbitrary code execution). The
manual parser is limited to the one pattern that appears in `variable_map.json`
(`hogar_id`'s concatenation expression). If new compute expressions with method
calls are added in future variables, the parser may need extension — document this
in PHASE_2_CODE_NOTES.md.

The manual parser handles: string literals (`'_'`, `"_"`), column references
with `.astype(str)`, and `+` concatenation. It raises `HarmonizationError` for
unrecognized patterns (fail-fast, no silent corruption).

---

## Consequences

- The harmonizer is stateless; `harmonize_variable` is a pure function of
  `(df, canonical_name, variable_entry, epoch)`. This makes it trivially testable.
- `keep_raw=True` means merged DataFrames can be wide (200+ raw columns after
  suffix expansion from 3-module outer join). For memory-constrained use cases,
  users can pass `keep_raw=False` or `variables=["subset"]`.
- The `merge_labor_status` heuristic for inactivo (`OCI.isna() & DSI.isna()`)
  is correct when the merged DataFrame is complete (all persons appear in exactly
  one of ocupados/no_ocupados). It may misclassify persons absent from both
  modules due to data quality issues. This limitation is documented in
  PHASE_2_CODE_NOTES.md.
