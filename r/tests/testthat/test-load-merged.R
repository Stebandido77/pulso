test_that("pulso_load_merged errors on empty modules", {
  expect_error(pulso_load_merged(2024, 6, character(0)),
               class = "pulso_validation_error")
  expect_error(pulso_load_merged(2024, 6, NULL),
               class = "pulso_validation_error")
  expect_error(pulso_load_merged(2024, 6, c(2L, 3L)),
               class = "pulso_validation_error")
})

test_that("pulso_load_merged errors on single module", {
  expect_error(pulso_load_merged(2024, 6, "ocupados"),
               class = "pulso_validation_error")
  expect_error(pulso_load_merged(2024, 6, "ocupados"),
               regexp = "pulso_load")
})

test_that("pulso_load_merged errors on unknown module", {
  expect_error(pulso_load_merged(2024, 6, c("ocupados", "modulo_inventado")),
               class = "pulso_validation_error",
               regexp = "Unknown module")
})

test_that("pulso_load_merged errors on invalid year or month", {
  expect_error(pulso_load_merged(1900, 6, c("ocupados", "caracteristicas_generales")),
               class = "pulso_validation_error")
  expect_error(pulso_load_merged(2024, 13, c("ocupados", "caracteristicas_generales")),
               class = "pulso_validation_error")
})

test_that("pulso_load_merged errors on mixed levels (Q4=A)", {
  expect_error(
    pulso_load_merged(2024, 6, c("ocupados", "vivienda_hogares")),
    class = "pulso_validation_error",
    regexp = "v0.2.0"
  )
})

test_that("pulso_load_merged returns merged tibble for 2 persona modules", {
  skip_on_ci()
  df <- pulso_load_merged(2024, 6, c("ocupados", "caracteristicas_generales"))
  expect_s3_class(df, "tbl_df")
  # both modules contribute columns: ocupados has p6430, caracteristicas_generales has p6020
  expect_true("p6430" %in% names(df) || any(grepl("^p64", names(df))))
  expect_true("p6020" %in% names(df) || "p3271" %in% names(df))
  # merge keys present
  expect_true(all(c("directorio", "secuencia_p", "orden") %in% names(df)))
})

test_that("pulso_load_merged metadata=TRUE attaches attr", {
  skip_on_ci()
  df <- pulso_load_merged(2024, 6, c("ocupados", "caracteristicas_generales"),
                          metadata = TRUE)
  expect_false(is.null(attr(df, "pulso_metadata")))
})

test_that("pulso_load_merged errors on modules with NA values", {
  expect_error(
    pulso_load_merged(2024, 6, c("ocupados", NA, "caracteristicas_generales")),
    class = "pulso_validation_error"
  )
})
