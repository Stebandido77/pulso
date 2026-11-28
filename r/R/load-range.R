#' Load consecutive months of a GEIH module
#'
#' Loads every month from \code{start} to \code{end} with
#' \code{\link{pulso_load}} and stacks them with a \code{periodo} column
#' (\code{"YYYY-MM"}). Mirrors \code{pulso.load_range()} in 'Python'.
#'
#' @param start,end Character. Inclusive bounds, \code{"YYYY-MM"}.
#' @param module Character. Module name (e.g., "ocupados").
#' @param harmonize,cache,strict,columns Passed to \code{\link{pulso_load}}.
#' @param average_weights Logical. If TRUE, add \code{peso_expansion_promedio}
#'   = expansion factor / number of months loaded. Each monthly file expands
#'   to the whole population, so pooling several months with the raw factor
#'   counts everyone once per month; DANE's moving-quarter levels (sheet
#'   "Total nacional Trim" of \code{anex-GEIH-<mes><anio>.xlsx}) are the
#'   average of the monthly levels, i.e. factor / 3. Rates (TD, TO, TGP) are
#'   the same with either factor. Default FALSE.
#'
#' @param deflate_to Character or NULL. If given ("YYYY-MM"), add
#'   \code{<col>_real} columns in pesos of that month with DANE's IPC
#'   (\code{\link{pulso_deflactar}}).
#' @param income_columns Character or NULL. Columns to deflate. Default:
#'   \code{inglabo} (or \code{INGLABO}) when present.
#'
#' @details A warning is raised when the range mixes microdata on the 2005
#'   and the 2018 census frames (2022-01 onwards, and 2020, whose files DANE
#'   re-weighted to the 2018 census): levels and rates are not comparable
#'   across frames.
#'
#' @return A tibble with \code{periodo}, \code{year} and \code{month} columns
#'   plus the module's columns (columns missing in some months are NA there).
#'
#' @examples
#' \donttest{
#' if (interactive()) {
#'   oc <- pulso_load_range("2026-07", "2026-09", "ocupados",
#'                          average_weights = TRUE)
#'   sum(oc$peso_expansion_promedio)  # moving-quarter employed population
#' }
#' }
#'
#' @export
pulso_load_range <- function(start, end, module,
                             harmonize = TRUE,
                             cache = TRUE,
                             strict = FALSE,
                             columns = NULL,
                             average_weights = FALSE,
                             deflate_to = NULL,
                             income_columns = NULL) {
  periods <- .period_range(start, end)
  frames <- vapply(seq_len(nrow(periods)), function(i) {
    .sampling_frame(periods$year[i], periods$month[i])
  }, character(1))
  if (length(unique(frames)) > 1) {
    labels <- sprintf("%d-%02d", periods$year, periods$month)
    detail <- vapply(unique(frames), function(f) {
      v <- labels[frames == f]
      sprintf("marco %s: %s..%s (%d meses)", f, v[1], v[length(v)], length(v))
    }, character(1))
    cli::cli_warn(paste0(
      "The range ", start, "..", end, " mixes microdata on the 2005 and 2018 census ",
      "frames (", paste(detail, collapse = "; "), "). Levels and rates are not ",
      "comparable across frames."
    ))
  }

  parts <- lapply(seq_len(nrow(periods)), function(i) {
    y <- periods$year[i]
    m <- periods$month[i]
    df <- pulso_load(y, m, module, harmonize = harmonize, cache = cache,
                     strict = strict, columns = columns)
    df <- tibble::add_column(df, periodo = sprintf("%d-%02d", y, m), year = y,
                             month = m, .before = 1)
    if (isTRUE(average_weights)) {
      wcol <- .weight_column(names(df))
      if (is.na(wcol)) {
        abort_validation_error(sprintf(
          "No expansion factor column in %d-%02d; include it in `columns`.", y, m
        ))
      }
      df$peso_expansion_promedio <- suppressWarnings(as.numeric(df[[wcol]])) / nrow(periods)
    }
    df
  })
  out <- dplyr::bind_rows(parts)
  if (!is.null(deflate_to)) {
    cols <- income_columns
    if (is.null(cols)) {
      cols <- intersect(c("inglabo", "INGLABO", "ingreso_laboral", "ingreso_total"), names(out))
    }
    out <- pulso_deflactar(out, cols, deflate_to)
  }
  out
}

#' Inclusive data.frame of (year, month) between two "YYYY-MM" strings
#' @noRd
.period_range <- function(start, end) {
  parse_one <- function(x, name) {
    ok <- is.character(x) && length(x) == 1 && grepl("^[0-9]{4}-[0-9]{2}$", x)
    if (ok) {
      y <- as.integer(substr(x, 1, 4))
      m <- as.integer(substr(x, 6, 7))
      ok <- m >= 1 && m <= 12
    }
    if (!ok) abort_validation_error(sprintf("`%s` must be \"YYYY-MM\"", name))
    c(y, m)
  }
  a <- parse_one(start, "start")
  b <- parse_one(end, "end")
  ia <- a[1] * 12 + a[2] - 1
  ib <- b[1] * 12 + b[2] - 1
  if (ia > ib) abort_validation_error("`start` is after `end`")
  idx <- ia:ib
  data.frame(year = as.integer(idx %/% 12), month = as.integer(idx %% 12 + 1))
}

#' Census frame of a period's microdata: "2018" from 2022-01 and in 2020
#'
#' Mirrors `sampling_frame()` in python/pulso/_core/range.py.
#' @noRd
.sampling_frame <- function(year, month) {
  if (year >= 2022 || year == 2020) "2018" else "2005"
}

#' First expansion-factor column among the (raw or lower-cased) names
#' @noRd
.weight_column <- function(names_df) {
  hit <- names_df[grepl("^(fex_c(_[0-9]{4}|18)?)$", names_df, ignore.case = TRUE)]
  if (length(hit) == 0) NA_character_ else hit[1]
}
