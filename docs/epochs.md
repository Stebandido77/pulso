# Epochs

The GEIH has two methodological epochs that `pulso` covers and harmonizes across.

## `geih_2006_2020` — GEIH marco 2005

- **Period:** 2006-01 to 2020-12 (180 months)
- **Sampling frame:** 2005 Census
- **Coverage:** 23 cities + metropolitan areas + rural ("resto")
- **Default expansion weight:** `fex_c_2011`
- **File encoding:** `latin-1` in most months
- **CSV separator:** `;` (semicolon)
- **CSV decimal mark:** `,` (comma)

This epoch begins with the launch of the GEIH in January 2006 (replacing the ECH) and ends in December 2020 just before the redesign.

## `geih_2021_present` — GEIH rediseñada

- **Period:** 2021-01 onward
- **Sampling frame:** 2018 Census
- **Coverage:** 23 cities + metropolitan areas + rural ("resto")
- **Default expansion weight:** `FEX_C18`
- **File encoding:** `utf-8`
- **CSV separator:** `;`
- **CSV decimal mark:** `,`

The 2021 redesign applied recommendations from the ILO's 19th International Conference of Labour Statisticians (2013), notably affecting how informality, time-related underemployment, and labor force participation are measured.

## What changes between epochs

| Aspect | 2006-2020 | 2021-present |
|---|---|---|
| Sampling frame | Census 2005 | Census 2018 |
| Encoding | latin-1 | utf-8 |
| Weight variable | `fex_c_2011` | `FEX_C18` |
| Merge keys (persona) | `DIRECTORIO`, `SECUENCIA_P`, `ORDEN` | `DIRECTORIO`, `SECUENCIA_P`, `ORDEN` |
| Module file naming | varies by year | "Cabecera - X.CSV" / "Resto - X.CSV" |

The merge keys are nominally the same; the harmonizer normalizes column names to match.

## What does NOT change at the epoch boundary

The DANE took care to preserve some continuity. The variable name `P6040` (age) means the same thing in both epochs. The variable name `INGLABO` (labor income) exists in both but with different imputation methodology — see [`harmonization.md`](harmonization.md).

## What about within-epoch changes?

Within `geih_2006_2020` there are smaller methodological notes (occasional reweightings, the 2020 pandemic period). These are flagged in the per-month `notes` field of `sources.json` and surfaced via `pulso.list_available()`.

## Why no `geih_2000_2005` epoch?

That period is the ECH, a different survey. See [ADR 0002](decisions/0002-scope-2006-present.md).
