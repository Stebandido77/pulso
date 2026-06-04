#' pulso: Load Microdata from Colombia's 'GEIH' ('DANE')
#'
#' R companion to the 'pulso-co' 'Python' package. Provides programmatic
#' access to microdata from Colombia's Gran Encuesta Integrada de Hogares
#' ('GEIH'), published by 'DANE', and to Banco de la Republica monetary
#' policy data.
#'
#' @section Loading microdata:
#' * [pulso_load()] - Load a single GEIH module for a year/month
#' * [pulso_load_merged()] - Load and merge multiple persona-level modules
#'
#' @section Describing columns and variables:
#' * [pulso_describe()] - Describe a survey module
#' * [pulso_describe_column()] - Describe a single loaded column
#' * [pulso_describe_variable()] - Describe a canonical variable and its epoch mappings
#' * [pulso_list_columns_metadata()] - List metadata for all columns in a loaded tibble
#' * [pulso_list_variables()] - List canonical variables, optionally by module
#'
#' @section Catalog and validation:
#' * [pulso_list_validated_range()] - List periods with verified downloads
#' * [pulso_validation_status()] - Validation info for a specific period
#'
#' @section Banco de la Republica:
#' * [pulso_tpm()] - Monetary policy rate (TPM), with offline fallback
#'
#' @section Comparison with Python:
#' This package mirrors the API of the 'pulso-co' 'Python' package. See
#' the package vignette for details.
#'
#' @keywords internal
"_PACKAGE"

## usethis namespace: start
#' @importFrom data.table fread
#' @importFrom dplyr bind_rows
## usethis namespace: end
NULL
