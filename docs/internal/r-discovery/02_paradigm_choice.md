# Phase 2 — Tidyverse vs Base R

**Question:** Which R paradigm should `pulso` (R port) follow — tidyverse, base R, or hybrid?
**Status:** Recommendation made; awaits human approval.
**Audience for the R port:** Colombian economists, academic researchers, public-health investigators, DANE technicians, undergrad/grad students. Same profile as the Python users plus a tail of R-leaning health/social-policy researchers.

---

## TL;DR

**Recommendation: tidyverse-flavored, but with a *minimal-dependency tidyverse* footprint.**

- Public functions return **tibbles** (S3 class extending `data.frame`, so base-R indexing keeps working).
- Function names follow **snake_case with `pulso_` prefix** (`pulso_load`, `pulso_describe_column`).
- Hard dependencies: `tibble`, `vctrs`, `rlang`, `cli`, `httr2`, `jsonlite`, `haven` (for `labelled`). Avoid hard-depping `dplyr`/`tidyr`/`ggplot2`.
- All public functions accept a `data.frame` for input where they currently take a tibble — no `tibble::is_tibble()` gates that would surprise base-R users.
- `magrittr` `%>%` is **not** a dep; users can pipe with `|>` (R 4.1+) or `%>%` from any source.

This gives us the affordances of tidyverse (clear printing, factors-as-labels, dplyr-friendly) without the "you must drink the whole Kool-Aid" cost.

---

## What's actually at stake

The choice is not binary. Three sub-decisions hide inside "tidyverse vs base":

1. **Return type** — `data.frame` vs `tibble` vs S3/S4 wrapper.
2. **Naming** — `pulso_load()` (snake) vs `pulsoLoad()` (camel) vs `pulso::load()` (terse namespaced).
3. **Dependency footprint** — none/lean/full tidyverse rdeps in `Imports`.

Each sub-decision can be made independently. The "hybrid" sweet spot is: tidyverse style on (1) and (2), lean on (3).

---

## User profile reality check

The Python `pulso` user profile is:

- Economists & academic researchers in Colombian universities (Andes, Externado, Nacional, Javeriana, Rosario)
- Mercado laboral specialists, public-policy analysts
- Undergrad/grad students writing theses on GEIH
- DANE internal technicians (small but high-credibility audience)

The R-leaning subset (which is the *target* of the port):

- Public-health researchers (R is dominant in epi/biostat)
- Quantitative sociologists
- Survey methodologists (very tidyverse-aligned via `survey`, `srvyr`, `srvyr` ⊂ tidyverse)
- A subset of econ folks who teach R (smaller in Colombia than Stata teachers, but growing)

**Empirical reality:** Colombian econ academia teaches Stata first, R second, Python third. Among R users in this niche, the *de facto* learning path goes through RStudio + `tidyverse`. Posit's R for Data Science and the Spanish translation (`R4DS-es`) are the dominant reference. Survey-data users specifically lean on `survey`/`srvyr` and `haven`.

**Implication:** New R users in this audience will *expect* tidyverse-style output. They will be surprised by row.names, by silent `factor` conversion of strings, by `data.frame` printing dumping 70k rows to console. Tibbles fix all of these by default.

---

## Tidyverse pros for `pulso`-R

| Pro | Why it matters here |
|---|---|
| **Tibble printing** truncates 70k rows of GEIH microdata into 10 lines + column types. | Default `data.frame` prints would drown a console. |
| **`haven::labelled`** stores DANE variable labels and value labels alongside the data. | `pulso` already has 1153 variables × value-label maps. `labelled()` is the canonical R representation. ipumsr, srvyr, and SPSS users all expect this. |
| **`srvyr` integration** lets users pipe survey-weighted estimators directly. | GEIH ships expansion factors (`fex_c_2011`). Users will weight everything. `srvyr` works on tibbles via `as_survey_design()`. |
| **Imperative verbs + snake_case** match Python's `pulso.load`. | Lower cognitive cost when porting analysis scripts. |
| **`cli` for messages** gives consistent UI (warnings, errors, status). | Python uses logging + UserWarning. `cli` is the modern equivalent and is used by tidyverse, devtools, etc. |
| **`vctrs`-based class system** lets us keep `labelled` columns through subsetting. | Without `vctrs`, custom classes drop on `df[, "col"]`. |

## Tidyverse cons for `pulso`-R

| Con | Mitigation |
|---|---|
| `dplyr`/`tidyr` are heavy — `dplyr` alone pulls 10+ recursive deps. | Don't depend on them. Use `tibble`, `vctrs`, `rlang` only. Suggest dplyr in `Suggests`. |
| Tibbles surprise hard-base-R users who expect `df$col[, drop=TRUE]` semantics. | Tibbles inherit from `data.frame`, so `df[["col"]]` works. Document in vignette. |
| Tidyverse style guide ≠ CRAN style guide; some CRAN reviewers prefer base. | snake_case is overwhelmingly common on CRAN now. Not a real risk. |
| `haven_labelled` columns can confuse users who do `mean(df$col)`. | Document the `unlabelled()`/`zap_labels()` escape hatch in the vignette. |

## Base R pros

| Pro | Why it matters |
|---|---|
| Zero deps beyond `utils`/`stats` is portable, fast install. | Lighter footprint = better for Posit Cloud / shared classroom environments. |
| `data.frame` is universal — any R user knows it cold. | No haven/labelled "magic" surprises. |
| CRAN reviewers historically favored lean packages. | Not differentiating — modern CRAN accepts tidyverse-style packages routinely. |

