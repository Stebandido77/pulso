# Anatomía del DDI XML del DANE

**Sample principal:** `samples/geih_2024_ddi.xml` (1.8 MB, 760 vars)
**Sample secundario:** `samples/geih_2018_ddi.xml` (4.5 MB, 1302 vars)
**Fecha inspección:** 2026-05-03

## Notas sobre los zips de microdata

El zip de microdata **no se descargó** porque H1 quedó refutado en
fase 2: no existe zip anual. La estructura interna de los zips
mensuales ya está cubierta por la implementación rc2 de pulso (el
`MonthlyLoader` actual). No tiene sentido replicar esa inspección
aquí.

Lo que importa para v1.0.0 metadata es el DDI XML.

## DDI 1.2.2 — estructura

Namespace y root:

```xml
<?xml version='1.0' encoding='UTF-8'?>
<codeBook
    version="1.2.2"
    ID="DANE-DIMPE-GEIH-2024"
    xml-lang="es"
    xmlns="http://www.icpsr.umich.edu/DDI"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="...DDI/Version1-2-2.xsd">
  <docDscr>...</docDscr>
  <stdyDscr>...</stdyDscr>
  <fileDscr ID="F63">...</fileDscr>
  ...
  <dataDscr>
    <var ID="V3990" name="P3271" files="F63">...</var>
    ...
  </dataDscr>
</codeBook>
```

## Las secciones que importan

### `<dataDscr>` — el codebook

Hijo más importante. Contiene una `<var>` por cada variable.

### `<var>` — esquema verificado

```xml
<var ID="V3990" name="P3271" files="F63">
  <location StartPos="..." EndPos="..." width="1"/>
  <labl>Cuál fue su sexo al nacer?</labl>
  <varFormat type="numeric" schema="other"/>
  <respUnit>Persona</respUnit>
  <qstn>
    <qstnLit>Cuál fue su sexo al nacer?</qstnLit>
  </qstn>
  <universe>Todas las personas</universe>
  <sumStat type="vald">...</sumStat>
  <sumStat type="invd">...</sumStat>
  <sumStat type="min">1</sumStat>
  <sumStat type="max">2</sumStat>
  <catgry>
    <catValu>1</catValu>
    <labl>Hombre</labl>
  </catgry>
  <catgry>
    <catValu>2</catValu>
    <labl>Mujer</labl>
  </catgry>
  <security>Confidencial / Confidential</security>
</var>
```

### Atributos garantizados

- `ID` — id interno DANE (no estable entre años, no usar)
- `name` — código de la variable (`P6020`, `P3271`, etc.) — **éste sí
  es estable** y es el que pulso ya usa
- `files` — file ID al que pertenece (no estable entre años)

### Hijos garantizados (presentes en 100% de las muestras inspeccionadas)

- `<location>` — posiciones byte
- `<labl>` — etiqueta humana corta
- `<varFormat type="numeric|character">` — tipo

### Hijos frecuentes (presentes en la mayoría)

- `<qstn><qstnLit>` — texto literal de la pregunta
- `<universe>` — universo (a quién se aplica)
- `<respUnit>` — unidad de respuesta
- `<sumStat>` — estadísticas resumen (vald, invd, min, max, mean, etc.)
- `<security>` — clasificación de confidencialidad
- `<catgry>` — una por cada categoría/código (solo en variables
  categóricas; ausente en numéricas continuas)

## Mapping para pulso

`parse_ddi(path) -> dict[str, VariableInfo]`:

```python
@dataclass
class VariableInfo:
    name: str            # = <var name="...">
    label: str           # = <var><labl>
    question: str | None # = <var><qstn><qstnLit>
    universe: str | None
    response_unit: str | None
    file_id: str         # = <var files="..."> (informativo, no estable)
    var_type: str        # numeric | character
    categories: dict[str, str] | None  # {catValu: labl}
```

`variable_map.json` empaquetable:

```json
{
  "epoch_b": {
    "P6020": {
      "label": "Sexo",
      "question": "Cuál fue su sexo al nacer?",
      "categories": {"1": "Hombre", "2": "Mujer"}
    },
    ...
  },
  "epoch_a": { ... }
}
```

## Tamaños observados

| Año | Tamaño DDI | Variables |
|----:|-----------:|----------:|
| 2024 | 1.8 MB | 760 |
| 2018 | 4.5 MB | 1302 |
| 2008 | >10 MB | (no medido — WebFetch cap) |

**Implicación:** descarga por streaming en producción (`requests.iter_content`
o `httpx.stream`). No descargar todo en memoria con `requests.get(url).content`
para los años pre-2015.

## Validación con `lxml`

El XML pasa validación con namespace correcto:

```python
from lxml import etree
NS = {"ddi": "http://www.icpsr.umich.edu/DDI"}
tree = etree.parse("samples/geih_2024_ddi.xml")
vars_ = tree.findall(".//ddi:var", namespaces=NS)
assert len(vars_) == 760  # confirmado
for var in vars_[:5]:
    name = var.get("name")
    label = var.find("ddi:labl", namespaces=NS).text
    cats = var.findall("ddi:catgry", namespaces=NS)
    print(f"{name}: {label} ({len(cats)} categorías)")
```

(Snippet de referencia, no se ejecutó en este fase porque está fuera
del scope no-code.)

## Curiosidades del DDI del DANE

1. **`<titl>` ruidoso.** En 2024 dice "GRAN ENCUESTA INTEGRADA DE
   HOGARES 2016 metodologia". DANE reusa títulos. Usar `<IDNo>` o el
   `catalog_id`.
2. **Ningún PDF necesario.** Todo lo que un PDF "Diccionario de datos"
   contiene está en el DDI XML.
3. **El JSON export está incompleto.** `/metadata/export/{id}/json`
   trae metadata del estudio (productor, fechas, descripción) pero
   **no trae variables**. Es inútil para el variable_map. Usar SOLO el DDI XML.
4. **El XLSX "Diccionario de datos" (2024+)** es redundante respecto al
   DDI XML — la información se solapa, el XML está más estructurado.
   No invertir en parser XLSX.
