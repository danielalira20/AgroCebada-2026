# T14 · Variable climática

Responsable: Migue | Revisor: Diego

- **Estado:** En revisión. 14 de octubre de 2026 (T14-v3).
- **Usa:** clima mensual de T04 (`registro/t04/clima_parcela_mes.csv`), particiones de T03, referencia de T08/D019 y la regla de T03 §4 en `sin_respaldo`.
- **Reproducir:** `python scripts/t14_clima.py --datos RUTA/DATASET_RETO_AGRO_2026 --clima registro/t04/clima_parcela_mes.csv --particiones registro/t03/particiones.csv --catalogo analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv --pares analisis/auditoria_catalogo_y_etiquetas/tablas/pares_de_parcelas_cercanas.csv --salida registro/t14`

> **Nota (15 oct):** T15 v3 alinea el centro municipal con la referencia LOO. Con esa alineación los ΔMAE de las variantes centradas cambian ≤ 0.001 y ninguna conclusión cambia.

## Pregunta

¿Cuál variable climática (lluvia, temperatura mínima o temperatura máxima) aporta más para estimar el rendimiento, por encima de la referencia territorial? (Segunda pregunta adicional del reto.)

## Diseño (fijado antes de ver resultados)

- **Variables:** temporada 2025 con corte al 31 de octubre (sólo meses con `posterior_al_corte = False`), en las dos ventanas candidatas de T03 §6: abril–octubre y junio–octubre. La lluvia se suma (mm) y Tmin y Tmax se promedian ponderando cada mes por sus días (°C). Son 6 variables (`variables_clima_t14.csv`). Es una representación propia de T14; si difiere de la tabla común (T07), no deben intercambiarse.
- **Controles (v3):** las validaciones lanzan error también con `python -O`; las particiones se rechazan si hay IDs repetidos, IDs faltantes o reservados, o celdas ausentes o inconsistentes; la salida se escribe en una carpeta temporal y sólo se mueve a `--salida` (que debe ser nueva) si todo termina bien.
- **Validación de entrada:** el script se detiene si la tabla de T04 tiene claves repetidas, meses faltantes, variables o unidades inesperadas, estados no permitidos, cobertura fuera de [0, 1] o una bandera de corte incoherente (pruebas en `tests/test_t14_clima.py`).
- **Candidatos:** la referencia `media_mun__resp_grupo` sola, y la referencia + una corrección Ridge del residuo con (a) lluvia, (b) Tmin, (c) Tmax o (d) las tres. **v3 (revisión de Dani, H3):** los mismos 4 con las variables **centradas por municipio** (se resta el promedio municipal aprendido sólo con el entrenamiento, al ajustar y al predecir; municipio ausente → grupo → global). Son 8 procedimientos, dentro del presupuesto de T03 §5. La variante centrada se añadió después de conocer los resultados de v2; se declara así.
- **Sin fuga de información:** el residuo de cada fila de entrenamiento usa una referencia calculada sin esa fila (T03 §5); el escalado y α se ajustan dentro de cada entrenamiento.
- **Presupuesto:** una familia (Ridge) y 6 valores de α (0.1 a 10 000), elegidos con 4 particiones internas estratificadas por municipio. En empate gana el α mayor (más cerca de la referencia).
- **Decisión:** regla de T03 §4 en `sin_respaldo`, con IC95 por celdas. Se reportan los escenarios A y B.

## Resultados

Métricas fuera de muestra (5 repeticiones, 138 parcelas etiquetadas; `metricas_t14.csv`). Las variantes sin centrar son idénticas a las de v2; las centradas se añadieron en v3.

