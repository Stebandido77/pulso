#' Resolve variable_map.json path (bundled or dev)
#' @noRd
.resolve_variable_map_path <- function() {
  bundled <- system.file("extdata", "variable_map.json", package = "pulso")
  if (nzchar(bundled)) return(bundled)

  dev_path <- fs::path_norm(
    fs::path(fs::path_real(getwd()), "..", "data", "variable_map.json")
  )
  if (fs::file_exists(dev_path)) return(as.character(dev_path))

  abort_parse_error("Cannot locate variable_map.json")
}

#' Load variable_map (cached in closure)
#'
#' Returns the inner `variables` dict directly so downstream lookups
#' can index canonical names without an extra `$variables` step. The
#' top-level `metadata` block in variable_map.json is intentionally
#' dropped at load time (no consumer needs it yet).
#'
#' @noRd
.load_variable_map <- local({
  cache <- NULL
  function() {
    if (is.null(cache)) {
      path <- .resolve_variable_map_path()
      raw <- jsonlite::fromJSON(path, simplifyVector = FALSE)
      cache <<- raw$variables
    }
    cache
  }
})

#' Find canonical name for a DANE column code
#'
#' Looks through variable_map.json to find which canonical variable
#' (e.g., "sexo") maps to a given DANE code (e.g., "P6020" or "P3271")
#' for a given epoch.
#'
#' @noRd
.find_canonical_name <- function(column_code, epoch_name) {
  variable_map <- .load_variable_map()

  for (canonical_name in names(variable_map)) {
    var_def <- variable_map[[canonical_name]]

    if (!is.null(var_def$mappings[[epoch_name]])) {
      mapping <- var_def$mappings[[epoch_name]]
      if (identical(mapping$source_variable, column_code)) {
        return(canonical_name)
      }
    }
  }

  NULL
}
