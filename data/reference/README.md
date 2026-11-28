# Validación automática contra el DANE

Artefactos de mantenimiento. No viajan en el wheel ni en el paquete R.

| Archivo | Qué es | Lo genera |
|---|---|---|
| `dane_labor_indicators.csv` | TD, TO y TGP mensuales del Total Nacional publicados por el DANE | `python/scripts/fetch_dane_reference.py` |
| `validation_results.csv` | TD, TO y TGP calculados con pulso, comparados con el DANE, uno por periodo del catálogo | `python/scripts/validate_periods.py` |

## Cifras oficiales de referencia

Descargadas el 2026-11-26 (`retrieved_at = 2026-11-26T13:51:39Z`).

| Época del catálogo | Periodos | Anexo | Hoja |
|---|---|---|---|
| `geih_2006_2020` (marco 2005) | 2006-01..2021-12 | https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/anexo_empleo_dic_21.xlsx | `Tnal mensual` |
| `geih_2021_present` (marco 2018) | 2022-01..2026-09 | https://www.dane.gov.co/files/operaciones/GEIH/anex-GEIH-sep2026.xlsx | `Total nacional` |

**Por qué dos anexos.** El anexo vigente trae la serie desde 2001, pero dice: "los datos entre 2001 y 2020 se encuentran con los valores retroproyectados a partir de las proyecciones del CNPV 2018" y "la PET corresponde a todas las personas de 15 años y más". Los microdatos del catálogo hasta 2021-12 son marco 2005 (`fex_c_2011`, PET 12+ urbano / 10+ rural), así que se comparan con el último anexo publicado en ese marco ("Datos expandidos con proyecciones de población, elaboradas con base en los resultados del censo 2005", actualizado el 31 de enero de 2022). Con el anexo vigente, 2015-06 daría TGP 64,41 (pulso) contra 67,31 (anexo): esa diferencia viene del anexo, no de pulso.

**Excepción: 2020.** Los microdatos de 2020 (catálogo 780 del DANE) ya traen los factores de expansión retroproyectados al CNPV 2018, aunque `epochs.json` los ubique en `geih_2006_2020`. Calculados con pulso, coinciden con el anexo vigente en sus cuatro decimales publicados (2020-01: TD 13,4585 / TO 55,3277 / TGP 63,9319) y no con `anexo_empleo_dic_21.xlsx` (12,9880 / 54,3707 / 62,4864). 2019 (catálogo 599) y 2021 (catálogo 701) sí coinciden con el anexo del marco 2005. Por eso `fetch_dane_reference.py` toma 2020-01..2020-12 del anexo vigente (`MICRODATA_ON_2018_FRAME`). Las 12 filas de 2020 se reemplazaron el 2026-11-28; las demás no cambiaron.

**Alcance.** El catálogo empieza en 2007-01 y los dos anexos cubren todos sus meses. No queda ningún periodo `pending`. La ECH (2000–2006) no está en el catálogo.

**Cobertura geográfica.** Se compara contra el Total Nacional del anexo, no contra "13 ciudades", porque los microdatos son nacionales (Cabecera + Resto en la época 2005; un único archivo nacional en la 2018).

### Verificación manual contra los boletines técnicos

