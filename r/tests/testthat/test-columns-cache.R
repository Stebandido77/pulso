# columns = and the parquet cache of parsed modules (W3, #86).

.make_zip <- function(files) {
  dir <- tempfile()
  fs::dir_create(dir)
  for (name in names(files)) {
    fs::dir_create(fs::path_dir(fs::path(dir, name)))
    writeLines(files[[name]], fs::path(dir, name))
  }
  zip_path <- tempfile(fileext = ".zip")
  old <- setwd(dir)
  on.exit(setwd(old), add = TRUE)
  utils::zip(zip_path, names(files), flags = "-r9X")
  zip_path
}

csv_lines <- c(
  "\ufeffDIRECTORIO;SECUENCIA_P;ORDEN;HOGAR;CLASE;P6040;INGLABO;fex_c_2011",
  "1;1;1;1;1;30;1000;10,5",
  "2;1;1;1;2;40;2000;20,5"
)

test_that(".canon_col folds BOM, case and the FEX_C year suffix", {
  expect_equal(
    .canon_col(c("\ufeffDIRECTORIO", "p6040", "fex_c_2011", "FEX_C18", " Clase ")),
    c("DIRECTORIO", "P6040", "FEX_C", "FEX_C18", "CLASE")
  )
})

test_that(".read_zip_member reads only the selected columns", {
  zip_path <- .make_zip(list("CSV/Ocupados.CSV" = csv_lines))
  df <- .read_zip_member(zip_path, "CSV/Ocupados.CSV",
                         select = .read_select(c("p6040", "FEX_C")))
  expect_equal(names(df), c("DIRECTORIO", "SECUENCIA_P", "ORDEN", "HOGAR", "CLASE",
                            "P6040", "fex_c_2011"))
  expect_equal(df$fex_c_2011, c(10.5, 20.5))
})

test_that(".select_columns keeps merge keys first and warns on missing columns", {
  df <- data.frame(P6040 = 1, DIRECTORIO = 2, ORDEN = 3, SECUENCIA_P = 4, X = 5)
  expect_equal(names(.select_columns(df, c("p6040"))),
               c("DIRECTORIO", "SECUENCIA_P", "ORDEN", "P6040"))
  expect_warning(out <- .select_columns(df, c("P6040", "NOPE")), "NOPE")
  expect_equal(names(out), c("DIRECTORIO", "SECUENCIA_P", "ORDEN", "P6040"))
})

test_that("parquet cache round-trips a parsed module unchanged", {
  skip_if_not_installed("arrow")
  withr::local_options(pulso.cache_dir = tempfile("pulso_cache_"))
  zip_path <- .make_zip(list("CSV/Ocupados.CSV" = csv_lines))
  df <- .parse_module_csv(zip_path, list(file = "CSV/Ocupados.CSV"), "ocupados", 2024L, 6L)
  info <- list(download_url = "https://example.org/x.zip", validated = FALSE)
  path <- .parsed_cache_path(info, "ocupados", 2024L, 6L)
  expect_true(.write_parsed_cache(df, path))
  expect_true(file.exists(path))
  expect_equal(.read_parsed_cache(path), df)
  expect_equal(names(.read_parsed_cache(path, .read_select("P6040"))),
               c("DIRECTORIO", "SECUENCIA_P", "ORDEN", "HOGAR", "CLASE", "P6040"))
  # Validating the period does not change the key; a new URL does.
  expect_equal(.parsed_cache_path(modifyList(info, list(validated = TRUE)), "ocupados", 2024L, 6L),
               path)
  expect_false(identical(
    .parsed_cache_path(modifyList(info, list(download_url = "https://example.org/y.zip")),
                       "ocupados", 2024L, 6L),
    path
  ))
  # An unreadable cache file is dropped, not returned.
  writeLines("not parquet", path)
  expect_null(.read_parsed_cache(path))
  expect_false(file.exists(path))
})

test_that("pulso_clear_cache removes the requested level only", {
  root <- tempfile("pulso_cache_")
  withr::local_options(pulso.cache_dir = root)
  fs::dir_create(fs::path(root, c("raw", "parsed")))
  writeLines("x", fs::path(root, "raw", "a.zip"))
  writeLines("x", fs::path(root, "parsed", "a.parquet"))
  pulso_clear_cache("parsed")
  expect_false(dir.exists(fs::path(root, "parsed")))
  expect_true(file.exists(fs::path(root, "raw", "a.zip")))
  pulso_clear_cache()
  expect_false(dir.exists(fs::path(root, "raw")))
  expect_error(pulso_clear_cache("bogus"))
})

test_that("pulso_load validates columns", {
  expect_error(pulso_load(2024, 6, "ocupados", columns = 1),
               class = "pulso_validation_error")
  expect_error(pulso_load(2024, 6, "ocupados", columns = character()),
               class = "pulso_validation_error")
})
