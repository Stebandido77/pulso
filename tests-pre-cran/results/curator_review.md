# Curator Review — Pre-CRAN Smoke Test

**Reviewer:** Curator (Claude Sonnet 4.6)
**Date:** 2026-05-23
**Artifacts reviewed:** `bugs_found.md`, `test_log.txt`, `raw_results.json`
**Source cross-check:** `R/R/load.R`, `R/R/utils-parse.R`, `R/R/utils-source.R`, `R/R/utils-validation.R`, `.venv-pypi-test/…/downloader.py`, `python/pulso/_core/downloader.py`, `pulso.Rcheck/00check.log`, `pulso.Rcheck/tests/testthat.Rout`

---

## Veredicto: ACEPTO el reporte del Coder — con tres correcciones y cuatro gaps significativos

El reporte del Coder es honesto y técnicamente correcto en sus hallazgos principales. Los bugs están correctamente descritos y las evidencias son consistentes entre los tres archivos. Sin embargo, hay dos errores de clasificación importantes (uno beneficia al Python package, uno lo perjudica), y hay cuatro items que el Coder omitió o minimizó que son relevantes para la decisión CRAN.

---

## Hallazgos de la revisión

### Bugs confirmados con evidencia en logs y código fuente

**BUG-001 (Python TypeError en allow_unvalidated):** CONFIRMADO en los venvs instalados.
- El archivo `.venv-pypi-test/Lib/site-packages/pulso/_core/downloader.py` línea 84 muestra literalmente `short = checksum[:16]` sin guard de None.
- Esto coincide exactamente con el error reportado.
- Afecta los 12 períodos no validados, todos con `checksum_sha256: null`.

**BUG-003 (UTF-8 filenames en R):** CONFIRMADO.
- `R/R/utils-parse.R` tiene `.normalize_zip_names()` que convierte CP437 → UTF-8 para el *listado* de contenidos del ZIP, pero la extracción posterior via `utils::unzip(zip_path, files = resolved, ...)` pasa el nombre original del zip (no normalizado). El error se dispara en esa segunda llamada a `unzip()`.
- Confirmado en 2015-06, 2022-01, 2023-03, 2024-06, 2025-01. La descripción del bug en el reporte es correcta.

**BUG-004 (R rbind column mismatch epoch1):** CONFIRMADO.
- `R/R/utils-parse.R` líneas 243-247: `rbind(df_c, df_r)` sin `fill=TRUE`. Esto falla cuando los archivos Cabecera y Resto tienen diferente número de columnas, que es el comportamiento documentado del DANE para epoch1.
- Reproducido en 3 períodos validados (2007-12, 2015-06, 2021-12) más 4 no validados.

**BUG-005 (R 1-column result en 2022-01):** CONFIRMADO.
- `R/R/utils-parse.R` línea 104-110: `utils::read.csv(... sep = ";" ...)` hardcodea el separador. El reporte dice "sep=NULL" pero en realidad ya es ";". Si los CSVs de 2022-01 usan otro separador (tab o guion bajo), la lectura produce una sola columna. La evidencia de [31819 x 1] con vivienda_hogares funcionando ([26098 x 48]) es sólida y diferencia los módulos afectados correctamente.

**BUG-006 (R sin validation guard):** CONFIRMADO.
- `R/R/utils-source.R` en `.resolve_source()` devuelve el registro sin verificar el campo `validated`. `R/R/load.R` en `pulso_load()` no tiene ninguna verificación posterior del campo `validated` antes de descargar. La ausencia es total, no parcial.

**BUG-008 (harmonize=TRUE no agrega columnas canónicas en R):** CONFIRMADO con matiz importante (ver sección de correcciones).
- `R/R/load.R` líneas 61-63 muestran que `harmonize=TRUE` solo hace `names(df) <- tolower(gsub("[^[:alnum:]_]", "_", names(df)))`. Eso es lowercase + sanitización de nombres, pero cero columnas canónicas nuevas. La descripción "silently ignored" es imprecisa pero la evidencia numérica es correcta.

