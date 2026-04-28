---
name: Month fails to load
about: A specific (year, month) is in sources.json but `pulso.load(...)` fails
title: "[load-fail] YYYY-MM module=X"
labels: bug, data
assignees: ''
---

## Period and module

- Year: <!-- e.g., 2019 -->
- Month: <!-- e.g., 4 -->
- Module: <!-- e.g., ocupados -->
- Area: <!-- cabecera / resto / total -->

## Reproduction

```python
import pulso
df = pulso.load(year=YYYY, month=MM, module="X", area="...")
```

## Error

```
<paste full traceback here>
```

## Environment

- pulso version: <!-- output of pulso.__version__ -->
- data_version: <!-- output of pulso.data_version() -->
- Python version:
- OS:

## What I've tried

- [ ] Cleared cache: `pulso.cache_clear("all")`
- [ ] Tried with `harmonize=False`
- [ ] Tried with `area="cabecera"` only

## Notes

<!-- Anything else relevant -->
