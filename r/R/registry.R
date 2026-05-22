#' List validated GEIH periods
#'
#' Returns the registry entries for which the downloaded data has been
#' manually validated against DANE published figures.
#'
#' @return A tibble with one row per validated (year, month) pair, with
#'   columns: \code{year} (integer), \code{month} (integer),
#'   \code{epoch} (character), \code{validated} (logical, always TRUE),
#'   \code{validated_at} (character, ISO-8601 or NA),
#'   \code{num_modules} (integer).
#'   Sorted by year, month ascending.
#'
#' @examples
#' pulso_list_validated_range()
#'
#' @export
pulso_list_validated_range <- function() {
  sources <- .load_sources()
  rows <- list()
  for (key in names(sources$data)) {
    rec <- sources$data[[key]]
    if (isTRUE(rec$validated)) {
      year  <- as.integer(substr(key, 1, 4))
      month <- as.integer(substr(key, 6, 7))
      rows[[length(rows) + 1]] <- list(
        year        = year,
        month       = month,
        epoch       = rec$epoch %||% NA_character_,
        validated   = TRUE,
        validated_at = if (is.null(rec$validated_at)) NA_character_ else rec$validated_at,
        num_modules  = length(rec$modules)
      )
    }
  }
  if (length(rows) == 0) {
    return(tibble::tibble(
      year = integer(), month = integer(), epoch = character(),
      validated = logical(), validated_at = character(), num_modules = integer()
    ))
  }
  result <- tibble::tibble(
    year        = vapply(rows, `[[`, integer(1), "year"),
    month       = vapply(rows, `[[`, integer(1), "month"),
    epoch       = vapply(rows, `[[`, character(1), "epoch"),
    validated   = vapply(rows, `[[`, logical(1), "validated"),
    validated_at = vapply(rows, `[[`, character(1), "validated_at"),
    num_modules  = vapply(rows, `[[`, integer(1), "num_modules")
  )
  result[order(result$year, result$month), ]
}
