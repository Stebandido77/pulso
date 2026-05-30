## Submission

This is the first submission of pulso to CRAN.

## R CMD check results

Tested on:
- win-builder R-release (R 4.6.0): 0 errors | 0 warnings | 1 note
- win-builder R-devel (R Under development, 2026-05-28 r90085): 0 errors | 0 warnings | 1 note
- GitHub Actions: windows-latest, macos-latest, ubuntu-latest (R-release and R-devel)

The single note is "New submission" plus a spell-check flag on the DESCRIPTION. All flagged words are intentional:

- `GEIH` — official Spanish acronym for "Gran Encuesta Integrada de Hogares", the household labour survey published by DANE (Colombia's national statistics office). This is the canonical name for the data source.
- `Encuesta`, `Integrada`, `Hogares`, `de` — Spanish words that appear because the official survey name is in Spanish; English translation is provided in the Description text.
- `Microdata` / `microdata` — standard term in survey statistics (e.g., IPUMS microdata, OECD microdata).
- `pulso` — the package name itself.

## Notes for the reviewer

`pulso` lives in the `r/` subdirectory of a monorepo that also contains the Python companion package `pulso-co`. The R package itself is self-contained and standard.

The package bundles a 174 KB Excel snapshot of Banco de la República's monetary policy rate series under `inst/ext/`. It serves as an offline fallback for `pulso_tpm()` when the live SDMX API (`totoro.banrep.gov.co`) is unavailable. Total installed size is well under CRAN limits.
