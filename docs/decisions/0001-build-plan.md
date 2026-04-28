# ADR 0001: Multi-agent build plan

- **Status:** Accepted
- **Date:** 2026-04-27
- **Deciders:** project owner

## Context

The `pulso` package wraps 20 years of inconsistent DANE microdata behind a stable Python API. The work splits naturally into two streams that can run in parallel:

1. **Code stream**: implementing the loader, downloader, parser, harmonizer, merger, and tests.
2. **Data stream**: discovering DANE URLs, validating them, populating `sources.json`, building the variable map, and writing the scraper.

Building both serially would be slow. Building them as freely-coordinating agents would produce conflicts and incoherent decisions.

## Decision

Use a **structured multi-agent model** with three roles and a hard contract between code and data:

| Role | Who | Owns | Cannot touch |
|------|-----|------|--------------|
| **Builder** | Claude Code (local) | `pulso/_core/`, `pulso/_config/`, `pulso/_utils/`, `tests/`, schemas, CI | `pulso/data/sources.json`, `pulso/data/variable_map.json` |
| **Curator** | Codex / Claude Code (separate session) | `pulso/data/sources.json`, `pulso/data/variable_map.json`, `scripts/agent_scraper.py`, scraper tests | `pulso/_core/`, `pulso/_config/`, `pulso/_utils/` |
| **Architect / QA** | Claude (chat) + human owner | ADRs, design reviews, PR reviews, schema changes, replication tests | direct commits to `main` |

The **contract** between Builder and Curator is the JSON Schemas in `pulso/data/schemas/`. The Builder consumes JSON; the Curator produces JSON. As long as both honor the schema, they can work without communication.

Branch path conventions enforce the separation (`feat/code-*` cannot touch data; `feat/data-*` cannot touch core code), validated by the `protected-paths` CI job.

## Phases

| Phase | Output | Builder | Curator | Architect |
|-------|--------|---------|---------|-----------|
| 0 | Scaffolding | structure, schemas, CI, stubs | — | review |
| 1 | Vertical slice | `load(2024, 6, "ocupados")` works | one validated month in `sources.json` | review, replicate |
| 2 | Harmonizer + merger | transforms, joins, `load_merged` | ~30 priority variables in `variable_map.json` | review |
| 3 | GEIH-2 coverage | (no new code) | all months 2021-present | spot-check |
| 4 | GEIH-1 coverage | encoding fixes if needed | all months 2006-2020 + epoch-1 mappings | replication tests |
| 5 | Scraper | (no new code) | `agent_scraper.py`, GH Action, fixtures | review |
| 6 | Release | docs, examples, expand() | (no changes) | sign-off, PyPI |

## Synchronization points

At the end of each phase, both streams hold and the Architect runs an integration check:
- All tests green
- New data validates against schemas
- No drift between code and data

Phase N+1 does not start until phase N's integration is green.

## Consequences

**Positive:**
- Two concurrent execution streams, ~2x throughput in long phases
- Conflicts are physically prevented by branch path enforcement
- The schema is the single source of design truth
- Clear escalation path: anything ambiguous → Architect → ADR

**Negative:**
- Schema becomes a chokepoint; changes are expensive (need ADR + coordinated update)
- Requires a human (or Claude in chat) actively reviewing PRs; not fully autonomous

**Mitigations:**
- Keep schemas conservative early (Phase 0 over-specifies rather than under-specifies)
- Track every schema change in `docs/decisions/`
- Synthesize fixtures in `tests/fixtures/` so the Builder can develop without waiting on the Curator
