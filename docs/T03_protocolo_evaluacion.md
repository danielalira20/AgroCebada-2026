# T03 · Protocolo de evaluación común

- **Responsable:** Migue. **Revisora:** Jass.
- **Estado:** En revisión. Borrador del 5 de octubre de 2026.
- **Artefactos:** `scripts/t03_evaluacion.py` y, en `registro/t03/`, `particiones.csv`, `soporte_parcelas.csv` y `soporte_resumen.csv`.
- **Reproducir:** desde la raíz del repositorio, `python scripts/t03_evaluacion.py --datos RUTA/DATASET_RETO_AGRO_2026` (escribe en `registro/t03/`). El dataset no se versiona.

Este documento fija **antes de comparar modelos** cómo se evalúa, para que ningún resultado posterior pueda cambiar el criterio (plan unificado, O3–O4). Sólo usa los rendimientos para contar etiquetas por municipio. Los modelos se comparan después, en T08–T16.

---

## 1. Diagnóstico de soporte: las 59 reservadas frente a las 138 etiquetadas

Los datos completos están en `registro/t03/soporte_resumen.csv`. Ninguna cifra de esta sección usa rendimientos.

| Aspecto | 59 reservadas | 138 etiquetadas | Lectura |
|---|---|---|---|
| Municipio con etiquetas | 59 / 59 | — | Todas caen en municipios con ejemplos. |
| Municipio con una sola etiqueta | 1 (AGC_120, Nanacamilpa, grupo `Cebada`) | — | Es el único caso donde se activa un respaldo. |
| Etiquetas del municipio (mediana) | 30 | 70 | Hay soporte amplio, concentrado en Chignahuapan (29 reservadas). |
| Distancia a la etiquetada más cercana (mediana; p75) | 349 m; 562 m | 399 m; 677 m | Las reservadas están igual o más cerca de ejemplos que las etiquetadas entre sí. |
| A más de 1 km de una etiquetada | 7 | 21 | No hay aislamiento sistemático. |
| Celda CHIRPS sin etiquetadas | 2 (AGC_174 Cuautepec, AGC_147 Calpulalpan) | — | Su clima no tendrá ejemplo en la misma celda. |
| Celdas CHIRPS tocadas por el polígono | 1 (máx. 2) | 1 (máx. 3) | Iguales. |
| Capturas S2 / Planet despejadas (≤ 20 %), abril–octubre de 2025 (mediana) | 33 / 83 | 32 / 82 | Iguales. Ningún mes queda sin captura despejada. |
| Hueco máximo de junio a octubre, S2 / Planet (mediana) | 25 / 20 días | 25 / 20 días | Iguales. |
| Área (mediana) | 5.66 ha | 4.92 ha | Parecida. |

**Nota.** Los parecidos de esta tabla describen el soporte. No demuestran que las distribuciones sean iguales (O7).

## 2. Escenarios de evaluación

| Escenario | Cómo se separa | Uso previsto | Limitación |
|---|---|---|---|
| **A. Municipio conocido** | 5 particiones estratificadas por municipio × 5 repeticiones (columna `particion_principal`). | Parcelas nuevas en municipios con ejemplos, que es el caso de las 59. | Entrenamiento y evaluación pueden compartir vecindad y celda climática. |
| **B. Separación espacial** | Celdas CHIRPS completas asignadas a 5 particiones (columna `particion_espacial`). | Medir cuánto depende el modelo de ejemplos cercanos o de la misma celda. | Las 5 repeticiones dan 5 agrupaciones distintas, pero las dos celdas grandes de Chignahuapan (34 parcelas cada una) quedan siempre como dos particiones completas; sólo cambian las otras tres (23/23/24 parcelas). La variación entre repeticiones es, por tanto, menor que en A. Las celdas vecinas siguen relacionadas. |
| **C. Municipio excluido** | Dejar fuera un municipio a la vez (columna `municipio`). | Transferencia a territorio no visto. | No representa a las 59. Excluir Chignahuapan quita 71 etiquetas. |

## 3. Regla para elegir la evaluación principal (escrita antes de comparar)

