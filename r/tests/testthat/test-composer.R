test_that(".compose_column_metadata returns list with required fields", {
  skip_on_cran()
  skip_if_offline()

  result <- pulso:::.compose_column_metadata("P6020", year = 2024,
                                              module = "ocupados")

  expect_type(result, "list")
  expect_true("source" %in% names(result))
  expect_true("column" %in% names(result))
  expect_true("epoch" %in% names(result))
  expect_true(result$source %in% c("merged", "curator", "codebook",
                                    "codebook (skeletal)", "missing"))
})

test_that(".compose_column_metadata handles missing column gracefully", {
  skip_on_cran()
  skip_if_offline()

  result <- pulso:::.compose_column_metadata("VARIABLE_INEXISTENTE_XYZ",
                                              year = 2024,
                                              module = "ocupados")

  expect_equal(result$source, "missing")
  expect_equal(result$column, "VARIABLE_INEXISTENTE_XYZ")
})

test_that(".find_canonical_name returns NULL for unknown variable", {
  skip_on_cran()

  result <- pulso:::.find_canonical_name("XYZ_NOT_REAL", "geih_2021_present")
  expect_null(result)
})

test_that(".get_epoch_for_year returns valid epoch names", {
  expect_type(pulso:::.get_epoch_for_year(2024), "character")
  expect_type(pulso:::.get_epoch_for_year(2010), "character")
  expect_type(pulso:::.get_epoch_for_year(2007), "character")
})

test_that(".get_epoch_for_year fails for invalid year inputs", {
  expect_error(
    pulso:::.get_epoch_for_year("not a year"),
    class = "pulso_validation_error"
  )
  expect_error(
    pulso:::.get_epoch_for_year(c(2020, 2024)),
    class = "pulso_validation_error"
  )
})

test_that(".get_epoch_for_year returns correct epoch at 2021/2022 boundary", {
  expect_equal(pulso:::.get_epoch_for_year(2021), "geih_2006_2020")
  expect_equal(pulso:::.get_epoch_for_year(2022), "geih_2021_present")
})

test_that(".get_epoch_for_year raises error for out-of-range years", {
  expect_error(
    pulso:::.get_epoch_for_year(2005),
    class = "pulso_validation_error"
  )
  expect_error(
    pulso:::.get_epoch_for_year(2200),
    class = "pulso_validation_error"
  )
})

test_that(".get_epoch_for_year accepts 2006 as lower boundary", {
  expect_equal(pulso:::.get_epoch_for_year(2006), "geih_2006_2020")
})

test_that(".find_canonical_name resolves scalar source_variable", {
  skip_on_cran()
  # sexo maps to scalar "P3271" in geih_2021_present (variable_map.json verified)
  result <- pulso:::.find_canonical_name("P3271", "geih_2021_present")
  expect_equal(result, "sexo")
})

test_that(".find_canonical_name resolves list-valued source_variable", {
  skip_on_cran()

  # "ingreso_total" has source_variable = ["INGLABO", "P7500S1A1", ...] in geih_2021_present
  result <- pulso:::.find_canonical_name("INGLABO", "geih_2021_present")
  expect_equal(result, "ingreso_total")
})

test_that("%||% operator returns first non-null/non-empty value", {
  expect_equal(pulso:::`%||%`("a", "b"), "a")
  expect_equal(pulso:::`%||%`(NULL, "b"), "b")
  expect_equal(pulso:::`%||%`("", "b"), "b")
  expect_null(pulso:::`%||%`(NULL, NULL))
})
