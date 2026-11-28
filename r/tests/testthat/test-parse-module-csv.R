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

test_that(".parse_module_csv rejects a nested wrapper whose CSV.zip is corrupt", {
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
    regexp = "CSV.zip"
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

test_that(".is_nested_zip_wrapper accepts numbered and variant inner names (#75)", {
  # 2022-10, 2023-04, 2023-08 and 2023-09 layouts.
  expect_true(.is_nested_zip_wrapper(c(
    "GEIH_Octubre_Marco_2018/CSV 4.zip", "GEIH_Octubre_Marco_2018/DTA 4.zip",
    "GEIH_Octubre_Marco_2018/SAV 4.zip"
  )))
  expect_true(.is_nested_zip_wrapper(c("Abril/CSV.zip", "Abril/DTA 9.zip", "Abril/SAV 9.zip")))
  expect_true(.is_nested_zip_wrapper(c("Agosto/CSV.zip", "Agosto/DAT.zip", "Agosto/SAV.zip")))
  expect_true(.is_nested_zip_wrapper(c("Septiembre/CSV 13.zip", "Septiembre/SAV 12.zip")))
  expect_false(.is_nested_zip_wrapper(c("CSV.zip", "CSVX.zip")))
  expect_false(.is_nested_zip_wrapper(c("CSV.zip", "CSV 4.csv")))
})

test_that(".parse_module_csv unwraps a numbered inner zip with a CVS/ folder (#75)", {
  tmp_dir <- tempfile()
  fs::dir_create(fs::path(tmp_dir, "inner", "CVS"))
  fs::dir_create(fs::path(tmp_dir, "outer", "Abril"))
  on.exit(fs::dir_delete(tmp_dir), add = TRUE)

  writeLines(c("DIRECTORIO;CLASE;FEX_C18", "1;1;10.5", "2;2;20.5"),
             fs::path(tmp_dir, "inner", "CVS", "Ocupados.CSV"))
  old_wd <- setwd(fs::path(tmp_dir, "inner"))
  utils::zip(fs::path(tmp_dir, "outer", "Abril", "CSV 13.zip"), "CVS/Ocupados.CSV",
             flags = "-r9X")
  writeLines("stub", fs::path(tmp_dir, "outer", "Abril", "DTA 9.zip"))
  setwd(fs::path(tmp_dir, "outer"))
  zip_path <- fs::path(tmp_dir, "wrapper.zip")
  utils::zip(zip_path, c("Abril/CSV 13.zip", "Abril/DTA 9.zip"), flags = "-r9X")
  setwd(old_wd)

  df <- .parse_module_csv(zip_path, list(file = "CSV/Ocupados.CSV"), "ocupados", 2023L, 9L)
  expect_equal(nrow(df), 2)
  expect_equal(df$FEX_C18, c(10.5, 20.5))
})

test_that(".find_shape_c_file tolerates the 2020 filename typos (#75)", {
  contents <- c(
    "5.Mayo/CSV/Ocupados.CSV", "5.Mayo/CSV/Descupados.CSV",
    "7.Julio/CSV/Ianctivos.CSV", "10.Octubre/CSV/Inativos.CSV",
    "9.Septiembre/CSV/Desoucpados.CSV", "11.Noviembre/CSV/Fuerzo de trabajo.CSV"
  )
  expect_equal(.find_shape_c_file(contents, "ocupados"), "5.Mayo/CSV/Ocupados.CSV")
  expect_equal(.find_shape_c_file(contents, "desocupados"), "5.Mayo/CSV/Descupados.CSV")
  expect_equal(.find_shape_c_file(contents[-2], "desocupados"),
               "9.Septiembre/CSV/Desoucpados.CSV")
  expect_equal(.find_shape_c_file(contents, "inactivos"), "7.Julio/CSV/Ianctivos.CSV")
  expect_equal(.find_shape_c_file(contents[-3], "inactivos"), "10.Octubre/CSV/Inativos.CSV")
  expect_equal(.find_shape_c_file(contents, "fuerza_de_trabajo"),
               "11.Noviembre/CSV/Fuerzo de trabajo.CSV")
  # 2020-03/04: DANE did not publish Desocupados or Inactivos.
  expect_null(.find_shape_c_file("3.Marzo/CSV/Ocupados.CSV", "inactivos"))
})
