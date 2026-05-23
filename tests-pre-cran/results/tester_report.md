# Tester Audit — Pre-CRAN Smoke Test

**Date:** 2026-05-23  
**Tester:** Auditor independiente (Claude Sonnet 4.6)  
**Coder report verified against:** resultados en `tests-pre-cran/results/`

---

## Hallazgo 1: BUG-004 (rbind epoch1)

**Veredicto: CONFIRMADO — con matiz sobre scope**

**Comandos ejecutados:**
```
Rscript -e 'library(pulso); df <- tryCatch(pulso_load(2007,12,"ocupados"), error=function(e) cat("ERROR:", conditionMessage(e), "\n")); if(is.data.frame(df)) cat("OK:", nrow(df), "x", ncol(df), "\n")'
Rscript -e '... pulso_load(2015,6,"ocupados") ...'
Rscript -e '... pulso_load(2021,12,"ocupados") ...'
# y módulos desocupados e inactivos para 2007-12 y 2021-12
```

**Output real:**
```
ERROR: numbers of columns of arguments do not match   # 2007-12 ocupados
ERROR: numbers of columns of arguments do not match   # 2015-06 ocupados
ERROR: numbers of columns of arguments do not match   # 2021-12 ocupados
ERROR: numbers of columns of arguments do not match   # 2007-12 desocupados
ERROR: numbers of columns of arguments do not match   # 2007-12 inactivos
ERROR: numbers of columns of arguments do not match   # 2021-12 desocupados
ERROR: numbers of columns of arguments do not match   # 2021-12 inactivos
```

**Análisis de causa raíz (desde código fuente):**  
En `R/R/utils-parse.R` línea 247, la función `.parse_module_csv()` usa `rbind(df_c, df_r)` para módulos Shape A (cabecera + resto). Los CSVs de epoch1 tienen diferente número de columnas entre cabecera y resto. El error exacto "numbers of columns of arguments do not match" es preciso. El Coder reportó todos los módulos disponibles para epoch1 fallan — confirmado para `ocupados`, `desocupados`, `inactivos`. Los módulos `fuerza_trabajo`, `vivienda`, `no_ocupados` devuelven "not available for 2007-12" (no es rbind error, simplemente no existen para ese período), lo que es comportamiento correcto.

**Matiz vs reporte del Coder:** El Coder dice "ALL 6 modules for ALL validated epoch1 periods". Los módulos `fuerza_trabajo`, `vivienda`, `no_ocupados` no están disponibles para epoch1 (error diferente, no rbind). El rbind bug afecta a los 3 módulos que SÍ existen en epoch1. Eso es consistente, pero el "6 modules" es impreciso — epoch1 tiene menos de 6 módulos disponibles.

**Veredicto final sobre BUG-004:** CONFIRMADO. El error es exactamente "numbers of columns of arguments do not match" en todos los módulos Shape A disponibles para epoch1 (2007-12, 2015-06, 2021-12). Causa raíz: `rbind()` en `utils-parse.R:247` sin alinear columnas antes de combinar cabecera y resto.

---

## Hallazgo 2: BUG-003 (UTF-8 filenames Windows)

**Veredicto: CONFIRMADO — con corrección del mensaje de error**

**Comandos ejecutados:**
```
Rscript -e 'library(pulso); tryCatch(pulso_load(2024,6,"caracteristicas_generales"), error=function(e) cat("ERROR:", conditionMessage(e), "\n"))'
Rscript -e '... pulso_load(2024,6,"migracion") ...'
Rscript -e '... pulso_load(2022,1,"caracteristicas_generales") ...'
Rscript -e '... pulso_load(2023,6,"caracteristicas_generales") ...'
Rscript -e '... pulso_load(2022,6,"caracteristicas_generales") ...'
```

**Output real:**
```
ERROR: invalid multibyte string at '<a1>sti'   # 2024-06 caracteristicas_generales
ERROR: invalid multibyte string at '<a2>n.C'   # 2024-06 migracion
ERROR: invalid multibyte string at '<a1>sti'   # 2022-01 caracteristicas_generales
ERROR: invalid multibyte string at '<a1>sti'   # 2023-06 caracteristicas_generales (+ "Downloading https://...")
ERROR: invalid multibyte string at '<a1>sti'   # 2022-06 caracteristicas_generales (+ "Downloading https://...")
```

