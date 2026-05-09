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
#'
#' @return A tibble with the microdata. If metadata = TRUE, the tibble
#'   has an attribute "pulso_metadata" with structured column info.
#'
#' @examples
#' \dontrun{
#' df <- pulso_load(year = 2024, month = 6, module = "ocupados",
#'                  metadata = TRUE)
#' cat(pulso_describe_column(df, "P6020"))
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
      "{.arg area} is not implemented in v0.1.0",
      "i" = "Returning all areas. Planned for v0.2.0."
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
