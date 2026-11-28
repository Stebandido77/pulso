#' Normalize DANE zip filename encoding to UTF-8
#'
#' DANE monthly zips mix two filename encodings, sometimes inside the same
#' archive: entries written by legacy DOS/Windows tools use CP437 without
#' the zip UTF-8 flag, while newer entries (2024-11 onwards) are UTF-8 with
#' the flag set. utils::unzip(list = TRUE) returns both as raw bytes with
#' Encoding() == "unknown", so each name is decoded individually: if the
#' bytes are valid UTF-8 they are kept as UTF-8, otherwise they are decoded
#' from CP437 (byte 0xa1 in CP437 is i-acute, which latin1 would misread).
#' @noRd
.normalize_zip_names <- function(zip_contents) {
  out <- zip_contents
  for (i in seq_along(out)) {
    x <- out[i]
    if (Encoding(x) != "unknown") next
    if (!grepl("[^\x01-\x7f]", x, useBytes = TRUE)) next
    if (validUTF8(x)) {
      Encoding(x) <- "UTF-8"
    } else {
      x <- iconv(x, from = "CP437", to = "UTF-8", sub = "?")
    }
    out[i] <- x
  }
  .mark_utf8(out)
}

#' Comparison key for DANE filenames
#'
#' Folds the cosmetic variations DANE introduces between releases so that
#' a sources.json path still matches the real zip member: non-breaking
#' spaces (U+00A0, present since 2025-12), repeated whitespace, accents,
#' letter case, and the file extension (.CSV vs .csv since 2026-08).
#' @noRd
.name_key <- function(x, drop_ext = TRUE) {
  # Byte-level replacements so this works in any locale (including C).
  x <- .mark_utf8(as.character(x))
  from <- c("\u00a0", "\u00e1", "\u00e9", "\u00ed", "\u00f3", "\u00fa",
            "\u00fc", "\u00f1", "\u00c1", "\u00c9", "\u00cd", "\u00d3",
            "\u00da", "\u00dc", "\u00d1")
  to <- c(" ", "a", "e", "i", "o", "u", "u", "n", "a", "e", "i", "o", "u",
          "u", "n")
  for (k in seq_along(from)) {
    x <- gsub(from[k], to[k], x, fixed = TRUE, useBytes = TRUE)
  }
  x <- iconv(x, from = "UTF-8", to = "ASCII", sub = "?")
  x[is.na(x)] <- ""
  x <- tolower(x)
  if (drop_ext) x <- sub("\\.[a-z0-9]{2,4}$", "", x)
  x <- gsub("[[:space:]_]+", " ", x)
  trimws(x)
}

#' Locale-safe basename (base::basename() can fail to translate UTF-8
#' names to the native encoding under a C locale)
#' @noRd
.base_name <- function(x) .mark_utf8(sub("^.*/", "", x, useBytes = TRUE))

#' Mark valid-UTF-8 strings as UTF-8 without re-encoding them (enc2utf8()
#' on an "unknown" string re-encodes from the native locale, which under C
#' turns bytes into literal "<c3><ad>" escapes)
#' @noRd
.mark_utf8 <- function(x) {
  x <- as.character(x)
  ok <- !is.na(x) & validUTF8(x)
  Encoding(x[ok]) <- "UTF-8"
  x
}

#' Basename of an inner format zip in a nested DANE wrapper: format tag,
#' optional " <n>" counter, ".zip". Seen: CSV.zip (2024-03), CSV 4.zip
#' (2022-10), CSV 13.zip / SAV 12.zip (2023-09), DTA 9.zip (2023-04),
#' DAT.zip (2023-08). Mirrors _NESTED_WRAPPER_RE in python/pulso/_core/parser.py.
#' @noRd
.NESTED_WRAPPER_RE <- "(?i)^(CSV|DTA|DAT|SAV)( [0-9]+)?\\.zip$"

#' Detect DANE nested-zip wrapper layout (2022-10, 2023-04/08/09, 2024-03/04)
#'
#' Some DANE releases wrap data files inside a second zip layer; every
#' entry of the outer archive is an inner format zip (see .NESTED_WRAPPER_RE).
#' @noRd
.is_nested_zip_wrapper <- function(zip_contents) {
  zip_contents <- .normalize_zip_names(zip_contents)
  entries <- zip_contents[!grepl("/$", zip_contents)]
  if (length(entries) == 0) return(FALSE)
  bases <- vapply(entries, .base_name, character(1), USE.NAMES = FALSE)
  all(grepl(.NESTED_WRAPPER_RE, bases, perl = TRUE))
}

