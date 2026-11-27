# Offline regression tests for DANE filename quirks (pulso 0.2.0).
# Fixtures are built by scripts/build_r_name_fixtures.py and mimic real
# DANE releases: mixed CP437 / UTF-8 names (2024-11+), non-breaking
# spaces (2025-12+), renamed files and lowercase .csv (2026-04, 2026-08),
# and the nested CSV.zip wrapper (2024-03 / 2024-04).

fixture <- function(name) testthat::test_path("fixtures", name)

spec_2026 <- function(module, period = "2026-02") {
  .load_sources()$data[[period]]$modules[[module]]
}

test_that(".normalize_zip_names decodes CP437 and UTF-8 names in the same zip", {
  raw_names <- suppressWarnings(
    utils::unzip(fixture("dane_mixed_names.zip"), list = TRUE)$Name
  )
  decoded <- .normalize_zip_names(raw_names)
  expect_true(all(validUTF8(decoded)))
  expect_true(any(grepl("Características generales", decoded, fixed = TRUE)))
  expect_true(any(grepl("Migración", decoded, fixed = TRUE)))
})

test_that("every redesigned-GEIH module resolves despite NBSP and encoding drift", {
  modules <- c("caracteristicas_generales", "vivienda_hogares", "ocupados",
               "desocupados", "migracion", "otras_formas_trabajo",
               "otros_ingresos")
  for (m in modules) {
    df <- .parse_module_csv(fixture("dane_mixed_names.zip"), spec_2026(m), m, 2026, 2)
    expect_equal(nrow(df), 2, info = m)
  }
})

test_that("ocupados never resolves to 'No ocupados'", {
  contents <- c("CSV/No ocupados.csv", "CSV/Ocupados.csv")
  expect_equal(
    .resolve_zip_path(contents, "CSV/Ocupados.CSV", "ocupados"),
    "CSV/Ocupados.csv"
  )
  expect_equal(
    .resolve_zip_path(contents, "CSV/No ocupados.CSV", "desocupados"),
    "CSV/No ocupados.csv"
  )
})

test_that("renamed caracteristicas file (2026-04) and lowercase .csv resolve by keyword", {
  df <- .parse_module_csv(
    fixture("dane_renamed.zip"),
    list(file = "CSV/Características generales, seguridad social en salud y educación.CSV"),
    "caracteristicas_generales", 2026, 4
  )
  expect_equal(nrow(df), 2)
})

test_that("nested CSV.zip wrapper (2024-03/04) is unwrapped transparently", {
  tmp <- tempfile(fileext = ".zip")
  file.copy(fixture("dane_nested.zip"), tmp)
  on.exit(unlink(c(tmp, sub("\\.zip$", "__CSV.zip", tmp))), add = TRUE)
  df <- .parse_module_csv(tmp, list(file = "CSV/Ocupados.CSV"), "ocupados", 2024, 3)
  expect_equal(nrow(df), 2)
})

test_that("Latin-1 text is converted to UTF-8 and comma decimals are numeric", {
  df <- .parse_module_csv(fixture("dane_mixed_names.zip"), spec_2026("ocupados"),
                          "ocupados", 2026, 2)
  expect_equal(df$NOMBRE, c("Bogotá", "Medellín"))
  expect_type(df$FEX_C18, "double")
  expect_equal(df$FEX_C18, c(100.5, 90.25))
})

test_that("missing module error lists the CSVs that are present", {
  expect_error(
    .read_single_csv_from_zip(fixture("dane_renamed.zip"), "CSV/Migración.CSV", "migracion"),
    class = "pulso_parse_error",
    regexp = "CSV files present"
  )
})

test_that("catalog covers DANE releases through 2026-09", {
  periods <- names(.load_sources()$data)
  expect_true(all(sprintf("2026-%02d", 1:9) %in% periods))
})

test_that("strict / allow_unvalidated resolution", {
  expect_false(.resolve_strict(FALSE, NULL))
  expect_true(.resolve_strict(TRUE, NULL))
  expect_warning(res <- .resolve_strict(FALSE, FALSE), "deprecated")
  expect_true(res)
  expect_error(.resolve_strict(NA, NULL), class = "pulso_validation_error")
})

