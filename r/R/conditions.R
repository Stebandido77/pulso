#' Abort with a pulso-specific condition class
#'
#' Internal helper for raising structured errors that callers can catch
#' by class name (e.g., tryCatch(pulso_data_not_available = ...)).
#'
#' @param class Character. Subclass of pulso_error.
#' @param message Character. Human-readable message.
#' @param ... Additional fields attached to the condition.
#'
#' @noRd
abort_pulso <- function(class, message, ...) {
  rlang::abort(
    message = message,
    class = c(class, "pulso_error", "error", "condition"),
    ...
  )
}

abort_data_not_available <- function(year, month) {
  abort_pulso(
    class = "pulso_data_not_available",
    message = sprintf("Data not available for %d-%02d", year, month),
    year = year,
    month = month
  )
}

abort_validation_error <- function(message, ...) {
  abort_pulso(
    class = "pulso_validation_error",
    message = message,
    ...
  )
}

abort_parse_error <- function(message, ...) {
  abort_pulso(
    class = "pulso_parse_error",
    message = message,
    ...
  )
}

abort_module_not_available <- function(module, year, month) {
  abort_pulso(
    class = "pulso_module_not_available",
    message = sprintf(
      "Module '%s' not available for %d-%02d",
      module, year, month
    ),
    module = module,
    year = year,
    month = month
  )
}

abort_data_not_validated <- function(year, month, ...) {
  abort_pulso(
    class = "pulso_data_not_validated",
    message = sprintf(
      "Period %d-%02d has not been validated against DANE published figures. Use allow_unvalidated = TRUE to load anyway.",
      year, month
    ),
    year = year,
    month = month,
    ...
  )
}
