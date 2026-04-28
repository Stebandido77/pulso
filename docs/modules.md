# Modules

The GEIH publishes several thematic files per month. `pulso` exposes these under canonical names.

| Canonical name | Level | Description |
|---|---|---|
| `caracteristicas_generales` | persona | Sex, age, kinship, marital status, ethnicity, education |
| `ocupados` | persona | Employed: occupation, branch of activity, income, formality |
| `desocupados` | persona | Unemployed and labor force: search, duration |
| `inactivos` | persona | Outside labor force: reasons, activities |
| `vivienda_hogares` | hogar | Dwelling and household characteristics |
| `otros_ingresos` | persona | Non-labor income: rents, pensions, transfers |

## Levels

- **`persona`**: one row per person interviewed
- **`hogar`**: one row per household
- **`vivienda`**: one row per dwelling (rare; in GEIH, `vivienda_hogares` covers this)

When merging modules of different levels (e.g., `ocupados` + `vivienda_hogares`), the household-level columns are broadcast to each person in that household.

## Module availability

All six modules exist in both epochs (`geih_2006_2020` and `geih_2021_present`). Use `pulso.list_available(year=Y)` to confirm for a specific period.
