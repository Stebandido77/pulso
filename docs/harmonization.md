# Harmonization methodology

> **Status:** This document grows as harmonized variables are added.
> Each variable in `variable_map.json` should have a corresponding section here when its transform is non-trivial.

## How to read this

For each canonical variable, we document:

1. **What it represents** (the concept)
2. **Where it comes from** in each epoch (the source DANE variable)
3. **What transformation we apply** (verbatim from `variable_map.json`)
4. **Why** (citation to DANE methodology)
5. **Comparability warnings** when applicable

If you see a harmonized column in your DataFrame and want to know what it means, look it up here. If you can't find it documented, that's a bug — open an issue.

## Conventions

- "Identity" means we just renamed the column. No values changed.
- "Recode" means we mapped specific source codes to canonical codes (e.g., 1↔1, 2↔2, 9→null).
- "Compute" means we applied an arithmetic expression to one or more source columns.
- "Custom" means a named Python function in `pulso._core.harmonizer`. The function's docstring contains the methodology.

## The 2021 transition

The single biggest source of harmonization concern. In January 2021, DANE switched:

- **Sampling frame:** 2005 Census → 2018 Census
- **Methodology:** ICLS-13 → ICLS-19 (ILO Resolution I, 2013)
- **Some variable definitions** (notably around informality and labor underutilization)

DANE published a technical document explaining the empalme (linkage) of pre- and post-2021 series. We follow that document where it gives clear guidance.

> **Reference:** DANE (2021). *Documento metodológico: Gran Encuesta Integrada de Hogares — Marco 2018.*
> When you call `pulso.describe_harmonization("variable_name")`, the `source_doc` field cites the relevant section.

## Variables (populated as Phase 2-4 progresses)

### `edad` *(Phase 2)*

Age in completed years.

| Epoch | Source variable | Transform |
|-------|-----------------|-----------|
| `geih_2006_2020` | `P6040` | identity |
| `geih_2021_present` | `P6040` | identity |

No methodological change. Direct rename.

### `sexo` *(Phase 2)*

Person's sex.

| Epoch | Source variable | Transform |
|-------|-----------------|-----------|
| `geih_2006_2020` | `P6020` | identity (1=hombre, 2=mujer) |
| `geih_2021_present` | `P6020` | identity (1=hombre, 2=mujer) |

### `ingreso_laboral_mensual` *(Phase 2)*

Monthly nominal labor income in current Colombian pesos.

⚠️ **Comparability warning.** Although the variable name `INGLABO` is the same in both epochs, the imputation methodology differs. DANE published an empalme series that adjusts pre-2021 values to the post-2021 methodology; this package does **not** apply that adjustment automatically. If you need a comparable real-income series across 2020↔2021, apply the official empalme manually after loading.

| Epoch | Source variable | Transform | Notes |
|-------|-----------------|-----------|-------|
| `geih_2006_2020` | `INGLABO` | identity | Imputed by DANE |
| `geih_2021_present` | `INGLABO` | identity | Imputed by DANE under new methodology |

---

*More variables will be added in Phase 3+.*
