#' Labor-market indicators (TD, TO, TGP) by domain
#'
#' Computes the unemployment rate (TD), employment rate (TO) and global
#' participation rate (TGP), plus the levels of the working-age population
#' (PET), labor force (FT), employed and unemployed, with DANE's definitions:
#' PET is 12+ in cabeceras and 10+ in centros poblados and rural disperso on
#' the 2005 census frame, and 15+ on the 2018 frame (2022 onwards, and 2020);
#' employed / unemployed / inactive come from DANE's per-module flags
#' (OCI, DSI, INI on the 2005 frame; OCI, DSI, FFT on the 2018 frame).
#' Mirrors \code{pulso.indicadores()} in 'Python'.
#'
#' Point estimates only: the public GEIH microdata have no design variables
#' (strata, PSU), so standard errors are not computed (\code{se} is NA).
#' DANE publishes confidence limits and relative errors in the "Errores
#' relativos" sheet of its monthly annex.
#'
#' @param start,end Character \code{"YYYY-MM"}. \code{end} defaults to
#'   \code{start}. With \code{trimestre_movil = TRUE} each row is the quarter
#'   ending in that month (e.g. "2026-09" = Jul-Sep 2026).
#' @param dominio Character. One of "nacional", "cabeceras",
#'   "centros_poblados_rural", "13_ciudades", "23_ciudades" (cities with
#'   their metropolitan areas, DANE's AREA codes), "ciudad" (one row per
#'   AREA code) or "departamento" (one row per DPTO).
#' @param trimestre_movil Logical. Pool each month with the two before it,
#'   with the expansion factor divided by 3. Default FALSE.
#' @param strict,cache Passed to \code{\link{pulso_load_merged}}.
#'
#' @return A tibble with \code{periodo}, \code{meses}, \code{dominio},
#'   \code{grupo}, \code{pet}, \code{ft}, \code{oc}, \code{ds} (persons),
#'   \code{td}, \code{to}, \code{tgp} (percent) and \code{se} (NA). Months that
#'   cannot be computed are skipped with a warning.
#'
#' @examples
#' \donttest{
#' if (interactive()) {
#'   pulso_indicadores("2026-01", "2026-09")
#'   pulso_indicadores("2026-09", dominio = "ciudad", trimestre_movil = TRUE)
#' }
#' }
#'
#' @export
pulso_indicadores <- function(start, end = NULL,
                              dominio = c("nacional", "cabeceras", "centros_poblados_rural",
                                          "13_ciudades", "23_ciudades", "ciudad",
                                          "departamento"),
                              trimestre_movil = FALSE,
                              strict = FALSE,
                              cache = TRUE) {
  dominio <- match.arg(dominio)
  if (is.null(end)) end <- start
  targets <- .period_range(start, end)
  lag <- if (isTRUE(trimestre_movil)) 2L else 0L
  idx0 <- targets$year[1] * 12 + targets$month[1] - 1 - lag
  first <- sprintf("%d-%02d", idx0 %/% 12, idx0 %% 12 + 1)
  needed <- .period_range(first, end)
  key <- sprintf("%d-%02d", needed$year, needed$month)

  frames <- vapply(seq_len(nrow(needed)), function(i) {
    .sampling_frame(needed$year[i], needed$month[i])
  }, character(1))
  if (length(unique(frames)) > 1) {
    cli::cli_warn(paste0(
      "The months ", key[1], "..", end, " mix microdata on the 2005 and 2018 census ",
      "frames; rates are not comparable across frames."
    ))
  }

  monthly <- list()
  for (i in seq_len(nrow(needed))) {
    res <- tryCatch(
      .indicadores_month(needed$year[i], needed$month[i], strict = strict, cache = cache),
      error = function(e) {
        if (isTRUE(strict)) stop(e)
        cli::cli_warn("Skipping {key[i]}: {conditionMessage(e)}")
        NULL
      }
    )
    if (!is.null(res)) monthly[[key[i]]] <- res
  }

  rows <- list()
  for (j in seq_len(nrow(targets))) {
    y <- targets$year[j]
    m <- targets$month[j]
    t_idx <- y * 12 + m - 1
    window <- vapply((t_idx - lag):t_idx, function(k) {
      sprintf("%d-%02d", k %/% 12, k %% 12 + 1)
    }, character(1))
    if (!all(window %in% names(monthly))) next
    pooled <- dplyr::bind_rows(monthly[window])
    pooled$w <- pooled$w / length(window)
    for (g in .indicadores_groups(pooled, dominio)) {
      d <- pooled[g$mask, , drop = FALSE]
      pet <- sum(d$w[d$pet], na.rm = TRUE)
      ft <- sum(d$w[d$ft], na.rm = TRUE)
      oc <- sum(d$w[d$status == "1"], na.rm = TRUE)
      ds <- sum(d$w[d$status == "2"], na.rm = TRUE)
      rows[[length(rows) + 1]] <- tibble::tibble(
        periodo = sprintf("%d-%02d", y, m), meses = length(window), dominio = dominio,
        grupo = g$grupo, pet = pet, ft = ft, oc = oc, ds = ds,
        td = if (ft > 0) 100 * ds / ft else NA_real_,
        to = if (pet > 0) 100 * oc / pet else NA_real_,
        tgp = if (pet > 0) 100 * ft / pet else NA_real_,
        se = NA_real_
      )
    }
  }
  if (length(rows) == 0) {
    return(tibble::tibble(periodo = character(), meses = integer(), dominio = character(),
                          grupo = character(), pet = numeric(), ft = numeric(),
                          oc = numeric(), ds = numeric(), td = numeric(), to = numeric(),
                          tgp = numeric(), se = numeric()))
  }
  dplyr::bind_rows(rows)
}