#' Extract the inner CSV zip of a nested DANE wrapper (cached next to it)
#' @noRd
.unwrap_nested_zip <- function(zip_path) {
  zip_contents <- suppressWarnings(utils::unzip(zip_path, list = TRUE)$Name)
  bases <- vapply(zip_contents, .base_name, character(1), USE.NAMES = FALSE)
  inner <- zip_contents[grepl(.NESTED_WRAPPER_RE, bases, perl = TRUE) &
                          grepl("(?i)^CSV", bases, perl = TRUE)]
  if (length(inner) == 0) {
    abort_parse_error(sprintf(
      "Nested zip %s has no CSV.zip member", basename(zip_path)
    ))
  }
  target <- paste0(sub("\\.zip$", "", zip_path), "__CSV.zip")
  if (!file.exists(target)) {
    exdir <- tempfile("pulso_nested_")
    dir.create(exdir)
    on.exit(unlink(exdir, recursive = TRUE), add = TRUE)
    utils::unzip(zip_path, files = inner[1], exdir = exdir, junkpaths = TRUE)
    ok <- file.copy(file.path(exdir, .base_name(inner[1])), target, overwrite = TRUE)
    if (!ok) {
      abort_parse_error(sprintf(
        "Could not extract CSV.zip from %s", basename(zip_path)
      ))
    }
  }
  if (!.is_valid_zip(target)) {
    unlink(target)
    abort_parse_error(sprintf(
      "Inner CSV.zip of nested zip %s is not a valid zip archive",
      basename(zip_path)
    ))
  }
  target
}

#' Shape B keyword index (redesigned GEIH, 2022+)
#'
#' Used when neither the literal sources.json path nor its folded form
#' matches, e.g. 2026-04 where DANE renamed the characteristics file to
#' "Capitulos de caracteristicas generales ...". Patterns run against
#' .name_key(basename) (lowercase, no accents, no extension).
#' @noRd
.MODULE_KEYWORDS_GEIH2 <- list(
  caracteristicas_generales = "caracteristicas generales",
  ocupados                  = "^ocupados$",
  desocupados               = "^no ocupados?$",
  inactivos                 = "^no ocupados?$",
  vivienda_hogares          = "hogar y la vivienda",
  otros_ingresos            = "^otros ingresos",
  migracion                 = "^migracion$",
  otras_formas_trabajo      = "^otras formas de trabajo$",
  fuerza_de_trabajo         = "^fuerza de trabajo$"
)

#' Resolve a zip member path tolerating case / encoding variations
#'
#' Returns the *original* (raw-byte) name from zip_contents so that
#' base::unz() can do byte-exact matching against the zip central
#' directory. Matching tiers: exact UTF-8 path, folded full path, folded
#' basename, and finally the module keyword index.
#' @noRd
.resolve_zip_path <- function(zip_contents, inner_path, module_name = NULL) {
  zip_normalized <- .normalize_zip_names(zip_contents)
  is_file <- !grepl("/$", zip_normalized)

  inner_path <- .normalize_zip_names(inner_path)

  idx <- match(inner_path, zip_normalized)
  if (!is.na(idx)) return(zip_contents[idx])

  keys_full <- .name_key(zip_normalized)
  idx <- which(is_file & keys_full == .name_key(inner_path))
  if (length(idx) >= 1) return(zip_contents[idx[1]])

  # The same table can ship as .csv, .dta and .sav: candidates with the
  # requested extension win over the rest (pulso #78).
  ext_of <- function(x) tolower(sub("^.*\\.", "", .base_name(x)))
  same_ext <- ext_of(zip_normalized) == ext_of(inner_path)
  keys_base <- .name_key(.base_name(zip_normalized))
  hit <- is_file & keys_base == .name_key(.base_name(inner_path))
  idx <- c(which(hit & same_ext), which(hit & !same_ext))
  if (length(idx) >= 1) return(zip_contents[idx[1]])

  pattern <- if (!is.null(module_name)) .MODULE_KEYWORDS_GEIH2[[module_name]]
  if (!is.null(pattern)) {
    is_csv <- grepl("(?i)\\.csv$", zip_normalized, perl = TRUE)
    idx <- which(is_file & is_csv & grepl(pattern, keys_base, perl = TRUE))
    if (length(idx) >= 1) return(zip_contents[idx[1]])
  }

  NULL
}

