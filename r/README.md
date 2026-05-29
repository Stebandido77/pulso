# pulso

<!-- badges: start -->
[![R-CMD-check](https://github.com/Stebandido77/pulso/actions/workflows/r-ci.yml/badge.svg)](https://github.com/Stebandido77/pulso/actions/workflows/r-ci.yml)
<!-- badges: end -->

`pulso` provides programmatic access to Colombian microdata, with a focus
on the Gran Encuesta Integrada de Hogares (GEIH) published monthly by
DANE. It is the R companion to the
[`pulso-co`](https://pypi.org/project/pulso-co/) Python package.

## Installation

```r
install.packages("pulso")
```

Development version:

```r
# install.packages("remotes")
remotes::install_github("Stebandido77/pulso", subdir = "r")
```

## Usage

Load a single GEIH module for a given period:

```r
library(pulso)
ocupados <- pulso_load(year = 2024, month = 6, module = "ocupados")
```

Discover and describe canonical variables across survey epochs:

```r
pulso_list_variables(module = "ocupados")
pulso_describe_variable("oci")
```

Fetch the Banco de la República monetary policy rate (TPM):

```r
tpm <- pulso_tpm(start = "2020-01-01")
```

See `vignette("pulso")` for the GEIH workflow and `vignette("banrep")`
for Banco de la República data.

## Data sources

- **GEIH** — Colombia's main household labor survey, 2007–present, via
  DANE's public anonymized microdata releases.
- **Banco de la República** — Monetary policy rate (TPM) via the
  SDMX 2.1 API, with a bundled snapshot as offline fallback.

## License

MIT (c) Esteban Labastidas
