# Harmonizer Core Design

This note designs `harmonize(raw_df, variable_map_entry, epoch_key) -> pd.Series`, the lowest-level runtime function that converts one canonical variable from raw DANE columns into a harmonized pandas Series.

The prompt schema uses `source_variables` and a flat transform payload; the current `pulso` repository still exposes a slightly older schema shape in `variable_map.schema.json`. The design below treats the prompt schema as the target contract, while keeping the error boundaries compatible with `pulso._utils.exceptions`.

## 1. Function signature and contract

```python
def harmonize(
    raw_df: pd.DataFrame,
    variable_map_entry: Mapping[str, Any],
    epoch_key: str,
) -> pd.Series:
    ...
```

`raw_df` is the unharmonized module DataFrame returned by `pulso.load(harmonize=False)`. `variable_map_entry` is one entry from `variable_map.json`, i.e. the value stored under a canonical variable name inside `variables`. `epoch_key` is a key such as `geih_2006_2020` or `geih_2021_present`.

The function returns a `pd.Series` with:

- the same index as `raw_df`
- `name` set to the canonical variable name
- harmonized values for the requested epoch
- dtype coerced as far as the declared variable type and transform allow

The function should raise when the config is incomplete, inconsistent, or references raw columns that are not present. It should not silently fabricate values. If a transform cannot be applied to at least one non-null input because of invalid config or invalid source data, the function should raise rather than partially succeed with corrupted output.

Recommended split of responsibilities:

- `ConfigError` for structural problems in `variable_map_entry` or epoch selection
- `HarmonizationError` for runtime transformation failures on a valid-looking config
- `ParseError` is not a fit here because parsing has already happened upstream

## 2. Algorithm dispatch

The function should first resolve `canonical_name` from the parent key supplied by the caller or from the entry context; if that is not available, the caller should wrap this function so the canonical name is known when setting `Series.name`.

Then resolve `epoch_mapping = variable_map_entry["mappings"][epoch_key]`. Minimal common checks:

- `epoch_key` must exist in `mappings`
- `source_variables` must be a non-empty list of strings
- `transform` must be one of `identity`, `recode`, `cast`, `compute`, `coalesce`
- all required source columns must exist in `raw_df.columns`

### `identity`

Minimal logic: return `raw_df[source_variables[0]]` copied or viewed as a Series, preserving nulls, then rename to the canonical name.

Expected fields:

- variable-level: `type`, `mappings`
- epoch-level: `source_variables` with exactly one column, `transform="identity"`

Edge cases:

- if more than one source column is declared, raise `ConfigError`
- if the source column is absent, raise `HarmonizationError`
- do not coerce dtype unless the broader harmonizer contract explicitly says variable type enforcement happens here

### `recode`

Minimal logic: map source values through `recode_map`; preserve null inputs as null outputs; optionally validate against declared categorical metadata.

Expected fields:

- epoch-level: one source column, `transform="recode"`, `recode_map`
- variable-level: for categorical variables, `categories` may be used for post-map validation

Edge cases:

- missing keys in `recode_map` need a decision: either preserve original value, map to null, or raise; recommendation is raise unless the schema later adds an explicit default rule
- string `"1"` versus integer `1` mismatches are common in survey data; implementation should compare using the source dtype as-is, not by stringifying everything
- if recoded output cannot fit the declared type, raise `HarmonizationError`
- null values should bypass the map and remain null

### `cast`

Minimal logic: cast one source column to `target_dtype`.

Expected fields:

- epoch-level: one source column, `transform="cast"`, `target_dtype`

Edge cases:

- nullable integer targets should use pandas nullable dtypes like `Int64`, not NumPy `int64`, so nulls survive
- boolean casts are ambiguous for values like `0/1`, `"0"/"1"`, `"True"/"False"`; this needs a strict conversion table, not Python truthiness
- failed coercion of non-null values should raise `HarmonizationError` with the offending dtype and variable name

### `compute`

Minimal logic: evaluate `formula` from one or more source columns and return the resulting Series.

Expected fields:

- epoch-level: `source_variables`, `transform="compute"`, `formula`

Edge cases:

- missing input columns should raise before evaluation
- arithmetic with nulls should follow pandas semantics unless the formula language specifies otherwise
- division by zero, invalid operators, or references to undeclared columns should raise `HarmonizationError`
- recommendation: do not use raw Python `eval`; use a restricted expression evaluator or tiny DSL limited to arithmetic, parentheses, constants, and explicitly referenced columns

### `coalesce`

Minimal logic: return the first non-null value across `source_variables`, evaluated left to right per row.

Expected fields:

- epoch-level: `source_variables` with length >= 1, `transform="coalesce"`

Edge cases:

- ordering matters and must be preserved exactly as declared
- if all values are null in a row, output null
- if source columns have incompatible dtypes, pandas may upcast to `object`; the implementation should either accept that or do a final cast based on declared variable type

## 3. Error handling

Use `ConfigError` when the JSON declaration is wrong or incomplete:

- `Variable 'sexo' has no mapping for epoch 'geih_2021_present'.`
- `Variable 'edad': transform 'cast' requires field 'target_dtype'.`
- `Variable 'clase_ocupacion': identity expects exactly 1 source variable, got 2.`
- `Unknown epoch key 'geih_2030_future'.`

Use `HarmonizationError` when the config is valid but application fails on actual data:

