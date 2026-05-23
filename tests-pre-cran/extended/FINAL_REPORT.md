# pulso — Extended Pre-CRAN Testing: FINAL REPORT

**Fecha:** 2026-05-23  
**Branch:** `testing/pre-cran-validation`  
**Metodología:** 4 fases secuenciales → Curator + Tester independientes  
**Entorno:** Python 3.12.9 / pulso-co 1.0.0rc1 · R 4.5.2 / pulso R 0.1.0 · Windows 11  
**Cache:** 52 períodos cacheados (~2 GB) — cero descargas necesarias  

---

## VEREDICTO: NOT CRAN-READY

El paquete R `pulso 0.1.0` tiene **al menos 5 CRAN-blockers**. Adicionalmente hay 8 bugs de alta severidad que afectan la usabilidad. No submitir hasta resolver los blockers.

---

## Cobertura del testing

| Fase | Duración | Foco | Períodos | Módulos |
|------|----------|------|----------|---------|
| 1 | 53 min | SEGFAULT + ECH + epoch1 2007-2011 | 6 + edge cases | 36 |
| 2 | 30 min | epoch1 2012-2017 | 11 | 33+ |
| 3 | ~40 min | epoch1 2018-2021 + transición 2022 | 11 | 33+ |
| 4 | ~60 min | epoch2 2022-2025 + canonical vars | 16+ | 128+ |
| **Total** | **~3h** | **2007-2025** | **~40+ únicos** | **~230+** |

---

## Bugs activos — Tabla completa

### CRAN-Blockers (paquete R)

| Bug | Sev | Componente | Descripción | Verificado por |
|-----|-----|-----------|-------------|----------------|
| BUG-004 | **Critical** | R | `rbind()` sin `fill=TRUE` — epoch1 completo (2007–2021) inutilizable | Tester Fase 1, Curator (código) |
| BUG-003 | **Critical** | R | "invalid multibyte string" para módulos con tildes en filename — universal en todos los períodos donde ZIP no tiene UTF-8 flag | Tester final (3 períodos) |
| BUG-006 | **High** | R | Sin validation guard — R carga silenciosamente todos los períodos no-validados (16/16 confirmados), incluyendo schema drift 2025+ | Tester final |
| BUG-005 | **High** | R | 1-columna en 2022-01 para 5/8 módulos — separator detection failure | Fase 3, Curator |
| BUG-011 | **High** | R | Vignette no pre-construida — `R CMD check --as-cran` → 2 WARNINGs (`inst/doc/` ausente) | Curator smoke test |

### Bugs de alta severidad

| Bug | Sev | Comp | Descripción | Scope |
|-----|-----|------|-------------|-------|
| BUG-010/023 | High | R | `.resolve_zip_path()` aplica `iconv(CP437→UTF-8)` a paths ya UTF-8 para ZIPs con flag=2056 (2025-06+) → "Expected file not found" | 2025-06 y posteriores |
| BUG-017 | High | R | Keyword matcher falla en 2013-06 — filenames con sufijo numérico (`Ocupados06.csv`) | Solo 2013-06 |
| BUG-018 | High | Both | 2020-06 y 2020-12 tienen "Shape C" (COVID-year, CSV plano sin Cabecera/Resto) — R falla con "Shape A files not found", Python bloqueado por BUG-001 | 2020-06, 2020-12 |
| BUG-001 | High | Python (rc1) | `allow_unvalidated=True` → `TypeError: 'NoneType' not subscriptable` en `downloader.py:84` para los ~225 períodos con `checksum_sha256=null` | ~225 de 230 períodos |

### Bugs de mediana severidad

| Bug | Sev | Comp | Descripción |
|-----|-----|------|-------------|
| BUG-008 | Medium | R | `harmonize=TRUE` solo aplica lowercase — no deriva las 13 columnas canónicas que Python sí agrega |
| BUG-002 | Medium | Python | 32+ líneas "Skipping variable" a stdout por cada `load()` en epoch2 |
| BUG-007 | Medium | Python | `TypeError` (BUG-001) enmascara el error de nested-zip (2024-03, 2024-04) |
| BUG-015 | Low | R | `pulso_load()` no tiene parámetro `allow_unvalidated` — "unused argument" error |

### Bugs de baja severidad

| Bug | Sev | Comp | Descripción |
|-----|-----|------|-------------|
| BUG-009 | Low | Python | `list_variables()` / `describe_variable()` → `NotImplementedError("Phase 2")` |

### Bugs cerrados / artifacts de testing

| Bug | Estado | Razón |
|-----|--------|-------|
| BUG-SEGFAULT | **CERRADO** | No reproducible en R 4.5.2/Win11. Los exit 139 previos eran artefactos del heredoc multiline de bash en Windows (BUG-024). |
| BUG-019 | **CERRADO** | Solo clarificación de scope de BUG-005, no bug nuevo. |
| BUG-024 | **ARTIFACT** | exit 139 al pasar multiline a Rscript.exe vía heredoc — no es crash de pulso. |

