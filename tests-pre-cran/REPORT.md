# pulso — Pre-CRAN Smoke Test Report

**Fecha:** 2026-05-23  
**Branch:** `testing/pre-cran-validation`  
**Metodología:** Coder (ejecución) → Curator (auditoría de honestidad) → Tester (re-verificación independiente)  
**Entorno:** Python 3.12.9 / pulso-co **1.0.0rc1** · R 4.5.2 / pulso R **0.1.0** · Windows 11

---

## Veredicto: NOT CRAN-READY

El paquete R `pulso 0.1.0` tiene **5 CRAN-blockers** que impiden la submisión. El paquete Python `pulso-co` tiene un bug de alta severidad en rc1 que ya está corregido en el source para v1.0.0.

---

## Cobertura del test

- **17 períodos** testeados (8 epoch1 / 9 epoch2)
- **Hasta 8 módulos** por período (según disponibilidad en sources.json)
- **Comparación Python vs R** para cada módulo de cada período
- **Cache pre-existente:** 54 archivos / ~2 GB — los bugs son de parseo, no de descarga
- **Verificación independiente:** Curator leyó el código fuente; Tester re-ejecutó 3 hallazgos críticos

---

## Bugs — Tabla completa

| ID | Sev | Comp | Descripción | CRAN-Blocker | Verificado |
|----|-----|------|-------------|:---:|:---:|
| BUG-004 | **Critical** | R | `rbind()` sin fill — todos los módulos epoch1 fallan | ✅ | Tester ✓ |
| BUG-003 | **High** | R | "invalid multibyte string" con filenames UTF-8 en Windows | ✅ | Tester ✓ |
| BUG-005 | **High** | R | 2022-01: 5/8 módulos retornan 1 columna (sep erróneo) | ✅ | Curator ✓ |
| BUG-006 | **High** | R | Sin validation guard — R carga datos no-validados sin aviso | ✅ | Curator ✓ |
| BUG-011 | **High** | R | Vignette no pre-construida — `R CMD check --as-cran` produce 2 WARNINGs | ✅ | Curator (nuevo) |
| BUG-008 | **Medium** | R | `harmonize=TRUE` incompleto — solo lowercase, cero columnas canónicas | ✅ (docs) | Tester ✓ |
| BUG-001 | **High** | Py | `allow_unvalidated=True` → `TypeError` en `downloader.py:84` (rc1) | N/A PyPI | Curator (corregido en source) |
| BUG-SEGFAULT | **?** | R | Segfault al llamar `pulso_load()` dos veces en la misma sesión R | ❓ | Tester (nuevo) |
| BUG-002 | Medium | Py | 32+ líneas "Skipping variable" a stdout por cada `load()` | ✗ | Coder |
| BUG-007 | Medium | Both | `TypeError` enmascara el error de nested-zip en Python | ✗ | Coder |
| BUG-009 | Low | Py | `list_variables()` / `describe_variable()` levantan "Phase 2" | ✗ | Coder |
| BUG-010 | Low | Both | Estructura ZIP cambió en períodos ≥ 2025-06 (file not found) | ✗ | Coder |

---

## Los 5 CRAN-blockers del paquete R

### BUG-004 — R: epoch1 completamente inutilizable

**Severidad:** Critical  
**Scope:** **14 años de datos** (2007–2021, `geih_2006_2020` completo)

**Error verificado (Tester, 3 períodos × 3 módulos):**
```
Error in rbind(deparse.level, ...) :
  numbers of columns of arguments do not match
Calls: pulso_load -> .parse_module_csv -> rbind -> rbind
```

**Causa raíz:** `R/R/utils-parse.R:247` hace `rbind(df_c, df_r)` para combinar los archivos Cabecera y Resto de epoch1. Los CSVs del DANE para distintas áreas geográficas tienen diferente número de columnas. `rbind()` sin `fill=TRUE` rechaza combinar DataFrames con columnas no coincidentes.

**Fix:** Reemplazar `rbind(df_c, df_r)` con `dplyr::bind_rows(df_c, df_r)` o `data.table::rbindlist(list(df_c, df_r), fill=TRUE)`.

**Matiz (Tester):** El Coder dice "6 módulos" — en epoch1 hay 3 módulos disponibles (los otros 3 retornan "not available", que es comportamiento correcto). El bug afecta los 3 que existen.

---

### BUG-003 — R: filenames UTF-8 dentro del ZIP crashean en Windows

**Severidad:** High  
**Scope:** `caracteristicas_generales` y `migracion` en **todos los períodos epoch2** testeados

**Error verificado (Tester, 5 combinaciones):**
```
invalid multibyte string at '<a1>sti'   # Características
invalid multibyte string at '<a2>n.C'   # Migración
```

