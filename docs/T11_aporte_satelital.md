# T11 · Aporte satelital

Revisa: Migue (aprobado en el PR #15) · Versión: T11-v2.1 · Diseño: D021 (antes de correr v1), D022 (corrección tras la revisión de Dani, antes de correr v2) y D023 (ajustes tras las revisiones de Migue y Dani, antes de correr v2.1)

## Problema que resuelve

¿Las variables satelitales mejoran la predicción de rendimiento más allá de la referencia territorial? Y si mejoran, ¿la mejora viene de la calidad de la observación o de la señal espectral? (Plan unificado corregido: T11, O2, O4.)

## Cómo se corre

```bash
python scripts/t11_aporte_satelital.py                   # ≈1.5 min, escribe en registro/t11/
python -m unittest tests.test_t11_aporte_satelital -v    # pruebas con los datos del repositorio
```

Entradas: `registro/t07/tabla_comun.csv`, `registro/t03/particiones.csv`, `registro/t07/calidad_parcelas.csv` y, sólo para verificar, `registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv`.

Versiones usadas: Python 3.12.10 · scikit-learn 1.9.1 · pandas 3.0.6.

## Ficha

- **Población:** las 138 parcelas etiquetadas, sin quitar ninguna. Se reporta en `todas` y en `sin_respaldo`; se decide en `sin_respaldo` (D019). Esto da unas 135 predicciones por repetición en A y unas 132 en B.
- **Corte:** 31 de octubre de 2025.
- **Referencia (territorio):** `media_mun__resp_grupo` (D019).
- **Validación:** particiones de T03, escenarios A (principal) y B (espacial), 5 repeticiones × 5 particiones.
- **Fijado antes de evaluar:** las 8 configuraciones (D006), el estimador y la rejilla de α (D021), la corrección de la selección interna (D022) y los ajustes de agregación y controles (D023).
- **Descriptivo, no decide:** la lectura de la O2, la comparación de ventanas, los desgloses y la sensibilidad sin las 24 parcelas.

## Modelo

Predicción = referencia + Ridge ajustado al residuo (real − referencia calculada sin la propia fila, O4).

- **Selección de α (T03 §5):** 4 particiones internas, semilla 0. El estrato es el municipio si tiene al menos 4 etiquetas en ese entrenamiento; si no, `otros`.
- **Sin fuga (D022):** en cada partición interna, la referencia y el residuo se calculan sólo con su parte de entrenamiento. El α se elige con el error de rendimiento de la parte de validación (referencia + Ridge). La prueba `test_t11_aporte_satelital.py`, con los datos del repositorio, comprueba que en v1 cambiar una etiqueta de validación movía 9 residuos de entrenamiento y que en v2 no cambia ninguno.
- **Criterio de α:** error cuadrático (D021). En empate, el α más grande, que es el modelo más simple. La regla de T03 decide con MAE; igualar el criterio se descartó porque cambiaría la elección de α después de ver resultados (D023).
- **Transformaciones:** el escalado y el centrado por municipio (config 8) se aprenden sólo con el entrenamiento. No hay imputación porque las 24 columnas distintas que usan las 8 configuraciones no tienen faltantes (D021 y D022 decían 18 por error; lo corrige D023).
- **Controles (D023):** el programa se detiene si una parcela aparece dos veces en una repetición, si está a la vez en entrenamiento y evaluación, o si la referencia no reproduce T08.
- **Presupuesto:** rejilla de 9 α × 8 configuraciones. Como el α se elige dentro de cada entrenamiento, externamente se comparan 8 procedimientos, uno por configuración de D006. La rejilla no se redujo después de ver resultados (D022). Migue aceptó esta conciliación con T03 §5 en la revisión del PR #15 (D023).

## Entradas

| # | Variables además de territorio |
|---|---|
| 1 | Calidad Planet abr_oct: `pl_capturas_abr_oct`, `pl_hueco_max_abr_oct`, `pl_nubosidad_media_abr_oct` |
| 2 | S2 compacto jun_oct: `s2_ndvi_max`, `s2_ndvi_integral`, `s2_ndvi_dias_sobre_mitad`, `s2_ndwi_en_maximo` (jun_oct) y `s2_ndvi_al_corte` |
| 3 | S2 compacto abr_oct (mismas columnas, ventana abr_oct) |
| 4 | Planet compacto jun_oct: `pl_ndvi_max`, `pl_ndvi_integral`, `pl_lai2_max`, `pl_ndvi_dias_sobre_mitad`, `pl_ndvi_dia_inicio` (jun_oct) y `pl_ndvi_al_corte` |
| 5 | Planet compacto abr_oct (mismas columnas, ventana abr_oct) |
| 6 | 5 + calidad Planet (mejora A) |
| 7 | 5 + heterogeneidad `pl_ndvi_std_en_maximo_abr_oct` (mejora B) |
| 8 | 5 centrado por municipio con la media del entrenamiento |

**Excluidas en T11:**
- clima (el contraste con clima queda para después de T09);
- relieve y área (T10);
- Landsat (`ls_*`);
- calidad de S2;
- `s2_ndvi_std_en_maximo_*`;
- metadatos, ID y `cultivo_origen` (sólo referencia y evaluación).

**Disponibilidad:** todas las variables usan observaciones hasta el 31 de octubre; no se verificó si en esa fecha ya estaban publicadas (la latencia de cada sensor queda pendiente). El máximo, la integral, los días sobre la mitad y el valor al corte requieren la temporada completa, así que no existen a mitad del ciclo. Las columnas de calidad tienen rol `calidad` en T07; D006 las usa como predictoras de forma explícita en las configs 1 y 6.

## Verificación

La referencia del script reproduce la de T08: 1380 predicciones fuera de muestra, diferencia máxima 8.9e-16, mismas fuentes y las mismas filas con respaldo (15 en A, 31 en B).

## Resultados (sin_respaldo, donde se decide)

Referencia: A → RMSE 0.4926, MAE 0.3205, R² 0.6586 · B → RMSE 0.5220, MAE 0.3579, R² 0.6110.

| # | ΔRMSE A | ΔMAE A | ΔRMSE B | ΔMAE B |
|---|---|---|---|---|
| 1 | +0.0010 | +0.0087 | −0.0012 | +0.0054 |
| 2 | −0.0032 | +0.0034 | −0.0026 | +0.0073 |
| 3 | +0.0014 | +0.0059 | +0.0132 | +0.0222 |
| 4 | +0.0013 | +0.0029 | −0.0003 | +0.0022 |
| 5 | +0.0008 | +0.0040 | +0.0034 | +0.0085 |
| 6 | −0.0000 | +0.0046 | −0.0035 | +0.0012 |
| 7 | +0.0024 | +0.0074 | +0.0039 | +0.0098 |
| 8 | +0.0009 | +0.0031 | −0.0039 | −0.0028 |

Como en T08, ΔMAE se promedia primero por parcela (cada parcela pesa igual aunque en B tenga distinto número de repeticiones elegibles); ΔRMSE y el conteo de repeticiones que mejoran se calculan por repetición (D023).

**Ninguna configuración cumple la regla de T03**, ni con MAE (vigente) ni con RMSE (si se confirma la métrica de FIRA), en ningún escenario ni subconjunto.

- **En A**, la mayor reducción de RMSE es la de la config 2 (−0.0032; IC95 por celdas [−0.0120, +0.0026]; 4/5 repeticiones), pero su MAE empeora. La referencia es la mejor en MAE.
- **En B**, la mayor es la de la config 8 (ΔRMSE −0.0039; IC95 [−0.0166, +0.0011]; 4/5 repeticiones). No alcanza el umbral y el intervalo incluye el cero.

El detalle completo (IC95 por celdas y por parcelas, repeticiones, ΔR²) está en `comparacion_emparejada_t11.csv`.

## O2: ¿calidad de observación o señal espectral?

- **A:** ninguna aporta. Calidad sola: +0.0010; espectral sobre calidad (6 vs. 1): −0.0010; calidad sobre espectral (6 vs. 5): −0.0008.
- **B:** sumar calidad a Planet tiende a mejorar (6 vs. 5: ΔRMSE −0.0070, ΔMAE −0.0073), pero con IC95 [−0.0335, +0.0042]. Es una tendencia, no evidencia.

No se atribuye mejora a ninguna fuente, y ninguna comparación demuestra causalidad. Como las parcelas son de temporal (FIRA, 2ª sesión, P1), la nubosidad podría reflejar lluvia más que la calidad de la observación. Conviene revisarlo cuando exista T09.

## Ventanas (D005) · observaciones, no conclusiones

- **S2:** en B, abr_oct se observó peor que jun_oct (ΔRMSE +0.0158; IC95 por celdas [+0.0011, +0.0375]; 0/5 repeticiones a favor). En A no se distinguen (+0.0046; IC95 [−0.0012, +0.0183]). Es compatible con que abril es mayormente previo a la siembra (FIRA P2), pero la diferencia es chica, es una de varias comparaciones descriptivas y no basta para fijar una ventana para todos los sensores.
- **Planet:** no se distinguen (−0.0005 en A, +0.0037 en B). Varias columnas coinciden entre ventanas (máximos y valor al corte), así que la comparación sólo difiere en integral, días sobre la mitad y día de inicio.

## Desgloses (T03 §4 y §4 bis) · escenario A, sin_respaldo

`desglose_error_t11.csv` tiene todos los escenarios, subconjuntos y configuraciones. Las métricas se calculan por repetición y después se promedian (T03 §4, D023). Aquí van la referencia y la config 2.

| Desglose | Categoría | Parcelas | RMSE ref. | RMSE config 2 | MAE ref. |
|---|---|---|---|---|---|
| Contorno | A | 122 | 0.488 | 0.485 | 0.320 |
| Contorno | B o C | 13 | 0.530 | 0.525 | 0.328 |
| Angosta o muy pequeña | no | 122 | 0.485 | 0.483 | 0.313 |
| Angosta o muy pequeña | sí | 13 | 0.557 | 0.547 | 0.393 |
| Escalón de la etiqueta | 0.01 | 86 | 0.540 | 0.539 | 0.339 |
| Escalón de la etiqueta | 0.1 | 16 | 0.459 | 0.437 | 0.347 |
| Escalón de la etiqueta | 0.5 | 33 | 0.360 | 0.360 | 0.261 |
| Vecina etiquetada < 20 m | no | 66 | 0.531 | 0.536 | 0.381 |
| Vecina etiquetada < 20 m | sí | 69 | 0.453 | 0.441 | 0.263 |

- **Vecindad:** con vecina etiquetada a menos de 20 m, el error es menor (RMSE 0.453 frente a 0.531), como anticipa T03 §4 bis para el escenario A. La pequeña ventaja de la config 2 en A aparece en las parcelas con vecina (0.441 frente a 0.453); en las parcelas sin vecina empeora (0.536 frente a 0.531). Hay que leerla con cautela: puede reflejar la cercanía entre parcelas más que señal generalizable.
- **Escalón 0.5:** en esos municipios (33 parcelas), el 51.5 % de los errores de la referencia es menor a 0.25 t/ha, es decir, por debajo de lo que la etiqueta distingue. En este subconjunto, el grupo `Cebada` coincide con esas mismas 33 parcelas.
- **Contorno:** las parcelas B o C y las angostas o muy pequeñas tienen más error. Son pocas (13 cada grupo) y el satélite no corrige esa diferencia.

## Sensibilidad sin las 24 parcelas con alerta de contorno (T03 §4 bis)

Se repitieron las métricas sin las 24 etiquetadas con contorno B o C o marca de angosta (114 de 138). El orden de las configuraciones casi no cambia: en A, la referencia sigue siendo la mejor en MAE y las configs 2 y 6 siguen primeras en RMSE.

La excepción es la config 2 en B: pasa de ΔRMSE −0.0026 a +0.0042, así que su ventaja se concentraba en esas parcelas. Según T03, esto es motivo de revisión, no prueba de que la mejora sea irreal; de todos modos no cumplía la regla. Detalle en `sensibilidad_sin_alerta_t11.csv`.

## Conclusión

Estas ocho variantes no demostraron una mejora suficiente sobre la referencia territorial: ninguna cumple la regla de T03. La referencia se mantiene y el presupuesto de D006 (8/8) quedó usado. Esto no demuestra que cualquier uso del satélite sea inútil; sólo que estas variables resumidas por temporada, con este estimador, no superan al municipio.

## Limitaciones

- Variables resumidas por temporada, no curvas completas.
- Sólo hay calidad de Planet para la O2.
- En el escenario B, el estrato interno `otros` queda con 3 parcelas en 4 de 25 entrenamientos; T03 lo garantiza sólo en A. Ninguna parcela se descarta.
- La regla de T03 sigue con MAE como métrica primaria provisional (D001). Se reporta también con RMSE; ninguna de las dos cambia el resultado. Dentro de un mismo conjunto de predicciones, RMSE y R² de determinación ordenan igual, pero promediados entre repeticiones (con denominadores distintos en cada una) pueden no ordenar exactamente igual.
- El α se elige con error cuadrático y la regla decide con MAE (D021, D023).
- La comparación de ventanas y la lectura de la O2 son descriptivas.

## Historial

- **v1** (commits del 11 de octubre): la selección interna calculaba los residuos con todo el entrenamiento externo, lo que filtraba etiquetas de validación interna a la elección de α. Las parcelas de prueba externas no se usaron, pero la corrección era necesaria. La conclusión de v1 era la misma.
- **v2** (D022): corrige la selección interna y agrega el estrato `otros`, los desgloses y la sensibilidad.
- **v2.1** (D023, revisiones de Migue y Dani): ΔMAE promediado por parcela, desgloses por repetición, controles que detienen el programa, columna `candidato` y desviaciones con ddof=0. Las 12,420 predicciones y los α elegidos son idénticos a v2; en B, los ΔMAE cambiaron menos de 0.002 t/ha y ninguna decisión cambió.

## Archivos

`registro/t11/`: `predicciones_oof_t11.csv` (con `candidato`, `fuente` y el α elegido en cada entrenamiento), `metricas_t11.csv`, `comparacion_emparejada_t11.csv`, `coeficientes_t11.csv`, `desglose_error_t11.csv` y `sensibilidad_sin_alerta_t11.csv`.