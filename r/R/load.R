#' Load GEIH microdata for a single year-month-module
#'
#' Downloads and parses microdata from Colombia's Gran Encuesta Integrada
#' de Hogares (GEIH), published by DANE.
#'
#' @param year Integer. Year (2007 to current year).
#' @param month Integer. Month (1-12).
#' @param module Character. Module name (e.g., "ocupados").
#' @param area Character or NULL. Optional area filter. NOT IMPLEMENTED in v0.1.0.
#' @param harmonize Logical. Whether to apply harmonization. Default TRUE.
#' @param cache Logical. Whether to cache downloads. Default TRUE.
#' @param metadata Logical. Whether to attach DANE metadata to result.
#'   Default FALSE for Python parity. When TRUE, attaches metadata via
#'   `attr(df, "pulso_metadata")` and triggers lazy download of codebook
#'   on first call.
#' @param strict Logical. When FALSE (default, same as 'pulso-co' in
#'   'Python'), periods not yet manually validated against DANE published
#'   figures are loaded with a one-time warning per period. When TRUE,
#'   such periods raise \code{pulso_data_not_validated}.
#' @param allow_unvalidated Deprecated. Use \code{strict} instead
#'   (\code{allow_unvalidated = FALSE} is \code{strict = TRUE}).
#' @param columns Character or NULL. Columns to keep (DANE names, matched
#'   case-insensitively; \code{FEX_C} also matches \code{fex_c_2011}). Only
#'   those columns are read from the file (\code{data.table::fread(select =)}).
#'   The merge keys (\code{DIRECTORIO}, \code{SECUENCIA_P}, \code{ORDEN},
#'   \code{HOGAR}) are always kept so the result can still be merged.
#'   Requested columns that the file lacks are skipped with a warning.
#'   Default NULL (all columns).
#'
#' @details When \code{cache = TRUE} and the 'arrow' package is installed,
#'   the parsed module is also cached as parquet under the pulso cache
#'   directory, so the next load of the same period and module skips the
#'   zip and the CSV parsing. The cache key includes the download URL, the
#'   module, the parser version and the period's catalog entry. Without
#'   'arrow' nothing changes. Clear it with \code{pulso_clear_cache("parsed")}.
#'
#' @return A tibble with the microdata. If metadata = TRUE, the tibble
#'   has an attribute "pulso_metadata" with structured column info.
#'
#' @examples
#' \donttest{
#' if (interactive()) {
#'   df <- pulso_load(year = 2024, month = 6, module = "ocupados",
#'                    metadata = TRUE)
#'   cat(pulso_describe_column(df, "P6430"))
#' }
#' }
#'
#' @export
pulso_load <- function(year, month, module,
                       area = NULL,
                       harmonize = TRUE,
                       cache = TRUE,
                       metadata = FALSE,
                       strict = FALSE,
                       allow_unvalidated = NULL,
                       columns = NULL) {

  strict <- .resolve_strict(strict, allow_unvalidated)

  .validate_module(module)
  if (!is.null(columns) && (!is.character(columns) || anyNA(columns) ||
                              length(columns) == 0)) {
    abort_validation_error("`columns` must be NULL or a non-empty character vector")
  }
  .validate_year(year)
  .validate_month(month)

  if (!is.null(area)) {
    cli::cli_warn(c(
      "{.arg area} is not implemented in v0.1.0",
      "i" = "Returning all areas. Planned for v0.2.0."
    ))
  }

  source_info <- .resolve_source(year, month)
  url <- source_info$download_url

  if (is.null(url)) {
    abort_data_not_available(year, month)
  }

  module_spec <- source_info$modules[[module]]
  if (is.null(module_spec)) {
    abort_module_not_available(module, year, month)
  }

  if (!isTRUE(source_info$validated)) {
    if (isTRUE(strict)) {
      abort_data_not_validated(year, month)
    }
    .warn_unvalidated_once(year, month)
  }

  zip_path <- .download_zip(url, year, month, use_cache = cache)

  select <- if (is.null(columns)) NULL else .read_select(columns)
  if (isTRUE(cache) && .has_arrow()) {
    parquet_path <- .parsed_cache_path(source_info, module, year, month)
    df <- .read_parsed_cache(parquet_path, select)
    if (is.null(df)) {
      df <- .parse_module_csv(zip_path, module_spec, module, year, month)
      .write_parsed_cache(df, parquet_path)
    }
  } else {
    df <- .parse_module_csv(zip_path, module_spec, module, year, month, select = select)
  }
  if (!is.null(columns)) df <- .select_columns(df, columns)

  if (harmonize) {
    names(df) <- tolower(gsub("[^[:alnum:]_]", "_", names(df)))
  }

  result <- tibble::as_tibble(df)

  if (metadata) {
    column_metadata <- .compose_dataframe_metadata(result, year, month, module)

    attr(result, "pulso_metadata") <- list(
      column_metadata = column_metadata,
      source_year = year,
      source_month = month,
      source_module = module,
      source_epoch = .get_epoch_for_year(year)
    )
  }

  result
}

