# ADR 0003: Schema 1.1 — Module files, area filtering, and GEIH-2 modules

- **Status:** Accepted
- **Date:** 2026-04-28
- **Deciders:** project owner + architect
- **Supersedes:** parts of `0001-build-plan.md` (the schema description)
- **Related issues:** Phase 1 Curator findings (3 issues opened during PR review)

## Context

When the Curator (Phase 1) downloaded the real DANE GEIH ZIP for June 2024 and inspected it, the structure differed from the schema's assumptions in three substantive ways:

1. **Module count.** The ZIP contains **8 modules**, not 6. Two of them (`Migración`, `Otras formas de trabajo`) are new in GEIH-2 (post-OIT redesign) and have no equivalent in GEIH-1.
2. **No physical Cabecera/Resto split.** GEIH-1 (2006-2020) delivered each module as two separate files (`Cabecera/X.CSV`, `Resto/X.CSV`). GEIH-2 (2021-present) delivers a single nationwide file per module; the urban/rural distinction is encoded in a column `CLASE`:
   - `CLASE = 1` → cabecera municipal (urban)
   - `CLASE = 2` → centro poblado
   - `CLASE = 3` → rural disperso
3. **`desocupados` and `inactivos` share a file.** Both map to `No ocupados.CSV` in GEIH-2 and need a row-level filter to be separated.

The schema as defined in v1.0.0 (`ModuleFiles` requiring `cabecera` and/or `resto` as filename strings) cannot model GEIH-2 honestly.

## Decision

Bump schema to **1.1.0** with three coordinated changes:

### Change 1 — Add two canonical modules

Extend the `modules` registry in `sources.json`:

```json
"migracion": {
  "level": "persona",
  "description_es": "Historial migratorio de las personas: lugar de nacimiento, residencia anterior, motivos de migración.",
  "description_en": "Migration history: birthplace, previous residence, migration reasons.",
  "available_in": ["geih_2021_present"]
},
"otras_formas_trabajo": {
  "level": "persona",
  "description_es": "Trabajo informal, autoempleo, trabajo de subsistencia y otras formas no clasificadas como ocupación principal (módulo nuevo post-OIT 2021).",
  "description_en": "Informal/gig/own-account/subsistence work (new module post-ILO 2021 redesign).",
  "available_in": ["geih_2021_present"]
}
```

`available_in` lists which epochs the module exists in. The 6 original modules are available in both epochs; the two new ones only in GEIH-2.

### Change 2 — `epochs.json` gains `area_filter`

Each epoch declares **how its files split urban/rural**:

```json
"geih_2006_2020": {
  ...
  "area_filter": null
},
"geih_2021_present": {
  ...
  "area_filter": {
    "column": "CLASE",
    "cabecera_values": [1],
    "resto_values": [2, 3]
  }
}
```

When `area_filter` is `null` (GEIH-1), files are physically separated and `ModuleFiles.cabecera` and `ModuleFiles.resto` are used as in v1.0.0.

When `area_filter` is set (GEIH-2), there's a single file (`ModuleFiles.file`) and the loader applies a row filter `df[df[column].isin(cabecera_values)]` etc.

### Change 3 — `ModuleFiles` becomes polymorphic

Two valid shapes, validated via `oneOf`:

**Shape A (epoch with `area_filter: null`, e.g. GEIH-1):**

```json
"ocupados": {
  "cabecera": "Cabecera/Cabecera - Ocupados.CSV",
  "resto": "Resto/Resto - Ocupados.CSV"
}
```

(Same as v1.0.0; backward compatible.)

**Shape B (epoch with `area_filter`, e.g. GEIH-2):**

```json
"ocupados": {
  "file": "CSV/Ocupados.CSV"
}
```

Optionally with a row filter for cases where multiple canonical modules share a file:

```json
"desocupados": {
  "file": "CSV/No ocupados.CSV",
  "row_filter": {
    "column": "OCI",
    "values": [2]
  }
},
"inactivos": {
  "file": "CSV/No ocupados.CSV",
  "row_filter": {
    "column": "OCI",
    "values": [3, 4]
  }
}
```

Validation rule: `MonthRecord.modules[X]` must use Shape A if its epoch has `area_filter: null`, Shape B if `area_filter` is set. The schema enforces this through conditional `oneOf` references.

## Consequences

### Positive

- **Schema honestly reflects the data.** The structural difference between GEIH-1 and GEIH-2 is preserved, not hidden in code branches.
- **Code stays generic.** The loader doesn't need `if epoch == "geih_X"`; it reads `area_filter` from the epoch and applies it.
- **Future-proof.** If DANE adds another redesign with yet another delivery format, the schema can express it without ripping out code.
- **Backward compatible.** v1.0.0 entries (currently zero in `data`) remain valid as Shape A. Phase 4 (GEIH-1 coverage) continues using Shape A.

### Negative

- **Schema is more complex.** Reviewers need to understand the polymorphism. Mitigated by the `oneOf` formal definition and examples in `docs/`.
- **Loader logic is conditional.** When parsing a record, the loader first checks the epoch's `area_filter` and dispatches to one of two paths.
- **Existing prompts to Builder/Curator need amendment.** Phase 1 prompts assumed Shape A only; future phases will reference both.

### Mitigations

- ADR 0003 (this document) is the canonical reference; reviewers point newcomers here.
- The `tests/unit/test_schemas.py` should add tests covering both shapes once Phase 1 closes.
- The Builder's parser implementation needs a `_resolve_module_files()` helper that abstracts the polymorphism away from the parsing logic.

## Deferred decisions

- **The `row_filter` column for `desocupados` vs `inactivos`** is not finalized in this ADR. The Curator's PHASE_1_DATA_NOTES did not confirm which exact column distinguishes the two inside `No ocupados.CSV`. We defer this to Phase 2 when the Builder works against the real ZIP and can inspect the file. For Phase 1, both modules will map to `No ocupados.CSV` without `row_filter`, and the Curator notes this in `notes`. Users who load `desocupados` will get the full no-ocupados population until Phase 2 closes the gap.

- **The `P6020 → P6016` rename** for the sex variable is purely a `variable_map.json` concern (Phase 2). No schema change needed for it; it's exactly the kind of transformation `variable_map.json` was designed for.

## Schema migration

Going from v1.0.0 to v1.1.0:

- All bundled JSON files (`epochs.json`, `sources.json`) update their `metadata.schema_version` to `"1.1.0"`.
- `epochs.json`: each epoch gets an `area_filter` field (null or object).
- `sources.json`: `modules` registry gets two new entries.
- `pulso/data/schemas/sources.schema.json`: `ModuleFiles` becomes `oneOf` two shapes; `ModuleDefinition` adds `available_in` (already there); `MonthRecord.modules` validation gains conditional rules.
- `pulso/data/schemas/epochs.schema.json`: `Epoch` gains `area_filter` field (nullable object).

The variable_map schema is unchanged — all variable harmonization remains as v1.0.0.

## Notes for implementers (Builder, Phase 1+)

When implementing the parser:

1. Read epoch first; check `area_filter`.
2. Read the module's `ModuleFiles` entry.
3. If `area_filter` is null: use Shape A logic (load `cabecera` file or `resto` file based on requested area; `total` concatenates).
4. If `area_filter` is set: load the single `file`; apply `row_filter` if present; then apply `area_filter` based on requested area (`cabecera` or `resto` filters by column values; `total` keeps all rows).

A helper like `resolve_module_files(record, area, epoch)` returning `list[FileSpec]` (each with optional pre-filters) abstracts this cleanly.