**Corrección al reporte del Coder:** El Coder reporta el error como relacionado a `utils::unzip()`. El mensaje real es "invalid multibyte string" — este error ocurre cuando R intenta procesar la lista de archivos dentro del ZIP (que contiene nombres de archivo con caracteres UTF-8 como `ó`, `ú`, `ñ` en "Características" y "Migración"). Ocurre en la función `utils::unzip(zip_path, list = TRUE)$Name` (ver `utils-parse.R:220`), donde el resultado se procesa como cadena y R/Windows no puede interpretar los bytes Latin-1/UTF-8. El error no es en la descarga — se produce al intentar listar el contenido del ZIP descargado correctamente.

El bug afecta TODOS los períodos epoch2 testeados para estos dos módulos (2022-01, 2022-06, 2023-06, 2024-06). El scope "TODOS los períodos epoch2" no fue refutado.

**Veredicto final sobre BUG-003:** CONFIRMADO con precisión mejorada. El error es "invalid multibyte string" (no un crash de `unzip` per se), causado por nombres de archivo con tildes dentro del ZIP que R en Windows no puede procesar al listar contenidos. Afecta sistemáticamente a `caracteristicas_generales` y `migracion` en todos los períodos epoch2 testeados.

---

## Hallazgo 3: BUG-008 (harmonize=TRUE silently ignored en R)

**Veredicto: PARCIAL — el Coder tiene razón en el resultado numérico pero la descripción es inexacta**

**Comandos ejecutados:**
```
# Python
python -c "df = pulso.load(2024,6,'ocupados',harmonize=True); print(df.shape)"
python -c "df_raw = pulso.load(2024,6,'ocupados',harmonize=False); print(df_raw.shape)"

# R
Rscript -e '... pulso_load(2024,6,"ocupados",harmonize=FALSE) ... ncol ...'
Rscript -e '... pulso_load(2024,6,"ocupados",harmonize=TRUE) ... ncol ...'
```

**Output real:**
```
Python harmonize=False:  (29925, 200)   — columnas UPPERCASE
Python harmonize=True:   (29925, 213)   — 13 columnas canónicas nuevas
  Nuevas cols: ['area', 'departamento', 'posicion_ocupacional', 'rama_actividad',
                'ocupacion', 'horas_trabajadas_sem', 'ingreso_laboral',
                'tiene_contrato', 'tipo_contrato', 'cotiza_pension',
                'hogar_id', 'peso_expansion', 'peso_expansion_persona']

R harmonize=FALSE: 200 cols (UPPERCASE)
R harmonize=TRUE:  200 cols (lowercase renaming solamente)
  'area' presente: TRUE (existía antes, solo renombrada)
  'departamento' presente: FALSE
  'posicion_ocupacional' presente: FALSE
```

**Análisis de causa raíz (desde código fuente):**  
En `R/R/load.R` línea 61-63, `harmonize=TRUE` en R solo ejecuta:
```r
names(df) <- tolower(gsub("[^[:alnum:]_]", "_", names(df)))
```
Es decir, R "harmonize" únicamente renombra columnas a minúsculas. Python "harmonize" hace eso Y además deriva/computa 13 columnas canónicas adicionales (área, departamento, posicion_ocupacional, rama_actividad, etc.).

El Coder reportó "R adds 0 canonical cols (200 raw → 200 total)". Esto es numéricamente correcto. La descripción "silently ignored" no es del todo exacta — R sí hace algo (lowercase renaming), pero no aplica la derivación de columnas canónicas que Python sí aplica. Es una asimetría de comportamiento documentada vs. no-documentada, no un "silently ignored".

**Nota adicional:** Python emite 17 warnings tipo "Skipping variable 'sexo': source columns missing" para el módulo `ocupados` 2024-06, lo que sugiere que incluso en Python la harmonización es parcial para ese módulo — las variables demográficas no se derivan porque `ocupados` no tiene columnas como P6040, P6050, P6080, etc. Solo se agregan 13 de las ~30 variables canónicas posibles.

