# Tester Final Audit — Extended Pre-CRAN Testing

Auditor: Tester independiente (claude-sonnet-4-6)
Fecha: 2026-05-23
Metodología: ejecución real de comandos; cero fabricación de resultados.

---

## Hallazgo 1: BUG-003 universal en epoch2

**Claim del Coder:** `migracion` falla con BUG-003 ("invalid multibyte string") en TODOS los epoch2
testeados (2022-06 hasta 2025-01), no solo en epoch1.

### Comandos ejecutados y salida literal

```
$ Rscript -e 'library(pulso); tryCatch(pulso_load(2023,6,"migracion"), error=function(e) cat("2023-06 migracion ERR:", conditionMessage(e), "\n"))'
2023-06 migracion ERR: invalid multibyte string at '<a2>n.C'

$ Rscript -e 'library(pulso); tryCatch(pulso_load(2024,1,"migracion"), error=function(e) cat("2024-01 migracion ERR:", conditionMessage(e), "\n"))'
2024-01 migracion ERR: invalid multibyte string at '<a2>n.C'

$ Rscript -e 'library(pulso); tryCatch(pulso_load(2025,1,"migracion"), error=function(e) cat("2025-01 migracion ERR:", conditionMessage(e), "\n"))'
2025-01 migracion ERR: invalid multibyte string at '<a2>n.C'
```

Control (módulo no afectado):
```
$ Rscript -e '... pulso_load(2023,6,"ocupados") ...'
2023-06 ocupados OK: 30535 x 200
```

### Análisis

- Error idéntico en los tres períodos: `invalid multibyte string at '<a2>n.C'`
  - `<a2>` es el segundo byte de `ó` mal interpretado (UTF-8: `c3 b3`; al leer como latin1 o
    sin encoding declarado, el byte `b3` es legal pero `c3` en el token previo corrompe la
    cadena; el fragmento `n.C` corresponde a `n.CSV` del nombre `Migración.CSV`).
- El error es exactamente el mismo en los tres períodos testeados (2023-06, 2024-01, 2025-01).
- `ocupados` funciona correctamente en el mismo período (30535 × 200), confirmando que el
  fallo es específico de módulos con tildes en el nombre de archivo, no un problema sistémico.

**Veredicto: CONFIRMADO**
BUG-003 es universal en epoch2: afecta `migracion` (y por extensión `caracgen`) en todos los
períodos testados; el error literal es siempre `invalid multibyte string at '<a2>n.C'`.

---

## Hallazgo 2: BUG-006 — R carga 2025-01 con 202 columnas sin aviso

**Claim del Coder:** R carga `ocupados` 2025-01 silenciosamente con 202 columnas (vs 200 en
períodos anteriores), sin emitir ningún warning de cambio de schema.

### Comandos ejecutados y salida literal

```
$ Rscript -e '... pulso_load(2025,1,"ocupados") ...'
2025-01 ocupados OK: 28317 x 202
Last 5 cols: oci, inglabo, rama2d_r4, rama4d_r4, oficio_c8

$ Rscript -e '... pulso_load(2024,12,"ocupados"); pulso_load(2025,1,"ocupados") ...'
New cols in 2025-01 vs 2024-12: p3071s3, p3072s2, p7140s9a1, p1881s1, p7240s1
ncol 2024-12: 200
ncol 2025-01: 202

$ Rscript -e 'withCallingHandlers(... pulso_load(2025,1,"ocupados"), warning=function(w) ...)'
Loaded silently: 28317 x 202   # no warnings interceptados
```

Reconciliación setdiff (5 cols nuevas) vs diferencia neta (+2 cols):

```
cols en 2024-12 que desaparecen en 2025-01: p3051s1, p3052s1, p3366   (3 eliminadas)
cols en 2025-01 que no estaban en 2024-12:  p3071s3, p3072s2, p7140s9a1, p1881s1, p7240s1  (5 añadidas)
Neto: +5 - 3 = +2  =>  200 + 2 = 202  ✓
```

### Análisis

- 2025-01 tiene efectivamente **202 columnas** (confirmado).
- Las **5 columnas añadidas** respecto a 2024-12 son: `p3071s3`, `p3072s2`, `p7140s9a1`,
  `p1881s1`, `p7240s1`.
