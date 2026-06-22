#' Load GEIH microdata for a single year-month-module
#'
#' Downloads and parses microdata from Colombia's Gran Encuesta Integrada
#' de Hogares (GEIH), published by DANE.
#'
#' @param year Integer. Year (2007 to current year).
#' @param month Integer. Month (1-12).
#' @param module Character. Module name (e.g., "ocupados").
#' @param area Character or NULL. Optional area filter. NOT IMPLEMENTED in v0.1.0.
#' @param harmonize Logical. Whether to apply harmonization. Default TRUE.
#' @param cache Logical. Whether to cache downloads. Default TRUE.
#' @param metadata Logical. Whether to attach DANE metadata to result.
#'   Default FALSE for Python parity. When TRUE, attaches metadata via
#'   `attr(df, "pulso_metadata")` and triggers lazy download of codebook
#'   on first call.
#' @param allow_unvalidated Logical. When FALSE (default), raises
#'   \code{pulso_data_not_validated} for periods not yet manually validated
#'   against DANE published figures. Set TRUE to load anyway with a warning.
#'
#' @return A tibble with the microdata. If metadata = TRUE, the tibble
#'   has an attribute "pulso_metadata" with structured column info.
#'
#' @examples
#' \donttest{
#' if (interactive()) {
#'   df <- pulso_load(year = 2024, month = 6, module = "ocupados",
#'                    metadata = TRUE)
#'   cat(pulso_describe_column(df, "P6430"))
#' }
#' }
#'
#' @export
pulso_load <- function(year, month, module,
                       area = NULL,
                       harmonize = TRUE,
                       cache = TRUE,
                       metadata = FALSE,
                       allow_unvalidated = FALSE) {

  .validate_module(module)
  .validate_year(year)
  .validate_month(month)

  if (!is.null(area)) {
    cli::cli_warn(c(
      "{.arg area} is not implemented in v0.1.0",
      "i" = "Returning all areas. Planned for v0.2.0."
    ))
  }

  source_info <- .resolve_source(year, month)
  url <- source_info$download_url

  if (is.null(url)) {
    abort_data_not_available(year, month)
  }

  module_spec <- source_info$modules[[module]]
  if (is.null(module_spec)) {
    abort_module_not_available(module, year, month)
  }

  if (!isTRUE(source_info$validated)) {
    if (!isTRUE(allow_unvalidated)) {
      abort_data_not_validated(year, month)
    }
    period_str <- sprintf("%d-%02d", year, month)
    cli::cli_warn(c(
      "Period {period_str} has not been validated against DANE published figures.",
      "i" = "Results may differ from official DANE tables. Proceed with caution."
    ))
  }

  zip_path <- .download_zip(url, year, month, use_cache = cache)

  df <- .parse_module_csv(zip_path, module_spec, module, year, month)

  if (harmonize) {
    names(df) <- tolower(gsub("[^[:alnum:]_]", "_", names(df)))
  }

  result <- tibble::as_tibble(df)

  if (metadata) {
    column_metadata <- .compose_dataframe_metadata(result, year, month, module)

    attr(result, "pulso_metadata") <- list(
      column_metadata = column_metadata,
      source_year = year,
      source_month = month,
      source_module = module,
      source_epoch = .get_epoch_for_year(year)
    )
  }

  result
}
