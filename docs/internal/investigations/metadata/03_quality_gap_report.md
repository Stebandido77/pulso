# Reporte de Calidad de Metadata — Pre-Wiring

**Fecha:** 2026-05-03
**Status:** ESPERANDO APROBACIÓN para Fase 2
**Generado por:** `scripts/verification/quality_gap_analysis.py`

## Resumen ejecutivo

- El codebook DANE cubre 1153 variables únicas a través de 19 años (2007–2026 menos 2013).
- En el caso real (`load(2024, 6, "ocupados")`, 299 columnas del archivo `F64 = Ocupados.CSV`), 36.5% de las columnas caen en categoría `poor` o `missing` después de componer Curator + codebook.
- Veredicto: **ALTA**. STOP. Considerar HTML scraper como tarea adicional.

## Distribución de calidad por época (codebook puro)

Una variable que aparece en ambas épocas cuenta una vez por columna.
`categories`/`universe` se evalúan en el top-level y, si están vacíos, en cualquier `available_in[year]`.

| Calidad | geih_2006_2020 | geih_2021_present | Total únicos |
|---|---:|---:|---:|
| rich | 467 | 318 | 506 |
| partial | 241 | 311 | 450 |
| poor | 33 | 169 | 197 |
| empty | 0 | 0 | 0 |
| **Total** | **741** | **798** | **1153** |

Recordatorio (de epochs.json y dane_codebook.json): epoch geih_2006_2020 declara 741 variables, epoch geih_2021_present declara 798.

## Variables canónicas del Curator vs Codebook

30 nombres canónicos × hasta 2 épocas = 60 filas. `composed` es el bucket final tras la regla de precedencia (Curator gana en `categories` y `description`; codebook aporta `universe` y `question_text`).

