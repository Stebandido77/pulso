<!--
Thanks for contributing to pulso!
Please pick a branch name following the convention:
  feat/code-XXX  → for changes to pulso/_core, _config, _utils, tests
  feat/data-XXX  → for changes to pulso/data/*.json or scripts/agent_scraper.py
  fix/XXX        → for bug fixes
  docs/XXX       → for documentation only
-->

## Summary

<!-- What does this PR do? Why? -->

## Type of change

- [ ] Code (logic, refactor, new feature in `pulso/`)
- [ ] Data (`sources.json`, `variable_map.json`, `epochs.json`)
- [ ] Scraper (`scripts/agent_scraper.py`)
- [ ] Tests
- [ ] Docs
- [ ] CI / build

## Phase

<!-- Which phase of the build plan does this belong to? -->
- [ ] 0 — Scaffolding
- [ ] 1 — Vertical slice
- [ ] 2 — Harmonizer + merger
- [ ] 3 — GEIH-2 coverage (2021-present)
- [ ] 4 — GEIH-1 coverage (2006-2020)
- [ ] 5 — Scraper
- [ ] 6 — Validation + release

## Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Linter passes (`ruff check`)
- [ ] If schema changed: bumped `schema_version` in metadata
- [ ] If new data added: `validated` flag is set honestly
- [ ] If touched harmonization: documented in `docs/harmonization.md`
- [ ] No secrets, no real data committed

## Notes for reviewer

<!-- Anything tricky? Edge cases considered? Open questions? -->
