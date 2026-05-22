# R Library Discovery — Analogues for `pulso-r`

Research date: 2026-05-08. Pure desk research; no code installed.

This file surveys eight R packages whose problem space overlaps with `pulso-co` (Colombia DANE GEIH microdata loader, just shipped to PyPI as `pulso-co` v1.0.0). The goal is to anchor an eventual `pulso-r` port in established R conventions rather than transliterating the Python API.

---

## 1. Executive summary

- **Tibble + tidyverse-style snake_case is the dominant paradigm** for any post-2018 statistical-data package targeting researchers. Only `WDI` and (the now archived/legacy) `imfr` still return base `data.frame`. Even older packages (`surveydata`, `OECD`) have drifted toward dplyr-style verbs.
- **Two metadata models compete:** (a) `haven::labelled` value labels stored on each column (`ipumsr` is the gold standard, leveraged via DDI XML codebooks) and (b) attribute-on-data.frame (`surveydata` keeps question text in `variable.labels`, an SPSS-export holdover). For GEIH, model (a) is the natural fit because the codebook has *value labels per variable*.
- **Caching is uniformly disk-based and uniformly opt-in or default-on.** `tidycensus`, `eurostat`, and `wbstats` all use `rappdirs::user_cache_dir()` (or a `tempdir()` fallback) with helper functions to set/clear. None use `tools::R_user_dir()` consistently — `rappdirs` predates it and has stuck.
- **Nobody ships >5 MB of bundled data inside the package.** The CRAN policy (https://cran.r-project.org/web/packages/policies.html) says "neither code nor data > 5 MB." The standard pattern is *download on demand into a user cache*, e.g. `pkgfilecache` (https://cran.r-project.org/web/packages/pkgfilecache/vignettes/pkgfilecache.html). Pulso's 6.6 MB codebook JSON cannot be embedded — it must be hosted (GitHub release asset, OSF, or a `pulso.codebook` data-only sister package) and fetched lazily.
- **Dependency budgets vary by 10x.** `WDI` imports only `jsonlite`; `eurostat` imports 19 packages. The lean end (`WDI`, `imfr`, `imf.data`) is more CRAN-friendly; the heavy end (`tidycensus`, `eurostat`) trades dependency weight for tidyverse ergonomics. `pulso-r` should sit in the middle.

---

## 2. Library-by-library

### 2.1 tidycensus — US Census Bureau

- **Repo / docs:** https://github.com/walkerke/tidycensus, https://walker-data.com/tidycensus/
- **CRAN:** https://cran.r-project.org/package=tidycensus
- **Version / release:** 1.7.5, released 2026-02-09. Active.
- **Paradigm:** Tidyverse, snake_case (`get_acs`, `get_decennial`, `load_variables`). Returns tibbles.
- **Return type:** Tibble; optional `geometry = TRUE` returns an `sf` object (list-column for spatial).
- **Metadata handling:** Variables themselves carry no haven labels. Instead, `load_variables(year, dataset)` returns a tibble of variable codes + descriptions which the analyst joins manually. Investigator-friendly but requires a separate lookup step.
- **Caching:** On-disk via `rappdirs`. `load_variables(..., cache = TRUE)` and `get_acs(..., cache_table = TRUE)` write to `rappdirs::user_cache_dir("tidycensus")`. Opt-in.
- **Auth:** `census_api_key(key, install = TRUE)` writes `CENSUS_API_KEY` to `~/.Renviron`. Standard idiom.
- **Imports (~17):** httr, sf, dplyr (>=1.0.0), tigris, stringr, jsonlite, purrr, rvest, tidyr, rappdirs, readr, xml2, units, utils, rlang, crayon, tidyselect. Heavy because of geospatial.
- **Distribution:** CRAN + GitHub (dev).
- **Bundled data:** None large; variable lookup tables are scraped on demand, then cached.
- **Docs quality:** Excellent. Kyle Walker's *Analyzing US Census Data* book (https://walker-data.com/census-r/) doubles as an extended vignette.

### 2.2 ipumsr — IPUMS international microdata

- **Repo / docs:** https://github.com/ipums/ipumsr, https://tech.popdata.org/ipumsr/
- **CRAN:** https://cran.r-project.org/package=ipumsr
- **Version / release:** 0.10.x, latest published 2026-03-13. 0.9.0 added IPUMS API extract building.
- **Paradigm:** Tidyverse, snake_case (`read_ipums_micro`, `read_ipums_ddi`, `define_extract_micro`). Returns tibbles.
- **Return type:** Tibble of microdata; metadata as a separate `ipums_ddi` S3 object.
- **Metadata handling:** **The model `pulso-r` should imitate.** DDI XML codebooks are parsed by `read_ipums_ddi()` into an `ipums_ddi` object containing variable names, descriptions, and value-label maps. The microdata tibble is then read with each column wrapped in `haven::labelled` (numeric storage + `labels` attribute mapping codes to text). See https://tech.popdata.org/ipumsr/reference/read_ipums_ddi.html. Helper accessors: `ipums_var_label()`, `ipums_val_labels()`, `lbl_clean()`, `as_factor()`.
- **Caching:** Downloaded extracts go where the user tells them; no global cache. The package treats data files as user-owned artifacts (downloaded once via API, kept on disk).
- **Auth:** `set_ipums_api_key(key, save = TRUE)` writes to `.Renviron`. Same idiom as tidycensus.
- **Imports (~14):** dplyr, haven (>=2.2.0), hipread (>=0.2.0), httr, jsonlite, lifecycle, purrr, R6, readr, rlang, tibble, tidyselect, xml2, zeallot. `hipread` is an IPUMS-maintained fork of `readr` for hierarchical fixed-width files.
- **Distribution:** CRAN + GitHub. Maintained by IPUMS staff.
- **Bundled data:** Minimal. Sample DDI fixtures in `inst/extdata` only.
- **Docs quality:** First-rate. Multi-vignette structure: `ipums.Rmd`, `ipums-read.Rmd`, `ipums-api.Rmd`. https://tech.popdata.org/ipumsr/

### 2.3 surveydata — SPSS-style attribute-based metadata

- **Repo / docs:** https://github.com/andrie/surveydata, https://andrie.github.io/surveydata/
- **CRAN:** https://cran.r-project.org/package=surveydata
- **Version / release:** 0.2.8, 2026-01-17 (0.2.7 in mid-2025). Slow-moving but maintained.
- **Paradigm:** Hybrid. Older base R bones (S3 class), but recent versions adopted dplyr/tidyr verbs.
- **Return type:** S3 class `surveydata` extending `data.frame`. Subset operators preserve the class (and metadata) — that's the package's whole reason to exist.
- **Metadata handling:** **Attribute-on-data.frame model.** Question text lives in `attr(df, "variable.labels")` (the same attribute `foreign::read.spss()` writes). Sub-question separators live in `attr(df, "patterns")`. Survives `[` and `[[`.
- **Caching:** None — purely an in-memory utility class.
- **Auth:** N/A.
- **Imports (~9):** dplyr, rlang, magrittr, purrr, ggplot2, scales, tidyr, DT, assertthat. Light.
- **Distribution:** CRAN + GitHub.
- **Bundled data:** Tiny example survey only.
- **Docs quality:** Decent vignette; package is niche so user base is smaller.

### 2.4 eurostat — Eurostat statistics

- **Repo / docs:** https://github.com/rOpenGov/eurostat, https://ropengov.github.io/eurostat/
- **CRAN:** https://cran.r-project.org/package=eurostat
- **Version / release:** 4.0.0 in 2023 (full rewrite to the new dissemination API). Current line in 4.x as of mid-2025.
- **Paradigm:** Tidyverse, snake_case (`get_eurostat`, `get_eurostat_dic`, `get_eurostat_toc`, `label_eurostat`, `search_eurostat`, `set_eurostat_cache_dir`, `clean_eurostat_cache`).
- **Return type:** Tibble.
- **Metadata handling:** Code-to-label dictionaries are *separate* tibbles fetched via `get_eurostat_dic()`. `label_eurostat()` joins labels onto the data tibble at user request — it does NOT use `haven::labelled`. This is the "join when you want it" model.
- **Caching:** Default-on. Files written under `tempdir()` by default; `set_eurostat_cache_dir()` persists a path; `clean_eurostat_cache()` clears. Compression toggleable.
- **Auth:** No key required (Eurostat API is open).
- **Imports (~19):** classInt, countrycode, curl, digest, dplyr, httr2 (>=0.2.3), ISOweek, jsonlite, lubridate, rappdirs, readr, RefManageR, regions, rlang, stringi, stringr, tibble, tidyr, xml2, data.table. Heavy — note `httr2` (modern) over `httr` (legacy).
- **Distribution:** CRAN + rOpenGov GitHub org.
- **Bundled data:** Some bundled country code lookups, all small.
- **Docs quality:** Very good. Has a JSS-style methods paper (Lahti et al.) and a tutorial vignette.

### 2.5 wbstats — World Bank API (modern client)

- **Repo / docs:** https://github.com/gshs-ornl/wbstats, https://gshs-ornl.github.io/wbstats/
- **CRAN:** https://cran.r-project.org/package=wbstats
- **Version / release:** 1.0.x line. Periodic maintenance; under transfer (gshs-ornl → pachadotdev fork).
- **Paradigm:** Tidyverse, snake_case (`wb_data`, `wb_search`, `wb_cache`, `wb_indicators`).
- **Return type:** Tibble (wide by default, `return_wide = FALSE` for long).
- **Metadata handling:** A single object `wb_cachelist` (a list of 8 tibbles: countries, indicators, sources, topics, regions, income_levels, lending_types, languages) acts as the in-memory metadata catalog. Refreshed via `wb_cache()`.
- **Caching:** `wb_cache()` returns a fresh catalog; analyst chooses to assign it. The bundled `wb_cachelist` ships as package data (small, English only). For other languages, refetch.
- **Auth:** None.
- **Imports (small ~7):** httr, jsonlite, dplyr, tibble, purrr, lubridate (and a few others).
- **Distribution:** CRAN + GitHub.
- **Bundled data:** **Yes — `wb_cachelist` is bundled.** Compressed it fits within the 5 MB limit because it's tibbles of metadata, not raw data.
- **Docs quality:** Good vignette, clean function reference.

### 2.6 OECD — search & extract OECD data

- **Repo / docs:** https://github.com/expersso/OECD
- **CRAN:** https://cran.r-project.org/package=OECD
- **Version / release:** 0.2.5, 2021-12-01 (last). Author Eric Persson; maintenance has slowed. The community has partly migrated to `rsdmx` (https://github.com/eblondel/rsdmx) for direct SDMX access.
- **Paradigm:** Mostly base R idioms, dot.case names mixed with snake_case (`get_dataset`, `search_dataset`, `get_data_structure`).
- **Return type:** `data.frame`.
- **Metadata handling:** `get_data_structure()` returns a *list of data.frames* (one per dimension) — closer to SDMX DSD semantics. No haven labels.
- **Caching:** None built in.
- **Auth:** No key.
- **Imports (~5):** xml2, rsdmx, readr, stringr, jsonlite. Lean.
- **Distribution:** CRAN + GitHub. Effectively in maintenance mode.
- **Bundled data:** None significant.
- **Docs quality:** Brief README; functional but not lavish.

### 2.7 imfr — IMF Data API (legacy)

- **Repo / docs:** https://github.com/christophergandrud/imfr
- **CRAN:** https://cran.r-project.org/package=imfr (mirror: https://github.com/cran/imfr)
- **Version / release:** 0.1.9.1 (Gandrud) / v2 rewrite by C.C. Smith. The IMF API itself broke/changed and the package's reliability has wobbled — community has partly moved to **`imf.data`** (https://cran.r-project.org/package=imf.data, published 2024-09-14).
- **Paradigm:** Tidyverse-leaning, snake_case (`imf_databases`, `imf_parameters`, `imf_dataset`, `imf_parameter_defs`).
- **Return type:** Tibble in v2.
- **Metadata handling:** `imf_parameters()` and `imf_parameter_defs()` return tibbles describing dimensions; analyst assembles a query.
- **Caching:** Lightweight in-memory; rate-limited via `ratelimitr`.
- **Auth:** None.
- **Imports (~7):** dplyr, httr (>=1.2.0), jsonlite, methods, purrr, ratelimitr, tidyr.
- **Distribution:** CRAN + GitHub. Status: tenuous; consider `imf.data` as the going-forward analogue.
- **Bundled data:** None.
- **Docs quality:** Decent README, smaller doc surface than tidycensus or ipumsr.

### 2.8 WDI — World Development Indicators (the original)

- **Repo / docs:** https://github.com/vincentarelbundock/WDI
- **CRAN:** https://cran.r-project.org/package=WDI
- **Version / release:** 2.7.x (CRAN page lists 2.7.10 with R >= 3.5.0). Stable, slow-moving, maintained by Vincent Arel-Bundock.
- **Paradigm:** Base R. Function names are `WDI`, `WDIsearch`, `WDIcache`, `WDIbulk` — camel/Pascal-ish, *not* snake_case. Predates tidyverse conventions.
- **Return type:** `data.frame`, wide format (countries × years × indicators). No tibble.
- **Metadata handling:** `WDIcache()` returns a list with `series` and `country` data.frames (indicator catalog + country dimension). No haven labels.
- **Caching:** `WDIcache()` builds a fresh in-memory cache on demand; the `cache` arg of `WDI()` accepts a previously computed cache. No on-disk persistence.
- **Auth:** None.
- **Imports (1!):** **`jsonlite` only.** Suggests altdoc, curl, testthat, tidyr. The leanest CRAN dependency footprint of any package on this list.
- **Distribution:** CRAN + GitHub.
- **Bundled data:** None.
- **Docs quality:** Compact README; no big vignette. Investigator-friendly because it's tiny and obvious.

---

## 3. Cross-cutting patterns

| Library      | Style          | Returns        | Metadata model                           | Caching                                  | Auth      | Deps  | Distribution |
|--------------|----------------|----------------|------------------------------------------|------------------------------------------|-----------|-------|--------------|
| tidycensus   | tidyverse      | tibble (+ sf)  | separate `load_variables()` tibble       | `rappdirs` on-disk, opt-in               | API key   | ~17   | CRAN+GH      |
| ipumsr       | tidyverse      | tibble + DDI   | `haven::labelled` driven by DDI XML      | user-managed extract files               | API key   | ~14   | CRAN+GH      |
| surveydata   | hybrid (S3)    | surveydata DF  | `attr(df, "variable.labels")` (SPSS)     | none                                     | n/a       | ~9    | CRAN+GH      |
| eurostat     | tidyverse      | tibble         | separate dictionary tibbles + `label_*`  | `rappdirs`/tempdir default-on            | none      | ~19   | CRAN+GH      |
| wbstats      | tidyverse      | tibble         | bundled `wb_cachelist` of tibbles        | bundled snapshot + `wb_cache()` refresh  | none      | ~7    | CRAN+GH      |
| OECD         | base-ish       | data.frame     | `get_data_structure()` list-of-df        | none                                     | none      | ~5    | CRAN+GH      |
| imfr         | tidyverse-ish  | tibble         | `imf_parameters` tibbles                 | rate-limit, no disk                      | none      | ~7    | CRAN+GH (shaky) |
| WDI          | base R         | data.frame     | `WDIcache()` list                        | in-memory only                           | none      | 1     | CRAN+GH      |

Sub-patterns worth highlighting:

- **API key idiom is uniform**: `<pkg>_api_key(key, install = TRUE)` writing `<PKG>_API_KEY` to `~/.Renviron`. Used identically by `tidycensus` and `ipumsr`. If `pulso-r` ever needs auth (for a pulso-cloud sister service, say), this is the pattern.
- **`rappdirs::user_cache_dir()` is the de-facto cache root** in 2026, despite `tools::R_user_dir()` being newer/nominally preferred. `tidycensus` and `eurostat` both use `rappdirs`. `pulso-r` should follow whichever the maintainers prefer; don't fight the ecosystem.
- **Variable-label storage splits the field cleanly:** ipumsr (haven::labelled per column) vs. eurostat/wbstats/tidycensus (separate metadata tibble, joined on demand). The DDI-XML + haven::labelled route is more "rich object" but heavier; the join-on-demand route is more transparent and dplyr-native.

---

## 4. Lessons for `pulso-r`

1. **Adopt tidyverse conventions wholesale.** Snake_case, tibble returns, `%>%`/`|>` friendly. Every actively maintained CRAN analogue from 2020 onward is tidyverse-shaped. Going base-R would isolate users.
2. **Imitate ipumsr's metadata model.** GEIH's codebook (variable labels + value-label maps per variable) maps perfectly onto `haven::labelled`. A `pulso_codebook` S3 object (analogous to `ipums_ddi`) holding the parsed codebook, plus `read_geih(...)` returning a tibble with each column wrapped in `haven::labelled`, is the cleanest path. Provide `as_factor()` and `as.numeric()` escape hatches per haven idioms.
3. **Do not bundle the 6.6 MB codebook in the package.** CRAN policy is strict at 5 MB total (https://cran.r-project.org/web/packages/policies.html). Three viable options:
   - (a) **Sister data package** `pulso.codebook` released with longer cadence; main `pulso` Imports it. Acceptable if the codebook is itself > 5 MB after compression. (Test: `xz` compression of the JSON should already shrink it considerably; check.)
   - (b) **Lazy download into `rappdirs::user_cache_dir("pulso")`** on first use, with a checksum to detect updates. Pattern documented by `pkgfilecache` (https://cran.r-project.org/web/packages/pkgfilecache/vignettes/pkgfilecache.html). Requires a stable hosting URL — GitHub release asset is fine.
   - (c) **Hybrid**: ship a tiny "manifest + minimal labels" inside the package; lazy-fetch the full codebook for users who need rich metadata.
   Option (b) is the strongest for v1 — minimal CRAN friction, mirrors how `tidycensus` handles variable lookups.
4. **Cache strategy:** `rappdirs::user_cache_dir("pulso")` for both the codebook fetch (per #3) and any downloaded GEIH microdata files. Provide `pulso_cache_dir()`, `pulso_clear_cache()` helpers — the eurostat trio of `set_eurostat_cache_dir / clean_eurostat_cache` is a good template.
5. **Keep the dependency footprint moderate.** Aim for ~10 imports: `tibble`, `dplyr`, `tidyr`, `haven`, `readr` (or `vroom` if performance demands), `rlang`, `cli`, `jsonlite`, `xml2` (for any DDI-style codebook XML), `rappdirs`. Skip `httr2` unless network calls are needed; if so, `httr2` over `httr` (eurostat 4.0.0 already migrated).
6. **Documentation: emulate ipumsr.** Multi-vignette: `pulso.Rmd` (overview), `pulso-read.Rmd` (reading microdata + label semantics), `pulso-codebook.Rmd` (querying the codebook). The pkgdown site should host the vignettes plus a function reference. Investigator-friendly README is mandatory; tidycensus's README is a strong template.
7. **Distribution: CRAN + GitHub from day one.** The CRAN release legitimizes the package for academic users (citations, reproducibility). GitHub-only would limit adoption; surveydata, OECD and even archived imfr show that maintainers without a CRAN presence end up forked and re-uploaded by third parties (`pachadotdev/wbstats`, `cran/imfr` mirror).
8. **Don't replicate Python pulso's API verbatim.** A pure transliteration would feel un-R. Map `pulso.load_geih(year=2023)` to `read_geih(year = 2023)` returning a `haven::labelled` tibble; map a `pulso.Codebook` class to a `pulso_codebook` S3 with print/summary methods and accessor helpers `pulso_var_label()`, `pulso_val_labels()` (mirroring ipumsr).
9. **Plan for the IMF/imfr trap.** That ecosystem fragmented when the maintainer disengaged and the API changed. Lessons: keep the API client surface small, isolate it behind one or two internal functions, and pin behavior to a stable codebook version so a DANE format change doesn't brick the package overnight.

---

Sources (deep-dive URLs cited above): https://github.com/walkerke/tidycensus, https://walker-data.com/tidycensus/, https://github.com/ipums/ipumsr, https://tech.popdata.org/ipumsr/, https://github.com/andrie/surveydata, https://github.com/rOpenGov/eurostat, https://ropengov.github.io/eurostat/, https://github.com/gshs-ornl/wbstats, https://gshs-ornl.github.io/wbstats/, https://github.com/expersso/OECD, https://github.com/christophergandrud/imfr, https://cran.r-project.org/package=imf.data, https://github.com/vincentarelbundock/WDI, https://cran.r-project.org/web/packages/policies.html, https://cran.r-project.org/web/packages/pkgfilecache/vignettes/pkgfilecache.html.
