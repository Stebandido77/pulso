test_that("pulso_describe_variable returns character for existing variable", {
  result <- pulso_describe_variable("sexo")
  expect_type(result, "character")
  expect_length(result, 1L)
})

test_that("pulso_describe_variable output includes variable name", {
  result <- pulso_describe_variable("sexo")
  expect_true(grepl("sexo", result, ignore.case = TRUE))
})

test_that("pulso_describe_variable exposes comparability_warning in output", {
  # sexo has comparability_warning in variable_map.json (P6020->P3271 epoch change, unverified)
  result <- pulso_describe_variable("sexo")
  expect_true(grepl("WARNING", result, ignore.case = TRUE))
})

test_that("pulso_describe_variable is case-insensitive", {
  r1 <- pulso_describe_variable("sexo")
  r2 <- pulso_describe_variable("SEXO")
  expect_identical(r1, r2)
})

test_that("pulso_describe_variable errors on unknown variable", {
  expect_error(
    pulso_describe_variable("variable_que_no_existe_xyzabc"),
    class = "pulso_validation_error"
  )
})