test_that(".download_zip discards a corrupt cached file instead of parsing it", {
  withr::local_options(pulso.cache_dir = tempfile("pulso_cache_"), pulso.max_tries = 1)
  url <- "https://example.invalid/file.zip"
  key <- substr(digest::digest(url, algo = "sha1", serialize = FALSE), 1, 10)
  path <- file.path(.cache_dir(), "raw", "2026", sprintf("01_%s.zip", key))
  dir.create(dirname(path), recursive = TRUE)
  writeLines("<html>not a zip</html>", path)
  expect_false(.is_valid_zip(path))
  expect_error(.download_zip(url, 2026, 1), class = "pulso_download_error")
  expect_false(file.exists(path))
})

test_that("pulso_update_catalog saves a newer catalog and pulso uses it", {
  withr::local_options(pulso.cache_dir = tempfile("pulso_cache_"))
  .load_sources(reset = TRUE)
  withr::defer(.load_sources(reset = TRUE))

  src <- .load_sources()
  newer <- src
  newer$data[["2099-01"]] <- src$data[[max(names(src$data))]]
  newer$metadata$covered_range <- list("2007-01", "2099-01")
  path <- tempfile(fileext = ".json")
  jsonlite::write_json(newer, path, auto_unbox = TRUE, null = "null")

  res <- pulso_update_catalog(url = paste0("file://", path))
  expect_equal(res$latest_end, "2099-01")
  expect_false(is.null(res$path))
  expect_true("2099-01" %in% names(.load_sources()$data))

  # An older catalog never replaces the one in use
  res2 <- pulso_update_catalog(url = paste0("file://", path))
  expect_null(res2$path)
})

test_that("pulso_update_catalog rejects a file that is not a catalog", {
  withr::local_options(pulso.cache_dir = tempfile("pulso_cache_"))
  .load_sources(reset = TRUE)
  withr::defer(.load_sources(reset = TRUE))
  path <- tempfile(fileext = ".json")
  writeLines("<html>nope</html>", path)
  expect_error(pulso_update_catalog(url = paste0("file://", path)),
               class = "pulso_parse_error")
})

test_that("';' files with point decimals keep weights numeric (#77)", {
  df <- .parse_module_csv(fixture("dane_point_decimal.zip"),
                          list(file = "CSV/Ocupados.CSV"), "ocupados", 2026, 9)
  expect_type(df$FEX_C18, "double")
  expect_equal(df$FEX_C18, c(43.55418099, 34.68595437))
  # leading-zero codes stay as they were parsed before (no forced coercion)
  expect_equal(nrow(df), 2)
})

test_that("CSV wins over a DTA with the same folded name (#78)", {
  df <- .parse_module_csv(fixture("dane_point_decimal.zip"),
                          list(file = "DTA_ignored/Datos del hogar y la vivienda.CSV"),
                          "vivienda_hogares", 2026, 9)
  expect_equal(nrow(df), 2)
  expect_type(df$FEX_C18, "double")
})

test_that(".sniff_decimal decides from the data", {
  expect_equal(.sniff_decimal("A;B\n1;43.5\n2;1.25\n", ";"), ".")
  expect_equal(.sniff_decimal("A;B\n1;43,5\n2;1,25\n", ";"), ",")
  expect_equal(.sniff_decimal("A;B\n1;2\n", ";"), ",")
  expect_equal(.sniff_decimal("A,B\n1,2\n", ","), ".")
})

test_that(".warn_unvalidated_once warns once per period per session", {
  old <- .pulso_state$warned_periods
  withr::defer(.pulso_state$warned_periods <- old)
  .pulso_state$warned_periods <- character()
  expect_warning(.warn_unvalidated_once(2099, 1), class = "pulso_unvalidated_warning")
  expect_no_warning(.warn_unvalidated_once(2099, 1))
  expect_warning(.warn_unvalidated_once(2099, 2), class = "pulso_unvalidated_warning")
})
