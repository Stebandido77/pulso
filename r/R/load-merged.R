#' Load and merge GEIH microdata across multiple modules
#'
#' Downloads, parses, and joins microdata from multiple GEIH modules for a
#' single year-month. All modules must be at the same survey level (persona
#' or hogar).
#'
#' @param year Integer. Year (2007 to current year).
#' @param month Integer. Month (1-12).
#' @param modules Character vector. Module names to merge (length >= 2).
#'   Use \code{\link{pulso_load}} for a single module.
#' @param harmonize Logical. Whether to lowercase column names. Default TRUE.
#' @param cache Logical. Whether to cache downloads. Default TRUE.
#' @param metadata Logical. Whether to attach DANE metadata. Default FALSE.
#' @param allow_unvalidated Logical. Passed through to each \code{pulso_load()}
#'   call. Default FALSE.
#'   When TRUE, metadata is composed from the first module's column index
#'   as a v0.1.0 approximation (multi-module metadata composition is planned
#'   for v0.2.0).
#'
#' @return A tibble with columns from all requested modules, joined on
#'   shared identifier keys (directorio, secuencia_p, orden for persona-level
#'   modules). The join is an outer join by default so that modules covering
#'   different person subsets (e.g., ocupados vs desocupados) are combined
#'   correctly.
#'
#' @note Mixed-level merges (persona + hogar modules in the same call) are
#'   deferred to v0.2.0. If you need a hogar-level module, merge the result
#'   manually after separate calls.
#'
#' @examples
#' \donttest{
#' if (interactive()) {
#'   df <- pulso_load_merged(2024, 6, c("ocupados", "caracteristicas_generales"))
#'   nrow(df)
#' }
#' }
#'
#' @export
pulso_load_merged <- function(year, month, modules,
                               harmonize = TRUE,
                               cache = TRUE,
                               metadata = FALSE,
                               allow_unvalidated = FALSE) {

  if (!is.character(modules) || length(modules) == 0) {
    abort_validation_error("'modules' must be a non-empty character vector")
  }
  if (length(modules) == 1) {
    abort_validation_error(
      "Single-module load: use pulso_load() instead of pulso_load_merged()"
    )
  }

  .validate_year(year)
  .validate_month(month)

  sources <- .load_sources()
  known <- names(sources$modules)
  for (m in modules) {
    if (!m %in% known) {
      abort_validation_error(sprintf(
        "Unknown module '%s'. Available: %s",
        m, paste(known, collapse = ", ")
      ))
    }
  }

  levels <- vapply(modules, function(m) sources$modules[[m]]$level, character(1))
  if (length(unique(levels)) > 1) {
    abort_validation_error(
      "Mixed-level merge (persona + hogar) is deferred to v0.2.0. Merge modules of the same level only."
    )
  }
  level <- levels[[1]]

  dfs <- lapply(modules, function(m) {
    pulso_load(year, month, m, harmonize = harmonize, cache = cache,
               metadata = FALSE, allow_unvalidated = allow_unvalidated)
  })
  names(dfs) <- modules

  # Merge keys match both epochs in epochs.json (geih_2006_2020 and geih_2021_present
  # define identical persona/hogar keys). Hardcoded to avoid runtime JSON parsing.
  merge_keys <- if (level == "persona") {
    if (harmonize) c("directorio", "secuencia_p", "orden") else c("DIRECTORIO", "SECUENCIA_P", "ORDEN")
  } else {
    if (harmonize) c("directorio", "secuencia_p") else c("DIRECTORIO", "SECUENCIA_P")
  }

  for (m in names(dfs)) {
    missing_keys <- setdiff(merge_keys, names(dfs[[m]]))
    if (length(missing_keys) > 0) {
      abort_validation_error(sprintf(
        "Module '%s' is missing merge keys: %s",
        m, paste(missing_keys, collapse = ", ")
      ))
    }
  }

  result <- dfs[[1]]
  for (i in seq_along(dfs)[-1]) {
    df_right <- dfs[[i]]
    existing_non_key <- setdiff(names(result), merge_keys)
    cols_to_drop <- intersect(names(df_right), existing_non_key)
    if (length(cols_to_drop) > 0) {
      df_right <- df_right[, !names(df_right) %in% cols_to_drop, drop = FALSE]
    }
    result <- merge(result, df_right, by = merge_keys, all = TRUE)
  }
  result <- tibble::as_tibble(result)

  if (metadata) {
    column_metadata <- .compose_dataframe_metadata(result, year, month, modules[[1]])
    attr(result, "pulso_metadata") <- list(
      column_metadata = column_metadata,
      source_year = year,
      source_month = month,
      source_module = modules[[1]],
      source_epoch = .get_epoch_for_year(year)
    )
  }

  result
}
