# pulso — Architecture

> This document is the primary architectural reference for the `pulso` codebase.  
> It covers the three CSV shapes, the full processing pipeline, code organization, data layer,  
> build model, testing strategy, and known issues.  
>
> **Spanish mirror:** [`docs/architecture.es.md`](architecture.es.md)  
> **Related decisions:** [`docs/decisions/`](decisions/)

---

## 1. Overview

`pulso` gives Python users single-line access to Colombia's **Gran Encuesta Integrada de Hogares (GEIH)** — the monthly household labour-force survey published by DANE (Departamento Administrativo Nacional de Estadística).

```
User request: load(year=2024, month=6, module="ocupados")
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │  pulso public API  (pulso/_core/loader.py)                      │
  │                                                                  │
  │  download → parse → (merge) → harmonize → pd.DataFrame          │
  └─────────────────────────────────────────────────────────────────┘
       │         │          │          │
       ▼         ▼          ▼          ▼
  DANE ZIP   shape-aware  epoch     variable_map
  (cached)   parser       keys      .json
```

**User-facing contract:**
- Input: year, month, module name (string), area (cabecera/resto/total)
- Output: `pd.DataFrame` with either raw DANE column codes or harmonized canonical variable names
- Side effects: ZIP cached locally; subsequent calls hit cache

**What pulso does NOT do:**
- Statistical inference (no sampling-design-aware standard errors)
- Imputation or missing-data filling
- Official DANE data products — this is a convenience wrapper, not a DANE tool

---

## 2. The Three CSV Shapes

The most important structural fact about `pulso` is that it handles three distinct CSV layouts produced by DANE across different series and years. Each shape requires different parsing logic.

```
Shape A  (GEIH-1, 2006–2021)    Shape B  (GEIH-2, 2022–present)   Shape C  (Empalme, 2010–2019)
─────────────────────────────   ──────────────────────────────────   ─────────────────────────────
annual_zip/                     annual_zip/                           empalme_YYYY.zip/
  Cabecera - Ocupados.csv   →     CSV/                                  1. Enero.zip/
  Resto    - Ocupados.csv           Ocupados.CSV                            1. Enero/CSV/
  Cabecera - Caract.csv              Características...CSV                      Ocupados.CSV
  Resto    - Caract.csv              No ocupados.CSV                             Caract. gen..CSV
  ...                                ...                                       ...
(split by urban/rural)          (single national file,             (nested: annual→monthly→module;
                                 CLASE col for area filter)         Shape C-style inside sub-ZIPs)
```

### Shape A — GEIH-1 (2006-01 → 2021-12)

