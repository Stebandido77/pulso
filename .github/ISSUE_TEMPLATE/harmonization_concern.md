---
name: Harmonization concern
about: A harmonized variable seems wrong, inconsistent, or undocumented
title: "[harm] variable_name"
labels: harmonization, needs-discussion
assignees: ''
---

## Variable

<!-- Canonical name as in variable_map.json -->

## What seems wrong?

- [ ] Values look implausible compared to DANE published statistics
- [ ] Values differ across epochs in unexpected ways
- [ ] The transform applied isn't documented in `docs/harmonization.md`
- [ ] The `comparability_warning` is missing or unclear
- [ ] Other:

## Evidence

<!--
Provide:
- A code snippet that reproduces the concern
- Comparison numbers (your output vs. DANE's published number)
- Link to the DANE methodological doc you're referencing
-->

```python
import pulso
df = pulso.load(year=YYYY, month=MM, module="...", harmonize=True)
# show the suspicious values
```

## Suggested fix (optional)

<!-- If you know what should change in variable_map.json, describe it -->
