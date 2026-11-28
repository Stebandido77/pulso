test_that("pulso_list_variables returns tibble with correct columns", {
  result <- pulso_list_variables()
  expect_s3_class(result, "tbl_df")
  expect_named(result, c("canonical_name", "module", "description_es",
                         "comparability", "has_warning", "num_epochs"))
})

test_that("pulso_list_variables NULL returns all variables", {
  result <- pulso_list_variables()
  expect_gte(nrow(result), 1L)
  # One row per variable of variable_map.json (32 since pet and
  # fuerza_trabajo, #79); read the count instead of hard-coding it.
  expect_equal(nrow(result), length(.load_variable_map()))
  expect_true(all(c("pet", "fuerza_trabajo") %in% result$canonical_name))
})

test_that("pulso_list_variables filters by valid module", {
  result <- pulso_list_variables(module = "ocupados")
  expect_s3_class(result, "tbl_df")
  expect_true(all(result$module == "ocupados"))
  expect_gte(nrow(result), 1L)
})

test_that("pulso_list_variables errors on invalid module", {
  expect_error(
    pulso_list_variables(module = "modulo_inventado_xyz"),
    class = "pulso_module_not_available"
  )
})

test_that("pulso_list_variables has_warning column is logical", {
  result <- pulso_list_variables()
  expect_type(result$has_warning, "logical")
})

test_that("pulso_list_variables has_warning TRUE for variable with known warning", {
  result <- pulso_list_variables()
  # sexo has comparability_warning in variable_map.json (P6020->P3271 epoch change)
  sexo_row <- result[result$canonical_name == "sexo", ]
  expect_true(sexo_row$has_warning)
})

test_that("pulso_list_variables is sorted by canonical_name", {
  result <- pulso_list_variables()
  expect_equal(result$canonical_name, sort(result$canonical_name))
})
