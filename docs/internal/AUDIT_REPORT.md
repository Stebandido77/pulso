# AUDIT_REPORT — `pulso-co==1.0.0rc1`

Auditoría exhaustiva del paquete antes de v1.0.0 estable.
**Fase A (read-only)** — no se ha tocado código todavía.

Auditado:
- `pulso/_core/{downloader,loader,parser,harmonizer,empalme,merger,expander,harmonizer_funcs}.py`
- `pulso/_utils/{exceptions,validation,cache,columns}.py`
- `pulso/_config/{registry,epochs,variables}.py`
- `pulso/__init__.py`
- `pulso/data/{sources.json, empalme_sources.json, schemas/*}`
- 463 tests en `tests/`
- `scripts/add_month.py`
- README, docs/architecture*.md

Estado del registro: 230 entradas (2007-01 → 2026-02). **5 validadas**, **225 no validadas** (`checksum_sha256: null`). Eso es lo que dispara el bug crítico en producción.

---

## Severidades

- **CRÍTICO**: crashea, datos corruptos, pérdida de datos.
- **MAYOR**: comportamiento incorrecto, UX rota, función pública no funciona.
- **MENOR**: cosmético, mensajes confusos, inconsistencias.

---

## 1. Bugs CRÍTICOS

### C-1 · `download_zip` crashea cuando `checksum_sha256` es `None` (3 paths distintos)

**Archivo**: `pulso/_core/downloader.py:83-124`
**Disparador**: cualquier entrada con `validated: false` + `checksum_sha256: null` (225 de 230 entradas en producción) cuando el usuario pasa `allow_unvalidated=True`.

Tres líneas separadas que rompen, no una:

| Línea | Código | Falla con `checksum=None` |
|-------|--------|---------------------------|
| 83-84 | `checksum: str = record["checksum_sha256"]` → `short = checksum[:16]` | `TypeError: 'NoneType' object is not subscriptable` (el bug que reportaste) |
| 88 | `if cache and dest.exists(): if verify_checksum(dest, checksum): ...` → `expected_sha256.lower()` | `AttributeError: 'NoneType' object has no attribute 'lower'` (cache-hit path) |
| 120 | `if not verify_checksum(dest, checksum): ...` → `expected_sha256.lower()` | `AttributeError` post-download (después de bajar exitosamente, crashea al verificar) |

**Por qué importa**: el schema explícitamente permite `checksum_sha256: null` (`sources.schema.json:94-102`), `add_month.py` deja entradas sin checksum, y el scraper también. La única razón por la que esto no se notó antes es que el flag `allow_unvalidated=True` *nunca se ejecutó end-to-end* contra una entrada real con checksum nulo. Los unit tests siempre pasan un SHA válido.

**Fix conceptual**: cuando `checksum is None`, saltarse `verify_checksum` y usar otro esquema de naming para el cache (sugerido: `f"unvalidated_{year}-{month:02d}.zip"` o un hash del URL).

**Tests faltantes que lo hubieran atrapado**:
- Unit test: `test_download_zip_allow_unvalidated_with_null_checksum`
- Unit test: cache-hit path con checksum `None`
- Integration test: `pulso.load(year=2007, month=1, ..., allow_unvalidated=True)` end-to-end

---

### C-2 · `pulso.DataNotValidatedError` no está exportado en `__init__.py`

**Archivo**: `pulso/__init__.py` (no aparece en `__all__` ni en imports)
**Disparador**: cualquier código que haga `except pulso.DataNotValidatedError`. Ejemplo: el smoke test que vas a usar para validar v1.0.0rc2 — lo escribiste así en el plan:

```python
except pulso.DataNotValidatedError:
    pass
```

Esto fallaría con `AttributeError: module 'pulso' has no attribute 'DataNotValidatedError'`.

**Fix conceptual**: re-exportar `DataNotValidatedError`, `DataNotAvailableError`, `PulsoError`, y idealmente toda la jerarquía de `_utils/exceptions.py` desde el paquete raíz. Sin esto, los usuarios deben importar de un módulo "privado" (`pulso._utils.exceptions`) — anti-pattern.

---

## 2. Bugs MAYORES

