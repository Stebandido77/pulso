# Tests

This directory contains the test suite for `pulso-co`. Tests are split into
two layers:

| Layer         | Location                | Network? | Default in CI |
|---------------|-------------------------|----------|---------------|
| Unit          | `tests/unit/`           | No       | Yes           |
| Integration   | `tests/integration/`    | Yes      | No (opt-in)   |

## Running unit tests

The unit suite is fast, network-free, and the default. It mocks the
HTTP layer and the parser so the tests exercise only pulso's own logic.

```bash
pytest                    # ~250 tests, < 5 seconds
pytest tests/unit/        # explicit
pytest -k strict_param    # filter by name
```

## Running integration tests

Integration tests download real DANE ZIPs and exercise the whole
pipeline end-to-end. They are skipped by default to keep CI fast and
avoid hitting the DANE servers on every PR.

```bash
pytest --run-integration            # full integration suite
pytest --run-integration -m integration  # same, explicit marker
pytest --run-integration tests/integration/test_all_validated_months.py
```

The first run will populate `~/.cache/pulso/` (~150 MB for the five
validated months). Subsequent runs reuse the cache.

### Per-validated-month coverage

`test_all_validated_months.py` parameterises every month flagged
`validated=true` in `pulso/data/sources.json`. As a new month is
validated, it automatically becomes part of the matrix — no test edits
needed.

## Markers

Defined in `pyproject.toml` under `[tool.pytest.ini_options]`:

- `integration` — needs `--run-integration` (network).
- `real_data` — subset of integration that hits the production DANE URLs.
- `slow` — needs `--run-slow`.
