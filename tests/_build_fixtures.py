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
    """Return a CLASE value: 60% = 1, 40% = 2."""
    return 1 if rng.random() < 0.60 else 2


def _make_unified_caracteristicas(rng: random.Random, n: int) -> pd.DataFrame:
    """Build unified caracteristicas_generales with n persons.

    DIRECTORIOs are zero-padded 5-digit strings ("00001"-"00050") shared
    across all modules to enable outer joins on [DIRECTORIO, SECUENCIA_P, ORDEN].
    """
    rows = []
    for i in range(1, n + 1):
        rows.append(
            {
                "DIRECTORIO": f"{i:05d}",
                "SECUENCIA_P": 1,
                "ORDEN": 1,
                "HOGAR": 1,
                "MES": 6,
                "CLASE": _clase_value(rng),
                "P3271": rng.choice([1, 2]),
                "P6040": rng.randint(0, 99),
                "FEX_C18": round(rng.uniform(1000.0, 5000.0), 4),
            }
        )
    return pd.DataFrame(rows)


def _make_unified_ocupados(rng: random.Random, carac_subset: pd.DataFrame) -> pd.DataFrame:
    """Build ocupados from a subset of carac rows (60% of N).

    All rows have OCI=1 (by definition: everyone in ocupados is employed).
    """
    sub = carac_subset[
        ["DIRECTORIO", "SECUENCIA_P", "ORDEN", "HOGAR", "MES", "CLASE", "FEX_C18"]
    ].copy()
    sub["OCI"] = 1
    sub["INGLABO"] = [round(rng.uniform(0.0, 10_000_000.0), 2) for _ in range(len(sub))]
    sub["P6800"] = [rng.randint(1, 60) for _ in range(len(sub))]
    return sub.reset_index(drop=True)


def _make_unified_no_ocupados(rng: random.Random, carac_subset: pd.DataFrame) -> pd.DataFrame:
    """Build no_ocupados from a subset of carac rows (40% of N).

    Of those: 30% have DSI=1 (desocupados), 70% have DSI=NaN (inactivos).
    Includes columns declared in PHASE_2_CODE_NOTES.md spec.
    """
    n = len(carac_subset)
    n_desoc = max(1, round(n * 0.30))

    sub = carac_subset[
        ["DIRECTORIO", "SECUENCIA_P", "ORDEN", "HOGAR", "MES", "CLASE", "FEX_C18"]
    ].copy()

    dsi_values = [1] * n_desoc + [None] * (n - n_desoc)
    dscy_values = [1] * n_desoc + [None] * (n - n_desoc)
    p7280_values = [rng.randint(1, 2)] * n_desoc + [None] * (n - n_desoc)

    sub["DSI"] = pd.array(dsi_values, dtype="Int64")
    sub["DSCY"] = pd.array(dscy_values, dtype="Int64")
    sub["P7430"] = pd.array([rng.randint(1, 2) for _ in range(n)], dtype="Int64")
    sub["P7280"] = pd.array(p7280_values, dtype="Int64")
    sub["P5090"] = pd.array([rng.randint(1, 7) for _ in range(n)], dtype="Int64")

    return sub.reset_index(drop=True)


def build_unified_fixture_zip(dest: Path, seed: int = 42) -> None:
    """Generate the synthetic Shape B (unified) fixture ZIP at `dest`.

    N=50 persons: first 30 → ocupados (OCI=1), last 20 → no_ocupados
    (DSI=1 for 6 desocupados, DSI=NaN for 14 inactivos).

    All three modules share the same DIRECTORIO/SECUENCIA_P/ORDEN keys so
    outer joins for condicion_actividad produce exactly 50 rows.

    Idempotent: running twice with the same seed produces the same file.
    """
    rng = random.Random(seed)
    dest.parent.mkdir(parents=True, exist_ok=True)

    N = 50
    carac = _make_unified_caracteristicas(rng, N)
    ocup = _make_unified_ocupados(rng, carac.iloc[:30])
    no_ocup = _make_unified_no_ocupados(rng, carac.iloc[30:])

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(UNIFIED_INNER_PATHS["ocupados"], _df_to_bytes(ocup))
        zf.writestr(UNIFIED_INNER_PATHS["no_ocupados"], _df_to_bytes(no_ocup))
        zf.writestr(UNIFIED_INNER_PATHS["caracteristicas_generales"], _df_to_bytes(carac))

    print(f"Written: {dest}  ({dest.stat().st_size:,} bytes)")


SHAPE_A_GEIH1_ZIP_NAME = "geih1_shape_a_sample.zip"

# Canonical module filenames used by build_shape_a_zip (mimic real DANE GEIH-1 naming).
_SHAPE_A_MODULES = {
    "caracteristicas_generales": "Características generales (Personas)",
    "ocupados": "Ocupados",
    "desocupados": "Desocupados",
    "inactivos": "Inactivos",
}


def _make_shape_a_carac(directorios: list[int]) -> pd.DataFrame:
    rows = [
        {
            "DIRECTORIO": f"{d:04d}",
            "SECUENCIA_P": 1,
            "ORDEN": 1,
            "P6020": 1 if d % 2 == 0 else 2,
            "P6040": 20 + d,
            "FEX_C18": float(1000 + d * 10),
        }
        for d in directorios
    ]
    return pd.DataFrame(rows)


def _make_shape_a_simple(directorios: list[int]) -> pd.DataFrame:
    """Minimal persona table — merge keys only."""
    rows = [{"DIRECTORIO": f"{d:04d}", "SECUENCIA_P": 1, "ORDEN": 1} for d in directorios]
    return pd.DataFrame(rows)


def build_shape_a_zip(
    output_path: Path,
    year: int = 2015,
    month: int = 6,
    folder_name: str = "Junio.csv",
    n_cabecera: int = 3,
    n_resto: int = 2,
) -> Path:
    """Create a synthetic GEIH-1 Shape A ZIP for testing.

    Produces 4 modules x 2 areas (Cabecera + Resto) = 8 CSVs inside a single
    ZIP, reproducing the structure of real DANE GEIH-1 microdata files.

    Args:
        output_path: Destination path for the ZIP.
        year: Nominal year (affects only the folder name indirectly).
        month: Nominal month (not embedded in this fixture).
        folder_name: Top-level folder inside the ZIP (varies across years).
        n_cabecera: Number of Cabecera rows to generate.
        n_resto: Number of Resto rows to generate.

    Returns:
        output_path (for convenience chaining).
    """
    cab_ids = list(range(1, n_cabecera + 1))
    resto_ids = list(range(n_cabecera + 1, n_cabecera + n_resto + 1))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for mod_key, label in _SHAPE_A_MODULES.items():
            if mod_key == "caracteristicas_generales":
                df_cab = _make_shape_a_carac(cab_ids)
                df_resto = _make_shape_a_carac(resto_ids)
            else:
                df_cab = _make_shape_a_simple(cab_ids)
                df_resto = _make_shape_a_simple(resto_ids)

            zf.writestr(
                f"{folder_name}/Cabecera - {label}.csv",
                _df_to_bytes(df_cab),
            )
            zf.writestr(
                f"{folder_name}/Resto - {label}.csv",
                _df_to_bytes(df_resto),
            )

    return output_path


if __name__ == "__main__":
    build_fixture_zip(FIXTURE_DIR / ZIP_NAME)
    build_unified_fixture_zip(FIXTURE_DIR / UNIFIED_ZIP_NAME)
    build_shape_a_zip(FIXTURE_DIR / SHAPE_A_GEIH1_ZIP_NAME)
