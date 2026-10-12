# T14 · Variable climática

Responsable: Migue | Revisor: Diego

- **Estado:** En revisión. 10 de octubre de 2026.
- **Usa:** clima mensual de T04 (`registro/t04/clima_parcela_mes.csv`), particiones de T03, referencia de T08/D019 y la regla de T03 §4 en `sin_respaldo`.
- **Reproducir:** `python scripts/t14_clima.py --datos RUTA/DATASET_RETO_AGRO_2026 --clima registro/t04/clima_parcela_mes.csv --particiones registro/t03/particiones.csv --catalogo analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv --pares analisis/auditoria_catalogo_y_etiquetas/tablas/pares_de_parcelas_cercanas.csv --salida registro/t14`

## Pregunta

¿Cuál variable climática (lluvia, temperatura mínima o temperatura máxima) aporta más para estimar el rendimiento, por encima de la referencia territorial? (Segunda pregunta adicional del reto.)

## Diseño (fijado antes de ver resultados)

- **Variables:** temporada 2025 con corte al 31 de octubre (sólo meses con `posterior_al_corte = False`), en las dos ventanas candidatas de T03 §6: abril–octubre y junio–octubre. La lluvia se suma (mm) y Tmin y Tmax se promedian ponderando cada mes por sus días (°C). Son 6 variables (`variables_clima_t14.csv`). Es una representación propia de T14; si difiere de la tabla común (T07), no deben intercambiarse.
- **Validación de entrada:** el script se detiene si la tabla de T04 tiene claves repetidas, meses faltantes, variables o unidades inesperadas, estados no permitidos, cobertura fuera de [0, 1] o una bandera de corte incoherente (pruebas en `tests/test_t14_clima.py`).
- **Candidatos:** la referencia `media_mun__resp_grupo` sola, y la referencia + una corrección Ridge del residuo con (a) lluvia, (b) Tmin, (c) Tmax o (d) las tres.
- **Sin fuga de información:** el residuo de cada fila de entrenamiento usa una referencia calculada sin esa fila (T03 §5); el escalado y α se ajustan dentro de cada entrenamiento.
- **Presupuesto:** una familia (Ridge) y 6 valores de α (0.1 a 10 000), elegidos con 4 particiones internas estratificadas por municipio. En empate gana el α mayor (más cerca de la referencia).
- **Decisión:** regla de T03 §4 en `sin_respaldo`, con IC95 por celdas. Se reportan los escenarios A y B.

## Resultados

Métricas fuera de muestra (5 repeticiones, 138 parcelas etiquetadas; `metricas_t14.csv`).

| Candidato | MAE A | RMSE A | Sesgo A | MAE B | RMSE B | Sesgo B |
|---|---|---|---|---|---|---|
| Referencia sola | 0.3192 | 0.4898 | +0.0029 | 0.3801 | 0.5553 | -0.0038 |
| Referencia + lluvia | 0.3201 | 0.4903 | -0.0001 | 0.3857 | 0.5595 | -0.0127 |
| Referencia + Tmin | 0.3225 | 0.4902 | -0.0012 | 0.3819 | 0.5557 | -0.0054 |
| Referencia + Tmax | 0.3215 | 0.4888 | -0.0013 | 0.3826 | 0.5551 | -0.0094 |
| Referencia + las tres | 0.3218 | 0.4898 | -0.0007 | 0.3823 | 0.5560 | -0.0087 |

La referencia coincide con `media_mun__resp_grupo` de T08/T03 (MAE 0.3192 en A y 0.3801 en B).

Comparación emparejada frente a la referencia en `sin_respaldo` (`comparacion_emparejada_t14.csv`; ΔMAE positivo = peor que la referencia; 22 celdas y 5 repeticiones):

| Escenario | Candidato | ΔMAE | IC95 por celdas | Repeticiones que mejoran | ¿Cumple T03 §4? |
|---|---|---|---|---|---|
| A | Referencia + lluvia | +0.0008 | [-0.0006, +0.0043] | 2 de 5 | No |
| A | Referencia + Tmin | +0.0030 | [+0.0006, +0.0081] | 0 de 5 | No |
| A | Referencia + Tmax | +0.0021 | [-0.0007, +0.0070] | 0 de 5 | No |
| A | Referencia + las tres | +0.0025 | [-0.0000, +0.0077] | 0 de 5 | No |
| B | Referencia + lluvia | +0.0069 | [+0.0009, +0.0195] | 0 de 5 | No |
| B | Referencia + Tmin | +0.0022 | [+0.0007, +0.0053] | 0 de 5 | No |
| B | Referencia + Tmax | +0.0028 | [+0.0002, +0.0088] | 1 de 5 | No |
| B | Referencia + las tres | +0.0033 | [+0.0004, +0.0098] | 0 de 5 | No |

