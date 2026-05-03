# `dane_codebook.json` — diseño del schema

**Decisión:** schema versión `1.0.0`, archivo en
`pulso/data/dane_codebook.json`, validado con
`pulso/data/schemas/dane_codebook.schema.json` (Draft-07).

Este artefacto coexiste con `pulso/data/variable_map.json` (que sigue
siendo el Curator harmonisation contract — keyed by canonical Spanish
name). Ningún campo se duplica: el codebook describe **lo que DANE
publica**; el variable_map describe **cómo pulso lo reescribe**.

## 1. Top-level

```json
{
  "schema_version": "1.0.0",
  "generated_at": "2026-05-03T14:00:00Z",
  "source": "DANE DDI-XML 1.2.2",
  "coverage_years": [2007, 2008, ..., 2026],
  "epochs": {
    "geih_2006_2020": {"years": [2007, ..., 2020], "variable_count": N},
    "geih_2021_present": {"years": [2021, ..., 2026], "variable_count": M}
  },
  "variables": {
    "P3271": { ... },
    "P6020": { ... },
    "FEX_C18": { ... }
  }
}
```

`coverage_years` es la lista de años efectivamente parseados (puede ser
subconjunto si se corre con `--years 2018,2024`). Es el contrato con los
consumidores.

`epochs` mantiene el mismo conjunto de keys que `pulso/data/epochs.json`
(`geih_2006_2020`, `geih_2021_present`). Los valores son derivados
(qué años cubrió este artefacto, cuántas vars únicas se encontraron).

`variables` es **un dict keyed por DANE code** (`name` del `<var>`).
Mantiene el espíritu de pulso: los nombres canónicos en Español viven en
otra parte; el codebook habla DANE puro.

## 2. Esquema por variable

Decisión: **per-year override**. Cada `available_in[year]` lleva su
propio `label`, `categories`, `question_text`, etc. Los campos top-level
representan el **valor del año más reciente** (= el que probablemente
quieren ver los usuarios al hacer `pulso.describe_codebook("P3271")`).

```json
"P3271": {
  "code": "P3271",
  "label": "Cuál fue su sexo al nacer?",
  "type": "numeric",
  "question_text": "Cuál fue su sexo al nacer?",
  "universe": "El universo para la Gran Encuesta Integrada de Hogares está conformado por la población civil no institucional, residente en todo el territorio nacional.",
  "response_unit": "La encuesta utiliza informante directo …",
  "categories": null,
  "value_range": {"min": 1.0, "max": 2.0},
  "notes": null,
  "available_in": {
    "2021": {
      "epoch": "geih_2021_present",
      "file_id_in_year": "F63",
      "var_id_in_year": "V3990",
      "label": "Cuál fue su sexo al nacer?",
      "type": "numeric",
      "question_text": "Cuál fue su sexo al nacer?",
      "categories": null,
      "value_range": {"min": 1.0, "max": 2.0}
    },
    "2022": { ... },
    "2023": { ... },
    "2024": { ... },
    "2025": { ... },
    "2026": { ... }
  }
}
```

### Campos a nivel `variables[code]`

| Campo | Tipo | Notes |
|---|---|---|
| `code` | string | Igual que la key, redundante para facilitar iteración. |
| `label` | string | Etiqueta del año más reciente disponible. |
| `type` | enum (`categorical`, `numeric`, `character`, `unknown`) | Heurística: hay `<catgry>`? entonces `categorical`. |
| `question_text` | string \| null | `<qstn><qstnLit>` del año más reciente. |
| `universe` | string \| null | `<universe>` del año más reciente. |
| `response_unit` | string \| null | `<respUnit>` del año más reciente. |
| `categories` | object \| null | `{catValu: labl}` del año más reciente, si la variable es categórica. |
| `value_range` | `{min: number, max: number}` \| null | `<valrng><range>`. |
| `notes` | string \| null | `<txt>` (concatenado si hay varios). |
| `available_in` | object | Una entrada por año donde aparece el código. |

### Campos a nivel `available_in[year]`

| Campo | Tipo | Notes |
|---|---|---|
| `epoch` | enum (`geih_2006_2020`, `geih_2021_present`) | Derivado de la tabla en `epochs.json`. |
| `file_id_in_year` | string | `Fxx` específico de ese año (informativo). |
| `var_id_in_year` | string | `Vxxxx` (informativo, no estable). |
| `label` | string | Etiqueta de **ese año**. |
| `type` | enum | Tipo en ese año. |
| `question_text` | string \| null | Texto de pregunta de ese año. |
| `categories` | object \| null | Categorías de ese año (puede diferir entre años, ver §4). |
| `value_range` | `{min, max}` \| null | Rango de ese año. |

