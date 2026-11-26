#' Get cache directory for pulso
#'
#' Honors the `pulso.cache_dir` option so users (and tests) can redirect
#' the cache; defaults to tools::R_user_dir("pulso", "cache").
#' @noRd
.cache_dir <- function() {
  dir <- getOption("pulso.cache_dir", tools::R_user_dir("pulso", "cache"))
  if (!fs::dir_exists(dir)) {
    fs::dir_create(dir, recurse = TRUE)
  }
  dir
}

#' TRUE when `path` is a readable zip archive
#' @noRd
.is_valid_zip <- function(path) {
  if (!file.exists(path) || file.size(path) < 22) return(FALSE)
  res <- tryCatch(
    suppressWarnings(utils::unzip(path, list = TRUE)),
    error = function(e) NULL
  )
  !is.null(res) && nrow(res) > 0
}

#' Download zip with on-disk caching
#'
#' The cache key includes a short hash of the URL, so when DANE republishes
#' a month under a new file id the stale copy is not reused. Downloads go to
#' a temporary file that is only moved into the cache once it is a valid
#' zip, so an interrupted download can no longer poison the cache (the
#' v0.1.x behaviour, which left a truncated file that every later call
#' tried to parse).
#'
#' @param url Character. URL to download.
#' @param year Integer. For cache key.
#' @param month Integer. For cache key.
#' @param use_cache Logical. Default TRUE.
#'
#' @return Path to local zip file.
#' @noRd
.download_zip <- function(url, year, month, use_cache = TRUE) {
  url <- trimws(url)
  key <- substr(digest::digest(url, algo = "sha1", serialize = FALSE), 1, 10)
  cache_path <- fs::path(
    .cache_dir(),
    "raw",
    as.character(year),
    sprintf("%02d_%s.zip", month, key)
  )
  cache_path <- as.character(cache_path)

  if (use_cache && file.exists(cache_path)) {
    if (.is_valid_zip(cache_path)) {
      return(cache_path)
    }
    cli::cli_inform("Cached file for {year}-{sprintf('%02d', month)} is corrupt; downloading again.")
    unlink(cache_path)
  }

  fs::dir_create(fs::path_dir(cache_path), recurse = TRUE)
  tmp <- paste0(cache_path, ".part")
  on.exit(unlink(tmp), add = TRUE)

  cli::cli_inform("Downloading {url}")

  timeout_s <- getOption("pulso.timeout", 600)
  req <- httr2::request(url) |>
    httr2::req_user_agent("pulso R package (https://github.com/Stebandido77/pulso)") |>
    httr2::req_timeout(timeout_s) |>
    httr2::req_retry(max_tries = getOption("pulso.max_tries", 3)) |>
    httr2::req_error(is_error = function(resp) FALSE)

  resp <- tryCatch(
    httr2::req_perform(req, path = tmp),
    error = function(e) {
      abort_download_error(
        sprintf("Download failed for %d-%02d (%s): %s",
                year, month, url, conditionMessage(e)),
        year = year, month = month
      )
    }
  )

  status <- httr2::resp_status(resp)
  if (status >= 400) {
    abort_download_error(
      sprintf("HTTP %d downloading %d-%02d from %s", status, year, month, url),
      year = year, month = month
    )
  }

  if (!.is_valid_zip(tmp)) {
    abort_download_error(
      sprintf(
        "Downloaded file for %d-%02d is not a valid zip archive (%s bytes). DANE may be returning an HTML page; try again later or check %s",
        year, month, format(file.size(tmp)), url
      ),
      year = year, month = month
    )
  }

  if (!file.rename(tmp, cache_path)) {
    file.copy(tmp, cache_path, overwrite = TRUE)
  }

  cache_path
}