**Causa raíz (Curator + Tester):** El código en `R/R/utils-parse.R:220` llama `utils::unzip(zip_path, list=TRUE)$Name` para obtener la lista de archivos dentro del ZIP. Los archivos del DANE tienen nombres con tildes (`Características generales...`, `Migración.CSV`). En Windows, R no puede procesar esos bytes como UTF-8 al listar el contenido. El ZIP se descarga correctamente — el crash es al parsear el directorio interno.

**Nota:** El Coder atribuía el crash a la extracción (`utils::unzip` con `files=`); la ubicación exacta es en el listado (`:list=TRUE`). El bug es el mismo, la línea de código es diferente.

**Fix:** Usar `zip::unzip(zip_path, list=TRUE)` del paquete `zip` que tiene soporte Unicode en Windows, o convertir los bytes del vector `$Name` de Latin-1 a UTF-8 antes de procesarlos.

---

### BUG-005 — R: 2022-01 retorna 1 columna en 5/8 módulos

**Severidad:** High  
**Scope:** `ocupados`, `desocupados`, `inactivos`, `otros_ingresos`, `otras_formas_trabajo` en 2022-01 (primer período epoch2 validado, 76 MB)

**Evidencia:**
```r
pulso_load(2022, 1, "ocupados")       # → [31819 × 1] (esperado: × ~212)
pulso_load(2022, 1, "vivienda_hogares") # → [26098 × 48] (FUNCIONA)
```

**Causa raíz (Curator):** `R/R/utils-parse.R:104-110` hardcodea `sep=";"` en `utils::read.csv()`. Los CSVs de algunos módulos de 2022-01 usan un separador diferente (tab u otro), por lo que toda la línea del header se lee como una sola cadena que se convierte en el nombre de la única columna del DataFrame.

**Fix:** Usar `readr::read_delim(delim=NULL)` o `data.table::fread()` con auto-detección de separador.

---

### BUG-006 — R: sin validation guard en `pulso_load()`

**Severidad:** High (data integrity)  
**Scope:** Todos los períodos `validated=false` (225 de 230 períodos en sources.json)

**Evidencia:**
```r
pulso_load(2026, 1, "ocupados")  # Descarga 70 MB y retorna [28359 × 208] — SIN AVISO
pulso_load(2026, 2, "ocupados")  # Ídem — SIN AVISO
```

Python lanza `DataNotValidatedError` correctamente. R no verifica el campo `validated` en ningún punto de `load.R` o `utils-source.R`.

**Nota (Curator):** Un usuario CRAN típico que llame `pulso_load(2026, 1, "ocupados")` recibirá datos de encuesta no validados sin ningún aviso. Dado que el paquete promete "tidy interface to download, parse, and harmonize labor market surveys", esto es un problema de integridad de datos, no solo de paridad de API.

**Fix:** Agregar en `pulso_load()`: si `validated == FALSE`, lanzar `pulso_validation_error` a menos que el usuario pase `allow_unvalidated = TRUE`.

---

### BUG-011 — R: vignette no pre-construida (R CMD check --as-cran → 2 WARNINGs)

**Severidad:** High (CRAN-blocker buildtime)  
**Fuente:** Curator — encontrado en `pulso.Rcheck/00check.log` (artefacto existente en el repo)

**Output de `R CMD check --as-cran`:**
```
Status: 2 WARNINGs, 2 NOTEs

WARNING: Files in the 'vignettes' directory but no files in 'inst/doc'
WARNING: Directory 'inst/doc' does not exist. Package vignette without
         corresponding single PDF/HTML
```

CRAN requiere que las vignettes estén pre-construidas en `inst/doc/` dentro del tarball. El tarball actual no las incluye.

**Fix:** Antes de `R CMD build`, ejecutar `devtools::build_vignettes()` o incluir el HTML pre-renderizado en `r/inst/doc/pulso.html`. Alternativamente, configurar `VignetteBuilder` correctamente en DESCRIPTION y asegurarse de que `pandoc` esté disponible en el entorno de build.

---

## Bugs de Python (rc1 / PyPI)

### BUG-001 — Python: TypeError en `allow_unvalidated=True` (rc1)

**Severidad:** High — pero **ya está corregido en el source para v1.0.0**

**Error en rc1:**
```python
TypeError: 'NoneType' object is not subscriptable
  File "pulso/_core/downloader.py", line 84
    short = checksum[:16]  # checksum es null para períodos no-validados
```

**Estado (Curator):** El source en `python/pulso/_core/downloader.py:100` ya tiene la corrección:
```python
short = checksum[:16] if checksum is not None else f"unvalidated_{year}-{month:02d}"
```

El paquete instalado vía PyPI (`pulso-co 1.0.0rc1`) tiene el bug; el source del repo ya no lo tiene. El próximo release (`v1.0.0 final`) no tendrá este bug.

---

## Bug adicional — SEGFAULT en R (requiere investigación)

**Severidad:** Desconocida — potencialmente alta  
**Fuente:** Tester (encontrado durante verificación de BUG-008)

Llamar `pulso_load()` **dos veces en la misma sesión R** produce un segmentation fault (exit code 139) en R 4.5.2 / Windows.

