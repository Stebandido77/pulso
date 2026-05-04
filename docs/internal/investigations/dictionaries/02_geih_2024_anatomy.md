# Anatomía de GEIH-2024 (catalog ID 819)

**URL:** https://microdatos.dane.gov.co/index.php/catalog/819
**Fecha inspección:** 2026-05-03

Año cerrado, anual ya publicado. Es el caso de referencia que motivaba
H1 ("zip anual"). Resultado: H1 refutado — no hay zip anual.

## Tabs disponibles

- `/catalog/819` — landing
- `/catalog/819/get-microdata` — descargas
- `/catalog/819/related-materials` — materiales
- `/catalog/819/data-dictionary` — diccionario navegable
- `/catalog/819/variable/{file_id}/{var_id}` — detalle por variable
- `/metadata/export/819/ddi` — DDI XML
- `/metadata/export/819/json` — metadata JSON (sin variables)

## Documentación

Lista de archivos en la sección "Documentación":

| Archivo | Formato | Descarga | Notas |
|---------|---------|----------|-------|
| Diccionario de datos | ZIP (~242 KB) | sí, directa | Excel + PDF dentro |
| Metodología general GEIH | PDF | sí | Documento metodológico |
| Ficha metodológica | PDF | sí | Resumen oficial |
| Manual de recolección | PDF | sí | Para el encuestador |
| Cuestionario | PDF | sí | Instrumento aplicado |

El **Diccionario de datos** ZIP empezó a publicarse de forma separada
desde 2024. Para 2023 y anteriores no existe como archivo separado —
pero el DDI XML siempre está disponible, así que no es bloqueante.

## Microdata (get-microdata)

URL: https://microdatos.dane.gov.co/index.php/catalog/819/get-microdata

**Resultado:** la página lista 12 zips mensuales (Enero a Diciembre 2024),
**no un zip anual**. Cada zip mensual sigue el patrón ya conocido por
pulso rc2:

- URL pattern: `/catalog/819/download/{file_id}`
- File IDs son enteros asignados por DANE (no derivables del año/mes)
- pulso rc2 ya tiene los 12 IDs en `sources.json` para 2024

Dentro de cada zip mensual (Época B, 2021+):
- 8 archivos CSV/SAV/DTA (Características generales, Ocupados, Desocupados, etc.)
- README/leeme corto

No hay un "wrapper" anual. **H1 refutado.**

## Variables

Tab `/catalog/819/data-dictionary` muestra los grupos de archivos
(`F63` … `F70` — 8 archivos) y permite navegar variable por variable.

Ejemplo verificado: `/catalog/819/variable/F63/V3990` corresponde a
**P3271** (`Cuál fue su sexo al nacer?`) con categorías 1=Hombre,
2=Mujer.

## DDI/XML — el descubrimiento clave

URL: `https://microdatos.dane.gov.co/index.php/metadata/export/819/ddi`

- Tamaño: 1,910,047 bytes (~1.8 MB)
- 760 variables (verificado: `grep -c '<var ' = 760`)
- DDI 1.2.2, namespace `http://www.icpsr.umich.edu/DDI`
- Encoding: UTF-8
- ID interno: `DANE-DIMPE-GEIH-2024`
- Curiosidad: el `<titl>` dice "GRAN ENCUESTA INTEGRADA DE HOGARES 2016
  metodologia" (DANE recicla títulos entre versiones). Usar `<IDNo>` y
  el `catalog_id`, no `<titl>`.

Sample copiado a `samples/geih_2024_ddi.xml`.

## URL pattern para metadata exports

Confirmado y reutilizable para todos los años:

```
https://microdatos.dane.gov.co/index.php/metadata/export/{catalog_id}/ddi
https://microdatos.dane.gov.co/index.php/metadata/export/{catalog_id}/json
```

El JSON solo trae metadata metodológica (sin variables). **Para el
codebook hay que usar el DDI XML.**

## Conclusión específica de 2024

- **NO hay zip anual.** 12 zips mensuales como entrega canónica.
- **SÍ hay diccionario estructurado** vía DDI XML (1.8 MB, 760 vars).
- **Hay también un "Diccionario de datos" Excel/PDF** publicado desde
  2024, pero es redundante con el DDI XML — no agrega información
  estructurada.
- pulso rc2 ya descarga los 12 zips correctamente; el único trabajo
  pendiente es **agregar metadata desde el DDI XML**.
