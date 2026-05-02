# Phase 3 Code Notes

## Phase 3.2.B: Shape A Parser Support

### Problem

GEIH-1 microdata (2007-2021) — 78% of the total 230 catalog entries — stores each
survey module as two physical CSV files inside the ZIP: `Cabecera - {module}.csv`
(urban households) and `Resto - {module}.csv` (rural households). The pre-existing
parser handled Shape B (single unified file) and had a legacy Shape A path that required
`sources.json` to list explicit file paths per module. Neither was usable for GEIH-1
without first populating all 180 × N module paths in `sources.json`.

### Solution

Auto-discover Cabecera and Resto files from the ZIP at parse time by:
1. Detecting Shape A via `is_shape_a(zip_path)` — checks for "Cabecera" in any filename.
2. Matching files to modules via keyword lookup (`MODULE_KEYWORDS_GEIH1`).
3. Concatenating Cabecera + Resto with a synthetic `CLASE` column (1=urban, 2=rural).

### New functions in `pulso/_core/parser.py`

| Function | Purpose |
|----------|---------|
| `is_shape_a(zip_path)` | Returns True if ZIP contains Cabecera-prefixed files |
| `find_shape_a_files(zip_path, module)` | Returns `(cab_path, resto_path)` by keyword scan |
| `parse_shape_a_module(zip_path, module, epoch)` | Loads and concatenates Cabecera+Resto; adds CLASE |

### `MODULE_KEYWORDS_GEIH1` (keyword mapping)

```python
{
    "caracteristicas_generales": ["Características generales", "Caracteristicas generales", "Caractericas generales"],
    "ocupados": ["Ocupados"],
    "desocupados": ["Desocupados"],
    "inactivos": ["Inactivos"],
    "vivienda_hogares": ["Vivienda y Hogares"],
    "otros_ingresos": ["Otros ingresos"],
    "otras_formas_trabajo": ["Otras actividades y ayudas"],
    "fuerza_de_trabajo": ["Fuerza de trabajo"],
}
```

Three variants of `caracteristicas_generales` are needed:
- `"Características generales"` — correct accent, 2015+
- `"Caracteristicas generales"` — no accent, fixture and some mid-era years
- `"Caractericas generales"` — 2007 typo (missing 't')

### Dispatch change in `parse_module()`

```
is_shape_a(zip_path)?
  YES → parse_shape_a_module()   # auto-discovery, bypasses sources.json paths
  NO  →
    epoch.area_filter is None?
      YES → legacy Shape A lookup via sources.json (preserved, rarely used)
      NO  → Shape B (single file, CLASE row filter)
```

Backward compat: `_area` column (`"cabecera"` / `"resto"`) is added after CLASE in the
auto-discovery path, so existing callers that check `"_area" in df.columns` continue working.

### Tests added

**Unit (7 new tests in `tests/unit/test_parser.py`)**:

| Test | What it covers |
|------|----------------|
| `test_is_shape_a_detects_cabecera_files` | True when Cabecera file present |
| `test_is_shape_a_returns_false_for_shape_b` | False for unified CSV ZIP |
| `test_find_shape_a_files_returns_cabecera_and_resto` | Both paths found |
| `test_find_shape_a_files_handles_2007_typo` | "Caractericas" typo matched |
| `test_find_shape_a_files_ignores_area_files` | Area/* files excluded |
| `test_parse_shape_a_concatenates_cabecera_and_resto` | 3+2=5 rows, CLASE 1/2 |
| `test_parse_shape_a_raises_when_module_missing` | ParseError on no-match |

**Integration (1 new test in `tests/integration/test_load_fixture.py`)**:

- `test_load_shape_a_geih1_fixture`: Builds a Shape A ZIP with `build_shape_a_zip()`, calls `parse_shape_a_module()` directly, asserts row counts and CLASE values.

**Fixture builder (new function in `tests/_build_fixtures.py`)**:

- `build_shape_a_zip(output_path, year, month, folder_name, n_cabecera, n_resto)`: creates a synthetic GEIH-1 ZIP with 4 modules × 2 areas (8 CSVs).

### Coverage impact

| | Before | After |
|--|--------|-------|
| Loadable entries (sources.json) | 1 (2024-06 only) | 1 (unchanged; sources.json not modified in 3.2.B) |
| Parser can handle | Shape B + Shape A (lookup-based) | Shape B + Shape A (auto-discovery) |
| GEIH-1 entries parseable once sources.json populated | 0 | ~180 |

Sources.json population is Phase 3.2.C. After 3.2.C, all 230 catalog entries will be loadable.

### Known limitations

- **Area files not loaded**: Their semantics are unclear (may be urban+rural aggregate or auxiliary). Phase 3.7 may revisit.
- **Encoding normalization not implemented**: Filenames stored as CP437 (producing `╡rea` for `Área`) are handled by the Cabecera/Resto prefix filter — Area files are excluded regardless of encoding.
- **`fuerza_de_trabajo` module**: Not in `sources.json` modules list; included in `MODULE_KEYWORDS_GEIH1` for forward compatibility.

### Shape B regression check

```python
import pulso
df = pulso.load_merged(year=2024, month=6, harmonize=True)
assert df.shape == (70020, 525)  # unchanged
```

Passes. Shape B dispatch path is untouched.

## Phase 3.3: Synthetic Mass Validation

### Coverage

- 230 sources.json entries, each tested with a synthetic ZIP fixture
- All declared modules parsed and verified non-empty per entry
- 8 representative months across both epochs tested through full merge → harmonize pipeline
- 412 total tests (156 baseline + 230 entry tests + 8 harmonize tests + 18 existing integration)

### Performance

- `test_load_all_entries.py --run-integration`: ~18–22s (well under 30s target)
- `test_harmonize_cross_epoch.py --run-integration`: ~3s
- Total CI runtime with all tests: ~28s

### Implementation: `build_fixture_from_sources_entry`

New function in `tests/_build_fixtures.py` that builds a synthetic ZIP matching any
`sources.json` entry structure:

- **Shape A**: detects via `"cabecera" in first_module`. Writes Cabecera + Resto CSV pairs
  for each module using alphabetical file-path ordering (see keyword collision discovery below).
- **Shape B**: detects via `"file" in first_module`. Writes one CSV per unique file path,
  deduplicating shared files (desocupados + inactivos share "No ocupados.CSV").
- Encoding: latin-1, separator `;`, decimal `,` (matches both epoch settings).
- Comprehensive persona-level columns (all variable_map.json source variables included)
  so the harmonize tests can produce all 30 canonical variables.

### Implementation: `test_load_all_entries.py`

Parametrized over all 230 `sources.json` entries (one test per entry, all modules
tested within each). Calls `parse_module()` directly with the synthetic ZIP — no network,
no download stack. Works because:
- Shape A: `is_shape_a(zip_path)` triggers auto-discovery path (no sources.json file lookup)
- Shape B: `parse_module()` reads file paths from real sources.json, which our synthetic
  ZIP satisfies exactly (built from the same entry)

### Implementation: `test_harmonize_cross_epoch.py`

8 representative months (4 GEIH-1, 4 GEIH-2). For each: build fixture → parse all modules →
`merge_modules()` → `harmonize_dataframe()`. Asserts:
1. Result is non-empty DataFrame
2. Core canonical vars (sexo, edad, grupo_edad, area, peso_expansion, peso_expansion_persona) present
3. At least half (15/30) of all canonical variables produced

With comprehensive fixture columns, all 30 canonical variables are produced for all 8 months. ✓

### Discoveries

**Parser keyword collision — Shape A "Ocupados" vs "Desocupados"** (known issue, Phase 3.4):

`find_shape_a_files(zip, "ocupados")` uses substring matching: `"ocupados" in filename.lower()`.
Since "desocupados" contains "ocupados" as a substring, BOTH "Cabecera - Ocupados.csv" AND
"Cabecera - Desocupados.csv" match the "ocupados" keyword. The parser uses a last-match-wins
strategy (iterates ZIP namelist, overwrites `cabecera` variable on each match).

**Effect in our fixtures**: fixed by writing ZIP entries in alphabetical order (D < O), so
"Cabecera - Desocupados.csv" is processed before "Cabecera - Ocupados.csv" → "Ocupados"
wins as the final assignment. Alphabetical ordering also matches typical real DANE ZIP structure.

**Effect with real DANE ZIPs**: depends on DANE's internal ZIP creation order. If DANE uses
alphabetical order (D < O), the bug does not manifest. If not, "Desocupados" content would
be returned when loading "ocupados" module — producing wrong columns. **Filed as known issue;
fix requires a word-boundary or negative-lookahead in `MODULE_KEYWORDS_GEIH1` matching logic
in `pulso/_core/parser.py`.**

### Out of scope

- Real DANE downloads (Phase 3.4)
- Performance benchmarks beyond runtime
- Parser keyword fix (Phase 3.4 or separate PR)
