#' Normalize DANE zip filename encoding to UTF-8
#'
#' DANE monthly zips are created with legacy DOS/Windows zip tools that
#' default to the CP437 codepage for filenames and do NOT set the zip's
#' UTF-8 flag bit. R's utils::unzip(list=TRUE) returns those names with
#' Encoding() == "unknown" on Linux/Mac. Naive comparison against the
#' UTF-8 paths from sources.json fails, and tolower() / basename() can
#' crash on invalid multibyte sequences under C locale.
#'
#' Byte 0xa1 in CP437 is i-acute ("Caracteristicas"); latin1 misreads it as
#' inverted-exclamation (wrong). Always use CP437 for DANE filenames.
#' @noRd
.normalize_zip_names <- function(zip_contents) {
  unknown <- Encoding(zip_contents) == "unknown"
  if (any(unknown)) {
    zip_contents[unknown] <- iconv(
      zip_contents[unknown],
      from = "CP437",
      to = "UTF-8",
      sub = "?"
    )
  }
  zip_contents
}

#' Detect DANE nested-zip wrapper layout (2024-03, 2024-04)
#'
#' Some DANE releases wrap data files inside a second zip layer; the outer
#' archive contains only CSV.zip / DTA.zip / SAV.zip entries. We don't
#' implement the descent in v0.1.0 -- callers get a clear deferral error.
#' @noRd
.is_nested_zip_wrapper <- function(zip_contents) {
  zip_contents <- .normalize_zip_names(zip_contents)
  entries <- zip_contents[!grepl("/$", zip_contents)]
  if (length(entries) == 0) return(FALSE)
  all(basename(entries) %in% c("CSV.zip", "DTA.zip", "SAV.zip"))
}

#' Resolve a zip member path tolerating case / encoding variations
#'
#' Returns the *original* (possibly CP437) name from zip_contents so that
#' base::unz() can do byte-exact matching against the zip central directory.
#' Comparison is done on normalized UTF-8 strings (locale-safe PCRE, no
#' tolower()), but the returned value is always zip_contents[i], not the
#' UTF-8 form.
#' @noRd
.resolve_zip_path <- function(zip_contents, inner_path) {
  zip_normalized <- .normalize_zip_names(zip_contents)

  if (Encoding(inner_path) == "unknown") {
    inner_path <- iconv(inner_path, from = "CP437", to = "UTF-8", sub = "?")
  }

  idx <- match(inner_path, zip_normalized)
  if (!is.na(idx)) return(zip_contents[idx])

  base_target <- basename(inner_path)
  pattern <- paste0("(?i)^\\Q", base_target, "\\E$")

  for (i in seq_along(zip_normalized)) {
    name_norm <- zip_normalized[i]
    if (grepl("/$", name_norm)) next
    if (grepl(pattern, basename(name_norm), perl = TRUE)) {
      return(zip_contents[i])
    }
  }

  NULL
}

#' Read a single CSV from inside a zip
#'
#' Lists with utils::unzip() (returns raw CP437 bytes that
#' .normalize_zip_names() can convert reliably). Reads with base::unz()
#' which does byte-exact matching against the zip central directory and
#' opens an in-memory connection -- no file is written to disk, so macOS
#' HFS+ UTF-8 filename validation is never triggered.
#' readLines(encoding="Latin-1") decodes the bytes; fread(text=) parses.
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

  con <- unz(zip_path, resolved)
  on.exit(try(close(con), silent = TRUE), add = TRUE)
  lines <- suppressWarnings(readLines(con, encoding = "Latin-1", warn = FALSE))
  if (length(lines) == 0) {
    abort_parse_error(sprintf(
      "Failed to read '%s' from zip %s",
      inner_path, basename(zip_path)
    ))
  }

  data.table::fread(
    text         = paste(lines, collapse = "\n"),
    sep          = "auto",
    header       = TRUE,
    data.table   = FALSE,
    showProgress = FALSE
  )
}

