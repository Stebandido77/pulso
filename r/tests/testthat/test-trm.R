# pulso_trm() (W7, #90).

test_that(".trm_expand_daily covers each validity window", {
  windows <- data.frame(
    vigenciadesde = c("2026-11-26T00:00:00.000", "2026-11-28T00:00:00.000"),
    vigenciahasta = c("2026-11-27T00:00:00.000", "2026-11-30T00:00:00.000"),
    valor = c("3630.89", "3498.46")
  )
  df <- .trm_expand_daily(windows)
  expect_equal(format(df$fecha), c("2026-11-26", "2026-11-27", "2026-11-28",
                                   "2026-11-29", "2026-11-30"))
  expect_equal(df$valor, c(3630.89, 3630.89, 3498.46, 3498.46, 3498.46))
  expect_true(all(df$serie == "trm"))
})

test_that("pulso_trm(use_fixture = TRUE) reads the bundled snapshot", {
  expect_message(
    df <- pulso_trm("2007-01-01", "2007-01-03", use_fixture = TRUE),
    "bundled TRM snapshot"
  )
  expect_s3_class(df, "tbl_df")
  expect_equal(df$valor, c(2238.79, 2238.79, 2231.42))
})

test_that("pulso_trm falls back to the snapshot when the live call fails", {
  local_mocked_bindings(.trm_from_api = function(...) stop("network down"))
  expect_warning(df <- pulso_trm("2026-11-29", "2026-11-30"), "network down")
  expect_equal(df$valor, c(3498.46, 3498.46))
  expect_error(pulso_trm("2026-11-29", "2026-11-30", use_fixture = FALSE), "network down")
})

test_that("pulso_trm live call matches the snapshot", {
  skip_on_cran()
  skip_if_offline()
  live <- tryCatch(pulso_trm("2026-11-20", "2026-11-30", use_fixture = FALSE),
                   error = function(e) NULL)
  skip_if(is.null(live), "datos.gov.co not reachable")
  snap <- suppressMessages(pulso_trm("2026-11-20", "2026-11-30", use_fixture = TRUE))
  expect_equal(live, snap)
})
