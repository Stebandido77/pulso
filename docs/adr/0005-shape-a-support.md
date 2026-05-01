# ADR 0005: Shape A Support (GEIH-1, 2007-2021)

## Status

Accepted (Phase 3.2.B)

## Context

GEIH-1 microdata (2007-2021) uses a different file structure than GEIH-2 (Shape B):
- Each module has 3 physical CSVs inside the ZIP: Cabecera (urban), Resto (rural), Area (unknown semantics).
- Filenames have inconsistencies across years: typos (`"Caractericas"` vs `"Caracteristicas"` vs `"Características"`), missing accents, spacing variations (`"Cabecera-"` vs `"Cabecera - "`), and encoding issues (`╡rea` for `Área`).
- Files are ~6 MB per ZIP vs ~70 MB for Shape B (post-2022 redesign).

Phase 3.2.B enables loading any GEIH-1 month by auto-discovering the Cabecera/Resto files from the ZIP rather than requiring explicit paths in `sources.json`.

## Decision

### Auto-discovery via substring keyword matching

Implement three new functions in `pulso/_core/parser.py`:

1. **`is_shape_a(zip_path)`**: Detects Shape A by checking whether any entry in the ZIP's `namelist()` contains the string `"Cabecera"`. Shape B ZIPs use a flat `CSV/` folder without Cabecera prefixes.

2. **`find_shape_a_files(zip_path, module)`**: Scans the ZIP namelist and returns `(cabecera_path, resto_path)` for the requested module. Matching logic:
   - Accept only files whose basename starts with `"Cabecera"` or `"Resto"` (case-insensitive).
   - Discard all other prefixes (including `"Area"`).
   - Match against `MODULE_KEYWORDS_GEIH1[module]`, a list of Spanish substrings covering all known filename variants.

3. **`parse_shape_a_module(zip_path, module, epoch)`**: Loads Cabecera and Resto files and concatenates them, adding a synthetic `CLASE` column (`1` = Cabecera/urban, `2` = Resto/rural).

### dispatch in `parse_module()`

`parse_module()` dispatches as follows:

1. `is_shape_a(zip_path)` → `True`: use auto-discovery (`parse_shape_a_module`). This bypasses `sources.json` file-path lookups entirely.
2. `epoch.area_filter is None`: fallback Shape A lookup via explicit paths in `sources.json` (legacy path, preserved for backward compatibility).
3. `epoch.area_filter is not None`: Shape B (single unified file + CLASE row filter).

For backward compatibility, the auto-discovery path also adds a `_area` column (`"cabecera"` or `"resto"`) derived from `CLASE`, since existing callers expect it.

### Behavioral decision: load Cabecera + Resto, discard Area

- Cabecera + Resto are concatenated with `pd.concat(..., ignore_index=True)`.
- Area files are discarded. Their semantics are unclear (may be aggregates or auxiliary); no pulso module maps to them.
- The synthetic `CLASE` column makes the resulting DataFrame compatible with downstream code that filters on `CLASE` (same as Shape B).

## Consequences

### Positive

- 180 GEIH-1 entries (2007-2021) become parseable without requiring `sources.json` to list individual file paths.
- Phase 3.3 and later can validate against any month in 2007-2021.
- Tolerant to real-world DANE filename inconsistencies without per-year hacks.
- Backward compatible: Shape B regression (`pulso.load_merged(2024, 6)` → shape `(70020, 525)`) unchanged.

### Negative

- Area files are discarded. If they carry unique data, a future phase would need to revisit.
- `MODULE_KEYWORDS_GEIH1` is a maintained list; if DANE introduces a new naming variant, it must be added manually.

### Mitigations

- `find_shape_a_files` falls back to `None` rather than crashing on unknown filenames.
- `parse_shape_a_module` raises `ParseError` with diagnostic output (first 8 ZIP entries) if no matching file is found.
- 7 unit tests cover detection, keyword matching, typo handling, Area exclusion, and error raising.

## Alternatives considered

### Loading Area files as a third stream

Rejected. Area file semantics are not documented in DANE metadata. Loading them could corrupt the Cabecera+Resto population union.

### Per-year filename configuration in `sources.json`

Rejected. Would require manually mapping ~180 entries. Fuzzy keyword matching is more maintainable and already handles the known variants.

### Strict filename parsing (regex)

Rejected. Real DANE filenames are too inconsistent; substring matching with a known-good keyword list is simpler and more robust.

## References

- `pulso/_core/parser.py`: implementation
- `tests/unit/test_parser.py`: unit tests (7 new Shape A tests)
- `tests/integration/test_load_fixture.py`: integration test (`test_load_shape_a_geih1_fixture`)
- `tests/_build_fixtures.py`: `build_shape_a_zip()` fixture builder
- `docs/CATALOG_NOTES.md`: Phase 3.1 findings on GEIH-1 file structure

## Decision date

2026-05-01

## Authors

Builder (Claude in chat) + Esteban Labastidas
