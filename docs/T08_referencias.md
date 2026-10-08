# T08 · Referencias territoriales

- **Responsable:** Migue. **Revisor:** Daf.
- **Estado:** En revisión. 5 de octubre de 2026; corregido el 8 de octubre con la revisión de Daf.
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
| mediana_mun__resp_grupo | 0.310 | 0.487 | +0.041 | 0.670 | 0.363 | 0.553 |
| mediana_mun_contraida_grupo | 0.310 | 0.487 | +0.041 | 0.670 | 0.388 | 0.590 |
| **media_mun__resp_grupo (recomendada)** | **0.319** | **0.490** | **+0.003** | **0.666** | **0.380** | **0.555** |
| mediana_mun__resp_global | 0.331 | 0.524 | +0.058 | 0.619 | 0.382 | 0.586 |
| media_mun__resp_global (base) | 0.335 | 0.512 | +0.014 | 0.636 | 0.388 | 0.562 |
| mediana_global | 0.739 | 0.932 | +0.352 | −0.21 | 1.031 | 1.165 |
| media_global | 0.751 | 0.852 | 0.000 | −0.01 | 0.852 | 0.953 |

- **Escenario A** (municipio conocido) es el principal; **B** (separación por celda CHIRPS) es la sensibilidad (T03 §3).
- La variación del MAE entre repeticiones es de 0.002–0.006 en A y de 0.03–0.04 en B.
- Detalle en `metricas_referencias.csv` y `metricas_por_municipio.csv`.

## Comparación emparejada frente a la base (regla T03 §4)

La regla usa el **IC95 por bloques espaciales** (se remuestrean las 23 celdas CHIRPS con parcelas etiquetadas; T03 §4). El IC por parcelas independientes se muestra sólo como referencia.

Se calcula en dos subconjuntos (revisión de Daf):

- **todas:** las 690 predicciones fuera del entrenamiento de cada escenario.
- **sin_respaldo:** sólo las predicciones cuyo municipio tiene etiquetas en el entrenamiento (675 en A, 659 en B). **Es el caso de las 59 reservadas**, donde el respaldo no se activa nunca. En A, las 15 predicciones con respaldo son siempre las mismas 3 parcelas (AGC_047 de Tepeapulco, AGC_048 de Nanacamilpa y AGC_164 de Apan, municipios con una sola etiqueta) en las 5 repeticiones.

| Candidato | Esc. | Subconjunto | ΔMAE | IC95 por celdas | IC95 por parcelas | Reps que mejoran | ΔRMSE | ¿Cumple? |
|---|---|---|---|---|---|---|---|---|
| mediana_mun (cualquier respaldo) | A | **sin_respaldo** | −0.008 | [−0.016, +0.006] | [−0.016, +0.000] | 5/5 | −0.002 | **No** |
| media_mun__resp_grupo | A | **sin_respaldo** | 0.000 | — | — | — | 0.000 | Idéntica a la base |
| mediana_mun (cualquier respaldo) | B | **sin_respaldo** | −0.016 | [−0.044, +0.021] | [−0.028, −0.004] | 5/5 | −0.006 | **No** |
| mediana_mun__resp_grupo | A | todas | −0.025 | [−0.057, −0.004] | [−0.048, −0.006] | 5/5 | −0.025 | Sí |
| mediana_mun__resp_grupo | B | todas | −0.025 | [−0.063, +0.027] | [−0.052, −0.001] | 4/5 | −0.010 | No (sí con el IC por parcelas) |
| media_mun__resp_grupo | A | todas | −0.016 | [−0.046, 0.000] | [−0.036, 0.000] | 5/5 | −0.022 | No |
| mediana_mun__resp_global | A | todas | −0.004 | [−0.015, +0.012] | [−0.015, +0.007] | 4/5 | **+0.012** | No (RMSE empeora) |

La contracción (`mediana_mun_contraida_grupo`) coincide con la mediana en A (eligió k = 0 en todas las particiones). Detalle completo en `comparacion_emparejada.csv`.

## Lectura

1. **De dónde viene la mejora de `mediana_mun__resp_grupo` en A (ΔMAE −0.025):**
   - **−0.018 viene del respaldo por grupo** en las 15 predicciones de las 3 parcelas de municipios con una sola etiqueta (por ejemplo, Nanacamilpa pasa de MAE 1.48 a 0.50 y Apan de 0.97 a 0.00).
   - **−0.008 viene de usar la mediana** en lugar de la media, en el resto.
   - Con respaldo global, la mediana sólo mejora 0.004 y empeora el RMSE en 0.012 (A) y 0.024 (B).
2. **En el caso de las 59 (sin respaldo), ningún candidato cumple la regla de T03.** La mediana mejora de forma consistente (5/5 repeticiones), pero menos que el umbral de 0.01 y con un IC95 por celdas que incluye 0. La mejora en "todas" depende de 3 parcelas que no representan a las 59 (T03 §3).
3. **Recomendación de referencia para T09–T16: `media_mun__resp_grupo`.**
   - **Estadístico, media:** como nada cumple la regla en el subconjunto que representa a las 59, se aplica el desempate de T03 §4 y se conserva el de la base (la media municipal del piloto).
   - **Respaldo, por grupo:** no se elige por desempeño. T03 §5 fija el respaldo grupo → global para el término municipal de todos los modelos (T09–T15); la referencia usa el mismo para que la comparación emparejada no le atribuya a un modelo la mejora del respaldo. En las 59 da las mismas predicciones que la base.
   - Además tiene el menor sesgo (+0.003) y RMSE similar (0.490 frente a 0.487 de la mediana).
4. **Para comparar los frentes T09–T16 se reportan los dos subconjuntos, y la decisión se toma en `sin_respaldo`**, porque es el que representa a las 59 (T03 §3).
5. **La contracción no aporta.** La selección interna eligió k = 0 (sin contracción) en 48 de 51 ajustes; en A coincide con la mediana municipal y en B empeora. No se promueve.
6. **Respaldos.** En la validación, el respaldo se activa en 15 de 690 predicciones en A (31 en B). **En las 59 reservadas no se activa nunca:** todas tienen municipio con etiquetas (`activacion_respaldos.csv`).
7. **Efecto del cambio a `IC95_celdas` (D010).** En A no cambia ningún veredicto. En B sí: con el IC por parcelas, `mediana_mun__resp_grupo` (todas) cumpliría la regla; con el IC por celdas, no.

## Para otros frentes

- **T09–T15:** usar `predicciones_oof_referencias_media_mun__resp_grupo.csv` como base de la comparación emparejada y reportar los subconjuntos `todas` y `sin_respaldo` (columna `fuente`). Si construyen un modelo de residuos, la referencia de cada fila de entrenamiento debe recalcularse dejando fuera esa fila (T03 §5).
- **T17 (app de Diego):** `predicciones_59_referencias.csv` trae la predicción de cada candidato para las 59 parcelas, ajustada con las 138 etiquetas, con la columna `fuente` (municipio, grupo o global). Para la app, usar `media_mun__resp_grupo` hasta que T16 elija el modelo final.

## Pendiente (no bloquea)

- **Corrección parcelaria sobre la referencia** (añadida por Dani en T08). Necesita las variables de T04–T06. Se evalúa en T11/T15 con esta referencia como base y con este mismo script de comparación emparejada.
