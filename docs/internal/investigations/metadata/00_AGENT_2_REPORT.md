# Agente 2 — Reporte consolidado

**Branch:** `feat/v1.0.0-metadata`
**Base:** `06af4f6` (Agente 1's discovery)
**Fecha:** 2026-05-03

## Architecture choice

**Option A — build script + pre-computed JSON committed** (as recommended).

Justificación de una línea: replica el patrón existente de pulso (`sources.json` también es un artefacto pre-computado en repo y consumido en read-only por `_config.registry`), evita ejecutar HTTP en cada `pip install`, y el archivo final pesa <10 MB — cabe sin gzip.

## Schema highlights

`pulso/data/schemas/dane_codebook.schema.json` (Draft-07).

- **Top-level keys:** `schema_version`, `generated_at`, `source`, `coverage_years`, `epochs`, `variables`.
- **`variables` está keyed por DANE code** (`P3271`, `P6020`, `FEX_C18`, `OCI`, etc.). NO por nombre canónico — los nombres canónicos viven en `variable_map.json`. Los dos artefactos coexisten sin solaparse.
- **`available_in[year]` per-year override:** cada año lleva su propio `label`, `categories`, `value_range`, `question_text`. Top-level fields representan el "valor del año más reciente" (lookup trivial). Justificación documentada en `02_schema_design.md`: AREA cambia de 13 a 23 categorías entre 2018 y 2024 — un override aplanado perdería esa verdad histórica.
- **Tipo inferido por presencia de `<catgry>`**, no por `<varFormat type=>` — DANE marca `AREA`/`DPTO` como `character` aunque sean enteros con catgry. La heurística `categorical → numeric → character → unknown` es uniforme.
- **`notes` captura `<txt>` concatenado** (notas conceptuales largas, e.g. P6090 con 5 KB de glosario de seguridad social).

Ver `02_schema_design.md` §5 para ejemplos completos de P6020 (categórica) y INGLABO (numérica).

## `dane_codebook.json` stats

| Métrica | Valor |
|---|---|
| Total unique variables | **1153** |
| Tamaño en disco | 6.7 MB (156 142 líneas, JSON con `indent=2`, `sort_keys=True`, UTF-8) |
| Cobertura años efectiva | **19 de 20** años (2007-2026 menos **2013**) |
| Variables en `geih_2006_2020` | 741 |
| Variables en `geih_2021_present` | 798 |
| Schema version | `1.0.0` |
| Source | `DANE DDI-XML 1.2.2` |

## Test summary

**22 tests añadidos** en `tests/unit/test_metadata/test_parser.py`. Total: **304 passed, 297 skipped, 0 failed** (baseline era 282 + 22 = 304).

Coverage en `pulso/metadata/`:

```
pulso/metadata/__init__.py      100%
pulso/metadata/parser.py         88%
pulso/metadata/schema.py          0%   (puro typing, sin código ejecutable)
TOTAL                            73%   (parser stand-alone: 88%, supera el 80% objetivo)
```

Ruff: `check` + `format --check` pasan en `pulso/metadata/`, `scripts/build_dane_codebook.py`, `tests/unit/test_metadata/`.

## Curator artifacts unchanged

```
07281bb8259aa6eea769e7fe5495a4cad0f9f2e6e5a09c463c5679cc02156c1f *pulso/data/variable_map.json
90c8539151da2aee5553eb075155ef3789704d6df2b85f3a218640f5f4c439ed *pulso/data/schemas/variable_map.schema.json
```

Idénticos al baseline. Confirmado.

## Sorpresas durante la implementación

1. **DANE catalog 68 (año 2013) devuelve HTTP 200 con body vacío.** El catálogo existe (página HTML viva), pero el endpoint `/metadata/export/68/ddi` no genera el XML. Manejo: el builder detecta el cuerpo vacío, lanza `EmptyDDIError`, registra warning, sigue adelante. El artefacto final cubre 19/20 años. Ningún `--retry` lo arregla porque DANE responde 200 estable.

2. **Cada `<var>` se repite una vez por `<fileDscr>` que lo contiene.** El sample 2024 tiene 760 elementos `<var>` pero sólo 675 códigos únicos; el 2018 tiene 1302 elementos pero 372 códigos únicos. Originalmente la brief asumía 760/1302 como counts target. El parser deduplica por `name` y concatena `file_id_in_year` con coma. Los tests asertan los conteos correctos (675/372).

3. **`varFormat type=`** no es confiable como predictor de "categórica vs numérica continua". `AREA` y `DPTO` declaran `character` pero tienen `<catgry>`. Decisión: **categorías presentes → categorical; sino, lo que diga `varFormat`**.

4. **Mismo concepto, distintos códigos en distintos años**, e incluso **categorías distintas** para el mismo código entre años (AREA: 13 ciudades en 2018, 23 en 2024). El schema soporta esto vía per-year override.

5. **`P6020` aparece en 2021** además de 2007-2020. El año 2021 fue de transición y DANE publicó dos esquemas; pulso ya documenta la frontera 2021/2022 en `epochs.json` (`date_range[0] = 2022-01`). El codebook lo refleja: P6020 cubre 2007-2021, P3271 cubre 2022-2026.

6. **DANE publica codebooks idénticos para 2023, 2024, 2025, 2026** (mismos 675 códigos exactos). Probablemente reusan plantilla. No es un bug; es la realidad de DANE.

7. **Dos códigos casi-iguales:** existe `AREA` y `Area`, `CLASE` y `Clase` en algunos años. Faithful representation de los XML originales (no es un bug del parser). Agente 3 puede decidir si deduplicar case-insensitively para la API pública o no.

## Decisiones pendientes para el usuario antes de Agente 3

1. **¿Empaquetar `lxml` como dependencia core?** Hoy está en `[scraper]` extra. El parser solo se ejecuta en CI/build, no al cargar `pulso`. Recomendación: **dejar lxml fuera de core**; agregar `[metadata]` extra opcional o mover lxml al extra `[dev]` ya que el JSON pre-computado es lo que ven los usuarios.

2. **Deduplicación case-insensitive de códigos (`AREA` vs `Area`)?** Hoy se preservan tal cual. Pro de dedupe: API más limpia. Pro de no-dedupe: faithful. **Recomendación: no dedupe, dejar a Agente 3 decidir cómo presentar al usuario.**

3. **¿Reportar oficialmente el problema 2013 a DANE o documentar y seguir?** Recomendación: documentar en CHANGELOG; reabrir si DANE eventualmente repuebla el endpoint.

4. **Tamaño del artefacto: 6.7 MB.** Cabe en sdist sin compresión. Si a Agente 3 le preocupa el tamaño del wheel, se podría comprimir como `.json.gz` o splittear por epoch. **Recomendación: dejar como está hasta tener feedback de tamaño**.

5. **Top-level "fields del año más reciente" estrategia**: si Agente 3 necesita filtros tipo "give me current GEIH variables" vs "give me historical", ya tiene `available_in` per-year y `coverage_years` para construirlo. El campo `comparability_warning` (estilo variable_map.json) NO existe en el codebook — Agente 3 puede agregarlo si fusionando ambas fuentes.

## Referencias

- `pulso/metadata/parser.py` — `parse_ddi(path, year=…)` + `DDIParseError`.
- `pulso/metadata/schema.py` — TypedDicts (`Variable`, `YearEntry`, `DaneCodebook`, etc.).
- `pulso/data/dane_codebook.json` — artefacto generado (6.7 MB).
- `pulso/data/schemas/dane_codebook.schema.json` — Draft-07 schema.
- `scripts/build_dane_codebook.py` — builder con `--years`, `--no-download`, `--cache-dir`, `--output`.
- `tests/unit/test_metadata/test_parser.py` — 22 tests, 88% coverage de parser.
- `docs/internal/investigations/metadata/01_ddi_anatomy.md` — análisis completo del DDI 1.2.2.
- `docs/internal/investigations/metadata/01_ddi_anatomy_excerpts.md` — XML excerpts variables representativas.
- `docs/internal/investigations/metadata/02_schema_design.md` — diseño detallado del schema.
- `.gitignore` — `.ddi_cache/` añadido.

Cache local de DDI XMLs (no commiteado): `.ddi_cache/` (19 archivos, ~80 MB).
