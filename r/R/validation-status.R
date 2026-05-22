#' Validation status for a GEIH period
#'
#' Returns structured metadata about a specific year-month entry in the
#' pulso registry, including whether it has been manually validated
#' against published DANE figures.
#'
#' @param year Integer. Year (2007 to current year).
#' @param month Integer. Month (1-12).
#'
#' @return A one-row tibble with columns: \code{year}, \code{month},
#'   \code{epoch}, \code{validated}, \code{validated_by},
#'   \code{validated_at}, \code{source_url}, \code{file_size_mb},
#'   \code{modules_available}, \code{checksum_sha256}.
#'
#' @examples
#' \donttest{
#' pulso_validation_status(2024, 6)
#' }
#'
#' @export
pulso_validation_status <- function(year, month) {
  .validate_year(year)
  .validate_month(month)
  # .resolve_source lanza abort_data_not_available si no existe
  rec <- .resolve_source(year, month)

  tibble::tibble(
    year              = as.integer(year),
    month             = as.integer(month),
    epoch             = rec$epoch %||% NA_character_,
    validated         = isTRUE(rec$validated),
    validated_by      = if (is.null(rec$validated_by)) NA_character_ else rec$validated_by,
    validated_at      = if (is.null(rec$validated_at)) NA_character_ else rec$validated_at,
    source_url        = if (is.null(rec$download_url)) NA_character_ else rec$download_url,
    file_size_mb      = if (is.null(rec$size_bytes)) NA_real_ else rec$size_bytes / 1e6,
    modules_available = paste(sort(names(rec$modules)), collapse = ", "),
    checksum_sha256   = if (is.null(rec$checksum_sha256)) NA_character_ else rec$checksum_sha256
  )
}
