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
