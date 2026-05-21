test_that("pulso_describe returns character", {
  result <- pulso_describe("ocupados")
  expect_type(result, "character")
  expect_equal(length(result), 1L)
})

test_that("pulso_describe includes module name in output", {
  result <- pulso_describe("ocupados")
  expect_match(result, "ocupados", fixed = TRUE)
  expect_match(result, "Available in epochs", fixed = TRUE)
  expect_match(result, "Harmonized variables", fixed = TRUE)
})

test_that("pulso_describe errors on unknown module", {
  expect_error(pulso_describe("modulo_inventado"),
               class = "pulso_module_not_available")
})

test_that("pulso_describe errors on invalid module type", {
  expect_error(pulso_describe(123), class = "pulso_validation_error")
  expect_error(pulso_describe(""),  class = "pulso_validation_error")
})
