"""Generate pulso/data/sources.json from pulso/data/_scraped_catalog.json.

Produces a deterministic sources.json with one MonthRecord per catalog entry.
Manually validated entries (e.g. 2024-06) are preserved unchanged.

Usage:
    python scripts/generate_sources_from_catalog.py \
        --catalog pulso/data/_scraped_catalog.json \
        --output pulso/data/sources.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

# ---------------------------------------------------------------------------
# Canonical module definitions
# ---------------------------------------------------------------------------

CANONICAL_MODULES: dict[str, dict] = {
    "caracteristicas_generales": {
        "level": "persona",
        "description_es": "Características demográficas, educativas y de salud de las personas.",
        "description_en": "Demographic, educational, and health characteristics of persons.",
        "available_in": ["geih_2006_2020", "geih_2021_present"],
    },
    "ocupados": {
        "level": "persona",
        "description_es": "Información laboral de las personas ocupadas en la semana de referencia.",
        "description_en": "Labor market information for employed persons in the reference week.",
        "available_in": ["geih_2006_2020", "geih_2021_present"],
    },
    "desocupados": {
        "level": "persona",
        "description_es": "Características de las personas que buscan empleo.",
        "description_en": "Characteristics of unemployed job seekers.",
        "available_in": ["geih_2006_2020", "geih_2021_present"],
    },
    "inactivos": {
        "level": "persona",
        "description_es": "Personas no ocupadas y no buscando empleo.",
        "description_en": "Persons not employed and not seeking work.",
        "available_in": ["geih_2006_2020", "geih_2021_present"],
    },
    "vivienda_hogares": {
        "level": "hogar",
        "description_es": "Características de la vivienda y los hogares que la habitan: servicios, tenencia, materiales.",
        "description_en": "Dwelling and household characteristics: services, tenure, materials.",
        "available_in": ["geih_2006_2020", "geih_2021_present"],
    },
    "otros_ingresos": {
        "level": "persona",
        "description_es": "Ingresos no laborales: pensiones, transferencias, ayudas, intereses, etc.",
        "description_en": "Non-labor income: pensions, transfers, aid, interests, etc.",
        "available_in": ["geih_2006_2020", "geih_2021_present"],
    },
    "migracion": {
        "level": "persona",
        "description_es": "Información sobre migración y desplazamientos de las personas.",
        "description_en": "Migration and displacement information for persons.",
        "available_in": ["geih_2021_present"],
    },
    "otras_formas_trabajo": {
        "level": "persona",
        "description_es": "Trabajo voluntario, doméstico no remunerado, y otras actividades laborales fuera del empleo formal.",
        "description_en": "Volunteer work, unpaid domestic labor, and other labor activities outside formal employment.",
        "available_in": ["geih_2021_present"],
    },
}

# ---------------------------------------------------------------------------
# File path templates per shape
# ---------------------------------------------------------------------------

# Shape B (Unified, geih_2021_present): canonical filenames verified against 2024-06 ZIP.
# desocupados/inactivos share "No ocupados.CSV" without row_filter — Phase 3.4 confirms
# the OCI column semantics and will add row_filter if needed.
SHAPE_B_FILES: dict[str, dict] = {
    "caracteristicas_generales": {
        "file": "CSV/Características generales, seguridad social en salud y educación.CSV"
    },
    "ocupados": {"file": "CSV/Ocupados.CSV"},
    "desocupados": {"file": "CSV/No ocupados.CSV"},
    "inactivos": {"file": "CSV/No ocupados.CSV"},
    "vivienda_hogares": {"file": "CSV/Datos del hogar y la vivienda.CSV"},
    "otros_ingresos": {"file": "CSV/Otros ingresos e impuestos.CSV"},
    "migracion": {"file": "CSV/Migración.CSV"},
    "otras_formas_trabajo": {"file": "CSV/Otras formas de trabajo.CSV"},
}

# Shape A (Split, geih_2006_2020): canonical filenames.
# The Shape A parser (is_shape_a + find_shape_a_files) tolerates real-world
# variations (missing accents, 2007 typos like "Caractericas", spacing) via
# keyword matching — so these canonical names are the authoritative declarations,
# not the actual filenames on disk.
SHAPE_A_FILES: dict[str, dict] = {
    "caracteristicas_generales": {
        "cabecera": "Cabecera - Características generales (Personas).csv",
        "resto": "Resto - Características generales (Personas).csv",
    },
    "ocupados": {
        "cabecera": "Cabecera - Ocupados.csv",
        "resto": "Resto - Ocupados.csv",
    },
    "desocupados": {
        "cabecera": "Cabecera - Desocupados.csv",
        "resto": "Resto - Desocupados.csv",
    },
    "inactivos": {
        "cabecera": "Cabecera - Inactivos.csv",
        "resto": "Resto - Inactivos.csv",
    },
    "vivienda_hogares": {
        "cabecera": "Cabecera - Vivienda y Hogares.csv",
        "resto": "Resto - Vivienda y Hogares.csv",
    },
    "otros_ingresos": {
        "cabecera": "Cabecera - Otros ingresos.csv",
        "resto": "Resto - Otros ingresos.csv",
    },
    # migracion and otras_formas_trabajo: not available in geih_2006_2020.
}


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def build_month_record(entry: dict, catalog_scraped_at: str) -> dict:
    """Build a MonthRecord dict from a _scraped_catalog.json entry."""
    epoch = entry["epoch_inferred"]

    if epoch == "geih_2021_present":
        modules = {
            name: dict(SHAPE_B_FILES[name])
            for name in CANONICAL_MODULES
            if epoch in CANONICAL_MODULES[name]["available_in"]
        }
    else:
        # geih_2006_2020: only modules with available_in that includes this epoch
        # AND that have a Shape A file definition.
        modules = {
            name: dict(SHAPE_A_FILES[name])
            for name in CANONICAL_MODULES
            if epoch in CANONICAL_MODULES[name]["available_in"] and name in SHAPE_A_FILES
        }

    return {
        "epoch": epoch,
        "download_url": entry["download_url"],
        "landing_page": entry.get("landing_page"),
        "checksum_sha256": entry.get("checksum_sha256"),  # null for most entries
        "size_bytes": entry.get("size_bytes"),
        "scraped_at": catalog_scraped_at,
        "validated": False,
        "validated_by": None,
        "validated_at": None,
        "modules": modules,
        "notes": None,
    }


def load_existing_sources(path: Path) -> dict | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("pulso/data/_scraped_catalog.json"),
        help="Path to _scraped_catalog.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("pulso/data/sources.json"),
        help="Path to write sources.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate but do not write the output file",
    )
    args = parser.parse_args()

    # Load catalog
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    entries = catalog["entries"]
    catalog_scraped_at = catalog["scraped_at"]
    print(f"Loaded {len(entries)} entries from catalog")

    # Load existing sources (to preserve manually validated entries)
    existing = load_existing_sources(args.output)
    existing_data: dict = existing.get("data", {}) if existing else {}

    # Build data dict
    new_data: dict = {}
    preserved = 0
    generated = 0

    for entry in entries:
        key = f"{entry['year']}-{entry['month']:02d}"

        if key in existing_data and existing_data[key].get("validated"):
            new_data[key] = existing_data[key]
            preserved += 1
        else:
            new_data[key] = build_month_record(entry, catalog_scraped_at)
            generated += 1

    print(
        f"Preserved {preserved} manually validated entr{'y' if preserved == 1 else 'ies'}: "
        f"{', '.join(k for k, v in existing_data.items() if v.get('validated'))}"
    )
    print(f"Generated {generated} new entries")

    # Build full sources structure
    result = {
        "metadata": {
            "schema_version": "1.1.0",
            "data_version": "2026.04",
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scraper_version": "generate_sources_from_catalog/0.1.0",
            "covered_range": [
                sorted(new_data.keys())[0],
                sorted(new_data.keys())[-1],
            ],
        },
        "modules": CANONICAL_MODULES,
        "data": new_data,
    }

    # Validate against schema
    schema_path = args.output.parent / "schemas" / "sources.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=result, schema=schema)
        print("Schema validation: OK")
    except jsonschema.ValidationError as e:
        print(f"VALIDATION FAILED: {e.message}")
        path_str = " -> ".join(str(p) for p in e.absolute_path)
        print(f"Path: {path_str}")
        return 1

    if args.dry_run:
        print(f"DRY RUN — would write {len(new_data)} entries to {args.output}")
        return 0

    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Written {len(new_data)} entries to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
