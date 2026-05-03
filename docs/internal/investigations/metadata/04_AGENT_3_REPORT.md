# Reporte Agente 3: Wiring de Metadata en `load()`

**Status:** COMPLETO — Esperando aprobación humana
**Branch:** `feat/v1.0.0-metadata`
**HEAD:** pendiente (push al final)
**Fecha:** 2026-05-03

## Resumen ejecutivo

- `pulso.load(metadata=True)` y `pulso.load_merged(metadata=True)`
  componen y adjuntan metadata Curator+codebook a `df.attrs["column_metadata"]`.
- Nuevas helpers `pulso.describe_column(df, column)` y
  `pulso.list_columns_metadata(df)` (públicas; en `__all__`).
- Caso skeletal (`P3044S2`, `P3057`, …) tiene su propio rendering con
  link al issue tracker — la limitación queda visible para el usuario.

## Cambios implementados

| Archivo | Naturaleza |
|---|---|
| `pulso/metadata/__init__.py` | Lazy-load de `parse_ddi`/`DDIParseError` (PEP 562 `__getattr__`). El runtime ya no carga lxml al importar `pulso.metadata.composer` o `.api`. |
| `pulso/metadata/composer.py` (NUEVO) | `compose_column_metadata`/`compose_dataframe_metadata` con precedencia Curator>codebook documentada. Lazy-load + memo de codebook, reverse-index `(epoch, dane_code)→canonical`, lookup case-insensitive AREA/CLASE. Pure stdlib + pandas. |
| `pulso/metadata/api.py` (NUEVO) | `describe_column` + `list_columns_metadata` con renderer §B para variables esqueléticas (`(sub-question, skeletal metadata)` y URL del issue tracker). |
| `pulso/_core/loader.py` | `metadata: bool = False` keyword-only en `load` y `load_merged`. Helpers `_attach_metadata_for_load`/`_attach_metadata_for_load_merged` aislados. Tracking de `used_modules` para `df.attrs["source_modules"]` en merged. |
| `pulso/__init__.py` | Export `describe_column`, `list_columns_metadata` (alfabéticos en `__all__`). |
| `tests/unit/test_metadata/test_composer.py` (NUEVO) | 12 tests: curator-only, codebook-only, merged P3271 / P6020, missing, case-insensitive AREA + CLASE, skeletal, dataframe-realistic, tildes, módulo Curator, resolución de época. |
| `tests/unit/test_metadata/test_api.py` (NUEVO) | 10 tests: canonical / merged / skeletal / not-in-df ValueError / no-metadata hint / column-added-after / list shape / list-without-attrs / tildes / public API export. |
| `tests/unit/test_metadata/test_no_lxml_runtime.py` (NUEVO) | 1 test: importar el runtime metadata no carga lxml. |
| `tests/integration/test_metadata_e2e.py` (NUEVO) | 5 tests gated por `--run-integration`: load(metadata=True), load(metadata=False) omite attrs, load_merged(metadata=True) con `source_modules`, describe_column real, list_columns_metadata real. |
| `CHANGELOG.md` | Bloque "Unreleased — v1.0.0" honesto sobre el ~36% skeletal y los 4 buckets de cobertura. |
| `docs/quickstart.md` | Sección "Column-level metadata" con ejemplos. |
| `README.md` | Snippet de `metadata=True` + 2 entradas en la tabla de API. |

## Smoke test del caso de uso

Ejecutado con `tests/integration/test_metadata_e2e.py` (Shape B unified
fixture) y un script ad-hoc usando `compose_dataframe_metadata` para el
caso skeletal. Output literal pegado:

