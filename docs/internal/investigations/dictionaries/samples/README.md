# Samples — DDI XML del DANE

Estos archivos fueron descargados durante la fase de discovery del
modelo metadata para pulso v1.0.0 (Agente 1, 2026-05-03).

| Archivo | Origen | Tamaño | Variables | Notas |
|---------|--------|-------:|----------:|-------|
| `geih_2024_ddi.xml` | https://microdatos.dane.gov.co/index.php/metadata/export/819/ddi | 1.8 MB | 760 | Año cerrado típico, época B (2021+) |
| `geih_2018_ddi.xml` | https://microdatos.dane.gov.co/index.php/metadata/export/547/ddi | 4.5 MB | 1302 | Época A (2006–2020), referencia para parser cross-época |

## Por qué están versionados

Son evidencia de hallazgo crítico (DDI XML estructurado existe). El
parser que se construya en v1.0.0 puede usarlos para tests sin pegarle
a la red del DANE en CI.

Si en algún momento estos archivos se vuelven obsoletos (DANE actualiza
el formato), eliminarlos del repo y volverlos a descargar de los
endpoints anotados arriba.

## Re-descarga

```bash
curl -o geih_2024_ddi.xml https://microdatos.dane.gov.co/index.php/metadata/export/819/ddi
curl -o geih_2018_ddi.xml https://microdatos.dane.gov.co/index.php/metadata/export/547/ddi
```

## Validación rápida

```python
from lxml import etree
NS = {"ddi": "http://www.icpsr.umich.edu/DDI"}
tree = etree.parse("geih_2024_ddi.xml")
print(len(tree.findall(".//ddi:var", namespaces=NS)))  # 760
```