| Candidato | MAE A | RMSE A | Sesgo A | MAE B | RMSE B | Sesgo B |
|---|---|---|---|---|---|---|
| Referencia sola | 0.3192 | 0.4898 | +0.0029 | 0.3801 | 0.5553 | -0.0038 |
| Referencia + lluvia | 0.3201 | 0.4903 | -0.0001 | 0.3857 | 0.5595 | -0.0127 |
| Referencia + Tmin | 0.3225 | 0.4902 | -0.0012 | 0.3819 | 0.5557 | -0.0054 |
| Referencia + Tmax | 0.3215 | 0.4888 | -0.0013 | 0.3826 | 0.5551 | -0.0094 |
| Referencia + las tres | 0.3218 | 0.4898 | -0.0007 | 0.3823 | 0.5560 | -0.0087 |
| Referencia + lluvia (centrada) | 0.3207 | 0.4905 | -0.0001 | 0.3869 | 0.5584 | -0.0074 |
| Referencia + Tmin (centrada) | 0.3212 | 0.4903 | -0.0005 | 0.3826 | 0.5561 | -0.0087 |
| Referencia + Tmax (centrada) | 0.3221 | 0.4892 | -0.0019 | 0.3809 | 0.5539 | -0.0084 |
| Referencia + las tres (centradas) | 0.3214 | 0.4892 | -0.0014 | 0.3820 | 0.5552 | -0.0063 |

La referencia coincide con `media_mun__resp_grupo` de T08/T03 (MAE 0.3192 en A y 0.3801 en B).

Comparación emparejada frente a la referencia en `sin_respaldo` (`comparacion_emparejada_t14.csv`; ΔMAE positivo = peor que la referencia; 22 celdas y 5 repeticiones):

| Escenario | Candidato | ΔMAE | IC95 por celdas | Repeticiones que mejoran | ¿Cumple T03 §4? |
|---|---|---|---|---|---|
| A | Referencia + lluvia | +0.0008 | [-0.0006, +0.0043] | 2 de 5 | No |
| A | Referencia + Tmin | +0.0030 | [+0.0006, +0.0081] | 0 de 5 | No |
| A | Referencia + Tmax | +0.0021 | [-0.0007, +0.0070] | 0 de 5 | No |
| A | Referencia + las tres | +0.0025 | [-0.0000, +0.0077] | 0 de 5 | No |
| A | Referencia + lluvia (centrada) | +0.0015 | [+0.0007, +0.0032] | 0 de 5 | No |
| A | Referencia + Tmin (centrada) | +0.0019 | [+0.0003, +0.0047] | 0 de 5 | No |
| A | Referencia + Tmax (centrada) | +0.0025 | [-0.0009, +0.0075] | 0 de 5 | No |
| A | Referencia + las tres (centradas) | +0.0020 | [-0.0002, +0.0047] | 0 de 5 | No |
| B | Referencia + lluvia | +0.0069 | [+0.0009, +0.0195] | 0 de 5 | No |
| B | Referencia + Tmin | +0.0022 | [+0.0007, +0.0053] | 0 de 5 | No |
| B | Referencia + Tmax | +0.0028 | [+0.0002, +0.0088] | 1 de 5 | No |
| B | Referencia + las tres | +0.0033 | [+0.0004, +0.0098] | 0 de 5 | No |
| B | Referencia + lluvia (centrada) | +0.0073 | [+0.0031, +0.0165] | 0 de 5 | No |
| B | Referencia + Tmin (centrada) | +0.0024 | [+0.0004, +0.0073] | 0 de 5 | No |
| B | Referencia + Tmax (centrada) | +0.0009 | [-0.0019, +0.0050] | 2 de 5 | No |
| B | Referencia + las tres (centradas) | +0.0021 | [-0.0006, +0.0072] | 1 de 5 | No |

Con el criterio de T03 §4 ningún candidato cumple en ningún escenario ni subconjunto (`cumple_regla_T03` = False en las 32 filas de la tabla emparejada).

### Valores de α elegidos

Cada candidato con corrección Ridge se ajustó 25 veces por escenario (5 repeticiones × 5 particiones); son 200 ajustes por escenario entre los ocho candidatos (`alfas_t14.csv`).

