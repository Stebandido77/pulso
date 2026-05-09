#' Load GEIH microdata for a single year-month-module
#'
#' Downloads and parses microdata from Colombia's Gran Encuesta Integrada
#' de Hogares (GEIH), published by DANE. This is the MVP version for
#' v0.1.0 supporting single year/month/module loads.
#'
#' @param year Integer. Year of the survey (e.g., 2024). Must be in
#'   2007 to current year.
#' @param month Integer. Month of the survey (1-12).
#' @param module Character. Module name. Common values: "ocupados",
#'   "vivienda", "caracteristicas_generales", "desocupados", etc.
#' @param area Character or NULL. Optional area filter ("urbano"/"rural").
#'   NULL means all areas. Currently NOT IMPLEMENTED in v0.1.0 (planned
#'   for v0.2.0).
#' @param harmonize Logical. Whether to apply harmonization rules.
#'   Default TRUE. v0.1.0 applies basic type coercion only; full
#'   harmonization in v0.2.0+.
#' @param cache Logical. Whether to cache downloaded data on disk.
#'   Default TRUE. Cache location: tools::R_user_dir("pulso", "cache").
#' @param metadata Logical. Whether to attach DANE metadata to the result.
#'   Default FALSE for Python parity. NOT IMPLEMENTED in v0.1.0 MVP
#'   (planned for v0.2.0).
#'
#' @return A tibble with the microdata.
#'
#' @examples
#' \dontrun{
#' df <- pulso_load(year = 2024, month = 6, module = "ocupados")
#' }
#'
#' @export
pulso_load <- function(year, month, module,
                       area = NULL,
                       harmonize = TRUE,
                       cache = TRUE,
                       metadata = FALSE) {

  .validate_year(year)
  .validate_month(month)
  .validate_module(module)

  if (!is.null(area)) {
    cli::cli_warn(c(
      "{.arg area} is not implemented in v0.1.0 MVP",
      "i" = "Planned for v0.2.0. Returning all areas."
    ))
  }
  if (metadata) {
    cli::cli_warn(c(
      "{.arg metadata = TRUE} is not implemented in v0.1.0 MVP",
      "i" = "Planned for v0.2.0. Returning data without metadata."
    ))
  }

  source_info <- .resolve_source(year, month)
  url <- source_info$url

  if (is.null(url)) {
    abort_data_not_available(year, month)
  }

  zip_path <- .download_zip(url, year, month, use_cache = cache)

  df <- tryCatch(
    .parse_module_csv(zip_path, module),
    pulso_module_not_available = function(e) {
      abort_module_not_available(module, year, month)
    }
  )

  if (harmonize) {
    names(df) <- tolower(gsub("[^[:alnum:]_]", "_", names(df)))
  }

  tibble::as_tibble(df)
}
