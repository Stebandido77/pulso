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


# ---------------------------------------------------------------------------
# Phase 3.3: sources.json entry fixture builder
# ---------------------------------------------------------------------------

_HOGAR_MODULES = {"vivienda_hogares"}


def _fixture_personas_df(module_name: str, directorios: list[int]) -> pd.DataFrame:
    """Persona-level DataFrame with source columns needed by variable_map.json transforms.

    Includes columns for both GEIH-1 and GEIH-2 epochs so the same fixture
    can drive harmonization tests across epochs.
    """
    n = len(directorios)
    data: dict[str, object] = {
        # Merge keys (persona level)
        "DIRECTORIO": [str(d) for d in directorios],
        "SECUENCIA_P": [1] * n,
        "ORDEN": [1] * n,
        "HOGAR": [1] * n,
        # Area / expansion (both epochs)
        "CLASE": [1] * n,
        "FEX_C18": [1000.0] * n,
        "fex_c_2011": [1000.0] * n,
        # Demographics (both epochs)
        "P6020": ([1, 2] * 10)[:n],  # sexo GEIH-1
        "P3271": ([1, 2] * 10)[:n],  # sexo GEIH-2
        "P6040": ([25, 30, 35, 40, 45] * 10)[:n],  # edad
        "P6050": [1] * n,  # parentesco GEIH-2
        "P6051": [1] * n,  # parentesco GEIH-1
        "P6070": [1] * n,  # estado_civil
        "P6080": [1] * n,  # grupo_etnico
        "DPTO": ["11"] * n,  # departamento (Bogotá)
        # Education (both epochs)
        "P6210": [1] * n,  # educ_max GEIH-1 (valid: 1-9)
        "P3042": [1] * n,  # educ_max GEIH-2 (valid: 1-13)
        "P6210S1": [3] * n,  # anios_educ GEIH-1
        "P3042S1": [3] * n,  # anios_educ GEIH-2
        "P6170": [1] * n,  # asiste_educ
        "P6160": [1] * n,  # alfabetiza
    }

    if module_name == "caracteristicas_generales":
        # OCI for condicion_actividad in GEIH-1 (1=ocupado, 2=desocupado, 3=inactivo)
        data["OCI"] = ([1, 2, 3, 1, 2] * 10)[:n]

    elif module_name == "ocupados":
        data.update(
            {
                "OCI": [1] * n,
                "P6430": [1] * n,  # posicion_ocupacional (valid: 1-9)
                "RAMA2D": ["10"] * n,  # rama_actividad GEIH-1
                "RAMA2D_R4": ["10"] * n,  # rama_actividad GEIH-2
                "OFICIO": ["1111"] * n,  # ocupacion GEIH-1
                "OFICIO_C8": ["1111"] * n,  # ocupacion GEIH-2
                "P6800": [40] * n,  # horas_trabajadas_sem
                "INGLABO": [1_000_000.0] * n,  # ingreso_laboral
                "P6440": [1] * n,  # tiene_contrato
                "P6450": [1] * n,  # tipo_contrato (valid: 1-4, 9)
                "P6920": [1] * n,  # cotiza_pension
            }
        )

    elif module_name in ("desocupados", "inactivos"):
        # Shared "No ocupados" file: include columns for both modules
        data.update(
            {
                "DSI": ([1, None, 1, None, 1] * 10)[:n],  # busco_trabajo GEIH-2
                "DSCY": ([1, 2, 1, 2, 1] * 10)[:n],  # tipo_desocupacion GEIH-2
                "P7430": ([1, 2, 1, 2, 1] * 10)[:n],  # tipo_inactividad GEIH-2
                "P7280": ([1, 2, 1, 2, 1] * 10)[:n],  # disponible GEIH-2
                # GEIH-1 columns
                "P6240": ([1, 2, 1, 2, 1] * 10)[:n],  # busco_trabajo GEIH-1
                "P7240": ([1, 2, 1, 2, 1] * 10)[:n],  # tipo_desocupacion GEIH-1
                "P7290": ([1, 2, 1, 2, 1] * 10)[:n],  # disponible GEIH-1
                "P7160": [1] * n,  # tipo_inactividad GEIH-1
            }
        )

    elif module_name == "otros_ingresos":
        data.update(
            {
                "INGTOT": [1_500_000.0] * n,  # ingreso_total GEIH-1
                "INGLABO": [1_000_000.0] * n,
                "P7500S1A1": [0.0] * n,  # income components GEIH-2
                "P7500S2A1": [0.0] * n,
                "P7500S3A1": [0.0] * n,
                "P750S1A1": [0.0] * n,
                "P750S2A1": [0.0] * n,
                "P750S3A1": [0.0] * n,
            }
        )

    # migracion, otras_formas_trabajo: only core columns (no extra canonical vars)

    return pd.DataFrame(data)


