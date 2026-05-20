# Unit tests for .parse_module_csv dispatch + helpers.
# These don't touch the network — they build small zip fixtures in tempdir.

test_that(".is_nested_zip_wrapper detects DANE 2024-03/04 layout", {
  expect_true(.is_nested_zip_wrapper(c("CSV.zip", "DTA.zip", "SAV.zip")))
  expect_true(.is_nested_zip_wrapper("CSV.zip"))
  expect_false(.is_nested_zip_wrapper(c("CSV/Ocupados.CSV", "CSV/No ocupados.CSV")))
  expect_false(.is_nested_zip_wrapper(character(0)))
})

test_that(".resolve_zip_path resolves exact + case-insensitive matches", {
  contents <- c("CSV/Ocupados.CSV", "CSV/No ocupados.CSV")
  expect_equal(.resolve_zip_path(contents, "CSV/Ocupados.CSV"), "CSV/Ocupados.CSV")
  expect_equal(.resolve_zip_path(contents, "CSV/ocupados.csv"), "CSV/Ocupados.CSV")
  expect_null(.resolve_zip_path(contents, "missing.csv"))
})

test_that(".read_single_csv_from_zip extracts the requested file", {
  # Build a tiny zip with two CSVs whose names differ only by a leading 'No '.
  tmp_dir <- tempfile()
  fs::dir_create(tmp_dir)
  on.exit(fs::dir_delete(tmp_dir), add = TRUE)

  fs::dir_create(fs::path(tmp_dir, "CSV"))
  writeLines(c("col1;col2", "A;1", "B;2"),
             fs::path(tmp_dir, "CSV", "Ocupados.CSV"))
  writeLines(c("colX;colY", "Z;9"),
             fs::path(tmp_dir, "CSV", "No ocupados.CSV"))

  zip_path <- tempfile(fileext = ".zip")
  on.exit(unlink(zip_path), add = TRUE)
  old_wd <- setwd(tmp_dir); on.exit(setwd(old_wd), add = TRUE)
  utils::zip(zip_path, c("CSV/Ocupados.CSV", "CSV/No ocupados.CSV"), flags = "-r9X")
  setwd(old_wd)

  df_ocup <- .read_single_csv_from_zip(zip_path, "CSV/Ocupados.CSV")
  expect_equal(names(df_ocup), c("col1", "col2"))
  expect_equal(nrow(df_ocup), 2)

  df_no <- .read_single_csv_from_zip(zip_path, "CSV/No ocupados.CSV")
  expect_equal(names(df_no), c("colX", "colY"))
  expect_equal(nrow(df_no), 1)
})

test_that(".parse_module_csv Shape B reads the explicit file", {
  tmp_dir <- tempfile()
  fs::dir_create(tmp_dir)
  on.exit(fs::dir_delete(tmp_dir), add = TRUE)

  fs::dir_create(fs::path(tmp_dir, "CSV"))
  writeLines(c("a;b", "1;2"), fs::path(tmp_dir, "CSV", "Ocupados.CSV"))
  writeLines(c("x;y;z", "3;4;5"),
             fs::path(tmp_dir, "CSV", "No ocupados.CSV"))

  zip_path <- tempfile(fileext = ".zip")
  on.exit(unlink(zip_path), add = TRUE)
  old_wd <- setwd(tmp_dir); on.exit(setwd(old_wd), add = TRUE)
  utils::zip(zip_path, c("CSV/Ocupados.CSV", "CSV/No ocupados.CSV"),
             flags = "-r9X")
  setwd(old_wd)

  # The wrong-file bug: 'ocupados' substring also matched 'No ocupados'.
  # After the fix, the module spec routes directly to Ocupados.CSV.
  spec_ocup <- list(file = "CSV/Ocupados.CSV")
  df_ocup <- .parse_module_csv(zip_path, spec_ocup, "ocupados", 2024L, 6L)
  expect_equal(ncol(df_ocup), 2)

  spec_des <- list(file = "CSV/No ocupados.CSV")
  df_des <- .parse_module_csv(zip_path, spec_des, "desocupados", 2024L, 6L)
  expect_equal(ncol(df_des), 3)
})

