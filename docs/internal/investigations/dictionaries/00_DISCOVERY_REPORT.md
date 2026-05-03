# Discovery Report: Catálogo del DANE para v1.0.0 metadata

**Fecha:** 2026-05-03
**Status:** COMPLETO — Esperando aprobación humana
**Agente:** Agente 1 (discovery, no-code)
**Branch:** `feat/v1.0.0-metadata`

## Resumen ejecutivo

El catálogo del DANE es uniformemente accesible para los 20 años 2007–2026
(todos `HTTP 200`). **H1 queda refutado**: ningún año cerrado entrega un
zip anual — todos los años entregan 12 zips mensuales como única forma
canónica de descarga. **El hallazgo grande es real**: el endpoint
`/metadata/export/{catalog_id}/ddi` devuelve un codeBook DDI 1.2.2
totalmente estructurado con cada variable (`<var>`), sus categorías
(`<catgry>/<catValu>/<labl>`), texto de pregunta, universo y notas, en XML
parseable por `lxml`. **Esto elimina la necesidad de parsear PDFs** y
reduce el alcance del feature de metadata de 7–10 días a 3–4 días.

## Hipótesis verificadas

### H1: El DANE entrega 1 zip anual por año cerrado
- **Veredicto:** REFUTADO
- **Evidencia:** GEIH-2024, 2025, 2021, 2018 y 2015 muestran 12 zips
  mensuales en `get-microdata`, sin zip anual. 2007–2008 incluyen además
  un `total_YYYY_c.zip` complementario, pero la entrega canónica sigue
  siendo mensual. La estructura mensual ya cubierta por `sources.json`
  de pulso rc2 (230 entradas) coincide.
- **Implicación:** El "modelo híbrido" que motivaba este discovery no es
  necesario porque el lado "anual" no existe en DANE. pulso debe
  mantener su downloader mensual; la simplificación es enorme.

### H2: El diccionario es anual, no mensual
- **Veredicto:** CONFIRMADO Y MEJORADO
- **Formato encontrado:** DDI 1.2.2 XML (machine-readable codeBook), un
  archivo por año, vía `https://microdatos.dane.gov.co/index.php/metadata/export/{catalog_id}/ddi`.
  Adicionalmente, desde 2024 DANE publica un "Diccionario de datos"
  separado (2024: ZIP 242 KB, 2026: XLSX 347 KB directo). En 2018 y
  anteriores no existe ese archivo separado, **pero el DDI XML siempre
  está disponible y contiene todo**.
- **Calidad parsing:** Excelente. Estructura jerárquica con namespace
  `http://www.icpsr.umich.edu/DDI`, no requiere OCR ni PDF parsing.
  Verificado en muestras: 760 variables en 2024, 1302 en 2018, todas
  con `<location>`, `<labl>`, `<qstn><qstnLit>`, `<universe>`,
  `<sumStat>` y la lista completa de `<catgry>`.

### H3: Estructura uniforme entre años
- **Veredicto:** MIXTO — dos épocas, uniformes dentro de cada una
- **Épocas detectadas:**
  - **Época A (2006–2020):** archivos divididos por geografía
    Área/Cabecera/Resto × 8 temas ≈ 24 archivos por mes (50 en 2008
    por desglose trimestral).
  - **Época B (2021–presente):** archivos unificados, 8 temas por mes.
- El patrón de URL, el endpoint DDI y el mecanismo de descarga son
  uniformes en **ambas** épocas. pulso ya codifica `geih_2006_2020` vs
  `geih_2021_present` en `sources.json`.

### H4: El año en curso publica mensualmente
- **Veredicto:** CONFIRMADO
- **Meses 2026 publicados:** Enero (release 2026-03-16) y Febrero
  (release 2026-04-13). Marzo y Abril 2026 no están publicados al
  2026-05-03.
- **URLs accesibles:** sí, mismo patrón `/catalog/900/download/{file_id}`.
- **Lag observado:** ~6 semanas entre fin de mes referenciado y release
  del DANE.

### H5: URLs mensuales persisten después del anual
- **Veredicto:** N/A — no existe zip anual, por lo tanto la pregunta
  desaparece. Las URLs mensuales son la entrega canónica permanente
  para todos los años verificados.
- **Implicación para fallback:** No se necesita lógica de fallback
  anual→mensual. El downloader siempre es mensual.

## Hallazgo crítico

**El DANE expone metadata estructurada DDI/XML por año:**

- Endpoint: `https://microdatos.dane.gov.co/index.php/metadata/export/{catalog_id}/ddi`
- Content-Type: XML (DDI 1.2.2, namespace ICPSR)
- Tamaños verificados: 2024 ≈ 1.8 MB / 760 vars; 2018 ≈ 4.5 MB / 1302 vars;
  2008 >10 MB (en producción descargar por streaming, no `requests.get` directo).
- Cada `<var ID="Vxxxx" name="Pxxxx" files="Fxx">` incluye:
  `<location>` (posiciones byte), `<labl>`, `<security>`, `<respUnit>`,
  `<qstn><qstnLit>` (texto de la pregunta), `<universe>`, `<sumStat>`,
  y la lista completa de
  `<catgry><catValu>code</catValu><labl>label</labl></catgry>`.

**Implicación:** el `variable_map` de pulso puede auto-construirse
parseando un DDI por año con `lxml`. Sin parser de PDF, sin parser de
Excel, sin transcripción manual.

> Nota menor: en el DDI de 2024 el `<titl>` dice
> "GRAN ENCUESTA INTEGRADA DE HOGARES 2016 metodologia" mientras que
> `<IDNo>` correctamente dice `COL-DANE-GEIH-2024`. DANE reusa títulos
> entre versiones — no usar `<titl>` como fuente de año, usar `<IDNo>`
> o el `catalog_id`.

