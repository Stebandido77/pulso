test_that("pulso_list_validated_range returns tibble with correct columns and types", {
  result <- pulso_list_validated_range()
  expect_s3_class(result, "tbl_df")
  expect_true(all(c("year", "month", "epoch", "validated", "validated_at",
                    "num_modules") %in% names(result)))
  if (nrow(result) > 0) {
    expect_type(result$year, "integer")
    expect_type(result$month, "integer")
    expect_type(result$epoch, "character")
    expect_type(result$validated, "logical")
    expect_type(result$validated_at, "character")
    expect_type(result$num_modules, "integer")
  }
})

test_that("pulso_list_validated_range: all rows have validated == TRUE", {
  result <- pulso_list_validated_range()
  if (nrow(result) > 0) {
    expect_true(all(result$validated))
  }
})

test_that("pulso_list_validated_range is sorted by year, month", {
  result <- pulso_list_validated_range()
  if (nrow(result) >= 2) {
    dates <- result$year * 100 + result$month
    expect_equal(dates, sort(dates))
  }
})

test_that("pulso_list_validated_range returns at least one validated entry", {
  result <- pulso_list_validated_range()
  expect_gt(nrow(result), 0)
})
