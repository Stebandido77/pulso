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

#' Last period covered by a parsed catalog
#' @noRd
.catalog_end <- function(sources) {
  covered <- unlist(sources$metadata$covered_range)
  if (length(covered) >= 2) return(as.character(covered[[2]]))
  if (length(sources$data)) max(names(sources$data)) else ""
}

#' Path where pulso_update_catalog() stores a refreshed catalog
#' @noRd
.cached_catalog_path <- function() {
  file.path(.cache_dir(), "catalog", "sources.json")
}

#' Parse a catalog file, returning NULL when it is not a usable catalog
#' @noRd
.read_catalog <- function(path) {
  res <- tryCatch(
    jsonlite::fromJSON(path, simplifyVector = FALSE),
    error = function(e) NULL
  )
  if (!is.list(res) || !is.list(res$data) || length(res$data) == 0 ||
      !is.list(res$modules) || !is.list(res$metadata)) {
    return(NULL)
  }
  res
}

#' Load sources.json once per session (cached)
#'
#' Uses the catalog bundled with the package unless pulso_update_catalog()
#' saved a newer one in the user cache (disable with
#' options(pulso.use_cached_catalog = FALSE)).
#' @noRd
.load_sources <- local({
  cache <- NULL
  function(reset = FALSE) {
    if (isTRUE(reset)) {
      cache <<- NULL
      return(invisible(NULL))
    }
    if (is.null(cache)) {
      path <- .resolve_sources_path()
      bundled <- jsonlite::fromJSON(path, simplifyVector = FALSE)
      cached_path <- .cached_catalog_path()
      if (isTRUE(getOption("pulso.use_cached_catalog", TRUE)) &&
          file.exists(cached_path)) {
        cached <- .read_catalog(cached_path)
        if (!is.null(cached) && .catalog_end(cached) > .catalog_end(bundled)) {
          bundled <- cached
        }
      }
      cache <<- bundled
    }
    cache
  }
})

#' Update the catalog of DANE releases
#'
#' DANE publishes a new GEIH month roughly every four weeks, faster than
#' package releases reach CRAN. This downloads the catalog maintained in
#' the pulso repository (refreshed monthly) into the user cache, so new
#' months become loadable without upgrading the package. The catalog is
#' only replaced when the download is valid and covers a later period than
#' the one in use.
#'
#' @param url Character. Catalog URL. Defaults to the `main` branch of the
#'   pulso repository on GitHub.
#'
#' @return Invisibly, a list with `previous_end`, `latest_end`,
#'   `n_periods` and `path` (where the catalog was saved, or `NULL` if it
#'   was not newer).
#'
#' @examples
#' \donttest{
#' if (interactive()) {
#'   pulso_update_catalog()
#' }
#' }
#'
#' @export
pulso_update_catalog <- function(
    url = "https://raw.githubusercontent.com/Stebandido77/pulso/main/data/sources.json") {
  previous_end <- .catalog_end(.load_sources())

  tmp <- tempfile(fileext = ".json")
  on.exit(unlink(tmp), add = TRUE)
  resp <- tryCatch(
    httr2::request(url) |>
      httr2::req_user_agent("pulso R package (https://github.com/Stebandido77/pulso)") |>
      httr2::req_timeout(60) |>
      httr2::req_error(is_error = function(resp) FALSE) |>
      httr2::req_perform(path = tmp),
    error = function(e) {
      abort_download_error(sprintf(
        "Could not download the catalog from %s: %s", url, conditionMessage(e)
      ))
    }
  )
  if (httr2::resp_status(resp) >= 400) {
    abort_download_error(sprintf(
      "HTTP %d downloading the catalog from %s", httr2::resp_status(resp), url
    ))
  }

  fresh <- .read_catalog(tmp)
  if (is.null(fresh)) {
    abort_parse_error(sprintf("The file at %s is not a valid pulso catalog", url))
  }

  latest_end <- .catalog_end(fresh)
  saved <- NULL
  if (latest_end > previous_end) {
    saved <- .cached_catalog_path()
    dir.create(dirname(saved), recursive = TRUE, showWarnings = FALSE)
    file.copy(tmp, saved, overwrite = TRUE)
    .load_sources(reset = TRUE)
    cli::cli_inform("Catalog updated: now covers up to {latest_end} (was {previous_end}).")
  } else {
    cli::cli_inform("Catalog already up to date (covers up to {previous_end}).")
  }

  invisible(list(
    previous_end = previous_end,
    latest_end = max(latest_end, previous_end),
    n_periods = length(fresh$data),
    path = saved
  ))
}

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