Con el criterio de T03 §4 ningún candidato cumple en ningún escenario ni subconjunto (`cumple_regla_T03` = False en las 16 filas de la tabla emparejada).

### Valores de α elegidos

Cada candidato con corrección Ridge se ajustó 25 veces por escenario (5 repeticiones × 5 particiones); son 100 ajustes por escenario entre los cuatro candidatos (`alfas_t14.csv`).

| Escenario | Ajustes | α = 10 000 | α ≥ 1 000 |
|---|---|---|---|
| A | 100 | 56 (56%) | 75 (75%) |
| B | 100 | 59 (59%) | 78 (78%) |

## Escala compartida y colinealidad

- **Escala compartida:** el clima viene en celdas de unos 5 km. Las 138 parcelas etiquetadas tienen sólo 43 combinaciones climáticas distintas, repartidas en 23 celdas CHIRPS (`escala_compartida_t14.csv`); hasta 34 parcelas comparten exactamente el mismo clima, aunque la mediana es 1 parcela por valor. El clima distingue sobre todo zonas; no todas las parcelas vecinas son climáticamente idénticas.
- **Colinealidad:** las seis variables están muy relacionadas entre sí (`colinealidad_t14.csv`): la misma variable en las dos ventanas casi coincide (Tmin abril–octubre con junio–octubre, r = 0.992; Tmax, r = 0.987; lluvia, r = 0.975) y los VIF van de 215 a 6 776. No se puede separar con confianza el efecto de cada variable; por eso se comparan por bloques y no coeficiente por coeficiente.

## Desglose (T03 §4 bis)

Sección de T03 §4 bis: MAE por grupo calculado con las predicciones fuera del entrenamiento (no reentrena; `desglose_errores_t14.csv`). Cada fila compara la referencia con el **mejor candidato de ese grupo** (el de menor MAE entre los cuatro con clima); Δ = MAE del mejor candidato − MAE de la referencia (negativo = mejora). El «mejor» se elige después de ver el grupo, así que sesga a favor del clima; aun así, las mejoras son mínimas. † = menos de 5 parcelas (poco informativo).

**Municipio**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| Almoloya | 10 | 0.1412 | Tmin | -0.0023 | 0.2174 | lluvia | +0.0023 |
| Apan † | 1 | 0.0259 | las tres | -0.0052 | 0.0354 | las tres | -0.0065 |
| Calpulalpan | 30 | 0.2869 | las tres | +0.0010 | 0.2752 | las tres | +0.0016 |
| Chignahuapan | 71 | 0.3801 | lluvia | -0.0005 | 0.4086 | Tmax | -0.0001 |
| Cuautepec de Hinojosa | 5 | 0.1430 | lluvia | +0.0004 | 0.1285 | lluvia | -0.0026 |
| Emiliano Zapata † | 3 | 0.0000 | lluvia | +0.0056 | 0.0000 | lluvia | +0.0033 |
| Nanacamilpa de Mariano Arista † | 1 | 0.5536 | Tmax | -0.0024 | 0.5636 | Tmax | -0.0197 |
| Singuilucan | 16 | 0.3467 | lluvia | +0.0018 | 0.7282 | Tmax | +0.0001 |
| Tepeapulco † | 1 | 0.2109 | lluvia | +0.0003 | 0.1177 | lluvia | -0.0194 |

**Grupo de registro**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| CEBADA | 103 | 0.3385 | lluvia | +0.0003 | 0.4233 | Tmin | +0.0007 |
| Cebada | 35 | 0.2625 | las tres | +0.0028 | 0.2530 | las tres | +0.0034 |

**Parcela dudosa**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| No | 114 | 0.3230 | lluvia | +0.0014 | 0.3869 | Tmin | +0.0016 |
| Sí | 24 | 0.3014 | lluvia | -0.0015 | 0.3476 | las tres | +0.0002 |

