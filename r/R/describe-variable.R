#' Describe a harmonized variable
#'
#' Returns a human-readable summary of a canonical variable defined in
#' variable_map.json: its module, description, source mappings per epoch,
#' and any comparability warning.
#'
#' @param variable_name Character. Canonical variable name (e.g., "sexo").
#'   The lookup is case-insensitive.
#'
#' @return A single multi-line character string.
#'
#' @examples
#' pulso_describe_variable("sexo")
#' pulso_describe_variable("edad")
#'
#' @export
pulso_describe_variable <- function(variable_name) {
  if (!is.character(variable_name) || length(variable_name) != 1 ||
      nchar(variable_name) == 0) {
    abort_validation_error("`variable_name` must be a non-empty single string")
  }

  vm <- .load_variable_map()

  # Case-insensitive lookup
  vm_names_lower <- tolower(names(vm))
  idx <- match(tolower(variable_name), vm_names_lower)

  if (is.na(idx)) {
    abort_validation_error(
      sprintf("Variable '%s' not found in variable map.", variable_name)
    )
  }

  canonical_name <- names(vm)[idx]
  var <- vm[[canonical_name]]

  description <- var$description_es %||% "(none)"

  lines <- c(
    sprintf("Variable: %s", canonical_name),
    sprintf("Module: %s", var$module %||% "(none)"),
    sprintf("Description: %s", description)
  )

  # Epoch mappings
  if (!is.null(var$mappings) && length(var$mappings) > 0) {
    epoch_lines <- vapply(names(var$mappings), function(epoch) {
      sv <- var$mappings[[epoch]]$source_variable
      if (is.list(sv)) sv <- paste(unlist(sv, use.names = FALSE), collapse = ", ")
      sprintf("  %s: %s", epoch, sv)
    }, character(1L))
    lines <- c(lines, "Epochs:", epoch_lines)
  } else {
    lines <- c(lines, "Epochs: (none)")
  }

  # Comparability warning: show when the field exists and is non-null
  cw <- var$comparability_warning
  if (!is.null(cw) && !identical(cw, FALSE) && nchar(as.character(cw)) > 0) {
    lines <- c(lines, sprintf("WARNING: %s", cw))
  }

  paste(lines, collapse = "\n")
}