### M-1 · `load_merged(apply_smoothing=True)` ignora silenciosamente el argumento `modules`

**Archivo**: `pulso/_core/loader.py:222-238` (rama empalme) + `pulso/_core/empalme.py:228-284` (`_load_empalme_month_merged`)
**Disparador**: usuario pasa `modules=["ocupados"]` con `apply_smoothing=True` y año en 2010-2019. La rama empalme llama a `_load_empalme_month_merged(y, mo, area, harmonize, variables)` — nota que `modules` no se pasa. La función carga TODOS los módulos de empalme (`MODULE_KEYWORDS_GEIH1` hardcoded). Severidad: el usuario pidió 1 módulo y recibe 6, sin warning.

**Fix conceptual**: pasar `modules` a `_load_empalme_month_merged` y respetarlo, o documentar explícitamente que `apply_smoothing=True` ignora `modules`.

---

### M-2 · `load_merged` silenciosamente descarta módulos que el usuario pidió pero el período no tiene

**Archivo**: `pulso/_core/loader.py:280-294`
```python
module_dfs = {
    mod: load(...)
    for mod in working_modules
    if mod in record["modules"]   # ← silent drop
}
```
**Disparador**: `pulso.load_merged(year=2007, month=1, modules=["migracion", "ocupados"])`. `migracion` solo existe en `geih_2021_present`. La validación al inicio (`validate_module(mod, all_known_modules)`) pasa porque `migracion` está en el registro global de módulos. Después, el módulo se cae silenciosamente. El usuario obtiene un merge solo con `ocupados`, sin pista de que perdió `migracion`.

Comparar con `load(module="migracion", year=2007, month=1)`: ahí sí raisea `ModuleNotAvailableError` (loader.py:127-132). Inconsistente.

**Fix conceptual**: emitir `UserWarning` o `ModuleNotAvailableError` cuando un módulo solicitado explícitamente no está en `record["modules"]`. Para `modules=None` (auto-discovery) el filtro silencioso es correcto.

---

### M-3 · `download_empalme_zip` NUNCA verifica checksum

**Archivo**: `pulso/_core/empalme.py:94-142`
**Disparador**: cualquier `pulso.load_empalme(year=...)` o `apply_smoothing=True`. La función baja la URL, escribe a tmp, hace `tmp.replace(dest)`, y retorna — sin tocar el `checksum_sha256` que SÍ está en `empalme_sources.json` (lo verifiqué: 9 de 11 años tienen checksum). El cache también nunca se valida en visitas posteriores.

**Por qué importa**: si el archivo se trunca en disco, si MITM modifica el ZIP, si el cache se corrompe — `pulso` lo va a aceptar sin pestañear. Y el README promete "verifies SHA-256". Promesa rota.

**Fix conceptual**: replicar el patrón de `download_zip` (verificar después de bajar, verificar al usar cache, re-bajar si mismatch), tolerando `checksum=None` como en C-1.

---

### M-4 · Funciones expuestas en `__init__` que crashean con `NotImplementedError`

**Archivo**: `pulso/__init__.py` exporta `expand`, además `pulso._config.registry` expone `list_variables`, `describe_variable`, `describe_harmonization` que están todas en `NotImplementedError`. El README las marca como "✅ estable" (líneas 132 y 139-141 marcan algunas como 🚧, pero `expand` sale como ✅).

**Disparador**: cualquier `pulso.expand(df)` o `pulso.list_variables()` crashea con `NotImplementedError("Phase 6: Claude Code")` — un mensaje que no le dice nada al usuario. `pulso._config.variables.get_variable / get_mapping / variables_for_module` también están sin implementar.

**Fix conceptual**: o (a) implementar las funciones (lista de variables, describe — son triviales sobre el variable_map), o (b) removerlas del `__all__` y del README. No dejar fantasmas en la API pública.

---

### M-5 · Multi-period `load`/`load_merged` aborta TODO en el primer período fallido

**Archivo**: `pulso/_core/loader.py:112-148` y `221-304`
**Disparador**: `pulso.load(year=range(2007, 2025), month=6, ...)` — si 2007-06 falla (no en registro, módulo no disponible, descarga rota), todos los demás años se pierden. Atraparon en cero datos en lugar de obtener 2008-2024.

