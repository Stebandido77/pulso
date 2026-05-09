#' Describe metadata for a single column
#'
#' Pretty-prints metadata for a column in a tibble loaded with
#' `metadata = TRUE`. Output format mirrors Python's
#' `pulso.describe_column()`.
#'
#' @param df A tibble loaded with `pulso_load(..., metadata = TRUE)`.
#' @param column Character. Column name to describe.
#'
#' @return A multi-line character string.
#'
#' @examples
#' \dontrun{
#' df <- pulso_load(2024, 6, "ocupados", metadata = TRUE)
#' cat(pulso_describe_column(df, "P6020"))
#' }
#'
#' @export
pulso_describe_column <- function(df, column) {
  if (!is.character(column) || length(column) != 1) {
    abort_validation_error("`column` must be a single character string")
  }

  if (!column %in% names(df)) {
    abort_validation_error(
      sprintf("Column '%s' is not in the DataFrame (have %d columns; first few: %s)",
              column, ncol(df),
              paste(utils::head(names(df), 5), collapse = ", "))
    )
  }

  metadata <- attr(df, "pulso_metadata")
  if (is.null(metadata)) {
    return(sprintf(
      "%s: no metadata attached (load with metadata = TRUE)",
      column
    ))
  }

  col_meta <- metadata$column_metadata[[column]]
  if (is.null(col_meta)) {
    return(sprintf(
      "%s: no metadata available (column exists but neither Curator nor Codebook has info)",
      column
    ))
  }

  .format_column_metadata(col_meta, column)
}

#' Format column metadata as text
#' @noRd
.format_column_metadata <- function(meta, column) {
  source <- meta$source %||% "missing"

  if (source == "codebook (skeletal)") {
    return(sprintf(
      "%s (sub-question, skeletal metadata)
Type: %s
Module: %s
Source: codebook (skeletal)
Note: Full metadata available on DANE catalog HTML, not yet integrated.
      Open issue at https://github.com/Stebandido77/pulso/issues if you
      need this for your analysis.",
      column,
      meta$type %||% "unknown",
      meta$module %||% "unknown"
    ))
  }

  lines <- c(
    sprintf("%s (%s)", column, meta$label %||% column),
    sprintf("Type: %s", meta$type %||% "unknown"),
    sprintf("Module: %s", meta$module %||% "unknown"),
    sprintf("Epoch: %s", meta$epoch %||% "unknown"),
    sprintf("Source: %s", source)
  )

  if (!is.null(meta$description_es) && nzchar(meta$description_es)) {
    lines <- c(lines, sprintf("Description: %s", meta$description_es))
  }

  if (!is.null(meta$question_text) && nzchar(meta$question_text)) {
    lines <- c(lines, sprintf("Question: %s", meta$question_text))
  }

  if (!is.null(meta$universe) && nzchar(meta$universe)) {
    lines <- c(lines, sprintf("Universe: %s", meta$universe))
  }

  if (!is.null(meta$categories) && length(meta$categories) > 0) {
    cats_str <- paste(
      sprintf("%s=%s", names(meta$categories), unlist(meta$categories)),
      collapse = ", "
    )
    lines <- c(lines, sprintf("Categories: %s", cats_str))
  }

  paste(lines, collapse = "\n")
}
