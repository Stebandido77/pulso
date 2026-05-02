# pulso

> **El pulso del mercado laboral colombiano.**  
> *Python library to load GEIH microdata from Colombia's DANE.*

[![CI](https://github.com/Stebandido77/pulso/actions/workflows/ci.yml/badge.svg)](https://github.com/Stebandido77/pulso/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/pulso.svg)](https://pypi.org/project/pulso/)
[![Python](https://img.shields.io/pypi/pyversions/pulso.svg)](https://pypi.org/project/pulso/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

[**Español**](#español) | [**English**](#english)

---

<a id="español"></a>

## 🇨🇴 Español

### ¿Qué es `pulso`?

`pulso` es una librería de Python que da acceso directo a la **Gran Encuesta Integrada de Hogares (GEIH)** — la encuesta mensual de hogares que publica el DANE de Colombia. Sin descargas manuales, sin lidiar con ZIPs, sin problemas de codificación.

Tres cosas que hace:

- **Descarga** — obtiene el ZIP oficial del portal de microdatos del DANE, lo cachea localmente y verifica SHA-256.
- **Parsea** — maneja tres formatos estructurales (Shape A: archivos Cabecera/Resto para 2006–2021; Shape B: archivo unificado nacional para 2022–presente; Shape C: ZIPs anuales Empalme).
- **Armoniza** — mapea los códigos de columna crudos del DANE (`P6020`, `FEX_C18`, …) a variables canónicas nombradas (`sexo`, `peso_expansion`, …) de forma consistente entre épocas metodológicas.

```python
import pulso

# Cargar un módulo, un mes
df = pulso.load(year=2024, month=6, module="ocupados")

# Serie temporal
df = pulso.load(year=range(2018, 2025), month=6, module="ocupados")

# Merge entre módulos
df = pulso.load_merged(year=2024, month=6,
                       modules=["ocupados", "caracteristicas_generales"])

# Carga con empalme entre épocas (2010–2019)
df = pulso.load_merged(year=2015, month=6, apply_smoothing=True)

# Dataset anual del Empalme GEIH
df_empalme = pulso.load_empalme(year=2015, harmonize=True)
```

### Cobertura

| Atributo | Detalle |
|----------|---------|
| **Período** | 2006-01 al presente (último mes publicado por el DANE) |
| **Cobertura geográfica** | Nacional: cabecera (urbano) + resto (rural), 23 ciudades y áreas metropolitanas |
| **Módulos** | `caracteristicas_generales`, `ocupados`, `desocupados`, `inactivos`, `vivienda_hogares`, `otros_ingresos`, `migracion`\*, `otras_formas_trabajo`\* |
| **Meses validados** | 2007-12, 2015-06, 2021-12, 2022-01, 2024-06 (end-to-end con datos reales del DANE) |
| **Entradas en el registro** | ~230 meses (2006-01 → 2026-02) |

\* Disponibles solo en la época `geih_2021_present` (desde 2022-01).

> **Fuera del alcance:** La Encuesta Continua de Hogares (ECH, 2000–2005) no está incluida. La ECH usa un marco muestral, definiciones y cobertura geográfica distintos; mezclarla con la GEIH bajo una API armonizada sería engañoso.

### Épocas metodológicas

El DANE cambió significativamente la metodología de la GEIH en 2022. `pulso` modela esto como dos épocas:

| Clave de época | Período | Marco muestral | Variable de expansión |
|----------------|---------|----------------|----------------------|
| `geih_2006_2020` | 2006-01 → 2021-12 | Censo 2005 | `FEX_C` |
| `geih_2021_present` | **2022-01** → presente | Censo 2018 (post-OIT) | `FEX_C18` |

> ⚠️ El cambio de época está en **2022-01**, no en 2021. Las estimaciones que cruzan este límite llevan una advertencia de comparabilidad documentada.

### Empalme entre épocas

El DANE publica la serie **GEIH Empalme** (2010–2020) — ZIPs anuales que re-estiman los microdatos mensuales bajo el marco unificado del Censo 2005. Es la herramienta estándar para construir series de tiempo consistentes antes del rediseño de 2022.

`pulso` expone dos formas de usarlo:

```python
# Intercambio transparente: carga 2015-06 con datos Empalme en vez de GEIH cruda
df = pulso.load_merged(year=2015, month=6, harmonize=True, apply_smoothing=True)

# Acceso directo: los 12 meses del Empalme 2015 apilados
df_empalme = pulso.load_empalme(year=2015, module="ocupados", harmonize=True)
```

Los ZIPs del Empalme se cachean en `empalme/{year}.zip`.  
El año 2020 existe en el catálogo del DANE pero el ZIP no ha sido publicado; `load_empalme(2020)` lanza `DataNotAvailableError`.

### Instalación

```bash
pip install pulso
```

### Quickstart

```python
import pulso

# 1. Ver qué hay disponible
disponible = pulso.list_available()              # todos los meses
disponible_2024 = pulso.list_available(year=2024)

# 2. Listar módulos canónicos
pulso.list_modules()

# 3. Cargar un módulo
df = pulso.load(year=2024, month=6, module="caracteristicas_generales", area="total")

# 4. Merge entre módulos con armonización
df = pulso.load_merged(
    year=2024, month=6,
    modules=["ocupados", "caracteristicas_generales"],
    harmonize=True,
)

# 5. Aplicar factores de expansión (decisión consciente, no automática)
df_expandido = pulso.expand(df, weight="peso_expansion")
```

### API pública

| Función | Estado | Descripción |
|---------|--------|-------------|
| `load(year, month, module, ...)` | ✅ estable | Carga un módulo para uno o más períodos |
| `load_merged(year, month, modules, ..., apply_smoothing)` | ✅ estable | Carga y merge de módulos; intercambio Empalme opcional |
| `load_empalme(year, module, area, harmonize)` | ✅ estable | Carga el dataset anual GEIH Empalme (2010–2019) |
| `expand(df, weight)` | ✅ estable | Aplica factores de expansión fila a fila |
| `list_available(year)` | ✅ estable | DataFrame de pares (año, mes) disponibles |
| `list_modules()` | ✅ estable | DataFrame de definiciones de módulos canónicos |
| `cache_info()` | ✅ estable | Resumen de tamaño y estructura del caché |
| `cache_clear(level)` | ✅ estable | Limpia raw / parsed / harmonized / todo |
| `cache_path()` | ✅ estable | Ruta absoluta al directorio de caché |
| `data_version()` | ✅ estable | Versión del registro de datos (ej. `"2026.04"`) |
| `list_variables()` | 🚧 planeada | Listar variables armonizadas canónicas |
| `describe_variable(name)` | 🚧 planeada | Definición + notas de comparabilidad |
| `describe_harmonization(variable)` | 🚧 planeada | Detalle del mapeo por época |
| `describe(module, year)` | 🚧 planeada | Metadatos del módulo + info de época |

### Caché local

Los microdatos descargados se guardan en el directorio predeterminado de la plataforma (gestionado por `platformdirs`):

| SO | Ruta de caché por defecto |
|----|--------------------------|
| Linux / macOS | `~/.cache/pulso/` |
| Windows | `%LOCALAPPDATA%\pulso\pulso\Cache\` |

Estructura:

```
<raíz_caché>/
├── raw/{year}/{month:02d}/{checksum_short}.zip    # ZIP original del DANE
├── empalme/{year}.zip                             # ZIPs anuales Empalme
├── parsed/{year}/{month:02d}/{module}.parquet     # post-parser (futuro)
└── harmonized/{year}/{month:02d}/{module}.parquet # post-armonización (futuro)
```

Inspeccionar y gestionar:

```python
pulso.cache_info()                    # tamaño, conteo de archivos, por nivel
pulso.cache_path()                    # ruta absoluta
pulso.cache_clear(level="raw")        # limpiar un nivel
pulso.cache_clear(level="all")        # borrar todo
```

### Caveats importantes

Antes de usar los resultados en una publicación, lee [`docs/caveats.md`](docs/caveats.md):

1. **La armonización no elimina las discontinuidades metodológicas reales del DANE.** El rediseño de 2022 cambió definiciones, marco muestral y cobertura geográfica. Trata las comparaciones entre épocas (especialmente antes/después de 2022) con cuidado.
2. **`expand()` ignora el diseño muestral.** Sumar pesos expandidos con `groupby().sum()` produce estimaciones puntuales pero no errores estándar correctos. Para inferencia rigurosa usa un paquete de análisis de encuestas (ej. `samplics`).
3. **No es un producto oficial del DANE.** Para uso oficial, consulta el portal de microdatos: <https://microdatos.dane.gov.co/>

### Por qué `pulso` y no `geih`

`pulso` es el nombre del paquete; `GEIH` es la encuesta que carga hoy. La distinción importa: si en el futuro se agregan otras encuestas del DANE (ej. ENPH, ECV), pueden vivir en sub-namespaces (`pulso.enph`, `pulso.ecv`) sin romper el namespace raíz. Hoy, `pulso.load(...)` siempre carga GEIH.

### Estado del proyecto

Versión actual: **v1.0.0-rc1** (release candidate). Disponible en [TestPyPI](https://test.pypi.org/project/pulso/).

| Fase | Descripción | Estado |
|------|-------------|--------|
| 0 | Andamiaje | ✅ |
| 1 | Vertical slice — un mes | ✅ |
| 2 | Harmonizer y merger | ✅ |
| 3 | Cobertura GEIH completa (2006–presente) | ✅ |
| 3.5 | Empalme loader + apply_smoothing | ✅ |
| 4 | Deuda técnica + normalización Shape A | ✅ |
| 5 | Release en PyPI | 🚧 |

Ver [`CHANGELOG.md`](CHANGELOG.md) para más detalles.

### Contribuir

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md). Especialmente útil si:

- Quieres reportar un mes que falla al cargar
- Quieres proponer una nueva variable armonizada
- Encuentras una discrepancia con estadísticas oficiales del DANE

### Citación

Si usas este paquete en una publicación, cita el DANE como fuente primaria de los datos, y opcionalmente este paquete como herramienta:

```text
DANE (2024). Gran Encuesta Integrada de Hogares (GEIH).
  Departamento Administrativo Nacional de Estadística.
  https://microdatos.dane.gov.co/

Labastidas, E. (2026). pulso: Python library to load GEIH microdata from Colombia's DANE.
  https://github.com/Stebandido77/pulso
```

### Licencia

El código está bajo licencia MIT (ver [`LICENSE`](LICENSE)). Los microdatos descargados son propiedad del DANE y se rigen por los términos de uso del portal de microdatos.

---

<a id="english"></a>

## 🇬🇧 English

### What is pulso?

`pulso` is a Python library that gives you single-line access to Colombia's **Gran Encuesta Integrada de Hogares (GEIH)** — the monthly household survey published by DANE, the national statistics office. No manual downloads, no ZIP wrangling, no encoding headaches.

Three things it does:

- **Download** — fetches the official ZIP from DANE's microdata portal, caches it locally, verifies SHA-256.
- **Parse** — handles three structural formats (Shape A: Cabecera/Resto split for 2006–2021; Shape B: unified nationwide file for 2022–present; Shape C: Empalme annual ZIPs).
- **Harmonize** — maps raw DANE column codes (`P6020`, `FEX_C18`, …) to named canonical variables (`sexo`, `peso_expansion`, …) consistently across methodological epochs.

```python
import pulso

# Load one module, one month
df = pulso.load(year=2024, month=6, module="ocupados")

# Time series across years
df = pulso.load(year=range(2018, 2025), month=6, module="ocupados")

# Multi-module merge
df = pulso.load_merged(year=2024, month=6,
                       modules=["ocupados", "caracteristicas_generales"])

# Epoch-smoothed load using GEIH Empalme (2010–2019)
df = pulso.load_merged(year=2015, month=6, apply_smoothing=True)

# Load the full Empalme annual dataset
df_empalme = pulso.load_empalme(year=2015, harmonize=True)
```

### Coverage

| Attribute | Detail |
|-----------|--------|
| **Period** | 2006-01 to present (latest month published by DANE) |
| **Geography** | National: cabecera (urban) + resto (rural), 23 cities and metro areas |
| **Modules** | `caracteristicas_generales`, `ocupados`, `desocupados`, `inactivos`, `vivienda_hogares`, `otros_ingresos`, `migracion`\*, `otras_formas_trabajo`\* |
| **Validated months** | 2007-12, 2015-06, 2021-12, 2022-01, 2024-06 (end-to-end with real DANE data) |
| **Registry entries** | ~230 monthly entries (2006-01 → 2026-02) |

\* Available only in `geih_2021_present` epoch (2022-01 onward).

> **Out of scope:** The Encuesta Continua de Hogares (ECH, 2000–2005) is not included. ECH uses a different sampling frame, definitions, and coverage; merging it with GEIH under a single harmonized API would be misleading.

### Methodological epochs

DANE changed the GEIH methodology significantly in 2022. `pulso` models this as two epochs:

| Epoch key | Period | Sampling frame | Weight variable |
|-----------|--------|----------------|-----------------|
| `geih_2006_2020` | 2006-01 → 2021-12 | 2005 census | `FEX_C` |
| `geih_2021_present` | **2022-01** → present | 2018 census (post-ILO) | `FEX_C18` |

> ⚠️ The epoch boundary is **2022-01**, not 2021. Estimates that span this boundary carry a documented comparability warning.

### Smoothing across the epoch boundary (Empalme)

DANE publishes the **GEIH Empalme** series (2010–2020) — annual ZIPs that re-estimate monthly microdata under the unified 2005-census framework. This is the standard tool for constructing consistent multi-year time series before the 2022 redesign.

`pulso` exposes two ways to use it:

```python
# Transparent swap: load 2015-06 using Empalme data instead of raw GEIH
df = pulso.load_merged(year=2015, month=6, harmonize=True, apply_smoothing=True)

# Direct access: all 12 months of Empalme 2015 stacked
df = pulso.load_empalme(year=2015, module="ocupados", harmonize=True)
```

Empalme ZIPs are cached separately under `empalme/{year}.zip`.  
Year 2020 exists in DANE's catalog but the ZIP has not been published; `load_empalme(2020)` raises `DataNotAvailableError`.

### Installation

```bash
pip install pulso
```

### Quickstart

```python
import pulso

# 1. See what's available
available = pulso.list_available()          # all months
available_2024 = pulso.list_available(year=2024)

# 2. List canonical modules
pulso.list_modules()

# 3. Load a single module
df = pulso.load(year=2024, month=6, module="caracteristicas_generales", area="total")

# 4. Multi-module merge with harmonization
df = pulso.load_merged(
    year=2024, month=6,
    modules=["ocupados", "caracteristicas_generales"],
    harmonize=True,
)

# 5. Apply expansion factors (conscious choice — not automatic)
df_expanded = pulso.expand(df, weight="peso_expansion")
```

### Public API

| Function | Status | Description |
|----------|--------|-------------|
| `load(year, month, module, ...)` | ✅ stable | Load one module for one or more periods |
| `load_merged(year, month, modules, ..., apply_smoothing)` | ✅ stable | Load + merge multiple modules; optional Empalme swap |
| `load_empalme(year, module, area, harmonize)` | ✅ stable | Load GEIH Empalme annual dataset (2010–2019) |
| `expand(df, weight)` | ✅ stable | Apply expansion factors row-by-row |
| `list_available(year)` | ✅ stable | DataFrame of available (year, month) pairs |
| `list_modules()` | ✅ stable | DataFrame of canonical module definitions |
| `cache_info()` | ✅ stable | Cache size and layout summary |
| `cache_clear(level)` | ✅ stable | Clear raw / parsed / harmonized / all |
| `cache_path()` | ✅ stable | Absolute path to cache root |
| `data_version()` | ✅ stable | Registry data version (e.g. `"2026.04"`) |
| `list_variables()` | 🚧 planned | List canonical harmonized variables |
| `describe_variable(name)` | 🚧 planned | Variable definition + comparability notes |
| `describe_harmonization(variable)` | 🚧 planned | Per-epoch mapping details |
| `describe(module, year)` | 🚧 planned | Module metadata + epoch info |

### Local cache

Downloaded microdata is cached under the platform default directory (managed by `platformdirs`):

| OS | Default cache path |
|----|--------------------|
| Linux / macOS | `~/.cache/pulso/` |
| Windows | `%LOCALAPPDATA%\pulso\pulso\Cache\` |

Layout:

```
<cache_root>/
├── raw/{year}/{month:02d}/{checksum_short}.zip    # original DANE ZIP
├── empalme/{year}.zip                             # Empalme annual ZIPs
├── parsed/{year}/{month:02d}/{module}.parquet     # post-parser (future)
└── harmonized/{year}/{month:02d}/{module}.parquet # post-harmonize (future)
```

Inspect and manage:

```python
pulso.cache_info()                    # size, file count, by level
pulso.cache_path()                    # absolute path
pulso.cache_clear(level="raw")        # clear one level
pulso.cache_clear(level="all")        # clear everything
```

### Important caveats

Before using results in a publication, please read [`docs/caveats.md`](docs/caveats.md):

1. **Harmonization does not remove real DANE discontinuities.** The 2022 redesign changed definitions, sampling frame, and geographic coverage. Treat cross-epoch comparisons (especially pre/post 2022) with care.
2. **`expand()` ignores sampling design.** Summing expanded weights with `groupby().sum()` yields point estimates but no correct standard errors. For rigorous inference, use a survey analysis package (e.g. `samplics`).
3. **Not an official DANE product.** For official use, refer to DANE's microdata portal: <https://microdatos.dane.gov.co/>

### Why "pulso" and not "geih"

`pulso` is the package name; `GEIH` is the survey it loads today. The distinction matters: if future versions add other DANE surveys (e.g. ENPH, ECV), they can live in sub-namespaces (`pulso.enph`, `pulso.ecv`) without breaking the root namespace. For now, `pulso.load(...)` always loads GEIH.

### Status

Current version: **v1.0.0-rc1** (release candidate). Available on [TestPyPI](https://test.pypi.org/project/pulso/).

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Scaffolding | ✅ |
| 1 | Vertical slice — single month | ✅ |
| 2 | Harmonizer and merger | ✅ |
| 3 | Full GEIH coverage (2006–present) | ✅ |
| 3.5 | Empalme loader + smoothing | ✅ |
| 4 | Technical debt + Shape A normalization | ✅ |
| 5 | PyPI release | 🚧 |

See [`CHANGELOG.md`](CHANGELOG.md) for details.

### Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Especially welcome:

- Reporting a month that fails to load
- Proposing a new harmonized variable
- Finding a discrepancy with official DANE statistics

### Citation

If you use this package in a publication, cite DANE as the primary data source, and optionally this package as the tool:

```text
DANE (2024). Gran Encuesta Integrada de Hogares (GEIH).
  Departamento Administrativo Nacional de Estadística.
  https://microdatos.dane.gov.co/

Labastidas, E. (2026). pulso: Python library to load GEIH microdata from Colombia's DANE.
  https://github.com/Stebandido77/pulso
```

### License

Code is MIT-licensed (see [`LICENSE`](LICENSE)). Downloaded microdata belongs to DANE and is governed by the terms of use of the microdata portal.

---

## Créditos

`pulso` fue creado por **Esteban Labastidas** ([@Stebandido77](https://github.com/Stebandido77)).

El paquete fue construido usando un sistema multi-agente de codificación basado en Claude (Anthropic), diseñado y dirigido por el autor:

- **Architect** (Claude Opus, chat): diseño arquitectónico, RFCs, revisión y coordinación de PRs
- **Builder** (Claude Code): implementación de código en `pulso/_core/`
- **Curator** (Claude Code): gestión del catálogo de datos en `pulso/data/`

La arquitectura del sistema multi-agente, las decisiones técnicas y el diseño del paquete son obra del autor. Los agentes ejecutan implementación bajo supervisión y dirección humana directa.

Ver [`docs/architecture.md`](docs/architecture.md) sección 6 para detalles del modelo de construcción.

---

## Credits

`pulso` was created by **Esteban Labastidas** ([@Stebandido77](https://github.com/Stebandido77)).

The package was built using a Claude-based (Anthropic) multi-agent coding system, designed and directed by the author:

- **Architect** (Claude Opus, chat): architectural design, RFCs, PR review and coordination
- **Builder** (Claude Code): code implementation in `pulso/_core/`
- **Curator** (Claude Code): data catalog management in `pulso/data/`

The multi-agent system architecture, technical decisions, and package design are the author's work. The agents execute implementation under direct human supervision and direction.

See [`docs/architecture.md`](docs/architecture.md) section 6 for build model details.
