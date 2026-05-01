# ADR 0004: DANE Catalog Scraping Strategy

## Status

Accepted (Phase 3.1)

## Context

Phase 3 of pulso requires complete coverage of GEIH microdata from August 2006 to the current month (~230 monthly entries). To populate `pulso/data/sources.json` with all entries, we need a reliable, reproducible way to discover:

1. Which months are available in the DANE catalog
2. Each month's download URL
3. Each month's checksum (when published)
4. Each month's landing page (for human inspection)
5. Any anomalies (missing months, format changes, special operatives like 2020-pandemia)

Manual data entry is not viable at this scale and would not survive future months. We need automation.

## Decision

We will implement a Python script `scripts/scrape_dane_catalog.py` that:

1. **Discovers DANE catalog URLs** by iterating known catalog ID ranges. DANE GEIH catalogs follow the pattern `https://microdatos.dane.gov.co/index.php/catalog/{ID}` where IDs are sequential integers. We start from a known anchor (catalog 819 = 2024-06 GEIH-2) and explore forward and backward.

2. **Extracts metadata** from each catalog page using HTML parsing. Required fields:
   - year, month
   - download_url (the ZIP)
   - checksum_sha256 (when DANE publishes one)
   - size_bytes (from HTTP HEAD or page metadata)
   - landing_page (the catalog URL itself)
   - epoch_inferred (geih_2006_2020 or geih_2021_present, based on year)

3. **Filters to GEIH-relevant catalogs only**. DANE publishes many surveys; we only want GEIH (Gran Encuesta Integrada de Hogares). Identification: title contains "Gran Encuesta Integrada de Hogares" and a month/year reference.

4. **Outputs `pulso/data/_scraped_catalog.json`** with structure:

```json
   {
     "scraped_at": "2026-05-01T00:00:00Z",
     "scraped_by": "scripts/scrape_dane_catalog.py",
     "schema_version": "0.1.0",
     "entries": [
       {
         "year": 2024,
         "month": 6,
         "catalog_id": 819,
         "download_url": "https://microdatos.dane.gov.co/...",
         "landing_page": "https://microdatos.dane.gov.co/index.php/catalog/819",
         "checksum_sha256": "c5799177...",
         "size_bytes": 66911109,
         "epoch_inferred": "geih_2021_present",
         "title": "...",
         "anomalies": []
       }
     ],
     "gaps": [
       {"year": 2020, "month": 4, "reason": "DANE suspended operations due to pandemic"}
     ],
     "scrape_log": {
       "catalogs_visited": 250,
       "geih_matches": 232,
       "errors": []
     }
   }
```

5. **The file `_scraped_catalog.json` is committed** to the repo. This makes the catalog reproducible without re-scraping.

6. **Discovery strategy for catalog IDs**:
   - Anchor: catalog 819 = 2024-06
   - Forward: increment IDs until we hit 5 consecutive non-GEIH catalogs (heuristic stop)
   - Backward: decrement IDs until we cover Aug 2006 (catalog ID estimated lower 100s based on chronology)
   - Cache discovered catalogs in `_scraped_catalog.json` for incremental updates

7. **Network resilience**:
   - Timeout: 10s per request
   - Retries: 3 with exponential backoff
   - User-Agent: `pulso-catalog-scraper/0.3.1 (https://github.com/Stebandido77/pulso)`
   - Rate limiting: 1 request per 2 seconds (be nice to DANE)

8. **Gap handling**:
   - Months explicitly missing from DANE → recorded in `gaps[]` with reason
   - Months where scraping failed (network error) → recorded in `scrape_log.errors[]` for retry
   - Months with non-standard structure → flagged in `anomalies[]` for human review

## Consequences

### Positive

- Reproducibility: anyone can re-run the scraper to verify catalog state
- Maintainability: new months are added by re-running the script
- Transparency: scraping logic is explicit and auditable
- Phase 3.2 enabler: with `_scraped_catalog.json` we can deterministically generate `sources.json`

### Negative

- Brittleness: if DANE redesigns their website, the scraper breaks. Mitigation: committed `_scraped_catalog.json` survives a redesign.
- Catalog ID heuristic: assuming sequential IDs can fail if DANE renumbers. Documented assumption.

### Mitigations

- Scraper logs all decisions and outputs detailed scrape_log
- A separate verification step in Phase 3.2 will re-fetch a sample to detect drift
- `docs/CATALOG_NOTES.md` records all assumptions and known anomalies

## Alternatives considered

### Manual catalog curation

Reject. 230 months × ~10 fields each = 2,300 manual entries. Error-prone, not maintainable.

### DANE provides a machine-readable API

DANE does not currently publish an API for catalog enumeration. If they add one, we should switch.

### Scraping at runtime (no committed catalog)

Reject. This would make pulso depend on DANE being online and stable for every user.

## References

- DANE catalog landing: https://microdatos.dane.gov.co/index.php/catalog
- ADR 0001: Multi-agent build model (Curator owns data files)
- ADR 0003: Schema 1.1.0
- Phase 2 sources.json structure (validated for 1 entry)

## Decision date

2026-05-01

## Authors

Architect (Claude in chat) + Esteban Labastidas
