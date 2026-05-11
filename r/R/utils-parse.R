#' Detect DANE nested-zip wrapper layout (2024-03, 2024-04)
#'
#' Some DANE releases wrap data files inside a second zip layer; the outer
#' archive contains only CSV.zip / DTA.zip / SAV.zip entries. We don't
#' implement the descent in v0.1.0 — callers get a clear deferral error.
#' @noRd
.is_nested_zip_wrapper <- function(zip_contents) {
  entries <- zip_contents[!grepl("/$", zip_contents)]
  if (length(entries) == 0) return(FALSE)
  basenames <- basename(entries)
  all(basenames %in% c("CSV.zip", "DTA.zip", "SAV.zip"))
}

#' Resolve a zip member path tolerating case / encoding variations
#'
#' Order: (1) exact, (2) latin-1 → UTF-8 reinterpretation, (3)
#' case-insensitive basename match across all entries.
#' @noRd
.resolve_zip_path <- function(zip_contents, inner_path) {
  if (inner_path %in% zip_contents) return(inner_path)

  fixed <- tryCatch(
    iconv(inner_path, from = "latin1", to = "UTF-8"),
    error = function(e) inner_path
  )
  if (!is.na(fixed) && fixed %in% zip_contents) return(fixed)

  target <- tolower(basename(inner_path))
  entries <- zip_contents[!grepl("/$", zip_contents)]
  for (name in entries) {
    if (tolower(basename(name)) == target) return(name)
  }

  NULL
}

#' Read a single CSV from inside a zip
#'
#' Extracts to a temp dir and reads with latin-1 encoding + ";" separator
#' (DANE convention). Resolves the inner path case-insensitively.
#' @noRd
.read_single_csv_from_zip <- function(zip_path, inner_path) {
  zip_contents <- suppressWarnings(utils::unzip(zip_path, list = TRUE)$Name)

  resolved <- .resolve_zip_path(zip_contents, inner_path)
  if (is.null(resolved)) {
    abort_parse_error(sprintf(
      "Expected file '%s' not found inside zip %s",
      inner_path, basename(zip_path)
    ))
  }

  temp_dir <- tempfile()
  fs::dir_create(temp_dir)
  on.exit(fs::dir_delete(temp_dir), add = TRUE)

  utils::unzip(zip_path, files = resolved, exdir = temp_dir)
  csv_path <- fs::path(temp_dir, resolved)

  utils::read.csv(
    csv_path,
    sep = ";",
    fileEncoding = "latin1",
    stringsAsFactors = FALSE,
    check.names = FALSE
  )
}

#' Parse a module CSV from a DANE monthly zip
#'
#' Dispatches on the module spec shape from sources.json:
#'   Shape A (geih_2006_2020 era): {cabecera, resto} → two CSVs, concat
#'     with synthetic CLASE column (1 = cabecera, 2 = resto).
#'   Shape B (geih_2021_present era): {file} → single CSV, read directly.
#'
#' Nested-zip layout (DANE 2024-03 / 2024-04) is deferred to v0.2.0; we
#' detect and raise pulso_parse_error.
#'
#' @param zip_path Path to outer zip file (already downloaded).
#' @param module_spec Named list from sources.json for the requested module
#'   and period — either list(file = "...") or list(cabecera = "...",
#'   resto = "...").
#' @param module_name Character. Module name for error messages.
#' @param year Integer. Period year for error messages.
#' @param month Integer. Period month for error messages.
#'
#' @return data.frame with the CSV contents.
#' @importFrom utils read.csv unzip
#' @noRd
.parse_module_csv <- function(zip_path, module_spec, module_name, year, month) {
  zip_contents <- suppressWarnings(utils::unzip(zip_path, list = TRUE)$Name)

  if (.is_nested_zip_wrapper(zip_contents)) {
    abort_parse_error(sprintf(
      "Period %d-%02d uses a nested-zip layout (CSV.zip wrapper) that is not yet supported in pulso v0.1.0. Planned for v0.2.0. See https://github.com/Stebandido77/pulso/issues/61",
      year, month
    ))
  }

  if (!is.null(module_spec$file)) {
    return(.read_single_csv_from_zip(zip_path, module_spec$file))
  }

  if (!is.null(module_spec$cabecera) && !is.null(module_spec$resto)) {
    df_c <- .read_single_csv_from_zip(zip_path, module_spec$cabecera)
    df_c$CLASE <- 1L
    df_r <- .read_single_csv_from_zip(zip_path, module_spec$resto)
    df_r$CLASE <- 2L
    return(rbind(df_c, df_r))
  }

  abort_parse_error(sprintf(
    "Module spec for '%s' (%d-%02d) has unknown shape (keys: %s)",
    module_name, year, month,
    paste(names(module_spec), collapse = ", ")
  ))
}