#' Read a zip member (by raw name) into a data.frame
#'
#' Streams the member through base::unz() (byte-exact name match, no
#' extraction under the original CP437/UTF-8 name, so macOS HFS+ filename
#' validation is never triggered) into a temporary file with an ASCII
#' name, then parses it with data.table::fread(). The text encoding is
#' sniffed (DANE ships Latin-1, a few releases ship UTF-8) and the decimal
#' mark follows the separator: DANE ';'-separated files use ',' decimals.
#' @noRd
.read_zip_member <- function(zip_path, member, label = member, select = NULL) {
  tmp <- tempfile("pulso_", fileext = ".csv")
  on.exit(unlink(tmp), add = TRUE)

  con <- unz(zip_path, member, open = "rb")
  out <- file(tmp, open = "wb")
  n_bytes <- 0
  tryCatch({
    repeat {
      chunk <- readBin(con, what = "raw", n = 8 * 1024 * 1024)
      if (length(chunk) == 0) break
      writeBin(chunk, out)
      n_bytes <- n_bytes + length(chunk)
    }
  }, finally = {
    close(out)
    close(con)
  })

  if (n_bytes == 0) {
    abort_parse_error(sprintf(
      "Failed to read '%s' from zip %s (empty member)",
      label, basename(zip_path)
    ))
  }

  sample <- readBin(tmp, what = "raw", n = 2 * 1024 * 1024)
  nl <- which(sample == as.raw(0x0a))
  if (length(nl) > 0) sample <- sample[seq_len(max(nl))]
  has_bom <- length(sample) >= 3 && identical(sample[1:3], as.raw(c(0xef, 0xbb, 0xbf)))
  sample_chr <- rawToChar(sample[sample != as.raw(0)])
  is_utf8 <- has_bom || validUTF8(sample_chr)
  encoding <- if (is_utf8) "UTF-8" else "Latin-1"

  first_line <- sub("[\r\n].*$", "", sample_chr, useBytes = TRUE)
  sep <- if (grepl(";", first_line, fixed = TRUE, useBytes = TRUE)) {
    ";"
  } else if (grepl("\t", first_line, fixed = TRUE, useBytes = TRUE)) {
    "\t"
  } else {
    ","
  }
  dec <- .sniff_decimal(sample_chr, sep)

  keep <- NULL
  if (!is.null(select)) {
    header <- names(data.table::fread(
      file = tmp, sep = sep, header = TRUE, nrows = 0, encoding = encoding,
      showProgress = FALSE
    ))
    keep <- header[.canon_col(header) %in% select]
    if (length(keep) == 0) keep <- NULL
  }

  df <- data.table::fread(
    file         = tmp,
    sep          = sep,
    dec          = dec,
    header       = TRUE,
    encoding     = encoding,
    data.table   = FALSE,
    showProgress = FALSE,
    select       = keep
  )

  names(df) <- sub("^\ufeff", "", enc2utf8(names(df)))
  if (encoding == "Latin-1") {
    for (j in seq_along(df)) {
      if (is.character(df[[j]])) df[[j]] <- enc2utf8(df[[j]])
    }
  }
  df
}

#' Comparison key for a column name: no BOM, upper case, FEX_C_2011 -> FEX_C
#'
#' Used to match `columns =` requests against raw DANE headers. Mirrors
#' `_canon_col()` in python/pulso/_core/parser.py.
#' @noRd
.canon_col <- function(x) {
  x <- gsub("\ufeff", "", as.character(x), fixed = TRUE)
  x <- toupper(trimws(x))
  sub("^FEX_C_[0-9]{4}$", "FEX_C", x)
}

#' Infer the decimal mark of a DANE CSV from its first data lines
#'
#' DANE is not consistent: older ';'-separated files use ',' decimals, while
#' the 2018-frame files (2022+) use ';' with '.' decimals ("43.55418099").
#' Counts numeric tokens of each kind in up to 200 data lines; ties (no
#' decimals at all) fall back to ',' for ';' files.
#' @noRd
.sniff_decimal <- function(sample_chr, sep) {
  if (sep == ",") return(".")
  lines <- strsplit(sample_chr, "\r?\n", useBytes = TRUE)[[1]]
  lines <- utils::head(lines[-1], 200)
  if (length(lines) == 0) return(",")
  fields <- unlist(strsplit(lines, sep, fixed = TRUE, useBytes = TRUE))
  fields <- gsub("^[ \t]+|[ \t\r]+$", "", fields, useBytes = TRUE)
  dots <- sum(grepl("^-?[0-9]+\\.[0-9]+$", fields, useBytes = TRUE))
  commas <- sum(grepl("^-?[0-9]+,[0-9]+$", fields, useBytes = TRUE))
  if (dots > commas) "." else ","
}