---

## Correcciones al diagnóstico del Coder (Curator + Tester)

### BUG-023: diagnóstico original INCORRECTO

**El Coder de Fase 4 afirmó:** sources.json tiene Mojibake (double-encoding UTF-8) en las rutas de módulos con tildes.

**Refutado por Curator y Tester independientemente:**
```
Bytes en sources.json alrededor de 'Migraci':
hex: 4d 69 67 72 61 63 69 c3 b3 6e 2e 43 53 56
= "Migración.CSV" en UTF-8 correcto (c3 b3 = ó, 2 bytes)
La secuencia de double-encoding c3 83 c2 b3 NO aparece.
```

**Diagnóstico correcto (Curator):** `.resolve_zip_path()` en `utils-parse.R` aplica `iconv(from="CP437", to="UTF-8")` al `inner_path` leído del JSON cuando `Encoding(inner_path) == "unknown"`. Para ZIPs con UTF-8 flag=0 (la mayoría), esto corrompe ambos lados de la comparación de forma simétrica (accidental match → funciona para módulos sin tildes). Para ZIPs con UTF-8 flag=2056 (2025-06+), el path del ZIP queda correcto pero el `inner_path` del JSON queda corrpto después del iconv → mismatch → "Expected file not found". El bug verdadero está en la lógica de `.resolve_zip_path()`, no en sources.json.

### BUG-004 scope: matiz

El Coder dijo "ALL 6 modules fail". En epoch1 hay 3 módulos disponibles (los otros 3 retornan "not available"). Los 3 disponibles sí fallan — pero el "6" es impreciso. Los reportes de fase son correctos; solo el status.md simplificó.

---

## Scope real de cada bug (cuantificado)

| Bug | Scope documentado original | Scope confirmado |
|-----|---------------------------|-----------------|
| BUG-001 | "12 períodos no-validados" | ~225 de 230 períodos (solo 5 con checksum) |
| BUG-003 | "epoch1, caracgen" | **Todos los epochs**, todos los módulos con tildes en filename (migracion + caracgen), cuando ZIP UTF-8 flag=0 |
| BUG-004 | "epoch1" | **Todo epoch1 (2007-2021)**, todos los períodos |
| BUG-005 | "2022 transition" | **Solo 2022-01** (2022-06 y 2022-12 OK) |
| BUG-006 | "algunos epoch2" | **Todos los 16** epoch2 no-validados testados |
| BUG-010/023 | "ZIP structure cambió" | Raíz en `.resolve_zip_path()` para ZIPs con UTF-8 flag=2056 (2025-06+) |
| BUG-017 | "desconocido" | **Solo 2013-06** |
| BUG-018 | "desconocido" | **Solo 2020-06 y 2020-12** (COVID-year) |

---

## Matriz funcional final

### Python — status por tipo de período

| Tipo | Ejemplo | Status | Notas |
|------|---------|--------|-------|
| Validado epoch1 | 2007-12, 2015-06, 2021-12 | ✅ OK | 6 módulos disponibles |
| Validado epoch2 | 2022-01, 2024-06 | ✅ OK | 8 módulos |
| No-validado (cualquier epoch) | 2008-06, 2023-06, 2025-01 | ❌ BUG-001 | ~225 períodos bloqueados |
| COVID-year | 2020-06, 2020-12 | ❌ BUG-001 | Sin checksum, no testeable |
| Nested-zip | 2024-03, 2024-04 | ❌ BUG-001+007 | TypeError enmascara error |

### R — status por tipo de período × módulo

| Período | caracgen | migracion | ocupados/desoc/inac | vivienda/ingresos/otras |
|---------|----------|-----------|---------------------|------------------------|
| epoch1 (2007-2021) | ❌ BUG-003 | N/A | ❌ BUG-004 | ❌ BUG-004 |
| 2013-06 epoch1 | ❌ BUG-003 | N/A | ❌ BUG-017 | ❌ BUG-017 |
| 2020-06/12 epoch1 | ❌ BUG-018 | N/A | ❌ BUG-018 | ❌ BUG-018 |
| 2022-01 epoch2 | ❌ BUG-003 | ❌ BUG-003 | ❌ BUG-005 (1-col) | vivienda ✅; otros ❌ BUG-005 |
| 2022-06 a 2024-12 epoch2 | ❌ BUG-003 | ❌ BUG-003 | ✅ OK (200 cols) | ✅ OK |
| 2025-01 a 2025-05 epoch2 | ❌ BUG-003 | ❌ BUG-003 | ✅ OK (202 cols) | ✅ OK |
| 2025-06+ epoch2 | ❌ BUG-010/023 | ❌ BUG-010/023 | ✅ OK (202 cols) | ✅ OK |
| nested-zip 2024-03/04 | — | — | ✅ Error claro (no es bug) | — |

