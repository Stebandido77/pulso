# ---- Date validation -------------------------------------------------------

.validate_banrep_date <- function(x, arg_name) {
  if (inherits(x, "Date")) return(x)
  parsed <- tryCatch(as.Date(x), error = function(e) NA_real_)
  if (is.na(parsed)) {
    cli::cli_abort(
      "{.arg {arg_name}} must be a Date or {.val YYYY-MM-DD} string, got {.val {x}}"
    )
  }
  parsed
}

# ---- API availability ------------------------------------------------------

.banrep_api_available <- function(timeout = 5) {
  url <- paste0(
    "https://totoro.banrep.gov.co/nsi-jax-ws/rest/data/",
    "ESTAT,DF_CBR_DAILY_HIST,1.0/all/ALL/",
    "?startPeriod=2025&endPeriod=2026"
  )
  result <- tryCatch({
    resp <- httr2::request(url) |>
      httr2::req_timeout(timeout) |>
      httr2::req_perform()
    httr2::resp_status(resp) == 200L
  }, error = function(e) FALSE)
  result
}

# ---- Fixture loader --------------------------------------------------------

.tpm_from_fixture <- function(start = NULL, end = NULL) {
  fixture_path <- system.file(
    "extdata", "tpm_jdbr_manual_20260422.xlsx",
    package = "pulso"
  )
  if (nchar(fixture_path) == 0L) {
    cli::cli_abort("TPM fixture not found in package extdata.")
  }

  # Sheet "Datos": row 0 = column names, row 1 = units (skip), rows 2+ = data
  # Dates stored as "dd/mm/yyyy" strings; values as "3,50" strings.
  raw <- suppressMessages(readxl::read_excel(
    fixture_path,
    sheet     = "Datos",
    col_names = TRUE,
    skip      = 1L,          # skip the units row (row index 1 after header)
    col_types = "text"        # read everything as text to control parsing
  ))

  fecha_col <- raw[[1]]
  valor_col <- raw[[2]]   # "Tasa de politica monetaria(Dato diario)"

  fecha <- as.Date(fecha_col, format = "%d/%m/%Y")
  valor <- suppressWarnings(
    as.numeric(gsub(",", ".", valor_col, fixed = TRUE))
  )

  df <- tibble::tibble(fecha = fecha, valor = valor, serie = "tpm")
  df <- df[!is.na(df$fecha) & !is.na(df$valor), ]

  if (!is.null(start)) df <- df[df$fecha >= start, ]
  if (!is.null(end))   df <- df[df$fecha <= end,   ]

  df
}

# ---- API fetcher -----------------------------------------------------------

.tpm_from_api <- function(start = NULL, end = NULL) {
  base <- "https://totoro.banrep.gov.co/nsi-jax-ws/rest/data"

  year_start <- if (!is.null(start)) format(start, "%Y") else "2010"
  # endPeriod is exclusive on year granularity; add 1 to include current year
  year_end <- if (!is.null(end)) {
    as.character(as.integer(format(end, "%Y")) + 1L)
  } else {
    "2027"
  }

  url <- sprintf(
    "%s/ESTAT,DF_CBR_DAILY_HIST,1.0/all/ALL/?startPeriod=%s&endPeriod=%s",
    base, year_start, year_end
  )

  resp <- httr2::request(url) |>
    httr2::req_headers(Accept = "application/xml") |>
    httr2::req_timeout(30L) |>
    httr2::req_perform()

  xml_doc <- httr2::resp_body_xml(resp)
  df <- .parse_sdmx_xml(xml_doc, serie_name = "tpm")

  if (!is.null(start)) df <- df[df$fecha >= start, ]
  if (!is.null(end))   df <- df[df$fecha <= end,   ]
  df
}

# ---- SDMX-ML 2.1 parser (generic, reusable for IBR in v0.2.0) -------------

.parse_sdmx_xml <- function(xml_doc, serie_name) {
  ns <- c(g = "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic")

  obs_nodes <- xml2::xml_find_all(xml_doc, "//g:Obs", ns)

  fechas  <- character(length(obs_nodes))
  valores <- numeric(length(obs_nodes))

  for (i in seq_along(obs_nodes)) {
    obs   <- obs_nodes[[i]]
    dim_n <- xml2::xml_find_first(obs, "g:ObsDimension", ns)
    val_n <- xml2::xml_find_first(obs, "g:ObsValue",     ns)
    fechas[[i]]  <- xml2::xml_attr(dim_n, "value")
    valores[[i]] <- suppressWarnings(
      as.numeric(xml2::xml_attr(val_n, "value"))
    )
  }

  tibble::tibble(
    fecha  = as.Date(fechas, format = "%Y%m%d"),
    valor  = valores,
    serie  = serie_name
  )
}