1. Si **todas** las reservadas están en municipios con etiquetas, y su distancia a la etiquetada más cercana no es mayor que la que hay entre etiquetadas, la principal es **A**.
2. Si una parte relevante de las reservadas (≥ 10 %) estuviera más aislada que las etiquetadas, o en celdas sin ejemplos, la principal sería **B**.
3. **C** nunca es la principal, salvo que haya reservadas en municipios no vistos.

**Aplicación:** 59 de 59 están en municipios conocidos, la distancia mediana es de 349 m frente a 399 m, y solo 2 de 59 (3 %) caen en celdas sin ejemplos. **Principal = A. B es un análisis de sensibilidad obligatorio. C se usa sólo para el informe.**

## 4. Métricas y regla de decisión

- **Error** = predicción − real (t/ha).
- **Métrica primaria (provisional mientras FIRA no confirme):** MAE.
- **Secundarias:** RMSE, sesgo, R² global y error por municipio y por grupo de registro. Los municipios con n < 5 se marcan como poco informativos.
- **Cómo se calcula:** las métricas salen de las 138 predicciones fuera del entrenamiento de cada repetición y después se promedian las 5 repeticiones. No se promedian las 25 particiones como si fueran independientes.
- **Comparación emparejada:** para cada parcela, la diferencia de error absoluto entre el candidato y la referencia, promediada en las 5 repeticiones (ΔMAE por parcela).
- **Incertidumbre que respeta la cercanía espacial (O4):** bootstrap por bloques.
  - **Unidad que se remuestrea:** la celda CHIRPS (0.05°) del centroide de la parcela. Hay 23 celdas con parcelas etiquetadas. Todas las parcelas de una celda entran o salen juntas.
  - **Estadístico:** el ΔMAE medio de todas las parcelas de las celdas elegidas (cada celda pesa según su número de parcelas).
  - **Remuestreo:** 5000 réplicas con reemplazo, semilla 20261006. Intervalo por percentiles 2.5 y 97.5 (`IC95_celdas`).
  - **Referencia:** también se reporta el bootstrap de parcelas independientes (`IC95_parcelas`), pero **la regla de decisión usa `IC95_celdas`**.
  - **Limitaciones:** (1) sólo 23 bloques, y dos de ellos tienen 34 parcelas cada uno, así que el intervalo es ancho e inestable en las colas; (2) captura la dependencia dentro de cada celda, no la que hay entre celdas vecinas; (3) las 5 repeticiones reutilizan las mismas parcelas, por lo que el ΔMAE por parcela no es una observación nueva; (4) es un intervalo de la diferencia de desempeño en estas 138 parcelas, no una garantía para las 59 ni para otra campaña.
  - **Respaldo de T02 (Jass):** la auditoría de catálogo y etiquetas encontró que, en los municipios de etiqueta gruesa, las parcelas vecinas suelen compartir el mismo valor de rendimiento (7 de 8 pares vecinos en Calpulalpan/Emiliano Zapata); por eso no deben tratarse como observaciones independientes al calcular esta incertidumbre.
- **Regla para promover un candidato sobre otro más simple.** Deben cumplirse las tres condiciones:
  1. ΔMAE ≤ −0.01 t/ha (umbral de diferencia práctica);
  2. el límite superior del IC95 por bloques espaciales (`IC95_celdas`) es < 0;
  3. el signo de ΔMAE es el mismo en al menos 4 de las 5 repeticiones.

  Además, el RMSE no puede empeorar más de 0.01 t/ha.
- **Desempate:** si nada cumple la regla, gana el procedimiento más simple (con menos entradas y pasos). Si dos candidatos la cumplen, gana el de menor MAE en el escenario B.
- **Disponibilidad:** un candidato sólo es elegible si puede producir una predicción finita para las 59 reservadas con un respaldo declarado.
- **Si FIRA confirma RMSE como métrica oficial,** se intercambian los papeles de MAE y RMSE en la regla, con los mismos umbrales.

## 5. Selección interna y presupuesto de búsqueda

- Todo lo que se aprende de los datos se ajusta **dentro** de cada entrenamiento externo: imputación, escalado, referencias municipales, selección de variables, filtros, ventanas e hiperparámetros.
- **Selección interna:** 4 particiones estratificadas dentro de cada entrenamiento externo, con semilla fija igual a 0.
  - **Estrato** = municipio, si tiene al menos 4 etiquetas en ese entrenamiento; los municipios con menos de 4 (Apan, Tepeapulco, Nanacamilpa y, según la partición, Emiliano Zapata) se agrupan en un estrato común `otros`. Así ninguna partición interna queda vacía de un estrato y no se descarta ninguna parcela.
