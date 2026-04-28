# pulso

> **El pulso del mercado laboral colombiano.**
> *Python library to load GEIH microdata from Colombia's DANE.*

[![CI](https://github.com/Stebandido77/pulso/actions/workflows/ci.yml/badge.svg)](https://github.com/Stebandido77/pulso/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/pulso.svg)](https://pypi.org/project/pulso/)
[![Python](https://img.shields.io/pypi/pyversions/pulso.svg)](https://pypi.org/project/pulso/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ¿Qué hace `pulso`?

Permite cargar microdatos mensuales de la **Gran Encuesta Integrada de Hogares (GEIH)** del DANE de Colombia directamente desde Python, con armonización de variables a través de épocas metodológicas, sin descargas manuales.

```python
import pulso

# Carga un módulo, un mes
df = pulso.load(year=2024, month=6, module="ocupados")

# Serie temporal de varios años
df = pulso.load(year=range(2018, 2025), month=6, module="ocupados")

# Merge automático entre módulos
df = pulso.load_merged(
    year=2024, month=6,
    modules=["ocupados", "caracteristicas_generales"]
)
```

## Cobertura

- **Periodo:** 2006-01 a presente (mes más reciente publicado por el DANE)
- **Cobertura geográfica:** cabecera + resto (urbano + rural), 23 ciudades + áreas metropolitanas
- **Módulos:** `caracteristicas_generales`, `ocupados`, `desocupados`, `inactivos`, `vivienda_hogares`, `otros_ingresos`

> **Nota sobre el alcance temporal:** este paquete *no* incluye la Encuesta Continua de Hogares (ECH, 2000-2005). La ECH usa marco muestral, definiciones operativas y cobertura geográfica diferentes; mezclarla con la GEIH bajo una API "armonizada" sería engañoso. Si necesitas ECH, consúltala con otra herramienta.

## Épocas metodológicas

La GEIH tiene dos épocas que `pulso` armoniza:

| Época | Periodo | Marco muestral | Variable de expansión |
|-------|---------|----------------|----------------------|
| `geih_2006_2020` | 2006-01 a 2020-12 | Censo 2005 | `fex_c_2011` |
| `geih_2021_present` | 2021-01 a presente | Censo 2018 (post-OIT) | `FEX_C18` |

Cuando usas `harmonize=True` (default), las variables se mapean a nombres canónicos consistentes a través de épocas. Variables con discontinuidad metodológica conocida llevan `comparability_warning` documentado en [`docs/harmonization.md`](docs/harmonization.md).

## Instalación

```bash
pip install pulso
```

Para soporte de archivos antiguos en formato SPSS o Stata (raro en GEIH, presente en algunos meses históricos):

```bash
pip install "pulso[legacy]"
```

## Quickstart

```python
import pulso

# 1. Ver qué hay disponible
pulso.list_available()                    # todos los meses
pulso.list_available(year=2024)           # solo 2024

# 2. Listar módulos
pulso.list_modules()

# 3. Listar variables armonizadas
pulso.list_variables()

# 4. Cargar datos
df = pulso.load(year=2024, month=6, module="ocupados", area="total")

# 5. Aplicar factores de expansión (decisión consciente)
df_expanded = pulso.expand(df)

# 6. Inspeccionar la armonización de una variable
pulso.describe_variable("ingreso_laboral_mensual")
pulso.describe_harmonization("ingreso_laboral_mensual")
```

Más ejemplos en [`docs/quickstart.md`](docs/quickstart.md) y [`docs/examples/`](docs/examples/).

## Caché local

Los microdatos descargados se guardan en `~/.pulso/`:

```
~/.pulso/
├── raw/{year}/{month}/{checksum}.zip       # ZIP original del DANE
├── parsed/{year}/{month}/{module}.parquet  # post-parser, pre-armonización
└── harmonized/{year}/{month}/{module}.parquet
```

Como los microdatos publicados son inmutables, la caché es eterna (invalidada solo por cambio de checksum). Gestiona con:

```python
pulso.cache_info()                         # tamaño, ubicación
pulso.cache_clear(level="harmonized")      # invalida solo armonizado
pulso.cache_clear(level="all")             # borra todo
```

## Caveats importantes

Antes de usar resultados de este paquete en una publicación, lee [`docs/caveats.md`](docs/caveats.md). En resumen:

1. La armonización entre épocas no elimina las discontinuidades metodológicas reales del DANE. Trata el cambio 2020→2021 con cuidado.
2. Los factores de expansión expandidos directamente con `df.groupby(...).sum()` ignoran el diseño muestral. Para inferencia rigurosa usa un paquete de análisis de encuestas (ej: `samplics`).
3. Este paquete *no* es un producto oficial del DANE. Para uso oficial, refiérete al portal de microdatos: https://microdatos.dane.gov.co/

## Por qué `pulso` y no `geih`

`pulso` es el nombre del paquete; `GEIH` es la encuesta que carga. La distinción importa: si en el futuro añadimos otras encuestas DANE (por ejemplo, ENPH, gran encuesta nacional de hogares previa), pueden vivir en sub-namespaces (`pulso.enph`, etc.) sin romper el namespace raíz. Hoy, `pulso.load(...)` siempre carga GEIH.

## Contribuir

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md). Especialmente útil si:
- Quieres reportar un mes que falla al cargar
- Quieres proponer una nueva variable armonizada
- Encuentras una discrepancia con estadísticas oficiales del DANE

## Citación

Si usas este paquete en una publicación, cita el DANE como fuente primaria de los datos, y opcionalmente este paquete como herramienta:

```
DANE (2024). Gran Encuesta Integrada de Hogares (GEIH).
  Departamento Administrativo Nacional de Estadística.
  https://microdatos.dane.gov.co/

pulso (2026). Python library to load GEIH microdata from Colombia's DANE.
  https://github.com/Stebandido77/pulso
```

## Licencia

Código bajo licencia MIT (ver [`LICENSE`](LICENSE)). Los microdatos descargados son propiedad del DANE y se rigen por los términos de uso del portal de microdatos.

---

## Estado del proyecto

🚧 En construcción. Ver [`CHANGELOG.md`](CHANGELOG.md) para versiones publicadas.

| Fase | Estado |
|------|--------|
| 0 — Andamiaje | ✅ |
| 1 — Vertical slice (un mes) | ⏳ |
| 2 — Harmonizer y merger | ⏳ |
| 3 — Cobertura GEIH-2 (2021-presente) | ⏳ |
| 4 — Cobertura GEIH-1 (2006-2020) | ⏳ |
| 5 — Scraper automático | ⏳ |
| 6 — Validación y release | ⏳ |
