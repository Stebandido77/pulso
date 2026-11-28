#' Version of the parsed output
#'
#' Bump it whenever a parser change alters what `.parse_module_csv()`
#' returns for the same zip: cached parquet files written by an older version
#' are then ignored. Mirrors `PARSER_VERSION` in python/pulso/_core/parser.py.
#' @noRd
.PARSER_VERSION <- "3.0"

#' Fields of a sources.json entry that change without changing its parse
#' @noRd
.VOLATILE_RECORD_FIELDS <- c("validated", "validated_by", "validated_at", "notes", "scraped_at")

#' Path of the parsed-module parquet cache for one period and module
#'
#' The key hashes the download URL, the module, `.PARSER_VERSION` and the
#' period's sources.json entry (without validation bookkeeping).
#' @noRd
.parsed_cache_path <- function(source_info, module, year, month) {
  entry <- source_info[setdiff(names(source_info), .VOLATILE_RECORD_FIELDS)]
  payload <- list(
    url = trimws(as.character(source_info$download_url)),
    module = module,
    parser_version = .PARSER_VERSION,
    entry = entry[order(names(entry))]
  )
  key <- substr(digest::digest(payload, algo = "sha1"), 1, 16)
  as.character(fs::path(
    .cache_dir(), "parsed", as.character(year), sprintf("%02d", month),
    paste0(module, "_", key, ".parquet")
  ))
}

#' Is the optional parquet cache available? ('arrow' is in Suggests)
#' @noRd
.has_arrow <- function() requireNamespace("arrow", quietly = TRUE)

#' Read a cached parsed module, or NULL if absent or unreadable
#' @noRd
.read_parsed_cache <- function(path, select = NULL) {
  if (!file.exists(path)) return(NULL)
  tryCatch({
    cols <- NULL
    if (!is.null(select)) {
      present <- arrow::ParquetFileReader$create(path)$GetSchema()$names
      cols <- present[.canon_col(present) %in% select]
    }
    df <- if (is.null(cols)) {
      arrow::read_parquet(path, as_data_frame = TRUE)
    } else {
      arrow::read_parquet(path, col_select = dplyr::all_of(cols), as_data_frame = TRUE)
    }
    as.data.frame(df)
  }, error = function(e) {
    unlink(path)
    NULL
  })
}

#' Write a parsed module to the parquet cache; failures only skip the cache
#' @noRd
.write_parsed_cache <- function(df, path) {
  tryCatch({
    fs::dir_create(fs::path_dir(path), recurse = TRUE)
    tmp <- paste0(path, ".tmp")
    arrow::write_parquet(df, tmp)
    if (!file.rename(tmp, path)) unlink(tmp)
    invisible(TRUE)
  }, error = function(e) {
    unlink(paste0(path, ".tmp"))
    invisible(FALSE)
  })
}

#' Clear the local pulso cache
#'
#' Deletes cached files under the pulso cache directory
#' (\code{tools::R_user_dir("pulso", "cache")}, or the \code{pulso.cache_dir}
#' option): the downloaded DANE zips (\code{"raw"}), the parsed modules
#' stored as parquet (\code{"parsed"}, only written when the 'arrow' package
#' is installed), or both. Mirrors \code{pulso.cache_clear()} in 'Python'.
#'
#' @param level Character. One of \code{"all"} (default), \code{"raw"} or
#'   \code{"parsed"}.
#'
#' @return Invisibly, the paths that were removed.
#'
#' @examples
#' \donttest{
#' if (interactive()) {
#'   pulso_clear_cache("parsed")
#' }
#' }
#'
#' @export
pulso_clear_cache <- function(level = c("all", "raw", "parsed")) {
  level <- match.arg(level)
  levels <- if (level == "all") c("raw", "parsed") else level
  paths <- as.character(fs::path(.cache_dir(), levels))
  paths <- paths[dir.exists(paths)]
  unlink(paths, recursive = TRUE)
  invisible(paths)
}