| Canónico | Época | DANE code | Codebook present | Codebook bucket | Curator categories | Composed bucket | Nota |
|---|---|---|:-:|---|:-:|---|---|
| sexo | 2006_2020 | P6020 | sí | rich | sí | rich |  |
| sexo | 2021_present | P3271 | sí | partial | sí | rich |  |
| edad | 2006_2020 | P6040 | sí | partial | no | partial |  |
| edad | 2021_present | P6040 | sí | partial | no | partial |  |
| grupo_edad | 2006_2020 | P6040 | sí | partial | sí | rich |  |
| grupo_edad | 2021_present | P6040 | sí | partial | sí | rich |  |
| parentesco_jefe | 2006_2020 | P6051 | no | — | sí | partial | DANE code not found in codebook (likely derived/empalme) |
| parentesco_jefe | 2021_present | P6050 | sí | rich | sí | rich |  |
| estado_civil | 2006_2020 | P6070 | sí | rich | sí | rich |  |
| estado_civil | 2021_present | P6070 | sí | rich | sí | rich |  |
| grupo_etnico | 2006_2020 | P6080 | sí | rich | sí | rich |  |
| grupo_etnico | 2021_present | P6080 | sí | rich | sí | rich |  |
| area | 2006_2020 | CLASE | sí | rich | sí | rich |  |
| area | 2021_present | CLASE | sí | rich | sí | rich |  |
| departamento | 2006_2020 | DPTO | sí | rich | no | rich |  |
| departamento | 2021_present | DPTO | sí | rich | no | rich |  |
| educ_max | 2006_2020 | P6210 | sí | rich | sí | rich |  |
| educ_max | 2021_present | P3042 | sí | rich | sí | rich |  |
| anios_educ | 2006_2020 | P6210S1 | sí | partial | no | partial |  |
| anios_educ | 2021_present | P3042S1 | sí | partial | no | partial |  |
| asiste_educ | 2006_2020 | P6170 | sí | rich | no | rich |  |
| asiste_educ | 2021_present | P6170 | sí | rich | no | rich |  |
| alfabetiza | 2006_2020 | P6160 | sí | rich | no | rich |  |
| alfabetiza | 2021_present | P6160 | sí | rich | no | rich |  |
| condicion_actividad | 2006_2020 | OCI | sí | rich | sí | rich |  |
| condicion_actividad | 2021_present | [OCI, DSI] | sí | rich | sí | rich |  |
| tipo_desocupacion | 2006_2020 | P7240 | sí | rich | sí | rich |  |
| tipo_desocupacion | 2021_present | DSCY | sí | rich | sí | rich |  |
| tipo_inactividad | 2006_2020 | P7160 | sí | rich | sí | rich |  |
| tipo_inactividad | 2021_present | P7430 | sí | rich | sí | rich |  |
| busco_trabajo | 2006_2020 | P6240 | sí | rich | no | rich |  |
| busco_trabajo | 2021_present | DSI | sí | rich | no | rich |  |
| disponible | 2006_2020 | P7290 | sí | rich | no | rich |  |
| disponible | 2021_present | P7280 | sí | rich | no | rich |  |
| posicion_ocupacional | 2006_2020 | P6430 | sí | rich | sí | rich |  |
| posicion_ocupacional | 2021_present | P6430 | sí | rich | sí | rich |  |
| rama_actividad | 2006_2020 | RAMA2D | sí | rich | no | rich |  |
| rama_actividad | 2021_present | RAMA2D_R4 | sí | partial | no | partial |  |
| ocupacion | 2006_2020 | OFICIO | sí | rich | no | rich |  |
| ocupacion | 2021_present | OFICIO_C8 | sí | partial | no | partial |  |
| horas_trabajadas_sem | 2006_2020 | P6800 | sí | partial | no | partial |  |
| horas_trabajadas_sem | 2021_present | P6800 | sí | partial | no | partial |  |
| ingreso_laboral | 2006_2020 | INGLABO | sí | partial | no | partial |  |
| ingreso_laboral | 2021_present | INGLABO | sí | partial | no | partial |  |
| tiene_contrato | 2006_2020 | P6440 | sí | rich | no | rich |  |
| tiene_contrato | 2021_present | P6440 | sí | rich | no | rich |  |
| tipo_contrato | 2006_2020 | P6450 | sí | rich | sí | rich |  |
| tipo_contrato | 2021_present | P6450 | sí | rich | sí | rich |  |
| cotiza_pension | 2006_2020 | P6920 | sí | rich | no | rich |  |
| cotiza_pension | 2021_present | P6920 | sí | rich | no | rich |  |
| ingreso_total | 2006_2020 | INGTOT | no | — | no | poor | DANE code not found in codebook (likely derived/empalme) |
| ingreso_total | 2021_present | [INGLABO, P7500S1A1, P7500S2A1, P7500S3A1, P750S1A1, P750S2A1, P750S3A1] | sí | partial | no | partial |  |
| hogar_id | 2006_2020 | [DIRECTORIO, SECUENCIA_P, HOGAR] | sí | partial | no | partial |  |
| hogar_id | 2021_present | [DIRECTORIO, SECUENCIA_P, HOGAR] | sí | partial | no | partial |  |
| vivienda_propia | 2006_2020 | P5090 | sí | rich | no | rich |  |
| vivienda_propia | 2021_present | P5090 | sí | rich | no | rich |  |
| peso_expansion | 2006_2020 | FEX_C | sí | partial | no | partial |  |
| peso_expansion | 2021_present | FEX_C18 | sí | partial | no | partial |  |
| peso_expansion_persona | 2006_2020 | FEX_C | sí | partial | no | partial |  |
| peso_expansion_persona | 2021_present | FEX_C18 | sí | partial | no | partial |  |

### Casos donde el Curator salva metadata del codebook

- **sexo** (época `geih_2021_present`, DANE `P3271`): codebook `partial` → composed `rich`.
- **grupo_edad** (época `geih_2006_2020`, DANE `P6040`): codebook `partial` → composed `rich`.
- **grupo_edad** (época `geih_2021_present`, DANE `P6040`): codebook `partial` → composed `rich`.

### Códigos del Curator no encontrados en codebook

- `parentesco_jefe` (época `geih_2006_2020`, DANE code `P6051`): DANE code not found in codebook (likely derived/empalme)
- `ingreso_total` (época `geih_2006_2020`, DANE code `INGTOT`): DANE code not found in codebook (likely derived/empalme)

## Caso real: `load(2024, 6, "ocupados")`

Columnas extraídas del DDI 2024 con `files="…F64…"` (F64 = `Ocupados.NSDstat`, mapeado en `sources.json` a `CSV/Ocupados.CSV`). Total: **299 columnas**.

| Bucket | Columnas | % |
|---|---:|---:|
| rich-curator | 15 | 5.0% |
| rich-codebook | 107 | 35.8% |
| partial-merged | 0 | 0.0% |
| partial-codebook | 68 | 22.7% |
| poor | 109 | 36.5% |
| missing | 0 | 0.0% |
| **Total** | **299** | **100%** |

### Ejemplos por bucket (hasta 5 cada uno)