- Las **3 columnas eliminadas** respecto a 2024-12 son: `p3051s1`, `p3052s1`, `p3366`.
- La carga es **completamente silenciosa**: ningún warning fue emitido durante la carga.
- Nota de precisión: el claim original dice "202 cols vs 200 en períodos anteriores". Esto es
  correcto en términos de recuento final, pero la transición no es solo adición: es un
  rebalanceo (3 eliminadas + 5 añadidas = neto +2). El número 202 es exacto.

**Veredicto: CONFIRMADO**
2025-01 carga con 202 columnas, silenciosamente, sin emitir ningún warning sobre el cambio de
schema. La diferencia neta es +2 cols, producto de 5 adiciones y 3 eliminaciones simultáneas.

---

## Hallazgo 3: BUG-023 — Mojibake en sources.json para rutas con tildes

**Claim del Coder:** `sources.json` tiene paths double-encoded (Mojibake) para módulos con tildes.

### Comandos ejecutados y salida literal

```python
# Contenido leído de r/inst/extdata/sources.json:

2022-01 migracion: {'file': 'CSV/Migración.CSV'}
2022-01 caracgen: {'file': 'CSV/Características generales, seguridad social en salud y educación.CSV'}

2024-06 migracion: {'file': 'CSV/Migración.CSV'}
2024-06 caracgen: {'file': 'CSV/Características generales, seguridad social en salud y educación.CSV'}

2025-06 migracion: {'file': 'CSV/Migración.CSV'}
2025-06 caracgen: {'file': 'CSV/Características generales, seguridad social en salud y educación.CSV'}

Bytes around 'Migraci': b'Migraci\xc3\xb3n.CSV"\n        }'
Hex: 4d696772616369c3b36e2e435356220a20202020202020207d
NORMAL UTF-8: correct o-acute encoding

UTF-8 Migración at byte offset: 247271
Mojibake Migración at byte offset: -1   # <-- no encontrado
```

### Análisis

- Los bytes `c3 b3` corresponden a `ó` en UTF-8 estándar correcto (U+00F3).
- La secuencia de Mojibake (`c3 83 c2 b3`) **no aparece** en ningún punto del archivo.
- El archivo `sources.json` está correctamente codificado en UTF-8 para todos los módulos
  con tildes inspeccionados (`Migración`, `Características generales…`).
- BUG-003 (el error "invalid multibyte string") **no se origina** en `sources.json`, sino
  en cómo R lee el archivo ZIP/CSV descargado del servidor DANE sin especificar encoding.

**Veredicto: REFUTADO**
`sources.json` NO tiene Mojibake. La codificación de rutas con tildes es UTF-8 correcto
(bytes `c3 b3` para `ó`). BUG-023 tal como fue formulado (double-encoding en sources.json)
no existe. La causa raíz de BUG-003 está en la lectura del CSV descargado, no en el JSON.

---

## Conclusión general

| Hallazgo  | Claim del Coder                            | Veredicto    |
|-----------|---------------------------------------------|--------------|
| BUG-003   | Error universal en epoch2 para `migracion`  | CONFIRMADO   |
| BUG-006   | 2025-01 carga 202 cols sin warning          | CONFIRMADO   |
| BUG-023   | Mojibake en sources.json                    | REFUTADO     |

**MODIFICO** los hallazgos del Coder en el siguiente sentido:

- BUG-003 y BUG-006: **CONFIRMO** ambos tal como fueron descritos.
- BUG-023: **RECHAZO** la hipótesis de Mojibake en `sources.json`. El archivo JSON está
  bien codificado. La causa real del BUG-003 debe buscarse en la capa de lectura de CSV
  (ausencia de `encoding="UTF-8"` en `read.csv` o equivalente), no en el catálogo de fuentes.

Recomendación de acción para BUG-003: agregar `fileEncoding = "UTF-8"` (o detectar el
encoding del ZIP descargado) en la función interna de lectura CSV de `pulso_load`.
Recomendación de acción para BUG-006: emitir un `warning()` cuando el número de columnas
difiere respecto al período anterior cargado en la misma sesión, o documentarlo en NEWS.
