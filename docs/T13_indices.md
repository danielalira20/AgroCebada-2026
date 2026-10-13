# T13 · ¿Qué índice es más importante en la predicción?

Responsable: Daf · Revisa: Dani · Versión: T13-v1 · Diseño: D024 (registrado antes de correr)

## Problema que resuelve

Primera pregunta guía de las bases (bonus): **¿Qué índice es más importante en la predicción?** El plan unificado corregido pide una ablación por índices sobre los mismos casos y con el mismo estimador, revisar la estabilidad, hacer una prueba acotada en el escenario B y responder aunque no haya ganador.

## Cómo se corre

```bash
python scripts/t13_indices.py                                   # ≈1 min, escribe en registro/t13/
python -m unittest discover -s tests -p "test_t1[13]*.py" -v    # pruebas de T11 y T13 (10)
```

Entradas: las mismas de T11 (`registro/t07/tabla_comun.csv`, `registro/t03/particiones.csv`, `registro/t07/calidad_parcelas.csv` y, sólo para verificar, las predicciones de la referencia de T08). Versiones: Python 3.12.10 · scikit-learn 1.9.1 · pandas 3.0.6.

## Diseño (D024)

- **Mismo estimador que T11-v2.1:** referencia `media_mun__resp_grupo` + Ridge sobre el residuo (calculado sin la propia fila), α elegido dentro de cada entrenamiento con 4 particiones internas y criterio cuadrático. El script no copia el código: carga una copia propia de `t11_aporte_satelital.py` y sólo cambia configuraciones, nombres y carpeta de salida. Si T11 cambia de versión, T13 se detiene.
- **Mismos casos:** 138 parcelas, particiones de T03, escenarios A y B, 5 × 5. Se decide en `sin_respaldo` (D019).
- **Ventana fija:** abr_oct para todos (las ventanas ya las compara T11).
- **Una columna por índice**, para que ningún índice gane sólo por tener más variables.

| # | Candidato | Variables |
|---|---|---|
| 1 | `t13_c1_ndvi_planet` | `pl_ndvi_max_abr_oct` |
| 2 | `t13_c2_lai2_planet` | `pl_lai2_max_abr_oct` |
| 3 | `t13_c3_ndvi_s2` | `s2_ndvi_max_abr_oct` |
| 4 | `t13_c4_ndwi_s2` | `s2_ndwi_en_maximo_abr_oct` |
| 5 | `t13_c5_vi6t_landsat` | `ls_vi6t_mediana_abr_oct` |
| 6 | `t13_c6_cinco_indices` | los cinco |
| 7 | `t13_c7_cinco_sin_ndvi` | los cinco sin los dos NDVI |
| 8 | `t13_c8_cinco_sin_vi6t` | los cinco sin VI6T |

Cada configuración se compara contra la referencia con la regla de T03. Las comparaciones 6 frente a 7 (aporte del NDVI) y 6 frente a 8 (aporte de VI6T) son descriptivas.

**Qué es cada índice** (`docs/Ecuaciones_indices_AgroCebada_FIRA_2026.pdf`):
- **LAI2** = 5.405 · (b8 − b7)/(b8 + b7) − 0.114. Es una transformación lineal de un NDVI de borde rojo (infrarrojo cercano frente a borde rojo); después de escalar, en el modelo equivale a ese índice.
- **VI6T** = (B3 − ST_B10)/(B3 + ST_B10). Combina la banda verde con la banda térmica de Landsat, así que no es un índice de verdor puro.

**Fuera de T13:** en T06 calculamos las series por captura de los 27 índices del paquete (22 de Sentinel-2, 4 de Planet y 1 de Landsat), pero sólo resumimos por parcela NDVI, NDWI, LAI2 y VI6T (variables compactas aprobadas en D009, `POR_SENSOR` en `scripts/t06_satelite.py`), que son las que llegaron a la tabla común y las que usa el presupuesto de T11 (D006). Esta primera parte de T13 (D024) no incluye los otros 22 (20 de Sentinel-2, más EVI y MSAVI de Planet); se prueban en una extensión aparte, registrada en D025 antes de correr, agrupados por familia para no multiplicar las comparaciones con 138 parcelas. La heterogeneidad (std) ya la probó T11 (config 7).

## Verificación

La referencia reproduce T08: 1380 predicciones fuera de muestra, diferencia máxima 8.9e-16, mismas fuentes (15 filas con respaldo en A, 31 en B). Los cinco índices no tienen faltantes en las 197 parcelas.