**BUG-009 (Python list_variables/describe_variable):** CONFIRMADO.
- `.venv-pypi-test/…/registry.py` línea 148: `raise NotImplementedError("Phase 2")`. Confirmado en la fuente instalada.

---

### Correcciones necesarias al reporte del Coder

**Corrección 1 — BUG-001: el bug YA ESTÁ CORREGIDO en el source, pero no en el paquete instalado.**

El Coder dice que BUG-001 está en `downloader.py:84`. Esto es verdad para el paquete instalado (`pulso_co-1.0.0rc1`). Sin embargo, el archivo fuente en `python/pulso/_core/downloader.py` línea 100 ya tiene la corrección:
```python
short = checksum[:16] if checksum is not None else f"unvalidated_{year}-{month:02d}"
```
El Coder testeó correctamente el paquete rc1 instalado (que tiene el bug), pero el reporte no documenta que la corrección ya existe en el source. Esto es importante porque el fix ya fue aplicado y el próximo release (1.0.0 final) no tendrá este bug. El reporte debería decir "BUG-001 presente en rc1, corregido en source para v1.0.0."

**Corrección 2 — BUG-008: "silently ignored" es incorrecto. El efecto real es lowercase + sanitización.**

El reporte dice que `harmonize=TRUE` "adds zero canonical columns" y que el parámetro es "silently ignored." La segunda parte es incorrecta. El parámetro SÍ tiene un efecto observable: convierte los nombres de columnas a lowercase y reemplaza caracteres no alfanuméricos con guión bajo (`tolower(gsub("[^[:alnum:]_]", "_", names(df)))`). Lo que no hace es agregar las columnas canónicas armonizadas que Python agrega. Esta distinción importa para el diagnóstico: no es un parámetro ignorado, es un parámetro con implementación incompleta. El veredicto de CRAN-blocker sigue siendo correcto (la funcionalidad prometida no se entrega), pero la descripción del bug es imprecisa.

**Corrección 3 — Versión Python: el test usó rc1, el source es 1.0.0.**

El log dice `pulso.__version__ = '1.0.0rc1'` y lo marca como "flagged." El reporte de bugs dice "Python 1.0.0rc1 (NOTE: rc1, not final)". Sin embargo, el source `python/pulso/__init__.py` dice `__version__ = "1.0.0"` (sin rc1). Los dos venvs de test tienen `pulso_co-1.0.0rc1.dist-info`. La confusión es: el test usó el paquete PyPI rc1, que tiene downloader bugueado; el source ya está en 1.0.0. El reporte debería aclarar explícitamente que BUG-001 aplica a rc1/PyPI pero no al source actual.

---

### Items que el Coder omitió o minimizó

**Gap 1 — R CMD check --as-cran ya fue ejecutado y tiene resultados, pero el Coder no lo mencionó.**

El directorio `pulso.Rcheck/` existe y contiene `00check.log` con un R CMD check completo (`--as-cran`). El resultado es:
```
Status: 2 WARNINGs, 2 NOTEs
```
Los WARNINGs son:
1. "Files in the 'vignettes' directory but no files in 'inst/doc'" — vignette no pre-construida
2. "Directory 'inst/doc' does not exist. Package vignette without corresponding single PDF/HTML"

Los NOTEs son:
1. "New submission" + "Package has a VignetteBuilder field but no prebuilt vignette index"
2. "Files 'README.md' or 'NEWS.md' cannot be checked without 'pandoc' being installed"

**Ambos WARNINGs son CRAN-blockers.** CRAN exige que las vignettes estén pre-construidas (en `inst/doc/`) en el tarball subido. Esto es un problema de buildtime, no de runtime, y el Coder no lo detectó ni reportó. El veredicto "NOT READY" del Coder es correcto, pero por razones incompletas. Este sería el quinto CRAN-blocker.

