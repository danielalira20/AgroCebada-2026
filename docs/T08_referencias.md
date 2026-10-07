# T08 · Referencias territoriales

- **Responsable:** Migue. **Revisor:** Daf.
- **Estado:** En revisión. 5 de octubre de 2026.
- **Usa:** las particiones de T03 (`registro/t03/particiones.csv`) y la regla de decisión de T03 §4.
- **Reproducir:** desde la raíz del repositorio, `python scripts/t08_referencias.py --datos RUTA/DATASET_RETO_AGRO_2026 --particiones registro/t03/particiones.csv --salida registro/t03` (escribe en `registro/t03/`, junto a los CSV de T03). El dataset no se versiona.

Todas las referencias se recalculan **dentro de cada entrenamiento**. Ningún valor municipal se calcula con las 138 etiquetas antes de evaluar.

## Candidatos

| Candidato | Qué predice | Respaldo si el municipio no tiene etiquetas en el entrenamiento |
|---|---|---|
| `media_global` / `mediana_global` | La media o mediana de todo el entrenamiento. | — |
| `media_mun__resp_global` | La media del municipio. **Es la referencia del piloto y la base de comparación.** | Media global. |
| `media_mun__resp_grupo` | La media del municipio. | Media del grupo de registro (`Cebada`/`CEBADA`). |
| `mediana_mun__resp_global` | La mediana del municipio. | Mediana global. |
| `mediana_mun__resp_grupo` | La mediana del municipio. | Mediana del grupo de registro. |
| `mediana_mun_contraida_grupo` | Contracción: w·mediana_mun + (1 − w)·mediana_grupo, con w = n/(n + k). | La intensidad k ∈ {0, 1, 2, 5, 10, 20, 50} se elige con 4 particiones internas. |

**Sobre el grupo de registro.** El campo `Cultivo` del shapefile se usa sólo como metadato de procedencia, sin atribuirle efecto agronómico (O5).

## Resultados (5 repeticiones; métricas sobre las 138 predicciones fuera del entrenamiento)

| Candidato | MAE A | RMSE A | Sesgo A | R² A | MAE B | RMSE B |
|---|---|---|---|---|---|---|
| **mediana_mun__resp_grupo** | **0.310** | **0.487** | +0.041 | 0.670 | **0.363** | **0.553** |
| mediana_mun_contraida_grupo | 0.310 | 0.487 | +0.041 | 0.670 | 0.388 | 0.590 |
| media_mun__resp_grupo | 0.319 | 0.490 | +0.003 | 0.666 | 0.380 | 0.555 |
| mediana_mun__resp_global | 0.331 | 0.524 | +0.058 | 0.619 | 0.382 | 0.586 |
| media_mun__resp_global (base) | 0.335 | 0.512 | +0.014 | 0.636 | 0.388 | 0.562 |
| mediana_global | 0.739 | 0.932 | +0.352 | −0.21 | 1.031 | 1.165 |
| media_global | 0.751 | 0.852 | 0.000 | −0.01 | 0.852 | 0.953 |

- **Escenario A** (municipio conocido) es el principal; **B** (separación por celda CHIRPS) es la sensibilidad (T03 §3).
- La variación del MAE entre repeticiones es de 0.002–0.006 en A y de 0.03–0.04 en B.
- Detalle en `metricas_referencias.csv` y `metricas_por_municipio.csv`.

## Comparación emparejada frente a la base (regla T03 §4)

La regla usa el **IC95 por bloques espaciales** (se remuestrean las 23 celdas CHIRPS con parcelas etiquetadas; T03 §4). El IC por parcelas independientes se muestra sólo como referencia.

| Candidato | Esc. | ΔMAE | IC95 por celdas | IC95 por parcelas | Reps que mejoran | ΔRMSE | ¿Cumple? |
|---|---|---|---|---|---|---|---|
| mediana_mun__resp_grupo | A | **−0.025** | [−0.057, −0.004] | [−0.048, −0.006] | 5/5 | −0.025 | **Sí** |
| mediana_mun__resp_grupo | B | −0.025 | [−0.063, +0.027] | [−0.052, −0.001] | 4/5 | −0.010 | No (el IC por celdas incluye 0) |
| media_mun__resp_grupo | A | −0.016 | [−0.046, 0.000] | [−0.036, 0.000] | 5/5 | −0.022 | No |
| mediana_mun__resp_global | A | −0.004 | [−0.015, +0.012] | [−0.015, +0.007] | 4/5 | +0.012 | No |
| mediana_mun_contraida_grupo | A | −0.025 | [−0.057, −0.004] | [−0.048, −0.006] | 5/5 | −0.025 | Sí, pero coincide con la mediana (k = 0); gana la más simple |

Detalle en `comparacion_emparejada.csv`.

## Lectura

1. **Recomendación de referencia para T09–T16: `mediana_mun__resp_grupo`.** Cumple la regla de T03 en el escenario principal (A). En el escenario espacial (B) mejora lo mismo en promedio (−0.025), pero con el intervalo por bloques la mejora ya no es concluyente; así se reporta. Todos los frentes deben medir su aporte **contra ella**, no contra la media municipal del piloto.
2. **La mejora viene sobre todo de usar la mediana, y el respaldo por grupo evita los fallos de los municipios pequeños.**
   - Con la mediana, Chignahuapan pasa de MAE 0.380 a 0.368.
   - Con el respaldo por grupo, Nanacamilpa pasa de 1.48 a 0.50 y Apan de 0.97 a 0.00 (son municipios de una sola etiqueta; poco informativos, n < 5).
3. **La contracción no aporta.** La selección interna eligió k = 0 (sin contracción) en 48 de 51 ajustes. En A coincide con la mediana municipal; en B empeora. No se promueve.
4. **Sesgo.** La mediana sobreestima en promedio 0.04 t/ha, porque Chignahuapan tiene una cola de rendimientos bajos. Es el costo de optimizar MAE. **Si FIRA confirma RMSE como métrica, la candidata sería `media_mun__resp_grupo`** (RMSE 0.490, sesgo 0.003).
5. **Respaldos.** En la validación, el respaldo se activa en 15 de 690 predicciones: municipios con una sola etiqueta que quedan fuera del entrenamiento. **En las 59 reservadas no se activa nunca:** todas tienen municipio con etiquetas (`activacion_respaldos.csv`).

## Para otros frentes

- **T09–T15:** usar `predicciones_oof_referencias_mediana_mun__resp_grupo.csv` como base de la comparación emparejada. Si construyen un modelo de residuos, la referencia de cada fila de entrenamiento debe recalcularse dejando fuera esa fila (T03 §5).
- **T17 (app de Diego):** `predicciones_59_referencias.csv` trae la predicción de cada candidato para las 59 parcelas, ajustada con las 138 etiquetas, con la columna `fuente` (municipio, grupo o global). Sirve para conectar la app ya, con la referencia real, y cambiarla por el modelo final en T16.

## Pendiente (no bloquea)

- **Corrección parcelaria sobre la referencia** (añadida por Dani en T08). Necesita las variables de T04–T06. Se evalúa en T11/T15 con esta referencia como base y con este mismo script de comparación emparejada.