#' Resolve `strict` against the deprecated `allow_unvalidated`
#' @noRd
.resolve_strict <- function(strict, allow_unvalidated) {
  if (!is.null(allow_unvalidated)) {
    if (!is.logical(allow_unvalidated) || length(allow_unvalidated) != 1 ||
        is.na(allow_unvalidated)) {
      abort_validation_error("`allow_unvalidated` must be TRUE or FALSE")
    }
    cli::cli_warn(
      c(
        "{.arg allow_unvalidated} is deprecated as of pulso 0.2.0.",
        "i" = "Use {.code strict = {!allow_unvalidated}} instead."
      ),
      .frequency = "regularly",
      .frequency_id = "pulso_allow_unvalidated"
    )
    return(!allow_unvalidated)
  }
  if (!is.logical(strict) || length(strict) != 1 || is.na(strict)) {
    abort_validation_error("`strict` must be TRUE or FALSE")
  }
  strict
}

.pulso_state <- new.env(parent = emptyenv())

#' Warn about an unvalidated period once per session
#' @noRd
.warn_unvalidated_once <- function(year, month) {
  period_str <- sprintf("%d-%02d", year, month)
  seen <- .pulso_state$warned_periods %||% character()
  if (period_str %in% seen) return(invisible(FALSE))
  .pulso_state$warned_periods <- c(seen, period_str)
  cli::cli_warn(c(
    "Period {period_str} has not been validated against DANE published figures.",
    "i" = "Results may differ from official DANE tables. Use {.code strict = TRUE} to refuse unvalidated periods."
  ), class = "pulso_unvalidated_warning")
  invisible(TRUE)
}

#' Merge keys kept by every `columns =` request
#' @noRd
.MERGE_KEY_COLUMNS <- c("DIRECTORIO", "SECUENCIA_P", "ORDEN", "HOGAR")

#' Canonical names to read for a `columns =` request (plus keys and CLASE)
#' @noRd
.read_select <- function(columns) {
  unique(.canon_col(c(columns, .MERGE_KEY_COLUMNS, "CLASE")))
}

#' Keep the merge keys present plus the requested columns, in that order
#'
#' Matches names with .canon_col(); requested columns that are absent are
#' reported in one warning. Mirrors `_select_columns()` in
#' python/pulso/_core/parser.py.
#' @noRd
.select_columns <- function(df, columns) {
  canon <- .canon_col(names(df))
  wanted <- .canon_col(c(.MERGE_KEY_COLUMNS, columns))
  idx <- match(wanted, canon)
  idx <- unique(idx[!is.na(idx)])
  missing <- columns[!(.canon_col(columns) %in% canon)]
  if (length(missing) > 0) {
    cli::cli_warn("Requested columns not found and skipped: {.val {missing}}.")
  }
  df[, idx, drop = FALSE]
}