## Redundancia entre índices (sin rendimiento)

Spearman en las 197 parcelas (`redundancia_indices_t13.csv` tiene también Pearson y las 138):

| | LAI2 Planet | NDVI S2 | NDWI S2 | VI6T Landsat |
|---|---|---|---|---|
| NDVI Planet | 0.90 | 0.90 | 0.79 | −0.24 |
| LAI2 Planet | | 0.85 | 0.75 | −0.16 |
| NDVI S2 | | | 0.84 | −0.25 |
| NDWI S2 | | | | −0.07 |

Cuatro de los cinco índices ordenan a las parcelas casi igual. VI6T es el único distinto.

## Resultados (sin_respaldo, donde se decide)

Referencia: A → MAE 0.3205, RMSE 0.4926, R² 0.6586 · B → MAE 0.3579, RMSE 0.5220, R² 0.6110.

| # | Índice | ΔMAE A | ΔRMSE A | ΔMAE B | ΔRMSE B |
|---|---|---|---|---|---|
| 1 | NDVI Planet | +0.0009 | +0.0003 | +0.0023 | +0.0009 |
| 2 | LAI2 Planet | +0.0010 | +0.0002 | +0.0048 | +0.0031 |
| 3 | NDVI S2 | +0.0013 | +0.0005 | +0.0016 | +0.0004 |
| 4 | NDWI S2 | +0.0009 | +0.0006 | +0.0018 | +0.0008 |
| 5 | VI6T Landsat | +0.0033 | +0.0023 | +0.0089 | +0.0053 |
| 6 | los cinco | +0.0035 | +0.0036 | +0.0082 | +0.0057 |
| 7 | cinco sin NDVI | +0.0030 | +0.0030 | +0.0122 | +0.0090 |
| 8 | cinco sin VI6T | +0.0022 | +0.0017 | +0.0092 | +0.0077 |

Positivo = más error que la referencia. ΔMAE promediado por parcela y ΔRMSE por repetición, como T11 (D023).

**Ningún índice ni combinación cumple la regla de T03**, ni con MAE ni con RMSE, en ningún escenario ni subconjunto. Las 16 diferencias frente a la referencia son positivas en MAE; en A todas son menores a 0.004 t/ha.

- **La selección interna casi apaga los índices.** El α más grande de la rejilla (10 000) se eligió en 47 de 50 entrenamientos para NDVI Planet y NDVI S2, y en 44 para NDWI. Con ese α el coeficiente queda cerca de cero y la predicción es prácticamente la referencia. VI6T fue el que menos veces lo eligió (22 de 50): el modelo le dio más peso y por eso empeoró más.
- **Sumar índices empeora.** Las tres combinaciones (6–8) tienen más error que los mejores índices solos. Con 138 parcelas y señales tan parecidas, más columnas agregan ruido.

## Orden y estabilidad de los cinco índices

Lugar de cada índice en cada repetición, según su MAE (1 = menor error). Detalle en `orden_indices_t13.csv` y `orden_indices_por_repeticion_t13.csv`.

| Índice | Lugar medio A | Veces 1.º A | Lugar medio B | Veces 1.º B | Veces último B | Coef. positivo (A / B) |
|---|---|---|---|---|---|---|
| NDVI Planet | 2.4 | 1 | 2.2 | 0 | 0 | 84 % / 60 % |
| LAI2 Planet | 2.4 | 2 | 4.2 | 0 | 1 | 100 % / 80 % |
| NDVI S2 | 3.0 | 0 | 1.2 | 4 | 0 | 92 % / 60 % |
| NDWI S2 | 3.2 | 1 | 2.6 | 1 | 0 | 44 % / 32 % |
| VI6T Landsat | 4.0 | 1 | 4.8 | 0 | 4 | 0 % / 0 % |

- **En A no hay ganador estable:** en 5 repeticiones hubo 4 índices distintos en primer lugar.
- **En B**, NDVI S2 fue primero en 4 de 5, pero LAI2, que en A empataba en primer lugar medio, cae a cuarto. El orden cambia con el escenario.
- **VI6T es consistentemente el peor** (último en 3/5 en A y 4/5 en B) y su coeficiente siempre es negativo.
- **Dirección:** en los índices de verdor el coeficiente es positivo en la mayoría de los entrenamientos (la parcela más verde que su municipio tiende a rendir algo más). Es una asociación predictiva, no causal, y de tamaño muy chico.

