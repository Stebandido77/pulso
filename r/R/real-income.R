#' DANE's monthly CPI index (IPC total, base December 2018 = 100)
#'
#' Returns the IPC index as a tibble. Same interface as \code{\link{pulso_tpm}}:
#' by default downloads the newest \code{anex-IPC-Indices-<mes><anio>.xlsx}
#' linked from DANE's IPC page and falls back to a bundled snapshot
#' (2003-01 to 2026-10). Mirrors \code{pulso.ipc()} in 'Python'.
#'
#' @param use_fixture Logical or NULL. NULL (default): try DANE, fall back to
#'   the snapshot. TRUE: always use the snapshot. FALSE: force the download.
#'
#' @return A tibble with \code{periodo} ("YYYY-MM"), \code{anio}, \code{mes},
#'   \code{indice}.
#'
#' @examples
#' \donttest{
#' if (interactive()) {
#'   tail(pulso_ipc())
#' }
#' }
#'
#' @export
pulso_ipc <- function(use_fixture = NULL) {
  if (isTRUE(use_fixture)) return(.ipc_from_fixture())
  tryCatch(
    .ipc_from_dane(),
    error = function(e) {
      if (isFALSE(use_fixture)) stop(e)
      cli::cli_warn(c(
        "x" = "DANE IPC download failed: {conditionMessage(e)}",
        "i" = "Falling back to bundled snapshot (extends to 2026-10)."
      ))
      .ipc_from_fixture()
    }
  )
}

#' @noRd
.ipc_finish <- function(df) {
  df <- df[order(df$anio, df$mes), , drop = FALSE]
  tibble::tibble(periodo = sprintf("%d-%02d", as.integer(df$anio), as.integer(df$mes)),
                 anio = as.integer(df$anio), mes = as.integer(df$mes),
                 indice = as.numeric(df$indice))
}

#' @noRd
.ipc_from_fixture <- function() {
  path <- system.file("extdata", "ipc_dane_indices_202610.csv", package = "pulso")
  if (!nzchar(path)) cli::cli_abort("IPC snapshot not found.")
  .ipc_finish(utils::read.csv(path))
}

#' @noRd
.ipc_from_dane <- function() {
  base <- "https://www.dane.gov.co"
  page <- httr2::req_perform(httr2::req_timeout(httr2::request(paste0(
    base, "/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc"
  )), 30))
  html <- httr2::resp_body_string(page)
  links <- regmatches(html, gregexpr(
    "/files/operaciones/IPC/[a-z]{3}[0-9]{4}/anex-IPC-Indices-[a-z]{3}[0-9]{4}\\.xlsx", html
  ))[[1]]
  if (length(links) == 0) cli::cli_abort("No IPC annex link on DANE's IPC page.")
  tmp <- tempfile(fileext = ".xlsx")
  on.exit(unlink(tmp), add = TRUE)
  httr2::req_perform(httr2::req_timeout(httr2::request(paste0(base, links[1])), 60), path = tmp)
  .parse_ipc_annex(tmp)
}

#' Parse DANE's anex-IPC-Indices-*.xlsx ("Mes" x years table)
#' @noRd
.parse_ipc_annex <- function(path) {
  raw <- readxl::read_excel(path, sheet = 1, col_names = FALSE, .name_repair = "minimal")
  raw <- as.data.frame(raw)
  hdr <- which(trimws(as.character(raw[[1]])) == "Mes")[1]
  years <- suppressWarnings(as.integer(unlist(raw[hdr, -1])))
  meses <- c("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre")
  out <- list()
  for (i in (hdr + 1):(hdr + 12)) {
    mes <- match(tolower(trimws(as.character(raw[i, 1]))), meses)
    vals <- suppressWarnings(as.numeric(unlist(raw[i, -1])))
    ok <- !is.na(years) & !is.na(vals)
    out[[length(out) + 1]] <- data.frame(anio = years[ok], mes = mes, indice = vals[ok])
  }
  .ipc_finish(do.call(rbind, out))
}

#' Monthly legal minimum wage (SMMLV) by year
#'
#' Bundled table of Colombia's monthly legal minimum wage (without the
#' transport allowance), 2007-2026, with the decree that set each value and
#' the official page where it was verified. Mirrors
#' \code{pulso.salario_minimo()} in 'Python'.
#'
#' @return A tibble with \code{anio}, \code{smmlv}, \code{decreto},
#'   \code{fuente}.
#'
#' @examples
#' pulso_salario_minimo()
#'
#' @export
pulso_salario_minimo <- function() {
  path <- system.file("extdata", "salario_minimo.csv", package = "pulso")
  tibble::as_tibble(utils::read.csv(path, stringsAsFactors = FALSE))
}

#' Convert nominal peso columns to pesos of a reference month
#'
#' Adds \code{<col>_real} = nominal * IPC(deflate_to) / IPC(periodo of the
#' row). Mirrors \code{pulso.deflactar()} in 'Python'.
#'
#' @param df A data frame with a \code{periodo} ("YYYY-MM") column, e.g. from
#'   \code{\link{pulso_load_range}}.
#' @param columns Character. Nominal peso columns to deflate.
#' @param deflate_to Character. Reference month "YYYY-MM".
#' @param periodo_col Character. Name of the period column.
#' @param ipc_table Optional output of \code{\link{pulso_ipc}}.
#'
#' @return \code{df} with the \code{<col>_real} columns added.
#'
#' @examples
#' df <- data.frame(periodo = "2018-12", inglabo = 1000)
#' pulso_deflactar(df, "inglabo", "2026-09", ipc_table = pulso_ipc(use_fixture = TRUE))
#'
#' @export
pulso_deflactar <- function(df, columns, deflate_to, periodo_col = "periodo",
                            ipc_table = NULL) {
  if (is.null(ipc_table)) ipc_table <- pulso_ipc()
  index <- ipc_table$indice
  names(index) <- ipc_table$periodo
  if (!deflate_to %in% names(index)) {
    abort_validation_error(sprintf("deflate_to '%s' is not in the IPC table", deflate_to))
  }
  missing <- setdiff(unique(df[[periodo_col]]), names(index))
  if (length(missing) > 0) {
    abort_validation_error(sprintf("No IPC for periods: %s", paste(missing, collapse = ", ")))
  }
  factor <- unname(index[[deflate_to]] / index[df[[periodo_col]]])
  for (col in columns) {
    df[[paste0(col, "_real")]] <- suppressWarnings(as.numeric(df[[col]])) * factor
  }
  df
}
