## Resubmission

This is a resubmission of pulso 0.1.0 addressing the feedback received on the initial submission from Benjamin Altmann (2026-05-30).

## Changes since previous submission

* Wrapped software, package, and API names in single quotes in Title and Description ('GEIH', 'DANE', 'pulso-co', 'Python'), per CRAN policy on formatting software names.
* Replaced `\dontrun{}` with `\donttest{}` in all examples that download data from external sources (DANE microdata and Banco de la República). These examples now run interactively when users invoke `example()`, but are skipped during automated CRAN checks. `pulso_validation_status()` already used `\donttest{}` and was not changed.
* Rewrote the package-level documentation (`?pulso`) to list all 10 exported functions grouped by category and removed an outdated "(More to come)" placeholder.

## R CMD check results

Tested on:
- win-builder R-release (R 4.6.0): 0 errors | 0 warnings | 1 note
- win-builder R-devel (R Under development, 2026-06-04 r90104): 0 errors | 0 warnings | 1 note
- GitHub Actions: windows-latest, macos-latest, ubuntu-latest (R-release and R-devel)

The single note is "New submission" plus a spell-check flag on the DESCRIPTION. All flagged words are intentional:

- `Encuesta`, `Integrada`, `Hogares`, `de` — Spanish words that form part of the official survey name "Gran Encuesta Integrada de Hogares" (the household labour survey published by DANE, Colombia's national statistics office). The official name is in Spanish; the surrounding text is in English.
- `Microdata` / `microdata` — standard term in survey statistics (e.g., IPUMS microdata, OECD microdata).

The previous submission also flagged `GEIH` and `pulso` from the same check; both were resolved by wrapping them in single quotes as requested.

## Notes for the reviewer

`pulso` lives in the `r/` subdirectory of a monorepo that also contains the Python companion package `pulso-co`. The R package itself is self-contained and standard.

The package bundles a 174 KB Excel snapshot of Banco de la República's monetary policy rate series under `inst/ext/`. It serves as an offline fallback for `pulso_tpm()` when the live SDMX API (`totoro.banrep.gov.co`) is unavailable. Total installed size is well under CRAN limits.

The package uses `tools::R_user_dir("pulso", "cache")` for caching downloaded DANE microdata ZIP files on first use. Caching is opt-out via `use_cache = FALSE` in `pulso_load()`.
