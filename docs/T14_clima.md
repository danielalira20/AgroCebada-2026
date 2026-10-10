# T14 · Variable climática

- **Responsable:** Migue. **Revisor:** Dani.
- **Estado:** En revisión. 10 de octubre de 2026.
- **Usa:** clima mensual de T04 (`registro/t04/clima_parcela_mes.csv`), particiones de T03, referencia de T08/D019 y la regla de T03 §4 en `sin_respaldo`.
- **Reproducir:** `python scripts/t14_clima.py --datos RUTA/DATASET_RETO_AGRO_2026 --clima registro/t04/clima_parcela_mes.csv --particiones registro/t03/particiones.csv --salida RUTA/SALIDA`

## Pregunta

¿Cuál variable climática (lluvia, temperatura mínima o temperatura máxima) aporta más para estimar el rendimiento, por encima de la referencia territorial? (Segunda pregunta adicional del reto.)

## Diseño (fijado antes de ver resultados)

- **Variables:** temporada 2025 con corte al 31 de octubre (sólo meses con `posterior_al_corte = False`). Dos etapas: temprana (abril–junio) y tardía (julio–octubre). La lluvia se suma (mm) y Tmin y Tmax se promedian (°C). Son 6 variables (`variables_clima_t14.csv`).
- **Candidatos:** la referencia `media_mun__resp_grupo` sola, y la referencia + una corrección Ridge del residuo con (a) lluvia, (b) Tmin, (c) Tmax o (d) las tres.
- **Sin fuga de información:** el residuo de cada fila de entrenamiento usa una referencia calculada sin esa fila (T03 §5); el escalado y α se ajustan dentro de cada entrenamiento.
- **Presupuesto:** una familia (Ridge) y 6 valores de α (0.1 a 10 000), elegidos con 4 particiones internas estratificadas por municipio. En empate gana el α mayor (más cerca de la referencia).
- **Decisión:** regla de T03 §4 en `sin_respaldo`, con IC95 por celdas. Se reportan los escenarios A y B.

## Resultados

Métricas fuera de muestra (5 repeticiones, 138 parcelas etiquetadas; `metricas_t14.csv`).

| Candidato | MAE A | RMSE A | Sesgo A | MAE B | RMSE B | Sesgo B |
|---|---|---|---|---|---|---|
| Referencia sola | 0.3192 | 0.4898 | +0.0029 | 0.3801 | 0.5553 | -0.0038 |
| Referencia + lluvia | 0.3202 | 0.4905 | -0.0003 | 0.3846 | 0.5582 | -0.0108 |
| Referencia + Tmin | 0.3217 | 0.4902 | -0.0007 | 0.3829 | 0.5558 | -0.0065 |
| Referencia + Tmax | 0.3225 | 0.4892 | -0.0010 | 0.3822 | 0.5553 | -0.0076 |
| Referencia + las tres | 0.3218 | 0.4900 | -0.0006 | 0.3822 | 0.5559 | -0.0081 |

La referencia coincide con `media_mun__resp_grupo` de T08/T03 (MAE 0.3192 en A y 0.3801 en B).

Comparación emparejada frente a la referencia en `sin_respaldo` (`comparacion_emparejada_t14.csv`; ΔMAE positivo = peor que la referencia; 5 repeticiones):

| Escenario | Candidato | ΔMAE | IC95_celdas | Repeticiones que mejoran | ¿Cumple T03 §4? |
|---|---|---|---|---|---|
| A | Referencia + lluvia | +0.0010 | [-0.0005, +0.0040] | 1 de 5 | No |
| A | Referencia + Tmin | +0.0022 | [-0.0002, +0.0068] | 0 de 5 | No |
| A | Referencia + Tmax | +0.0031 | [+0.0001, +0.0088] | 0 de 5 | No |
| A | Referencia + las tres | +0.0025 | [0.0000, +0.0079] | 0 de 5 | No |
| B | Referencia + lluvia | +0.0055 | [+0.0009, +0.0150] | 0 de 5 | No |
| B | Referencia + Tmin | +0.0037 | [+0.0011, +0.0097] | 0 de 5 | No |
| B | Referencia + Tmax | +0.0025 | [+0.0001, +0.0079] | 1 de 5 | No |
| B | Referencia + las tres | +0.0031 | [+0.0004, +0.0092] | 0 de 5 | No |

## Escala compartida y colinealidad

- **Escala compartida:** el clima viene en celdas de unos 5 km. Las 138 parcelas etiquetadas tienen sólo 43 combinaciones climáticas distintas (`escala_compartida_t14.csv`); hasta 34 parcelas comparten exactamente el mismo clima. El clima no distingue parcelas vecinas: sólo distingue zonas.
- **Colinealidad:** las variables están muy relacionadas entre sí (`colinealidad_t14.csv`), por ejemplo Tmin temprana y Tmin tardía (r ≈ 0.96) y la lluvia temprana con la Tmin temprana (r ≈ −0.62). Con VIF tan altos no se puede separar con confianza el efecto de cada variable; por eso se comparan por bloques y no coeficiente por coeficiente.

## Lectura

- **Ninguna variable cumple la regla de T03 §4.** En `sin_respaldo`, ningún candidato alcanza ΔMAE ≤ −0.01 ni un IC95 por celdas por debajo de cero, y como mucho 1 de 5 repeticiones mejora. Todos los ΔMAE son positivos.
- **Todos quedan igual o ligeramente peor que la referencia.** En A, ΔMAE va de +0.0010 (lluvia) a +0.0031 (Tmax) y los IC95 incluyen cero o lo rozan. En B, de +0.0025 (Tmax) a +0.0055 (lluvia) y los IC95 quedan por encima de cero: el empeoramiento es pequeño (milésimas de MAE) pero consistente.
- **Qué variable aporta «más» depende del escenario, y la diferencia no es robusta.** La lluvia es la menos mala en A y la más desfavorable en B; Tmax es la menos mala en B y la más desfavorable en A. Con 43 valores climáticos distintos y 23 celdas, esta alternancia no permite nombrar una ganadora. Juntar las tres variables no ayuda (A +0.0025, B +0.0031).
- **El propio modelo prefirió quedarse cerca de la referencia.** En el escenario A la contracción eligió el α máximo (10 000) en 1 517 de 2 760 ajustes (55 %), y α ≥ 1 000 en 1 989 (72 %); en B, α = 10 000 en 1 750 de 2 760 (63 %) (`alfas_t14.csv`).
- **Consecuencia para el modelo:** se conserva la referencia `media_mun__resp_grupo`. El clima de 2025 casi coincide con el municipio, que la referencia ya captura. Lo que aportaría una variable climática, si algo, no se distingue con estas 138 parcelas y una sola temporada.

## Límites

- Una sola temporada (2025): el clima varía entre zonas, pero no entre años dentro de los datos etiquetados.
- El clima casi coincide con el municipio, y la referencia ya captura el nivel de cada municipio.
- Resultado válido para esta ventana y estas 6 variables; otras ventanas (por ejemplo, alrededor de la floración) quedan fuera del presupuesto.
