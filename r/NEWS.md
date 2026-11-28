# pulso (development version)

## Novedades

* `pulso_trm()`: TRM certificada por la Superintendencia Financiera, un
  registro por día, con la misma interfaz de `pulso_tpm()` (snapshot incluido
  hasta 2026-11-30 y llamada en vivo con fallback) (#90).
* `pulso_load()` acepta `columns =`: lee solo esas columnas del archivo
  (`data.table::fread(select =)`) y conserva siempre las llaves de merge
  (#86).
* Con el paquete 'arrow' instalado (ahora en Suggests), `pulso_load()` guarda
  el módulo ya parseado en parquet dentro de la caché de pulso. La siguiente
  carga del mismo periodo y módulo no vuelve a leer el zip. Sin 'arrow' no
  cambia nada.
* `pulso_clear_cache()` borra la caché: los zips (`"raw"`), los parquet
  (`"parsed"`) o ambos.
* `pulso_indicadores()` calcula TD, TO y TGP (y los niveles de PET, FT,
  ocupados y desocupados) por dominio, mensual o de trimestre móvil, con las
  definiciones del DANE. Coincide con el anexo del DANE. Solo estimación
  puntual: los microdatos públicos no traen variables de diseño (#88).
* `pulso_load_range(start, end, module)` carga meses consecutivos con una
  columna `periodo`. Avisa si el rango mezcla los marcos censales 2005 y 2018.
  Con `average_weights = TRUE` agrega `peso_expansion_promedio` (factor / número
  de meses), que reproduce los niveles del trimestre móvil del DANE (#87).

## Correcciones

* `pulso_load()` detecta los zips anidados del DANE con nombres variantes:
  `CSV 4.zip` (2022-10), `DTA 9.zip` (2023-04), `DAT.zip` (2023-08) y
  `CSV 13.zip` (2023-09). Antes solo reconocía `CSV.zip`, `DTA.zip` y
  `SAV.zip` (#75).
* Los archivos nacionales de 2020 (Shape C) con errores de tipeo del DANE ya
  se encuentran: `Descupados`, `Desoucpados`, `Ianctivos`, `Inativos` y
  `Fuerzo de trabajo` (#75).

## Datos

* 235 de los 237 periodos del catálogo quedan validados contra el DANE (antes
  193). Diferencia máxima: 0,004595 pp (2011-07). Faltan 2020-03 y 2020-04: el
  DANE no publicó los módulos de desocupados ni de inactivos de esos meses.
* 2008 y 2011 se descargan ahora de los `Mes_txt.zip` del DANE. Los CSV que se
  usaban traían el factor de expansión sin punto decimal (#74).
* Los microdatos de 2020 vienen con factores retroproyectados al censo 2018:
  no son comparables con 2019 ni con 2021.

# pulso 0.2.1

## Datos

* 191 de los 237 periodos del catálogo quedan validados (antes 5): TD, TO y
  TGP calculados con pulso coinciden con el anexo oficial del DANE con
  diferencias de 0,000049 pp o menos. Los 46 restantes no cargan en Python
  y siguen sin validar (issues #74 a #76). El detalle está en
  `data/reference/` del repositorio.
* El esquema de `sources.json` acepta `validated_by: "auto:validate_periods.py"`
  para los periodos validados automáticamente contra las cifras oficiales del
  DANE. `pulso_validation_status()` lo devuelve tal cual en `validated_by`.

## Mantenimiento

* Validación automática de periodos (scripts en `python/scripts/`, la lógica
  vive en Python y R solo consume `sources.json`): se calculan TD, TO y TGP
  nacionales ponderados y se comparan con el anexo de mercado laboral del DANE
  de la misma época (marco 2005 hasta 2021-12, marco 2018 desde 2022-01).
* Nuevo workflow `dane_smoke.yml`: cada lunes carga con `pulso_load()` el
  último periodo del catálogo y 2024-03 desde el DANE real, verifica filas,
  `FEX_C18` numérico y ausencia de mojibake, y abre un issue
  `dane-format-change` si algo falla.

# pulso 0.2.0

## Datos

* El catálogo incluido (`sources.json`) cubre ahora hasta septiembre de 2026
  (antes llegaba a febrero de 2026): se agregan 2026-03 a 2026-09 del
  catálogo DANE 900 y se corrigen los tamaños de 2026-01 y 2026-02.
* `pulso_data_not_available` indica hasta qué periodo llega el catálogo.

## Cambios de comportamiento

* `pulso_load()` y `pulso_load_merged()` cargan por defecto los periodos no
  validados, con una advertencia por periodo y sesión (paridad con
  'pulso-co'). Antes fallaban con `pulso_data_not_validated` en 225 de 230
  periodos justo después de instalar el paquete.
* Nuevo argumento `strict`; `allow_unvalidated` queda deprecado
  (`allow_unvalidated = FALSE` equivale a `strict = TRUE`).

## Correcciones

* Nombres de archivo dentro de los zip del DANE: se decodifican por entrada
  (CP437 o UTF-8, que el DANE mezcla en el mismo zip desde 2024-11). Antes
  los módulos con tildes (`caracteristicas_generales`, `migracion`) fallaban
  en todas las versiones recientes, y en locale C fallaban todos.
* Se toleran espacios no separables (U+00A0, desde 2025-12), extensiones en
  minúscula (`.csv`, desde 2026-08) y archivos renombrados (2026-04,
  "Capítulos de características generales..."), con búsqueda por palabra
  clave como último recurso. El error de archivo faltante lista los CSV
  presentes en el zip.
* Se leen los periodos con zip anidado (`CSV.zip`, 2024-03 y 2024-04).
* El texto en Latin-1 se convierte a UTF-8. El separador decimal se detecta
  en cada archivo: los CSV del marco 2018 usan `;` con punto (`43.55418099`)
  y los antiguos `;` con coma, así que `FEX_C18` y demás columnas decimales
  quedan numéricas en ambos casos (#77).
* Cuando el mismo archivo viene en `.csv`, `.dta` y `.sav`, gana la extensión
  pedida (#78).
* Descargas atómicas: se escriben a un archivo temporal y solo pasan a la
  caché si son un zip válido. Un zip corrupto en caché se descarta y se
  descarga de nuevo. La clave de caché incluye la URL, así que una
  republicación del DANE no reutiliza la copia vieja. Se agregan timeout
  (`options(pulso.timeout)`), reintentos, user agent y la opción
  `pulso.cache_dir`.
* Nueva condición `pulso_download_error` (subclase de `pulso_parse_error`).

# pulso 0.1.1

* Fix: corregido nombre de columna en ejemplo de `pulso_describe_column`
  (`P6020` → `P6430`); ejemplos con descarga de red envueltos en
  `if (interactive())` para cumplir política CRAN de `\donttest`.

# pulso 0.1.0

## Initial CRAN release

pulso provides programmatic access to microdata from Colombia's Gran Encuesta
Integrada de Hogares (GEIH), published monthly by DANE.

### Functions

Loading data:

* `pulso_load()` -- download and parse a single GEIH module
* `pulso_load_merged()` -- download and merge multiple persona-level modules

Column metadata:

* `pulso_describe_column()` -- describe a single column in loaded data
* `pulso_list_columns_metadata()` -- list metadata for all columns in a tibble

Catalog and validation:

* `pulso_list_validated_range()` -- list periods with verified downloads
* `pulso_validation_status()` -- validation info for a specific period

Module and variable discovery:

* `pulso_describe()` -- describe a survey module
* `pulso_describe_variable()` -- describe a canonical variable and its epoch mappings
* `pulso_list_variables()` -- list canonical variables, optionally filtered by module

Banco de la República data:

* `pulso_tpm()` -- download the monetary policy rate (TPM) set by Banco de la República, with automatic fallback to a bundled snapshot when the live SDMX API is unavailable

### Bug fixes (pre-CRAN)

* **BUG-003/010:** Fixed Unicode filename handling. Modules with tildes
  (caracteristicas_generales, migracion) now load correctly on all
  platforms including macOS and Windows. Uses base `unz()` connection
  to read CP437-encoded zip entries without writing to disk.
* **BUG-004:** Fixed epoch1 column variance crash. `dplyr::bind_rows()`
  replaces `rbind()` to handle Cabecera/Resto CSVs with type-mismatched
  shared columns. Affects 2007-2021 (14 years of data).
* **BUG-005:** Auto-detect CSV separator. `data.table::fread(sep="auto")`
  replaces `read.csv(sep=";")` to handle period-specific delimiters.
  Affects 2022-01.
* **BUG-006:** `pulso_load()` now raises `pulso_data_not_validated` by
  default for unvalidated periods. Pass `allow_unvalidated = TRUE` to
  load with a visible warning. Currently 5 periods are validated:
  2007-12, 2015-06, 2021-12, 2022-01, 2024-06.
* **BUG-011:** Vignettes are pre-built in the package tarball.
* **BUG-017:** Keyword matcher now accepts numeric suffixes in filenames
  (e.g., `Ocupados06.csv`). Affects 2013-06.
* **BUG-018:** Added Shape C dispatch for COVID-period single-CSV
  variants. Affects 2020-06 and 2020-12.
* **BUG-NEW-001:** Skip adding synthetic `CLASE` column when the DANE
  CSV already contains one (case-insensitive check). Prevents duplicate-
  column error on `tibble::as_tibble()`. Affects 2014-06, 2015-06, and
  other periods where DANE encodes `clase` directly in Cabecera/Resto CSVs.

### Known Limitations

* Only 5/230 periods are explicitly validated. Use
  `allow_unvalidated = TRUE` for the rest.
* Variable map (Curator) entries have `comparability_warning` flag.
  Use `pulso_list_variables()` to see `has_warning` column.
* Nested-zip periods (2024-03, 2024-04) raise `pulso_parse_error` with
  a v0.2.0 deferral notice.
* ECH epoch (2000-2006) not yet supported. Planned for v0.2.0.
* Mixed-level merges (persona + hogar in same `pulso_load_merged()` call)
  deferred to v0.2.0.
* Banco de la República integration currently covers the policy rate (`pulso_tpm()`) only. The Indicador Bancario de Referencia (IBR) and a generic SDMX accessor are deferred to v0.2.0.