**Por qué importa con la nueva API**: con `strict=False` siendo el default y warnings (no errores) por entrada no validada, la *expectativa* del usuario es "carga lo que puedas, ignora lo que falle". Hoy no hay try/except per-period.

**Fix conceptual**: cuando `strict=False`, envolver el cuerpo del loop en try/except, emitir `UserWarning` por período fallido, continuar. Cuando `strict=True`, mantener fail-fast.

---

### M-6 · `load_merged` rama smoothing ignora `multi` para columnas year/month en escenarios de empalme single-period

**Archivo**: `pulso/_core/loader.py:235-238`
```python
merged = _load_empalme_month_merged(...)
if multi:
    merged = merged.assign(year=y, month=mo)
```
`_load_empalme_month_merged` no añade columnas `year`/`month`. El path normal (`load_merged` sin smoothing, `load`) tampoco las añade en single-period. Consistente, pero distinto de `load_empalme(year=...)` que SÍ añade siempre `year`/`month` (`empalme.py:385`). Inconsistencia silenciosa entre `load_empalme(year=2015)` (con year/month) y `load_merged(year=2015, month=6, apply_smoothing=True)` (sin year/month).

**Fix conceptual**: documentar la regla en docstrings o uniformar el comportamiento.

---

## 3. Bugs MENORES + inconsistencias

### m-1 · Distribución se llama `pulso-co` pero README dice `pip install pulso`

**Archivo**: `README.md:96` y badges en `README.md:7-8`. Tras `fadf1bd build: rename PyPI distribution to pulso-co`, el README quedó desactualizado. Usuarios que copian `pip install pulso` instalan otra cosa (el paquete `pulso` ya existía en PyPI, por eso el rename).

---

### m-2 · `validate_year_month` permite años hasta 2100 y acepta `bool`

**Archivo**: `pulso/_utils/validation.py:52-54`. `if y < 2006 or y > 2100` — el rango 2026-2100 nunca tiene datos. `True` es int en Python → `validate_year_month(True, 6)` ejecuta como year=1.

**Fix conceptual**: rechazar bools explícitamente; hacer el upper bound coincidir con `metadata.covered_range[1]` o usar `current_year + 5`.

---

### m-3 · `validate_year_month` no valida tipos primitivos antes de iterar

**Archivo**: `pulso/_utils/validation.py:38-50`
```python
elif isinstance(year, range):
    years = list(year)
else:
    years = sorted({int(y) for y in year})  # crashea con string crítico
```
`pulso.load(year="2024", ...)` produce `years = sorted({2, 0, 2, 4})` (itera el string char por char), que después raisea por out-of-range, pero el mensaje es confuso. Lo mismo `month="6"` → `months = list("6")` → crash en `int(...)`.

**Fix conceptual**: rechazar `str` explícitamente con mensaje "year must be int, range, or iterable of ints, not str".

---

### m-4 · `loader.load` no usa `validate_module` con la lista global

**Archivo**: `pulso/_core/loader.py:106-132`. `load_merged` hace `validate_module(mod, all_known_modules)` upfront. `load` solo valida con `validate_module(module, all_modules)` sobre `sources["modules"].keys()` (que es el global, OK), pero después rechequea `if module not in record["modules"]`. Doble check redundante con dos errores distintos. No es un bug per se, pero la inconsistencia explica por qué `load_merged` (M-2) tiene comportamiento silent-drop diferente.

---

### m-5 · `DataNotAvailableError.__init__` toma `(year, month, hint)`; otros errores toman `str` libre

**Archivo**: `pulso/_utils/exceptions.py`. `DataNotAvailableError(2024, 6, hint=...)` vs `DataNotValidatedError("...")`. Si quieres mantener strict typing en errores, `DataNotValidatedError` debería tomar también `(year, month)` o `(key)` para que el caller no construya el mensaje cada vez.

---

### m-6 · `download_zip` race condition para descargas concurrentes del mismo período

**Archivo**: `pulso/_core/downloader.py:95-118`. `tmp = dest.with_suffix(".tmp")` es el mismo path para dos procesos concurrentes que descarguen el mismo `(year, month)`. `tmp.replace(dest)` puede dejar bytes mezclados.