El test unitario sí pasó: `[ FAIL 0 | WARN 0 | SKIP 20 | PASS 160 ]`, con 18 tests skipped on CRAN (por `skip_on_cran()`) y 2 skipped por deferral (Shape A single-CSV). El Coder no mencionó los 18 tests que se saltan en CRAN, lo que significa que la cobertura de testing real en CRAN sería significativamente menor que en dev.

**Gap 2 — 2020-06 (Shape A) no carga en NINGUNO de los dos lenguajes, pero el Coder lo trata como "expected".**

El log dice que R falla con "Shape A files for module ocupados not found. Tried: Ocupados" para 2020-06. Pero el Coder no classifica esto como un bug separado — lo agrupa implícitamente en BUG-004. Sin embargo, la causa es diferente: BUG-004 es rbind column mismatch (datos se leen pero no se combinan), mientras que para 2020-06 los archivos no se encuentran (keyword matching falla). El keyword en `.MODULE_KEYWORDS_GEIH1` para `ocupados` es simplemente `"Ocupados"` (con mayúscula inicial), pero si los archivos DANE en 2020-06 se llaman de otra forma, el matching falla. Esto es un caso potencialmente distinto de BUG-004 que merece documentación separada. No es necesariamente más severo, pero la causa raíz es diferente.

**Gap 3 — p_coded count de 2025-06, 2026-01, 2026-02 está marcado como "not_measured".**

En el raw_results.json, los períodos 2025-06, 2026-01, 2026-02 tienen `"p_coded_count": "not_measured"` para ocupados. El Coder cita que "p_coded column consistency: Where both load the same module, P-coded column counts match exactly" en la sección positiva. Pero para estos tres períodos, el p_coded nunca fue medido, por lo que la afirmación de consistencia no aplica a ellos. La afirmación "match exactly" está respaldada solo para los períodos validados y algunos no validados, no para toda la muestra. Esto es una imprecisión menor en la sección de resultados positivos.

**Gap 4 — BUG-006 tiene una consecuencia operativa que el Coder menciona de pasada pero no cuantifica.**

R descargó ~70MB de datos no validados para 2026-01 y 2026-02 sin advertencia al usuario. El reporte lo nota en el raw_results.json pero no cuantifica el riesgo en bugs_found.md: un usuario que llame `pulso_load(2026, 1, "ocupados")` en producción recibirá datos no validados (potencialmente incorrectos o desactualizados) sin ningún aviso. Dado que el paquete DESCRIPTION dice "Provides a tidy interface to download, parse, and harmonize labor market surveys" con implicación de calidad, este es un bug de integridad de datos, no solo de API parity. El Coder lo clasificó como Medium, lo cual podría ser LOW para un usuario avanzado pero es HIGH para usuarios CRAN típicos que no conocen el estado de validación.

---

### Inconsistencias internas en el reporte

**Inconsistencia 1 — Versión Python.**
El log dice "pulso 1.0.0rc1", el reporte de bugs dice lo mismo correctamente. El summary JSON dice `"pulso_python_version": "1.0.0rc1"`. No hay confusión interna entre los tres archivos, pero el Coder no explica la diferencia con el source (que ya dice "1.0.0"). Esto no es una inconsistencia interna pero es un contexto ausente.

**Inconsistencia 2 — "2001 MB de cache pre-existente" y tiempos de descarga.**
El log reporta 2001 MB / 54 archivos de cache pre-existente a las [09:02]. Esto indica que la mayoría de los ZIPs ya estaban descargados. El log muestra que 2026-01 y 2026-02 sí se descargaron (~70MB) en la fase 4 entre [09:19] y [09:25], lo que implica ~6 minutos para dos descargas de 70MB — plausible en una conexión normal. No hay inconsistencia de timing que invalide los resultados.

