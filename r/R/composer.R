#' Null-coalesce / empty-string-coalesce
#'
#' Returns `y` when `x` is NULL or a length-1 empty string; otherwise `x`.
#' Internal-only operator used by the metadata composer and renderers.
#'
#' @noRd
`%||%` <- function(x, y) {
  if (is.null(x) || (is.character(x) && length(x) == 1 && !nzchar(x))) y else x
}

#' Epoch name for a year
#'
#' Hardcoded to match Python's `pulso/metadata/parser.py::_epoch_for_year`.
#' Year >= 2021 -> "geih_2021_present"; otherwise "geih_2006_2020".
#' Avoids parsing `epochs.json$epochs[*]$date_range` strings on every call.
#'
#' @noRd
.get_epoch_for_year <- function(year) {
  if (!is.numeric(year) || length(year) != 1) {
    abort_validation_error(sprintf("Invalid year for epoch lookup: %s",
                                   paste(deparse(year), collapse = "")))
  }
  if (year >= 2021) "geih_2021_present" else "geih_2006_2020"
}

#' Compose metadata for a single column
#'
#' Mirrors python/pulso/metadata/composer.py::compose_column_metadata
#' (simplified: assumes columns are raw DANE codes, which is the v0.1.0
#' MVP harmonization output). Precedence: Curator wins for categories /
#' description / type / module; codebook contributes question_text /
#' universe.
#'
#' @noRd
.compose_column_metadata <- function(column_code, year, module) {
  epoch_name <- .get_epoch_for_year(year)

  variable_map <- .load_variable_map()
  codebook <- .load_codebook()

  canonical <- .find_canonical_name(column_code, epoch_name)
  curator_entry <- if (!is.null(canonical)) variable_map[[canonical]] else NULL

  codebook_entry <- codebook$variables[[column_code]]

  result <- list()

  if (!is.null(curator_entry) && !is.null(codebook_entry)) {
    result$source <- "merged"
    result$label <- curator_entry$description_es %||%
      codebook_entry$label %||% column_code
    result$description_es <- curator_entry$description_es
    result$description_en <- curator_entry$description_en
    result$categories <- curator_entry$categories
    result$question_text <- codebook_entry$question_text
    result$universe <- codebook_entry$universe
    result$type <- curator_entry$type %||% codebook_entry$type
    result$module <- curator_entry$module
    result$canonical_name <- canonical

  } else if (!is.null(curator_entry)) {
    result$source <- "curator"
    result$label <- curator_entry$description_es %||% column_code
    result$description_es <- curator_entry$description_es
    result$description_en <- curator_entry$description_en
    result$categories <- curator_entry$categories
    result$type <- curator_entry$type
    result$module <- curator_entry$module
    result$canonical_name <- canonical

  } else if (!is.null(codebook_entry)) {
    has_categories <- !is.null(codebook_entry$categories) &&
      length(codebook_entry$categories) > 0
    has_question_text <- !is.null(codebook_entry$question_text) &&
      nchar(codebook_entry$question_text) > 0

    if (!has_categories && !has_question_text) {
      result$source <- "codebook (skeletal)"
    } else {
      result$source <- "codebook"
    }
    result$label <- codebook_entry$label %||% column_code
    result$question_text <- codebook_entry$question_text
    result$universe <- codebook_entry$universe
    result$categories <- codebook_entry$categories
    result$type <- codebook_entry$type
    result$module <- "unknown"

  } else {
    result$source <- "missing"
    result$label <- column_code
  }

  result$column <- column_code
  result$epoch <- epoch_name

  result
}

#' Compose metadata for all columns of a dataframe
#'
#' Mirrors python/pulso/metadata/composer.py::compose_dataframe_metadata.
#'
#' @noRd
.compose_dataframe_metadata <- function(df, year, month, module) {
  column_metadata <- list()

  for (col_name in names(df)) {
    column_metadata[[col_name]] <-
      .compose_column_metadata(col_name, year, module)
  }

  column_metadata
}