**Fix conceptual**: añadir PID al tmp suffix (`f".{os.getpid()}.tmp"`) o usar `tempfile.mkstemp` en `dest.parent`. Baja prioridad — pulso es lib single-user, no daemon.

---

### m-7 · `_normalize_dane_columns` usa `(df.columns == c).sum() > 1` por columna duplicada

**Archivo**: `pulso/_utils/columns.py:34-37`. Funciona pero es O(n²) en columnas duplicadas. `Index.value_counts()` o `Series.duplicated` ya da la respuesta. No bloqueante.

---

### m-8 · `cache_clear(level="raw_zips")` o cualquier string inválido NO levanta error

**Archivo**: `pulso/_utils/cache.py:71-86`. La firma es `Literal[...]` pero en runtime cualquier string que no sea `"all"` solo intenta `if target.exists()` y se va. Sin error, sin warning. Usuario piensa que limpió el cache.

**Fix conceptual**: validar contra `_LEVELS` y raisear `CacheError` para valores no reconocidos.

---

### m-9 · `cache_path()` crashea sin diagnóstico cuando el dir no es escribible

**Archivo**: `pulso/_utils/cache.py:24-38`. `root.mkdir(parents=True, exist_ok=True)` levanta `PermissionError` crudo. Útil envolver con `CacheError` y mensaje sobre `PULSO_CACHE_DIR`.

---

### m-10 · `download_zip` flag `cache=False` no borra `dest` si ya existe

**Archivo**: `pulso/_core/downloader.py:87-118`. Con `cache=False`, brinca el chequeo de cache pero `tmp.replace(dest)` igual sobreescribe atómicamente. Comportamiento OK pero ambiguo: ¿`cache=False` significa "no leer del cache" o "no usar cache para nada"? Los docstrings no lo aclaran.

---

### m-11 · `parser._read_csv_with_fallback`: si la primera lectura tiene 1 columna por mismatch de separador, hace una segunda lectura — pero no logea cuál separador detectó

**Archivo**: `pulso/_core/parser.py:154-162`. Útil para debugging si hay datos con encoding raro. No bloqueante.

---

### m-12 · `find_shape_a_files` toma el ÚLTIMO match si hay múltiples

**Archivo**: `pulso/_core/parser.py:82-105`. Loop sin `break`. Si un ZIP tiene `Cabecera Ocupados.csv` y `Cabecera Ocupados v2.csv`, el segundo gana sin warning. Edge case improbable pero silencioso.

---

### m-13 · `tests/unit/test_smoke.py` no incluye `load_empalme` en los exports esperados

**Archivo**: `tests/unit/test_smoke.py:17-31`. El `__all__` lo lista (`pulso/__init__.py:54`) pero el smoke test no lo verifica. Tampoco verifica que las exceptions estén exportadas — relacionado con C-2.

---

### m-14 · `validate_year_month` con `range()` vacío retorna `[]` silenciosamente

**Archivo**: `pulso/_utils/validation.py:39-43`. `pulso.load(year=range(2030, 2025))` (rango invertido) retorna `pd.DataFrame()` sin error. Probablemente OK, pero un warning ayudaría.

---

### m-15 · README y `architecture.md` no documentan que `download_url` puede ser una URL de catálogo (no directa)

**Archivo**: `pulso/data/sources.json` muestra `"download_url": "https://microdatos.dane.gov.co/index.php/catalog/317/download/10934"` — esto sí es directo. Pero el schema (`sources.schema.json:81-85`) solo dice `format: uri`. Para futuro-proofing, ningún chequeo verifica que la URL apunte a un ZIP.

---

## 4. Gaps de cobertura de tests

Tests existentes: 463 (todos pasando). Gaps:

### G-1 · Cero tests con `validated=false` + `checksum_sha256: null`

`test_download_zip_allow_unvalidated` (test_downloader.py:100) usa `checksum_sha256 = sha` válido. Nunca probó el escenario real. **Este es el gap que produjo C-1.**

### G-2 · Cero tests end-to-end de `load(allow_unvalidated=True)`

Solo se testea `download_zip`. La cadena completa `load → download_zip → parse_module` con un `validated=false` real nunca se ejerce.

