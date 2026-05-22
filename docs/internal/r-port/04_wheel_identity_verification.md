# 04 — Wheel Byte-Identity Verification (Migration Gate)

**Phase:** Agente 2, Phase 4
**Status:** Gate spec — Agente 3 may NOT merge to `main` if this gate fails.

---

## TL;DR

After Agente 3 finishes the migration, building the wheel from `python/` MUST produce a wheel whose **content tree** is byte-identical to the reference wheel `dist/pulso_co-1.0.0-py3-none-any.whl` shipped today on PyPI.

We have a strong reproducibility position: the existing wheel uses **Hatch's deterministic Feb 2, 2020 timestamps** for every entry. As long as (a) file *contents* match, (b) file *layout* in the wheel matches, (c) hatchling version is pinned to the version that built the reference wheel, the resulting `.whl` will match byte-for-byte.

The gate has **two tiers**:

1. **Tier 1 (mandatory): Content identity.** For each file in the wheel, name + size + SHA256 must match the reference. If any file in the new wheel is missing or differs, **block merge**.
2. **Tier 2 (target, may be waived with justification): Bytes-of-zip identity.** SHA256 of the entire `.whl` file matches. This requires hatchling version pinning + clean build env.

---

## 1. The reference wheel

Today's shipped artifact:

```
File:    dist/pulso_co-1.0.0-py3-none-any.whl
Size:    418,158 bytes
SHA256:  b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37
```

(Confirmed locally on 2026-05-08 against the wheel built for the v1.0.0 release.)

Every file inside the zip uses timestamp `(2020, 2, 2, 0, 0, 0)` — Hatch's default unchanging value when `SOURCE_DATE_EPOCH` is unset (per [Hatch build docs](https://hatch.pypa.io/1.9/config/build/)).

**File inventory** (44 entries total):

```
   2325  pulso/__init__.py
     83  pulso/_config/__init__.py
   4959  pulso/_config/epochs.py
  16098  pulso/_config/registry.py
   1404  pulso/_config/variables.py
     56  pulso/_core/__init__.py
   4809  pulso/_core/downloader.py
  19500  pulso/_core/empalme.py
   2894  pulso/_core/expander.py
  15965  pulso/_core/harmonizer.py
   4533  pulso/_core/harmonizer_funcs.py
  27975  pulso/_core/loader.py
   5686  pulso/_core/merger.py
  17205  pulso/_core/parser.py
     36  pulso/_utils/__init__.py
   2971  pulso/_utils/cache.py
   2171  pulso/_utils/columns.py
   2037  pulso/_utils/exceptions.py
    785  pulso/_utils/logging.py
   5128  pulso/_utils/validation.py
 113553  pulso/data/_scraped_catalog.json
6853633  pulso/data/dane_codebook.json
   6033  pulso/data/empalme_sources.json
   3174  pulso/data/epochs.json
 306831  pulso/data/sources.json
  37384  pulso/data/variable_map.json
   2297  pulso/data/variable_module_map.json
   5411  pulso/data/schemas/dane_codebook.schema.json
   4161  pulso/data/schemas/empalme_sources.schema.json
   4868  pulso/data/schemas/epochs.schema.json
   7329  pulso/data/schemas/sources.schema.json
   5516  pulso/data/schemas/variable_map.schema.json
   1526  pulso/data/schemas/variable_module_map.schema.json
   1309  pulso/metadata/__init__.py
   7178  pulso/metadata/api.py
  14637  pulso/metadata/composer.py
  10097  pulso/metadata/parser.py
   1891  pulso/metadata/schema.py
  28131  pulso_co-1.0.0.dist-info/METADATA
     87  pulso_co-1.0.0.dist-info/WHEEL
    114  pulso_co-1.0.0.dist-info/entry_points.txt
   1075  pulso_co-1.0.0.dist-info/licenses/LICENSE
   3629  pulso_co-1.0.0.dist-info/RECORD
```

This list is the contract. Any deviation (file added, removed, size changed, content changed) is a merge blocker.

---

## 2. Why content identity is achievable

The Python package source files don't change — `git mv pulso/ python/pulso/` preserves byte content. The data JSONs likewise are moved from `pulso/data/` to `data/` and copied back into `pulso/data/` by the build hook with byte-identical content.

The four files that **could** drift:

| File | Why it could change | Mitigation |
|---|---|---|
| `pulso_co-1.0.0.dist-info/METADATA` | Generated from `[project]` block of `pyproject.toml`. If we edit any field (`description`, `keywords`, `urls`), it changes. | Migration plan forbids editing `[project]` content; only `[tool.hatch.build]` and `[tool.hatch.build.targets.*.hooks]` blocks are touched. |
| `pulso_co-1.0.0.dist-info/RECORD` | Lists every file in the wheel with its SHA256 + size. Computed automatically. | If the file inventory matches, RECORD will match. |
| `pulso_co-1.0.0.dist-info/WHEEL` | Records the build tool: `Generator: hatchling X.Y.Z`. | Pin hatchling in `python/pyproject.toml` `[build-system].requires` to the **exact** version that built the reference wheel. |
| `pulso_co-1.0.0.dist-info/entry_points.txt` | Generated from `[project.scripts]`. | Verify entries: `pulso-validate-sources = scripts.validate_sources:main` and `pulso-add-month = scripts.add_month:main`. Path module names must resolve correctly from `python/` cwd (where build runs). |