El Tester lo descubrió al intentar comparar `harmonize=TRUE` vs `FALSE` en un solo script. No fue posible reproducirlo de forma aislada en el tiempo disponible. Requiere investigación antes de CRAN submission.

---

## Correcciones al reporte del Coder (Curator + Tester)

| Item | Reporte Coder | Corrección |
|------|--------------|------------|
| BUG-001 | "bug en downloader.py:84" | Bug en rc1; ya corregido en source para v1.0.0 |
| BUG-004 scope | "ALL 6 modules fallan" | Epoch1 tiene 3 módulos disponibles, los 3 fallan |
| BUG-003 ubicación | Crash en extracción | Crash al listar contenido (`:list=TRUE`), no en extracción |
| BUG-008 descripción | "silently ignored" | "incompletely implemented" — R aplica lowercase/sanitize pero no deriva columnas canónicas |
| JSON vs md | JSON lista 3 CRAN-blockers | Markdown correcto: 4 (+ vignette = 5 total) |

---

## Qué funciona bien

- **Python validated epochs:** Los 5 períodos validados cargan correctamente en todos los módulos
- **Python validation guard:** `DataNotValidatedError` correcto en todos los períodos no-validados
- **R epoch2 (parcial):** En `2024-06` (validado), 6/8 módulos cargan bien en R
- **R API offline:** `pulso_list_variables()`, `pulso_describe_variable()`, `pulso_validation_status()`, `pulso_describe()` funcionan y retornan data significativa
- **Epoch boundary detection:** Ambos lenguajes asignan correctamente 2021-12 → `geih_2006_2020` y 2022-01 → `geih_2021_present`
- **R nested-zip errors:** Mensaje claro con referencia al issue de GitHub y versión planificada
- **Row counts Python vs R:** Donde ambos lenguajes cargan el mismo módulo, los row counts coinciden exactamente
- **p_coded column counts:** Donde ambos cargan, los conteos de columnas P-coded coinciden exactamente

---

## Inconsistencias Python / R

| Aspecto | Python (1.0.0rc1) | R (0.1.0) |
|---------|-------------------|-----------|
| Validation guard | ✅ `DataNotValidatedError` | ✗ Sin guard |
| `harmonize=TRUE` | ✅ Lowercase + 13 cols canónicas | ⚠️ Solo lowercase |
| `list_variables()` | ✗ `NotImplementedError("Phase 2")` | ✅ Funciona (30 vars) |
| `describe_variable()` | ✗ `NotImplementedError("Phase 2")` | ✅ Funciona |
| Epoch1 load | ✅ Todos los módulos disponibles | ✗ Todos fallan (BUG-004) |
| Epoch2 `caracteristicas_generales` | ✅ OK | ✗ Falla en Windows (BUG-003) |
| Epoch2 `migracion` | ✅ OK | ✗ Falla en Windows (BUG-003) |
| Nested-zip error message | ✗ Enmascarado por BUG-001 | ✅ Mensaje claro |

---

## Cobertura de tests en CRAN (riesgo adicional)

El Curator identificó que el testsuite de R tiene **18 tests con `skip_on_cran()`**, incluyendo prácticamente todos los tests de `test-load.R`. El resultado en CRAN sería `[ FAIL 0 | WARN 0 | SKIP 18 | PASS ~160 ]`. La función core `pulso_load()` tiene cobertura de testing casi nula en CRAN. No es un CRAN-blocker per se, pero es un riesgo de regresión que debería documentarse.

---

## Recomendación

**No submitir a CRAN hasta corregir los 5 blockers del paquete R.**

### Orden de prioridad para fixes

1. **BUG-004** (Critical): `rbind` → `dplyr::bind_rows` en `utils-parse.R:247` — desbloquea 14 años de datos
2. **BUG-003** (High): `utils::unzip` → `zip::unzip` en `utils-parse.R:220` — desbloquea `caracteristicas_generales` y `migracion`
3. **BUG-005** (High): auto-detección de separador en `utils-parse.R:104-110` — desbloquea 2022-01
4. **BUG-006** (High): agregar validation guard en `load.R` — corrige integridad de datos
5. **BUG-011** (High): pre-construir vignette antes de `R CMD build` — requerido por CRAN
6. **BUG-008** (Medium): portar lógica de derivación de columnas canónicas de Python a R
7. **BUG-SEGFAULT** (?): investigar y reproducir — potencialmente grave para uso interactivo

### Artifacts generados

- `tests-pre-cran/results/raw_results.json` — datos completos por período × módulo
- `tests-pre-cran/results/bugs_found.md` — reporte original del Coder
- `tests-pre-cran/results/test_log.txt` — log de ejecución con timestamps
- `tests-pre-cran/results/curator_review.md` — auditoría de honestidad + gaps
- `tests-pre-cran/results/tester_report.md` — re-verificación independiente de 3 hallazgos
- `tests-pre-cran/REPORT.md` — este reporte consolidado
