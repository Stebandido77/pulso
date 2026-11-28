# pulso_load_range() (W4, #87). pulso_load is mocked: no network.

test_that(".period_range crosses years and validates input", {
  pr <- .period_range("2021-11", "2022-02")
  expect_equal(pr$year, c(2021L, 2021L, 2022L, 2022L))
  expect_equal(pr$month, c(11L, 12L, 1L, 2L))
  expect_error(.period_range("2026-10", "2026-09"), class = "pulso_validation_error")
  expect_error(.period_range("2026-13", "2026-12"), class = "pulso_validation_error")
})

test_that(".sampling_frame puts 2020 and 2022+ on the 2018 frame", {
  expect_equal(.sampling_frame(2019, 12), "2005")
  expect_equal(.sampling_frame(2020, 6), "2018")
  expect_equal(.sampling_frame(2021, 12), "2005")
  expect_equal(.sampling_frame(2022, 1), "2018")
})

fake_load <- function(year, month, module, ...) {
  tibble::tibble(directorio = 1:2, fex_c18 = c(30, 30))
}

test_that("pulso_load_range stacks months and averages the weights", {
  local_mocked_bindings(pulso_load = fake_load)
  df <- pulso_load_range("2026-07", "2026-09", "ocupados", average_weights = TRUE)
  expect_equal(df$periodo, rep(c("2026-07", "2026-08", "2026-09"), each = 2))
  expect_equal(names(df)[1:3], c("periodo", "year", "month"))
  expect_equal(df$peso_expansion_promedio, rep(10, 6))
  expect_equal(sum(df$peso_expansion_promedio), 60)
})

test_that("pulso_load_range warns when the range crosses census frames", {
  local_mocked_bindings(pulso_load = fake_load)
  expect_warning(
    df <- pulso_load_range("2021-12", "2022-01", "ocupados"),
    "2005 and 2018 census"
  )
  expect_equal(df$periodo, rep(c("2021-12", "2022-01"), each = 2))
})
