# Internal documentation

This directory contains documentation **about the development process**
of `pulso-co` — audits, technical investigations, phase notes, drafted
issues, and historical verification artefacts.

It is NOT user-facing documentation. End-user docs live in:

- The top-level [`README.md`](../../README.md) (Spanish + English)
- [`CHANGELOG.md`](../../CHANGELOG.md) (release history)
- [`BREAKING_CHANGES_v1.0.0rc2.md`](../../BREAKING_CHANGES_v1.0.0rc2.md)
- [`DEPRECATIONS.md`](../../DEPRECATIONS.md)
- [`docs/architecture.md`](../architecture.md), [`docs/architecture.es.md`](../architecture.es.md)
- [`docs/caveats.md`](../caveats.md)

## Layout

```
docs/internal/
├── AUDIT_REPORT.md                    Pre-rc2 audit (Phase A) — all bugs, gaps, severities
├── FRAGMENTATION_INVESTIGATION.md     pandas block fragmentation root-cause analysis
├── phases/                            Per-phase development notes (Phase 0 → Phase 3)
├── issue_drafts/                      Draft GitHub issue bodies awaiting publication
└── verifications/                     Frozen output of pre-release verification scripts
```

## When to add to this directory

- Decisions or audits that informed a release but don't belong in the
  user-facing changelog.
- Drafted GitHub issues you intend to publish later.
- Output snapshots of verification scripts that prove a contract held
  at a specific commit.

## When NOT to add to this directory

- Anything users need to read to use the library (→ root or `docs/`).
- Anything that becomes stale within one release cycle (delete it instead).
- Anything that should be excluded from the sdist (it already is — see
  `pyproject.toml` `[tool.hatch.build.targets.sdist]`).