**Vecina etiquetada ≤ 20 m**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| No | 68 | 0.3806 | lluvia | +0.0009 | 0.4379 | Tmax | +0.0011 |
| Sí | 70 | 0.2596 | lluvia | +0.0010 | 0.3239 | Tmin | +0.0015 |

Parcela dudosa = contorno B o C, o contorno angosto o muy pequeño (24 parcelas, catálogo de T02). Vecina etiquetada = parcela con otra parcela etiquetada a ≤ 20 m (70 parcelas; tabla de pares de T02).

- **Municipio:** en los municipios con 10 o más parcelas la diferencia entre la referencia y el mejor candidato es de ±0.0023 o menos; sólo Chignahuapan (n = 71) mejora en ambos escenarios, por −0.0005 en A y −0.0001 en B. Los saltos grandes (Nanacamilpa B −0.0197, Tepeapulco B −0.0194) vienen de 1 parcela y no son informativos.
- **Grupo de registro y vecinas:** el mejor candidato queda igual o peor que la referencia en todos los grupos y escenarios (Δ entre +0.0003 y +0.0034).
- **Parcelas dudosas:** en A la lluvia mejora la referencia por −0.0015 (24 parcelas); en B no mejora (+0.0002). Es una diferencia de milésimas, elegida después de ver el grupo, y no cambia la decisión.
- **Parcelas vecinas:** el clima no ayuda más en las parcelas con vecina etiquetada ≤ 20 m (Δ +0.0010 en A y +0.0015 en B), donde la referencia ya acierta mejor (MAE 0.26 y 0.32 frente a 0.38 y 0.44 sin vecina).

## Lectura

- **Ninguna variable cumple la regla de T03 §4.** En `sin_respaldo`, ningún candidato alcanza ΔMAE ≤ −0.01 ni un IC95 por celdas por debajo de cero, y como mucho 2 de 5 repeticiones mejoran. Todos los ΔMAE son positivos.
- **Todos quedan igual o ligeramente peor que la referencia.** En A, ΔMAE va de +0.0008 (lluvia) a +0.0030 (Tmin); los IC95 de lluvia y Tmax incluyen cero y el de las tres lo roza. En B, de +0.0022 (Tmin) a +0.0069 (lluvia), con IC95 por encima de cero: el empeoramiento es pequeño (milésimas de MAE) pero consistente.
- **Qué variable aporta «más» depende del escenario, y la diferencia no es robusta.** La lluvia es la menos mala en A y la más desfavorable en B; Tmin es la más desfavorable en A y la menos mala en B. Con 43 valores climáticos distintos y 23 celdas, esta alternancia no permite nombrar una ganadora. Juntar las tres variables no ayuda (A +0.0025, B +0.0033).
- **El propio modelo prefirió quedarse cerca de la referencia.** La contracción eligió α = 10 000 en 56 de 100 ajustes en A y 59 de 100 en B; α ≥ 1 000 en 75 y 78 de 100 (`alfas_t14.csv`).
- **El desglose (T03 §4 bis) no cambia la lectura.** Las mejoras que aparecen en algún grupo con n ≥ 5 son de menos de 0.003 de MAE y no se repiten entre escenarios, salvo Chignahuapan, donde son de menos de una milésima.

### Conclusión

Con esta representación climática y esta corrección Ridge, ninguno de los candidatos mejora la referencia bajo las particiones evaluadas.

La información climática es espacialmente gruesa y muchas parcelas comparten los mismos resúmenes, aunque no todas las parcelas vecinas son climáticamente idénticas.

Gran parte de la señal climática está asociada a la estructura territorial que ya captura la referencia municipal, aunque existe variación climática dentro de los municipios; en este experimento esa variación adicional no produjo una mejora predictiva detectable.

Por tanto se conserva la referencia `media_mun__resp_grupo` y no se agrega clima a los modelos por esta evidencia.

## Límites

- Una sola temporada (2025): el clima varía entre zonas, pero no entre años dentro de los datos etiquetados.
- El clima casi coincide con el municipio, y la referencia ya captura el nivel de cada municipio.
- Resultado válido para esta ventana y estas 6 variables; otras ventanas (por ejemplo, alrededor de la floración) quedan fuera del presupuesto.