**R funcional sin bugs:** 6 de 8 módulos en epoch2 (2022-06 a 2025-06).  
**R completamente roto:** epoch1 completo + migracion + caracgen en todas las épocas.

### API offline — Python vs R

| Función | Python | R |
|---------|--------|---|
| `list_variables()` | ❌ Phase 2 | ✅ 30 vars (6 módulos) |
| `describe_variable()` | ❌ Phase 2 | ✅ OK |
| `list_available()` | ✅ (230, 5) | ❌ función no existe |
| `describe(module)` | ✅ OK | ✅ `pulso_describe()` OK |
| `validation_status()` | ✅ OK | ✅ OK |
| `list_validated_range()` | N/A | ✅ 5 períodos |
| `harmonize=TRUE` | ✅ +13 canonical cols | ⚠️ solo lowercase |

---

## Descubrimiento: schema drift en 2025+

2025-01 a 2025-05 tienen **202 columnas** en vez de 200. El cambio no es aditivo puro: se eliminan 3 variables (`p3051s1`, `p3052s1`, `p3366`) y se agregan 5 (`p3071s3`, `p3072s2`, `p7140s9a1`, `p1881s1`, `p7240s1`). R carga estos períodos sin ningún warning — BUG-006 hace que el schema drift sea invisible para el usuario.

---

## Recomendación: Fix antes de CRAN

### Orden de prioridad

**Fix 1 — BUG-003 + BUG-010/023** (mismo sistema, mismo fix)  
`utils-parse.R` en `.normalize_zip_names()` y `.resolve_zip_path()`: usar `zip::unzip()` del paquete `zip` (soporte Unicode nativo en Windows) o manejar encoding explícitamente según el flag del ZIP.  
**Desbloquea:** `migracion` + `caracgen` en todas las épocas.

**Fix 2 — BUG-004**  
`utils-parse.R:247`: reemplazar `rbind(df_c, df_r)` con `dplyr::bind_rows(df_c, df_r)`.  
**Desbloquea:** epoch1 completo (2007-2021) — 14 años de datos.

**Fix 3 — BUG-005**  
`utils-parse.R:104-110`: auto-detección de separador con `data.table::fread()` o `readr::read_delim(delim=NULL)`.  
**Desbloquea:** 2022-01 completamente.

**Fix 4 — BUG-006**  
`load.R`: agregar guard `if (!source_info$validated && !allow_unvalidated) stop(pulso_validation_error(...))`.  
**Fix 5 — BUG-011**  
Ejecutar `devtools::build_vignettes()` antes de `R CMD build` para pre-construir `inst/doc/pulso.html`.

**Fix 6 — BUG-017**  
`utils-parse.R` en el keyword matcher de Shape A: agregar fallback para `{keyword}{month:02d}.csv`.

**Fix 7 — BUG-018**  
`utils-parse.R`: detectar "Shape C" (un CSV plano por módulo, sin Cabecera/Resto) y agregar dispatch para ese caso. Afecta 2020-06/12.

**Fix 8 — BUG-008** (post-CRAN como v0.2.0)  
Portar la lógica de derivación de columnas canónicas de Python (`harmonize.py`) a R (`load.R`).

**Fix 9 — BUG-001 (Python)** — ya corregido en source v1.0.0, aplicar en próximo release PyPI.

---

## Estadísticas finales

| Categoría | Cantidad |
|-----------|----------|
| Períodos testados | ~40+ únicos |
| Combinaciones período × módulo × lenguaje | ~230+ |
| Bugs totales logueados | 24 (BUG-001 a BUG-024) |
| Bugs activos | 14 |
| Bugs cerrados / artifacts | 3 (SEGFAULT, 019, 024) |
| Scope clarifications | 7 |
| Correcciones al diagnóstico del Coder | 1 (BUG-023 → real causa en `.resolve_zip_path()`) |
| CRAN-blockers | 5 |

---

## Archivos de evidencia

```
tests-pre-cran/extended/
├── bugs_log.md              — todos los bugs con evidencia literal
├── phase_1_complete.md      — SEGFAULT + ECH + epoch1 2007-2011
├── phase_2_complete.md      — epoch1 2012-2017
├── phase_3_complete.md      — epoch1 2018-2021 + transición 2022
├── phase_4_complete.md      — epoch2 2022-2025 + canonical + matriz funcional
├── curator_final_review.md  — auditoría de honestidad post-4-fases
├── tester_final_report.md   — re-verificación independiente de 3 hallazgos
└── FINAL_REPORT.md          — este archivo
tests-pre-cran/
├── REPORT.md                — reporte del smoke test inicial (17 períodos)
└── results/
    ├── raw_results.json
    ├── bugs_found.md
    ├── curator_review.md
    └── tester_report.md
```