To find the exact hatchling version that built the reference wheel:

```bash
unzip -p dist/pulso_co-1.0.0-py3-none-any.whl pulso_co-1.0.0.dist-info/WHEEL
# Output:
# Wheel-Version: 1.0
# Generator: hatchling X.Y.Z
# Root-Is-Purelib: true
# Tag: py3-none-any
```

**Action item for Agente 3:** Run that command, record the version, set `python/pyproject.toml` `[build-system] requires = ["hatchling==X.Y.Z"]`. Pre-migration `pyproject.toml` says `requires = ["hatchling>=1.18"]` — this needs to become a pinned `==` to lock determinism.

---

## 3. Why bytes-of-zip identity is harder (but achievable)

Beyond content identity, byte identity of the `.whl` file requires:

1. **Same compression:** Python's `zipfile` uses `ZIP_DEFLATED` with default compression level 6. Hatch passes through. **Stable across Python versions and OSes.**
2. **Same file order in the zip:** Hatch sorts alphabetically. Stable.
3. **Same per-file timestamps:** `(2020, 2, 2, 0, 0, 0)` everywhere. Stable for as long as we don't set `SOURCE_DATE_EPOCH`.
4. **Same file contents:** Covered above.
5. **Same metadata text:** `METADATA`, `WHEEL`, `RECORD`, `entry_points.txt`. Covered above.
6. **Same hatchling version:** Pinned in `[build-system] requires`.