### G-3 · Cero tests de los 4 cuadrantes `{strict, validated}`

- strict=True + validated=true → OK
- strict=True + validated=false → DataNotValidatedError
- strict=False + validated=true → OK (sin warning)
- strict=False + validated=false → OK (con UserWarning)

### G-4 · Cero tests de imports top-level de exceptions

`from pulso import DataNotValidatedError` no se prueba. Los unit tests siempre importan de `pulso._utils.exceptions`.

### G-5 · Cero tests de `range(year_a, year_b)` con períodos NO en registro

`test_range_year_single_month` solo cubre validación pura. No hay test que invoque `load(year=range(2005, 2009), month=6)` con `2005` ausente — debería hoy abortar todo (M-5).

### G-6 · Cero tests de `load_merged(apply_smoothing=True, modules=[...])`

Confirma M-1 (modules ignorados) silenciosamente.

### G-7 · Cero tests de empalme con checksum mismatch

Confirma M-3 (`download_empalme_zip` no verifica).

### G-8 · Cero tests integration con todos los meses validados

Solo `test_real_2024_06_regression` ejerce un mes específico vía `load_merged`. Faltaría algo como:
```python
@pytest.mark.parametrize("y,m", VALIDATED_MONTHS)
def test_load_works_for_all_validated_months(y, m): ...
```
Esto hubiera atrapado regresiones de parser/harmonizer en cualquier mes validado.

### G-9 · Cero tests de `load(year=range(...), month=N)` que stackeen DataFrames

`test_real_2024_06_regression` solo carga 1 mes. No se verifica que `pd.concat` con `multi=True` produce columnas `year`/`month` correctas.

### G-10 · Cero tests para `cache_clear` con string inválido

Confirma m-8.

### G-11 · Cero tests de `expand`, `list_variables`, etc. — solo `test_phase2_functions_raise_not_implemented` (test_registry.py)

Pero éste valida que crashea, no que esté en la API pública. Confirma M-4.

---

## 5. Inconsistencias de API

### A-1 · `load(allow_unvalidated)` y `load_merged(allow_unvalidated)` tienen el flag, `load_empalme(...)` no

`load_empalme` no expone `allow_unvalidated` porque la entrada de empalme tiene su propio flag `downloadable: bool`. Diseño consciente, pero confunde: ¿por qué un loader tiene strict y el otro no?

### A-2 · `load` requiere un `module: str`, `load_merged` toma `modules: list[str] | None`, `load_empalme` toma `module: str | None`

Inconsistente. Tres APIs, tres convenciones. Aceptable porque cada loader tiene semántica distinta, pero documentar.

### A-3 · `apply_smoothing` solo en `load_merged`, no en `load`

Si el usuario pide `pulso.load(year=2015, month=6, module="ocupados", apply_smoothing=True)` no le dice nada — `apply_smoothing` no es parámetro de `load`. Para coherencia podría ser un kwarg de `load` también, o documentar explícitamente "para empalme usa `load_empalme` o `load_merged`".

### A-4 · `DataNotAvailableError` constructor estructurado vs `DataNotValidatedError` constructor de string libre

Ver m-5.

### A-5 · `cache_info()` retorna dict; `list_available()` retorna DataFrame; `data_version()` retorna string

Diferentes formatos por función. Probablemente intencional (y razonable), pero un `pulso.status()` que aglutine podría ayudar.

### A-6 · `validation_status()` (propuesto) — campo `last_validated_at` en el plan vs `validated_at` en el schema

El plan del usuario menciona columna `last_validated_at`. El schema (sources.schema.json:122-127) usa `validated_at`. Hay que decidir uno y mantenerlo (sugerencia: respetar el schema → `validated_at`).

---

## 6. Mejoras de UX sugeridas

### U-1 · Mensaje del nuevo `UserWarning` por entrada no validada

Sugerencia: incluir el conteo de entradas no validadas en el rango cargado, no una por una. Ejemplo:
```
UserWarning: Loaded 217 of 230 months from registry; 18 months had not been
checksum-validated (e.g., 2007-01, 2007-02, ...). Pass strict=True to enforce
validation, or call pulso.list_validated_range() to see which months ARE
validated end-to-end.
```
Más útil que 217 warnings spamming stderr.

