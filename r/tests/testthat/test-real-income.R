# IPC, minimum wage and deflation (W6, #89).

test_that("pulso_ipc(use_fixture = TRUE) is monthly with base Dec 2018 = 100", {
  t <- pulso_ipc(use_fixture = TRUE)
  expect_equal(nrow(t), 286)
  expect_equal(t$periodo[c(1, nrow(t))], c("2003-01", "2026-10"))
  expect_equal(t$indice[t$periodo == "2018-12"], 100)
})

test_that("pulso_ipc falls back to the snapshot when DANE fails", {
  local_mocked_bindings(.ipc_from_dane = function() stop("down"))
  expect_warning(t <- pulso_ipc(), "down")
  expect_equal(t$periodo[nrow(t)], "2026-10")
  expect_error(pulso_ipc(use_fixture = FALSE), "down")
})

test_that("pulso_salario_minimo covers 2007-2026 with decrees", {
  t <- pulso_salario_minimo()
  expect_equal(t$anio, 2007:2026)
  expect_equal(t$smmlv[t$anio == 2026], 1750905)
  expect_equal(t$smmlv[t$anio == 2011], 535600)
  expect_true(all(startsWith(t$fuente, "https://")))
})

test_that("pulso_deflactar converts to pesos of the reference month", {
  ipc <- pulso_ipc(use_fixture = TRUE)
  df <- data.frame(periodo = c("2018-12", "2026-09"), x = c(1000, 1000))
  out <- pulso_deflactar(df, "x", "2026-09", ipc_table = ipc)
  expect_equal(out$x_real, c(1610, 1000))
  expect_error(pulso_deflactar(df, "x", "2030-01", ipc_table = ipc),
               class = "pulso_validation_error")
})

test_that("pulso_load_range(deflate_to =) adds real income columns", {
  local_mocked_bindings(pulso_load = function(...) tibble::tibble(inglabo = 1000),
                        pulso_ipc = function(...) .ipc_from_fixture())
  df <- pulso_load_range("2018-12", "2018-12", "ocupados", deflate_to = "2026-09")
  expect_equal(df$inglabo_real, 1610)
})

test_that("pulso_ipc live download matches the snapshot", {
  skip_on_cran()
  skip_if_offline()
  live <- tryCatch(pulso_ipc(use_fixture = FALSE), error = function(e) NULL)
  skip_if(is.null(live), "DANE not reachable")
  snap <- pulso_ipc(use_fixture = TRUE)
  common <- live[live$periodo %in% snap$periodo, ]
  expect_equal(common$indice, snap$indice)
})