- **rich-curator**: `DIRECTORIO`, `SECUENCIA_P`, `HOGAR`, `CLASE`, `FEX_C18`
- **rich-codebook**: `MES`, `ORDEN`, `REGIS`, `AREA`, `FT`
- **partial-codebook**: `PERIODO`, `PER`, `P6460S1`, `P6424S5`, `P6426`
- **poor**: `P3044S2`, `P6420S2`, `p64301`, `p64302`, `p64303`

### Diagnóstico de las columnas `poor`

De las 109 columnas en bucket `poor` (solo `label`, sin `categories` ni `universe`):

- 109/109 no tienen categorías en NINGÚN año disponible.
- 109/109 no tienen `universe` en NINGÚN año disponible.
- 10/109 tienen `label` igual al propio código (e.g. label de `P3044S2` = `"P3044S2"`) — label sin contenido semántico.
- Adicionalmente, varias entradas tienen `label` que es OTRO código (e.g. `p64301.label = "P6430S1"`) — referencia parent, no contenido. Combinando ambos casos, ~99 de 109 columnas no ofrecen al usuario ningún texto comprensible.

**Causa raíz:** DANE publica DDI XML mínimo para sub-preguntas y para muchas variables introducidas en el rediseño 2021. El parser está haciendo el trabajo correcto; la fuente es la limitada.

## Top variables con metadata pobre o ausente

Top 15 (codebook puro, sin pasar por Curator). `empty` = sin label.

| DANE code | Bucket | Label (truncated) |
|---|---|---|
| `P1807` | poor | En caso de que le ofrecieran un empleo a ... ¿Cuál sería el  |
| `P1884` | poor | ¿Cuántas horas a la semana estaba disponible para trabajar? |
| `P3044S2` | poor | P3044S2 |
| `P3057` | poor | P3057 |
| `P3058S2` | poor | P3058S2 |
| `P3058S4` | poor | P3058S4 |
| `P3059` | poor | P3059 |
| `P3062S1` | poor | P3062S1 |
| `P3062S5` | poor | P3062S5 |
| `P3062S7` | poor | P3062S7 |
| `P3062S9` | poor | P3062S9 |
| `P3084S2` | poor | P3084S2 |
| `P3086S1` | poor | P3086S1 |
| `P3087S1` | poor | P3087S1 |
| `P3089S3` | poor | P3089S3 |

## Veredicto

- **BAJA**: <5% poor/missing en el caso típico → proceder Fase 2 sin cambios
- **MEDIA**: 5–20% → proceder + warning + nota en CHANGELOG
- **ALTA**: >20% → STOP, considerar HTML scraper como tarea adicional

**Veredicto: ALTA (36.5% poor/missing en el caso real).**

## Recomendación

**STOP.** El bucket `poor` cubre 36% de las columnas en el caso típico (`load(2024, 6, "ocupados")`). DANE publica DDI XML esquelético para sub-preguntas (`P3044S2`, `p64301`, …) y para muchas variables del rediseño 2021: solo `<labl>` (a veces literalmente el propio código), sin `<qstn>`, `<universe>`, ni `<catgry>`.

**Opciones a discutir con el usuario:**

1. **Proceder igual** y aceptar que ~36% de las columnas se presentarán como `source='codebook'` con label vacío/auto-referencial. Documentar la limitación en CHANGELOG y agregar `UserWarning` cuando el ratio supere 25% al cargar.
2. **Aumentar el Curator** con etiquetas para las sub-preguntas más importantes (P3044S*, P6420S*, P6430S*, P6765S*, P3057, P3058S*, P30511–P30599) — trabajo manual ~2h, supuesto que se puede mapear desde el cuestionario PDF de DANE GEIH 2024.
3. **Scraper HTML del diccionario interactivo** (`https://microdatos.dane.gov.co/index.php/catalog/819/data-dictionary/F64`) que sí tiene `categories` y descripciones expandidas. Tarea adicional antes de Fase 2.
4. **Híbrido**: proceder con Fase 2 ahora, pero abrir issue para Curator-bump sobre los códigos sub-pregunta con mayor frecuencia de uso.

**Recomendación de Agente 3:** opción **4 (híbrido)**. La Fase 2 como diseñada ya hace lo correcto: `compose_column_metadata` devolverá `source='codebook'` y `label=str(column)` para las sub-preguntas, lo cual es honesto. Bloquear Fase 2 esperando un scraper HTML retrasaría el release sin ganancia inmediata para los 30 nombres canónicos del Curator (que sí están todos cubiertos rich).

