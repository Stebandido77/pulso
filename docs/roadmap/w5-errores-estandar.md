# W5: errores estándar de `pulso_indicadores()`, informe para decidir

Fecha: 2026-11-28. Issue: #88. Este informe responde la pregunta del brief: ¿traen los microdatos públicos de la GEIH las variables de diseño (estrato, UPM) que hacen falta para calcular errores estándar con `survey`/`srvyr`? **No las traen.** Por eso esta sesión no implementa errores estándar: la decisión es de Esteban, y abajo están las opciones.

## Evidencia

### 1. Columnas de los microdatos

Revisé los encabezados de todos los archivos de cada zip (Cabecera/Resto en el marco 2005; nacionales en el 2018) y busqué, sin distinguir mayúsculas, `ESTRAT`, `UPM`, `SEGMENT`, `CONGLOM`, `MUESTRA`, `PSU`, `STRAT` y `DOMINIO`. También listé los identificadores y las columnas geográficas:

```
2015-06: 338 columnas únicas; coincidencias: ['AREA', 'CLASE', 'DIRECTORIO', 'DPTO', 'FEX_C_2011', 'FT', 'HOGAR', 'MES', 'REGIS', 'SECUENCIA_P']
2021-06: 385 columnas únicas; coincidencias: ['AREA', 'CLASE', 'DIRECTORIO', 'DPTO', 'FEX_C_2011', 'FT', 'HOGAR', 'MES', 'REGIS', 'SECUENCIA_P']
2024-06: 524 columnas únicas; coincidencias: ['AREA', 'CLASE', 'DIRECTORIO', 'DPTO', 'FEX_C18', 'FFT', 'FT', 'HOGAR', 'MES', 'PERIODO', 'PET', 'REGIS', 'SECUENCIA_P']
2026-09: 520 columnas únicas; coincidencias: ['AREA', 'CLASE', 'DIRECTORIO', 'DPTO', 'FEX_C18', 'FFT', 'FT', 'HOGAR', 'MES', 'PERIODO', 'PET', 'REGIS', 'SECUENCIA_P']
```

No hay estrato, UPM, segmento ni conglomerado, ni réplicas de pesos, en ninguno de los dos marcos. Lo que sí hay:
- `DIRECTORIO` identifica la vivienda, no la UPM.
- `DPTO`, `AREA` y `CLASE` son dominios geográficos, no los estratos de diseño.
- Un único factor de expansión calibrado (`FEX_C_2011` / `FEX_C18`).

### 2. Lo que publica el DANE

La metodología (DSO-GEIH-MET-001, V11, p. 19–20) describe un diseño probabilístico multietápico, estratificado y de conglomerados, con un factor básico (producto de las probabilidades de selección) que se calibra por particiones geográficas. Esos componentes no se publican en los microdatos.

El DANE sí publica la precisión: la hoja **"Errores relativos"** de `anex-GEIH-sep2026.xlsx` trae límites de confianza y error relativo, calculados con el diseño completo, para el total nacional, cabeceras, centros poblados y rural disperso, y 13 y 23 ciudades. Por ejemplo, septiembre de 2026, total nacional:

```
Tasa de Desocupación (TD)  | NO | 7.505154280707147 | 8.52888318522551 | 0.03257511819342711
Tasa de Ocupación (TO)     | NO | 57.97338543276938 | 59.35039822851588 | 0.005988193756847605
Tasa Global de Participación (TGP) | NO | 63.13771071490658 | 64.4117359818528 | 0.005096163943732782
```

(La columna "Error Relativo %" está como fracción: 0,0326 = 3,26 %.)

## Opciones (decide Esteban)

| Opción | Qué hace | A favor | En contra |
|---|---|---|---|
| **A. Solo punto estimado** | `pulso_indicadores()` devuelve estimaciones puntuales, con una columna `se = NA` y una nota que remite al anexo del DANE. | Honesto; sin supuestos; coincide con el DANE. | El usuario no tiene incertidumbre. |
| **B. Pegar la precisión oficial** | Para los dominios y periodos que el DANE publica, añadir `li`, `ls` y `cv_dane` leídos de la hoja "Errores relativos" (misma arquitectura de bundle + descarga que la referencia). | Es la precisión oficial y exacta. | Solo cubre los dominios publicados (no departamentos ni cruces del usuario) y depende de bajar el anexo. |
| **C. Aproximación etiquetada** | Usar `survey` con conglomerado = `DIRECTORIO` (vivienda) y pseudoestratos = `DPTO` × `CLASE`, más el peso calibrado. La columna se llamaría `se_aprox` y la documentación lo diría. Se calibra y se reporta contra la opción B (razón del error aproximado sobre el error del DANE). | Cubre cualquier dominio. | Subestima el error, porque ignora los conglomerados de manzanas o segmentos y la calibración. Puede llevar a conclusiones falsas si no se lee la etiqueta. |
| **D. Pedir el diseño al DANE** | Solicitar (p. ej. por el sistema de PQRSD o por convenio) las variables de estrato y UPM, o pesos de réplica. | Sería lo correcto. | Fuera de nuestro control y de los plazos de v3. |

**Recomendación:** A en la v3 (es lo que se implementa en esta sesión) y B como mejora siguiente, porque da la precisión oficial sin inventar un diseño. C solo si se quiere cubrir departamentos y cruces, y siempre con la etiqueta de aproximación y la comparación contra B en la documentación.
