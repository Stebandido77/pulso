# Catalog URLs por año (GEIH 2007–2026)

**Fuente:** scraping del catálogo `https://microdatos.dane.gov.co`
**Fecha verificación:** 2026-05-03

## Mapa completo

| Año | catalog ID | URL | Status |
|----:|-----------:|-----|:------:|
| 2007 | 317 | https://microdatos.dane.gov.co/index.php/catalog/317 | 200 |
| 2008 | 206 | https://microdatos.dane.gov.co/index.php/catalog/206 | 200 |
| 2009 | 207 | https://microdatos.dane.gov.co/index.php/catalog/207 | 200 |
| 2010 | 205 | https://microdatos.dane.gov.co/index.php/catalog/205 | 200 |
| 2011 | 182 | https://microdatos.dane.gov.co/index.php/catalog/182 | 200 |
| 2012 |  77 | https://microdatos.dane.gov.co/index.php/catalog/77  | 200 |
| 2013 |  68 | https://microdatos.dane.gov.co/index.php/catalog/68  | 200 |
| 2014 | 328 | https://microdatos.dane.gov.co/index.php/catalog/328 | 200 |
| 2015 | 356 | https://microdatos.dane.gov.co/index.php/catalog/356 | 200 |
| 2016 | 427 | https://microdatos.dane.gov.co/index.php/catalog/427 | 200 |
| 2017 | 458 | https://microdatos.dane.gov.co/index.php/catalog/458 | 200 |
| 2018 | 547 | https://microdatos.dane.gov.co/index.php/catalog/547 | 200 |
| 2019 | 599 | https://microdatos.dane.gov.co/index.php/catalog/599 | 200 |
| 2020 | 780 | https://microdatos.dane.gov.co/index.php/catalog/780 | 200 |
| 2021 | 701 | https://microdatos.dane.gov.co/index.php/catalog/701 | 200 |
| 2022 | 771 | https://microdatos.dane.gov.co/index.php/catalog/771 | 200 |
| 2023 | 782 | https://microdatos.dane.gov.co/index.php/catalog/782 | 200 |
| 2024 | 819 | https://microdatos.dane.gov.co/index.php/catalog/819 | 200 |
| 2025 | 853 | https://microdatos.dane.gov.co/index.php/catalog/853 | 200 |
| 2026 | 900 | https://microdatos.dane.gov.co/index.php/catalog/900 | 200 |

20/20 años accesibles. Cobertura completa.

## Observaciones

- Los IDs **no son monotónicos** con el año: 2014 (328) viene antes que
  2007 (317) por orden de creación, y 2007 viene mucho después que 2008
  (206) o 2012 (77). Esto refleja órdenes de catalogación interna del
  DANE, no la cronología del estudio.
- No hay un patrón derivable año→ID. El mapa debe vivir como tabla
  estática en `pulso/data/sources.json` (donde ya vive) o en un módulo
  de constantes.
- Todas las URLs siguen el patrón
  `https://microdatos.dane.gov.co/index.php/catalog/{id}` con tabs:
  - `/catalog/{id}` — landing page
  - `/catalog/{id}/get-microdata` — descargas mensuales
  - `/catalog/{id}/related-materials` — materiales relacionados
  - `/catalog/{id}/data-dictionary` — diccionario navegable (HTML)
  - `/metadata/export/{id}/ddi` — DDI XML estructurado (la fuente que
    importa)
  - `/metadata/export/{id}/json` — metadata JSON metodológica (sin variables)

## Fechas creación / modificación

No se capturó la fecha exacta de creación de cada catalog porque
quedó parcialmente fuera del scope tras descubrir que H5 no aplica
(no hay zip anual). En la implementación, si se necesita, está
expuesta en el HTML de cada landing page bajo
`Última modificación` / `Created on`.

## Comparación con `sources.json` actual de pulso

El archivo `pulso/data/sources.json` (rc2) ya enumera los 20 años con
sus 230 meses. Los IDs encontrados aquí coinciden con los que usa el
loader actual (verificado spot-check para 2018, 2021, 2024).