| Attribute | Value |
|-----------|-------|
| **Detection** | `is_shape_a(zip_path)`: any filename contains `"Cabecera"` |
| **Structure** | Two files per module: `Cabecera - {module}.csv` (urban) and `Resto - {module}.csv` (rural) |
| **Encoding** | `latin-1` |
| **Separator** | `;` (no auto-detect needed for Shape A) |
| **Decimal** | `,` |
| **Area split** | Physical file split (no `CLASE` column needed) |
| **Column case** | Mixed — varies by year and module (e.g. `Hogar`, `Directorio`, `Fex_c_2011`) |
| **Column normalization** | ⚠️ **INCOMPLETE** — only merge keys are uppercased; non-key columns may be mixed case. Known bug: issue [#42](https://github.com/Stebandido77/pulso/issues/42). Fix tracked in Phase 4 Line A. |
| **Weight column** | `fex_c_2011` (lowercase, with year suffix) → will become `FEX_C` after Line A fix |
| **Parser entry point** | `parse_shape_a_module()` in [`pulso/_core/parser.py`](../pulso/_core/parser.py) |

Module file matching uses word-boundary regex against the keyword map `MODULE_KEYWORDS_GEIH1`, which handles DANE filename typos (e.g. `"Caractericas"` for `"Características"` in 2007).

### Shape B — GEIH-2 (2022-01 → present)

| Attribute | Value |
|-----------|-------|
| **Detection** | `is_shape_a()` returns `False` (no `"Cabecera"` filenames) |
| **Structure** | Single nationwide CSV per module inside a `CSV/` folder |
| **Encoding** | `latin-1` |
| **Separator** | `;` declared in epoch; auto-detect fallback (some months use `,`) |
| **Decimal** | `,` |
| **Area split** | Row-level via `CLASE` column (1 = cabecera, 2/3 = resto) |
| **Column case** | Native uppercase from DANE |
| **Column normalization** | ✅ BOM stripping + merge-key uppercase via `_read_csv_with_fallback()` |
| **Weight column** | `FEX_C18` (uppercase, no year suffix) |
| **Parser entry point** | `_parse_csv()` in [`pulso/_core/parser.py`](../pulso/_core/parser.py) |

The separator auto-detect fallback (`sep=None, engine="python"`) activates when `_read_csv_with_fallback()` reads a 1-column DataFrame, which signals a separator mismatch. This was necessary for the 2022-01 entry (see PR [#36](https://github.com/Stebandido77/pulso/pull/36)).

### Shape C — Empalme (2010-2019)

| Attribute | Value |
|-----------|-------|
| **Detection** | Called explicitly via `load_empalme()` or `apply_smoothing=True`; not auto-detected |
| **Structure** | Annual ZIP → 12 monthly sub-ZIPs → `<NN>. <Mes>/CSV/<ModuleName>.CSV` |
| **Encoding** | `latin-1` |
| **Separator** | `;` with auto-detect fallback (inherited from `_read_csv_with_fallback`) |
| **Decimal** | `,` |
| **Area split** | Unified file; `CLASE` column used if present |
| **Column case** | Mixed — DANE delivers `Hogar`, `Fex_c_2011`, etc. |
| **Column normalization** | ✅ Full uppercase + `FEX_C_XXXX → FEX_C` via `_normalize_empalme_columns()` |
| **Weight column** | `FEX_C` (after normalization) |
| **Parser entry point** | `_parse_empalme_module()` in [`pulso/_core/empalme.py`](../pulso/_core/empalme.py) |

Monthly sub-ZIP naming uses Spanish month names (`Enero`, `Febrero`, …, `Diciembre`). The `_detect_month_from_name()` function extracts the month number from the sub-ZIP filename.

**Anomalies documented in registry:**
- **2013:** outer ZIP filename has DANE typo `GEIH_Emplame_2013.zip` (missing `p`); preserved as-is.
- **2020:** ZIP not published by DANE; `download_empalme_zip(2020)` raises `DataNotAvailableError`.
- **2020 IDNO:** truncated to `DANE-DIMPE-GEIH-EMPAL-2020` (missing `ME` suffix).

---

## 3. Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        load() / load_merged()                        │
│                     pulso/_core/loader.py                            │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│  1. REGISTRY LOOKUP                │   pulso/_config/registry.py
│  sources.json → (year,month) record│   Raises DataNotAvailableError if missing
│  epoch_for_month() → Epoch object  │   pulso/_config/epochs.py
└────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│  2. DOWNLOAD                       │   pulso/_core/downloader.py
│  download_zip(year, month) → Path  │   Cache: <cache_root>/raw/{year}/{month}/{sha[:16]}.zip
│  Checksum verification (SHA-256)   │   DownloadError on mismatch
└────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│  3. PARSE (shape-aware)            │   pulso/_core/parser.py  OR  pulso/_core/empalme.py
│  parse_module(zip_path, ...) →     │
│    Shape A: parse_shape_a_module() │   Cabecera + Resto concatenated; CLASE synthetic
│    Shape B: _parse_csv()           │   Single CSV; BOM strip + sep auto-detect
│    Shape C: _parse_empalme_module()│   Sub-ZIP extracted to temp; full normalization
│  → raw pd.DataFrame               │
└────────────────────────────────────┘
    │
    ▼  (only in load_merged / apply_smoothing)
┌────────────────────────────────────┐
│  4. MERGE (persona + hogar)        │   pulso/_core/merger.py
│  merge_modules(module_dfs, epoch)  │   Auto-detects persona/hogar level per module
│  → merged pd.DataFrame            │   MergeError if keys missing (see issue #42)
└────────────────────────────────────┘
    │
    ▼  (when harmonize=True)
┌────────────────────────────────────┐
│  5. HARMONIZE                      │   pulso/_core/harmonizer.py
│  harmonize_dataframe(df, epoch)    │   Reads variable_map.json
│  → canonical column names appended │   keep_raw=True: raw columns preserved alongside
│    (sexo, edad, condicion_activ…)  │   HarmonizationError skipped with logger.warning
└────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│  6. RETURN pd.DataFrame            │
│  Raw DANE columns + canonical cols │   User calls expand() separately if needed
└────────────────────────────────────┘
```

### Step details

**Step 1 — Registry lookup**  
`_load_sources()` reads `pulso/data/sources.json` (230 entries; cached in memory after first load). `epoch_for_month(year, month)` iterates the two epoch records and returns the matching `Epoch` frozen dataclass. Raises `ConfigError` if no epoch covers the date (i.e. before 2006-01).

**Step 2 — Download**  
`download_zip()` checks the local cache first. The cache slot is `<cache_root>/raw/{year}/{month:02d}/{sha256[:16]}.zip`. If the file exists and the checksum matches, it is returned immediately. If the checksum field in `sources.json` is `null` (most GEIH-1 entries), the file is returned without verification once downloaded. A `.tmp` file pattern prevents partial downloads from polluting the cache.

**Step 3 — Parse**  
`parse_module()` dispatches first via `is_shape_a(zip_path)`. If `True`, Shape A logic runs regardless of the `epoch.area_filter` field. If `False`, it reads the `sources.json` record for file paths and dispatches to Shape B (`_parse_csv`). Shape C is invoked separately via `empalme.py` and never flows through `parse_module()`.

**Step 4 — Merge**  
`merge_modules()` auto-detects each module's level (persona vs hogar) by checking which merge keys are present. Persona-level modules are merged on `(DIRECTORIO, SECUENCIA_P, ORDEN)`; hogar-level modules are merged on `(DIRECTORIO, SECUENCIA_P, HOGAR)`, then left-joined into the persona result. The `how="outer"` default ensures persons appear even if absent from a module (e.g. employed persons are not in `desocupados`).

**Step 5 — Harmonize**  
`harmonize_dataframe()` iterates `variable_map.json` variables, resolves source columns for the current epoch, applies the declared transform (identity/recode/compute/cast/coalesce), and appends the result as a new column. Variables with missing source columns emit `logger.warning()` and are skipped — they do **not** raise an exception. With `keep_raw=True` (default), the original DANE columns are preserved alongside the canonical ones.

---

## 4. Code Organization — `pulso/_core/`

```
pulso/_core/
├── downloader.py       # Download, cache, checksum
├── parser.py           # Shape A + Shape B parsing
├── empalme.py          # Shape C (Empalme) exclusively
├── harmonizer.py       # variable_map transforms
├── merger.py           # multi-module merge
├── loader.py           # public API orchestrator
└── expander.py         # expand() helper
```

### `downloader.py`

Responsible for: fetching ZIPs from DANE, caching to disk, verifying SHA-256.

Key functions:
- `download_zip(year, month, cache, show_progress, allow_unvalidated)` — main entry point
- `verify_checksum(path, expected_sha256)` — streaming SHA-256 comparison

Notable: the downloader deliberately does **not** parse — it returns a `Path` to the local ZIP and nothing more. This separation allows the parser to be tested with pre-cached ZIPs without network access.

### `parser.py`

Responsible for: Shape A and Shape B parsing. Shape C is **not here** (see `empalme.py`).

Key functions:
- `is_shape_a(zip_path)` — detects Shape A by checking for `"Cabecera"` in namelist
- `find_shape_a_files(zip_path, module)` — keyword+regex match for Cabecera/Resto files
- `parse_shape_a_module(zip_path, module, epoch)` — reads both halves, concatenates, adds synthetic `CLASE`
- `_read_csv_with_fallback(raw_bytes, epoch)` — separator auto-detect + BOM strip + merge-key uppercase
- `_resolve_zip_path(zf, path)` — tolerates mojibake paths and missing subfolder prefixes
- `_parse_csv(zip_path, inner_path, epoch, columns)` — Shape B single-file reader
- `parse_module(zip_path, year, month, module, area, epoch, columns)` — top-level dispatcher

The `MODULE_KEYWORDS_GEIH1` dictionary maps canonical module names to lists of Spanish keywords used to identify files inside Shape A ZIPs. Multiple keywords per module handle DANE's filename typos.

### `empalme.py`

Responsible for: Shape C (Empalme) exclusively. Kept separate because:
1. The annual→monthly→sub-ZIP nesting is structurally different from Shapes A/B.
2. The Empalme series has a distinct registry (`empalme_sources.json`) and cache layout.
3. Column normalization for Shape C is currently more complete than for Shape A (post-Phase 4 Line A fix, this divergence will be resolved by a shared helper).

Key functions:
- `_load_empalme_registry()` / `_get_empalme_entry(year)` — registry access with validation
- `download_empalme_zip(year, show_progress)` — cache at `<root>/empalme/{year}.zip`
- `_find_empalme_module_csv(zf, module)` — keyword match inside a sub-ZIP
- `_parse_empalme_module(inner_zip_path, module)` — reads one module CSV + applies `_normalize_empalme_columns()`
- `_normalize_empalme_columns(df)` — uppercase all columns + `FEX_C_XXXX → FEX_C`
- `_load_empalme_month_merged(year, month, area, harmonize, variables)` — single-month load for `apply_smoothing`
- `load_empalme(year, module, area, harmonize)` — public API, all 12 months stacked

### `harmonizer.py`

Responsible for: applying `variable_map.json` transforms to a raw DataFrame.

Key functions:
- `harmonize_dataframe(df, epoch, variables, keep_raw)` — main entry point; iterates variables and appends canonical columns
- `harmonize_variable(df, canonical_name, entry, epoch)` — applies a single variable's transform
- `_apply_recode()`, `_apply_compute()`, `_apply_cast()`, `_apply_coalesce()` — transform primitives

Design invariant: `harmonize_dataframe()` never raises on missing source columns — it logs a warning and skips. This allows partial harmonization when not all modules are loaded.

### `merger.py`

Responsible for: merging multiple module DataFrames using epoch-appropriate keys.

Key functions:
- `merge_modules(module_dfs, epoch, level, how)` — top-level merge
- `_detect_module_level(df, epoch)` — persona vs hogar detection by key presence
- `_merge_within_level(dfs_dict, keys, how)` — repeated left-join within a level

The merger drops shared non-key columns from later DataFrames to avoid `_x`/`_y` suffixes. Shared identifier columns (`CLASE`, `DPTO`, weight variables, `MES`, `HOGAR`) appear exactly once.

### `loader.py`

Responsible for: the public API. Orchestrates the pipeline steps above.

Key functions:
- `load(year, month, module, area, harmonize, columns, cache, show_progress, allow_unvalidated)` — single module
- `load_merged(year, month, modules, area, harmonize, variables, cache, show_progress, allow_unvalidated, apply_smoothing)` — multi-module merge with optional Empalme swap
- `_required_modules_for_variables(variable_map, sources, epoch_key, requested_variables)` — auto-expands the module list when `harmonize=True` and the user specified `variables=`

The `apply_smoothing` parameter triggers `_load_empalme_month_merged()` for years 2010–2019. Year 2020 emits `UserWarning` and falls back to raw GEIH.

---

## 5. Data Layer — `pulso/data/`

This directory is **Curator territory**. The Builder must not modify files here; the Curator must not modify `pulso/_core/`. CI enforces this via branch path conventions.

```
pulso/data/
├── sources.json              # 230 monthly GEIH entries (2006-01 → 2026-02)
├── empalme_sources.json      # 11 annual Empalme entries (2010–2020)
├── epochs.json               # 2 epoch definitions
├── variable_map.json         # 30 canonical variable mappings
└── schemas/
    ├── sources.schema.json
    ├── empalme_sources.schema.json
    ├── epochs.schema.json
    └── variable_map.schema.json
```

### `sources.json`

230 entries keyed by `"YYYY-MM"`. Each entry contains:
- `epoch`: `"geih_2006_2020"` or `"geih_2021_present"`
- `download_url`: direct DANE ZIP URL
- `checksum_sha256`: SHA-256 hex (5 validated entries filled; rest `null`)
- `modules`: file paths inside the ZIP per canonical module
- `validated`: `true/false`

The schema in `sources.schema.json` enforces two polymorphic `ModuleFiles` shapes:
- `ModuleFilesSplit`: `{cabecera, resto}` (Shape A)
- `ModuleFilesUnified`: `{file, row_filter?}` (Shape B)

### `empalme_sources.json`

11 entries keyed by 4-digit year string (`"2010"` … `"2020"`). Each downloadable entry contains:
- `catalog_id`, `idno`: DANE NADA catalog identifiers
- `download_url`, `zip_filename`, `size_bytes`, `checksum_sha256`
- `downloadable`: `false` for 2020 (ZIP not published)

All 10 downloadable entries (2010–2019) have verified SHA-256 checksums as of 2026-05-02.

### `epochs.json`

Two epoch records:

| Key | Date range | Label |
|-----|-----------|-------|
| `geih_2006_2020` | 2006-01 → 2021-12 | GEIH marco muestral 2005 |
| `geih_2021_present` | **2022-01** → present | GEIH rediseñada (post-OIT, marco 2018) |

> ⚠️ The epoch boundary is **2022-01**, not 2021. This is a common source of confusion in documentation.

### `variable_map.json`

30 canonical variables mapped across both epochs. Each entry:
- `type`: `numeric`, `categorical`, `string`, or `boolean`
- `level`: `persona` or `hogar`
- `module`: source module name
- `mappings`: per-epoch `{source_variable, transform, source_doc, notes?}`

Transform types: `identity`, `recode`, `compute` (pandas eval expression), `cast`, `coalesce`.

---

## 6. Multi-Agent Build Model

`pulso` uses a three-role build model where each role has distinct permissions:

```
Architect      →   Design, ADRs, architecture docs, roadmap RFCs
Builder        →   pulso/_core/, pulso/__init__.py, tests/
Curator        →   pulso/data/, tests/
```

CI enforces branch path conventions:

| Branch prefix | May touch |
|--------------|-----------|
| `feat/code-*` | `pulso/_core/`, `pulso/__init__.py`, `tests/` |
| `feat/data-*` | `pulso/data/`, `tests/` |
| `docs/*`      | `docs/`, `README.md` |
| `fix/code-*`  | Same as `feat/code-*` |

Violations cause CI to fail. This prevents accidental cross-layer changes and maintains a clean audit trail of who changed what.

**Why this matters:** `sources.json` and `variable_map.json` contain research-quality metadata that must be validated by the Curator before the Builder can depend on it. Separating branches ensures these files are reviewed independently.

---

## 7. Active Architectural Decisions

See [`docs/decisions/`](decisions/) for full ADR records.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](decisions/0001-build-plan.md) | Build plan and phase structure | Active |
| [0002](decisions/0002-scope-2006-present.md) | GEIH scope (2006-present only, no ECH) | Active |
| [0003](decisions/0003-schema-1.1-area-filtering.md) | Schema v1.1 polymorphic ModuleFiles | Active |
| [0004](decisions/0004-harmonizer-design.md) | Harmonizer design (keep_raw=True default) | Active |
| [0005](decisions/0005-phase4-roadmap.md) | Phase 4 roadmap (C→A→v1.0→B→v1.1) | Active |

Key active invariants:
- **Epoch boundary = 2022-01.** Empirically verified via `epoch_for_month()`.
- **`apply_smoothing` degrades gracefully for year=2020.** Emits `UserWarning`, falls back to raw GEIH.
- **`harmonize_dataframe` never raises on missing columns.** Skips with `logger.warning`.
- **Cache is append-only.** Downloaded ZIPs are never overwritten unless checksum fails; partial downloads use `.tmp` suffix.

---

## 8. Testing Strategy

```
                    ┌─────────────────────────────────────────┐
                    │            CI Test Suite                 │
                    │                                          │
                    │  Integration (275 tests)                 │
                    │    @pytest.mark.integration              │
                    │    --run-integration flag required       │
                    │    Real DANE ZIPs from network           │
                    │    5 strategic months validated          │
                    │                                          │
                    │  Unit (179 tests)                        │
                    │    Fast, no network                      │
                    │    Synthetic fixture ZIPs                │
                    │    Always run in CI                      │
                    └─────────────────────────────────────────┘
```

### Unit tests (179 tests, always run)

Location: `tests/unit/`

- Fixture ZIPs in `tests/fixtures/zips/` built by `tests/_build_fixtures.py`
- `geih2_sample.zip` — Shape A fixture (Cabecera + Resto)
- `geih2_unified_sample.zip` — Shape B fixture (unified file)
- Registry injection via `monkeypatch.setattr(reg, "_SOURCES", ...)` to avoid loading `sources.json`
- Parser tests verify BOM stripping, separator auto-detect, column normalization, keyword matching

### Integration tests (275 tests, require `--run-integration`)

Location: `tests/integration/`

**5 strategic months** validated with real DANE ZIPs:

| Month | Epoch | Shape | Why chosen |
|-------|-------|-------|-----------|
| 2007-12 | geih_2006_2020 | A | Earliest stable GEIH-1 entry; BOM in CSV headers |
| 2015-06 | geih_2006_2020 | A | Mixed-case column bug (issue #42) confirmed here |
| 2021-12 | geih_2006_2020 | A | Last month before epoch boundary |
| 2022-01 | geih_2021_present | B | First month of new epoch; comma separator anomaly |
| 2024-06 | geih_2021_present | B | Most recent manually validated; Phase 2 regression anchor |

**Phase 2 regression test:** `load_merged(year=2024, month=6, harmonize=True).shape == (70020, 525)` — this exact value is locked and must not change.

### Empalme integration tests

`tests/integration/test_smoothing.py`:
- `test_smoothing_2015_06_real` — `apply_smoothing=True` for 2015-06 produces normalized columns (FEX_C, HOGAR uppercase) and plausible row count
- `test_load_empalme_2015_real` — `load_empalme(2015)` returns 12 months stacked with non-null FEX_C

---

## 9. Known Issues

### Issue #42 — Shape A parser: mixed-case columns (HIGH severity)

**Status:** Open. Tracked for Phase 4 Line A.

**Symptom:** `load_merged(year, month)` for some GEIH-1 months raises `MergeError: Module is missing merge keys`. Confirmed for 2015-06 `vivienda_hogares` module.

**Root cause:** DANE delivers columns like `Hogar`, `Area`, `Fex_c_2011` (mixed case) in some Shape A CSVs. The merger's case-sensitive lookup for `HOGAR` fails.

**Current workaround:** None for the raw path. The Empalme path (`apply_smoothing=True`) normalizes columns correctly via `_normalize_empalme_columns()`.

**Fix planned:** Phase 4 Line A — extract a shared `_normalize_dane_columns()` helper in `parser.py`, apply it in `parse_shape_a_module()`. Update `variable_map.json` to use `FEX_C` instead of `fex_c_2011` (coordinated Builder + Curator PRs). See [ADR 0005](decisions/0005-phase4-roadmap.md).

---

## 10. Glossary

| Term | Definition |
|------|-----------|
| **GEIH** | Gran Encuesta Integrada de Hogares. Colombia's official monthly labour-force survey, published by DANE since 2007 (redesigned sampling frame in 2022). |
| **ECH** | Encuesta Continua de Hogares. DANE's predecessor survey (2000–2005). Not supported by `pulso` due to incompatible methodology. |
| **GEIH-1** | Informal name for GEIH under the 2005 census sampling frame (2006-01 → 2021-12 in `pulso`'s epoch model). |
| **GEIH-2** | Informal name for GEIH under the 2018 census sampling frame, redesigned post-ILO (2022-01 → present). |
| **Empalme** | DANE's annually-published harmonized GEIH series (2010–2019) that re-estimates monthly microdata under the unified 2005-census methodology. Enables consistent multi-year analysis across the 2022 redesign. |
| **Factor de expansión** | Expansion factor (survey weight). Each respondent represents a population count. `fex_c_2011` (GEIH-1) / `FEX_C18` (GEIH-2) / `FEX_C` (Empalme, normalized). |
| **Época (Epoch)** | A period during which DANE's methodology is internally consistent. `pulso` defines two epochs; their boundary is 2022-01. |
| **Módulo** | A thematic CSV file within a GEIH monthly ZIP. Examples: `ocupados`, `caracteristicas_generales`. Each module is one analysis level (persona or hogar). |
| **Persona level** | Microdata at the individual respondent level. Merge keys: `DIRECTORIO`, `SECUENCIA_P`, `ORDEN`. |
| **Hogar level** | Microdata at the household level. Merge keys: `DIRECTORIO`, `SECUENCIA_P`, `HOGAR`. |
| **Shape A / B / C** | `pulso`'s internal names for the three CSV structural layouts produced by DANE (see Section 2). |
| **Canonical variable** | A harmonized variable name in `variable_map.json` (e.g. `sexo`, `peso_expansion`) that is consistent across epochs, as opposed to the raw DANE code (`P6020`, `FEX_C18`). |
| **Builder** | Role in the multi-agent build model responsible for `pulso/_core/`. |
| **Curator** | Role responsible for `pulso/data/` — registry files, schemas, variable map. |
| **Architect** | Role responsible for ADRs, RFCs, and cross-cutting design decisions. |