| Escenario | Ajustes | α = 10 000 | α ≥ 1 000 |
|---|---|---|---|
| A | 200 | 121 (60.5%) | 163 (81.5%) |
| B | 200 | 123 (61.5%) | 170 (85.0%) |

## Escala compartida y colinealidad

- **Escala compartida:** el clima viene en celdas de unos 5 km. Las 138 parcelas etiquetadas tienen sólo 43 combinaciones climáticas distintas, repartidas en 23 celdas CHIRPS (`escala_compartida_t14.csv`); hasta 34 parcelas comparten exactamente el mismo clima, aunque la mediana es 1 parcela por valor. El clima distingue sobre todo zonas; no todas las parcelas vecinas son climáticamente idénticas.
- **Colinealidad:** las seis variables están muy relacionadas entre sí (`colinealidad_t14.csv`): la misma variable en las dos ventanas casi coincide (Tmin abril–octubre con junio–octubre, r = 0.992; Tmax, r = 0.987; lluvia, r = 0.975) y los VIF van de 215 a 6 776. No se puede separar con confianza el efecto de cada variable; por eso se comparan por bloques y no coeficiente por coeficiente.

## Desglose (T03 §4 bis)

Sección de T03 §4 bis, calculada **en `sin_respaldo`** (la población de decisión; `desglose_errores_t14.csv` incluye también `todas`) con las predicciones fuera del entrenamiento, sin reentrenar. Cada fila compara la referencia con el **mejor candidato de ese grupo** (el de menor MAE entre los ocho con clima); Δ = MAE del mejor candidato − MAE de la referencia (negativo = mejora). El «mejor» se elige después de ver el grupo, así que sesga a favor del clima; aun así, las diferencias son de milésimas. † = menos de 5 parcelas (poco informativo). Los municipios que sólo existen con respaldo (Apan, Nanacamilpa, Tepeapulco) no aparecen: en `sin_respaldo` no tienen predicciones.

**Municipio**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| Almoloya | 10 | 0.1412 | Tmin | -0.0023 | 0.2174 | lluvia | +0.0023 |
| Calpulalpan | 30 | 0.2869 | las tres | +0.0010 | 0.2752 | las tres | +0.0016 |
| Chignahuapan | 71 | 0.3801 | lluvia | -0.0005 | 0.4086 | Tmax (centrada) | -0.0006 |
| Cuautepec de Hinojosa | 5 | 0.1430 | lluvia | +0.0004 | 0.1285 | lluvia (centrada) | -0.0031 |
| Emiliano Zapata † | 3 | 0.0000 | lluvia (centrada) | +0.0037 | 0.0000 | lluvia | +0.0033 |
| Singuilucan | 16 | 0.3467 | lluvia (centrada) | +0.0015 | 0.5590 | Tmax (centrada) | -0.0061 |

**Grupo de registro**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| CEBADA | 102 | 0.3398 | lluvia | +0.0002 | 0.3946 | Tmax (centrada) | -0.0006 |
| Cebada | 33 | 0.2609 | Tmin (centrada) | +0.0021 | 0.2502 | las tres (centradas) | +0.0033 |

**Escalón de la etiqueta del municipio (t/ha)**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| 0.01 | 86 | 0.3385 | lluvia | -0.0001 | 0.3701 | Tmax (centrada) | +0.0003 |
| 0.1 | 16 | 0.3467 | lluvia (centrada) | +0.0015 | 0.5590 | Tmax (centrada) | -0.0061 |
| 0.5 | 33 | 0.2609 | Tmin (centrada) | +0.0021 | 0.2502 | las tres (centradas) | +0.0033 |

Columna `escalon_etiqueta_municipio`: el paso más grueso que comparten todas las etiquetas del municipio (igual que `paso_comun` de T02). Apan, Nanacamilpa y Tepeapulco tienen una sola etiqueta: sin escalón, igual que en T02.

**Parcela dudosa**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| No | 111 | 0.3246 | lluvia | +0.0014 | 0.3608 | Tmax (centrada) | +0.0007 |
| Sí | 24 | 0.3014 | lluvia | -0.0015 | 0.3476 | las tres | +0.0002 |