- **Municipios con muy pocas etiquetas (regla para todos los candidatos):** ninguna parcela se elimina. Cuando una parcela que se evalúa no tiene ejemplos de su municipio en el entrenamiento (por ejemplo, en la repetición 1 del escenario A: AGC_047 de Tepeapulco, AGC_048 de Nanacamilpa y AGC_164 de Apan), el candidato usa este respaldo, en orden:
  1. la referencia de su **grupo de registro** (`Cebada`/`CEBADA`), calculada con el entrenamiento;
  2. si el grupo tampoco tiene ejemplos, la referencia **global** del entrenamiento.
  - Los candidatos con respaldo "global" declarado (como el del piloto) saltan el paso 1.
  - Los modelos con variables (T09–T15) aplican el mismo respaldo a su término municipal; sus variables propias se usan igual.
  - Cada predicción registra qué respaldo usó (columna `fuente`), y T08 reporta cuántas veces se activa (`activacion_respaldos.csv`): 15 de 690 predicciones en el escenario A y ninguna en las 59 reservadas.
  - **Coincide con T02 (Jass):** el catálogo confirma que Apan, Nanacamilpa y Tepeapulco tienen una sola parcela conocida cada uno, por lo que su finura de etiqueta no se puede determinar; es el mismo motivo por el que se agrupan en `otros`.
- **Presupuesto por frente:** una familia de modelo y como máximo 8 configuraciones (por ejemplo, 6–8 valores de α en Ridge o Huber). Cualquier búsqueda mayor cuenta como otro experimento y se registra.
- **Candidatos admitidos en T08–T16:**
  - Mediana global.
  - Media y mediana municipal, cada una con respaldo global o por grupo de registro.
  - Mediana municipal contraída hacia el grupo.
  - Referencia + corrección de residuo (Ridge o Huber).
  - Regresión con interceptos municipales sin penalizar.
  - Un contraste no lineal pequeño (T12).
- **Residuos (O4):** residuo = real − referencia. Dentro de cada entrenamiento externo, la referencia de cada fila se calcula **dejando fuera esa fila**. Nunca se calcula una referencia con las 138 etiquetas antes de evaluar.

## 6. Corte temporal provisional (mejora C)

- **Momento de la estimación:** retrospectivo, con información hasta el **31 de octubre de 2025**. Toda variable debe calcularse sólo con observaciones hasta esa fecha, cortando **antes** de suavizar o interpolar.
- **Ventanas candidatas** (se comparan en T06 y T11, no se fijan aquí): 1 de abril–31 de octubre y 1 de junio–31 de octubre.
- **Etiqueta de las salidas:** se presentan como **estimación retrospectiva**, no como pronóstico temprano, salvo que se documente la disponibilidad real de cada variable en una fecha anterior.
- **Pendiente con FIRA:** si se admiten observaciones posteriores al 31 de octubre.

## 7. Formato de las predicciones que entrega cada frente

Archivo `predicciones_oof_<frente>_<candidato>.csv` con las columnas `ID_POLIGONO, repeticion, particion, escenario, real, prediccion, candidato, version`. Con ese formato, T16 compara todos los frentes sobre las mismas parcelas sin rehacer nada.

## 8. Comprobaciones para la revisora

- `particiones.csv`: 690 filas (138 IDs × 5 repeticiones). Cada ID aparece una vez por repetición. Los tamaños de la partición principal son 28/28/28/27/27.
- Ningún ID de PREDICCION aparece en `particiones.csv`.
- Volver a correr el script produce archivos idénticos.

## 9. Pendientes que no bloquean T08

- Respuesta de FIRA sobre la métrica y el corte. Si llega, se actualizan las secciones 4 y 6, con fecha.
- **Correcciones del 6 de octubre** (observaciones de Dani, corroboradas por la auditoría de T02 de Jass): descripción del escenario B ajustada a los CSV; regla escrita para municipios con pocas etiquetas y estratos internos; especificación del intervalo por bloques espaciales, ya aplicado en T08.
- Conciliar con T04 la celda climática cuando un polígono toca 2 o 3 celdas. El escenario B usa la celda del centroide.
