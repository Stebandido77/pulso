test_that("pulso_load validates inputs before any download", {
  expect_error(
    pulso_load(year = 2027, month = 6, module = "ocupados"),
    class = "pulso_validation_error"
  )
  expect_error(
    pulso_load(year = 2024, month = 13, module = "ocupados"),
    class = "pulso_validation_error"
  )
  expect_error(
    pulso_load(year = 2024, month = 6, module = ""),
    class = "pulso_validation_error"
  )
})

test_that("pulso_load happy path returns tibble", {
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2024, month = 6, module = "ocupados")

  expect_s3_class(df, "tbl_df")
  expect_gt(nrow(df), 100)
  expect_gt(ncol(df), 5)
})

test_that("pulso_load with metadata=TRUE attaches pulso_metadata attr", {
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2024, month = 6, module = "ocupados",
                   metadata = TRUE)

  meta <- attr(df, "pulso_metadata")
  expect_type(meta, "list")
  expect_true("column_metadata" %in% names(meta))
  expect_true("source_year" %in% names(meta))
  expect_equal(meta$source_year, 2024)
  expect_equal(meta$source_month, 6)
  expect_equal(meta$source_module, "ocupados")
})

test_that("pulso_load uses cache on second call", {
  skip_on_cran()
  skip_if_offline()

  df1 <- pulso_load(year = 2024, month = 6, module = "ocupados")

  start <- Sys.time()
  df2 <- pulso_load(year = 2024, month = 6, module = "ocupados")
  elapsed <- as.numeric(Sys.time() - start, units = "secs")

  expect_lt(elapsed, 5)
  expect_identical(df1, df2)
})

test_that("pulso_load fails for unavailable year/month", {
  skip_on_cran()
  skip_if_offline()

  expect_error(
    pulso_load(year = 2026, month = 12, module = "ocupados"),
    class = "pulso_data_not_available"
  )
})

test_that("pulso_load fails for unknown module", {
  skip_on_cran()
  skip_if_offline()

  expect_error(
    pulso_load(year = 2024, month = 6, module = "modulo_inexistente"),
    class = "pulso_module_not_available"
  )
})

test_that("pulso_load warns about not-yet-implemented args", {
  skip_on_cran()
  skip_if_offline()

  expect_warning(
    pulso_load(year = 2024, month = 6, module = "ocupados", area = "urbano"),
    regexp = "area"
  )
})
