# pulso_indicadores() (W5, #88).

merged_month <- function(oc_w, ds_w, fft_w, frame_2018 = TRUE) {
  out <- data.frame(
    directorio = 1:4, p6040 = c(30, 30, 30, 11), clase = c(1, 1, 2, 2),
    area = c(11, 5, NA, NA), dpto = c(11, 5, 99, 99),
    oci = c(1, NA, NA, NA), dsi = c(NA, 1, NA, NA),
    fex_c18 = c(oc_w, ds_w, fft_w, 50)
  )
  if (frame_2018) out$fft <- c(NA, NA, 1, NA) else out$ini <- c(NA, NA, 1, NA)
  out
}

test_that(".indicadores_person_table applies the PET rule of each frame", {
  t18 <- .indicadores_person_table(merged_month(90, 10, 100), 2026, 9)
  expect_equal(t18$pet, c(TRUE, TRUE, TRUE, FALSE))
  expect_equal(t18$status, c("1", "2", "3", NA))
  expect_equal(t18$ft, c(TRUE, TRUE, FALSE, FALSE))
  # 2005 frame: an 11-year-old in rural CLASE 2 is in the PET (10+).
  t05 <- .indicadores_person_table(merged_month(90, 10, 100, frame_2018 = FALSE), 2015, 6)
  expect_equal(t05$pet, c(TRUE, TRUE, TRUE, TRUE))
  expect_equal(t05$status, c("1", "2", "3", NA))
})

test_that("pulso_indicadores computes monthly and moving-quarter rates", {
  months <- list(
    "2026-07" = merged_month(80, 20, 100), "2026-08" = merged_month(70, 30, 100),
    "2026-09" = merged_month(90, 10, 100)
  )
  local_mocked_bindings(.indicadores_month = function(year, month, ...) {
    .indicadores_person_table(months[[sprintf("%d-%02d", year, month)]], year, month)
  })
  r <- pulso_indicadores("2026-09")
  expect_equal(c(r$pet, r$ft, r$oc, r$ds), c(200, 100, 90, 10))
  expect_equal(c(r$td, r$to, r$tgp), c(10, 45, 50))
  q <- pulso_indicadores("2026-09", trimestre_movil = TRUE)
  expect_equal(q$meses, 3L)
  expect_equal(q$oc, (80 + 70 + 90) / 3)
  expect_equal(q$td, 100 * 60 / 300)
  cities <- pulso_indicadores("2026-09", dominio = "ciudad")
  expect_equal(cities$grupo, c("05", "11"))
  expect_true(is.na(r$se))
})

test_that("pulso_indicadores skips months it cannot compute", {
  local_mocked_bindings(.indicadores_month = function(year, month, ...) stop("not published"))
  expect_warning(out <- pulso_indicadores("2020-03"), "not published")
  expect_equal(nrow(out), 0)
})

test_that("pulso_indicadores reproduces DANE's national TD for 2026-09", {
  skip_on_cran()
  skip_if_offline()
  r <- tryCatch(pulso_indicadores("2026-09"), error = function(e) NULL)
  skip_if(is.null(r) || nrow(r) == 0, "DANE microdata not reachable")
  # anex-GEIH-sep2026.xlsx, sheet "Total nacional": TD 8.017019 / TO 58.661892 / TGP 63.774723
  expect_equal(r$td, 8.017019, tolerance = 1e-5)
  expect_equal(r$to, 58.661892, tolerance = 1e-5)
  expect_equal(r$tgp, 63.774723, tolerance = 1e-5)
})
