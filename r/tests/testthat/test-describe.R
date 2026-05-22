test_that("pulso_describe_column requires single string column", {
  df <- tibble::tibble(a = 1:3, b = 4:6)

  expect_error(
    pulso_describe_column(df, c("a", "b")),
    class = "pulso_validation_error"
  )
  expect_error(
    pulso_describe_column(df, 123),
    class = "pulso_validation_error"
  )
})

test_that("pulso_describe_column errors for column not in df", {
  df <- tibble::tibble(a = 1:3, b = 4:6)

  expect_error(
    pulso_describe_column(df, "nonexistent"),
    class = "pulso_validation_error"
  )
})

test_that("pulso_describe_column returns message for df without metadata", {
  df <- tibble::tibble(a = 1:3, b = 4:6)

  result <- pulso_describe_column(df, "a")
  expect_type(result, "character")
  expect_match(result, "no metadata")
})

test_that("pulso_describe_column is case-insensitive", {
  df <- tibble::tibble(p6020 = 1:3, otro = 4:6)

  # exact lowercase match
  result_lower <- pulso_describe_column(df, "p6020")
  expect_type(result_lower, "character")
  expect_match(result_lower, "no metadata")

  # uppercase version should also work
  result_upper <- pulso_describe_column(df, "P6020")
  expect_type(result_upper, "character")
  expect_match(result_upper, "no metadata")
})

test_that("pulso_describe_column is case-insensitive when df column is uppercase", {
  df <- tibble::tibble(P6020 = 1:3, otro = 4:6)

  # real-world case: pulso_load without harmonize returns uppercase DANE codes
  result <- pulso_describe_column(df, "p6020")
  expect_type(result, "character")
  expect_match(result, "no metadata")
})

test_that("pulso_describe_column returns formatted text with metadata", {
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2024, month = 6, module = "ocupados",
                   metadata = TRUE)

  some_col <- names(df)[1]
  result <- pulso_describe_column(df, some_col)

  expect_type(result, "character")
  expect_gt(nchar(result), 10)
})