Empirically, when all six hold, the `.whl` SHA256 is identical. IPython has shipped byte-identical wheels since 7.16.1 ([Quansight Labs report](https://labs.quansight.org/blog/2020/08/ipython-reproducible-builds)).

**Risk:** if the maintainer's local hatchling has been upgraded since the v1.0.0 build (pip auto-upgraded a transitive), the WHEEL line `Generator: hatchling 1.X.Y` differs and Tier 2 fails. Tier 1 (content identity) still passes. **Tier 2 may be waived if Tier 1 passes and the only diff is the WHEEL `Generator:` line.**

---

## 4. The gate test (Agente 3 runs this before merging)

### Pre-migration: capture the reference

```bash
# Run from repo root, on main (pre-Agente-3 branch)
cd /path/to/pulso
python -m build  # produces dist/pulso_co-1.0.0-py3-none-any.whl

# Save reference inventory + per-file SHAs
python scripts/wheel_inventory.py dist/pulso_co-1.0.0-py3-none-any.whl > /tmp/wheel-pre.txt
sha256sum dist/pulso_co-1.0.0-py3-none-any.whl > /tmp/wheel-pre.sha256
```

### Post-migration: verify

```bash
# After Agente 3 has migrated, on feat/r-port (with monorepo layout)
cd /path/to/pulso/python
python -m build  # produces python/dist/pulso_co-1.0.0-py3-none-any.whl

python ../scripts/wheel_inventory.py dist/pulso_co-1.0.0-py3-none-any.whl > /tmp/wheel-post.txt
sha256sum dist/pulso_co-1.0.0-py3-none-any.whl > /tmp/wheel-post.sha256

# Tier 1: Content identity
diff /tmp/wheel-pre.txt /tmp/wheel-post.txt
# Expected output: empty (no differences). Non-empty → BLOCK MERGE.

# Tier 2: Bytes identity (target, waivable)
diff /tmp/wheel-pre.sha256 /tmp/wheel-post.sha256
# Expected: empty (SHAs match). Diff in path component (dist/ vs python/dist/) is fine.
```

### `scripts/wheel_inventory.py` (spec for Agente 3 to write)

```python
# scripts/wheel_inventory.py — pseudo-spec, real impl is Agente 3
"""Print a deterministic content inventory of a wheel for diff-based comparison."""
import hashlib, sys, zipfile

def main(path: str) -> None:
    with zipfile.ZipFile(path) as z:
        rows = []
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            with z.open(info) as f:
                sha = hashlib.sha256(f.read()).hexdigest()
            rows.append(f"{info.file_size:>10}  {sha}  {info.filename}")
    print("\n".join(rows))

if __name__ == "__main__":
    main(sys.argv[1])
```

Output format (one line per file, deterministic order, content SHA256 + size + name). Trivially diff-able.

---

## 5. CI assertion (permanent gate)

Add this assertion to the new `python-ci.yml` workflow (see `03_ci_design.md`):

```yaml
  wheel-identity:
    name: Wheel content identity
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install build
        run: pip install build
      - name: Build wheel
        run: cd python && python -m build --wheel
      - name: Compare to reference inventory
        run: |
          python scripts/wheel_inventory.py python/dist/pulso_co-*.whl > /tmp/now.txt
          diff docs/internal/r-port/wheel_reference_inventory.txt /tmp/now.txt
```

The reference inventory file `docs/internal/r-port/wheel_reference_inventory.txt` is committed once (by Agente 3 during migration) and should change only when:
- A real new file is added to the package (intentional change).
- Existing file is intentionally edited (intentional change).

In both cases the developer manually regenerates the reference and commits it alongside the source change. CI catches accidental drift.

---

## 6. Risk register specific to wheel identity

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| W1 | Hatchling version drift between local dev and CI | Medium | Pin `hatchling==X.Y.Z` in `[build-system] requires`. CI uses fresh venv, deterministic. |
| W2 | New file accidentally gets bundled (e.g. `__pycache__`, `.DS_Store`, dev artifact under `pulso/`) | Medium | Existing `[tool.hatch.build.targets.sdist] exclude` block already blocks `**/__pycache__`, `**/*.pyc`. Verify it also applies to wheel target (Hatch shares exclusions). Add `pulso/data/` to `.gitignore` so dev edits don't sneak in. |
| W3 | Build hook copies extra files from `data/` (e.g. a stray `.DS_Store` left by macOS contributor) | Medium | Build hook should explicitly enumerate file patterns: only `*.json` + `schemas/*.json`, not `*`. |
| W4 | Build hook fails silently when `data/` is missing (e.g. CI checks out wrong tree) | High | Hook raises `RuntimeError` if `data/` doesn't exist or is empty. Fail loudly. |
| W5 | `[project.scripts]` entry points reference `scripts.add_month:main` but post-migration `scripts/` is at `python/scripts/` and is not on `sys.path` | High | Hatch builds wheel with `cwd = python/`. From there, `scripts/` is a sibling. Two options: (a) keep `scripts.add_month:main` (works because `python/` is the build root and Hatch finds `python/scripts/`), or (b) make `scripts` a real package by adding `python/scripts/__init__.py`. Verify in Agente 3 dry-run. |
| W6 | METADATA changes because pyproject.toml was edited beyond hooks block | High | Migration plan EXPLICITLY says: "Do not edit any `[project]`, `[tool.pytest]`, `[tool.ruff]`, `[tool.coverage]`, `[tool.mypy]` content. Only add `[tool.hatch.build.targets.*.hooks.custom]` and pin `hatchling==X.Y.Z`." |
| W7 | Whitespace/line-ending changes in moved Python files (CRLF on Windows clone) | Medium | Verify `.gitattributes` doesn't normalize line endings on `*.py`. If it does, set `* -text` for Python files OR make the migration on a fresh Linux clone. |

---

## 7. If Tier 1 fails

If the post-migration wheel diverges from the reference at Tier 1 (content identity), Agente 3 must:

1. Run `diff /tmp/wheel-pre.txt /tmp/wheel-post.txt` to identify which file(s).
2. For each differing file, use `unzip -p OLD.whl X | sha256sum` vs `unzip -p NEW.whl X | sha256sum` to confirm.
3. Investigate root cause:
   - Missing file → build hook didn't copy it. Fix hook.
   - Extra file → build hook copied something it shouldn't. Add exclusion.
   - Same name, different content → file was modified during migration (shouldn't happen with `git mv`). Investigate.
4. Fix and re-test.
5. **Do not merge until Tier 1 passes clean.**

If Tier 2 fails but Tier 1 passes:

1. Run `cmp` on the two wheels to find first diff offset.
2. Use `python -c "import zipfile; ..."` to inspect that region.
3. Most common cause: METADATA differs because hatchling version differs. Pin and rebuild.
4. Acceptable to merge with Tier 1 only IF the human approves the waiver.

---

## 8. Sign-off contract for Agente 3

Agente 3's PR description (or report) MUST include:

```
## Wheel identity verification

Reference wheel:
  SHA256: b1c6155782e1177cec1715048b5f52a4d3a01cf6dbfc8edcdcbeaf99c866dc37
  Size:   418158 bytes

Post-migration wheel:
  SHA256: <computed>
  Size:   <computed>

Tier 1 (content identity): PASS / FAIL
Tier 2 (bytes identity):   PASS / FAIL / WAIVED (reason: ...)

Inventory diff:
  <output of `diff /tmp/wheel-pre.txt /tmp/wheel-post.txt`>
```

If Tier 1 = FAIL or Tier 2 = FAIL without explicit waiver from human → **DO NOT MERGE**.

---

## Sources

- [Hatch — Build configuration](https://hatch.pypa.io/1.9/config/build/) (deterministic timestamps)
- [SOURCE_DATE_EPOCH — reproducible-builds.org](https://reproducible-builds.org/docs/source-date-epoch/)
- [IPython reproducible builds — Quansight Labs](https://labs.quansight.org/blog/2020/08/ipython-reproducible-builds)
- [pypa/wheel issue #362 — file permissions reproducibility](https://github.com/pypa/wheel/issues/362)
