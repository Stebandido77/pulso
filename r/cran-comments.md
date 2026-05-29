## Submission

This is the first submission of pulso to CRAN.

## R CMD check results

Tested on:
- win-builder (R-devel and R-release)
- GitHub Actions: windows-latest, macos-latest, ubuntu-latest (R-release and R-devel)

0 errors | 0 warnings | 1 note

* This is a new release.

## Notes for the reviewer

`pulso` lives in the `r/` subdirectory of a monorepo that also contains
the Python companion package `pulso-co`. The R package itself is
self-contained and standard.

The package bundles a 174 KB Excel snapshot of Banco de la República's
monetary policy rate series under `inst/ext/`. It serves as an offline
fallback for `pulso_tpm()` when the live SDMX API
(`totoro.banrep.gov.co`) is unavailable. Total installed size is well
under CRAN limits.
