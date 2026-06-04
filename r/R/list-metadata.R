#' List metadata for all columns of a tibble
#'
#' Returns a tibble summary of all columns with their metadata.
#'
#' @param df A tibble loaded with `pulso_load(..., metadata = TRUE)`.
#'
#' @return A tibble with columns: column, label, type, module, source,
#'   has_categories.
#'
#' @examples
#' \donttest{
#' df <- pulso_load(2024, 6, "ocupados", metadata = TRUE)
#' summary <- pulso_list_columns_metadata(df)
#' print(summary)
#' }
#'
#' @export
pulso_list_columns_metadata <- function(df) {
  metadata <- attr(df, "pulso_metadata")

  if (is.null(metadata)) {
    cli::cli_warn(c(
      "No metadata attached to DataFrame",
      "i" = "Load with {.code metadata = TRUE} to get metadata"
    ))
    return(tibble::tibble(
      column = character(0),
      label = character(0),
      type = character(0),
      module = character(0),
      source = character(0),
      has_categories = logical(0)
    ))
  }

  cols_meta <- metadata$column_metadata

  rows <- lapply(names(cols_meta), function(col_name) {
    cm <- cols_meta[[col_name]]
    list(
      column = col_name,
      label = cm$label %||% NA_character_,
      type = cm$type %||% NA_character_,
      module = cm$module %||% NA_character_,
      source = cm$source %||% "missing",
      has_categories = !is.null(cm$categories) && length(cm$categories) > 0
    )
  })

  tibble::as_tibble(do.call(rbind.data.frame, rows))
}
