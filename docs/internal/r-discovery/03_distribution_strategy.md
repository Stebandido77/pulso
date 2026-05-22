# Phase 3 — Distribution Strategy

**Question:** How do we ship `pulso` (R) given that the bundled `dane_codebook.json` is **6.6 MB**, larger than CRAN's de facto 5 MB total package limit?
**Status:** Recommendation made; awaits human approval. **This is the most consequential infrastructure decision** of the R port.

---

## TL;DR

**Recommendation: Option A (runtime download via `piggyback` from GitHub Releases) with a small bundled fallback subset.**

- **Phase 1 (initial release, GitHub-only):** Bundle the full 6.6 MB codebook in `inst/extdata/` to keep development simple. Don't submit to CRAN yet.
- **Phase 2 (CRAN submission, ~6 months later):** Switch to runtime download of the full codebook via `piggyback` from a GitHub Release asset. Bundle a *small* subset (~500 KB, top ~150 most-used variables) in `inst/extdata/` so the package is useful offline on first call without download.
- **Reject Option C (reticulate):** Violates the "pure R, no Python dep" constraint.
- **Reject Option D (subset only):** Loses the core value of the metadata feature.
- **Option B (gzip in inst/):** Keep as backup if A turns out infeasible. Likely OK on size but locks the codebook to release cadence.

---

## The numerical reality

Current artifacts under `pulso/data/`:

| File | Size | Notes |
|---|---|---|
| `dane_codebook.json` | **6.6 MB** | The blocker. 1153 vars × 19 years. |
| `sources.json` | 300 KB | Fine. |
| `variable_map.json` | 37 KB | Fine. |
| `_scraped_catalog.json` | 111 KB | Internal/scraping; not user-facing. |
| `epochs.json` | 3.1 KB | Fine. |
| `empalme_sources.json` | 5.9 KB | Fine. |
| `variable_module_map.json` | 2.3 KB | Fine. |

Total user-facing data needed at runtime: **~7 MB raw**.

Gzip estimates (JSON typically compresses 8–12×):

- `dane_codebook.json` raw 6.6 MB → gzipped ~600–900 KB
- All other files combined: ~50 KB gzipped

So the **gzipped codebook would fit under CRAN's 5 MB limit comfortably** (Option B would technically work). But the cost is awkward decompression on every read and lock-in to package release cadence for any DANE update.

---

## CRAN policy as we know it