**Vecina etiquetada a < 20 m**

| Grupo | n | MAE ref. A | Mejor candidato A | Δ A | MAE ref. B | Mejor candidato B | Δ B |
|---|---|---|---|---|---|---|---|
| No | 66 | 0.3806 | lluvia | +0.0008 | 0.4195 | Tmax (centrada) | +0.0006 |
| Sí | 69 | 0.2630 | lluvia (centrada) | +0.0008 | 0.3000 | Tmax (centrada) | +0.0016 |

Parcela dudosa = contorno B o C, o contorno angosto o muy pequeño (24 parcelas, catálogo de T02). Vecina etiquetada = parcela con otra parcela etiquetada a menos de 20 m (pares de T02).

- **Municipio:** en los municipios con 10 o más parcelas el mejor candidato cambia el MAE entre −0.0023 y +0.0023, salvo Singuilucan en B (−0.0061 con Tmax centrada; 16 parcelas, el municipio con más error en B). Chignahuapan (71 parcelas) mejora −0.0005 en A y −0.0006 en B; es una diferencia menor que una milésima.
- **Grupo de registro:** en A el mejor candidato queda peor que la referencia (+0.0002 y +0.0021); en B sólo CEBADA mejora, por −0.0006.
- **Escalón de la etiqueta:** el mejor candidato queda a −0.0001 de la referencia en 0.01 (A) y a +0.0003 (B); en 0.1 y 0.5 es peor en A (+0.0015 y +0.0021) y en 0.5 también en B (+0.0033). La única diferencia mayor a una milésima a favor del clima es 0.1 en B (−0.0061), que es Singuilucan (16 parcelas, el mismo municipio). El clima no ayuda donde la etiqueta es más gruesa.
- **Parcelas dudosas:** en A la lluvia mejora la referencia por −0.0015 (24 parcelas); en B no mejora (+0.0002). Diferencia de milésimas, elegida después de ver el grupo.
- **Parcelas vecinas:** el clima no ayuda más en las parcelas con vecina etiquetada (Δ +0.0008 en A y +0.0016 en B), donde la referencia ya acierta mejor (MAE 0.263 y 0.300 frente a 0.381 y 0.420 sin vecina).

### Sensibilidad sin las 24 parcelas dudosas

`sensibilidad_sin_dudosas_t14.csv` repite la comparación emparejada sin las 24 parcelas dudosas (en `sin_respaldo`, 555 de 675 predicciones en A y 539 de 659 en B). La referencia sigue sin ser superada y ninguna variante cumple la regla. Sin las 24 dudosas, el orden se mantiene casi idéntico, con un cruce por escenario (correlación de rangos 0.97 en A y 0.98 en B): dentro de las variantes sin centrar y dentro de las centradas el orden es idéntico en A y en B; el cruce es un par entre ambos grupos (en A, Tmax con las tres centradas; en B, lluvia con lluvia centrada).

## Respuesta a la pregunta guía 2

No se puede nombrar una variable climática de mayor peso: lluvia, Tmin y Tmax están muy correlacionadas, el clima varía en sólo 23 celdas y hay una sola temporada. Con este estimador, ninguna mejora la referencia, centrada o no.

Como dato descriptivo (`asociacion_dentro_municipio_t14.csv`: Pearson entre cada variable y el rendimiento, ambos centrados por municipio, 138 parcelas, IC95 por bootstrap de celdas CHIRPS): Tmax es la única variable cuya asociación con el rendimiento dentro del municipio excluye el cero (r = −0.18, IC95 por celdas [−0.25, −0.02]); lluvia y Tmin lo incluyen. Es una asociación débil y descriptiva: no mejora la predicción sobre la referencia.

