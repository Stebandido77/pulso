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

## Phase 3.4: Real-Data Validation

### Months validated

| Month | Shape | Size | Download URL |
|---|---|---|---|
| 2007-12 | A (GEIH-1) | 6.4 MB | catalog/317/download/10934 |
| 2015-06 | A (GEIH-1) | 6.7 MB | catalog/356/download/13061 |
| 2021-12 | A (GEIH-1, last) | 5.9 MB | catalog/701/download/20902 |
| 2022-01 | B (GEIH-2, first) | 77 MB | catalog/771/download/22688 |
| 2024-06 | B (GEIH-2) | 67 MB | catalog/819/download/23625 |

### Results

- All 5 ZIPs downloaded and verified structurally (non-empty, contain CSV files)
- 4 of 5 months load `caracteristicas_generales` module without errors
- Phase 2 regression intact: `load_merged(2024, 6, harmonize=True).shape == (70020, 525)`
- 4 SHA-256 checksums computed and written to `sources.json` (2024-06 unchanged)
- `sources.json` file paths for 2022-01 corrected (see Finding 3 below)

### Findings

#### Finding 1 — UTF-8 BOM in GEIH-1 CSVs (2007-12, 2015-06)

Early GEIH-1 files embed a UTF-8 BOM (`\xef\xbb\xbf`) at the start of the CSV.
The epoch encoding is `latin-1`. When pandas reads these files with `latin-1`,
the BOM bytes decode to the three-character sequence `ï»¿`, which becomes a
prefix on the first column name:
- 2007-12: `DIRECTORIO` → `ï»¿DIRECTORIO`
- 2015-06: `Directorio` → `ï»¿Directorio` (also mixed-case column names in this year)

**Impact**: Merge keys (`DIRECTORIO`, `SECUENCIA_P`, `ORDEN`) are unaffected in name
(the BOM only affects the first column), but the mangled first-column name breaks any
code that uses `df["DIRECTORIO"]` to access the column. The parser (`parse_shape_a_module`)
still loads the data; harmonizer and merger would fail downstream.

**Fix needed**: Change epoch encoding from `latin-1` to `utf-8-sig` for files with BOM,
or add BOM-stripping to `parse_shape_a_module`. Requires `pulso/_core/` change.

**Workaround in smoke tests**: The `test_real_zip_loads_caracteristicas_module` test
accepts any column containing "DIRECTORIO" (case-insensitive substring match) to
accommodate both BOM-prefixed and clean column names.

#### Finding 2 — Mixed-case column names in 2015-06

Beyond the BOM issue, the 2015-06 Cabecera CSV uses mixed-case column names:
`Directorio;Secuencia_p;Orden;Hogar;...` instead of `DIRECTORIO;SECUENCIA_P;ORDEN;...`.
This is different from both 2007 (all caps) and 2021+ (consistent all caps).
The merger uses hardcoded keys `["DIRECTORIO", "SECUENCIA_P", "ORDEN"]` which would
fail to merge 2015-06 data.

**Fix needed**: Column name normalization (`.str.upper()`) in the merger or parser.
Requires `pulso/_core/` change. Filed as known issue.

#### Finding 3 — 2022-01 ZIP folder prefix and comma separator

The first GEIH-2 release (January 2022) uses a different packaging convention:
- Files are under `GEIH_Enero_2022_Marco_2018/CSV/` (outer folder), not `CSV/` directly
- CSV separator is `,` (comma), not `;` (semicolon) as used in 2024-06

**sources.json fix applied**: File paths for 2022-01 have been updated to include
the `GEIH_Enero_2022_Marco_2018/` prefix with correct case for each filename.

**Unresolved**: The comma separator cannot be fixed via sources.json — it requires
either a per-entry `separator` override in sources.json (not currently supported by the
schema) or a change to how `parse_module` reads the epoch separator. The
`test_real_zip_loads_caracteristicas_module[2022-01]` test is skipped until this is resolved.

**Implication**: Other early GEIH-2 months (2022-01 through ~2022-12) may also use comma
separator and/or folder prefixes. These need to be checked against real downloads.

#### Finding 4 — 2007-12 contains `Cabecera- Ocupados.csv` (no space before dash)

The 2007-12 ZIP has `Cabecera- Ocupados.csv` (no space between "Cabecera" and the dash)
for the `ocupados` module. The word-boundary fix in Phase 3.3.1 handles this correctly
(the file is found via keyword "Ocupados"), but the file path in `sources.json` declares
`"Cabecera - Ocupados.csv"` (with space). This is intentional: sources.json declares the
canonical form; the parser uses keyword matching, not exact path matching for Shape A.

### SHA-256 checksums

Updated in `sources.json`:
- `2007-12`: `ec339fca43a262fb...`
- `2015-06`: `361f8c4244be9785...`
- `2021-12`: `607ece9b97744df9...`
- `2022-01`: `48d6bd634c3c98e4...`
- `2024-06`: unchanged (`c5799177604b0e08...`)

### Out of scope

- Validating remaining 225 entries (would require ~30 GB of downloads)
- Automatic CI execution of `real_data` tests (slow, network-dependent)
- Fixing the BOM encoding issue in `pulso/_core/` (tracked as a separate issue)
- Fixing the comma separator compatibility for early GEIH-2 months
