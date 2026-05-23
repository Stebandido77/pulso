# Curator Final Review — Extended Testing

**Curator:** claude-sonnet-4-6 (independent, no authorship of any phase report)
**Date:** 2026-05-23
**Files read:** bugs_log.md, phase_1-4_complete.md, status.md, progress.json, tester_final_report.md, r/R/utils-parse.R, r/R/load.R, r/inst/extdata/sources.json (raw bytes + parsed JSON)

---

## Veredicto general: ACEPTO con corrección obligatoria en BUG-023

El reporte de las 4 fases es sustancialmente honesto, internamente consistente y técnicamente sólido. Los hallazgos principales son verificables directamente en el código fuente y en los bytes del JSON. Un único diagnóstico de causa raíz es materialmente incorrecto (BUG-023). El Tester independiente ya llegó a la misma conclusión; esto refuerza la credibilidad del proceso.

---

## Consistencia de evidencia

### BUG-003 "universal": CONFIRMO

La claim es sustancialmente correcta con una excepción bien documentada en los propios reportes.

- `caracteristicas_generales`: falla en TODOS los períodos epoch1 (2007-2021, todas las fases) y en todos los epoch2 testeados. Evidencia cruzada: Fases 1, 2, 3, 4 sin excepción.
- `migracion`: falla en TODOS los epoch2 con UTF-8 flag=0 (2022-06 hasta 2025-01), y de manera distinta en 2025-06 (UTF-8 flag=2056). El Tester ejecutó comandos reales (2023-06, 2024-01, 2025-01) y obtuvo `invalid multibyte string at '<a2>n.C'` en los tres.
- La excepción (2025-06 da "Expected file not found" en lugar de "invalid multibyte string") está correctamente anotada como modo de falla diferente, no como funcionamiento exitoso.
- **BUG-016** (dos variantes de error message de BUG-004) está bien documentado y no contradice la universalidad de BUG-003.

La evidencia de la tabla en phase_4_complete.md — 7 períodos epoch2 con el mismo `<a2>n.C` + 2025-06 con error diferente — es coherente entre sí y con el código fuente.

### BUG-004 "cubre TODO epoch1": CONFIRMO con precisión necesaria

El claim de universalidad es correcto a nivel funcional ("R no puede cargar ningún período epoch1") pero técnicamente impreciso si se lee literalmente como "BUG-004 es la causa en todos los casos". Los reportes de fase son precisos; es el status.md el que habla sin matices:

- BUG-004 propiamente (rbind sin fill): afecta 2007-2012, 2014-2019, 2021 — para módulos distintos de caracgen.
- 2013-06: falla por BUG-017 (sufijo numérico en filename), no BUG-004. Documentado en Fase 2.
- 2020-06, 2020-12: fallan por BUG-018 (Shape C COVID), no BUG-004. Documentado en Fase 3.
- caracgen en todo epoch1: falla por BUG-003, no BUG-004. Documentado en Fase 1/2.

La Phase 4 consolidated table es correcta. El status.md dice "BUG-004 = universal en epoch1" que es una simplificación aceptable en contexto (el resultado práctico — epoch1 inutilizable en R — es correcto), pero si alguien intenta aplicar la corrección de fill=TRUE a 2013-06 o 2020, va a seguir fallando. Esta imprecisión debe anotarse.

El código fuente confirma el mecanismo: `utils-parse.R` línea 247: `return(rbind(df_c, df_r))` — rbind() base de R sin `fill=TRUE`. Las dos variantes de error (Variante A: "numbers of columns do not match"; Variante B: "names do not match previous names") están ambas documentadas y son las manifestaciones esperadas de un rbind() sobre DataFrames con columnas distintas.

### BUG-023 Mojibake en sources.json: REFUTO

Esta es la corrección material del reporte.

**Verificación de bytes reales:**

```
with open('sources.json', 'rb') as f: raw = f.read()
# Primer match de 'Migraci' en raw bytes:
# offset 247271: b'Migraci\xc3\xb3n.CSV"\n        }'
# Hex: 4d696772616369c3b36e2e435356
```

Los bytes son `\xc3\xb3` — codificación UTF-8 correcta para `ó` (U+00F3). La secuencia de doble-encoding `\xc3\x83\xc2\xb3` **no aparece en ningún punto del archivo**. El Tester independiente confirmó exactamente esto con el mismo resultado: "Mojibake Migración at byte offset: -1".

