# pulso documentation

> *El pulso del mercado laboral colombiano.*

Welcome to the documentation for the `pulso` Python package.

## Quick links

- **[Quickstart](quickstart.md)** — install and load your first month
- **[Modules](modules.md)** — what each module contains
- **[Epochs](epochs.md)** — methodological epochs and how we handle the transition
- **[Harmonization](harmonization.md)** — how variables are mapped across epochs (read this before publishing!)
- **[Caveats](caveats.md)** — what this package does *not* promise
- **[Contributing](../CONTRIBUTING.md)** — how to help

## What is this?

`pulso` is a Python package that provides programmatic access to harmonized microdata from Colombia's Gran Encuesta Integrada de Hogares (GEIH), produced monthly by DANE since 2006.

It is **not** an official DANE product. The microdata it downloads come from the public DANE microdata portal; this package is a convenience layer for researchers who would otherwise download and parse those ZIPs by hand.

## Why "harmonized"?

The GEIH was redesigned in 2021 to adopt ILO 19th ICLS recommendations. Variable names, codings, and even some definitions changed. A naive concatenation of 2020-12 and 2021-01 would produce silently incorrect time series.

`pulso` ships a `variable_map.json` that documents how each canonical variable is constructed from the raw DANE columns in each epoch, with citations to the methodological documents. When you call `pulso.load(..., harmonize=True)`, you get columns with consistent meaning across epochs — but the package is loud about which transformations were applied so you can decide if they're appropriate for your use case.

See [`harmonization.md`](harmonization.md) for the methodology in detail.
