"""Generate synthetic test fixtures for the pulso unit and integration tests.

Run to (re)generate the fixture ZIPs:

    python tests/_build_fixtures.py

The resulting files are committed to the repo (whitelisted in .gitignore).
"""

from __future__ import annotations

import io
import random
import zipfile
from pathlib import Path

import pandas as pd

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "zips"
ZIP_NAME = "geih2_sample.zip"
UNIFIED_ZIP_NAME = "geih2_unified_sample.zip"

# Separator and decimal match the geih_2021_present epoch definition.
SEP = ";"
DECIMAL = ","

AREA_NAMES = ("Cabecera", "Resto")

# File paths inside the Shape A ZIP (must match conftest fixture entry).
INNER_PATHS: dict[str, dict[str, str]] = {
    "Cabecera": {
        "caracteristicas_generales": (
            "Cabecera/Cabecera - Caracteristicas generales (Personas).CSV"
        ),
        "ocupados": "Cabecera/Cabecera - Ocupados.CSV",
    },
    "Resto": {
        "caracteristicas_generales": ("Resto/Resto - Caracteristicas generales (Personas).CSV"),
        "ocupados": "Resto/Resto - Ocupados.CSV",
    },
}

# File paths inside the Shape B unified ZIP.
UNIFIED_INNER_PATHS = {
    "ocupados": "CSV/Ocupados.CSV",
    "no_ocupados": "CSV/No ocupados.CSV",
    "caracteristicas_generales": (
        "CSV/Características generales, seguridad social en salud y educación.CSV"
    ),
}


def _make_caracteristicas(rng: random.Random, n: int) -> pd.DataFrame:
    """Build a synthetic caracteristicas_generales table with `n` rows."""
    directorios = [f"{i:04d}" for i in range(1, n + 1)]
    rows = []
    for d in directorios:
        rows.append(
            {
                "DIRECTORIO": d,
                "SECUENCIA_P": 1,
                "ORDEN": 1,
                "HOGAR": 1,
                "MES": 6,
                "P6020": rng.choice([1, 2]),
                "P6040": rng.randint(0, 99),
                "FEX_C18": round(rng.uniform(1000.0, 5000.0), 4),
            }
        )
    return pd.DataFrame(rows)


def _make_ocupados(rng: random.Random, carac: pd.DataFrame) -> pd.DataFrame:
    """Build a synthetic ocupados table covering ~60 % of carac rows."""
    mask = pd.Series([rng.random() < 0.60 for _ in range(len(carac))], index=carac.index)
    subset = carac[mask][["DIRECTORIO", "SECUENCIA_P", "ORDEN", "FEX_C18"]].copy()
    subset["INGLABO"] = [round(rng.uniform(0.0, 10_000_000.0), 2) for _ in range(len(subset))]
    subset["P6800"] = [rng.randint(1, 60) for _ in range(len(subset))]
    return subset.reset_index(drop=True)


def _df_to_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_csv(buf, index=False, sep=SEP, decimal=DECIMAL, encoding="utf-8")
    return buf.getvalue()


def build_fixture_zip(dest: Path, seed: int = 42) -> None:
    """Generate the synthetic Shape A fixture ZIP at `dest`.

    Idempotent: running twice with the same seed produces the same file.
    """
    rng = random.Random(seed)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for area in AREA_NAMES:
            carac = _make_caracteristicas(rng, 50)
            ocup = _make_ocupados(rng, carac)

            zf.writestr(INNER_PATHS[area]["caracteristicas_generales"], _df_to_bytes(carac))
            zf.writestr(INNER_PATHS[area]["ocupados"], _df_to_bytes(ocup))

    print(f"Written: {dest}  ({dest.stat().st_size:,} bytes)")


def _clase_value(rng: random.Random) -> int:
    """Return a CLASE value: 60% = 1, 20% = 2, 20% = 3."""
    r = rng.random()
    if r < 0.60:
        return 1
    if r < 0.80:
        return 2
    return 3


def _make_unified_ocupados(rng: random.Random, n: int) -> pd.DataFrame:
    """Build a unified ocupados table with CLASE column (Shape B)."""
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "DIRECTORIO": f"{i:04d}",
                "SECUENCIA_P": 1,
                "ORDEN": 1,
                "HOGAR": 1,
                "MES": 6,
                "CLASE": _clase_value(rng),
                "P6016": rng.choice([1, 2]),
                "P6040": rng.randint(15, 99),
                "FEX_C18": round(rng.uniform(1000.0, 5000.0), 4),
                "INGLABO": round(rng.uniform(0.0, 10_000_000.0), 2),
                "P6800": rng.randint(1, 60),
            }
        )
    return pd.DataFrame(rows)


def _make_unified_no_ocupados(rng: random.Random, n: int) -> pd.DataFrame:
    """Build a unified no-ocupados table with CLASE and OCI columns (Shape B).

    OCI distribution: ~30% = 2 (desocupado), ~70% = 3 (inactivo).
    """
    rows = []
    for i in range(1, n + 1):
        oci = 2 if rng.random() < 0.30 else 3
        rows.append(
            {
                "DIRECTORIO": f"{i + 10000:05d}",
                "SECUENCIA_P": 1,
                "ORDEN": 1,
                "HOGAR": 1,
                "MES": 6,
                "CLASE": _clase_value(rng),
                "OCI": oci,
                "P7250": rng.randint(0, 52),
                "FEX_C18": round(rng.uniform(1000.0, 5000.0), 4),
            }
        )
    return pd.DataFrame(rows)


def _make_unified_caracteristicas(rng: random.Random, n: int) -> pd.DataFrame:
    """Build a unified caracteristicas table with CLASE column (Shape B)."""
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "DIRECTORIO": f"{i:06d}",
                "SECUENCIA_P": 1,
                "ORDEN": 1,
                "HOGAR": 1,
                "MES": 6,
                "CLASE": _clase_value(rng),
                "FEX_C18": round(rng.uniform(1000.0, 5000.0), 4),
            }
        )
    return pd.DataFrame(rows)


def build_unified_fixture_zip(dest: Path, seed: int = 42) -> None:
    """Generate the synthetic Shape B (unified) fixture ZIP at `dest`.

    Structure mirrors the real DANE GEIH-2 ZIP: one CSV per module with a
    CLASE column encoding the urban/rural distinction.

    Idempotent: running twice with the same seed produces the same file.
    """
    rng = random.Random(seed)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            UNIFIED_INNER_PATHS["ocupados"],
            _df_to_bytes(_make_unified_ocupados(rng, 200)),
        )
        zf.writestr(
            UNIFIED_INNER_PATHS["no_ocupados"],
            _df_to_bytes(_make_unified_no_ocupados(rng, 150)),
        )
        zf.writestr(
            UNIFIED_INNER_PATHS["caracteristicas_generales"],
            _df_to_bytes(_make_unified_caracteristicas(rng, 300)),
        )

    print(f"Written: {dest}  ({dest.stat().st_size:,} bytes)")


if __name__ == "__main__":
    build_fixture_zip(FIXTURE_DIR / ZIP_NAME)
    build_unified_fixture_zip(FIXTURE_DIR / UNIFIED_ZIP_NAME)