El archivo sources.json está correctamente codificado en UTF-8. Parsear el JSON con `json.load(open(..., encoding='utf-8'))` funciona sin error. Las rutas para 2022-01, 2024-06 y 2025-06 son idénticas y contienen bytes UTF-8 correctos.

**¿Qué es entonces BUG-023?**

El bug es real — 2025-06 migracion y caracgen dan "Expected file not found" — pero la causa raíz está en el runtime de R, no en sources.json.

El mecanismo correcto (trazado desde el código fuente en `utils-parse.R`):

1. `sources.json` almacena `"CSV/Migración.CSV"` con bytes UTF-8 correctos (`c3 b3`).
2. R lee la cadena del JSON. En Windows/R, `Encoding()` de esa cadena puede ser `"unknown"`.
3. `.resolve_zip_path()` (línea 49-51) comprueba: `if (Encoding(inner_path) == "unknown") inner_path <- iconv(inner_path, from="CP437", to="UTF-8")`.
4. Los bytes `c3 b3` (ya UTF-8 correcto) son interpretados como dos caracteres CP437: `0xc3` = `Ã` (U+00C3) y `0xb3` = `³` (U+00B3). Convertidos a UTF-8: `c3 83` + `c2 b3` → resultado: `MigraciÃ³n.CSV` (doble-encoding en runtime).
5. Para ZIPs con flag=0: `.normalize_zip_names()` también corrompe la entrada del ZIP igualmente, de modo que ambas cadenas coinciden accidentalmente → la extracción llega al CSV, y el fallo ocurre en `read.csv()` (el "invalid multibyte string" de BUG-003).
6. Para 2025-06 (flag=2056, UTF-8 declarado): `normalize_zip_names` NO aplica iconv (Encoding != "unknown"), el ZIP queda con UTF-8 correcto → mismatch con el `inner_path` corrupto → NULL → "Expected file not found".

La causa raíz unificada: `.resolve_zip_path` aplica `iconv(CP437→UTF-8)` a `inner_path` cuando `Encoding=="unknown"`, incluso si los bytes ya son UTF-8 válido. El sources.json está bien; el problema es que R no distingue entre "bytes desconocidos CP437" y "bytes UTF-8 con Encoding no declarado".

**Corrección al bugs_log:** BUG-023 no debe describirlo como "sources.json double-encodes accented filenames". La descripción correcta es: "`.resolve_zip_path` aplica iconv(CP437→UTF-8) a paths de sources.json cuyo Encoding R marca como 'unknown', corrompiendo en runtime rutas con caracteres no-ASCII que son UTF-8 válido." El tester ya propuso la corrección adecuada (agregar `fileEncoding="UTF-8"` en la lectura del CSV o detectar el encoding del ZIP).

### BUG-SEGFAULT closure: CONFIRMO

El cierre está bien justificado y la explicación del BUG-024 (artifact de bash heredoc multiline) es técnicamente plausible. Tres evidencias convergen:

1. 9 runs (3 escenarios × 3 repeticiones) con código de una línea, todos exit 0.
2. Test C (error seguido de éxito en la misma sesión R) funciona correctamente — esto es el test más directo de "¿se corrompe el estado de R?".
3. BUG-024 muestra que los exit 139 solo ocurrían con heredoc multiline, que es un artefacto del ambiente bash-on-Windows.

El argumento "bash en Windows falla al pasar strings multiline a procesos Win32 via -e" es conocido. Exit 139 en ese contexto es coherente con un fault en bash, no en R ni en pulso.

---

## Correcciones necesarias

### Corrección 1 (obligatoria): BUG-023 — rediagnóstico de causa raíz

El bugs_log.md dice: *"sources.json stores paths... DOUBLE-ENCODED as Mojibake"*. Esto es factualmente incorrecto. Debe corregirse:

