#' Fetch the TRM (COP per USD) certified by the Superintendencia Financiera
#'
#' Returns Colombia's Tasa Representativa del Mercado as a tibble with one
#' row per calendar day. Data source: the Superintendencia Financiera's
#' dataset on datos.gov.co (\code{32sa-8pi3}); the Superfinanciera is the
#' entity that certifies the TRM. Each certified value covers a validity
#' window (Friday's value covers the weekend), which is expanded to days.
#' When the live call fails, falls back to a bundled snapshot extending to
#' 2026-11-30. Same interface as \code{\link{pulso_tpm}}; mirrors
#' \code{pulso.trm()} in 'Python'.
#'
#' @param start Optional start date as character "YYYY-MM-DD" or Date.
#' @param end Optional end date as character "YYYY-MM-DD" or Date.
#' @param use_fixture Logical or NULL. If NULL (default), try the live
#'   dataset and fall back to the snapshot. If TRUE, always use the bundled
#'   snapshot. If FALSE, force the live call (errors if it fails).
#'
#' @return A tibble with columns:
#'   \describe{
#'     \item{fecha}{Date. Calendar day.}
#'     \item{valor}{numeric. Pesos per US dollar.}
#'     \item{serie}{character. Always "trm".}
#'   }
#'
#' @export
#' @examples
#' \donttest{
#' if (interactive()) {
#'   trm_2026 <- pulso_trm(start = "2026-01-01", end = "2026-09-30")
#' }
#' }
pulso_trm <- function(start = NULL, end = NULL, use_fixture = NULL) {
  if (!is.null(start)) start <- .validate_banrep_date(start, "start")
  if (!is.null(end))   end   <- .validate_banrep_date(end,   "end")
  if (!is.null(start) && !is.null(end) && start > end) {
    cli::cli_abort("start ({start}) must be <= end ({end})")
  }

  if (isTRUE(use_fixture)) {
    cli::cli_inform(c(
      "i" = "Using bundled TRM snapshot (extends to 2026-11-30).",
      "i" = "Set {.arg use_fixture=FALSE} to force a live call."
    ))
    return(.trm_from_fixture(start = start, end = end))
  }

  tryCatch(
    .trm_from_api(start = start, end = end),
    error = function(e) {
      if (isFALSE(use_fixture)) stop(e)
      cli::cli_warn(c(
        "x" = "TRM live call failed: {conditionMessage(e)}",
        "i" = "Falling back to bundled snapshot (extends to 2026-11-30)."
      ))
      .trm_from_fixture(start = start, end = end)
    }
  )
}

#' @noRd
.TRM_API_URL <- "https://www.datos.gov.co/resource/32sa-8pi3.json"

#' @noRd
.TRM_FIXTURE <- "trm_superfinanciera_20261128.csv.gz"

#' One row per calendar day from (vigenciadesde, vigenciahasta, valor) windows
#' @noRd
.trm_expand_daily <- function(windows) {
  if (nrow(windows) == 0) {
    return(tibble::tibble(fecha = as.Date(character()), valor = numeric(),
                          serie = character()))
  }
  desde <- as.Date(substr(windows$vigenciadesde, 1, 10))
  hasta <- as.Date(substr(windows$vigenciahasta, 1, 10))
  valor <- as.numeric(windows$valor)
  parts <- lapply(seq_along(desde), function(i) {
    data.frame(fecha = seq(desde[i], hasta[i], by = "day"), valor = valor[i])
  })
  out <- do.call(rbind, parts)
  # A later certification wins if two windows ever overlap.
  out <- out[!duplicated(out$fecha, fromLast = TRUE), , drop = FALSE]
  out <- out[order(out$fecha), , drop = FALSE]
  tibble::tibble(fecha = out$fecha, valor = out$valor, serie = "trm")
}

#' @noRd
.trm_filter <- function(df, start, end) {
  if (!is.null(start)) df <- df[df$fecha >= start, , drop = FALSE]
  if (!is.null(end))   df <- df[df$fecha <= end, , drop = FALSE]
  df
}

#' @noRd
.trm_from_fixture <- function(start = NULL, end = NULL) {
  path <- system.file("extdata", .TRM_FIXTURE, package = "pulso")
  if (!nzchar(path)) cli::cli_abort("TRM snapshot {.file {(.TRM_FIXTURE)}} not found.")
  con <- gzfile(path, "rt")
  on.exit(close(con), add = TRUE)
  windows <- utils::read.csv(con, colClasses = "character")
  .trm_filter(.trm_expand_daily(windows), start, end)
}

#' @noRd
.trm_from_api <- function(start = NULL, end = NULL) {
  where <- character()
  if (!is.null(start)) where <- c(where, sprintf("vigenciahasta >= '%sT00:00:00'", format(start)))
  if (!is.null(end))   where <- c(where, sprintf("vigenciadesde <= '%sT00:00:00'", format(end)))
  req <- httr2::request(.TRM_API_URL)
  query <- list(`$select` = "vigenciadesde,vigenciahasta,valor",
                `$order` = "vigenciadesde", `$limit` = 50000)
  if (length(where)) query[["$where"]] <- paste(where, collapse = " AND ")
  req <- do.call(httr2::req_url_query, c(list(req), query))
  req <- httr2::req_timeout(req, 30)
  resp <- httr2::req_perform(req)
  windows <- jsonlite::fromJSON(httr2::resp_body_string(resp))
  if (length(windows) == 0) windows <- data.frame()
  windows <- as.data.frame(windows)
  if (nrow(windows) > 0 && !all(c("vigenciadesde", "vigenciahasta", "valor") %in% names(windows))) {
    cli::cli_abort("Unexpected TRM response columns: {names(windows)}")
  }
  .trm_filter(.trm_expand_daily(windows), start, end)
}
