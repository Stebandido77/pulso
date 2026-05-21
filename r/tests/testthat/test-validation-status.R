test_that("pulso_validation_status returns tibble with correct columns", {
  result <- pulso_validation_status(2024, 6)
  expect_s3_class(result, "tbl_df")
  expect_equal(nrow(result), 1L)
  expect_true(all(c("year", "month", "epoch", "validated", "validated_by",
                    "validated_at", "source_url", "file_size_mb",
                    "modules_available", "checksum_sha256") %in% names(result)))
})

test_that("pulso_validation_status column types are correct", {
  result <- pulso_validation_status(2024, 6)
  expect_type(result$year, "integer")
  expect_type(result$month, "integer")
  expect_type(result$epoch, "character")
  expect_type(result$validated, "logical")
  expect_type(result$file_size_mb, "double")
  expect_type(result$modules_available, "character")
  expect_type(result$validated_by, "character")
  expect_type(result$validated_at, "character")
  expect_type(result$source_url, "character")
  expect_type(result$checksum_sha256, "character")
})

test_that("pulso_validation_status errors on invalid year", {
  expect_error(pulso_validation_status(1900, 6), class = "pulso_validation_error")
  expect_error(pulso_validation_status(9999, 6), class = "pulso_validation_error")
})

test_that("pulso_validation_status errors on invalid month", {
  expect_error(pulso_validation_status(2024, 0),  class = "pulso_validation_error")
  expect_error(pulso_validation_status(2024, 13), class = "pulso_validation_error")
})

test_that("pulso_validation_status errors on unknown period", {
  # 1985-06 is before pulso coverage starts (2007), so .validate_year fires
  # first. Use a valid year with a period not in sources.json instead.
  # 2024-02 IS in sources.json, so use a period that is genuinely absent.
  # The year 2007 is covered; confirm a missing month within it if needed.
  # Safest: let .validate_year pass (year >= 2007, <= current) but pick a
  # year/month combo absent from the registry. 2026-12 is after last entry.
  expect_error(pulso_validation_status(2026, 12), class = "pulso_data_not_available")
})

test_that("pulso_validation_status values are sensible for known period", {
  result <- pulso_validation_status(2024, 6)
  expect_equal(result$year, 2024L)
  expect_equal(result$month, 6L)
  expect_false(is.na(result$epoch))
  expect_match(result$modules_available, "ocupados", fixed = TRUE)
  expect_true(is.na(result$file_size_mb) || result$file_size_mb > 0)
})

test_that("pulso_validation_status NA fields are NA for unvalidated period", {
  result <- pulso_validation_status(2007, 3)
  expect_false(result$validated)
  expect_true(is.na(result$validated_by))
  expect_true(is.na(result$validated_at))
  expect_true(is.na(result$checksum_sha256))
  expect_false(is.na(result$source_url))
})