#' Shape A module keyword index (GEIH-1 era, 2007-2020)
#'
#' Ported from python/pulso/_core/parser.py:39 (MODULE_KEYWORDS_GEIH1).
#' DANE filenames in Shape A zips drift across years (typos, missing
#' accents, spacing variants), so sources.json strings cannot be used
#' for literal matching. Keyword discovery against this index is the
#' Python parity behavior -- preserves the 2007 typo "Caractericas"
#' (missing 't') and the no-accent fallback for older fixtures.
#' @noRd
.MODULE_KEYWORDS_GEIH1 <- list(
  caracteristicas_generales = c(
    "Caracter\u00edsticas generales",
    "Caracteristicas generales",
    "Caractericas generales"
  ),
  ocupados             = "Ocupados",
  desocupados          = "Desocupados",
  inactivos            = "Inactivos",
  vivienda_hogares     = "Vivienda y Hogares",
  otros_ingresos       = "Otros ingresos",
  otras_formas_trabajo = "Otras actividades y ayudas",
  fuerza_de_trabajo    = "Fuerza de trabajo"
)

#' Locate Cabecera and Resto files for a module inside a Shape A zip
#'
#' Mirrors python/pulso/_core/parser.py:62 (find_shape_a_files). Scans
#' the zip entries for filenames whose basename starts with "cabecera"
#' or "resto" (case-insensitive) AND contains a module keyword on a
#' word boundary. Files starting with "Area" or any other prefix are
#' silently dropped -- they're auxiliary metadata, not the module data.
#'
#' Returns the original (possibly CP437) names from zip_contents so
#' that base::unz() can do byte-exact matching in .read_single_csv_from_zip().
#' @noRd
.find_shape_a_files <- function(zip_contents, module_name) {
  zip_normalized <- .normalize_zip_names(zip_contents)
  keywords <- .MODULE_KEYWORDS_GEIH1[[module_name]]
  if (is.null(keywords)) keywords <- module_name

  cabecera <- NULL
  resto    <- NULL

  for (i in seq_along(zip_normalized)) {
    name_norm <- zip_normalized[i]
    if (grepl("/$", name_norm)) next

    base <- basename(name_norm)

    if (grepl("(?i)^cabecera", base, perl = TRUE)) {
      prefix <- "cabecera"
    } else if (grepl("(?i)^resto", base, perl = TRUE)) {
      prefix <- "resto"
    } else {
      next
    }

    matched <- FALSE
    for (kw in keywords) {
      # Allow optional trailing digits so e.g. "Ocupados06.csv" matches
      # keyword "Ocupados" (DANE appended year suffixes in 2013-06).
      pattern <- paste0("(?i)\\b\\Q", kw, "\\E\\d*\\b")
      if (grepl(pattern, base, perl = TRUE)) {
        matched <- TRUE
        break
      }
    }
    if (!matched) next

    if (prefix == "cabecera") {
      cabecera <- zip_contents[i]
    } else {
      resto <- zip_contents[i]
    }
  }

  list(cabecera = cabecera, resto = resto)
}

#' Parse a Shape C (COVID-era single-CSV) module from a DANE monthly zip
#'
#' Shape C occurs in 2020-06 and 2020-12 where DANE published a single CSV
#' for modules that normally have Cabecera/Resto pairs (Shape A). The zip
#' does NOT contain files prefixed with "Cabecera" or "Resto"; instead a
#' single CSV matching the module keyword is present.
#' Uses base::unz() connection (no file extraction) so CP437 filenames
#' never touch the filesystem and macOS HFS+ UTF-8 validation is bypassed.
#' @noRd
.parse_shape_c <- function(zip_path, csv_name) {
  con <- unz(zip_path, csv_name)
  on.exit(try(close(con), silent = TRUE), add = TRUE)
  lines <- suppressWarnings(readLines(con, encoding = "Latin-1", warn = FALSE))
  if (length(lines) == 0) {
    abort_parse_error(sprintf(
      "Shape C CSV '%s' not found in zip %s",
      csv_name, basename(zip_path)
    ))
  }
  data.table::fread(
    text         = paste(lines, collapse = "\n"),
    sep          = "auto",
    header       = TRUE,
    data.table   = FALSE,
    showProgress = FALSE
  )
}