- **Diagnóstico erróneo:** "Mojibake en sources.json" / "double-encoding en el archivo"
- **Diagnóstico correcto:** "`.resolve_zip_path` corrompe en runtime los paths UTF-8 de sources.json al aplicar iconv(CP437→UTF-8) cuando `Encoding(inner_path)=='unknown'"
- **Impacto en severidad:** La severidad (HIGH) y el síntoma (2025-06 falla con "Expected file not found") son correctos. Solo el diagnóstico de causa raíz es erróneo.
- **Impacto en fix:** El fix correcto es proteger `inner_path` de la conversión innecesaria en `.resolve_zip_path`. No requiere tocar sources.json.

### Corrección 2 (menor): status.md — precisión sobre BUG-004

El status.md afirma "BUG-004: rbind() epoch1 falla — UNIVERSAL en epoch1" sin mencionar que 2013-06, 2020-06/12 y caracgen fallan por bugs distintos. Los reportes de fase son correctos; es el status.md el simplificado. Agregar una nota: "2013-06, 2020-06/12 fallan por BUG-017/BUG-018 respectivamente; epoch1 en R es inutilizable por múltiples bugs, no solo BUG-004."

---

## Gaps no cubiertos

### Gap 1: BUG-011 (vignette) — nunca testeado en extended testing

BUG-011 aparece en el known bugs list y en el CRAN critical summary de Phase 4, pero ninguna de las 4 fases ejecutó `R CMD check` ni verificó si la vignette pre-construida existe. Este es el único bug CRAN-critical que no tiene evidencia de extended testing. Para una CRAN submission, este bug probablemente causará un check failure directamente. Requiere verificación separada.

### Gap 2: BUG-007 (TypeError enmascara nested-zip en Python) — parcialmente cubierto

BUG-007 está OPEN pero no fue verificado de forma aislada. Para 2024-03/04, Python siempre dispara BUG-001 (checksum=null) antes de llegar al nested-zip check. No se sabe si Python daría un error informativo en un período nested-zip con checksum no-nulo. El bug puede ser más o menos severo de lo documentado. Gap de alcance acotado.

### Gap 3: BUG-005 root cause no identificado

Se confirmó que 2022-01 da 1-col result en R (5/8 módulos), pero la causa exacta (¿por qué el parser falla solo para 2022-01 y no para 2022-06 o 2022-12?) no fue trazada hasta el código. El reporte señala la diferencia en estructura de carpetas ZIP pero no explica el mecanismo por el cual esa diferencia rompe la detección del separador. Esto no afecta CRAN directamente (el bug está correctamente scoped) pero dificulta el fix.

### Gap 4: BUG-002 (warnings Python) — observado pero no cuantificado sistemáticamente

Las warnings "Skipping variable" de Python se observaron múltiples veces como efecto secundario. No hubo un test específico de: (a) ¿van a stdout o stderr? (b) ¿interfieren con el resultado del usuario? La claim "32+ warnings" del smoke test no fue re-verificada en extended testing.

---

## Veredicto CRAN final

**Estado:** NO LISTO para CRAN en estado actual. Esto es independiente de la calidad del reporte de testing — el testing simplemente confirma lo que bloquea la submission.

Bugs bloqueantes para CRAN (por orden de impacto):

| Bug | Sev | Evidencia | Estado |
|-----|-----|-----------|--------|
| BUG-004 | Critical | rbind() en utils-parse.R línea 247 | Confirmado en código |
| BUG-011 | High | Vignette no pre-built | No testeado en extended, asumido del smoke |
| BUG-003+BUG-023 | High | 2/8 módulos (migracion, caracgen) totalmente rotos en R | Confirmado |
| BUG-006 | High | pulso_load() no tiene validation guard | Confirmado en load.R |
| BUG-008 | Medium | harmonize=TRUE en R no añade canonical cols | Confirmado en load.R |

BUG-004 es suficiente por sí solo para bloquear CRAN: toda la era epoch1 (14 años de datos) es inutilizable en R. BUG-003 bloquea 2 de 8 módulos en todas las épocas. BUG-011 probablemente falla `R CMD check --as-cran`.

**Calidad del reporte de testing:** ALTA. Las 4 fases son metodológicamente rigurosas, la evidencia está cruzada entre fases, los bugs nuevos se documentan con mensajes de error literales, y los cierres (BUG-SEGFAULT, BUG-019) tienen justificación sustancial. La única falla material es el diagnóstico de causa raíz de BUG-023, que afortunadamente no afecta el síntoma reportado ni la severidad asignada.