**Inconsistencia 3 — "OK [29925 x 213]" y el claim de evidencia observada.**
El reporte cita "[29925 x 213]" para 2024-06 ocupados en Python como evidencia de BUG-008. Esto está en el raw_results.json con `"shape": [29925, 213]` y en el log `[09:05] Python ocupados: OK [29925 x 213]`. Las shapes observadas son consistentes entre los tres archivos y coinciden con valores plausibles (la diferencia de 13 columnas entre Python 213 y R 200 está explicada y los p_coded cuentas iguales confirman los datos raw son idénticos). La evidencia es observada, no inferida.

**Inconsistencia 4 — Summary JSON vs bugs_found.md en CRAN blockers.**
El summary JSON lista 3 CRAN-blockers: BUG-004, BUG-003, BUG-008. El markdown lista 4: BUG-004, BUG-003, BUG-005, BUG-008. El JSON omite BUG-005 como CRAN-blocker. La tabla en markdown es la fuente correcta (BUG-005 sí bloquea CRAN ya que 5 de 8 módulos del primer período epoch2 validado fallan en R). Esta inconsistencia menor sugiere que el JSON fue escrito antes de finalizar el análisis de BUG-005.

---

### Veredicto CRAN revisado

El Coder dice "NOT CRAN-READY" con 4 CRAN-blockers para R. El veredicto es correcto. Tras la revisión, los CRAN-blockers son:

**Para el R package (pulso 0.1.0):**
1. BUG-004: Epoch1 completo inutilizable (14 años de datos, rbind sin fill)
2. BUG-003: 2 de 8 módulos siempre fallan en Windows (encoding UTF-8)
3. BUG-005: 5 de 8 módulos fallan en 2022-01 (primer período epoch2 validado)
4. BUG-008: harmonize=TRUE no implementado completamente (solo lowercase, cero columnas canónicas)
5. **[NUEVO]** Vignette no pre-construida: `R CMD check --as-cran` produce 2 WARNINGs por `inst/doc/` ausente

**Para el Python package (pulso-co 1.0.0rc1):**
1. BUG-001: `allow_unvalidated=True` crashea para todos los períodos no validados (presente en rc1, ya corregido en source para v1.0.0)

El Python package 1.0.0 (source actual) probablemente pasaría PyPI sin BUG-001, pero eso está fuera del scope de este smoke test.

---

## Recomendación

El reporte del Coder es sólido, honesto y reproduce los bugs con evidencia concreta. Las shapes y errores son consistentes entre los tres archivos de resultados. Se acepta con las siguientes correcciones prioritarias:

1. **Corregir BUG-001:** Documentar explícitamente que el bug existe en rc1 pero ya está corregido en el source para v1.0.0. Cambiar "Fix:" por "Fixed in source (v1.0.0); rc1 deployed to PyPI still has the bug."

2. **Corregir BUG-008:** Cambiar "silently ignored" por "incompletely implemented — only applies lowercase + name sanitization, does not add canonical columns." El diagnóstico correcto facilita el fix.

3. **Agregar BUG-011:** Vignette no pre-construida. `R CMD check --as-cran` produce 2 WARNINGs por `inst/doc/` ausente. Severidad: CRAN-blocker (buildtime). Fix: `devtools::build_vignettes()` antes de `R CMD build`, o agregar `inst/doc/pulso.html` pre-renderizado.

4. **Documentar 18 tests skip_on_cran:** El testsuite de R tiene 18 tests con `skip_on_cran()`. Los tests que se saltan incluyen todos los tests de `test-load.R` (excepto 2). Esto significa que en CRAN la cobertura de testing de la función core `pulso_load()` es casi cero. No es un CRAN-blocker per se, pero es un riesgo de regresión que debería documentarse.

5. **Revisar clasificación de 2020-06:** La falla de Shape A en 2020-06 tiene causa raíz diferente al rbind de BUG-004. Documentar como caso de keyword matching que requiere investigación separada.
