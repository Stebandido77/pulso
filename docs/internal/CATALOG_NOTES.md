# DANE GEIH Catalog Notes

Phase 3.1 findings from scraping the DANE MERCLAB-Microdatos collection.
Produced by `scripts/scrape_dane_catalog.py` on 2026-05-01.

---

## Scrape summary

| Field | Value |
|-------|-------|
| **Scraped at** | 2026-05-01 |
| **Annual catalogs visited** | 20 |
| **GEIH monthly entries found** | 230 |
| **Coverage span** | 2007-01 to 2026-02 |
| **Total months covered** | 230 |
| **Expected months (2007-01 → 2026-05)** | 233 |
| **Gap count** | 3 (all in 2026, not yet published) |

---

## Coverage by year

| Year | Months | Catalog ID | Size range (MB) | Notes |
|------|--------|-----------|-----------------|-------|
| 2007 | 12/12 | 317 | 6–7 | Earliest available microdata |
| 2008 | 12/12 | 206 | 6–15 | |
| 2009 | 12/12 | 207 | 6–6 | |
| 2010 | 12/12 | 205 | 6–7 | |
| 2011 | 12/12 | 182 | 7–7 | |
| 2012 | 12/12 | 77 | 6–7 | |
| 2013 | 12/12 | 68 | 6–7 | |
| 2014 | 12/12 | 328 | 6–7 | |
| 2015 | 12/12 | 356 | 6–7 | |
| 2016 | 12/12 | 427 | 6–7 | |
| 2017 | 12/12 | 458 | 6–9 | |
| 2018 | 12/12 | 547 | 6–7 | |
| 2019 | 12/12 | 599 | 6–7 | |
| 2020 | 12/12 | 780 | 8–23 | COVID-19 reduced coverage Mar–Jul (see below) |
| 2021 | 12/12 | 701 | 5–7 | Transitional year (Marco 2005 format retained) |
| 2022 | 12/12 | 771 | 46–75 | **Major format change**: GEIH Marco 2018 deployed |
| 2023 | 12/12 | 782 | 59–71 | |
| 2024 | 12/12 | 819 | 55–66 | Sources.json anchor; 2024-06 validated |
| 2025 | 12/12 | 853 | 59–66 | Full year available as of 2026-05 |
| 2026 | 2/12 | 900 | 63–67 | Jan–Feb only; Mar–May not yet published |

---

## GEIH 2006: the microdata gap

**The GEIH started field data collection on August 7, 2006** — but DANE has not
published microdata for August–December 2006 in the MERCLAB portal.

Evidence gathered during Phase 3.1:
- The MERCLAB-Microdatos collection has no "GEIH 2006" catalog entry.
- The earliest main annual GEIH catalog is **ID 317, titled "Gran Encuesta Integrada
  de Hogares - GEIH 2007"**. Its `/get_microdata` page lists 12 files named
  "Enero" through "Diciembre" (no year qualifier), all with upload dates of
  2018-02-02 and file content clearly representing January–December 2007.
- The catalog's own metadata says `Fecha inicio: 2007` for its data collection
  period. The `idno` is `COL-DANE-GEIH-2007-IV-TRIMESTRE`, placing it in 2007.