| Variable | r dentro del municipio | IC95 por celdas |
|---|---|---|
| Lluvia abr–oct | −0.055 | [−0.150, +0.186] |
| Lluvia jun–oct | −0.047 | [−0.149, +0.195] |
| Tmin abr–oct | −0.047 | [−0.150, +0.062] |
| Tmin jun–oct | −0.093 | [−0.179, +0.039] |
| Tmax abr–oct | −0.175 | [−0.247, −0.022] |
| Tmax jun–oct | −0.177 | [−0.252, −0.028] |

## Lectura

- **Ninguna variable cumple la regla de T03 §4, centrada o no.** En `sin_respaldo`, ninguno de los ocho candidatos alcanza ΔMAE ≤ −0.01 ni un IC95 por celdas por debajo de cero, y como mucho 2 de 5 repeticiones mejoran. Todos los ΔMAE son positivos.
- **Centrar por municipio no cambia la conclusión.** En A, las variantes sin centrar quedan de +0.0008 (lluvia) a +0.0030 (Tmin) y las centradas de +0.0015 (lluvia) a +0.0025 (Tmax). En B, de +0.0022 (Tmin) a +0.0069 (lluvia) frente a +0.0009 (Tmax centrada) a +0.0073 (lluvia centrada). La mejor en B es Tmax centrada (+0.0009; IC95 [−0.0019, +0.0050]; 2 de 5 repeticiones): no se distingue de la referencia.
- **Qué variable aporta «más» depende del escenario, y la diferencia no es robusta.** La lluvia es la menos mala en A y la más desfavorable en B (centrada o no); Tmax centrada es la menos mala en B. Con 43 valores climáticos distintos y 23 celdas, esta alternancia no permite nombrar una ganadora. Juntar las tres variables no ayuda.
- **El propio modelo prefirió quedarse cerca de la referencia.** La contracción eligió α = 10 000 (el techo de la rejilla) en 121 de 200 ajustes en A y 123 de 200 en B; α ≥ 1 000 en 163 y 170 (`alfas_t14.csv`).
- **El desglose (T03 §4 bis) no cambia la lectura.** Las mejoras que aparecen en algún grupo de las tablas anteriores con 5 o más parcelas son de menos de 0.007 de MAE y no se repiten entre escenarios, salvo Chignahuapan; ninguna alcanza el criterio de T03 §4, y sin las 24 dudosas el orden se mantiene casi idéntico, con un cruce por escenario.

### Conclusión

Con o sin centrar por municipio, ninguna variable climática mejora la referencia; es consistente con T09 (en el escenario B y `sin_respaldo`, su corrección con clima da un MAE de 0.362 a 0.372 según la variante, frente a 0.358 de la referencia).

Con esta representación climática y esta corrección Ridge, ninguno de los candidatos mejora la referencia bajo las particiones evaluadas.

La información climática es espacialmente gruesa y muchas parcelas comparten los mismos resúmenes, aunque no todas las parcelas vecinas son climáticamente idénticas.

Gran parte de la señal climática está asociada a la estructura territorial que ya captura la referencia municipal, aunque existe variación climática dentro de los municipios; en este experimento esa variación adicional no produjo una mejora predictiva detectable.

Por tanto se conserva la referencia `media_mun__resp_grupo` y no se promueve el clima bajo la regla de T03 §4 con este estimador (Ridge sobre el residuo, con y sin centrado).

## Límites

- Una sola temporada (2025): el clima varía entre zonas, pero no entre años dentro de los datos etiquetados.
- El clima casi coincide con el municipio, y la referencia ya captura el nivel de cada municipio.
- α = 10 000 es el techo de la rejilla y se eligió en más de la mitad de los ajustes: el modelo prefiere quedarse cerca de la referencia. Con variables centradas por municipio la conclusión no cambia.
- Un solo estimador (Ridge sobre el residuo de la referencia) y selección interna de α por partición aleatoria estratificada, incluso en B (T03 §5); otros estimadores quedan para T09 y T15.
- Resultado válido para esta ventana y estas 6 variables; otras ventanas (por ejemplo, alrededor de la floración) quedan fuera del presupuesto.