#' Read a single CSV from inside a zip
#' @noRd
.read_single_csv_from_zip <- function(zip_path, inner_path, module_name = NULL,
                                      select = NULL) {
  zip_contents <- suppressWarnings(utils::unzip(zip_path, list = TRUE)$Name)

  resolved <- .resolve_zip_path(zip_contents, inner_path, module_name)
  if (is.null(resolved)) {
    available <- .normalize_zip_names(zip_contents)
    available <- available[grepl("(?i)\\.csv$", available, perl = TRUE)]
    abort_parse_error(sprintf(
      "Expected file '%s' not found inside zip %s. CSV files present: %s",
      inner_path, basename(zip_path),
      if (length(available)) paste(available, collapse = "; ") else "(none)"
    ))
  }

  .read_zip_member(zip_path, resolved, label = inner_path, select = select)
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
  # 2020 Shape C typos: "Descupados" (2020-05), "Desoucpados" (2020-09/10).
  desocupados          = c("Desocupados", "Descupados", "Desoucpados"),
  # 2020 Shape C typos: "Ianctivos" (2020-07), "Inativos" (2020-10).
  inactivos            = c("Inactivos", "Ianctivos", "Inativos"),
  vivienda_hogares     = "Vivienda y Hogares",
  otros_ingresos       = "Otros ingresos",
  otras_formas_trabajo = "Otras actividades y ayudas",
  # 2020 Shape C typo: "Fuerzo de trabajo" (2020-11).
  fuerza_de_trabajo    = c("Fuerza de trabajo", "Fuerzo de trabajo")
)

#' DANE labor-force flag of each GEIH-1 condition file
#'
#' GEIH-1 ships one file per labor-force condition, so every row of the
#' Ocupados / Desocupados / Inactivos files is in that condition. The flag
#' columns (OCI / DSI / INI = 1) are missing in some releases (all three in
#' 2007-01..11, INI in 2007-12); .ensure_labor_flag() fills them from the
#' file. Mirrors LABOR_FLAG_GEIH1 in python/pulso/_core/parser.py.
#' @noRd
.LABOR_FLAG_GEIH1 <- c(ocupados = "OCI", desocupados = "DSI", inactivos = "INI")

#' @noRd
.ensure_labor_flag <- function(df, module_name) {
  flag <- unname(.LABOR_FLAG_GEIH1[module_name])
  if (length(flag) == 1 && !is.na(flag) && !(flag %in% names(df))) df[[flag]] <- 1L
  df
}

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

    base <- .base_name(name_norm)

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
#' for modules that normally have Cabecera/Resto pairs (Shape A).
#' @noRd
.parse_shape_c <- function(zip_path, csv_name, select = NULL) {
  .read_zip_member(zip_path, csv_name, select = select)
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

    base <- .base_name(name_norm)
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
#' Nested-zip layout (DANE 2024-03 / 2024-04): the inner CSV.zip is
#' extracted once next to the cached outer zip and parsed transparently.
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
.parse_module_csv <- function(zip_path, module_spec, module_name, year, month,
                              select = NULL) {
  zip_contents <- suppressWarnings(utils::unzip(zip_path, list = TRUE)$Name)

  if (.is_nested_zip_wrapper(zip_contents)) {
    zip_path <- .unwrap_nested_zip(zip_path)
    zip_contents <- suppressWarnings(utils::unzip(zip_path, list = TRUE)$Name)
  }

  if (!is.null(module_spec$file)) {
    return(.read_single_csv_from_zip(zip_path, module_spec$file, module_name, select))
  }

  if (!is.null(module_spec$cabecera) && !is.null(module_spec$resto)) {
    files <- .find_shape_a_files(zip_contents, module_name)

    if (!is.null(files$cabecera) && !is.null(files$resto)) {
      # Shape A: Cabecera + Resto pair found
      df_c <- .read_single_csv_from_zip(zip_path, files$cabecera, select = select)
      if (!any(toupper(names(df_c)) == "CLASE")) df_c$CLASE <- 1L
      df_r <- .read_single_csv_from_zip(zip_path, files$resto, select = select)
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
      return(.ensure_labor_flag(dplyr::bind_rows(df_c, df_r), module_name))
    }

    # Shape C fallback: module_spec signals Shape A but zip has no
    # Cabecera/Resto files (COVID periods 2020-06, 2020-12).
    shape_c_file <- .find_shape_c_file(zip_contents, module_name)
    if (!is.null(shape_c_file)) {
      return(.ensure_labor_flag(.parse_shape_c(zip_path, shape_c_file, select), module_name))
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
