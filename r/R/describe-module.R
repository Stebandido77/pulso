#' Describe a GEIH module
#'
#' Returns a human-readable summary of a GEIH survey module: its survey
#' level, available epochs, and harmonized canonical variables.
#'
#' @param module Character. Module name (e.g., "ocupados"). Must be one
#'   of the modules registered in sources.json.
#'
#' @return A multi-line character string.
#'
#' @examples
#' pulso_describe("ocupados")
#'
#' @export
pulso_describe <- function(module) {
  .validate_module(module)

  # Verify that the module exists in sources.json top-level $modules
  sources <- .load_sources()
  known_modules <- names(sources$modules)
  if (!module %in% known_modules) {
    dists   <- utils::adist(module, known_modules, ignore.case = TRUE)[1, ]
    closest <- known_modules[which.min(dists)]
    abort_pulso(
      class   = "pulso_module_not_available",
      message = sprintf(
        "Module '%s' not found. Did you mean '%s'? Available: %s",
        module, closest, paste(known_modules, collapse = ", ")
      ),
      module = module
    )
  }

  mod_info <- sources$modules[[module]]

  # Invert variable_module_map.json$applicability: module -> canonicals
  vmm_path <- system.file("extdata", "variable_module_map.json", package = "pulso")
  if (!nzchar(vmm_path)) {
    dev_vmm  <- fs::path_norm(
      fs::path(fs::path_real(getwd()), "..", "data", "variable_module_map.json")
    )
    vmm_path <- if (fs::file_exists(dev_vmm)) as.character(dev_vmm) else NULL
  }

  canon_vars <- character(0)
  if (!is.null(vmm_path)) {
    vmm <- jsonlite::fromJSON(vmm_path, simplifyVector = FALSE)
    for (canonical in names(vmm$applicability)) {
      mods <- vmm$applicability[[canonical]]
      if (module %in% unlist(mods, use.names = FALSE)) {
        canon_vars <- c(canon_vars, canonical)
      }
    }
  }

  # Build output lines
  lines <- c(
    sprintf("Module: %s", module),
    sprintf("Level: %s", mod_info$level %||% "unknown"),
    sprintf("Description: %s", mod_info$description_es %||% "—"),
    sprintf("Available in epochs: %s",
            paste(unlist(mod_info$available_in %||% list(), use.names = FALSE), collapse = ", "))
  )

  if (length(canon_vars) > 0) {
    lines <- c(lines,
      sprintf("Harmonized variables (%d): %s%s",
              length(canon_vars),
              paste(sort(canon_vars)[seq_len(min(5, length(canon_vars)))], collapse = ", "),
              if (length(canon_vars) > 5)
                sprintf(" ... and %d more", length(canon_vars) - 5)
              else
                "")
    )
  } else {
    lines <- c(lines, "Harmonized variables: none mapped in variable_module_map.json")
  }

  paste(lines, collapse = "\n")
}
