# Deprecations

This file tracks every public-API element that has been marked deprecated
in `pulso-co`, when it was deprecated, and when it is scheduled for removal.

## Active deprecations

### `allow_unvalidated` parameter (in `load` and `load_merged`)

- **Deprecated in:** 1.0.0rc2
- **Will be removed in:** 2.0.0
- **Replacement:** `strict` parameter

The semantics are inverted between the two flags:

| Old kwarg                       | New equivalent       |
|---------------------------------|----------------------|
| `allow_unvalidated=True`        | `strict=False`       |
| `allow_unvalidated=False`       | `strict=True`        |
| (default in rc1) `=False`       | (default in rc2) `=False` (note: opposite semantics) |

The default behaviour also changed — see
[`BREAKING_CHANGES_v1.0.0rc2.md`](BREAKING_CHANGES_v1.0.0rc2.md).

#### Migration

```python
# rc1
pulso.load(year=2024, month=6, module="ocupados", allow_unvalidated=True)
pulso.load(year=2024, month=6, module="ocupados", allow_unvalidated=False)

# rc2
pulso.load(year=2024, month=6, module="ocupados", strict=False)
pulso.load(year=2024, month=6, module="ocupados", strict=True)
```

While `allow_unvalidated` is deprecated it still works — every call
emits a `DeprecationWarning`. Passing both kwargs in the same call
raises `ValueError`.

## Removal log

(Empty — nothing has been removed yet.)
