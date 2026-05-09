#' Validate year argument
#' @noRd
.validate_year <- function(year) {
  if (!is.numeric(year) || length(year) != 1 || year != as.integer(year)) {
    abort_validation_error(
      sprintf("`year` must be a single integer, got: %s",
              paste(deparse(year), collapse = ""))
    )
  }

  current_year <- as.integer(format(Sys.Date(), "%Y"))
  if (year > current_year) {
    abort_validation_error(
      sprintf("Year %d is in the future (current year: %d)",
              year, current_year)
    )
  }

  if (year < 2007) {
    abort_validation_error(
      sprintf("Year %d is before pulso coverage starts (2007)", year)
    )
  }

  invisible(TRUE)
}

#' Validate month argument
#' @noRd
.validate_month <- function(month) {
  if (!is.numeric(month) || length(month) != 1 || month != as.integer(month)) {
    abort_validation_error(
      sprintf("`month` must be a single integer, got: %s",
              paste(deparse(month), collapse = ""))
    )
  }

  if (month < 1 || month > 12) {
    abort_validation_error(
      sprintf("Month must be between 1 and 12, got: %d", month)
    )
  }

  invisible(TRUE)
}

#' Validate module argument
#' @noRd
.validate_module <- function(module) {
  if (!is.character(module) || length(module) != 1 || nchar(module) == 0) {
    abort_validation_error(
      "`module` must be a non-empty single string"
    )
  }

  invisible(TRUE)
}