- Historical text within the catalog descriptions repeatedly references 2006
  as the *start of operations* (e.g., "La recolección de la GEIH empezó el 7
  de agosto de 2006"), not as data that is available for download.

**Conclusion**: The 2006 microdata (Aug–Dec 2006, 5 months) was collected but is
not published through the DANE microdata portal. The user community sometimes
confuses **GEIH operational start (August 2006)** with **public microdata start
(January 2007)**. For pulso, the effective earliest entry is **2007-01**.

Phase 3.2 should set `covered_range` minimum to `"2007-01"` in `sources.json`
metadata. If 2006 data becomes available, it would be in a separate catalog not
yet present in MERCLAB.

---

## Identified gaps

| Year | Month | Reason |
|------|-------|--------|
| 2026 | 03 | Not yet published (DANE publication lag ~2 months) |
| 2026 | 04 | Not yet published (DANE publication lag ~2 months) |
| 2026 | 05 | Not yet published (DANE publication lag ~2 months) |

No months were completely absent for 2007–2025. The 2020 pandemic months
(April–July 2020) **do exist** in the catalog — they have reduced file sizes
reflecting smaller sample coverage, but the data files are present. See the
2020 anomaly note below.

---

## Identified anomalies

### 2020 COVID-19: reduced coverage March–July 2020

DANE suspended in-person field operations in March 2020 and switched to
telephone interviews for a subset of the sample. The monthly file sizes show
this clearly:

| Month | Size (MB) | Note |
|-------|-----------|------|
| Jan 2020 | 20.8 | Pre-COVID, full sample |
| Feb 2020 | 20.8 | Pre-COVID, full sample |
| Mar 2020 | 10.4 | **Partial** — lockdown mid-month |
| Apr 2020 | 8.0 | **Reduced** — telephone-only interviews |
| May 2020 | 11.7 | **Reduced** — telephone interviews |
| Jun 2020 | 11.7 | **Reduced** — telephone interviews |
| Jul 2020 | 11.6 | **Reduced** — telephone interviews |
| Aug 2020 | 22.9 | Resumed, full sample |
| Sep 2020 | 22.6 | Full sample |

The data exists and downloads normally; coverage is simply reduced. Phase 3.2
should flag these months with a note in `sources.json` so downstream users know
to weight accordingly.

### 2022 GEIH Marco 2018: major redesign

Starting January 2022, DANE deployed the fully redesigned GEIH (Marco 2018 —
using the 2018 Population and Housing Census as the sampling frame). This is
visible as a dramatic size jump:

- 2021-06 (old format): ~6 MB
- 2022-06 (new format): ~67 MB — **11× larger**

The 2022+ files also have a distinct naming convention:
`GEIH_{Month}_{Year}_Marco_2018.zip` (though this shortened again in 2023+).
The new survey adds expanded modules for migration, alternative work forms,
and more socioeconomic variables. These align with the `geih_2021_present` epoch
(though the true redesign boundary is 2022, not 2021 — see design note below).

### Epoch boundary vs. survey redesign boundary

The current `epochs.json` defines:
- `geih_2006_2020`: covers 2006–2020
- `geih_2021_present`: covers 2021 onwards

However, the actual file format and survey design break at **2022, not 2021**:
- 2021: Same ~5-7 MB CSV files as 2019–2020; same variable structure.
  This was the "Sistema General de Pruebas" (testing phase) — new questionnaire
  tested in parallel but published data is Marco 2005 format.
- 2022: New Marco 2018 files, 46–75 MB, expanded modules.

**Implication for Phase 3.2/3.3**: The variable harmonizer should treat 2021
as behaviorally identical to the 2019–2020 era for file structure purposes,
even though it's labeled `geih_2021_present`. The boundary where file structure
truly changes is 2022-01. Flag this for the Builder team.

### 2026 catalog: only 2 months

Catalog 900 (GEIH 2026) was created anticipating the full year. Only January
and February 2026 are published. This is expected — DANE typically publishes
with a 2-month lag. March–May 2026 will be available by mid-2026.

---

## Catalog ID distribution

| Stat | Value |
|------|-------|
| Earliest GEIH annual catalog ID | 68 (GEIH 2013) |
| Lowest GEIH catalog ID found | 68 |
| Highest GEIH catalog ID found | 900 (GEIH 2026) |
| IDs are sequential by year? | **No** — IDs are assigned in upload order, not chronologically |
| Range covered | 68–900 |
| Non-GEIH catalogs in range | ~860 |

Catalog ID 819 (GEIH 2024) was the known anchor from Phase 1. As a sanity
check: this entry's download URL in `_scraped_catalog.json` matches exactly
the URL in `sources.json` (`catalog/819/download/23625`). ✓

---

## Format observations

### 2007–2021 (epoch `geih_2006_2020` + 2021)

Each annual catalog contains multiple file formats per month. For example,
2007 has for each month: the original SPSS file (no extension), a CSV ZIP,
and sometimes a Stata DTA ZIP. By 2018, the set settled to SPSS + CSV + Stata
for every month.

The scraper selects **CSV format** as primary (`Enero.csv`, `Febrero.csv`, etc.)
because pulso's core loader targets CSV input. For months where only SPSS or
Stata is available (some 2007 entries), the SPSS file is selected.

Auxiliary files in these catalogs (excluded by the scraper):
- `Total_fact_exp_{YEAR}` / `Total_Fex_{YEAR}`: expansion factor files
- `Fex proyecciones CNPV 2018_{YEAR}`: 2018 Census projection weights (added
  retroactively to all years)
- Various annual totals and methodology documentation ZIPs

### 2022–2026 (epoch `geih_2021_present` from 2022)

Single ZIP per month containing all survey modules as CSV files. File sizes
are 55–79 MB. No auxiliary format variants — the CSV is the sole published format.
File naming is less consistent than older years (trailing periods, underscores
vs. spaces, month abbreviations like "Ene_2024").

---

## Discovery strategy: deviation from ADR 0004

ADR 0004 described a sequential catalog-ID scanning strategy (start at ID 819,
expand forward/backward, stop after 5 consecutive non-GEIH IDs). This was
written before inspecting the live site.

**Actual implementation**: The MERCLAB-Microdatos collection provides a paginated
index of all surveys in DANE's labor-market catalog. Enumerating 9 pages (135
catalog links) finds all GEIH catalogs in ~20 seconds, without scanning ~900
individual IDs. The scraper then fetches each annual catalog's `/get_microdata`
page to extract monthly file entries.

