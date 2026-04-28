# Contributing

See the canonical guide at the repo root: [`CONTRIBUTING.md`](../CONTRIBUTING.md).

Quick summary of the build model:

- **Builder** (Claude Code): code under `pulso/_*` and `tests/`. Branch: `feat/code-*`.
- **Curator** (Codex / separate session): JSON data and scraper. Branch: `feat/data-*`.
- **Architect / QA** (Claude in chat + human owner): reviews PRs, manages schema changes, signs off on phases.

The contract between Builder and Curator is the JSON Schema in `pulso/data/schemas/`. CI rejects PRs that cross the boundary (a `feat/code-*` branch touching `sources.json`, or vice versa).