| Mes | Boletín | Boletín TD / TGP / TO (%) | Anexo TD / TGP / TO | pulso TD / TGP / TO |
|---|---|---|---|---|
| 2015-06 | [bol_empleo_jun_15.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/bol_empleo_jun_15.pdf) | 8,2 / 64,4 / 59,1 | 8,245788 / 64,409526 / 59,098453 | 8,245787 / 64,409525 / 59,098453 |
| 2021-12 | [bol_empleo_dic_21.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/bol_empleo_dic_21.pdf) | 11,0 / 59,8 / 53,2 | 11,006662 / 59,780808 / 53,200936 | 11,006662 / 59,780808 / 53,200936 |
| 2025-03 | [bol-GEIH-mar2025.pdf](https://www.dane.gov.co/files/operaciones/GEIH/bol-GEIH-mar2025.pdf) | 9,6 / 64,7 / 58,5 | 9,616369 / 64,729495 / 58,504869 | 9,616369 / 64,729495 / 58,504869 |

Texto de los boletines: "la tasa de desempleo fue 8,2 %", "La tasa global de participación fue 64,4 %", "La tasa de ocupación fue 59,1 %" (junio 2015); "Para el mes de diciembre de 2021, la tasa de desempleo fue 11,0% ... La tasa global de participación se ubicó en 59,8% ... la tasa de ocupación fue 53,2%"; "Para el mes de marzo de 2025, la tasa de desocupación del total nacional fue 9,6% ... La tasa global de participación se ubicó en 64,7% ... la tasa de ocupación fue 58,5%".

## Cómo calcula pulso

TGP = FT / PET, TO = OC / PET, TD = DS / FT, ponderados con el factor de expansión de `variable_map.json` (`peso_expansion`: `FEX_C` en la época 2005, `FEX_C18` en la 2018).

Desde W2 (#85, #79), todo sale de `variable_map.json`, por el mismo camino que usa cualquier usuario: `pulso.load_merged(año, mes, modules=["caracteristicas_generales", ...módulos de fuerza de trabajo], harmonize=True, variables=["pet", "fuerza_trabajo", "condicion_actividad", "peso_expansion"])`.

| Variable | Marco 2005 (`geih_2006_2020`) | Marco 2018 (`geih_2021_present`, y 2020) | Fuente |
|---|---|---|---|
| `pet` | `P6040` ≥ 12 en cabecera (`CLASE` = 1) y ≥ 10 en centro poblado y rural disperso (`CLASE` 2 o 3) | `P6040` ≥ 15 | [DANE, boletín de educación 2018](https://www.dane.gov.co/files/investigaciones/boletines/especiales/educacion/Bol_edu_2018.pdf); [DANE, boletín GEIH 2024](https://www.dane.gov.co/files/operaciones/GEIH/bol-GEIHFLE-2024.pdf) |
| `condicion_actividad` | `OCI` / `DSI` / `INI` = 1 en Ocupados / Desocupados / Inactivos | `OCI` = 1 en Ocupados; `DSI` = 1 y `FFT` = 1 en No ocupados | diccionarios GEIH |
| `fuerza_trabajo` | ocupado o desocupado (mismas banderas) | ídem | DANE: FT = OC + DS |

Verificación de la regla de la PET con microdatos: coincide exactamente (0 discrepancias) con la pertenencia al módulo Fuerza de trabajo, que el DANE solo aplica a la PET. La regla 12/10 da 0 discrepancias en 2015-06 y 2021-06; la de 15+, 0 en 2020-06, 2024-06 y 2026-09. Por eso **2020 usa 15+** aunque su época sea `geih_2006_2020` (`frame_2018_periods` en el mapeo).

El script cuenta las inconsistencias entre definiciones (personas en FT fuera de la PET, personas de la PET sin condición de actividad) y las escribe en `notes`. En la época 2018, `FEX_C18` puede llegar como texto ([#77](https://github.com/Stebandido77/pulso/issues/77)): el script lo convierte y lo anota como `weight_coerced_from_text`.

Tolerancia: máx. |pulso − DANE| ≤ 0,1 pp en los tres indicadores es `pass`; ≤ 0,5 pp es `review`; más es `fail`. `error` significa que el periodo no cargó.

## Resultado de la corrida completa (2026-11-26, los 237 periodos)

```
237 periodos en rango; 0 ya calculados; 237 por calcular con 4 worker(s)
Tiempo total: 50.4s            (caché caliente; la primera corrida, que descargó los 237 zip, tardó 216.5s)
Conteo por status: {"error": 46, "pass": 191}
```

- **191 `pass`**, con diferencia máxima de **0,000049 pp** (2022-01). Las diferencias vienen del redondeo del anexo; no hay ningún `review` ni `fail`.
- Los 5 periodos que ya estaban validados (2007-12, 2015-06, 2021-12, 2022-01, 2024-06) siguen en `pass`. Ninguno cambió de estado.
- **46 `error`**: ninguno es una diferencia numérica. Todos son periodos que pulso (Python) no logra cargar:

| Periodos | n | Causa diagnosticada | Tipo | Issue |
|---|---|---|---|---|
| 2008-01..03 | 3 | `.txt` separados por tabulador **sin encabezado**: la primera fila de datos se toma como nombres de columna | formato DANE + parser | [#74](https://github.com/Stebandido77/pulso/issues/74) |
| 2008-04..12, 2011-01..12 | 21 | CSV con coma y texto libre sin comillas que contiene comas (3–10 filas de ~25.000) | formato DANE + parser | [#74](https://github.com/Stebandido77/pulso/issues/74) |
| 2013-04..06 | 3 | Nombres con sufijo de mes (`Ocupados05.csv`) que la regex de palabra clave no reconoce (R ya lo resuelve, BUG-017) | parser (paridad) | [#75](https://github.com/Stebandido77/pulso/issues/75) |
| 2020-01..12 | 12 | Archivo nacional único (`CSV/Ocupados.CSV`), pero `sources.json` declara Cabecera/Resto (R ya lo resuelve, BUG-018) | parser / catálogo | [#75](https://github.com/Stebandido77/pulso/issues/75) |
| 2022-10, 2023-04, 2023-08, 2023-09 | 4 | Zip anidado con nombres variantes (`CSV 4.zip`, `DTA 9.zip`, `DAT.zip`) que no se detectan | parser | [#75](https://github.com/Stebandido77/pulso/issues/75) |
| 2024-03 | 1 | `No ocupado.CSV` (singular) dentro de `CSV.zip`; el catálogo declara `No ocupados.CSV` | parser / catálogo | [#75](https://github.com/Stebandido77/pulso/issues/75) |
| 2026-08, 2026-09 | 2 | `DSI` pasó a 0/1 (antes 1/vacío); `merge_labor_status` deja ~21.000 personas sin condición | cambio de formato DANE + armonizador | [#76](https://github.com/Stebandido77/pulso/issues/76) |

## Corrida completa del 2026-11-28 (v3, W2: definiciones de `variable_map`)

```
Tiempo total: 124.3s
Conteo por status: {"error": 2, "pass": 235}
```

- PET, FT, OC y DS salen de `pet`, `fuerza_trabajo` y `condicion_actividad` de `variable_map.json`, a través de `load_merged(..., harmonize=True)` (#101).
- **235 `pass`**, con diferencia máxima de **0,000049 pp**. 2011-07 baja de 0,004595 a 0,000002 pp con la PET explícita. Ninguna inconsistencia entre definiciones y ninguna regresión.
- **2020-03 y 2020-04 (`error`). Diagnóstico:** el DANE publicó solo Características generales, Fuerza de trabajo y Ocupados, sin desocupados ni inactivos. Con PET de 15+ y `OCI`, la TO coincide exacta (2020-03: 52,4500 contra 52,45; 2020-04: 42,4971 contra 42,4971). TD y TGP necesitan a los desocupados. En el archivo de Fuerza de trabajo de esos meses, `Ft` vale 1 para toda la PET, así que no sirve como bandera de FT. La alternativa sería derivar la desocupación de las preguntas del cuestionario, y eso queda como decisión pendiente.

## Corrida completa del 2026-11-28 (v3, W1)

```
Tiempo total: 218.8s
Conteo por status: {"error": 2, "pass": 235}
```

- **235 `pass`**. La diferencia máxima es **0,004595 pp** (2011-07, TGP); en el resto es de 0,000049 pp o menos. No hay regresiones: los 193 periodos que ya estaban validados siguen en `pass`.
- Cargan los 42 periodos nuevos gracias a #97 (estructuras de zip), #98 (referencia de 2020) y #99 (txt tabulados y clave de caché).
- **2008 y 2011**: el catálogo apunta ahora a los `Mes_txt.zip` del DANE (catálogos 206 y 182). Los CSV que usaba traían `fex_c_2011` sin punto decimal en todas las filas (`730.787.704.198.798`), y eso no se puede reparar.
- **2 `error`**: 2020-03 y 2020-04. El DANE no publicó los módulos Desocupados ni Inactivos para esos meses. Se validan cuando FT y PET salgan de variables (W2, #85).

Para regenerar todo:

```
python python/scripts/fetch_dane_reference.py
python python/scripts/validate_periods.py --workers 4      # --resume para seguir por lotes
python python/scripts/apply_validation.py --report validation_report.md
```
