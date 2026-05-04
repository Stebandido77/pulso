# Año en curso: GEIH-2026 (catalog ID 900)

**URL:** https://microdatos.dane.gov.co/index.php/catalog/900
**Fecha inspección:** 2026-05-03 (mayo de 2026)

## ¿Existe la ficha?

Sí. La ficha del año en curso está creada y operativa. No hay tab
"próximamente" / "pendiente" — DANE crea el catálogo y va publicando
los meses progresivamente.

## ¿Hay zip anual?

No. Como en años cerrados, **no hay zip anual** — solo mensuales.

## Meses publicados

Al 2026-05-03:

| Mes | Estado | Fecha de release DANE |
|-----|--------|-----------------------|
| Enero 2026 | publicado | 2026-03-16 |
| Febrero 2026 | publicado | 2026-04-13 |
| Marzo 2026 | NO publicado | — |
| Abril 2026 | NO publicado | — |
| Mayo–Diciembre | NO publicado | — |

**Lag típico:** ~6 semanas entre fin del mes de referencia y el release.
Es decir: un usuario que pida `pulso.load(2026, 3)` el 2026-05-03 debe
recibir `DataNotAvailableError` (DANE aún no lo publicó). Un usuario
que pida `pulso.load(2026, 5)` el mismo día también — pulso no debe
asumir disponibilidad por anticipado.

## URLs de descarga

Mismo patrón: `/catalog/900/download/{file_id}`. Los 2 meses publicados
ya están en `pulso/data/sources.json` rc2 (verificado).

## Diccionario

DDI XML disponible:
`https://microdatos.dane.gov.co/index.php/metadata/export/900/ddi`

El DDI XML tiene 8 file descriptors (`F1`–`F8`), reflejando los 8
archivos por mes de la Época B (2021+). Esto incluso antes de que el
año esté completo — el DDI describe la estructura esperada, no requiere
que los 12 meses estén publicados.

Adicionalmente DANE ya publicó el "Diccionario de datos" XLSX de 2026
de forma directa (347 KB) — es la primera vez que un año se publica
con XLSX directo (sin ZIP envolvente).

## Implicaciones para `pulso.load()`

- `load(year=2026, month=1)` → datos disponibles
- `load(year=2026, month=2)` → datos disponibles
- `load(year=2026, month=3)` → `DataNotAvailableError` (DANE no publicó)
- `load(year=2026)` (todo el año) → `DataNotAvailableError` o devolver
  parcial; **decisión pendiente del usuario** sobre el comportamiento
  por defecto. Recomendación: lanzar error + parámetro
  `partial=True` opt-in para devolver lo disponible.
- `load(year=2027)` → `DataNotAvailableError` (catalog ni siquiera existe)

## Confirma H4

✅ El año en curso publica mensualmente con un lag de ~6 semanas. Las
URLs son accesibles tan pronto como aparecen en el catálogo. No se
requiere lógica especial — el downloader mensual existente cubre el
caso si `sources.json` se mantiene actualizado.
