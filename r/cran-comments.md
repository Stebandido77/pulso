## Update

This is an update from pulso 0.2.1 (accepted on CRAN on 2026-11-28) to 0.3.0.
It is to be submitted no earlier than 2026-12-28, one month after 0.2.1.

* New functions: `pulso_load_range()` (consecutive months with moving-quarter
  weights), `pulso_indicadores()` (unemployment, employment and participation
  rates by domain), `pulso_trm()` (exchange rate from the Superintendencia
  Financiera), `pulso_ipc()`, `pulso_salario_minimo()` and
  `pulso_deflactar()` (real income), and `pulso_clear_cache()`.
* `pulso_load()` gains `columns =` (reads only those columns) and, when the
  suggested package 'arrow' is installed, caches parsed modules as parquet in
  `tools::R_user_dir("pulso", "cache")`. Without 'arrow' behaviour is
  unchanged.
* Reads more 'DANE' archive layouts (nested archives with numbered names,
  2020 national files with typos in their names) and 235 of the 237 bundled
  periods are now validated against official 'DANE' figures.

## R CMD check results

* GitHub Actions `r-check.yml` (`R CMD check --as-cran`, 2026-11-28, run
  46132821189): ubuntu-latest (R-release and R-devel), windows-latest and
  macos-latest: 0 errors | 0 warnings | 1 note. The note is "Days since
  last update: 0" (0.2.1 was accepted the same day); it goes away once the
  one-month wait has passed.
* Local `--as-cran` check: not run on the maintainer's current machine
  (an application-control policy blocks loading compiled packages there);
  to be run locally and on win-builder (R-release and R-devel) before
  submission.

## Notes for the reviewer

* 'arrow' is in Suggests and only used behind `requireNamespace("arrow")`;
  tests that need it use `skip_if_not_installed("arrow")`.
* All examples that download data are wrapped in `\donttest{}` plus
  `if (interactive())`. Tests that need the network are skipped on CRAN.
* The bundled snapshots (`trm_superfinanciera_20261128.csv.gz`,
  `ipc_dane_indices_202610.csv`, `salario_minimo.csv`) are small (under
  50 KB each) and are used offline and as fallbacks.
