# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Sin publicar] — pulso-co 1.3.0 / R pulso 0.3.0

### Agregado
- `pulso.trm()` / `pulso_trm()` (#90): TRM (pesos por dólar) certificada por la Superintendencia Financiera (dataset `32sa-8pi3` de datos.gov.co), un registro por día, con la interfaz de `tpm()`: snapshot incluido (`trm_superfinanciera_20261128.csv.gz`, 2006–2026-11-30, 40 KB) y llamada en vivo con fallback. **IBR pendiente**: la API SDMX del Banco de la República (la única fuente del IBR) estaba en mantenimiento y no se pudo verificar el identificador del flujo.
- Caché del módulo ya parseado en parquet (#86): `pulso.load()` guarda el módulo completo en `<caché>/parsed/<año>/<mes>/<módulo>_<clave>.parquet`. La clave combina la URL de descarga, el módulo, `PARSER_VERSION` y la entrada de `sources.json` del periodo, sin los campos de validación. Las cargas siguientes no vuelven a abrir el zip y leen solo las columnas pedidas. `pulso.cache_clear("parsed")` la borra y `cache=False` la evita. En R, con `arrow` instalado (Suggests), igual: `pulso_clear_cache()` es nueva. Sin `arrow`, R no usa caché parquet.
- `pulso_load(columns =)` en R (antes solo existía en Python): lee solo esas columnas con `fread(select =)`.
- `python/scripts/benchmark_load.py`: tiempo y memoria pico de `pulso.load` en primera y segunda carga.
- `pulso.indicadores()` / `pulso_indicadores()` (#88): TD, TO y TGP con los niveles de PET, FT, ocupados y desocupados, por dominio (nacional, cabeceras, centros poblados y rural disperso, 13 y 23 ciudades con sus áreas metropolitanas, cada ciudad y cada departamento), mensuales o de trimestre móvil. Usan las definiciones de `variable_map.json`. Coinciden con el anexo del DANE en los 9 meses nacionales de 2026 y en jul–sep 2026 para el total nacional, 13 y 23 ciudades, Bogotá, Medellín y Cali (diferencia de 0,000000 pp). Solo estimación puntual (`se` = NA): los microdatos públicos no traen estrato ni UPM (`docs/roadmap/w5-errores-estandar.md`). Subocupación e informalidad quedan pendientes.
- `pulso.load_range(start, end, module, ...)` / `pulso_load_range()` (#87): carga meses consecutivos ("YYYY-MM") apilados con `periodo`, `year` y `month`, armonizando cada mes con el mapeo de su época. Avisa si el rango mezcla los marcos 2005 y 2018 (2022 en adelante, y 2020). Con `average_weights=True` agrega `peso_expansion_promedio` = factor / número de meses: los niveles del trimestre móvil del DANE son el promedio de los niveles mensuales. Verificado contra el anexo del DANE: jul–sep 2026 da TD 8,490844 y 24.160,496 miles de ocupados, iguales a la hoja "Total nacional Trim" de `anex-GEIH-sep2026.xlsx`.
- Variables canónicas `pet` (población en edad de trabajar) y `fuerza_trabajo` (FT) en `variable_map.json`, para las dos épocas, con la definición del DANE citada (#79):
  - PET: 12+ en cabecera y 10+ en centro poblado y rural disperso en el marco 2005; 15+ en el marco 2018. 2020 usa 15+ porque sus microdatos están en el marco 2018.
  - FT: ocupados + desocupados, a partir de las banderas de cada módulo.
- Funciones de armonización `labor_status_from_flags`, `labor_force_from_flags` y `pet_by_age_zone`. Los transforms `custom` aceptan `params` en el esquema de `variable_map`.

### Cambiado
- `columns=` lee solo esas columnas desde el CSV (`usecols`) y conserva siempre las llaves de merge (`DIRECTORIO`, `SECUENCIA_P`, `ORDEN` y `HOGAR` si existe), para que el resultado se pueda seguir uniendo. Los nombres se comparan sin distinguir mayúsculas y `FEX_C` también encuentra `fex_c_2011`. Si una columna pedida no existe, se avisa con un `UserWarning` en vez de lanzar `KeyError` (Shape B).
- Shape B: el DataFrame se consolida con `copy()` al leerlo, en vez de quedar en ~200 bloques (#52).
- La clave de caché de los zips sin checksum incluye un hash corto de la URL (`<año>-<mes>_<sha1[:10]>.zip`), como en R. Si el catálogo apunta un periodo a otro archivo del DANE, ya no se reutiliza el zip viejo. Los zips cacheados con el nombre anterior (`unvalidated_<año>-<mes>.zip`) se vuelven a descargar una vez.
- El separador se decide por el encabezado antes de deducir la marca decimal: un archivo tabulado en una época que declara `;` (los `Mes_txt.zip` de 2008 y 2011, #74) ya no queda con los decimales como texto.
- `condicion_actividad` en el marco 2005 usa `OCI`/`DSI`/`INI` en vez de solo `OCI`, que dejaba sin código a desocupados e inactivos (#79). Requiere cargar juntos los módulos de fuerza de trabajo con `load_merged()`.
- `merge_labor_status` (marco 2018) usa `FFT` cuando la tabla lo trae. Los menores de 15 que solo están en Características generales quedan NA en vez de "inactivo" (#79).
- `validate_periods.py` calcula PET, FT, OC y DS con esas variables a través de `load_merged(..., harmonize=True)`, en vez de la pertenencia a los módulos.

### Corregido
- `hatch_build.py` y `scripts/sync_data.py` ya no fallan en Windows al borrar `python/pulso/data`: copian sin el atributo de solo lectura, reintentan con permiso de escritura los archivos de solo lectura y reutilizan el directorio si quedó vacío pero bloqueado. Si aun así no pueden borrarlo, el error nombra el archivo y cómo resolverlo.
- Python carga las estructuras de zip que antes solo resolvía R, o ninguno de los dos (#75):
  - 2013-04..06: nombres con el mes como sufijo (`Cabecera - Ocupados04.csv`).
  - 2020 (Shape C): un archivo nacional por módulo con su propia columna `CLASE`, aunque el catálogo declare Cabecera/Resto. El filtro de área usa `CLASE`.
  - Errores de tipeo del DANE en 2020, en R y Python: `Descupados`, `Desoucpados`, `Ianctivos`, `Inativos` y `Fuerzo de trabajo`.
  - Zips anidados con nombres variantes, en R y Python: `CSV 4.zip` (2022-10), `DTA 9.zip` y carpeta `CVS/` (2023-04), `DAT.zip` (2023-08), `CSV 13.zip` (2023-09).
  - 2024-03: `No ocupado.CSV` en singular, con el índice de palabras clave de la GEIH rediseñada que ya tenía R.
- En 2020-03 y 2020-04 el DANE no publicó los módulos `desocupados` ni `inactivos`. Pedirlos da un `ParseError` que lo dice.
- Referencia de validación de 2020: los microdatos de 2020 (catálogo 780 del DANE) vienen con factores retroproyectados al CNPV 2018, así que `fetch_dane_reference.py` toma 2020-01..2020-12 del anexo vigente y no del anexo del marco 2005. Se reemplazaron solo esas 12 filas de `data/reference/dane_labor_indicators.csv`. `docs/caveats.md` advierte que 2020 no es comparable con 2019 ni con 2021.

### Mantenimiento
- Mantenimiento de CI: las actions que corrían en Node 20 pasan a versiones en Node 24 (`checkout@v7`, `setup-python@v7`, `upload-artifact@v7`, `download-artifact@v8`, `cache@v6`, `codecov-action@v7`, `create-pull-request@v8`). Las de `r-lib/actions@v2` ya estaban en Node 24.
- `r/inst/doc/` sale del repositorio (lo genera `R CMD build`) y queda en `.gitignore`.

### Datos
- 235 de 237 periodos con `validated: true` (antes 193), validados con `validate_periods.py` contra el DANE: diferencia máxima de 0,004595 pp (2011-07) y ninguna regresión. Faltan 2020-03 y 2020-04, para los que el DANE no publicó desocupados ni inactivos.
- 2008-01..12 y 2011-01..12 apuntan a los `Mes_txt.zip` del DANE (tabulados y con encabezado). Los CSV anteriores traían `fex_c_2011` sin punto decimal en todas las filas (#74).

## [1.2.1] — sin publicar  (Python pulso-co) / R pulso 0.2.1

### Agregado
- `python/scripts/fetch_dane_reference.py`: descarga los anexos oficiales de mercado laboral de la GEIH y extrae la serie mensual del Total Nacional (TD, TO, TGP) a `data/reference/dane_labor_indicators.csv`. Usa un anexo por época porque el anexo vigente retroproyecta 2001–2020 al marco 2018 (PET 15+): `anexo_empleo_dic_21.xlsx` (marco 2005) para 2006-01..2021-12 y el `anex-GEIH-<mes><año>.xlsx` más reciente para 2022-01 en adelante.
- `python/scripts/validate_periods.py`: carga los módulos de fuerza de trabajo de cada periodo con `pulso`, calcula TD, TO y TGP ponderados con el factor de expansión de `variable_map.json` y los compara con el DANE (≤ 0,1 pp `pass`, ≤ 0,5 pp `review`, más `fail`; `pending` sin cifra oficial; `error` si no carga). Flags `--periods`, `--workers` y `--resume`; escribe `data/reference/validation_results.csv`.
- `python/scripts/apply_validation.py`: marca como `validated: true` (`validated_by: "auto:validate_periods.py"`) los periodos en `pass` en `data/sources.json` y `r/inst/extdata/sources.json`. Nunca modifica un periodo ya validado: si deja de pasar, lo reporta como regresión y sale con código 1. Reescribe solo las cuatro líneas tocadas de cada periodo y verifica por re-lectura que nada más cambió.
- `.github/workflows/dane_smoke.yml` (+ `python/scripts/dane_smoke.py`, `scripts/dane_smoke.R`): smoke test semanal contra el DANE real en R y Python, con issue automático `dane-format-change`, y resumen de meses nuevos vía `agent_scraper.py --dry-run`.
- Extra opcional `validation` (`openpyxl`) para leer los anexos del DANE.

### Cambiado
- `sources.schema.json`: `validated_by` admite `"auto:validate_periods.py"`.

### Corregido
- `merge_labor_status`: desde 2026-08 el DANE codifica `DSI` como 1/0 en vez de 1/vacío, y las ~21.000 filas con `DSI == 0` quedaban sin `condicion_actividad`. Ahora `DSI` 0 o vacío (sin `OCI`) cuenta como inactivo (#76).

### Datos
- 191 de 237 periodos con `validated: true` (antes 5), validados con `validate_periods.py` contra el anexo del DANE de su época (diferencia máxima 0,000049 pp). Los 46 que no cargan en Python siguen con `validated: false`: 2008, 2011, 2013-04..06, 2020, 2022-10, 2023-04/08/09, 2024-03 y 2026-08/09 (issues #74, #75 y #76). Resultados y método en `data/reference/`.

## [1.2.0] — 2026-11-26  (Python pulso-co) / R pulso 0.2.0

### Added
- Catalog now covers DANE GEIH releases through **2026-09** (2026-03 to 2026-09 added from DANE catalog 900; sizes of 2026-01/02 corrected).
- `pulso.update_catalog()` (Python) / `pulso_update_catalog()` (R): fetch the latest catalog from the repository into the user cache, so new DANE months load without upgrading the package. Set `PULSO_IGNORE_CACHED_CATALOG=1` (Python) or `options(pulso.use_cached_catalog = FALSE)` (R) to stick to the bundled catalog.
- `python/scripts/agent_scraper.py`: real incremental updater (was a stub). Adds new months as `validated: false`, updates republished URLs of unvalidated months, never touches validated months, and writes both `data/sources.json` and `r/inst/extdata/sources.json`.

### Fixed
- Monthly scrape workflow reported success while doing nothing (stub + `continue-on-error`), which is why the catalog stopped at 2026-02. Failures now turn the run red.
- Decimal mark is detected per file in both packages: 2018-frame CSVs use `;` with point decimals, so `FEX_C18` was read as text (#77).
- Name resolution prefers the requested extension, so a `.dta` with the same folded name is never picked over the `.csv` (#78).
- ZIP member resolution tolerates DANE filename drift: non-breaking spaces (2025-12+), lowercase `.csv` (2026-08+) and the renamed characteristics file (2026-04). Affects `vivienda_hogares` and `otras_formas_trabajo` from 2025-12 in both packages.
- R only: per-entry CP437/UTF-8 filename decoding, nested `CSV.zip` periods (2024-03/04), Latin-1 → UTF-8 text, comma decimals, atomic downloads with cache validation. Unvalidated periods now load with a warning by default (parity with Python); `allow_unvalidated` is deprecated in favour of `strict`.

## [1.1.1] — 2026-06-09  (Python pulso-co)

### Fixed
- Packaging: `python-publish.yml` now builds wheel-only (`python -m build --wheel`) instead of sdist+wheel. The previous flow built the wheel from an extracted sdist, which did not include the canonical `data/` directory (it lives outside `python/` in the monorepo) and caused the build to fail in CI. Since `pulso-co` is pure Python, the wheel is sufficient for installation.

### Notes
- Version 1.1.0 was tagged but never published to PyPI (the publish workflow failed on the build step). 1.1.1 is the first public release of the TPM feature.

## [1.1.0] — 2026-06-07  (Python pulso-co)

### Added
- `pulso.tpm()` — Banco de la República monetary policy rate (TPM), with bundled fixture fallback when the SDMX API is unavailable. Brings parity with the R package's `pulso_tpm()`.

### Notes
- This is a Python-only release. The R package (`pulso`) is at v0.1.0, awaiting CRAN review.
- Wheel includes the bundled fixture `tpm_jdbr_manual_20260422.xlsx` (5,958 rows, 2010–2026) under `pulso/ext/`.

## [1.0.0] — 2026-05-03

### Added

- `metadata=True` opt-in for `pulso.load()` and `pulso.load_merged()`
  attaches composed Curator + DANE-codebook metadata to
  `df.attrs["column_metadata"]`, plus the source `year`, `month`,
  `module`/`modules`, and `epoch` for traceability.
- New helpers `pulso.describe_column(df, column)` and
  `pulso.list_columns_metadata(df)` for inspecting the attached
  metadata. Both are exported from the top-level `pulso` namespace.
- Bundled `pulso/data/dane_codebook.json` (1153 unique DANE codes ×
  19 years, 2007–2026 minus 2013) generated from DANE DDI XML 1.2.2.
  The runtime path uses only stdlib + pandas; the generator script
  (and its `lxml` dependency) lives in the `[scraper]` optional extra.

### Metadata coverage at v1.0.0

The composed metadata is built from two sources:

- `variable_map.json` (Curator-curated, 30 canonical Spanish names like
  `sexo`, `edad`, `ingreso_laboral`).
- `dane_codebook.json` (auto-generated from DDI XML, 1153 raw DANE codes).

For a typical analysis of a single module-month — e.g.
`load(2024, 6, "ocupados")` returning 299 columns — the source
distribution after composition is:

- ~5% of columns hit Curator-rich metadata (the canonical happy path).
- ~36% hit codebook-rich metadata (label + categories + universe).
- ~23% hit codebook-partial (label + universe, no categories).
- **~36% hit codebook-skeletal**: variables for which DANE publishes a
  near-empty DDI entry (typically conditional sub-questions like
  `P3044S2`, `P3057`, `P3058S*`, `P30511–P30599`). For these only the
  variable code is available in our pipeline; the full metadata exists
  on DANE's catalog HTML pages but is not yet scraped. `describe_column`
  detects this case explicitly and renders a "skeletal" block pointing
  the user at our issue tracker.
- 0% truly missing.

If you depend on metadata for sub-questions, please open an issue at
<https://github.com/Stebandido77/pulso/issues> — high demand will
trigger an HTML-catalog scraper add-on for v1.1.0.

### Changed

- `lxml` and `playwright` already lived in the `[scraper]` optional
  extra; runtime install of `pulso-co` does not pull them in. The new
  metadata-runtime path (composer + describe helpers) is also lxml-free
  and is regression-tested in `tests/unit/test_metadata/test_no_lxml_runtime.py`.

### Known issues

- GEIH 2013 gap: DANE catalog id 68 returns HTTP 200 with empty body.
  18 years are covered (2007–2012, 2014–2026). Will revisit if DANE
  republishes.
- P3271 (sex in GEIH-2) has no `<catgry>` in DDI; Curator's hand-curated
  `sexo` mapping supplies the categories. Compose precedence ensures
  `describe_column(df, "P3271")` shows rich metadata regardless.
- `df.attrs` is preserved across slicing but pandas does not propagate
  it across `merge`, `groupby`, or `concat`. Re-call
  `pulso.load(..., metadata=True)` (or copy the attrs manually) if you
  need the metadata after one of those operations.

## [1.0.0rc2] — 2026-05-02

### Fixed

- **CRITICAL (C-1):** `download_zip` no longer crashes with `TypeError`
  / `AttributeError` when loading entries with `validated=false` and
  `checksum_sha256: null`. Three separate code paths (cache-key
  generation, cache-hit verification, post-download verification) all
  failed in production for 225 of 230 registry entries. The fix treats
  `checksum=None` as "not verifiable, skip", logs an INFO line, and
  uses a stable period-derived cache filename
  (`unvalidated_{year}-{month:02d}.zip`).
- **MAJOR (M-3):** `download_empalme_zip` now actually performs SHA-256
  verification when the registry has a checksum (9 of 11 years),
  matching the README's promise. Cached files with mismatched checksums
  are removed and re-downloaded; mismatch after re-download raises
  `ChecksumMismatchError`. When no checksum is recorded, verification
  is skipped with an INFO log.
- **MAJOR (M-1):** `load_merged(apply_smoothing=True, modules=[...])`
  now respects the explicit `modules` argument instead of silently
  loading every empalme module.
- **MAJOR (M-2):** `load_merged(modules=["x"])` raises
  `ModuleNotAvailableError` when "x" is unavailable for the period
  instead of silently dropping it. Auto-discovery (`modules=None`)
  still skips silently.
- **MAJOR (M-5):** Multi-period `load(year=range(...))` and
  `load_merged` continue past per-period failures when `strict=False`
  (the new default). Skipped periods are summarised in the same
  aggregated `UserWarning` that lists unvalidated periods. With
  `strict=True` the original abort-on-first-failure behaviour is
  preserved (rc1).
- **MAJOR (M-4):** `expand`, `list_variables`, `describe_variable`,
  and `describe_harmonization` are no longer
  `NotImplementedError("Phase 6")` stubs — they now have working
  implementations with tests.
- README installation snippet (`pip install pulso-co`) and badges now
  use the actual PyPI distribution name (rc1 still said `pulso`).
- `validate_year_month` rejects `bool` and `str` upfront with a clear
  `TypeError` instead of crashing mid-iteration with a cryptic int()
  error.
- `cache_clear(level="...")` raises `CacheError` for unknown levels
  instead of silently no-op'ing (rc1 quietly accepted any string).
- `DataNotValidatedError` message points at the new `strict=False`
  flag instead of the deprecated `allow_unvalidated=True`.

### Added

- **All exception classes** (`PulsoError`, `DataNotValidatedError`,
  `DataNotAvailableError`, `ModuleNotAvailableError`,
  `ChecksumMismatchError`, `DownloadError`, `ParseError`,
  `HarmonizationError`, `MergeError`, `CacheError`, `ConfigError`)
  exported at the top-level `pulso` namespace and listed in `__all__`.
  Users can `except pulso.DataNotValidatedError` directly.
- New `ChecksumMismatchError(DownloadError)` for the post-download
  hash-mismatch path. Existing `except DownloadError` keeps working
  (it's a subclass).
- New `pulso.list_validated_range()` — sorted `list[(year, month)]`
  of entries flagged `validated=True`. Validated months are
  non-contiguous in production, so this deliberately does NOT return
  `(min, max)`.
- New `pulso.validation_status()` — DataFrame with one row per
  registry entry: `year`, `month`, `validated`, `checksum_sha256`,
  `validated_at`, `modules`. Column name `validated_at` matches
  `sources.schema.json`.
- New parameter `strict: bool = False` in `load`, `load_merged`
  (replaces `allow_unvalidated`).
- Integration test matrix (`tests/integration/test_all_validated_months.py`)
  parameterised over every `validated=true` entry in the registry,
  picks up newly validated months automatically.

### Changed

- **BEHAVIORAL CHANGE:** Default for unvalidated entries flips from
  "raise `DataNotValidatedError`" (rc1: `allow_unvalidated=False`) to
  "load with single aggregated `UserWarning`" (rc2: `strict=False`).
  Old behaviour is recoverable via `strict=True`.
  See [`BREAKING_CHANGES_v1.0.0rc2.md`](BREAKING_CHANGES_v1.0.0rc2.md).
- Multi-period load with `strict=False` emits ONE aggregated
  `UserWarning` covering both unvalidated periods and skipped failures,
  instead of N warnings (one per period). Truncates with
  `... and N more` past 10 examples.

### Deprecated

- `allow_unvalidated` parameter in `load`, `load_merged`. Use `strict`
  instead. Will be removed in **v2.0.0**. See
  [`DEPRECATIONS.md`](DEPRECATIONS.md). Emits `DeprecationWarning` at
  every call.

### Internal

- `_emit_unvalidated_warning_at_end=False` private kwarg in `load` so
  `load_merged` can suppress per-module warnings and emit only the
  outer aggregated one.
- Streaming download factored into `_stream_to_file` in
  `pulso/_core/empalme.py`.

## [1.0.0rc1] — 2026-05-01

Initial public release on PyPI as `pulso-co`.

### Critical issue identified post-release

Bug C-1: `download_zip` crashes for any entry with `checksum_sha256: null`,
which is 225 of 230 production entries. Documented and fixed in 1.0.0rc2.
**Users on rc1 should upgrade.**

[1.0.0rc2]: https://github.com/Stebandido77/pulso/compare/v1.0.0rc1...v1.0.0rc2
[1.0.0rc1]: https://github.com/Stebandido77/pulso/releases/tag/v1.0.0rc1
