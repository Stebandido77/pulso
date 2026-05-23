# Python v1.0.0 Re-validacion

**Fecha:** 2026-05-23
**Version testeada:** 1.0.0 (PyPI)
**Version anterior:** 1.0.0rc1
**Tester:** Agente de testing automatizado

---

## BUG-001 status

**FIXED** — pulso.load(year=2025, month=6, module="ocupados", allow_unvalidated=True) retorna (29706, 213) sin excepcion. En rc1 este call lanzaba TypeError: NoneType not subscriptable en downloader.py:84 para cualquier periodo con checksum_sha256=null (~225 de 230 periodos en el registry).

Nota adicional: allow_unvalidated ahora emite un DeprecationWarning indicando que en v2.0.0 se usara strict=False. Behavior correcto.

---

## Periodos testeados (Test B)

5 periodos x 6 modulos = 30 combinaciones — PASS: 30/30 — FAIL: 0/30

| Periodo  | ocupados      | desocupados  | caract_gral   | vivienda_hog  | inactivos    | otros_ingresos |
|----------|---------------|--------------|---------------|---------------|--------------|----------------|
| 2007-06  | (26345,248) OK| (3944,49) OK | (66608,76) OK | (17537,59) OK | (21706,21) OK| (51994,32) OK  |
| 2018-06  | (29027,177) OK| (3238,47) OK | (62683,50) OK | (19009,65) OK | (19395,32) OK| (51660,50) OK  |
| 2019-06  | (28034,177) OK| (3578,47) OK | (62488,50) OK | (19150,65) OK | (19884,32) OK| (51496,50) OK  |
| 2022-06  | (32522,211) OK| (28114,44) OK| (77999,89) OK | (25822,52) OK | (28114,42) OK| (60636,62) OK  |
| 2024-06  | (29925,211) OK| (25605,43) OK| (70020,82) OK | (24373,52) OK | (25605,41) OK| (55530,62) OK  |

---

## Variables canonical (Test C)

- list_variables(): OK (30 variables). Primeras 5: sexo, edad, grupo_edad, parentesco_jefe, estado_civil
- describe_variable(): 2/3 OK
  - sexo: OK
  - edad: OK
  - ingresos: FAIL ConfigError (expected — canonical names son ingreso_laboral / ingreso_total, no "ingresos")

---

## BUG-001 scope — allow_unvalidated (Test D)

10/10 periodos no-validados cargaron sin TypeError.
3 periodos retornan (0,0) por ParseErrors en ZIPs origen — ver BUG-002.

| Periodo | Shape      | Nota                     |
|---------|------------|--------------------------|
| 2007-01 | (24514,247)| OK                       |
| 2008-06 | (0,0)      | ParseError ZIP — BUG-002 |
| 2010-06 | (28396,195)| OK                       |
| 2013-06 | (0,0)      | ParseError ZIP — BUG-002 |
| 2015-06 | (30136,166)| OK                       |
| 2017-06 | (29820,166)| OK                       |
| 2020-06 | (0,0)      | ParseError ZIP — BUG-002 |
| 2021-06 | (23863,176)| OK                       |
| 2023-06 | (30535,211)| OK                       |
| 2025-06 | (29706,213)| OK                       |

---

## API surface (Test E)

Public API (29 miembros callable): cache_clear, cache_info, cache_path, data_version, describe, describe_column, describe_harmonization, describe_variable, expand, list_available, list_columns_metadata, list_modules, list_validated_range, list_variables, load, load_empalme, load_merged, validation_status (+ exception classes).

load_merged: PRESENTE — load_merged(2024, 6, ["ocupados","caracteristicas_generales"]) -> (70020, 394). OK.

---

## Bugs nuevos o pendientes

### BUG-002 — Silent empty DataFrame on ParseError (MEDIUM severity)

Cuando allow_unvalidated=True y el ZIP origen tiene estructura no-standard o CSV malformado, load() retorna DataFrame (0,0) sin excepcion. El error solo se comunica via UserWarning.

Periodos afectados (modulo ocupados): 2008-06, 2013-06, 2020-06

Sub-casos:
- 2008-06: CSV malformado en Junio_csv/Cabecera - Ocupados (6).csv: Expected 177 fields in line 38, saw 178
- 2013-06: ZIP usa subdirectorio Junio.csv/; el matcher no encuentra Cabecera/Resto en root
- 2020-06: Archivo Cabecera - Ocupados.csv ausente en ZIP (convencion de nombres distinta)

Impacto: caller sin chequeo de shape procesa silenciosamente un DF vacio con resultados incorrectos.
Workaround: assert df.shape[0] > 0
Es una regresion de v1.0.0? No. ZIPs de DANE con estructura no-standard desde su origen.

---

## Conclusion

v1.0.0 esta sustancialmente limpio. BUG-001 FIXED. BUG-002 es issue de severidad MEDIA pre-existente (parse silencing) que no bloquea el uso normal con datos validados.

Agente 6B puede proceder.