## Base R cons

| Con | Why it bites here |
|---|---|
| Ugly default printing of 70k-row microdata. | Forces every user to wrap with `head()` or `View()`. |
| No first-class slot for variable/value labels. | Forced to invent custom attribute scheme — duplicates work `haven` already did. |
| No clean way to chain operations without `magrittr` or `|>`. | Modern users expect pipes. |
| `stringsAsFactors` historical baggage; coercion surprises. | R 4.0+ defaults to FALSE but legacy code can still hit it. |

---

## Why "lean tidyverse" beats "full tidyverse"

A quick dependency audit (using `pak::pkg_deps()` mental model):

- `tibble` — ~5 transitive deps, all core (rlang, vctrs, pillar, lifecycle, cli)
- `dplyr` — ~15 transitive deps including R6, generics, tidyselect, glue
- `tidyr` — ~10 transitive deps, overlaps with dplyr
- `purrr` — ~5 transitive deps, often replaceable with base `lapply`/`mapply`

A package that hard-deps `dplyr` becomes uninstallable when `dplyr` doesn't compile (rare, but happens on bleeding-edge R-devel or strict corporate environments). A package that only hard-deps `tibble` + `vctrs` + `rlang` + `cli` is safer.

The tradeoff cost: we can't write `df %>% filter(year == 2024)` *inside* `pulso`. We write `df[df$year == 2024, , drop = FALSE]`. That's fine — `pulso` has very little internal data manipulation; most of it is parsing, downloading, and metadata composition.

---

## Style guide implications

**Tidyverse style guide** (Hadley Wickham, https://style.tidyverse.org):

- snake_case for variables AND functions
- Verbs preferred, imperative mood
- Prefix-grouped functions (autocomplete-friendly)
- Lines ≤ 80 chars
- 2-space indentation

**`pulso`-R alignment:**

- ✅ All functions verb-prefixed: `pulso_load`, `pulso_describe_column`, `pulso_list_modules`
- ✅ Internal helpers: snake_case (`compose_metadata`, `parse_codebook`)
- ✅ Constants: `SCREAMING_SNAKE_CASE` per tidyverse guide (`PULSO_DEFAULT_CACHE_DIR`)
- ✅ Format with `styler::style_pkg()`
- ✅ Lint with `lintr` using tidyverse default config

This is a free win — tooling already exists.

---

## Specific recommendations for `pulso`-R

1. **Hard `Imports`** (in `DESCRIPTION`):
   `tibble`, `vctrs`, `rlang`, `cli`, `httr2`, `jsonlite`, `haven`, `tools` (base).

2. **`Suggests`**: `dplyr`, `tidyr`, `srvyr`, `ggplot2`, `testthat`, `knitr`, `rmarkdown`, `withr`, `vcr` (HTTP test mocking), `piggyback` (only if we go option A in Phase 3).

3. **Public functions**:
   - Always return `tibble` (with `haven_labelled` columns when `metadata = TRUE`).
   - Always accept `data.frame` OR `tibble` as input (use `tibble::as_tibble()` internally if needed).
   - snake_case + `pulso_` prefix.

4. **Pipe-friendliness**:
   - Document `|>` first in vignette; mention `%>%` works too.
   - Public functions should have `df` as the first arg (data-first) for `|>` chains.

5. **Print methods**:
   - Don't override tibble printing. It already does the right thing.
   - For `pulso_describe_*` returning a list/object, define a `print.pulso_description` S3 method using `cli` for color.

6. **Error conditions**:
   - Use `rlang::abort()` with structured classes mirroring Python exceptions:
     `pulso_error`, `pulso_data_not_available_error`, `pulso_parse_error`, etc.
   - This lets users `tryCatch(..., pulso_data_not_available_error = ...)`.

---

## Decision required from human

**Q1 — Paradigm: tidyverse-lean / full-tidyverse / hybrid / base R?**

Recommendation: **tidyverse-lean** (returns tibbles, snake_case names, but only `tibble`+`vctrs`+`rlang`+`cli`+`haven`+`httr2`+`jsonlite` as hard deps).

Rationale:
- Matches the audience's expectation (tidyverse-trained R users).
- `haven::labelled` solves the metadata-on-columns problem out of the box.
- Avoids the "have to install dplyr" cost for users who don't want it.
- Style guide is mature and tooled (`styler`, `lintr`).

If the human prefers **base R** (e.g., for minimum-dependency posture), we'd still want to ship `haven_labelled` columns when `metadata=TRUE` because there's no clean base-R substitute. So "pure base R" is partially infeasible without reinventing the labelled-vector wheel.

If the human prefers **full tidyverse** (depend on dplyr + tidyr in `Imports`), the cost is install weight and a tighter coupling to tidyverse release cadence. The benefit is internal code looks more idiomatic. **Not worth it for `pulso`'s small surface area.**

---

## Sources

- [Tidyverse style guide](https://style.tidyverse.org)
- [Tidy design principles — function names](https://design.tidyverse.org/function-names.html)
- [haven CRAN docs](https://cran.r-project.org/web/packages/haven/refman/haven.html)
- [labelled package — Larmarange](https://larmarange.github.io/labelled/articles/labelled.html)
- [Leveraging labelled data in R — Piping Hot Data](https://www.pipinghotdata.com/posts/2020-12-23-leveraging-labelled-data-in-r/)