def _fixture_hogar_df(directorios: list[int]) -> pd.DataFrame:
    """Hogar-level DataFrame. ORDEN is intentionally absent so the merger detects hogar level."""
    n = len(directorios)
    return pd.DataFrame(
        {
            "DIRECTORIO": [str(d) for d in directorios],
            "SECUENCIA_P": [1] * n,
            "HOGAR": [1] * n,
            "P5090": [1] * n,  # vivienda_propia: value 1 → P5090 <= 2 → True
            "P5000": [3] * n,  # household size
        }
    )


def _df_bytes_latin1(df: pd.DataFrame) -> bytes:
    """Serialize DataFrame as latin-1 CSV (matches epoch encoding)."""
    buf = io.BytesIO()
    df.to_csv(buf, index=False, sep=";", decimal=",", encoding="latin-1")
    return buf.getvalue()


def build_fixture_from_sources_entry(
    entry: dict,
    output_path: Path,
    rows_per_file: int = 5,
) -> Path:
    """Build a synthetic ZIP that matches the structure declared in a sources.json entry.

    For Shape A entries, creates Cabecera/Resto pairs for each module.
    For Shape B entries, creates unified CSVs (shared files written once).

    Args:
        entry: A MonthRecord dict from sources.json (i.e., data["YYYY-MM"]).
        output_path: Where to write the ZIP.
        rows_per_file: Number of rows per CSV (kept small for test speed).

    Returns:
        Path to the created ZIP.
    """
    first_module = next(iter(entry["modules"].values()))
    is_shape_a = "cabecera" in first_module

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if is_shape_a:
            _write_shape_a_fixture(zf, entry["modules"], rows_per_file)
        else:
            _write_shape_b_fixture(zf, entry["modules"], rows_per_file)

    return output_path


def _write_shape_a_fixture(
    zf: zipfile.ZipFile,
    modules: dict,
    rows_per_file: int,
) -> None:
    """Write Cabecera + Resto CSV pairs for each module into the ZIP.

    Files are written in alphabetical path order so that the parser's
    last-match-wins keyword scan correctly resolves "Ocupados" over
    "Desocupados" (D < O alphabetically, so Ocupados is processed last
    and wins the final assignment).
    """
    cab_ids = list(range(1, rows_per_file + 1))
    resto_ids = list(range(rows_per_file + 1, 2 * rows_per_file + 1))

    # Build (path, bytes) pairs, then sort alphabetically before writing.
    entries: list[tuple[str, bytes]] = []

    for mod_name, mod_data in modules.items():
        cab_path = mod_data.get("cabecera")
        resto_path = mod_data.get("resto")

        if mod_name in _HOGAR_MODULES:
            cab_df = _fixture_hogar_df(cab_ids)
            resto_df = _fixture_hogar_df(resto_ids)
        else:
            cab_df = _fixture_personas_df(mod_name, cab_ids)
            resto_df = _fixture_personas_df(mod_name, resto_ids)

        if cab_path:
            entries.append((cab_path, _df_bytes_latin1(cab_df)))
        if resto_path:
            entries.append((resto_path, _df_bytes_latin1(resto_df)))

    for path, data in sorted(entries, key=lambda x: x[0].lower()):
        zf.writestr(path, data)


def _write_shape_b_fixture(
    zf: zipfile.ZipFile,
    modules: dict,
    rows_per_file: int,
) -> None:
    """Write one CSV per unique file path declared in the Shape B modules."""
    directorios = list(range(1, rows_per_file + 1))
    written: set[str] = set()

    for mod_name, mod_data in modules.items():
        file_path = mod_data.get("file")
        if not file_path or file_path in written:
            continue
        written.add(file_path)

        if mod_name in _HOGAR_MODULES:
            df = _fixture_hogar_df(directorios)
        else:
            df = _fixture_personas_df(mod_name, directorios)

        zf.writestr(file_path, _df_bytes_latin1(df))


if __name__ == "__main__":
    build_fixture_zip(FIXTURE_DIR / ZIP_NAME)
    build_unified_fixture_zip(FIXTURE_DIR / UNIFIED_ZIP_NAME)
    build_shape_a_zip(FIXTURE_DIR / SHAPE_A_GEIH1_ZIP_NAME)