### Por qué per-year override y no `by_year_overrides`

Probé tres variantes:

| Opción | Pros | Contras |
|---|---|---|
| Solo top-level (último año), sin per-year | JSON pequeño | Pierde la verdad histórica de las categorías cambiantes (AREA: 13 → 23 ciudades). Inviable. |
| Top-level fijo + `by_year_overrides[year]` solo si difiere | JSON aún más pequeño | Lógica de lookup compleja para el consumidor (¿usa el override o el top-level?). |
| **Per-year `available_in[year]` siempre full** | Lookup trivial; cada año es self-contained. | JSON ~4–5x más grande. |

Elegimos la tercera. Estimación: 1500 vars × 20 años × ~0.5 KB ≈ 15 MB
sin compresión, ~3–4 MB con sort_keys + repetición. Aceptable; el archivo
no se carga en memoria por todos los consumidores (Agente 3 puede hacer
lazy-load por código si pesa demasiado).

## 3. Detección de tipo

```python
def infer_type(var_elem) -> str:
    if var_elem.findall("ddi:catgry", namespaces=NS):
        return "categorical"
    fmt = var_elem.find("ddi:varFormat", namespaces=NS)
    if fmt is None:
        return "unknown"
    return fmt.get("type", "unknown")  # "numeric" | "character"
```

Esta heurística cubre todos los samples observados sin error. Variables
como `AREA` (catgry presente) → `categorical`, `INGLABO` (sin catgry,
varFormat=numeric) → `numeric`, etc.

## 4. Manejo de divergencias entre años

Para una misma `code`, las categorías pueden diferir:

- `AREA` 2018: 13 ciudades. AREA 2024: 23 ciudades.
- `FT` 2018 label = `"Fuerza de trabajo"`. FT 2024 label = `"FT"`.

**Regla:**

1. `available_in[year].label` y `.categories` son la verdad de ese año.
2. Top-level `label`/`categories` = los del año máximo en `available_in`.
3. Si dos años tienen valores **idénticos** para un código, sus
   `available_in[y]` simplemente repiten esos valores. La redundancia es
   intencional (lookup trivial).

No marcamos divergencias explícitamente (no hay un campo `has_drift`).
Los consumidores que quieran detectarlo pueden iterar `available_in`.

## 5. Ejemplos finales

### Ejemplo categórico — `P6020` (sexo, epoch_a)

```json
"P6020": {
  "code": "P6020",
  "label": "Sexo",
  "type": "categorical",
  "question_text": "2. Sexo\n\n1\tHombre\n2\tMujer",
  "universe": "El universo para la Gran Encuesta Integrada de Hogares …",
  "response_unit": "La encuesta utiliza informante directo …",
  "categories": {"1": "Hombre", "2": "Mujer"},
  "value_range": null,
  "notes": null,
  "available_in": {
    "2007": {"epoch": "geih_2006_2020", "file_id_in_year": "F255", "var_id_in_year": "V13373",
              "label": "Sexo", "type": "categorical",
              "categories": {"1": "Hombre", "2": "Mujer"},
              "question_text": "2. Sexo\n\n1\tHombre\n2\tMujer", "value_range": null},
    "...": "...",
    "2020": { ... }
  }
}
```

### Ejemplo numérico — `INGLABO` (ingresos laborales)

```json
"INGLABO": {
  "code": "INGLABO",
  "label": "Ingresos laborales",
  "type": "numeric",
  "question_text": "Ingresos Laborales",
  "universe": "El universo para la Gran Encuesta Integrada de Hogares …",
  "response_unit": "La encuesta utiliza informante directo …",
  "categories": null,
  "value_range": {"min": 0.0, "max": 30000000.0},
  "notes": null,
  "available_in": {
    "2018": {"epoch": "geih_2006_2020", "file_id_in_year": "F259", "var_id_in_year": "V13592",
              "label": "Ingresos laborales", "type": "numeric",
              "categories": null,
              "question_text": "Ingresos Laborales",
              "value_range": {"min": 0.0, "max": 30000000.0}},
    "...": "...",
    "2024": { ... }
  }
}
```

## 6. Versionado del schema

`schema_version` es semver simple. Cambios:

- `1.0.0` (este). Captura DDI 1.2.2 con per-year override. Si DANE cambia
  a DDI 1.3 / 2.x, bumping a `2.0.0` y nuevo parser.
- Añadir campos opcionales nuevos = bump minor.
- Cambiar tipos / quitar campos = bump major.
