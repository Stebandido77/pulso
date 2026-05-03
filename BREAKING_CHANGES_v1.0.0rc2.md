# Breaking changes & compat — v1.0.0rc2

This document tracks every behavioral change between `pulso-co==1.0.0rc1`
and `pulso-co==1.0.0rc2` that could affect existing user code, plus the
mechanism that preserves backward compatibility.

**Hard rule:** no change in this release breaks rc1 code without a
documented compat mechanism (deprecation warning, alias, default fallback).

| Cambio | Código rc1 que se rompería | Mecanismo de compat |
|--------|---------------------------|---------------------|
| `allow_unvalidated` → `strict` (renombrado) | `pulso.load(..., allow_unvalidated=True)` o `=False` | Aceptar ambos kwargs. Si se pasa `allow_unvalidated`, traducir a `strict = not allow_unvalidated` y emitir `DeprecationWarning`. Si se pasan ambos, `ValueError`. Removido en v2.0.0. |
| Default cambia de `allow_unvalidated=False` (raise) a `strict=False` (warn + load) | Código que dependía del raise como flag de control para entradas no validadas | Documentado en CHANGELOG.md sección "Behavioral changes". Para mantener el comportamiento rc1, pasar explícitamente `strict=True`. |
| Multi-period `load`/`load_merged` continúa tras fallo cuando `strict=False` | Código que dependía del fail-fast antiguo en multi-period | Solo aplica cuando `strict=False`. Con `strict=True` se mantiene fail-fast (comportamiento rc1). |
| `load_merged(modules=[...])` ahora raisea `ModuleNotAvailableError` cuando un módulo solicitado explícitamente no existe en el período | Código que pasaba `modules=["migracion"]` para 2007-01 y aceptaba el silent-drop | Solo aplica cuando `modules` se pasa explícitamente. `modules=None` (auto-discovery) mantiene el filtrado silencioso. |
| `load_merged(apply_smoothing=True, modules=[...])` ahora respeta `modules` | Código que pasaba `modules=["x"]` con `apply_smoothing=True` y dependía de obtener TODOS los módulos | Mejora estricta — el comportamiento anterior era un bug. Documentado en CHANGELOG. |
| `expand`, `list_variables`, `describe_variable`, `describe_harmonization` ahora funcionan en vez de raisear `NotImplementedError` | Código que dependía del `NotImplementedError` para detectar disponibilidad de la función | Asumimos buena fe — improbable que exista código en producción que dependa explícitamente de `NotImplementedError` en una API pública. Sin compat shim. |
| `download_empalme_zip` ahora verifica SHA-256 cuando está disponible | Código que dependía de descargas no verificadas (improbable: el README ya prometía verificación) | Comportamiento alineado con la promesa del README. Sin compat shim. |
| Mensaje de `DataNotValidatedError` actualizado de `"Pass allow_unvalidated=True"` a `"Pass strict=False (with warning)"` | Código que parsea el mensaje de la excepción literalmente | El mensaje no es API estable. Sin compat shim. |
| Multi-period `load` con `strict=False` emite UN warning agregado en vez de N | Código que contaba `len(caught_warnings) == N` | Cambio cualitativo de mensaje, no de tipo. El warning sigue siendo `UserWarning`, sigue siendo emitido. Si un usuario contaba warnings exactos, romperá; documentado en CHANGELOG. |
| `validate_year_month` ahora rechaza `bool` y `str` | Código que pasaba `year=True` (year=1) o `year="2024"` | Estos eran bugs latentes. `year="2024"` ya rompía con un error críptico mid-iter; ahora falla al validar con mensaje claro. `year=True` cargaba year=1 silenciosamente. Sin compat shim — no son usos legítimos. |
| `cache_clear(level="...")` con un nivel no reconocido ahora raisea `CacheError` | Código que pasaba un literal no listado y dependía del no-op silencioso | Improbable. La firma siempre fue `Literal[...]` — los type checkers ya advertían. Sin compat shim. |

## Migration cheat-sheet

```python
# rc1
pulso.load(year=2024, month=6, module="ocupados", allow_unvalidated=True)

# rc2
pulso.load(year=2024, month=6, module="ocupados", strict=False)
# o sin pasar nada (strict=False es el nuevo default):
pulso.load(year=2024, month=6, module="ocupados")
```

```python
# rc1: comportamiento por default era raise
try:
    df = pulso.load(year=2007, month=1, module="ocupados")
except DataNotValidatedError:
    handle_unvalidated()

# rc2: para mantener ese comportamiento
try:
    df = pulso.load(year=2007, month=1, module="ocupados", strict=True)
except pulso.DataNotValidatedError:
    handle_unvalidated()
```

## Deprecation timeline

- **v1.0.0rc2** (esta release): `allow_unvalidated` deprecado, sigue
  funcionando con `DeprecationWarning`.
- **v2.0.0** (futuro): `allow_unvalidated` removido. Solo `strict`.