From [CRAN Repository Policy](https://cran.r-project.org/web/packages/policies.html):

- **Neither data nor documentation should exceed 5 MB.**
- Source tarballs **should not exceed 10 MB** (more can be requested at submission for third-party source code).
- Where large data is required, **separate data-only package** is the suggested pattern.
- Exemptions are **rarely granted**; CRAN team has publicly stated they have <10 large packages historically and don't accept new ones.

[Posit Community thread](https://forum.posit.co/t/data-size-limits-for-packages/3748): confirms exemption requests are routinely denied even for legitimate reference data.

[The Coatless Professor write-up](https://thecoatlessprofessor.com/programming/r/size-and-limitations-of-packages-on-cran/): the 5 MB applies to **the installed package** size on disk, not the source tarball. Compressed inst/extdata helps.

**Practical take:** Don't fight CRAN policy. Either compress aggressively, split into a data-only package, or download at runtime.

---

## The four options, fully evaluated

### Option A — Runtime download via `piggyback` (RECOMMENDED)

**Mechanism:** Host `dane_codebook.json` (and `dane_codebook.json.gz`) as assets attached to a versioned GitHub Release (e.g., `data-v1.0.0`). `pulso` (R) calls a function on first need that downloads, validates checksum, caches under `tools::R_user_dir("pulso", which = "cache")`, and reads from cache thereafter.

**Library:** [`piggyback`](https://cran.r-project.org/package=piggyback) by rOpenSci. Stable, on CRAN, supports public repos without auth, handles up to 2 GB per file.

**Pros:**
- ✅ CRAN-compatible — package itself stays well under 5 MB.
- ✅ Codebook can be updated independently of package releases (just push a new GitHub Release).
- ✅ Same data file shared by Python (which already bundles it) and R port — single source of truth in `shared/dane_codebook.json` of the monorepo.
- ✅ Caching is automatic + idempotent — second call is instant.
- ✅ Public repos need no auth; no API key for users.
- ✅ Pattern is well-established (used by `tidycensus`, `eurostat`, many others — see Phase 1 report).

**Cons:**
- ⚠️ First-call requires internet. Must handle gracefully (clear error, point to manual download instructions in docs).
- ⚠️ Adds `piggyback` (or alternative HTTP client) as a hard dep. `piggyback` itself depends on `httr2`, `jsonlite`, `gh`, `lubridate`, `fs`, `cli` — all small.
- ⚠️ Possible to mitigate by writing our own minimal downloader in `httr2` (which we'd already have as dep) and skip `piggyback`. ~80 lines of code. **Recommended sub-choice.**
- ⚠️ Need a GitHub Release asset workflow (one-time setup; we already use Releases).
- ⚠️ Corporate users behind a proxy may have download issues. Doc the env vars (`https_proxy`, etc.).

**Sub-decision A.1: Use `piggyback` or roll our own?**

`piggyback` adds 6 transitive deps. Our own 80-line `httr2`-based downloader (`pulso_download_codebook()`) avoids them. **Roll our own** — it's not complex. Pattern:

```r
# pseudo-code, not real R
pulso_codebook_path <- function() {
  cache_dir <- tools::R_user_dir("pulso", which = "cache")
  file <- file.path(cache_dir, "dane_codebook.json.gz")
  if (!file.exists(file)) {
    url <- "https://github.com/Stebandido77/pulso/releases/download/data-v1.0.0/dane_codebook.json.gz"
    expected_sha <- "abc123..."  # bundled in package as constant
    download_with_checksum(url, file, expected_sha)
  }
  file
}
```

### Option B — Ship gzipped in `inst/extdata/`

**Mechanism:** Compress the codebook to ~700 KB and ship inside the package.

**Pros:**
- ✅ No internet on first use.
- ✅ Simpler: no download logic, no GitHub Release coordination.
- ✅ Atomic with package version (no codebook/code skew).

**Cons:**
- ⚠️ Codebook updates require a full package release. DANE publishes new GEIH variables periodically — every release becomes a DANE-tracking release.
- ⚠️ Locks the user to whatever codebook shipped with their installed `pulso` version. A user on `pulso 1.0.0` has the May-2026 codebook forever unless they upgrade.
- ⚠️ Source tarball grows by ~700 KB; not a hard CRAN problem but trends in the wrong direction.
- ⚠️ Decompression on every load (or once into memory). `jsonlite::fromJSON(gzfile(...))` is fine but slower than reading already-decompressed.

**When this becomes the right choice:** If `piggyback`/runtime-download is rejected for offline-first reasons (e.g., target audience is in air-gapped policy shops). Or as Phase 1 of the rollout (see hybrid below).

### Option C — `reticulate` (REJECTED)

**Mechanism:** `pulso` (R) calls into the Python `pulso-co` package via `reticulate`, getting the codebook as a side effect.

**Reasons to reject:**
- ❌ **Hard violation** of the user's stated constraint that the R port must be pure R, no Python dep.
- ❌ Doubles the install burden: users need both R and Python+pulso-co.
- ❌ Breaks for users who don't have Python (a meaningful share of pure-R researchers).
- ❌ `reticulate`-wrapped objects are awkward (Python dicts vs R lists, NaN/None handling).
- ❌ Couples R release to Python release.

`reticulate` is great for thin wrappers around fundamentally Python projects (e.g., `keras` for R). For `pulso`, where the goal is parity in R, it's the wrong tool.

### Option D — Subset codebook only

**Mechanism:** Ship only the most-frequently-queried variables (~150 of 1153 ≈ 13%), drop the rest.

**Reasons to reject:**
- ❌ **Defeats the point of the metadata feature.** The whole 1.0.0 release was about giving users codebook access *for any DANE variable*, including the long tail.
- ❌ Skeletal-variable detection logic (Python `_is_skeletal`) was built explicitly to surface the gap so users can request enrichment. Subset shipping would silently hide variables that *do* have metadata.
- ❌ Decision of "which 150" is contentious and political (whose variables are 'top'?). DANE technicians, econ researchers, and health researchers care about different subsets.

**As a fallback subset bundled in inst/extdata/** (when combined with Option A), it's useful for offline-first first-call. That's the only role for it.

---

## The recommended hybrid

**Architecture:**

```
pulso (R) installed package
├── inst/extdata/
│   ├── codebook_subset.json    (~500 KB, top ~150 vars, gzipped)
│   ├── codebook_subset.sha256  (integrity check)
│   ├── sources.json            (~300 KB)
│   ├── variable_map.json       (~37 KB)
│   ├── epochs.json             (~3 KB)
│   └── codebook_release_url.txt  (URL of full codebook on GitHub Release)
└── R/
    └── codebook.R              (loader: subset first, full on demand)
```

**User flow:**

1. `pulso_load(metadata = TRUE)` for a top-150 variable → reads from bundled subset, no network.
2. `pulso_load(metadata = TRUE)` for a long-tail variable → bundled subset doesn't have it → loader auto-fetches full codebook from GitHub Release, caches in `tools::R_user_dir("pulso", "cache")`, reads from cache.
3. Subsequent calls hit the cache.
4. `pulso_codebook_refresh()` (public function) re-downloads if user wants the latest.
5. `pulso_codebook_offline()` (env var or option) disables network entirely; long-tail vars return a clear error pointing to manual download.

**Estimated installed size:** ~1.2 MB. Well under CRAN limit. Source tarball ~1.5 MB.

**Why this is the right shape:**
- Optimizes for the *common* case (top variables) — no network, fast.
- Doesn't bloat the package with the long tail.
- Long-tail availability is preserved without DANE-tracking releases.
- Codebook updates ship via GitHub Release (separate cadence from R package).
- Same `dane_codebook.json` file used by Python — one source of truth in `shared/`.

---

## Phasing

Given there's no urgency for CRAN, the cleanest rollout is:

**Phase 1 (R port v0.1.0 → v0.5.0, GitHub-only):**
- Bundle full 6.6 MB codebook in `inst/extdata/` (Option B for simplicity).
- Distribute via `remotes::install_github("Stebandido77/pulso", subdir = "r")`.
- Get API stable, get user feedback, iterate fast.
- Source tarball is bigger but no one is downloading from CRAN yet.

**Phase 2 (R port v1.0.0, CRAN submission):**
- Switch to hybrid (Option A + bundled subset).
- Wire up GitHub Release asset workflow.
- Submit to CRAN.

This deferral is important: **don't engineer for CRAN before the API is stable.** Re-architecting the codebook loader is cheaper than re-architecting public API.

---

## Specific implementation notes

### Where the codebook lives in the monorepo

```
shared/
├── dane_codebook.json           (canonical, used by Python + R)
├── dane_codebook.json.gz        (built artifact for R distribution)
├── sources.json
└── variable_map.json
```

Build script (`scripts/build_r_package.R` or in CI):
1. Read `shared/dane_codebook.json`
2. Generate `r/inst/extdata/codebook_subset.json.gz` (top-150 vars, gzipped)
3. Compute SHA256 of full codebook → embed in `r/R/sysdata.rda` as `PULSO_CODEBOOK_SHA256`
4. Upload `dane_codebook.json.gz` to GitHub Release `data-v{N}` on tag

### Caching directory

Use `tools::R_user_dir("pulso", which = "cache")` (R 4.0+, native, no external dep).
Mirrors Python's use of `platformdirs`.

| OS | Path |
|---|---|
| Linux | `~/.cache/R/pulso/` |
| macOS | `~/Library/Caches/org.R-project.R/R/pulso/` |
| Windows | `%LOCALAPPDATA%/R/cache/R/pulso/` |

### Integrity & versioning

- Bundle a `codebook_release_url.txt` (or constant in `R/sysdata.rda`) that points at exactly one GitHub Release asset URL.
- Bundle the expected SHA256 of that file as a constant.
- Downloader verifies SHA256 after download. Mismatch → delete + raise.
- Codebook URL changes = new package version (forces explicit upgrade if data schema changes).

### Tests

- Unit tests on subset loading (no network needed).
- Integration tests on full-codebook download (gated behind `Sys.getenv("PULSO_RUN_NETWORK_TESTS")` like Python's `--run-integration`).
- VCR-based mocks for download failures.

### Failure modes to handle

| Failure | Response |
|---|---|
| No internet | Clear `cli::cli_abort()` with manual download instructions. |
| GitHub rate-limited | Retry once with backoff, then abort with rate-limit message. |
| SHA256 mismatch | Delete cache, abort, suggest `pulso_codebook_refresh()`. |
| Disk full in cache dir | Abort with cache-dir path so user can clear. |
| Corporate proxy | Document `httr2::with_proxy()` usage in vignette. |

---

## Decision required from human

**Q3 — Codebook distribution: A (runtime download) / B (gzipped bundled) / Hybrid / D (subset)?**

Recommendation: **Hybrid (Option A + bundled subset), phased.**

- **Phase 1 release (GitHub-only):** Option B — bundle full codebook gzipped (~700 KB). Get to working R port fast.
- **Phase 2 release (CRAN-targeting):** Hybrid — small subset bundled, full codebook auto-downloaded on demand from GitHub Release.

**If the human prefers a single approach** (no phasing): go straight to **Hybrid**. Slightly more upfront engineering but no rework later.

**If the human prefers maximum simplicity:** **Option B** alone, defer CRAN indefinitely. ~700 KB gzipped fits comfortably even in 5 MB CRAN limit; the only cost is codebook updates require package releases.

---

## Sources

- [CRAN Repository Policy](https://cran.r-project.org/web/packages/policies.html)
- [piggyback CRAN](https://cran.r-project.org/package=piggyback)
- [piggyback intro vignette](https://cran.r-project.org/web/packages/piggyback/vignettes/intro.html)
- [How to distribute data with your R package — R-hub blog](https://blog.r-hub.io/2020/05/29/distribute-data/)
- [Size and limitations of packages on CRAN — The Coatless Professor](https://thecoatlessprofessor.com/programming/r/size-and-limitations-of-packages-on-cran/)
- [pkgfilecache vignette](https://cran.r-project.org/web/packages/pkgfilecache/vignettes/pkgfilecache.html)
- [R Packages 2e — Chapter 7 Data](https://r-pkgs.org/data.html)
