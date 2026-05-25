library(pulso)

test_that("pulso_tpm returns tibble with correct structure (fixture)", {
  df <- pulso_tpm(use_fixture = TRUE)

  expect_s3_class(df, "tbl_df")
  expect_named(df, c("fecha", "valor", "serie"))
  expect_s3_class(df$fecha, "Date")
  expect_type(df$valor, "double")
  expect_equal(unique(df$serie), "tpm")
  expect_gt(nrow(df), 5000L)
})

test_that("pulso_tpm filters by start date", {
  df <- pulso_tpm(start = "2020-01-01", use_fixture = TRUE)
  expect_true(all(df$fecha >= as.Date("2020-01-01")))
  expect_gt(nrow(df), 0L)
})

test_that("pulso_tpm filters by end date", {
  df <- pulso_tpm(end = "2015-12-31", use_fixture = TRUE)
  expect_true(all(df$fecha <= as.Date("2015-12-31")))
  expect_gt(nrow(df), 0L)
})

test_that("pulso_tpm filters by start and end", {
  df <- pulso_tpm(start = "2022-01-01", end = "2022-12-31", use_fixture = TRUE)
  expect_true(all(df$fecha >= as.Date("2022-01-01")))
  expect_true(all(df$fecha <= as.Date("2022-12-31")))
})

test_that("pulso_tpm validates invalid date string", {
  expect_error(pulso_tpm(start = "not-a-date"))
  expect_error(pulso_tpm(end   = "31-13-2020"))
})

test_that("pulso_tpm rejects start > end", {
  expect_error(pulso_tpm(start = "2024-12-31", end = "2024-01-01"))
})

test_that("pulso_tpm full range has dates from 2010 onward", {
  df <- pulso_tpm(use_fixture = TRUE)
  expect_gte(as.integer(format(min(df$fecha), "%Y")), 2010L)
  expect_gte(as.integer(format(max(df$fecha), "%Y")), 2025L)
})

test_that("pulso_tpm valores are numeric and > 0", {
  df <- pulso_tpm(start = "2023-01-01", end = "2023-12-31", use_fixture = TRUE)
  expect_true(all(df$valor > 0))
  expect_true(all(is.finite(df$valor)))
})

# Live API test (skip if server down or on CRAN)
test_that("pulso_tpm live API returns tibble", {
  skip_on_cran()
  skip_if(!pulso:::.banrep_api_available(), "Banrep API unavailable")
  df <- pulso_tpm(use_fixture = FALSE)
  expect_s3_class(df, "tbl_df")
  expect_named(df, c("fecha", "valor", "serie"))
})
