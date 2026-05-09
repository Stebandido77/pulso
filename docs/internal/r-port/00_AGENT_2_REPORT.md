# Agente 2 Report — Monorepo Architecture Design

**Date:** 2026-05-08
**Branch:** `feat/r-port`
**Status:** COMPLETE — Awaits human approval on 3 decisions before Agente 3 executes.
**Tier 0 prerequisites for Agente 3:** Decisions Q1–Q3 below resolved.

---

## Executive summary

The Phase 1 R discovery (Agente 1 R) produced 8 architectural decisions, all approved. Decision 4 — sibling-layout monorepo with `python/`, `r/`, `data/` at root — is the keystone, and this Agente 2 report turns it into an executable plan.

The core insight: **the existing wheel uses Hatch's deterministic Feb 2, 2020 timestamps for every file**, so byte-identical reproducibility is achievable as long as (a) file contents don't change, (b) hatchling version is pinned, (c) the build hook copies `data/*` → `pulso/data/*` byte-faithfully. The migration is thus a layout-only change with strong guarantees that PyPI users see no change.

The migration is **10 atomic steps** (~3 hours focused work) executable as a single PR. Every step has explicit verify + revert. The final gate is **wheel content identity** — diffing the new wheel's per-file SHA256 inventory against the committed reference. **No merge if the gate fails.**

Recommendation on the one remaining design decision: **Option B (build-time copy via Hatch hook for `wheel`+`sdist`+`editable` targets, plus `scripts/sync_data.py` for explicit dev sync).** Option A (symlink) breaks on Windows. Option C (runtime path resolution) reduces to B + extra runtime branching that solves nothing.

---

## Final monorepo structure (ASCII tree)

```
pulso/                                    # repo root
├── python/                               # Python package "pulso-co"
│   ├── pulso/                            # importable as `import pulso`
│   │   ├── __init__.py
│   │   ├── _config/  _core/  _utils/  metadata/
│   │   └── data/                         # GITIGNORED, build-time generated
│   ├── tests/                            # 357 tests
│   ├── scripts/                          # add_month.py, validate_sources.py, etc.
│   ├── pyproject.toml                    # + hatch hook + pinned hatchling
│   ├── hatch_build.py                    # NEW: copies ../data → pulso/data on build
│   ├── README.md                         # short, points to root
│   └── .gitignore                        # local: pulso/data/, dist/, build/
├── r/                                    # R package "pulso"
│   ├── DESCRIPTION                       # skeletal, Agente 4 expands
│   ├── NAMESPACE  R/  tests/testthat/    # empty for Agentes 4-5
│   ├── inst/extdata/                     # GITIGNORED, populated by sync_data_to_r.R
│   ├── inst/CITATION
│   ├── vignettes/  man/                  # empty for now
│   ├── README.md  NEWS.md  .Rbuildignore
├── data/                                 # CANONICAL source of truth
│   ├── sources.json                      # 300 KB
│   ├── dane_codebook.json                # 6.6 MB
│   ├── variable_map.json  variable_module_map.json
│   ├── epochs.json  empalme_sources.json  _scraped_catalog.json
│   └── schemas/                          # 6 .schema.json
├── docs/
│   ├── shared/  python/  r/              # per-language docs source
│   └── internal/                         # ADRs, agent reports
│       ├── investigations/  metadata/    # historical (pre-monorepo)
│       ├── r-discovery/                  # Agente 1 R
│       └── r-port/                       # Agente 2+ (THIS REPORT)
├── scripts/                              # cross-language helpers
│   ├── sync_data.py                      # data/ → python/pulso/data/
│   ├── sync_data_to_r.R                  # data/ → r/inst/extdata/
│   ├── wheel_inventory.py                # gate test helper
│   └── bump_version.py                   # rewrites VERSION + pyproject + DESCRIPTION
├── .github/workflows/                    # 6 files post-migration
│   ├── python-ci.yml  r-ci.yml
│   ├── python-publish.yml  r-check.yml
│   └── integration.yml  scrape_monthly.yml  (edited paths)
├── README.md                             # root: Python + R install
├── CHANGELOG.md                          # combined, sectioned per-language
├── VERSION                               # canonical "1.0.0"
├── LICENSE                               # MIT, covers both
├── Makefile                              # convenience targets
└── .gitignore                            # adds python/pulso/data/, r/inst/extdata/, etc.
```

Full file-by-file rationale in `01_directory_structure.md`.

---

## Decision: how `python/pulso/` accesses `data/`

**Recommendation: Option B** — Hatch build hook copies `data/*` → `pulso/data/*` at wheel/sdist/editable build time, plus `scripts/sync_data.py` for explicit dev sync. `python/pulso/data/` is gitignored.

**Why not A (symlink):** Windows-broken (symlinks need Developer Mode or admin). Half of contributors would see empty data dirs.

**Why not C (runtime path resolution):** Wheel must still bundle data anyway, so C reduces to B + extra runtime branching. Adds complexity, solves nothing.

