test_that("pulso_load validates inputs before any download", {
  expect_error(
    pulso_load(year = 2027, month = 6, module = "ocupados"),
    class = "pulso_validation_error"
  )
  expect_error(
    pulso_load(year = 2024, month = 13, module = "ocupados"),
    class = "pulso_validation_error"
  )
  expect_error(
    pulso_load(year = 2024, month = 6, module = ""),
    class = "pulso_validation_error"
  )
  # module is validated first; invalid module with invalid year raises
  # pulso_validation_error from .validate_module, not .validate_year
  expect_error(
    pulso_load(year = 9999, month = 6, module = ""),
    regexp = "module",
    class = "pulso_validation_error"
  )
})

test_that("pulso_load happy path returns tibble", {
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2024, month = 6, module = "ocupados")

  expect_s3_class(df, "tbl_df")
  expect_gt(nrow(df), 100)
  # Post-Mini-5A: ocupados is the real ocupados frame, not the 37-column
  # No-ocupados file that the fuzzy-grep used to return. The original bug
  # was "ocupados returns 37 admin-only columns"; assert against that
  # specifically (P-coded variables present, plenty of them) without
  # naming any one variable — the Curator's variable_map.json carries
  # theoretical mappings that haven't all been empirically verified
  # against the data. See followup on issue #61.
  expect_gt(ncol(df), 50)
  # testthat::expect_gt() doesn't accept info=; use label= or comment only.
  p_coded <- grep("^[Pp][0-9]", names(df), value = TRUE)
  expect_gt(length(p_coded), 0)
})

test_that("pulso_load distinguishes ocupados from desocupados", {
  skip_on_cran()
  skip_if_offline()

  df_ocup <- pulso_load(year = 2024, month = 6, module = "ocupados")
  df_des  <- pulso_load(year = 2024, month = 6, module = "desocupados")

  # Different physical CSVs ⇒ different schemas. The pre-Mini-5A bug
  # silently returned the same DataFrame for both because the substring
  # "ocupados" matched both files and csv_match[1] picked one.
  expect_false(identical(sort(names(df_ocup)), sort(names(df_des))))
})

test_that("pulso_load Shape A (2020-06) concatenates cabecera + resto", {
  skip("Shape A single-CSV-with-CLASE variant deferred to Mini-5B (issue #61)")
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2020, month = 6, module = "ocupados",
                   harmonize = FALSE)

  expect_true("CLASE" %in% names(df))
  expect_setequal(unique(df$CLASE), c(1L, 2L))
})

test_that("pulso_load Shape A (2020-06) keeps CLASE after harmonize", {
  skip("Shape A single-CSV-with-CLASE variant deferred to Mini-5B (issue #61)")
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2020, month = 6, module = "ocupados")
  expect_true("clase" %in% names(df))
})

test_that("pulso_load defers nested-zip layout (2024-03) with parse_error", {
  skip_on_cran()
  skip_if_offline()

  expect_error(
    pulso_load(year = 2024, month = 3, module = "ocupados",
               allow_unvalidated = TRUE),
    class = "pulso_parse_error",
    regexp = "nested-zip"
  )
})

test_that("pulso_load with metadata=TRUE attaches pulso_metadata attr", {
  skip_on_cran()
  skip_if_offline()

  df <- pulso_load(year = 2024, month = 6, module = "ocupados",
                   metadata = TRUE)

  meta <- attr(df, "pulso_metadata")
  expect_type(meta, "list")
  expect_true("column_metadata" %in% names(meta))
  expect_true("source_year" %in% names(meta))
  expect_equal(meta$source_year, 2024)
  expect_equal(meta$source_month, 6)
  expect_equal(meta$source_module, "ocupados")
})

test_that("pulso_load uses cache on second call", {
  skip_on_cran()
  skip_if_offline()

  df1 <- pulso_load(year = 2024, month = 6, module = "ocupados")

  start <- Sys.time()
  df2 <- pulso_load(year = 2024, month = 6, module = "ocupados")
  elapsed <- as.numeric(Sys.time() - start, units = "secs")

  expect_lt(elapsed, 5)
  expect_identical(df1, df2)
})

test_that("pulso_load fails for unavailable year/month", {
  skip_on_cran()
  skip_if_offline()

  expect_error(
    pulso_load(year = 2026, month = 12, module = "ocupados"),
    class = "pulso_data_not_available"
  )
})

test_that("pulso_load fails for unknown module", {
  skip_on_cran()
  skip_if_offline()

  expect_error(
    pulso_load(year = 2024, month = 6, module = "modulo_inexistente"),
    class = "pulso_module_not_available"
  )
})

test_that("pulso_load warns about not-yet-implemented args", {
  skip_on_cran()
  skip_if_offline()

  expect_warning(
    pulso_load(year = 2024, month = 6, module = "ocupados", area = "urbano"),
    regexp = "area"
  )
})

test_that("BUG-003: Module with tilde in filename loads on all platforms", {
  skip_on_cran()
  skip_if_offline()
  df <- pulso_load(2024, 6, "caracteristicas_generales")
  expect_s3_class(df, "data.frame")
  expect_gt(nrow(df), 0)
  expect_gt(ncol(df), 5)
})

test_that("BUG-004: Epoch1 with column variance loads", {
  skip_on_cran()
  skip_if_offline()
  df <- pulso_load(2018, 6, "ocupados", allow_unvalidated = TRUE)
  expect_s3_class(df, "data.frame")
  expect_gt(nrow(df), 1000)
})

test_that("BUG-005: 2022-01 with non-semicolon separator loads", {
  skip_on_cran()
  skip_if_offline()
  df <- pulso_load(2022, 1, "ocupados")
  expect_gt(ncol(df), 1)
})

test_that("BUG-017: 2013-06 filenames with numeric suffix load", {
  skip_on_cran()
  skip_if_offline()
  df <- pulso_load(2013, 6, "ocupados", allow_unvalidated = TRUE)
  expect_s3_class(df, "data.frame")
  expect_gt(nrow(df), 0)
})

test_that("BUG-018: 2020 COVID Shape C variant loads", {
  skip_on_cran()
  skip_if_offline()
  df <- pulso_load(2020, 6, "ocupados", allow_unvalidated = TRUE)
  expect_s3_class(df, "data.frame")
  expect_gt(nrow(df), 1000)
  df2 <- pulso_load(2020, 12, "ocupados", allow_unvalidated = TRUE)
  expect_gt(nrow(df2), 1000)
})

test_that("BUG-006: unvalidated period raises pulso_data_not_validated by default", {
  # 2024-09 is confirmed validated=FALSE in sources.json.
  # Guard fires before any download so no skip_if_offline() needed.
  expect_error(
    pulso_load(year = 2024, month = 9, module = "ocupados"),
    class = "pulso_data_not_validated"
  )
})

test_that("BUG-006: allow_unvalidated=TRUE emits warning and loads data", {
  skip_on_cran()
  skip_if_offline()
  expect_warning(
    df <- pulso_load(year = 2024, month = 9, module = "ocupados",
                     allow_unvalidated = TRUE),
    regexp = "not been validated"
  )
  expect_s3_class(df, "data.frame")
  expect_gt(nrow(df), 0)
})

test_that("BUG-006: validated period loads without warning", {
  skip_on_cran()
  skip_if_offline()
  # 2024-06 is validated=TRUE; no warning should be emitted.
  expect_no_warning(
    pulso_load(year = 2024, month = 6, module = "ocupados")
  )
})
