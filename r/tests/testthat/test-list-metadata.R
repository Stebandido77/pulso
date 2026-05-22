test_that("pulso_list_columns_metadata returns empty tibble when no metadata", {
  df <- tibble::tibble(a = 1:3)

  expect_warning(
    result <- pulso_list_columns_metadata(df),
    regexp = "metadata"
  )

  expect_s3_class(result, "tbl_df")
  expect_equal(nrow(result), 0)
})

test_that("pulso_list_columns_metadata returns tibble with required columns", {
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2024, month = 6, module = "ocupados",
                   metadata = TRUE)

  result <- pulso_list_columns_metadata(df)

  expect_s3_class(result, "tbl_df")
  expect_equal(nrow(result), ncol(df))

  expected_cols <- c("column", "label", "type", "module", "source",
                     "has_categories")
  expect_true(all(expected_cols %in% names(result)))
})

test_that("pulso_list_columns_metadata source values are valid", {
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2024, month = 6, module = "ocupados",
                   metadata = TRUE)

  result <- pulso_list_columns_metadata(df)

  valid_sources <- c("merged", "curator", "codebook",
                     "codebook (skeletal)", "missing")
  expect_true(all(result$source %in% valid_sources))
})