## Ablación (descriptiva)

| Comparación | Escenario | ΔMAE | IC95 celdas MAE | Reps a favor MAE | ΔRMSE | Reps a favor RMSE |
|---|---|---|---|---|---|---|
| Aporte del NDVI (6 vs 7) | A | +0.0005 | [−0.0003, +0.0014] | 1/5 | +0.0006 | 2/5 |
| Aporte del NDVI (6 vs 7) | B | −0.0040 | [−0.0071, −0.0010] | 5/5 | −0.0032 | 5/5 |
| Aporte de VI6T (6 vs 8) | A | +0.0013 | [−0.0015, +0.0026] | 1/5 | +0.0018 | 0/5 |
| Aporte de VI6T (6 vs 8) | B | −0.0011 | [−0.0041, +0.0003] | 2/5 | −0.0020 | 5/5 |

Negativo = tener ese índice dentro de la combinación reduce el error.

- **NDVI:** en B, quitar los dos NDVI empeora la combinación en las 5 repeticiones y el intervalo excluye el cero. Dentro de la combinación, el NDVI es lo que más pesa. En A no se distingue.
- **VI6T:** en A tiende a estorbar y en B a ayudar un poco; el signo cambia con el escenario, así que no hay conclusión.
- En los dos casos, la combinación completa sigue siendo peor que la referencia.

## Desgloses y sensibilidad (T03 §4 y §4 bis)

`desglose_error_t13.csv` tiene el error por municipio, grupo, contorno, angosta, escalón de la etiqueta y vecindad para las 9 configuraciones, en ambos escenarios y subconjuntos.

Sin las 24 parcelas con alerta de contorno (114 de 138), el orden casi no cambia: la referencia sigue primera en A y en B, VI6T y las combinaciones siguen al final, y NDVI S2 sigue siendo el mejor índice en B. En B las combinaciones empeoran más sin esas parcelas (por ejemplo, los cinco: ΔMAE +0.0083 → +0.0127). Detalle en `sensibilidad_sin_alerta_t13.csv`.

## Respuesta a la pregunta guía 1

Con las 138 parcelas etiquetadas, **ningún índice satelital mejoró la predicción respecto al rendimiento promedio del municipio**, así que no hay un índice que sea "el más importante" en el sentido de que mejore el modelo. Lo que sí muestran los datos:

1. **Los índices de verdor (NDVI de Planet y de Sentinel-2, y LAI2) son los que mejor se comportan**, aunque no mejoran a la referencia. Cuál de los tres queda primero cambia con el escenario y la repetición, porque los tres miden casi lo mismo (correlaciones de 0.85 a 0.90).
2. **Dentro de una combinación, el NDVI es lo que más pesa:** en el escenario espacial, quitarlo empeora el error en las 5 repeticiones.
3. **VI6T es el que peor funciona** y su señal va en sentido contrario a la de los índices de verdor.
4. **La dirección es la esperada:** la parcela más verde que el promedio de su municipio tiende a rendir un poco más. El efecto es tan chico que la selección interna casi siempre lo reduce a cero.

En estas parcelas, el rendimiento lo explica sobre todo la zona. El verdor resumido por temporada no agrega información estable con este tamaño de muestra. Es importancia predictiva, no causal.

## Limitaciones

- Esta parte sólo prueba los cinco índices resumidos en T06. Los otros 22 que calculamos en sus series se prueban en la extensión D025; hasta tener ese resultado, la respuesta al bonus 1 cubre sólo estos cinco.
- Un resumen por índice (máximo o mediana de abr_oct), no la curva completa ni otras ventanas.
- No se verificó si las observaciones estaban publicadas al 31 de octubre (como en T11).
- La unidad física de LAI2 sigue pendiente (P03); no cambia el resultado porque las variables se escalan.
- Con índices tan correlacionados, el orden entre los tres de verdor no es estable y no debe leerse como ranking firme.
- En B, el estrato interno `otros` queda con 3 parcelas en algunos entrenamientos (aviso de scikit-learn), igual que en T11.

## Archivos

`registro/t13/`: `predicciones_oof_t13.csv`, `metricas_t13.csv`, `comparacion_emparejada_t13.csv`, `coeficientes_t13.csv`, `orden_indices_t13.csv`, `orden_indices_por_repeticion_t13.csv`, `redundancia_indices_t13.csv`, `desglose_error_t13.csv` y `sensibilidad_sin_alerta_t13.csv`.