- `Variable 'edad': source column 'P6040' not found in raw data for epoch 'geih_2021_present'.`
- `Variable 'estrato': recode_map does not define source value 9.`
- `Variable 'meses_busqueda': failed cast to 'Int64' due to non-numeric value 'NS/NR'.`
- `Variable 'ingreso_hora': compute formula 'INGLABO / HORAS' failed: division by zero.`

`ParseError` should remain upstream for file-reading failures only.

If more granularity is desired later, a dedicated subclass such as `MissingSourceColumnError(HarmonizationError)` could help tests and user messaging, but it is not required for Phase 2.

## 4. Testing strategy

1. Identity returns the same values and index as the raw source column and sets the canonical series name.
2. Identity raises `ConfigError` when `source_variables` contains more than one column.
3. Identity raises `HarmonizationError` when the declared source column is absent from `raw_df`.
4. Recode maps integer survey codes to canonical integer codes while preserving null inputs.
5. Recode maps string survey codes correctly without coercing integer keys into strings.
6. Recode raises `HarmonizationError` when a non-null source value is missing from `recode_map`.
7. Cast converts a numeric string column to nullable integer dtype and preserves null rows.
8. Cast converts a numeric column to string dtype without altering index or series name.
9. Cast raises `HarmonizationError` when a non-null value cannot be coerced to the requested dtype.
10. Compute evaluates a simple arithmetic formula using two declared source columns.
11. Compute propagates nulls according to pandas arithmetic semantics.
12. Compute raises `HarmonizationError` when the formula references a column not listed in `source_variables`.
13. Coalesce returns the first non-null value in declared left-to-right order across three source columns.
14. Coalesce returns null when every source column is null for a row.
15. A categorical variable with bilingual variable descriptions and declared categories returns canonical codes only, while category validation rejects harmonized values outside the allowed category set.

## 5. Open design questions

- What is the exact structure and role of `categories`? If it is only metadata, `harmonize` should validate allowed codes but should not replace codes with labels.
- What should happen for recode misses? I recommend fail-fast by default, because silent passthrough hides comparability bugs.
- Should every transform perform a final dtype normalization based on variable-level `type`, or should transform-specific dtypes be authoritative?
- How should categorical values outside `categories` behave? My recommendation is raise `HarmonizationError` for non-null out-of-domain values.
- Should `compute` support only arithmetic expressions, or a broader DSL with conditionals? I recommend a very small DSL first; avoid Python `eval`.
- How should booleans be represented canonically: pandas `boolean`, Python `bool`, or integer `0/1` codes?
- Coalesce returning null when all inputs are null is natural, but should that ever be flagged for required variables?
- Should source column existence be validated eagerly for every declared variable during registry load, or only lazily at harmonization time? For this function, lazy runtime validation is sufficient.

## 6. Pseudocode skeleton

```python
def harmonize(raw_df, variable_map_entry, epoch_key):
    canonical_name = variable_map_entry["canonical_name"]
    mappings = variable_map_entry.get("mappings")
    if not isinstance(mappings, dict):
        raise ConfigError(f"Variable '{canonical_name}' has invalid mappings block.")

    if epoch_key not in mappings:
        raise ConfigError(
            f"Variable '{canonical_name}' has no mapping for epoch '{epoch_key}'."
        )

    mapping = mappings[epoch_key]
    source_variables = mapping.get("source_variables")
    transform = mapping.get("transform")

    if not isinstance(source_variables, list) or not source_variables:
        raise ConfigError(
            f"Variable '{canonical_name}': source_variables must be a non-empty list."
        )

    missing = [col for col in source_variables if col not in raw_df.columns]
    if missing:
        raise HarmonizationError(
            f"Variable '{canonical_name}': source columns not found: {missing!r}."
        )

    def _named(series):
        series.name = canonical_name
        return series

    if transform == "identity":
        if len(source_variables) != 1:
            raise ConfigError(
                f"Variable '{canonical_name}': identity expects exactly 1 source variable."
            )
        result = raw_df[source_variables[0]]
        return _named(result)

    if transform == "recode":
        recode_map = mapping.get("recode_map")
        if not isinstance(recode_map, dict):
            raise ConfigError(
                f"Variable '{canonical_name}': transform 'recode' requires recode_map."
            )
        source = raw_df[source_variables[0]]
        result = recode_series_strict(source, recode_map, canonical_name)
        validate_categories_if_needed(result, variable_map_entry, canonical_name)
        return _named(result)

    if transform == "cast":
        target_dtype = mapping.get("target_dtype")
        if not target_dtype:
            raise ConfigError(
                f"Variable '{canonical_name}': transform 'cast' requires target_dtype."
            )
        source = raw_df[source_variables[0]]
        result = cast_series_strict(source, target_dtype, canonical_name)
        return _named(result)

    if transform == "compute":
        formula = mapping.get("formula")
        if not formula:
            raise ConfigError(
                f"Variable '{canonical_name}': transform 'compute' requires formula."
            )
        frame = raw_df[source_variables]
        result = eval_safe_formula(formula, frame, allowed_names=source_variables)
        return _named(result)

    if transform == "coalesce":
        frame = raw_df[source_variables]
        result = coalesce_left_to_right(frame)
        return _named(result)

    raise ConfigError(
        f"Variable '{canonical_name}': unsupported transform {transform!r}."
    )
```