**Hatch build hook spec** (Agente 3 implements `python/hatch_build.py`, ~30 lines):
- Copy `<repo_root>/data/` → `<python_root>/pulso/data/` recursively.
- Ignore `.gitkeep`.
- Fail loudly (raise) if `data/` missing or final JSON count < 13.
- Registered for `wheel`, `sdist`, AND `editable` targets so `pip install -e .` works.

Editable-mode insurance: `make dev-install` runs `python scripts/sync_data.py` then `cd python && pip install -e ".[dev]"`. Documented in root README's developer setup.

---

## Migration plan summary (10 steps for Agente 3)

Detailed in `02_migration_plan.md`. High-level:

| # | Step | Estimate |
|---|---|---|
| 0 | Prereqs: capture pre-migration wheel inventory + SHA + hatchling version | 10 min |
| 1 | Create empty top-level structure (python/, r/, data/, docs/shared/, docs/python/, docs/r/) | 2 min |
| 2 | `git mv pulso/ python/pulso/`, `tests/`, `scripts/` | 5 min |
| 3 | `git mv python/pulso/data/* data/`; remove old data dir | 5 min |
| 4 | Edit `python/pyproject.toml`: pin hatchling + add 3 hook blocks | 15 min |
| 5 | Create `python/hatch_build.py` (the build hook) | 20 min |
| 6 | Create `scripts/sync_data.py` (dev-mode sync) | 10 min |
| 7 | Update root `.gitignore`, create `python/.gitignore` | 5 min |
| 8 | Move + edit GitHub Actions workflows (drop ci.yml + release.yml; add 4 new; edit 2 existing) | 30 min |
| 9 | Create R skeleton + VERSION + Makefile + root README updates | 30 min |
| 10 | **GATE:** end-to-end verification (tests, wheel identity, smoke install, R CMD check) | 30 min |
| | **TOTAL** | **~3 hours** |

Each step is atomic, verifiable, and reversible. Step 10 is the gate — if Tier 1 (wheel content identity) fails, **do not merge**.

---

## CI design summary

Detailed in `03_ci_design.md`. Workflow YAMLs ready in `workflows/`.

| File | Trigger | Status |
|---|---|---|
| `python-ci.yml` | push/PR to `python/**`, `data/**` | NEW (replaces `ci.yml`) |
| `r-ci.yml` | push/PR to `r/**`, `data/**` | NEW |
| `python-publish.yml` | tag `python-v*` | NEW (replaces `release.yml`) |
| `r-check.yml` | tag `r-v*` or workflow_dispatch | NEW (CRAN-strict) |
| `integration.yml` | weekly cron + dispatch | EDITED (paths only) |
| `scrape_monthly.yml` | monthly cron | EDITED (paths only) |

Key features:
- **Per-language paths-filter** — R-only PRs don't trigger Python CI and vice versa.
- **Wheel identity gate** runs on every Python push (catches accidental drift).
- **No coupling** between Python and R workflows.
- **Tag scheme** changes from `v*` to `python-v*` / `r-v*` per Decision 8.

The four NEW workflow YAMLs are committed in this report's `workflows/` subdirectory, ready for Agente 3 to copy into `.github/workflows/`.

---

## Wheel byte-identity verification

Detailed in `04_wheel_identity_verification.md`. The contract:

**Reference wheel** (today's `dist/pulso_co-1.0.0-py3-none-any.whl`):
```
SHA256: b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37
Size:   418,158 bytes
44 internal entries, all timestamped (2020, 2, 2, 0, 0, 0)
```

**Two-tier gate:**

- **Tier 1 (mandatory):** Per-file content identity (name + size + SHA256). If `diff /tmp/wheel-pre.txt /tmp/wheel-post.txt` is non-empty → BLOCK MERGE.
- **Tier 2 (target, may be waived):** Bytes-of-zip identity. Requires hatchling version pinning + clean env.

The reference inventory is committed at `docs/internal/r-port/wheel_reference_inventory.txt` during step 10 of the migration. The CI workflow `python-ci.yml` runs `wheel-identity` on every push and fails if the inventory drifts.

**Gate philosophy:** if a real change to package contents is intended, the developer regenerates the reference inventory + commits it alongside the source change. CI catches accidental drift. Reproducibility is enforced by infrastructure, not human discipline alone.

---

## Risks identified during design

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| W1 | Hatchling version drift between local dev and CI | Medium | Pin `hatchling==X.Y.Z` in `[build-system].requires` (Agente 3 captures the version from current WHEEL file) |
| W2 | Stray dev artifact (`__pycache__`, `.DS_Store`) sneaks into wheel | Medium | `[tool.hatch.build.targets.sdist] exclude` block already covers; verify wheel excludes match. Build hook explicit pattern (`*.json`, `schemas/*.json`) avoids `*` glob |
| W3 | Build hook fails silently on missing `data/` | High | Hook raises `RuntimeError` if `data/` missing or JSON count < 13 |
| W4 | Editable install (`pip install -e .`) leaves `pulso/data/` empty | High | Register hook for `editable` target. Document `make dev-install` as standard dev setup |
| W5 | `[project.scripts]` entry points break post-move | High | Two paths: keep `scripts.X:main` (works since hatch builds from `python/` cwd); OR move scripts inside package as `pulso._scripts.X`. Smoke-test in step 10 |
| W6 | METADATA changes from accidental `[project]` edit | High | Migration plan EXPLICITLY forbids edits outside hooks block. Diff before commit |
| W7 | CRLF line-endings on Windows clones change file content | Medium | Verify `.gitattributes` doesn't normalize `*.py`; if it does, fix or migrate from Linux clone |
| W8 | `protected-paths` job removal breaks open `feat/code-*` branches | Low | Drop in this PR; document in CONTRIBUTING.md |
| W9 | scrape_monthly.yml monthly job opens broken PR if path edits incomplete | Medium | Step 8d explicitly fixes both the script invocation AND the output path |
| W10 | First post-migration `python-v1.1.0` tag publish fails because PyPI Trusted Publisher config still references old workflow `release.yml` | High | Action item for human BEFORE first release: update PyPI project settings → workflow `python-publish.yml`, environment `pypi`. Document in step 8 PR description. |

---

## Decisions required from human (3)

### Q1 — `python/pulso/` access to `data/`: A (symlink), B (build-time copy via hatch hook), or C (runtime path resolution)?

**Recommendation: B.**
- B is cross-platform (Windows-safe).
- Single source of truth (`data/` canonical).
- Wheel byte-identity preserved.
- Editable mode handled by registering hook on `editable` target + `make dev-install`.

A breaks Windows. C reduces to B + needless complexity.

### Q2 — Any structural objections to the proposed tree?

**Default: proceed as drawn.** Specific points where you may want to override:

| Question | My recommendation | Alternative |
|---|---|---|
| `docs/python/` vs `python/docs/`? | `docs/python/` (all docs discoverable from one root) | `python/docs/` (docs co-located with code) |
| Single `CHANGELOG.md` vs per-language? | Single root + `r/NEWS.md` (CRAN expects NEWS) | Two CHANGELOGs |
| Build orchestration tool? | `Makefile` (universal, matches LightGBM/Arrow) | `justfile`, `tasks.py`, npm scripts |
| Drop `protected-paths` job from `python-ci.yml`? | **Yes** — paths-filter replaces branch convention | Keep with updated paths |

### Q3 — OK to use the 10-step migration plan in `02_migration_plan.md` as the Agente 3 brief?

**Default: yes.** The plan is atomic, verifiable, reversible. Step 10 enforces the wheel identity gate.

If you want to amend any step, flag now — the brief is durable.

---

## Files generated by this report

```
docs/internal/r-port/
├── 00_AGENT_2_REPORT.md                  (this file)
├── 01_directory_structure.md             (full tree + Option B rationale)
├── 02_migration_plan.md                  (10 atomic steps for Agente 3)
├── 03_ci_design.md                       (6-workflow design + per-workflow specs)
├── 04_wheel_identity_verification.md     (gate spec for Agente 3)
└── workflows/
    ├── python-ci.yml                     (NEW, ready to drop in .github/workflows/)
    ├── r-ci.yml                          (NEW)
    ├── python-publish.yml                (NEW, replaces release.yml)
    └── r-check.yml                       (NEW, CRAN-strict placeholder)
```

Total: 5 markdown docs (~3,500 lines including code examples) + 4 ready-to-use workflow YAMLs.

---

## Next steps

1. **Human reads `00` (this) + skims `01` §1 (the access decision) + `02` §10 (the gate).**
2. **Human approves Q1, Q2, Q3** (or amends).
3. **Authorize Agente 3** with the approved 10-step plan.
4. Agente 3 executes on a fresh branch `refactor/monorepo-layout` off `feat/r-port`, runs gate, opens PR.
5. Once Agente 3's PR merges to `feat/r-port`, Agentes 4–6 can begin building the R package on the now-stable monorepo layout.

**Critical reminder:** The wheel identity gate (Tier 1) is **not negotiable**. PyPI users must see byte-identical contents post-migration. If anything breaks the gate, fix the issue or do not merge.

---

## Sources

- Agente 1 R discovery: `docs/internal/r-discovery/00_DISCOVERY_REPORT.md`
- Reference wheel: `dist/pulso_co-1.0.0-py3-none-any.whl` (SHA256 `b1c6155782e1...866dc37`)
- [Hatch build hooks](https://hatch.pypa.io/1.9/config/build/)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [r-lib/actions](https://github.com/r-lib/actions)
- [SOURCE_DATE_EPOCH spec](https://reproducible-builds.org/docs/source-date-epoch/)
- Monorepo precedents (from Agente 1 R): apache/arrow, dmlc/xgboost, microsoft/LightGBM