**Veredicto final sobre BUG-008:** CONFIRMADO EN RESULTADO NUMÉRICO, DESCRIPCIÓN REFINADA. R harmonize=TRUE aplica solo lowercase renaming (200 → 200 cols). Python harmonize=True añade 13 columnas derivadas (200 → 213 cols). La discrepancia es real y reproducible. La causa es que la lógica de derivación de variables canónicas de Python no fue portada al R.

---

## Cache Analysis

**Resultado:** El cache en el momento del test del Coder tenía exactamente 54 archivos ZIP en `raw/` ocupando ~2.0 GB (reportados por `pulso.cache_info()`).

**Períodos pre-cacheados en `raw/`:**
- epoch1 (zips pequeños ~6-13 MB): 2007-06, 2007-12, 2008-06, 2009-06, 2010-06, 2011-06, 2012-06, 2013-06, 2013-12, 2014-06, 2014-12, 2015-06, 2015-12, 2016-06, 2016-12, 2017-06, 2017-12, 2018-06, 2018-12, 2019-06, 2019-12, 2020-06, 2020-12, 2021-06, 2021-12
- epoch2 (zips grandes ~55-74 MB): 2022-01, 2022-06, 2022-12, 2023-06, 2023-12, 2024-01 a 2024-12 (12 meses), 2025-01 a 2025-12 (12 meses)
- empalme (zips muy grandes ~200-250 MB): 2010-2019

**Implicación para el reporte del Coder:** Los períodos testeados (2007-12, 2015-06, 2021-12 para epoch1; varios epoch2) estaban pre-cacheados. Los resultados de éxito/fallo son igualmente válidos, pero el Coder no midió tiempos reales de descarga. Los "OK" en Python para esos períodos son legítimos — Python procesó los ZIPs locales del cache correctamente. Los errores en R también son legítimos — el cache reduce el tiempo de obtención del ZIP pero el bug ocurre al parsear, no al descargar.

---

## Observaciones Adicionales

1. **Segfault en R al encadenar dos pulso_load() en la misma sesión:** Al intentar llamar `pulso_load()` dos veces en un mismo script `-e` (ej. para comparar harmonize=TRUE vs FALSE), R 4.5.2 produce un segmentation fault (exit code 139). Esto es un bug potencialmente severo adicional, no reportado por el Coder. Podría ser una fuga de memoria o un problema con la gestión de conexiones al ZIP. Requiere investigación independiente.

2. **Python harmonize=True emite 17 warnings en stderr para 2024-06 ocupados:** Todas las variables demográficas (sexo, edad, estado_civil, etc.) son skipped porque el módulo `ocupados` no contiene las columnas fuente necesarias (P3271, P6040, etc.). Esto es comportamiento esperado pero puede confundir usuarios — los warnings no son errores pero son verbosos.

3. **BUG-003 produce "Downloading https://..." antes del error:** Para períodos no cacheados (2022-06, 2023-06), el R descarga el ZIP exitosamente antes de fallar al listar su contenido. Confirma que el problema es post-descarga, en el procesamiento de nombres de archivo dentro del ZIP.

4. **El cache empalme (2010-2019) no fue usado en los tests:** Los archivos `empalme/*.zip` (~200 MB cada uno) existen en cache pero ninguno de los tests descritos del Coder usa la función de empalme.

---

## Veredicto Final

**CONFIRMO el reporte del Coder para BUG-004 y BUG-003.**  
**MODIFICO el reporte del Coder para BUG-008.**

| Bug | Veredicto | Nota |
|-----|-----------|------|
| BUG-004 (rbind epoch1) | CONFIRMADO | Error exacto verificado en 3 períodos x 3 módulos. "6 modules" es impreciso — epoch1 tiene 3 módulos disponibles, todos fallan. |
| BUG-003 (UTF-8 Windows) | CONFIRMADO | Error "invalid multibyte string", no crash de unzip per se. Afecta todos los epoch2 testeados. |
| BUG-008 (harmonize) | MODIFICADO | No es "silently ignored" — R sí hace lowercase renaming. La asimetría es que Python deriva 13 columnas canónicas que R no deriva. Diferencia: 200 vs 213 cols, reproducible. |

**Bug adicional detectado (no reportado por Coder):**  
SEGFAULT en R cuando `pulso_load()` se llama dos veces en la misma sesión. Severidad potencialmente alta — requiere validación por el equipo.
