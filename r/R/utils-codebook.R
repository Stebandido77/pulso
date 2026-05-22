#' Resolve codebook release manifest path
#' @noRd
.resolve_codebook_release_path <- function() {
  bundled <- system.file("extdata", "codebook_release.json", package = "pulso")
  if (nzchar(bundled)) return(bundled)

  dev_path <- fs::path_norm(
    fs::path(fs::path_real(getwd()), "..", "data", "codebook_release.json")
  )
  if (fs::file_exists(dev_path)) return(as.character(dev_path))

  abort_parse_error("Cannot locate codebook_release.json")
}

#' Resolve cached codebook path
#' @noRd
.codebook_cache_path <- function() {
  fs::path(.cache_dir(), "codebook", "dane_codebook.json")
}

#' Verify SHA256 of cached codebook
#' @noRd
.verify_codebook_sha256 <- function(path, expected_sha256) {
  if (!fs::file_exists(path)) return(FALSE)

  actual_sha256 <- digest::digest(file = path, algo = "sha256")
  identical(actual_sha256, expected_sha256)
}

#' Download codebook with SHA256 verification
#' @noRd
.download_codebook <- function() {
  manifest <- jsonlite::fromJSON(.resolve_codebook_release_path())

  cache_path <- .codebook_cache_path()

  if (.verify_codebook_sha256(cache_path, manifest$sha256)) {
    return(as.character(cache_path))
  }

  fs::dir_create(fs::path_dir(cache_path), recurse = TRUE)

  cli::cli_inform(c(
    "Downloading codebook ({format(manifest$size_bytes / 1024^2, digits=1)} MB) on first use",
    "i" = "Cached at {.path {cache_path}}"
  ))

  resp <- httr2::request(manifest$url) |>
    httr2::req_perform(path = as.character(cache_path))

  if (httr2::resp_status(resp) >= 400) {
    abort_parse_error(
      sprintf("HTTP %d downloading codebook from %s",
              httr2::resp_status(resp), manifest$url)
    )
  }

  if (!.verify_codebook_sha256(cache_path, manifest$sha256)) {
    fs::file_delete(cache_path)
    abort_parse_error(
      "Downloaded codebook SHA256 mismatch (expected vs actual)"
    )
  }

  as.character(cache_path)
}

#' Load codebook (lazy, cached in closure)
#' @noRd
.load_codebook <- local({
  cache <- NULL
  function() {
    if (is.null(cache)) {
      path <- .download_codebook()
      cache <<- jsonlite::fromJSON(path, simplifyVector = FALSE)
    }
    cache
  }
})
