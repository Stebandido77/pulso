# Phase 1 — Data Curator Notes: GEIH 2024-06

**Status:** Complete  
**Date:** 2026-04-29  
**Branch:** `feat/data-2024-06`  
**Curator:** Claude Code (Sonnet 4.6)

---

## Source

| Field | Value |
|-------|-------|
| Survey | Gran Encuesta Integrada de Hogares (GEIH) |
| Period | June 2024 (Junio 2024) |
| Epoch | `geih_2021_present` |
| DANE Catalog ID | 819 |
| Landing page | https://microdatos.dane.gov.co/index.php/catalog/819 |
| Download URL | https://microdatos.dane.gov.co/index.php/catalog/819/download/23625 |
| ZIP filename | `Junio_2024.zip` |
| Published by DANE | 2024-08-12 |

---

## Verification

| Check | Result |
|-------|--------|
| HTTP status on download | 200 OK (no login required) |
| Downloaded size | 66,911,109 bytes (63.8 MB) |
| SHA-256 | `c5799177604b0e0890212fbde8d0623e62ec64cca7c301d0e794ba06af44706b` |
| ZIP integrity | Valid (all 24 files extract without error) |
| DIRECTORIO present | Yes (uppercase) in all modules |
| SECUENCIA_P present | Yes (uppercase) in all modules |
| ORDEN present | Yes (uppercase) in all persona-level modules |

---

## ZIP Contents

The archive contains 24 files: 8 modules × 3 formats (CSV, DTA, SAV).

### CSV files (used by pulso)

| Internal path | Rows | Columns | Notes |
|---------------|------|---------|-------|
| `CSV/Características generales, seguridad social en salud y educación.CSV` | 70,020 | 67 | Maps to `caracteristicas_generales` |
| `CSV/Ocupados.CSV` | 29,925 | 200 | Maps to `ocupados` |
| `CSV/No ocupados.CSV` | 25,605 | 37 | Closest map for `desocupados` AND `inactivos` (combined) |
| `CSV/Fuerza de trabajo.CSV` | 55,530 | 43 | No canonical equivalent — see Quirk #3 |
| `CSV/Migración.CSV` | 70,020 | 43 | No canonical equivalent — see Quirk #1 |
| `CSV/Otras formas de trabajo.CSV` | 55,530 | 112 | No canonical equivalent — see Quirk #1 |
| `CSV/Datos del hogar y la vivienda.CSV` | 24,373 | 48 | Maps to `vivienda_hogares` |
| `CSV/Otros ingresos e impuestos.CSV` | 55,530 | 59 | Maps to `otros_ingresos` |

Row totals are consistent (55,530 = 29,925 ocupados + 25,605 no ocupados; 70,020 = total persons in scope).

---

## Module Mapping

```
Schema module          → ZIP file (cabecera)
─────────────────────────────────────────────────────────────────────────────
caracteristicas_generales → CSV/Características generales, seguridad social
                              en salud y educación.CSV
ocupados               → CSV/Ocupados.CSV
desocupados            → CSV/No ocupados.CSV   ← QUIRK: combined with inactivos
inactivos              → CSV/No ocupados.CSV   ← QUIRK: same file as desocupados
vivienda_hogares       → CSV/Datos del hogar y la vivienda.CSV
otros_ingresos         → CSV/Otros ingresos e impuestos.CSV

No canonical mapping:
  CSV/Fuerza de trabajo.CSV       (labor force aggregate)
  CSV/Migración.CSV               (migration module, new in GEIH-2)
  CSV/Otras formas de trabajo.CSV (own-account / gig work module)
```

All `resto` fields are `null` — see Quirk #2.

---

## Quirks

### Quirk 1: 8 modules instead of 6 (GitHub issue needed)

The ZIP contains `Migración` and `Otras formas de trabajo` that have no equivalent in the current 6-module canonical schema:

- `Migración` (70,020 rows, 43 cols): captures migration history and origin. New in GEIH-2.
- `Otras formas de trabajo` (55,530 rows, 112 cols): captures gig work, own-account informal work, subsistence agriculture. New in GEIH-2.

**Action:** Documented here. Schema not modified. GitHub issue opened requesting two new canonical modules: `migracion` and `otras_formas_trabajo`.

### Quirk 2: No Cabecera / Resto file split (GitHub issue needed)

In GEIH-1 (2006-2020), each module came in two separate files: one for Cabecera (urban head municipality) and one for Resto (rural + smaller towns). In GEIH-2 (2021-present), the data is delivered as a single nationwide file per module. The urban/rural distinction is encoded via columns:

- **CLASE**: 1 = Cabecera municipal, 2 = Centro poblado, 3 = Rural disperso (values 2 and 3 form the old "Resto")
- **AREA**: Department code (DPTO-level, e.g. 05=Antioquia, 11=Bogotá)

**Implication for the code (Phase 1 Builder):** The `area` parameter in `pulso.load(..., area="cabecera")` must be translated to a `CLASE == 1` filter applied after loading the single file, rather than selecting a separate file path.

**Action:** All `cabecera` fields in `sources.json["data"]["2024-06"]["modules"]` point to the unified national file. All `resto` fields are `null`. The parser must handle this by filtering on CLASE. GitHub issue opened.

### Quirk 3: desocupados and inactivos share one source file

In GEIH-1, there were separate modules: Desocupados (unemployed, actively seeking work) and Inactivos (outside labor force). In GEIH-2, both are merged into a single "No ocupados" module (25,605 rows). Disaggregation requires filtering by a labor-force-status variable within that file.

Both schema modules `desocupados` and `inactivos` point to `CSV/No ocupados.CSV`. This is the closest valid mapping per the hard rules.

### Quirk 4: Sex variable renamed — P6020 → P6016

The Phase 1 DoD check asserts:

```python
assert "P6020" in df.columns or "p6020" in df.columns  # sex variable present
```

**P6020 does not exist in any GEIH-2 (2024-06) module.** The sex variable is now coded **P6016** (values: 1=Hombre, 2=Mujer). All column names are uppercase.

**Action:** GitHub issue opened to update the DoD assertion. The Builder should be aware when implementing the harmonizer (Phase 2).

### Quirk 5: CSV delimiter is semicolon

All CSV files use `;` (semicolon) as the field separator, not `,` (comma). The parser must specify `sep=";"` when calling `pd.read_csv()`.

---

## Open Questions Answered (from PHASE_0_NOTES.md)

| Question | Answer |
|----------|--------|
| Are merge keys uppercase? | **Yes.** `DIRECTORIO`, `SECUENCIA_P`, `ORDEN` are all uppercase in GEIH-2 2024-06. |
| Does 2024-06 ZIP contain all 6 modules? | **No.** It contains 8 modules, of which 6 map (imperfectly) to the canonical schema. Two (Migración, Otras formas de trabajo) are new with no schema equivalent. |
| Column case? | **All uppercase** (no mixed or lowercase columns observed). |

---

## Awaiting Human QA

- [ ] Confirm file download is reproducible from the stated URL
- [ ] Confirm SHA-256 matches
- [ ] Review Quirk #2 mapping decision: should `cabecera` point to the unified file, or should a new `national` key be added to `ModuleFiles`?
- [ ] Review Quirk #3 mapping decision: should `desocupados` be `null` rather than pointing to the combined file?
- [ ] Confirm GitHub issues were opened (links in PR body)
- [ ] Approve merge
