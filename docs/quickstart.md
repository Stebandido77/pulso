# Quickstart

## Install

```bash
pip install pulso
```

For older months that DANE published in SPSS or Stata format (rare):

```bash
pip install "pulso[legacy]"
```

## Your first load

```python
import pulso

# What's available?
print(pulso.list_available(year=2024))

# Load one month, one module
df = pulso.load(year=2024, month=6, module="ocupados")
print(df.shape)
print(df.columns.tolist())
```

## Common patterns

### Time series of one month across years

```python
# All Junes from 2018 to 2024
df = pulso.load(
    year=range(2018, 2025),
    month=6,
    module="ocupados",
    harmonize=True,
)
# df has 'year' and 'month' columns to distinguish observations
```

### Multiple months in one year

```python
# Q1 2024
df = pulso.load(year=2024, month=[1, 2, 3], module="ocupados")
```

### Merging modules

```python
df = pulso.load_merged(
    year=2024,
    month=6,
    modules=["caracteristicas_generales", "ocupados", "vivienda_hogares"],
)
# Person-level columns from caracteristicas_generales and ocupados,
# plus household-level columns from vivienda_hogares broadcast to persons.
```

### Weighted estimates

```python
df = pulso.load(year=2024, month=6, module="ocupados")
df = pulso.expand(df)

# Total employed persons
total = (df["_weight"]).sum()

# Mean wage, weighted
import numpy as np
mean_wage = np.average(
    df["ingreso_laboral_mensual"].dropna(),
    weights=df.loc[df["ingreso_laboral_mensual"].notna(), "_weight"],
)
```

> **For inference (standard errors, confidence intervals)**, use a survey-aware
> package like [`samplics`](https://github.com/survey-methods/samplics).
> Naive `df["x"].std() / sqrt(n)` ignores the GEIH's complex sampling design.

## Inspecting the data

```python
# What modules exist?
pulso.list_modules()

# What harmonized variables are defined?
pulso.list_variables()

# Tell me about this variable
pulso.describe_variable("ingreso_laboral_mensual")

# How was it harmonized across epochs?
pulso.describe_harmonization("ingreso_laboral_mensual")
```

## Caching

Downloaded ZIPs and parsed parquets live in `~/.pulso/`. They're permanent because DANE's published microdata are immutable.

```python
pulso.cache_info()        # see what's cached
pulso.cache_clear("harmonized")  # if you change your variable_map
pulso.cache_clear("all")  # full reset
```
