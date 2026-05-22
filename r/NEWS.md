# pulso 0.1.0

## Initial Release

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

### Known Limitations

* Curator entries in variable_map.json are theoretical mappings pending empirical
  verification against DANE microdata. Use `has_warning` column from
  `pulso_list_variables()` to identify entries that need verification.
* Nested-zip periods (2024-03, 2024-04) raise `pulso_parse_error` with a v0.2.0
  deferral notice.
* Shape A 2020-06 variant (single CSV with CLASE column) not yet supported.
* Mixed-level merges (persona + hogar in same `pulso_load_merged()` call) deferred
  to v0.2.0.
