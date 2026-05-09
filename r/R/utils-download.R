#' Get cache directory for pulso
#' @noRd
.cache_dir <- function() {
  dir <- tools::R_user_dir("pulso", "cache")
  if (!fs::dir_exists(dir)) {
    fs::dir_create(dir, recurse = TRUE)
  }
  dir
}

#' Download zip with on-disk caching
#'
#' @param url Character. URL to download.
#' @param year Integer. For cache key.
#' @param month Integer. For cache key.
#' @param use_cache Logical. Default TRUE.
#'
#' @return Path to local zip file.
#' @noRd
.download_zip <- function(url, year, month, use_cache = TRUE) {
  cache_path <- fs::path(
    .cache_dir(),
    "raw",
    as.character(year),
    sprintf("%02d.zip", month)
  )

  if (use_cache && fs::file_exists(cache_path)) {
    return(as.character(cache_path))
  }

  fs::dir_create(fs::path_dir(cache_path), recurse = TRUE)

  cli::cli_inform("Downloading {url}")

  resp <- httr2::request(url) |>
    httr2::req_perform(path = as.character(cache_path))

  if (httr2::resp_status(resp) >= 400) {
    abort_parse_error(
      sprintf("HTTP %d downloading %s", httr2::resp_status(resp), url)
    )
  }

  as.character(cache_path)
}
