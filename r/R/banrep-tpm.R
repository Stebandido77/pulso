#' Fetch Tasa de Politica Monetaria (TPM) from Banco de la Republica
#'
#' Returns Colombia's monetary policy rate as a tibble. Data source:
#' Banco de la Republica SDMX API (DF_CBR_DAILY_HIST). When the API is
#' unavailable, falls back to a bundled snapshot extending to 2026-04-21.
#'
#' @param start Optional start date as character "YYYY-MM-DD" or Date.
#' @param end Optional end date as character "YYYY-MM-DD" or Date.
#' @param use_fixture Logical or NULL. If NULL (default), auto-detect:
#'   tries API first, falls back to snapshot if unavailable.
#'   If TRUE, always use bundled snapshot. If FALSE, force API call.
#'
#' @return A tibble with columns:
#'   \describe{
#'     \item{fecha}{Date. Observation date.}
#'     \item{valor}{numeric. TPM rate in percentage points.}
#'     \item{serie}{character. Always "tpm".}
#'   }
#'
#' @export
#' @examples
#' \dontrun{
#' # Recent TPM
#' tpm_2024 <- pulso_tpm(start = "2024-01-01", end = "2024-12-31")
#' # Full history (uses fixture if API down)
#' tpm_all <- pulso_tpm()
#' }
pulso_tpm <- function(start = NULL, end = NULL, use_fixture = NULL) {
  if (!is.null(start)) start <- .validate_banrep_date(start, "start")
  if (!is.null(end))   end   <- .validate_banrep_date(end,   "end")
  if (!is.null(start) && !is.null(end) && start > end) {
    cli::cli_abort("start ({start}) must be <= end ({end})")
  }

  if (is.null(use_fixture)) {
    use_fixture <- !.banrep_api_available()
  }

  if (use_fixture) {
    cli::cli_inform(c(
      "i" = "Using bundled TPM snapshot (extends to 2026-04-21).",
      "i" = "Set {.arg use_fixture=FALSE} to force a live API call."
    ))
    return(.tpm_from_fixture(start = start, end = end))
  }

  tryCatch(
    .tpm_from_api(start = start, end = end),
    error = function(e) {
      cli::cli_warn(c(
        "x" = "Banrep API call failed: {conditionMessage(e)}",
        "i" = "Falling back to bundled snapshot."
      ))
      .tpm_from_fixture(start = start, end = end)
    }
  )
}