This is faster, more reliable (no heuristic stop conditions), and more
maintainable (DANE adding new surveys doesn't affect the scan). The committed
`_scraped_catalog.json` captures the result for reproducibility.

---

## Open questions / human review needed

1. **2006 microdata**: Confirm definitively whether DANE has Aug–Dec 2006 data
   in any other system (e.g., the legacy ECH portal, or internal DANE requests).
   If recoverable, it would require a new catalog entry type not currently modeled.

2. **2021 epoch boundary**: The `geih_2021_present` epoch starts at 2021, but
   the Marco 2018 redesign data starts at 2022. Should `epochs.json` be updated
   to split 2021 into its own epoch, or is the current grouping acceptable for
   harmonization? (Builder/Architect decision.)

3. **2020 COVID months**: Should these have a `note` field in `sources.json`
   flagging reduced coverage? Recommended: yes. Phase 3.2 should add a note to
   April–July 2020 entries.

4. **Primary file for 2007–2021**: The scraper selects CSV format. However, some
   CSV ZIPs from this era may have different internal file structures than 2022+
   (e.g., multiple sheets, different column names). Phase 3.3 (harmonizer) should
   verify the first entry from each year range.

---

## Recommendations for Phase 3.2

1. **Populate `sources.json`** with entries for all 230 months. The
   `_scraped_catalog.json` provides all required fields: `download_url`,
   `landing_page`, `size_bytes`, `epoch_inferred`.

2. **Set `covered_range` to `["2007-01", "2026-02"]`** in `sources.json` metadata.
   The commonly cited "August 2006" start is the survey inception, not the
   earliest available microdata.

3. **Mark 2024-06 as `validated: true`** (already in `sources.json` from Phase 1);
   all other entries should start as `validated: false`.

4. **Add `notes` field** to April–July 2020 entries documenting COVID-19 reduced
   coverage.

5. **Watch for 2026 updates**: Catalog 900 will gain March–May 2026 entries as
   DANE publishes them. The scraper can be re-run to capture new months.

6. **Check `checksum_sha256`**: Currently `null` for all entries — DANE does not
   publish checksums on the get_microdata page. The validate step in Phase 3.2
   should compute checksums after downloading a sample.


## Update 2026-05-01: Epoch Boundary Correction

After Phase 3.1 was merged, the Phase 3.2 strategic spike (downloading 4 ZIPs from 2007-12, 2015-06, 2021-06, 2022-01) provided empirical evidence that the GEIH file format break is **January 2022**, not January 2021 as initially assumed.

### Evidence

| Month | Size (MB) | File format | Epoch |
|---|---|---|---|
| 2007-12 | 6.4 | Shape A (CSV simple) | geih_2006_2020 |
| 2015-06 | 6.7 | Shape A | geih_2006_2020 |
| 2021-06 | 6.2 | Shape A | geih_2006_2020 (corrected) |
| 2022-01 | 77 | Shape B (Marco 2018) | geih_2021_present |

The 2021 files retain the old format despite DANE's documented methodological redesign date being 2021. The actual file format transition occurred 12 months later when the 2018 sampling frame was deployed in production.

### Impact

- `pulso/data/epochs.json`: `geih_2006_2020.date_range` extended from `[2006-01, 2020-12]` to `[2006-01, 2021-12]`. `geih_2021_present.date_range` shifted from `[2021-01, null]` to `[2022-01, null]`.
- `scripts/scrape_dane_catalog.py`: `infer_epoch()` updated from `year < 2021` to `year < 2022`.
- `pulso/data/_scraped_catalog.json`: regenerated. 12 entries (2021-01 through 2021-12) reclassified from `geih_2021_present` to `geih_2006_2020`.
- Tests: `test_epoch_for_month_2021_01_boundary` removed (no longer a boundary). Added `test_epoch_for_month_2022_01_boundary`, `test_epoch_for_month_2021_12_is_geih2006`, `test_epoch_for_month_2021_06_is_geih2006`.

### Final distribution

- `geih_2006_2020`: 180 entries (2007-01 through 2021-12)
- `geih_2021_present`: 50 entries (2022-01 through 2026-02)

The epoch key name `geih_2021_present` is intentionally retained despite being technically misleading. Renaming to `geih_2022_present` would touch ~170 references across code, tests, and data files. The key is an internal identifier; the date_range is the source of truth.
