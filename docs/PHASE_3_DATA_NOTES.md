# Phase 3 Data Notes

## Phase 3.2.C: sources.json scaled to 230 entries

### Scale

| | Before | After |
|--|--------|-------|
| Entries | 1 (2024-06, Phase 1 manual) | 230 (2007-01 to 2026-02) |
| Shape A (geih_2006_2020) | 0 | 180 |
| Shape B (geih_2021_present) | 0 | 50 |

### Generation

Deterministic from `pulso/data/_scraped_catalog.json` via:

```bash
python scripts/generate_sources_from_catalog.py \
    --catalog pulso/data/_scraped_catalog.json \
    --output pulso/data/sources.json
```

The generator is idempotent: re-running produces the same output (given the same catalog).

### Decisions

#### Schema change: `checksum_sha256` made nullable

DANE does not publish checksums on their microdata portal. All 229 new entries have
`checksum_sha256: null`. The existing 2024-06 entry retains its manually computed
checksum. Phase 3.4 will populate real checksums for each entry after downloading
the ZIP files.

#### Canonical filenames declared (not actual disk filenames)

`sources.json` declares the expected canonical names (e.g.
`"Cabecera - Características generales (Personas).csv"`). The Shape A parser
(`is_shape_a` + `find_shape_a_files` in `pulso/_core/parser.py`) tolerates
real-world DANE filename variations via keyword matching:
- Missing accents: `"Caracteristicas generales"` vs `"Características generales"`
- 2007 typo: `"Caractericas generales"` (missing 't')
- Spacing: `"Cabecera-"` vs `"Cabecera - "`

Phase 3.3 (real-data validation) will confirm actual filenames and flag any that
don't match. No changes to `sources.json` are expected unless a module is entirely
missing from some year's ZIP.

#### 2024-06 entry preserved

The Phase 1 manually validated entry (with a real checksum, `validated: true`,
`validated_by: "manual"`) is preserved unchanged. The generator detects
`validated: true` and skips regeneration.

#### Shape A entries get 6 modules

GEIH-1 (2007-2021) does not have the `migracion` or `otras_formas_trabajo`
modules (introduced in GEIH-2 in 2022). The `available_in` field in
`CANONICAL_MODULES` enforces this — Shape A entries receive only the 6 modules
whose `available_in` list includes `"geih_2006_2020"`.

#### Shape B entries get 8 modules

GEIH-2 (2022-2026) includes all 8 canonical modules. File paths verified against
the 2024-06 ZIP (the only validated entry at this point).

#### row_filter omitted for new Shape B entries

`desocupados` and `inactivos` share `"CSV/No ocupados.CSV"` without `row_filter`.
This matches the existing 2024-06 pattern. Phase 3.4 (real-data validation) will
confirm the OCI column values and add `row_filter` if needed.

### Out of scope (subsequent sprints)

- Downloading any ZIP file (Phase 3.4)
- Computing real checksums (Phase 3.4)
- Verifying that all 230 entries load without errors (Phase 3.3)
- Adding `row_filter` for desocupados/inactivos after confirming OCI (Phase 3.4)
