# Caveats: what this package does NOT promise

Read this before publishing results based on `pulso`.

## 1. Not an official DANE product

`pulso` is an independent Python package. It downloads files from the public DANE microdata portal but is not endorsed, certified, or maintained by DANE. For official statistics, refer to:

- DANE microdata portal: https://microdatos.dane.gov.co/
- DANE press releases: https://www.dane.gov.co/

If your numbers from `pulso` disagree with a DANE publication, **trust the DANE publication** and open an issue here.

## 2. "Harmonized" does not mean "comparable"

The 2021 GEIH redesign was substantive. Even where variable names match across epochs, the underlying questions, sample design, or operational definitions may have changed. The `variable_map.json` documents what was renamed and what was transformed, but it cannot eliminate genuine methodological discontinuities.

Before treating a 2020↔2021 difference as a real change in the world rather than a measurement artifact:

1. Check `pulso.describe_variable("var_name")` for `comparability_warning`
2. Read the relevant section of [`harmonization.md`](harmonization.md)
3. Consult the official DANE empalme documents for the variables you care about

## 3. Naive expansion ≠ rigorous inference

`pulso.expand(df)` multiplies observations by their expansion factor. This gives you point estimates of population totals. It does **not** give you valid standard errors, because the GEIH uses stratified multi-stage sampling.

For valid inference (CIs, hypothesis tests, regression standard errors):

- Use a survey-aware package: [`samplics`](https://github.com/survey-methods/samplics) for Python, or `survey` in R.
- The GEIH is published with stratification and PSU variables; you'll need to point your survey package at them.

## 4. Some months are weird

The `notes` field in each `sources.json` entry flags non-standard months:

- **2020-04 to 2020-07**: pandemic, partial telephone-based collection
- **Specific months with reweighting**: when DANE republishes weights after a population update
- Other one-offs: any time DANE issues an erratum, the `validated_at` and `notes` fields are updated

Always inspect `pulso.list_available(year=...)` for the period you care about and read the `notes`.

## 5. Cache invalidation is your responsibility (sort of)

If you change `variable_map.json` (e.g., contributing a new harmonization rule), the package does NOT automatically re-harmonize cached parquets. Run:

```python
pulso.cache_clear("harmonized")
```

Raw and parsed caches don't need invalidation because their inputs are immutable (the DANE ZIP and the parser).

## 6. ECH 2000-2005 is not in this package

See [ADR 0002](decisions/0002-scope-2006-present.md). If you need ECH, use a different tool — and don't try to mechanically concatenate ECH and GEIH series.

## 7. The scraper might be wrong

The monthly scraper is a maintenance convenience, not an oracle. New entries in `sources.json` from the scraper start with `validated: false`, and `pulso.load(...)` refuses to load them by default. A human reviewer flips the flag after spot-checking.

If you set `allow_unvalidated=True`, you're acknowledging that you're loading data the project hasn't yet vouched for.

## 8. This is research software

Bugs exist. Test your conclusions against published DANE statistics for at least one period before using `pulso` outputs for high-stakes work. Open issues when something looks off.
