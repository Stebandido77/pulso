#' Parse a specific module CSV from a zip
#'
#' @param zip_path Path to zip file.
#' @param module Module name (e.g., "ocupados").
#'
#' @return data.frame with the CSV contents.
#' @noRd
.parse_module_csv <- function(zip_path, module) {
  zip_contents <- utils::unzip(zip_path, list = TRUE)$Name

  module_pattern <- sprintf("(?i)%s", module)
  csv_match <- grep(module_pattern, zip_contents, value = TRUE)
  csv_match <- csv_match[grepl("\\.csv$", csv_match, ignore.case = TRUE)]

  if (length(csv_match) == 0) {
    abort_module_not_available(
      module,
      year = NA,
      month = NA
    )
  }

  csv_name <- csv_match[1]

  temp_dir <- tempfile()
  fs::dir_create(temp_dir)
  on.exit(fs::dir_delete(temp_dir), add = TRUE)

  utils::unzip(zip_path, files = csv_name, exdir = temp_dir)
  csv_path <- fs::path(temp_dir, csv_name)

  df <- utils::read.csv(
    csv_path,
    sep = ";",
    fileEncoding = "latin1",
    stringsAsFactors = FALSE,
    check.names = FALSE
  )

  df
}
