# pulso — Arquitectura del sistema

> Este documento es la referencia arquitectónica principal del repositorio `pulso`.  
> Cubre las tres shapes de CSV, el flujo completo del pipeline, organización del código,  
> capa de datos, modelo de construcción multi-agente, estrategia de tests y problemas conocidos.  
>
> **English version:** [`docs/architecture.md`](architecture.md)  
> **Decisiones relacionadas:** [`docs/decisions/`](decisions/)

---

## 1. Descripción general

`pulso` da acceso Python directo a la **Gran Encuesta Integrada de Hogares (GEIH)** — la encuesta mensual de hogares del mercado laboral colombiano publicada por el DANE.

```
Solicitud del usuario: load(year=2024, month=6, module="ocupados")
        │
        ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  API pública de pulso  (pulso/_core/loader.py)                   │
  │                                                                   │
  │  descarga → parseo → (merge) → armonización → pd.DataFrame       │
  └──────────────────────────────────────────────────────────────────┘
        │          │           │            │
        ▼          ▼           ▼            ▼
   ZIP DANE    parser       claves       variable_map
  (cacheado)  por shape     época         .json
```

**Contrato público:**
- Entrada: año, mes, nombre de módulo (string), área (cabecera/resto/total)
- Salida: `pd.DataFrame` con códigos de columna DANE crudos o variables canónicas armonizadas
- Efectos secundarios: ZIP cacheado localmente; llamadas posteriores usan el caché

**Qué NO hace `pulso`:**
- Inferencia estadística (sin errores estándar que respeten el diseño muestral)
- Imputación o relleno de datos faltantes
- Productos oficiales del DANE — es un wrapper de conveniencia, no una herramienta oficial

---

## 2. Las tres shapes de CSV

El hecho estructural más importante de `pulso` es que maneja tres layouts de CSV distintos producidos por el DANE en distintas series y años. Cada shape requiere lógica de parseo diferente.

```
Shape A  (GEIH-1, 2006–2021)    Shape B  (GEIH-2, 2022–presente)   Shape C  (Empalme, 2010–2019)
──────────────────────────────  ────────────────────────────────────  ────────────────────────────
zip_anual/                      zip_anual/                            empalme_YYYY.zip/
  Cabecera - Ocupados.csv   →     CSV/                                  1. Enero.zip/
  Resto    - Ocupados.csv           Ocupados.CSV                            1. Enero/CSV/
  Cabecera - Caract.csv              Características...CSV                      Ocupados.CSV
  Resto    - Caract.csv              No ocupados.CSV                             Caract. gen..CSV
  ...                                ...                                       ...
(split cabecera/resto)          (archivo único nacional,             (anidado: anual→mensual→módulo;
                                 columna CLASE para filtrar área)     estructura Shape C en sub-ZIPs)
```

### Shape A — GEIH-1 (2006-01 → 2021-12)