test_that(".parse_module_csv Shape A concatenates cabecera + resto with CLASE", {
  tmp_dir <- tempfile()
  fs::dir_create(tmp_dir)
  on.exit(fs::dir_delete(tmp_dir), add = TRUE)

  writeLines(c("DIRECTORIO;EDAD", "1;25", "2;30"),
             fs::path(tmp_dir, "Cabecera - Ocupados.csv"))
  writeLines(c("DIRECTORIO;EDAD", "3;40"),
             fs::path(tmp_dir, "Resto - Ocupados.csv"))

  zip_path <- tempfile(fileext = ".zip")
  on.exit(unlink(zip_path), add = TRUE)
  old_wd <- setwd(tmp_dir); on.exit(setwd(old_wd), add = TRUE)
  utils::zip(zip_path,
             c("Cabecera - Ocupados.csv", "Resto - Ocupados.csv"),
             flags = "-r9X")
  setwd(old_wd)

  spec <- list(
    cabecera = "Cabecera - Ocupados.csv",
    resto    = "Resto - Ocupados.csv"
  )
  df <- .parse_module_csv(zip_path, spec, "ocupados", 2020L, 6L)

  expect_equal(nrow(df), 3)
  expect_true("CLASE" %in% names(df))
  expect_equal(sort(unique(df$CLASE)), c(1L, 2L))
  expect_equal(sum(df$CLASE == 1L), 2L)
  expect_equal(sum(df$CLASE == 2L), 1L)
})

test_that(".parse_module_csv detects nested-zip layout (2024-03/04) and defers", {
  tmp_dir <- tempfile()
  fs::dir_create(tmp_dir)
  on.exit(fs::dir_delete(tmp_dir), add = TRUE)

  writeLines("placeholder", fs::path(tmp_dir, "CSV.zip"))
  writeLines("placeholder", fs::path(tmp_dir, "DTA.zip"))

  zip_path <- tempfile(fileext = ".zip")
  on.exit(unlink(zip_path), add = TRUE)
  old_wd <- setwd(tmp_dir); on.exit(setwd(old_wd), add = TRUE)
  utils::zip(zip_path, c("CSV.zip", "DTA.zip"), flags = "-r9X")
  setwd(old_wd)

  spec <- list(file = "CSV/Ocupados.CSV")
  expect_error(
    .parse_module_csv(zip_path, spec, "ocupados", 2024L, 3L),
    class = "pulso_parse_error",
    regexp = "nested-zip"
  )
})

test_that(".parse_module_csv raises on missing inner file", {
  tmp_dir <- tempfile()
  fs::dir_create(tmp_dir)
  on.exit(fs::dir_delete(tmp_dir), add = TRUE)

  writeLines(c("a;b", "1;2"), fs::path(tmp_dir, "other.csv"))

  zip_path <- tempfile(fileext = ".zip")
  on.exit(unlink(zip_path), add = TRUE)
  old_wd <- setwd(tmp_dir); on.exit(setwd(old_wd), add = TRUE)
  utils::zip(zip_path, "other.csv", flags = "-r9X")
  setwd(old_wd)

  spec <- list(file = "CSV/Ocupados.CSV")
  expect_error(
    .parse_module_csv(zip_path, spec, "ocupados", 2024L, 6L),
    class = "pulso_parse_error"
  )
})

test_that(".parse_module_csv raises on unknown shape", {
  zip_path <- tempfile(fileext = ".zip")
  on.exit(unlink(zip_path), add = TRUE)

  # Build any non-nested zip just so .is_nested_zip_wrapper returns FALSE.
  tmp_dir <- tempfile()
  fs::dir_create(tmp_dir)
  on.exit(fs::dir_delete(tmp_dir), add = TRUE)
  writeLines("x", fs::path(tmp_dir, "dummy.txt"))
  old_wd <- setwd(tmp_dir); on.exit(setwd(old_wd), add = TRUE)
  utils::zip(zip_path, "dummy.txt", flags = "-r9X")
  setwd(old_wd)

  spec_unknown <- list(something_else = "x.csv")
  expect_error(
    .parse_module_csv(zip_path, spec_unknown, "modX", 2024L, 6L),
    class = "pulso_parse_error",
    regexp = "unknown shape"
  )
})
