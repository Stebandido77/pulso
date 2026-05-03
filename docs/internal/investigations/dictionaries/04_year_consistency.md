# Verificación cruzada — consistencia entre años

**Fecha:** 2026-05-03
**Años inspeccionados:** 2008, 2015, 2018, 2021 (sample representativo)
**Método:** WebFetch sobre landing + DDI XML, sin descargar zips de microdata

## Tabla resumen

| Año | catalog ID | Zip anual? | Zips mensuales | Diccionario formato | DDI XML disponible | Notas |
|----:|-----------:|:----------:|:---------------|---------------------|:-----:|-------|
| 2008 | 206 | NO (hay extra `total_2008_c.zip`) | 12 mensuales + total trimestral | DDI XML únicamente (sin Diccionario separado) | sí (>10 MB) | Estructura "época A" con desglose trimestral; DDI muy grande |
| 2015 | 356 | NO | 12 mensuales | DDI XML únicamente | sí | Estructura "época A" estable |
| 2018 | 547 | NO | 12 mensuales | DDI XML únicamente | sí (4.5 MB, 1302 vars) | Marco muestral cambia, DDI sigue uniforme |
| 2021 | 701 | NO | 12 mensuales | DDI XML únicamente | sí | Transición a "época B" — archivos consolidados |
| 2024 | 819 | NO | 12 mensuales | DDI XML + Diccionario ZIP separado | sí (1.8 MB, 760 vars) | Primera vez que se publica diccionario separado |
| 2026 | 900 | NO | 2 mensuales (en curso) | DDI XML + Diccionario XLSX directo | sí | Año en curso, lag ~6 sem |

## Las dos épocas

### Época A: 2006–2020

- ~24 archivos por mes (8 temas × 3 cortes geográficos: Área / Cabecera / Resto)
- 2007–2008 además incluyen un desglose trimestral, llevando el conteo
  a ~50 archivos.
- DDI XML mantiene la misma forma — solo cambia el número de
  `<fileDscr>`.

### Época B: 2021–presente

- 8 archivos por mes (consolidados, sin corte geográfico)
- DDI XML con 8 `<fileDscr>` por mes.
- El cambio de marco muestral en 2018 NO crea una época nueva en términos
  de estructura de archivos — la consolidación a 8 ocurre en 2021.

`pulso/data/sources.json` ya distingue `geih_2006_2020` vs
`geih_2021_present`. Esa partición coincide con las épocas observadas.

## H5 revisitado

**No hay zip anual en ningún año.** La pregunta "¿persisten las URLs
mensuales después del anual?" es N/A. Las URLs mensuales son la
entrega canónica permanente. Verificado spot-check:
- GEIH-2008 (catalog 206) sigue listando los 12 meses en
  get-microdata, accesibles.
- GEIH-2024 (catalog 819) **no** muestra ningún anual, solo los 12
  mensuales.

## H3 — veredicto detallado

**Mixto, pero manejable:**

- **2 épocas detectables** por número de archivos por mes (24 vs 8).
- **DDI XML uniforme** en estructura (mismo namespace, mismas tags
  `<var>`, `<catgry>`, `<location>`, `<qstn>`).
- **Tamaño del DDI varía** mucho con la época (1.8 MB en 2024,
  4.5 MB en 2018, >10 MB en 2008).
- **Conteo de variables varía** (760 en 2024, 1302 en 2018) — refleja
  la cantidad de cortes y disposiciones, no del cuestionario.

Implicación para el parser: una sola implementación de `parse_ddi`
funciona para todos los años. No se necesita un parser por época.

## File IDs (`Fxx`) y Variable IDs (`Vxxxx`) — no estables entre años

Confirmado: los IDs internos del DDI cambian año a año.

| Año | Rango de file IDs | Rango aproximado de variable IDs |
|----:|-------------------|----------------------------------|
| 2024 | F63–F70 | V3990 y vecinos |
| 2018 | F255–F279 | distinto al de 2024 |
| 2026 | F1–F8 | reseteado |

**Implicación:** `variable_map.json` debe estar keyed por
`(year, var_name)` o `(epoch, var_name)`, **nunca** por el ID
interno (`Vxxxx` o `Fxx`) del DDI.

## Conclusión

- H3 mixto pero el "mixto" no impide un parser único.
- H5 N/A — la lógica de fallback no se necesita.
- Los 20 años son cubribles uniformemente vía DDI XML.