### U-2 · `pulso.list_validated_range()` retorno

El plan dice `(min_year, max_year)`. Pero las 5 entradas validadas son `2007-12, 2015-06, 2021-12, 2022-01, 2024-06` — NO son contiguas. `(2007, 2024)` sería engañoso. Sugerencia: retornar `list[tuple[int, int]]` de pares (year, month) validados, o un DataFrame, o ambas via `validation_status()`.

### U-3 · `DataNotValidatedError` mensaje hardcodea el flag viejo

`pulso/_core/downloader.py:80`: `"Pass allow_unvalidated=True to load it anyway."` — al renombrar a `strict`, este mensaje queda obsoleto. Actualizar a `"Pass strict=False to load it anyway (with warning)."`.

### U-4 · No hay `__repr__` en `Epoch`, `AreaFilter`, `Variable`

Imprimir `pulso._config.epochs.get_epoch("geih_2021_present")` produce el dataclass auto-repr (denso, multilinea). Un `__repr__` corto ayudaría debugging.

### U-5 · `ModuleNotAvailableError` debería sugerir alternativas

Mensaje actual: `"Module 'migracion' is not available for 2007-06. Available: [...]"`. Útil. Pero si el usuario tipeó `"migracion"` y debería ser `"otras_formas_trabajo"`, no hay difflib-esque sugerencia ("did you mean ...?"). Bajo costo.

### U-6 · README Estado del proyecto desactualizado

README.md:186 dice "v1.0.0-rc1 ... Disponible en [TestPyPI]". Pero ya estás en PyPI real (`pulso-co==1.0.0rc1`). README.md:194 dice Phase 5 "🚧". Actualizar.

### U-7 · No hay log/print en `pulso.cache_path()` o `pulso.cache_info()` cuando el cache es enorme

Si un usuario tiene `~/.cache/pulso/` con 10 GB, no lo nota hasta que el disco se llena. `cache_info()` lo mostraría pero hay que pedirlo. Bajo costo: en `download_zip` warn si `cache_info()['total_size_bytes'] > 5 GB`.

### U-8 · No hay manera de pedir "el dataset más reciente disponible"

`pulso.load(year=pulso.list_available().year.max(), ...)` es feo. `pulso.load_latest(module="ocupados")` sería pythonic. Opcional.

---

## 7. Resumen ejecutivo / qué priorizar para v1.0.0rc2

**Bloqueantes para release:**
1. **C-1** (3 sub-bugs) → fix downloader para `checksum=None`
2. **C-2** → exportar exceptions en `__init__`
3. **M-3** → empalme también necesita verificar checksum cuando existe
4. Cambio de default `strict=False` con compat retroactiva (`allow_unvalidated` → DeprecationWarning)
5. Tests de los 4 cuadrantes `{strict, validated}` (G-3)
6. Tests de imports top-level (G-4)

**Fuertemente recomendados:**
7. **M-1** → `apply_smoothing=True` debe respetar `modules`
8. **M-2** → `load_merged` con módulo no disponible para período: error explícito, no silent drop
9. **M-4** → quitar funciones NotImplemented de la API pública o implementarlas
10. **M-5** → `strict=False` debe permitir continuar tras período fallido
11. **m-1** → README dice `pip install pulso`, debe ser `pip install pulso-co`
12. **U-2** → `list_validated_range()` con semántica que represente la realidad no-contigua

**Nice-to-have:**
13. **m-3** → validación de tipos en `validate_year_month`
14. **m-8** → `cache_clear` con string inválido
15. **U-1** → warning agregado en lugar de N warnings individuales
16. **U-6** → README "Estado del proyecto" actualizado

---

## Decisión sobre `last_validated_at` vs `validated_at`

El schema actual usa **`validated_at`** (sources.schema.json:122-127). El plan original mencionaba `last_validated_at`. Recomiendo **respetar el schema** → la nueva función `validation_status()` debe exponer la columna como `validated_at`, no `last_validated_at`. Cambiar el schema sería un break del registro.

---

**Fin del audit. Esperando revisión antes de empezar Fase B (fixes).**