#' Locate a single keyword-matching CSV in the zip (Shape C fallback)
#'
#' Scans zip contents for any CSV whose basename contains the module keyword
#' on a word boundary (with optional trailing digits). Returns the original
#' (possibly CP437) name from zip_contents for byte-exact matching by unz().
#' @noRd
.find_shape_c_file <- function(zip_contents, module_name) {
  zip_normalized <- .normalize_zip_names(zip_contents)
  keywords <- .MODULE_KEYWORDS_GEIH1[[module_name]]
  if (is.null(keywords)) keywords <- module_name

  for (i in seq_along(zip_normalized)) {
    name_norm <- zip_normalized[i]
    if (grepl("/$", name_norm)) next
    if (!grepl("\\.csv$", name_norm, ignore.case = TRUE)) next

    base <- basename(name_norm)
    for (kw in keywords) {
      pattern <- paste0("(?i)\\b\\Q", kw, "\\E\\d*\\b")
      if (grepl(pattern, base, perl = TRUE)) {
        return(zip_contents[i])
      }
    }
  }
  NULL
}

#' Parse a module CSV from a DANE monthly zip
#'
#' Dispatches on the module spec shape from sources.json:
#'   Shape A (geih_2006_2020 era): {cabecera, resto} keys signal this
#'     shape; actual filenames are recovered via keyword-based discovery
#'     against the zip contents (mirrors Python's find_shape_a_files).
#'     The sources.json paths for Shape A are aspirational only -- real
#'     DANE filenames drift across years (typos, spacing, encoding).
#'     The two CSVs are concatenated with a synthetic CLASE column
#'     (1 = cabecera, 2 = resto).
#'   Shape B (geih_2021_present era): {file} -> single CSV, read directly
#'     from the literal sources.json path. 2021+ filenames are stable.
#'   Shape C (COVID 2020 variant): module_spec has {cabecera, resto} keys
#'     but the zip does NOT contain Cabecera/Resto files. A single matching
#'     CSV is found by keyword search and read directly (no CLASE split).
#'
#' Nested-zip layout (DANE 2024-03 / 2024-04) is deferred to v0.2.0; we
#' detect and raise pulso_parse_error.
#'
#' @param zip_path Path to outer zip file (already downloaded).
#' @param module_spec Named list from sources.json for the requested module
#'   and period -- either list(file = "...") (Shape B) or
#'   list(cabecera = "...", resto = "...") (Shape A -- keys signal shape,
#'   values are aspirational and ignored at runtime).
#' @param module_name Character. Module name for keyword lookup + errors.
#' @param year Integer. Period year for error messages.
#' @param month Integer. Period month for error messages.
#'
#' @return data.frame with the CSV contents.
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
    files <- .find_shape_a_files(zip_contents, module_name)

    if (!is.null(files$cabecera) && !is.null(files$resto)) {
      # Shape A: Cabecera + Resto pair found
      df_c <- .read_single_csv_from_zip(zip_path, files$cabecera)
      if (!any(toupper(names(df_c)) == "CLASE")) df_c$CLASE <- 1L
      df_r <- .read_single_csv_from_zip(zip_path, files$resto)
      if (!any(toupper(names(df_r)) == "CLASE")) df_r$CLASE <- 2L
      # DANE CSVs sometimes encode the same column as different types across
      # Cabecera/Resto files (e.g. RAMA4DP8 as integer vs character).
      # Coerce shared columns to character when types are incompatible so
      # that dplyr::bind_rows() (vctrs-backed) doesn't abort.
      for (.col in intersect(names(df_c), names(df_r))) {
        if (!identical(class(df_c[[.col]]), class(df_r[[.col]]))) {
          df_c[[.col]] <- as.character(df_c[[.col]])
          df_r[[.col]] <- as.character(df_r[[.col]])
        }
      }
      return(dplyr::bind_rows(df_c, df_r))
    }

    # Shape C fallback: module_spec signals Shape A but zip has no
    # Cabecera/Resto files (COVID periods 2020-06, 2020-12).
    shape_c_file <- .find_shape_c_file(zip_contents, module_name)
    if (!is.null(shape_c_file)) {
      return(.parse_shape_c(zip_path, shape_c_file))
    }

    keywords <- .MODULE_KEYWORDS_GEIH1[[module_name]]
    if (is.null(keywords)) keywords <- module_name
    abort_parse_error(sprintf(
      "Shape A/C files for module '%s' (%d-%02d) not found in zip. Tried keywords: %s",
      module_name, year, month, paste(keywords, collapse = ", ")
    ))
  }

  abort_parse_error(sprintf(
    "Module spec for '%s' (%d-%02d) has unknown shape (keys: %s)",
    module_name, year, month,
    paste(names(module_spec), collapse = ", ")
  ))
}
