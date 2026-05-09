#' Resolve sources.json path (bundled or dev)
#'
#' @noRd
.resolve_sources_path <- function() {
  bundled <- system.file("extdata", "sources.json", package = "pulso")
  if (nzchar(bundled)) {
    return(bundled)
  }

  dev_path <- fs::path_norm(
    fs::path(fs::path_real(getwd()), "..", "data", "sources.json")
  )
  if (fs::file_exists(dev_path)) {
    return(dev_path)
  }

  abort_parse_error(
    "Cannot locate sources.json (not in installed package nor in ../data/)"
  )
}

#' Load sources.json once per session (cached)
#' @noRd
.load_sources <- local({
  cache <- NULL
  function() {
    if (is.null(cache)) {
      path <- .resolve_sources_path()
      cache <<- jsonlite::fromJSON(path, simplifyVector = FALSE)
    }
    cache
  }
})

#' Resolve source for year/month
#' @noRd
.resolve_source <- function(year, month) {
  sources <- .load_sources()

  year_str <- as.character(year)
  month_str <- sprintf("%s-%02d", year_str, month)

  if (!is.null(sources$data[[month_str]])) {
    return(sources$data[[month_str]])
  }

  abort_data_not_available(year, month)
}