#' Person-level PET / FT / status / weight table for one month
#' @noRd
.indicadores_month <- function(year, month, strict = FALSE, cache = TRUE) {
  info <- .resolve_source(year, month)
  shared <- identical(info$modules$desocupados, info$modules$inactivos)
  labor <- if (shared) c("ocupados", "desocupados") else c("ocupados", "desocupados", "inactivos")
  for (m in labor) {
    if (is.null(info$modules[[m]])) {
      abort_validation_error(sprintf("module '%s' not in the catalog for %d-%02d", m, year, month))
    }
  }
  df <- pulso_load_merged(year, month, c("caracteristicas_generales", labor),
                          harmonize = TRUE, cache = cache, strict = strict)
  .indicadores_person_table(df, year, month)
}

#' Apply DANE's PET / FT / status definitions to a merged, lower-cased frame
#'
#' Same rules as pet_by_age_zone / labor_status_from_flags in
#' python/pulso/_core/harmonizer_funcs.py.
#' @noRd
.indicadores_person_table <- function(df, year, month) {
  num <- function(x) suppressWarnings(as.numeric(x))
  flag <- function(name) if (name %in% names(df)) num(df[[name]]) %in% 1 else rep(FALSE, nrow(df))
  age <- num(df$p6040)
  clase <- num(df$clase)
  min_age <- if (.sampling_frame(year, month) == "2018") {
    rep(15, nrow(df))
  } else {
    ifelse(clase %in% 1, 12, 10)
  }
  pet <- !is.na(age) & age >= min_age
  occ <- flag("oci")
  unemp <- flag("dsi") & !occ
  outside_col <- if ("ini" %in% names(df)) "ini" else "fft"
  outside <- flag(outside_col) & !occ & !unemp
  status <- ifelse(occ, "1", ifelse(unemp, "2", ifelse(outside, "3", NA_character_)))
  wcol <- .weight_column(names(df))
  if (is.na(wcol)) abort_validation_error(sprintf("no expansion factor in %d-%02d", year, month))
  tibble::tibble(
    pet = pet, ft = occ | unemp, status = status, w = num(df[[wcol]]),
    clase = clase,
    area = if ("area" %in% names(df)) num(df$area) else NA_real_,
    dpto = if ("dpto" %in% names(df)) num(df$dpto) else NA_real_
  )
}

#' @noRd
.CITIES_13 <- c(11, 5, 76, 8, 68, 17, 52, 66, 54, 73, 23, 13, 50)

#' @noRd
.CITIES_23 <- c(.CITIES_13, 15, 18, 19, 20, 27, 41, 44, 47, 63, 70)

#' Row masks for each group of a domain
#' @noRd
.indicadores_groups <- function(pooled, dominio) {
  one <- function(grupo, mask) list(list(grupo = grupo, mask = mask))
  by_code <- function(x) {
    codes <- sort(unique(x[!is.na(x)]))
    lapply(codes, function(cd) list(grupo = sprintf("%02d", as.integer(cd)), mask = x %in% cd))
  }
  switch(dominio,
    nacional = one("total", rep(TRUE, nrow(pooled))),
    cabeceras = one("cabeceras", pooled$clase %in% 1),
    centros_poblados_rural = one("centros_poblados_rural", pooled$clase %in% c(2, 3)),
    `13_ciudades` = one("13_ciudades", pooled$area %in% .CITIES_13),
    `23_ciudades` = one("23_ciudades", pooled$area %in% .CITIES_23),
    ciudad = by_code(pooled$area),
    departamento = by_code(pooled$dpto)
  )
}