| Atributo | Valor |
|----------|-------|
| **Detección** | `is_shape_a(zip_path)`: algún archivo contiene `"Cabecera"` en su nombre |
| **Estructura** | Dos archivos por módulo: `Cabecera - {módulo}.csv` (urbano) y `Resto - {módulo}.csv` (rural) |
| **Codificación** | `latin-1` |
| **Separador** | `;` (sin auto-detección para Shape A) |
| **Decimal** | `,` |
| **División área** | Separación física de archivos (no necesita columna `CLASE`) |
| **Mayúsculas/minúsculas** | Mixto — varía por año y módulo (ej. `Hogar`, `Directorio`, `Fex_c_2011`) |
| **Normalización de columnas** | ⚠️ **INCOMPLETA** — solo se ponen en mayúsculas las claves de merge; columnas no clave pueden quedar en minúsculas. Bug conocido: issue [#42](https://github.com/Stebandido77/pulso/issues/42). Corrección en Phase 4 Línea A. |
| **Columna de peso** | `fex_c_2011` (minúsculas, con sufijo de año) → pasará a `FEX_C` tras la corrección de Línea A |
| **Punto de entrada del parser** | `parse_shape_a_module()` en [`pulso/_core/parser.py`](../pulso/_core/parser.py) |

El matching de archivos de módulos usa regex de límite de palabra contra el mapa `MODULE_KEYWORDS_GEIH1`, que maneja errores tipográficos en nombres de archivo del DANE (ej. `"Caractericas"` por `"Características"` en 2007).

### Shape B — GEIH-2 (2022-01 → presente)

| Atributo | Valor |
|----------|-------|
| **Detección** | `is_shape_a()` retorna `False` (no hay archivos con `"Cabecera"`) |
| **Estructura** | Un CSV nacional único por módulo dentro de una carpeta `CSV/` |
| **Codificación** | `latin-1` |
| **Separador** | `;` declarado en la época; auto-detección de respaldo (algunos meses traen `,`) |
| **Decimal** | `,` |
| **División área** | A nivel de fila mediante columna `CLASE` (1 = cabecera, 2/3 = resto) |
| **Mayúsculas/minúsculas** | Mayúsculas nativas del DANE |
| **Normalización de columnas** | ✅ Stripping de BOM + mayúsculas en claves de merge via `_read_csv_with_fallback()` |
| **Columna de peso** | `FEX_C18` (mayúsculas, sin sufijo de año) |
| **Punto de entrada del parser** | `_parse_csv()` en [`pulso/_core/parser.py`](../pulso/_core/parser.py) |

El fallback de auto-detección de separador (`sep=None, engine="python"`) se activa cuando `_read_csv_with_fallback()` lee un DataFrame de una sola columna, señal de separador incorrecto. Fue necesario para la entrada 2022-01 (ver PR [#36](https://github.com/Stebandido77/pulso/pull/36)).

### Shape C — Empalme (2010-2019)

| Atributo | Valor |
|----------|-------|
| **Detección** | Se invoca explícitamente via `load_empalme()` o `apply_smoothing=True`; no se auto-detecta |
| **Estructura** | ZIP anual → 12 sub-ZIPs mensuales → `<NN>. <Mes>/CSV/<NombreMódulo>.CSV` |
| **Codificación** | `latin-1` |
| **Separador** | `;` con auto-detección de respaldo (heredado de `_read_csv_with_fallback`) |
| **Decimal** | `,` |
| **División área** | Archivo unificado; columna `CLASE` si está presente |
| **Mayúsculas/minúsculas** | Mixto — el DANE entrega `Hogar`, `Fex_c_2011`, etc. |
| **Normalización de columnas** | ✅ Mayúsculas completas + `FEX_C_XXXX → FEX_C` via `_normalize_empalme_columns()` |
| **Columna de peso** | `FEX_C` (tras normalización) |
| **Punto de entrada del parser** | `_parse_empalme_module()` en [`pulso/_core/empalme.py`](../pulso/_core/empalme.py) |

El naming de los sub-ZIPs usa nombres de meses en español (`Enero`, `Febrero`, …, `Diciembre`). La función `_detect_month_from_name()` extrae el número de mes del nombre del sub-ZIP.

**Anomalías documentadas en el registry:**
- **2013:** el ZIP exterior tiene un error tipográfico del DANE `GEIH_Emplame_2013.zip` (falta una `p`); se preserva tal cual.
- **2020:** ZIP no publicado por el DANE; `download_empalme_zip(2020)` lanza `DataNotAvailableError`.
- **IDNO 2020:** truncado a `DANE-DIMPE-GEIH-EMPAL-2020` (le falta el sufijo `ME`).

---

## 3. Flujo del pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                       load() / load_merged()                         │
│                     pulso/_core/loader.py                            │
└─────────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│  1. CONSULTA AL REGISTRO           │   pulso/_config/registry.py
│  sources.json → registro (año,mes) │   Lanza DataNotAvailableError si falta
│  epoch_for_month() → Epoch         │   pulso/_config/epochs.py
└────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│  2. DESCARGA                       │   pulso/_core/downloader.py
│  download_zip(year, month) → Path  │   Caché: <raíz>/raw/{year}/{month}/{sha[:16]}.zip
│  Verificación de checksum SHA-256  │   DownloadError si no coincide
└────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│  3. PARSEO (según shape)           │   pulso/_core/parser.py  O  pulso/_core/empalme.py
│  parse_module(zip_path, ...) →     │
│    Shape A: parse_shape_a_module() │   Cabecera + Resto concatenados; CLASE sintético
│    Shape B: _parse_csv()           │   CSV único; BOM strip + auto-detección sep
│    Shape C: _parse_empalme_module()│   Sub-ZIP extraído a temp; normalización completa
│  → pd.DataFrame crudo              │
└────────────────────────────────────┘
    │
    ▼  (solo en load_merged / apply_smoothing)
┌────────────────────────────────────┐
│  4. MERGE (persona + hogar)        │   pulso/_core/merger.py
│  merge_modules(module_dfs, epoch)  │   Auto-detecta nivel persona/hogar por módulo
│  → pd.DataFrame fusionado          │   MergeError si faltan claves (ver issue #42)
└────────────────────────────────────┘
    │
    ▼  (cuando harmonize=True)
┌────────────────────────────────────┐
│  5. ARMONIZACIÓN                   │   pulso/_core/harmonizer.py
│  harmonize_dataframe(df, epoch)    │   Lee variable_map.json
│  → columnas canónicas añadidas     │   keep_raw=True: columnas crudas se preservan
│    (sexo, edad, condicion_activ…)  │   Errores se omiten con logger.warning
└────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────┐
│  6. RETORNO pd.DataFrame           │
│  Columnas DANE crudas + canónicas  │   Usuario llama expand() por separado si requiere
└────────────────────────────────────┘
```

### Detalles de cada paso

**Paso 1 — Consulta al registro**  
`_load_sources()` lee `pulso/data/sources.json` (230 entradas; cacheado en memoria tras la primera carga). `epoch_for_month(year, month)` itera los dos registros de época y retorna el dataclass `Epoch` correspondiente. Lanza `ConfigError` si ninguna época cubre la fecha (es decir, antes de 2006-01).

**Paso 2 — Descarga**  
`download_zip()` verifica primero el caché local. El slot de caché es `<raíz>/raw/{year}/{month:02d}/{sha256[:16]}.zip`. Si el archivo existe y el checksum coincide, se retorna de inmediato. Si el campo checksum en `sources.json` es `null` (la mayoría de entradas GEIH-1), el archivo se retorna sin verificación una vez descargado. Un patrón de archivo `.tmp` evita que descargas parciales contaminen el caché.

**Paso 3 — Parseo**  
`parse_module()` despacha primero via `is_shape_a(zip_path)`. Si es `True`, corre la lógica Shape A independientemente del campo `epoch.area_filter`. Si es `False`, lee el registro de `sources.json` para las rutas de archivos y despacha a Shape B (`_parse_csv`). Shape C se invoca por separado via `empalme.py` y nunca pasa por `parse_module()`.

**Paso 4 — Merge**  
`merge_modules()` auto-detecta el nivel de cada módulo (persona vs hogar) verificando qué claves de merge están presentes. Los módulos de nivel persona se fusionan en `(DIRECTORIO, SECUENCIA_P, ORDEN)`; los de nivel hogar en `(DIRECTORIO, SECUENCIA_P, HOGAR)`, luego se hace un left-join al resultado de persona. El default `how="outer"` asegura que las personas aparezcan aunque no estén en algún módulo.

**Paso 5 — Armonización**  
`harmonize_dataframe()` itera las variables de `variable_map.json`, resuelve las columnas fuente para la época actual, aplica el transform declarado y añade el resultado como nueva columna. Las variables con columnas fuente faltantes emiten `logger.warning()` y se omiten — **no lanzan excepción**. Con `keep_raw=True` (defecto), las columnas DANE originales se preservan junto a las canónicas.

---

## 4. Organización del código — `pulso/_core/`

```
pulso/_core/
├── downloader.py       # Descarga, caché, checksums
├── parser.py           # Parseo Shape A + Shape B
├── empalme.py          # Shape C (Empalme) exclusivamente
├── harmonizer.py       # Transforms de variable_map
├── merger.py           # Merge multi-módulo
├── loader.py           # Orquestador de API pública
└── expander.py         # Helper expand()
```

### `downloader.py`

Responsable de: obtener ZIPs del DANE, cachear en disco, verificar SHA-256.

Funciones clave:
- `download_zip(year, month, cache, show_progress, allow_unvalidated)` — punto de entrada principal
- `verify_checksum(path, expected_sha256)` — comparación SHA-256 en streaming

Nota: el downloader deliberadamente **no** parsea — retorna un `Path` al ZIP local y nada más. Esta separación permite probar el parser con ZIPs pre-cacheados sin acceso a red.

### `parser.py`

Responsable de: parseo de Shape A y Shape B. Shape C **no está aquí** (ver `empalme.py`).

Funciones clave:
- `is_shape_a(zip_path)` — detecta Shape A verificando si hay `"Cabecera"` en el namelist
- `find_shape_a_files(zip_path, module)` — matching por keyword+regex para archivos Cabecera/Resto
- `parse_shape_a_module(zip_path, module, epoch)` — lee ambas mitades, las concatena, añade `CLASE` sintético
- `_read_csv_with_fallback(raw_bytes, epoch)` — auto-detección de separador + BOM strip + mayúsculas en claves
- `_resolve_zip_path(zf, path)` — tolera rutas con mojibake y prefijos de subcarpeta faltantes
- `_parse_csv(zip_path, inner_path, epoch, columns)` — lector de archivo único Shape B
- `parse_module(zip_path, year, month, module, area, epoch, columns)` — dispatcher de nivel superior

El diccionario `MODULE_KEYWORDS_GEIH1` mapea nombres canónicos de módulos a listas de palabras clave en español para identificar archivos dentro de ZIPs Shape A. Múltiples keywords por módulo manejan los errores tipográficos de nombres del DANE.

### `empalme.py`

Responsable de: Shape C (Empalme) exclusivamente. Separado porque:
1. El anidamiento anual→mensual→sub-ZIP es estructuralmente distinto de Shapes A/B.
2. La serie Empalme tiene un registry propio (`empalme_sources.json`) y layout de caché distinto.
3. La normalización de columnas para Shape C es actualmente más completa que para Shape A (tras el fix de Phase 4 Línea A, esta divergencia se resolverá con un helper compartido).

Funciones clave:
- `_load_empalme_registry()` / `_get_empalme_entry(year)` — acceso al registry con validación
- `download_empalme_zip(year, show_progress)` — caché en `<raíz>/empalme/{year}.zip`
- `_find_empalme_module_csv(zf, module)` — keyword match dentro de un sub-ZIP
- `_parse_empalme_module(inner_zip_path, module)` — lee un CSV de módulo + aplica `_normalize_empalme_columns()`
- `_normalize_empalme_columns(df)` — mayúsculas en todas las columnas + `FEX_C_XXXX → FEX_C`
- `_load_empalme_month_merged(year, month, area, harmonize, variables)` — carga de un mes para `apply_smoothing`
- `load_empalme(year, module, area, harmonize)` — API pública, 12 meses apilados

### `harmonizer.py`

Responsable de: aplicar los transforms de `variable_map.json` a un DataFrame crudo.

Funciones clave:
- `harmonize_dataframe(df, epoch, variables, keep_raw)` — punto de entrada; itera variables y añade columnas canónicas
- `harmonize_variable(df, canonical_name, entry, epoch)` — aplica el transform de una variable
- `_apply_recode()`, `_apply_compute()`, `_apply_cast()`, `_apply_coalesce()` — primitivas de transform

Invariante de diseño: `harmonize_dataframe()` nunca lanza excepción ante columnas fuente faltantes — registra un warning y omite. Esto permite armonización parcial cuando no todos los módulos están cargados.

### `merger.py`

Responsable de: fusionar múltiples DataFrames de módulos usando las claves apropiadas de la época.

Funciones clave:
- `merge_modules(module_dfs, epoch, level, how)` — merge de nivel superior
- `_detect_module_level(df, epoch)` — detección persona vs hogar por presencia de claves
- `_merge_within_level(dfs_dict, keys, how)` — left-join repetido dentro de un nivel

El merger elimina columnas no-clave compartidas de los DataFrames posteriores para evitar sufijos `_x`/`_y`. Las columnas identificadoras compartidas (`CLASE`, `DPTO`, variables de peso, `MES`, `HOGAR`) aparecen exactamente una vez.

### `loader.py`

Responsable de: la API pública. Orquesta los pasos del pipeline.

Funciones clave:
- `load(year, month, module, area, harmonize, columns, cache, show_progress, allow_unvalidated)` — módulo único
- `load_merged(year, month, modules, area, harmonize, variables, cache, show_progress, allow_unvalidated, apply_smoothing)` — merge multi-módulo con swap Empalme opcional
- `_required_modules_for_variables(variable_map, sources, epoch_key, requested_variables)` — expande automáticamente la lista de módulos cuando `harmonize=True` y el usuario especificó `variables=`

El parámetro `apply_smoothing` activa `_load_empalme_month_merged()` para años 2010–2019. El año 2020 emite `UserWarning` y retrocede al GEIH crudo.

---

## 5. Capa de datos — `pulso/data/`

Este directorio es **territorio del Curator**. El Builder no debe modificar archivos aquí; el Curator no debe modificar `pulso/_core/`. CI hace cumplir esto via convenciones de path de branches.

```
pulso/data/
├── sources.json              # 230 entradas mensuales GEIH (2006-01 → 2026-02)
├── empalme_sources.json      # 11 entradas anuales Empalme (2010–2020)
├── epochs.json               # 2 definiciones de épocas
├── variable_map.json         # 30 mapeos de variables canónicas
└── schemas/
    ├── sources.schema.json
    ├── empalme_sources.schema.json
    ├── epochs.schema.json
    └── variable_map.schema.json
```

### `sources.json`

230 entradas con clave `"YYYY-MM"`. Cada entrada contiene:
- `epoch`: `"geih_2006_2020"` o `"geih_2021_present"`
- `download_url`: URL directa del ZIP del DANE
- `checksum_sha256`: hex SHA-256 (5 entradas validadas completas; el resto `null`)
- `modules`: rutas de archivos dentro del ZIP por módulo canónico
- `validated`: `true/false`

El schema en `sources.schema.json` hace cumplir dos shapes polimórficas de `ModuleFiles`:
- `ModuleFilesSplit`: `{cabecera, resto}` (Shape A)
- `ModuleFilesUnified`: `{file, row_filter?}` (Shape B)

### `empalme_sources.json`

11 entradas con clave de 4 dígitos (`"2010"` … `"2020"`). Cada entrada descargable tiene:
- `catalog_id`, `idno`: identificadores del catálogo NADA del DANE
- `download_url`, `zip_filename`, `size_bytes`, `checksum_sha256`
- `downloadable`: `false` para 2020 (ZIP no publicado)

Todas las 10 entradas descargables (2010–2019) tienen checksums SHA-256 verificados al 2026-05-02.

### `epochs.json`

Dos registros de época:

| Clave | Rango de fechas | Etiqueta |
|-------|----------------|---------|
| `geih_2006_2020` | 2006-01 → 2021-12 | GEIH marco muestral 2005 |
| `geih_2021_present` | **2022-01** → presente | GEIH rediseñada (post-OIT, marco 2018) |

> ⚠️ El cambio de época está en **2022-01**, no en 2021. Esta es una fuente frecuente de confusión en la documentación.

### `variable_map.json`

30 variables canónicas mapeadas a través de ambas épocas. Cada entrada:
- `type`: `numeric`, `categorical`, `string` o `boolean`
- `level`: `persona` o `hogar`
- `module`: nombre del módulo fuente
- `mappings`: por época — `{source_variable, transform, source_doc, notes?}`

Tipos de transform: `identity`, `recode`, `compute` (expresión pandas eval), `cast`, `coalesce`.

---

## 6. Modelo de construcción multi-agente

`pulso` usa un modelo de tres roles donde cada uno tiene permisos distintos:

```
Architect      →   Diseño, ADRs, docs de arquitectura, RFCs de roadmap
Builder        →   pulso/_core/, pulso/__init__.py, tests/
Curator        →   pulso/data/, tests/
```

CI hace cumplir las convenciones de path de branches:

| Prefijo de branch | Puede tocar |
|------------------|------------|
| `feat/code-*` | `pulso/_core/`, `pulso/__init__.py`, `tests/` |
| `feat/data-*` | `pulso/data/`, `tests/` |
| `docs/*`      | `docs/`, `README.md` |
| `fix/code-*`  | Igual que `feat/code-*` |

Las violaciones hacen fallar el CI. Esto previene cambios accidentales entre capas y mantiene una traza de auditoría limpia de quién cambió qué.

**Por qué importa esto:** `sources.json` y `variable_map.json` contienen metadatos de calidad investigativa que el Curator debe validar antes de que el Builder pueda depender de ellos. Separar los branches asegura que estos archivos se revisen de forma independiente.

---

## 7. Decisiones arquitectónicas activas

Ver [`docs/decisions/`](decisions/) para los registros completos de ADR.

| ADR | Título | Estado |
|-----|--------|--------|
| [0001](decisions/0001-build-plan.md) | Plan de construcción y estructura de fases | Activo |
| [0002](decisions/0002-scope-2006-present.md) | Alcance GEIH (solo 2006-presente, sin ECH) | Activo |
| [0003](decisions/0003-schema-1.1-area-filtering.md) | Schema v1.1 ModuleFiles polimórfico | Activo |
| [0004](decisions/0004-harmonizer-design.md) | Diseño del harmonizer (keep_raw=True por defecto) | Activo |
| [0005](decisions/0005-phase4-roadmap.md) | Roadmap Phase 4 (C→A→v1.0→B→v1.1) | Activo |

Invariantes activos clave:
- **Cambio de época = 2022-01.** Verificado empíricamente via `epoch_for_month()`.
- **`apply_smoothing` degrada graciosamente para año 2020.** Emite `UserWarning`, retrocede al GEIH crudo.
- **`harmonize_dataframe` nunca lanza ante columnas faltantes.** Omite con `logger.warning`.
- **El caché es de solo-adición.** Los ZIPs descargados nunca se sobreescriben salvo que el checksum falle; las descargas parciales usan sufijo `.tmp`.

---

## 8. Estrategia de tests

```
                    ┌─────────────────────────────────────────┐
                    │            Suite de tests CI             │
                    │                                          │
                    │  Integración (275 tests)                 │
                    │    @pytest.mark.integration              │
                    │    Requiere flag --run-integration       │
                    │    ZIPs reales del DANE desde red        │
                    │    5 meses estratégicos validados        │
                    │                                          │
                    │  Unitarios (179 tests)                   │
                    │    Rápidos, sin red                      │
                    │    Fixtures sintéticos de ZIP            │
                    │    Siempre corren en CI                  │
                    └─────────────────────────────────────────┘
```

### Tests unitarios (179, siempre corren)

Ubicación: `tests/unit/`

- ZIPs fixture en `tests/fixtures/zips/` construidos por `tests/_build_fixtures.py`
- `geih2_sample.zip` — fixture Shape A (Cabecera + Resto)
- `geih2_unified_sample.zip` — fixture Shape B (archivo unificado)
- Inyección de registry via `monkeypatch.setattr(reg, "_SOURCES", ...)` para evitar cargar `sources.json`

### Tests de integración (275, requieren `--run-integration`)

Ubicación: `tests/integration/`

**5 meses estratégicos** validados con ZIPs reales del DANE:

| Mes | Época | Shape | Por qué se eligió |
|-----|-------|-------|-------------------|
| 2007-12 | geih_2006_2020 | A | Entrada GEIH-1 más temprana estable; BOM en encabezados CSV |
| 2015-06 | geih_2006_2020 | A | Bug de columnas mixtas (issue #42) confirmado aquí |
| 2021-12 | geih_2006_2020 | A | Último mes antes del cambio de época |
| 2022-01 | geih_2021_present | B | Primer mes de nueva época; anomalía de separador coma |
| 2024-06 | geih_2021_present | B | Más reciente validado manualmente; ancla de regresión Phase 2 |

**Test de regresión Phase 2:** `load_merged(year=2024, month=6, harmonize=True).shape == (70020, 525)` — este valor exacto está bloqueado y no debe cambiar.

### Tests de integración del Empalme

`tests/integration/test_smoothing.py`:
- `test_smoothing_2015_06_real` — `apply_smoothing=True` para 2015-06 produce columnas normalizadas (FEX_C, HOGAR en mayúsculas) y conteo de filas plausible
- `test_load_empalme_2015_real` — `load_empalme(2015)` retorna 12 meses apilados con FEX_C no nulo

---

## 9. Problemas conocidos

### Issue #42 — Parser Shape A: columnas en minúsculas (severidad ALTA)

**Estado:** Abierto. Previsto para Phase 4 Línea A.

**Síntoma:** `load_merged(year, month)` para algunos meses GEIH-1 lanza `MergeError: Module is missing merge keys`. Confirmado para 2015-06 módulo `vivienda_hogares`.

**Causa raíz:** El DANE entrega columnas como `Hogar`, `Area`, `Fex_c_2011` (mayúsculas y minúsculas mixtas) en algunos CSVs Shape A. La búsqueda sensible a mayúsculas del merger para `HOGAR` falla.

**Solución temporal:** Ninguna para el path crudo. El path Empalme (`apply_smoothing=True`) normaliza columnas correctamente via `_normalize_empalme_columns()`.

**Corrección planificada:** Phase 4 Línea A — extraer un helper compartido `_normalize_dane_columns()` en `parser.py`, aplicarlo en `parse_shape_a_module()`. Actualizar `variable_map.json` para usar `FEX_C` en vez de `fex_c_2011` (PRs coordinados Builder + Curator). Ver [ADR 0005](decisions/0005-phase4-roadmap.md).

---

## 10. Glosario

| Término | Definición |
|---------|-----------|
| **GEIH** | Gran Encuesta Integrada de Hogares. Encuesta mensual oficial del mercado laboral de Colombia, publicada por el DANE desde 2007 (marco muestral rediseñado en 2022). |
| **ECH** | Encuesta Continua de Hogares. Encuesta predecesora del DANE (2000–2005). No soportada por `pulso` por metodología incompatible. |
| **GEIH-1** | Nombre informal para la GEIH bajo el marco muestral del Censo 2005 (2006-01 → 2021-12 en el modelo de épocas de `pulso`). |
| **GEIH-2** | Nombre informal para la GEIH bajo el marco muestral del Censo 2018, rediseñada post-OIT (2022-01 → presente). |
| **Empalme** | Serie GEIH Empalme publicada anualmente por el DANE (2010–2019) que re-estima los microdatos mensuales bajo el marco unificado del Censo 2005. Permite análisis de series de tiempo consistentes a través del rediseño de 2022. |
| **Factor de expansión** | Peso muestral. Cada encuestado representa un conteo poblacional. `fex_c_2011` (GEIH-1) / `FEX_C18` (GEIH-2) / `FEX_C` (Empalme, normalizado). |
| **Época** | Período durante el cual la metodología del DANE es internamente consistente. `pulso` define dos épocas; su límite es 2022-01. |
| **Módulo** | Un archivo CSV temático dentro de un ZIP mensual GEIH. Ejemplos: `ocupados`, `caracteristicas_generales`. Cada módulo tiene un nivel de análisis (persona u hogar). |
| **Nivel persona** | Microdatos a nivel del encuestado individual. Claves de merge: `DIRECTORIO`, `SECUENCIA_P`, `ORDEN`. |
| **Nivel hogar** | Microdatos a nivel del hogar. Claves de merge: `DIRECTORIO`, `SECUENCIA_P`, `HOGAR`. |
| **Shape A / B / C** | Nombres internos de `pulso` para los tres layouts estructurales de CSV producidos por el DANE (ver Sección 2). |
| **Variable canónica** | Nombre de variable armonizada en `variable_map.json` (ej. `sexo`, `peso_expansion`) consistente entre épocas, en contraposición al código DANE crudo (`P6020`, `FEX_C18`). |
| **Builder** | Rol en el modelo de construcción multi-agente responsable de `pulso/_core/`. |
| **Curator** | Rol responsable de `pulso/data/` — archivos de registry, schemas, mapa de variables. |
| **Architect** | Rol responsable de ADRs, RFCs y decisiones de diseño transversales. |