## JSON export descartado

`https://microdatos.dane.gov.co/index.php/metadata/export/{catalog_id}/json`
existe pero contiene solo metadata metodológica (productor, fechas,
descripción). **No contiene variables.** Usar el DDI/XML, no el JSON.

## Estructura por año (resumen)

20 IDs de catálogo encontrados, todos `HTTP 200`. Mapeo completo en
`01_catalog_urls.md`. Resumen:

```
2007=317  2008=206  2009=207  2010=205  2011=182  2012=77
2013=68   2014=328  2015=356  2016=427  2017=458  2018=547
2019=599  2020=780  2021=701  2022=771  2023=782  2024=819
2025=853  2026=900
```

Detalle por época en `04_year_consistency.md`.

Detalle de IDs internos: el esquema `Fxx` (file IDs) y `Vxxxx`
(variable IDs) **no es estable entre años**. 2024 usa F63–F70, 2018
usa F255–F279, 2026 usa F1–F8. La fuente de verdad por año es el DDI XML.

## Información disponible en diccionarios DDI

Por variable se obtiene:
- Código (`name`, ej. `P6020`)
- Etiqueta corta (`<labl>`)
- Texto literal de pregunta (`<qstn><qstnLit>`)
- Universo (`<universe>`)
- Categorías y valores (`<catgry><catValu>...</catValu><labl>...</labl></catgry>`)
- Posición en archivo (`<location StartPos="..." EndPos="..." width="..."/>`)
- Tipo (numérico/alfa) y precisión
- Estadística resumen (`<sumStat>`)
- Comparabilidad (sección `<verStmt>` cuando existe)

## Estimación de esfuerzo revisada

Plan original: 7–10 días (parser PDF + downloader híbrido + integración).

Plan revisado tras hallazgos:
- Parser DDI con `lxml`: **1 día** (no PDF, no Excel)
- Build-time `variable_map.json` consolidado para 2007–2026: **0.5 día**
- Wiring `load(metadata=True)` con etiquetas/categorías: **1 día**
- Reestructurar downloader híbrido: **0 días** (no se hace, no aplica)
- Fixes pendientes rc2 (ParseError, variable_map, verbosidad): **1 día**

**Total revisado: 3–4 días.**

## Riesgos identificados

1. **DDI grandes 2007–2010** (>10 MB) requieren descarga por streaming;
   `WebFetch` standard cortó en 10 MB. No es bloqueante, solo nota
   técnica para el implementador.
2. **`<titl>` ruidoso** (ej. dice "2016" en el DDI de 2024). Usar
   `<IDNo>` o el `catalog_id` como identificador, nunca `<titl>`.
3. **File IDs (`Fxx`) y Variable IDs (`Vxxxx`) no estables entre años**
   — `variable_map.json` debe estar keyed por `(year, var_name)` o
   `(epoch, var_name)`, no por ID DANE.
4. **2 épocas con conteo de archivos distinto** (24 vs 8). El parser
   debe iterar todos los `<fileDscr>` del DDI, no asumir conteo fijo.
5. **DDI 2008 entregado por DANE pesa >10 MB** — descarga directa OK con
   `requests.iter_content`, pero hay que probar antes de release.

## Decisiones que necesita tomar el usuario

1. **Eliminar el modelo híbrido del plan v1.0.0.** El zip anual no
   existe en DANE; el plan debe revertir a "monthly only, always" y
   `pulso.load(year=2027)` sigue lanzando `DataNotAvailableError`. ¿OK?
2. **Adoptar DDI/XML como única fuente de metadata** (descartar plan
   de PDF parser y de XLSX parser para el "Diccionario de datos"
   separado de 2024+). ¿OK?
3. **Cobertura de años para v1.0.0 metadata.** Recomendado: cubrir
   2007–2026 uniformemente porque todos los años exponen DDI con la
   misma forma. Alternativa más conservadora: 2015–2026 si se quiere
   limitar tamaño del `variable_map.json` empaquetado.

## Recomendación del Agente 1

Reemplazar el plan "downloader híbrido + parser PDF" por un alcance
mucho más pequeño:

1. Añadir módulo `pulso/metadata/` con
   `fetch_ddi(catalog_id) -> Path` (cacheado) y
   `parse_ddi(path) -> dict[var_name, VariableInfo]`. (~1 día)
2. Generar `variable_map.json` precomputado al build, corriendo
   `parse_ddi` sobre los 20 años, keyed por `(epoch, var_name)`. (~½ día)
3. Wiring `load(metadata=True)` para adjuntar etiquetas a columnas y
   categorías a códigos del DataFrame. (~1 día)
4. **Mantener el downloader mensual existente sin cambios.** El plan
   híbrido se basaba en H1 (falsa).
5. Resolver fixes pendientes de rc2 en paralelo (ParseError,
   variable_map regression, verbosidad). (~1 día)

**Total: 3–4 días** vs los 7–10 estimados originalmente.

## Archivos generados

- `00_DISCOVERY_REPORT.md` (este)
- `01_catalog_urls.md` — mapa completo de catalog IDs 2007–2026
- `02_geih_2024_anatomy.md` — anatomía detallada de GEIH-2024
- `03_year_in_progress.md` — estado de GEIH-2026
- `04_year_consistency.md` — verificación cruzada, épocas
- `05_zip_and_dict_anatomy.md` — estructura del DDI XML
- `samples/geih_2024_ddi.xml` — DDI 2024 (1.8 MB, 760 variables)
- `samples/geih_2018_ddi.xml` — DDI 2018 (4.5 MB, 1302 variables)
- `samples/README.md` — descripción de los samples
