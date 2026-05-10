test_that(".validate_year accepts valid years", {
  expect_silent(pulso:::.validate_year(2024))
  expect_silent(pulso:::.validate_year(2007))
  expect_silent(pulso:::.validate_year(as.integer(format(Sys.Date(), "%Y"))))
})

test_that(".validate_year rejects future years", {
  current_year <- as.integer(format(Sys.Date(), "%Y"))
  expect_error(
    pulso:::.validate_year(current_year + 1),
    class = "pulso_validation_error"
  )
  expect_error(
    pulso:::.validate_year(current_year + 100),
    class = "pulso_validation_error"
  )
})

test_that(".validate_year rejects pre-2007 years", {
  expect_error(pulso:::.validate_year(2006), class = "pulso_validation_error")
  expect_error(pulso:::.validate_year(1990), class = "pulso_validation_error")
})

test_that(".validate_year rejects non-integer types", {
  expect_error(pulso:::.validate_year("2024"), class = "pulso_validation_error")
  expect_error(pulso:::.validate_year(2024.5), class = "pulso_validation_error")
  expect_error(pulso:::.validate_year(c(2024, 2025)), class = "pulso_validation_error")
  expect_error(pulso:::.validate_year(NA), class = "pulso_validation_error")
})

test_that(".validate_month accepts valid months", {
  expect_silent(pulso:::.validate_month(1))
  expect_silent(pulso:::.validate_month(6))
  expect_silent(pulso:::.validate_month(12))
})

test_that(".validate_month rejects out-of-range", {
  expect_error(pulso:::.validate_month(0), class = "pulso_validation_error")
  expect_error(pulso:::.validate_month(13), class = "pulso_validation_error")
  expect_error(pulso:::.validate_month(-1), class = "pulso_validation_error")
})

test_that(".validate_month rejects non-integer types", {
  expect_error(pulso:::.validate_month("6"), class = "pulso_validation_error")
  expect_error(pulso:::.validate_month(6.5), class = "pulso_validation_error")
})

test_that(".validate_module accepts non-empty strings", {
  expect_silent(pulso:::.validate_module("ocupados"))
  expect_silent(pulso:::.validate_module("vivienda"))
})

test_that(".validate_module rejects empty/non-string", {
  expect_error(pulso:::.validate_module(""), class = "pulso_validation_error")
  expect_error(pulso:::.validate_module(NULL), class = "pulso_validation_error")
  expect_error(pulso:::.validate_module(c("a", "b")), class = "pulso_validation_error")
  expect_error(pulso:::.validate_module(123), class = "pulso_validation_error")
})
