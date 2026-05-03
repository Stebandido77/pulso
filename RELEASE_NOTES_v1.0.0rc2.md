# v1.0.0rc2 — Critical bug fixes + API improvements

> ⚠️ **If you installed v1.0.0rc1, please upgrade.** This release fixes a
> critical `TypeError` that affected the documented `allow_unvalidated=True`
> usage pattern.
>
> Upgrade with: `pip install --pre --upgrade pulso-co`

## What's new for users

### Load full historical ranges without crashes

```python
import pulso

# Now works (previously crashed with TypeError on rc1)
df = pulso.load(year=range(2007, 2025), month=6, module="ocupados")

# Cartesian product also works
df = pulso.load(year=range(2018, 2025), month=range(1, 13), module="ocupados")
```

### Inspect what's available

```python
pulso.list_validated_range()      # Returns checksum-validated months
pulso.validation_status()         # Full registry status as DataFrame
pulso.list_variables()            # Harmonized canonical variables
pulso.describe("ocupados", 2024)  # Module metadata
```

### Catch errors cleanly

```python
try:
    df = pulso.load(year=2007, month=1, module="ocupados", strict=True)
except pulso.DataNotValidatedError:
    # Now properly importable from top-level
    pass
```

## Breaking changes & deprecations

### Default for `strict` is now `False` (was effectively the inverse on rc1)

Old behavior (rc1): `pulso.load(year=2007, ...)` raised
`DataNotValidatedError` for unvalidated entries.

New behavior (rc2): `pulso.load(year=2007, ...)` loads the data and emits
a single aggregated `UserWarning`.

To restore old behavior: `pulso.load(year=2007, ..., strict=True)`.

See [`BREAKING_CHANGES_v1.0.0rc2.md`](BREAKING_CHANGES_v1.0.0rc2.md) for
the full migration guide.

### `allow_unvalidated` parameter is deprecated

Use `strict` instead:
- Old: `allow_unvalidated=True` → New: `strict=False`
- Old: `allow_unvalidated=False` → New: `strict=True`

Old parameter still works but emits `DeprecationWarning`. Will be removed
in v2.0.0.

## Bug fixes

- **CRITICAL:** Fixed `TypeError` / `AttributeError` in `download_zip`
  when `checksum_sha256` is `None` — affected 225 of 230 production
  registry entries (3 separate code paths).
- Fixed `download_empalme_zip` not verifying SHA-256 (the README
  documented this, but it wasn't implemented).
- Fixed `load_merged(apply_smoothing=True, modules=[...])` silently
  ignoring the `modules` argument.
- Fixed `load_merged` silently dropping requested modules unavailable
  in the period (now raises `ModuleNotAvailableError`).
- Fixed multi-period `load(year=range(...))` aborting on first failure
  with `strict=False` — it now continues and emits one aggregated
  warning summarising what failed.
- Fixed `expand`, `list_variables`, `describe_variable`,
  `describe_harmonization` raising `NotImplementedError` (now implemented).
- Fixed pandas `PerformanceWarning` ("DataFrame is highly fragmented")
  being escalated to a real error on wide multi-period loads.
- Fixed `pandas.errors.ParserError` from `parse_shape_a_module` leaking
  past the per-period catch and aborting multi-period loads on a single
  bad CSV.
- Fixed README installation command (`pip install pulso-co`, not `pulso`).
- Fixed type validation accepting `bool` and `str` for `year` / `month`
  (now rejected with a clear `TypeError`).
- Fixed `cache_clear(level="...")` silently no-op'ing on unknown levels
  (now raises `CacheError`).

## New features

- `month` and `year` accept `range`, `list`, `tuple`, and any iterable
  of ints. Cartesian product on multi-period.
- `load_empalme(year=range(...))` accepts iterables (was `int`-only).
- New: `pulso.list_validated_range()` → sorted `list[(year, month)]`.
- New: `pulso.validation_status()` → DataFrame of every registry entry.
- New: `pulso.describe(module, year=None, month=None)` — three call
  shapes (catalog / year / period detail), with difflib "did you mean
  ...?" suggestions on unknown modules.
- All exception classes now exported at top level
  (`pulso.DataNotValidatedError`, `pulso.PulsoError`, etc.).
- New exception subclass: `ChecksumMismatchError(DownloadError)`.
- New parameter: `strict: bool = False` (replaces `allow_unvalidated`).
- Aggregated warning for multi-period unvalidated loads (was N warnings,
  now 1).

## Stats

- 16 commits on `feat/v1.0.0rc2`
- 100+ new tests (282 unit + 8 integration vs 463 baseline at rc1)
- Test coverage: 83% (integration tests cover all critical paths)

## Known issues / deferred to v1.1.0

- **Performance:** Shape B (GEIH-2 / 2022+) DataFrames have higher
  block-fragmentation than Shape A. Mitigation in place; root fix in
  v1.1.0. See `ISSUE_DRAFT_fragmentation.md` (will become a tracked
  issue post-release).
- **Test coverage:** an end-to-end multi-period continue-on-failure
  test with a synthetic ParseError will land in v1.1.0. See
  `ISSUE_DRAFT_parse_error_regression.md`.
- **Integration matrix:** the full month range
  (2007-2026, all 240 periods) only runs in the scheduled
  `integration.yml` workflow (Mondays 04:00 UTC). Manual trigger
  available via `gh workflow run integration.yml -f include_slow=true`.

## Acknowledgments

This release was triggered by user testing that exposed the C-1 bug in
v1.0.0rc1. Thank you for using release candidates as intended — that's
what surfaced everything in this changelog.

---

**Full changelog:** [CHANGELOG.md](CHANGELOG.md)
**Migration guide:** [BREAKING_CHANGES_v1.0.0rc2.md](BREAKING_CHANGES_v1.0.0rc2.md)
**Deprecations:** [DEPRECATIONS.md](DEPRECATIONS.md)
**Audit trail:** [AUDIT_REPORT.md](AUDIT_REPORT.md), [FRAGMENTATION_INVESTIGATION.md](FRAGMENTATION_INVESTIGATION.md)
