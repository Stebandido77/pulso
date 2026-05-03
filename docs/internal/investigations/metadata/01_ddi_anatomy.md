# DDI 1.2.2 — anatomía completa para `parse_ddi`

**Samples:** `samples/geih_2024_ddi.xml` (1.8 MB, 760 vars) y
`samples/geih_2018_ddi.xml` (4.5 MB, 1302 vars).
**Inspección:** 2026-05-03, lxml 6.1.0.

Esta nota extiende `dictionaries/05_zip_and_dict_anatomy.md` con
la información empírica que falta para implementar el parser y la
estrategia de merge (Phase 2).

## 1. Estructura del documento

Ambos samples comparten exactamente el mismo perfil DDI:

| Atributo | Valor |
|---|---|
| Root | `{http://www.icpsr.umich.edu/DDI}codeBook` |
| `version` | `1.2.2` |
| Namespace default | `http://www.icpsr.umich.edu/DDI` (sin prefijo) |
| Namespace `xsi` | `http://www.w3.org/2001/XMLSchema-instance` |
| Encoding XML | `UTF-8` |
| `xml-lang` | `es` |

`root.attrib['ID']` es el slug DANE-DIMPE-GEIH-{año}; útil para detectar
el año real cuando `<titl>` está roto (en 2024 dice "2016 metodologia").

`<IDNo>` aparece varias veces; los dos primeros valores son
`COL-DANE-GEIH-{año}` y `DANE-DIMPE-GEIH-{año}`. Estables como source-of-truth
del año, pero siempre habrá que confiar en `catalog_id`/argumento.

## 2. Niveles relevantes para el parser

Solo nos interesa `<dataDscr>` (codebook). Por completitud, los hijos del
root son:

```
<docDscr>     metadata del documento (no útil para el codebook)
<stdyDscr>    descripción del estudio (idem)
<fileDscr>+   uno por archivo de microdata; <fileName>, <fileType>, etc.
<dataDscr>    *** lo único que parseamos ***
  <var>+      uno por variable (760 en 2024; 1302 en 2018)
```

`<fileDscr>` aporta nombres legibles ("Características generales" etc.)
pero el `ID` (`F63`, `F255`) NO es estable entre años. Lo usamos solo como
metadato secundario en `available_in[year].file_id_in_year`.

## 3. Esqueleto del elemento `<var>`

Cada `<var>` tiene 0–N hijos de los siguientes tipos. Frecuencias
observadas:

| Hijo | 2024 (760 vars) | 2018 (1302 vars) | Comentario |
|---|---:|---:|---|
| `<location>` | 760 (100 %) | 1302 (100 %) | Posición de bytes; informativo. |
| `<labl>` | 760 (100 %) | 1302 (100 %) | Etiqueta corta (texto humano). |
| `<varFormat type="…">` | 760 (100 %) | 1302 (100 %) | Tipo declarado. |
| `<catgry>` (≥1) | 408 vars con catgry | ~700 con catgry | Una por categoría. |
| `<sumStat>` | 1513 ocurrencias | 2599 | min, max, vald, invd, etc. |
| `<security>` | 588 / 760 | 1204 / 1302 | Texto idéntico para casi todo. |
| `<respUnit>` | 588 / 760 | 1210 / 1302 | Texto repetitivo. |
| `<universe>` | 588 / 760 | 1207 / 1302 | Texto repetitivo. |
| `<qstn><qstnLit>` | 469 / 760 | 1217 / 1302 | Texto literal de la pregunta. |
| `<valrng><range>` | 407 / 760 | 200 / 1302 | Solo numéricas (min/max). |
| `<txt>` | 38 / 760 | 202 / 1302 | Notas conceptuales largas. |

**Implicación para el parser:** todo lo distinto a `<location>`,
`<labl>` y `<varFormat>` debe usarse con `find()` + `is None` check.

### Atributos del propio `<var>`

- `ID` — id interno DANE (`V3990`, `V13373`). NO estable entre años.
- `name` — código de la variable (`P3271`, `P6020`, `FEX_C18`).
  **Estable**, único dentro de un año, es la clave canónica.
- `files` — `Fxx` (no estable entre años).
- `dcml`, `intrvl` — informativos (`discrete`/`contin`).

### Detección de tipo

`<varFormat type="…">` puede valer `numeric` o `character`, pero no es
fiable como predictor de "categórica vs continua":

- `AREA` y `DPTO` tienen `varFormat type="character"` pero son enteros con
  `<catgry>` (códigos 05, 08, 11…).
- `FEX_C18` y `INGLABO` son `numeric` sin `<catgry>` (continuas).
- `OCI` es `numeric` con un único `<catgry>` (categórica binaria
  presente/ausente).

Por eso definimos:

```
type =
    "categorical" si el <var> tiene ≥1 <catgry>,
    "numeric"     si <varFormat type="numeric"> y no hay catgry,
    "character"   si <varFormat type="character"> y no hay catgry,
    "unknown"     en cualquier otro caso (no debería ocurrir; ver §6).
```

## 4. Variables representativas (XML completo)

Estas se conservan en `01_ddi_anatomy_excerpts.md` (anexo). Resumen:

### Categórica binaria — `P3271` (sólo 2024)
- `<labl>`: `Cuál fue su sexo al nacer?`
- 0 `<catgry>` (¡!) → no es categórica en este DDI; etiqueta es la pregunta.
  *Nota DANE:* aunque conceptualmente el sexo tiene 2 categorías, el DDI
  2024 no las declara explícitamente. Se infiere por `<valrng min=1 max=2>`
  y por `<universe>`. **Este es un dato real para el codebook.**

### Categórica multinivel — `P6020` (sólo 2018)
- `<labl>`: `Sexo`
- 2 `<catgry>`: `{1: Hombre, 2: Mujer}`
- Apareados con `P3271` por `variable_map.json["sexo"]`. **No los unifiquemos
  en el codebook**: cada uno es su propio código.

### Continua sin categorías — `INGLABO`, `FEX_C18`, `P6040`
- `<labl>` legible.
- `<valrng><range UNITS="REAL" min="0" max="…"/>`.
- `<varFormat type="numeric">`.
- 0 `<catgry>`.

### Categórica con códigos territoriales — `AREA`
- `<varFormat type="character">` aunque los códigos son numéricos.
- Categorías DIFIEREN entre años: 2024 tiene 23 ciudades, 2018 tiene 13.
- **Justifica el diseño per-year override.**

## 5. Diferencias entre años

### Variables presentes en ambos samples

- 248 variables comparten `name` entre 2024 y 2018.
- 427 son nuevas en 2024 (cuestionarios post-rediseño 2021: `P3271`,
  `P3038`, `Discapacidad`, `LGBT_Numerica`, `OFICIO_C8`, …).
- 124 sólo viven en 2018 (`ESC`, `INI`, `OFICIO`, `OFICIO1`, `OFICIO2`,
  `P5210Sxx`, …).

### Diferencias dentro de variables compartidas

- `FT` etiqueta cambia: `Fuerza de trabajo` (2018) → `FT` (2024).
- `AREA` categorías cambian (13 vs 23, mismas + nuevas; sin colisión).
- `INGLABO` etiqueta y rango idénticos (afortunadamente).

**Consecuencia para el schema (§Phase 2):** label y categories son
**per-year**, no globales.

## 6. Calidad de datos

- 0 variables sin `<labl>` en ambos años.
- 0 variables sin `<varFormat>` en ambos años.
- 0 `<catgry>` sin `<catValu>` (es decir: si hay categoría, hay valor).
- Todas las cadenas tienen tildes y ñ correctas (sin mojibake).
- Whitespace: cada `<elem>texto</elem>` viene con `\n          texto\n        `.
  Hay que `text.strip()` siempre.

## 7. Tamaño y descarga

| Año | Catálogo | DDI XML | Variables |
|----:|----:|---:|---:|
| 2007 | 317 | (no descargado, esperado >10 MB) | ~1300 |
| 2018 | 547 | 4.5 MB | 1302 |
| 2024 | 819 | 1.8 MB | 760 |
| 2026 | 900 | (no descargado) | ~760 |

Los DDIs pre-2015 son significativamente más grandes (más variables, más
texto en `<txt>`). El builder usará streaming (`requests.get(stream=True)`).

## 8. Implicaciones para el schema final (§Phase 2)

1. **Top-level keyed por DANE code (`P3271`, `FEX_C18`, etc.)**, NO por
   nombre canónico (`sexo`, `peso`). El nombre canónico vive en
   `variable_map.json`; el codebook es el catálogo crudo.

2. **`available_in` per-year:** dict `{"2024": {epoch, file_id, var_id, …}}`
   con label y categorías per-year (override a nivel local).

3. **Top-level fields** (label, categories, type, etc.) representan el
   "valor más reciente" — útil para listados/búsqueda — pero los
   consumidores pueden inspeccionar `available_in[year]` para precisión.

4. **`notes`** capturado de `<txt>` cuando exista. Ejemplo: P6090 (afiliación
   a salud) tiene 5 KB de glosario.

5. **`question_text`** capturado de `<qstn><qstnLit>`. Para variables
   derivadas (FEX_C18, OCI, INGLABO) suele repetir el `<labl>`.

6. **`type`** computado por la heurística de §3, no por `varFormat type=`.

7. **`universe`**, **`response_unit`**: capturado tal cual; mucho texto
   repetitivo se descartará en una pasada de deduplicación opcional (no
   forzosa para v1.0.0).