```
=== loaded shape: (50, 21) ===

--- describe_column(df, 'sexo') ---
sexo: Sexo de la persona.
DANE code: P3271
Description (es): Sexo de la persona.
Description (en): Person's sex.
Type: categorical
Module: caracteristicas_generales
Epoch: geih_2021_present
Categories:
  1 = hombre
  2 = mujer
Notes: El código de variable cambió de P6020 (marco 2005) a P3271 (marco 2018). ...
Source: curator

--- describe_column(synth, 'P3044S2') ---
P3044S2 (sub-question, skeletal metadata)
Type: numeric
Module: unknown
Source: codebook (skeletal)
Note: Full metadata available on DANE catalog HTML, not yet integrated.
      Open issue at https://github.com/Stebandido77/pulso/issues if you
      need this for your analysis.

--- describe_column(df, 'P3271') ---
P3271: Sexo de la persona.
Canonical name: sexo
Description (es): Sexo de la persona.
Description (en): Person's sex.
Type: categorical
Module: caracteristicas_generales
Epoch: geih_2021_present
Question text: Cuál fue su sexo al nacer?
Universe: El universo para la Gran Encuesta Integrada de Hogares está conformado
          por la población civil no institucional, residente en todo el territorio nacional.
Value range: [1.0, 2.0]
Categories:
  1 = hombre
  2 = mujer
Notes: El código de variable cambió de P6020 (marco 2005) a P3271 (marco 2018). ...
Source: merged
  (categories/description from Curator's variable_map.json; question_text/universe from DANE codebook.)

--- list_columns_metadata(df).head(10) ---
     column                                                                        label        type                    module   source  has_categories
 DIRECTORIO Identificador único del hogar construido concatenando las claves de empalme.      string caracteristicas_generales   merged           False
SECUENCIA_P Identificador único del hogar construido concatenando las claves de empalme.      string caracteristicas_generales   merged           False
      ORDEN                                                                        Orden     numeric                       NaN codebook           False
      HOGAR Identificador único del hogar construido concatenando las claves de empalme.      string caracteristicas_generales   merged           False
        MES                                                                          Mes   character                       NaN codebook           False
      CLASE        Área geográfica: cabecera municipal, centro poblado o rural disperso. categorical caracteristicas_generales   merged            True
      P3271                                                          Sexo de la persona. categorical caracteristicas_generales   merged            True
      P6040                                                      Edad en años cumplidos.     numeric caracteristicas_generales   merged           False
    FEX_C18              Factor de expansión para estimaciones de totales poblacionales.     numeric caracteristicas_generales   merged           False
        OCI              Condición de actividad laboral: ocupado, desocupado o inactivo. categorical caracteristicas_generales   merged            True

source distribution: merged=10, curator=9, codebook=2
```

Las tildes y caracteres no-ASCII se preservan en todos los renderings.

## Métricas

- **Tests:** 326 passed, 302 skipped, 0 failed (baseline pre-Phase 2: 304 passed, 297 skipped). 22 tests nuevos + 5 tests gated por `--run-integration`.
- **Cobertura `pulso/metadata/composer.py`:** 93%.
- **Cobertura `pulso/metadata/api.py`:** 88%.
- **Curator SHA256:** ✓ idéntico al baseline.
  - `pulso/data/variable_map.json` → `07281bb8259aa6eea769e7fe5495a4cad0f9f2e6e5a09c463c5679cc02156c1f`
  - `pulso/data/schemas/variable_map.schema.json` → `90c8539151da2aee5553eb075155ef3789704d6df2b85f3a218640f5f4c439ed`
- **Wheel:** `pulso_co-1.0.0rc2-py3-none-any.whl` = 415,864 bytes (incluye codebook 7 MB descomprimido).
- **Lint/format:** `ruff check` + `ruff format --check` clean en todos los archivos modificados.

## CHANGELOG entry

Ver `CHANGELOG.md` líneas 8–60 (sección `## [Unreleased] — v1.0.0`).
Bloques principales:

- **Added**: `metadata=True`, `describe_column`, `list_columns_metadata`,
  bundled codebook.
- **Metadata coverage at v1.0.0**: distribución honesta — ~5% Curator-rich,
  ~36% codebook-rich, ~23% codebook-partial, ~36% codebook-skeletal,
  0% missing. Apunta al issue tracker para el escenario skeletal.
- **Changed**: documenta que `lxml`/`playwright` están en el extra
  `[scraper]` y que la nueva ruta de metadata es lxml-free, con
  regression test.
- **Known issues**: 2013 gap, P3271 sin `<catgry>` (Curator suple),
  `df.attrs` no sobrevive merge/groupby/concat.

## Issues / Limitaciones

- **~36% de columnas en `load(2024, 6, "ocupados")` son skeletal.** El
  `describe_column` lo señala explícitamente con bloque dedicado. Documentado en CHANGELOG. Si la demanda lo justifica, Agente 5 implementaría un scraper HTML del catálogo DANE.
- **`df.attrs` no se propaga por `merge`/`groupby`/`concat`.** Limitación de pandas — documentada en docstrings de `load`/`describe_column`/`list_columns_metadata` y en el CHANGELOG.
- **`compose_column_metadata` recibe `module` pero no lo usa hoy.** Reservado para overrides por módulo en el futuro (suprimido con `# noqa: ARG001`). El argumento se mantiene para no romper la firma cuando se introduzca el feature.
- **`load_merged` ancla la metadata al último período cargado.** Si el rango cruza épocas, el metadata refleja el período final. Es honesto (y la mayoría de las llamadas son single-period o single-epoch).
- **Caso de Curator donde el código DANE es una lista** (`ingreso_total = [INGLABO, ...]` en GEIH-2): el reverse-index registra cada código y el primer canonical en orden de archivo gana. No se observan colisiones en el variable_map actual.

## Próximos pasos

- **Agente 4:** fixes pendientes rc2 (ParseError 2024-03/04, verbosidad, regresión variable_map). NO empezar sin autorización del usuario.
- **Agente 5 (condicional):** scraper HTML del catálogo DANE para enriquecer las ~36% sub-preguntas, si feedback de v1.0.0 lo justifica.
