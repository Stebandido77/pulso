#' List harmonized variables from the variable map
#'
#' Returns a tibble summarizing all canonical variables defined in
#' variable_map.json, optionally filtered by module.
#'
#' @param module Character or NULL. When non-NULL, restricts output to
#'   variables whose \code{module} field equals this value (exact match,
#'   case-sensitive). Available modules in the current variable map:
#'   \code{caracteristicas_generales}, \code{desocupados},
#'   \code{inactivos}, \code{ocupados}, \code{otros_ingresos},
#'   \code{vivienda_hogares}.
#'
#' @return A tibble with one row per variable and columns:
#'   \describe{
#'     \item{canonical_name}{chr. Key used throughout the pulso package.}
#'     \item{module}{chr. Survey module the variable belongs to.}
#'     \item{description_es}{chr. Spanish description, or \code{NA} if absent.}
#'     \item{comparability}{chr. Always \code{NA} in this version (see Note).}
#'     \item{has_warning}{lgl. \code{TRUE} when a comparability_warning is
#'       present and non-empty for the variable.}
#'     \item{num_epochs}{int. Number of epoch mappings defined.}
#'   }
#'   Rows are sorted ascending by \code{canonical_name}.
#'
#' @note The \code{comparability} column is always \code{NA_character_} in the
#'   current version because the \code{comparability} field (expected values:
#'   "high" / "limited") has not yet been added to variable_map.json.
#'   Only \code{comparability_warning} (free text) is present in the data.
#'
#' @examples
#' # All variables
#' pulso_list_variables()
#'
#' # Subset by module
#' pulso_list_variables(module = "ocupados")
#'
#' @export
pulso_list_variables <- function(module = NULL) {
  vm <- .load_variable_map()

  if (!is.null(module)) {
    .validate_module(module)

    # Determine known modules from the map before filtering
    all_modules <- unique(vapply(vm, function(v) v$module %||% NA_character_,
                                 character(1L)))
    known_mods <- sort(all_modules[!is.na(all_modules)])

    vm_filtered <- Filter(function(v) {
      isTRUE(!is.null(v$module) && v$module == module)
    }, vm)

    if (length(vm_filtered) == 0L) {
      abort_pulso(
        class   = "pulso_module_not_available",
        message = sprintf(
          "Module '%s' not found in variable map. Available: %s",
          module, paste(known_mods, collapse = ", ")
        ),
        module = module
      )
    }

    vm <- vm_filtered
  }

  # Build rows
  canonical_names <- names(vm)
  rows <- lapply(canonical_names, function(cn) {
    var <- vm[[cn]]
    cw  <- var$comparability_warning
    hw  <- !is.null(cw) && !identical(cw, FALSE) && nchar(as.character(cw)) > 0
    list(
      canonical_name  = cn,
      module          = var$module %||% NA_character_,
      description_es  = var$description_es %||% NA_character_,
      comparability   = NA_character_,
      has_warning     = hw,
      num_epochs      = length(var$mappings %||% list())
    )
  })

  df <- tibble::tibble(
    canonical_name = vapply(rows, `[[`, character(1L), "canonical_name"),
    module         = vapply(rows, `[[`, character(1L), "module"),
    description_es = vapply(rows, `[[`, character(1L), "description_es"),
    comparability  = vapply(rows, `[[`, character(1L), "comparability"),
    has_warning    = vapply(rows, `[[`, logical(1L),   "has_warning"),
    num_epochs     = vapply(rows, `[[`, integer(1L),   "num_epochs")
  )

  df[order(df$canonical_name), ]
}
