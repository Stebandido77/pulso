# Regression test: multi-period strict=False with corrupted month

**Type:** Test coverage
**Severity:** Medium (defensive test for known fix)
**Target version:** v1.1.0 or sooner
**Found in:** v1.0.0rc2 audit

## Background

During Commit 14 of v1.0.0rc2, a bug was discovered where
`pandas.errors.ParserError` from `parse_shape_a_module` was not being
wrapped, so a single corrupted CSV inside a multi-period range under
`strict=False` aborted the entire load instead of being skipped.

The bug was fixed in Commit 14 by wrapping `_read_csv_with_fallback`
calls in `try/except → ParseError`, which puts the error inside the
`_SKIPPABLE` tuple that `load`/`load_merged` catch.

## What's already in place (rc2)

Commit 9289bcc shipped `tests/unit/test_skippable_parse_error.py` with
four assertions:

1. AST introspection: `ParseError` appears in `load()`'s local `_SKIPPABLE`.
2. AST introspection: `ParseError` appears in `load_merged()`'s local `_SKIPPABLE`.
3. Behavioural: a stubbed `parse_module` raising `ParseError` is swallowed
   by `pulso.load(..., strict=False)` and the call returns an empty
   DataFrame plus the aggregated UserWarning.
4. Behavioural: same stubbed `parse_module` propagates under
   `pulso.load(..., strict=True)`.

Plus `verify_skippable.py` at the repo root for ad-hoc verification.

## What's still missing

Both behavioural tests in (3) and (4) use a registry stubbed to a
**single period**. They prove the catch tuple works, but they don't
prove the *multi-period continue-on-failure* contract end-to-end:

> If period N in `range(start, stop)` raises `ParseError`, every other
> period MUST still be loaded and concatenated, with the failure
> surfaced via the aggregated warning.

A future refactor could keep the unit tests passing while breaking
this multi-period invariant (for example, by moving the catch out of
the per-iteration `try/except` and into a wrapper that aborts on first
error).

## Suggested test to add

```python
@pytest.mark.integration  # uses real DANE for the surviving months
def test_multiperiod_continues_after_corrupted_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ParseError in ONE period must not abort the surrounding range."""
    import pulso
    import pulso._core.parser as parser_mod
    from pulso._utils.exceptions import ParseError

    real_parse = parser_mod.parse_module

    def parse_with_one_failure(zip_path, year, month, *args, **kwargs):
        if (year, month) == (2024, 3):  # arbitrary "corrupted" month
            raise ParseError("simulated CSV corruption")
        return real_parse(zip_path, year, month, *args, **kwargs)

    monkeypatch.setattr(parser_mod, "parse_module", parse_with_one_failure)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        df = pulso.load(
            year=2024,
            month=range(1, 5),  # 4 months: 2024-01..04, with 03 "broken"
            module="ocupados",
            strict=False,
        )

    # 3 of 4 months loaded, year 2024 only.
    assert df["year"].unique().tolist() == [2024]
    assert sorted(df["month"].unique().tolist()) == [1, 2, 4]

    # One aggregated warning naming the broken period.
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) == 1
    assert "2024-03" in str(user_warnings[0].message)
    assert "ParseError" in str(user_warnings[0].message)
```

## Why this is deferred (not blocking rc2)

- The behavioural unit test in `test_skippable_parse_error.py` already
  exercises the catch tuple, just not multi-period.
- The user-case test
  `tests/integration/test_user_use_cases.py::test_exact_user_reported_case`
  loaded 14 of 18 months past 4 real ParseError failures during
  development of Commit 14 — that already exercises the multi-period
  invariant at the integration level (just not deterministically with
  a known synthetic failure).
- Adding a deterministic synthetic-failure test is small and self-
  contained; ideal for v1.1.0.

## References

- Commit 14 (rc2): bug fix
- Commit 9289bcc (rc2): unit-level regression test
- `verify_skippable.py` (rc2): ad-hoc verification script
