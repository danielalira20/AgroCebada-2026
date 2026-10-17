# T10 · Aporte de relieve y área sobre la referencia territorial

- **Responsable:** Jass. **Revisora:** Daf.
- **Estado (12 de octubre de 2026):** ejecutado; en revisión de Daf. Diseño escrito **antes de correr** (decisión `D_T10_001`), con correcciones de implementación y aclaraciones documentadas **después de los resultados y de la auditoría con Codex** (nota en la sección 7 y decisión `D_T10_002`). Resultado en la sección 13; informe de cierre en `analisis/aporte_relieve_y_area/informe_relieve_y_area.md`.
- **Actualización del 15 de octubre de 2026 (posterior a los resultados, `D_T10_004`):** se distinguen las configuraciones sin centrar (1–5) de la centrada (6) y se fija cómo entran relieve y área en las comparaciones nuevas (sección 15). No cambia ninguna cifra, predicción ni código.
- **Usa:** T03 (particiones, subconjuntos y regla de decisión), T05 (relieve), T07 (tabla común) y T08 (referencia `media_mun__resp_grupo`, D019).
- **Plan:** «T10 · relieve y área: territorio frente a territorio + relieve/área; sensibilidad a tamaño y cobertura parcial. Entregar predicciones y errores». Anexo de selección de atributos (11 de octubre): «comparar aporte sobre territorio; revisar relación entre relieve, área y ubicación y sensibilidad a calidad».

## 1. Pregunta

¿Conocer la elevación, la pendiente y el tamaño de una parcela mejora la estimación que da el promedio de su municipio? ¿Esa mejora se sostiene en las parcelas pequeñas y en las de cobertura parcial?

En palabras sencillas: la referencia tasa una casa con el promedio de su colonia. T10 pregunta si conocer los metros y la inclinación del terreno afina el precio o solo añade ruido.

## 2. Lo que ya se vio antes (declaración)

Este diseño **no es ciego**. Durante la comprensión del dataset (antes del plan de tareas) se correlacionaron con el rendimiento, usando las 138 etiquetas y restando el promedio de cada municipio, cientos de resúmenes por parcela, entre ellos relieve y área. Lo más constante, aunque débil, fue la pendiente (+0.26) y el área en logaritmo (−0.25); la prueba de permutación sobre el máximo dio p = 0.22. Además, T02 (`desviacion_por_tamano.csv`) encontró que en Chignahuapan las parcelas de más de 5 ha quedan en promedio 0.23 t/ha bajo la media municipal.

Para que eso no incline el resultado:

- se prueban las tres variables, no solo las dos que parecían relacionadas;
- cada transformación se justifica sin usar rendimientos (sección 3);
- todas las configuraciones se reportan, ganen o no;
- una mejora solo cuenta si cumple la regla de T03 §4 y, además, el control de revuelto (sección 8).

## 3. Entradas

Todas salen de `registro/t07/tabla_comun.csv` y se unen por `id_parcela`, nunca por posición.

| Columna | Transformación | Razón (sin rendimientos) |
|---|---|---|
| `elevacion_media_m` | ninguna | Sin faltantes; de 2,497 a 2,906 m s.n.m. |
| `pendiente_media_t10_grados` | ninguna; los 2 faltantes (AGC_023 y AGC_170, piso D020) se rellenan con la **mediana del entrenamiento** de cada partición | El vacío no significa cero; el relleno se aprende sólo con entrenamiento. |
| `area_ha_origen` | logaritmo natural | Va de 0.35 a 64.3 ha y su desviación estándar (7.4 ha) supera a su media (6.6 ha): unas pocas parcelas grandes dominarían la escala. |

- **No entran:** las áreas alternativas (`area_ha_geodesica`, `area_parcela_6372_m2`; contrato `area_t10`), extremos, coberturas, conteos de celdas o avisos de relieve, ni ninguna columna de clima o satélite.
- **Las 59 reservadas** tienen las tres variables completas. Tres quedan apenas fuera del rango de las etiquetadas, cada una en una sola variable: AGC_088 en elevación (2,906.0 m; máximo etiquetado 2,904.0 m), AGC_153 en pendiente (0.282°; mínimo 0.288°) y AGC_091 en área (0.35 ha; mínimo 0.38 ha). Estos valores no alteran las predicciones finales de T10 porque las seis configuraciones eligen «referencia sola»; esto no demuestra que la extrapolación sea inocua para otro modelo. El pendiente y sus criterios de aceptación para T17 están en [T10_seguimiento_T17.md](T10_seguimiento_T17.md).
- **Relación con la ubicación, sin rendimientos (138 etiquetadas; `registro/t10/diagnostico_atributos_t10.csv`):** el municipio explica el 28 % de la variación de la elevación, el 13 % de la pendiente y el 15 % del logaritmo del área (el 53 % del área sin logaritmo: unas pocas parcelas grandes concentradas en pocos municipios dominan esa escala). Correlaciones entre variables: elevación–pendiente 0.51, pendiente–log del área −0.30 y elevación–log del área −0.09.

## 4. Procedimiento principal

1. **Predicción** = referencia `media_mun__resp_grupo` + Ridge ajustado al residuo. El residuo es *rendimiento real − referencia calculada sin esa fila* (O4).
2. **Comprobación previa:** la referencia de T10 debe reproducir las 1,380 predicciones fuera del entrenamiento de T08 (`registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv`), con las mismas fuentes de respaldo.
3. **Selección interna (T03 §5):** 4 particiones dentro de cada entrenamiento externo, semilla 0, estrato = municipio con al menos 4 etiquetas en ese entrenamiento; si no, `otros`. Dentro de cada partición interna se recalculan referencia, residuo, relleno, escalado y centrado con su parte de entrenamiento, sin tocar su parte de validación.
4. **Opciones que compiten en la selección interna:** «referencia sola» (Ridge apagado) y α ∈ {0.1, 1, 3, 10, 30, 100, 300, 1000, 10000}. Incluir la referencia sola atiende O7: una penalización grande no apaga necesariamente las variables.
5. **Criterio de la selección interna:** error absoluto del rendimiento en la parte de validación, porque la métrica primaria de T03 es el MAE. Empate: gana lo más simple, primero «referencia sola» y después el α más grande.
6. Con la opción elegida se reajusta en el entrenamiento externo completo y se predice una sola vez su partición de evaluación.

**Relación con T11 v2 (D021–D022):** el principal cambia las opciones y el criterio de los puntos 4 y 5. T10 también incorpora imputación para las pendientes faltantes; T11 no admite faltantes. La comprobación empírica del puente alcanzó 100/100 elecciones de α en las configuraciones 1 y 3; no se verificó equivalencia en las configuraciones con pendiente ni equivalencia completa de predicciones.

**Referencia documental fijada el 12 de octubre de 2026 (punto 7 del PR):** D021 y D022 se consultaron en el commit `bfa525d003c535349ff586ebea4a51e2487a513e` de `t11-aporte-satelital`: [decisiones de T11](https://github.com/danielalira20/AgroCebada-2026/blob/bfa525d003c535349ff586ebea4a51e2487a513e/registro/decisiones.csv), [método](https://github.com/danielalira20/AgroCebada-2026/blob/bfa525d003c535349ff586ebea4a51e2487a513e/docs/T11_aporte_satelital.md) y [código](https://github.com/danielalira20/AgroCebada-2026/blob/bfa525d003c535349ff586ebea4a51e2487a513e/scripts/t11_aporte_satelital.py). Son referencias externas a esta rama; ese commit no está integrado en la referencia local de `dev` consultada. Esta fijación documental posterior permite resolver las citas de `D_T10_001` y `D_T10_002` sin esperar la fusión de T11; no identifica retrospectivamente el commit usado en la comprobación original de α ni acredita cambios posteriores de T11. Al integrar, conservar las decisiones de ambas tareas. Véase `D_T10_003`.

## 5. Configuraciones (presupuesto: 6 de 8)

| # | Variables además del territorio | ¿Centrada por municipio? | Qué mide |
|---|---|---|---|
| 1 | Elevación | No | Si la variable tal cual mejora la referencia. Mezcla «dónde está la parcela» con «cómo es frente a las de su municipio». |
| 2 | Pendiente | No | Igual que la 1. |
| 3 | Área (logaritmo) | No | Igual que la 1. |
| 4 | Relieve: elevación + pendiente | No | Igual que la 1. |
| 5 | Relieve + área | No | Igual que la 1. |
| 6 | Relieve + área, cada variable centrada con la media de su municipio en el entrenamiento (si el municipio no está en el entrenamiento, con la media global) | Sí | Si una parcela más alta, más inclinada o más grande que el promedio de su municipio rinde distinto: el aporte dentro del municipio. |

La configuración 6 separa «cómo es la parcela frente a las de su municipio» de «dónde está». Las 2 configuraciones restantes del presupuesto **no se usan**: no hay otra pregunta que justifique gastarlas, y no se agregan después de ver resultados.

**Nota del 15 de octubre de 2026 (`D_T10_004`):** las columnas «¿Centrada por municipio?» y «Qué mide» se añadieron después de los resultados, a partir de la observación H3 de Dani. Las configuraciones corridas no cambian. Ver la sección 15.

## 6. Procedimiento puente (descriptivo)

Las 6 configuraciones se corren también con un puente basado en T11 v2 (sin «referencia sola»; α elegido por error cuadrático; empate al α más grande), con la imputación de T10 y el alcance de equivalencia descrito en la sección 4. Sus resultados se guardan con `procedimiento = puente_t11`, junto a los del principal (`procedimiento = t10`), y una tabla compara ambos.

**El puente nunca decide:** no puede promoverse ni cambiar la conclusión de T10, y no consume presupuesto de búsqueda porque ninguna de sus configuraciones es elegible. Sirve para que T15 combine con T11 sin rehacer nada y para medir cuánto cambian los resultados por el procedimiento.

## 7. Evaluación (T03 §4)

**Nota de trazabilidad — 12 de octubre de 2026, posterior a los resultados.** Las secciones 7–8 se editaron después de la auditoría con Codex para hacer explícita la promoción sólo en A y la decisión en dos tiempos (`candidata_a_promover` y `promueve`, condicionada a superar el control de revuelto). En esa misma corrección se ajustaron los desgloses de la sección 9 para calcular las métricas por repetición y después promediarlas. Son correcciones de la implementación para cumplir T03 y el diseño registrado en `D_T10_001`; esta redacción actual no debe interpretarse como la versión íntegra anterior a la evaluación. Tras volver a evaluar, se actualizaron `comparacion_emparejada_t10.csv`, `desglose_error_t10.csv` y `manifest.json`; las predicciones no cambiaron y ninguna configuración promovía antes ni después. Véanse `D_T10_002` e `IA_T10_002`, y la entrada «Correcciones tras la auditoría externa (Codex): decisión y desgloses» en [la bitácora](../analisis/aporte_relieve_y_area/bitacora.md).

- Escenario A (principal) y B (sensibilidad obligatoria), 5 repeticiones, particiones de `registro/t03/particiones.csv`.
- MAE (primaria), RMSE, sesgo y R², por repetición y después promediados; subconjuntos `todas` y `sin_respaldo`.
- `MAE_sd_rep` es la desviación estándar de los MAE por repetición con divisor N (`ddof=0`), igual que T08; también se aplica a los desgloses y a `MAE_sd_rep_sin24` en la sensibilidad. Describe dispersión entre repeticiones, no un error estándar ni un intervalo de confianza. Se alineó el 12 de octubre de 2026 tras el comentario 4 del PR; antes T10 usaba `ddof=1`. Las predicciones y la decisión de promoción permanecen idénticas.
- **Regla de promoción, en `sin_respaldo` y en el escenario A (el B es sensibilidad y no promueve por sí solo):** ΔMAE ≤ −0.01 t/ha frente a la referencia; límite superior de `IC95_celdas` < 0 (bootstrap por celdas CHIRPS, 5,000 réplicas, semilla 20261006); mismo signo en al menos 4 de 5 repeticiones; y el RMSE no empeora más de 0.01 t/ha. Si nada la cumple, se conserva la referencia.
- **Comparaciones descriptivas (no deciden):** 5 frente a 4 (¿el área añade algo al relieve?) y 6 frente a 5 (¿aporta «dónde está» o «cómo es»?).

## 8. Control de revuelto (sólo si alguna configuración cumple la regla)

La decisión va en dos tiempos: una configuración es `candidata_a_promover` si el procedimiento principal cumple la regla de la sección 7 en `sin_respaldo` y en A; `promueve` sólo si además supera este control. El puente y el subconjunto `todas` nunca promueven. Cada fila de `comparacion_emparejada_t10.csv` guarda `candidata_a_promover`, `supera_revuelto` y `motivo`.

Se repite la evaluación completa de esa configuración 20 veces, revolviendo sus variables al azar entre las parcelas etiquetadas de un mismo municipio (semilla 20261012). Se reporta la fracción de revueltos con ΔMAE igual o mejor que el observado. Si esa fracción es mayor que 0.05 (2 o más de 20), la mejora **no se promueve** y se informa como no distinguible del azar.

## 9. Sensibilidad a tamaño y cobertura

Error de la referencia y de cada configuración desglosado por:

- **Tamaño:** menos de 2 ha, 2 a 5 ha y más de 5 ha (los cortes de T02), y la marca de parcela menor a una celda de 120 m (1.44 ha).
- **Cobertura de relieve:** las 5 etiquetadas con cobertura parcial (AGC_020, 023, 044, 164 y 170) y las que tienen 4 celdas válidas o menos.
- **Desgloses obligatorios de T03 §4 bis:** municipio, grupo de registro, contorno A frente a B o C, angosta o muy pequeña, escalón de la etiqueta y vecina etiquetada a menos de 20 m; con la marca de grupo poco informativo cuando tenga menos de 5 parcelas.
- **Sensibilidad sin las 24** parcelas con alerta de contorno.

**Control del pendiente P06:** si el aporte del área se concentra en los contornos B o C, se informa como sospecha de efecto de medición (un error en el área usada como denominador del rendimiento produce una relación negativa aparente), no como señal agronómica.

## 10. Diagnóstico de atributos

- **Sin rendimientos (antes de evaluar):** cuánto explica el municipio a cada variable, correlaciones entre las tres variables y reservadas fuera del rango de las etiquetadas.
- **Con rendimientos (después de evaluar, exploratorio):** Pearson de cada variable con el rendimiento, global y dentro de municipio, con número de pares y gráficos de puntos. No decide nada (anexo de selección, §2.2).
- **De la selección:** frecuencia con que se eligió «referencia sola» y cada α, por configuración y escenario. Es descriptiva, no una probabilidad de importancia.

## 11. Entregables

| Qué | Dónde |
|---|---|
| Método (este documento) | `docs/T10_relieve_area.md` |
| Código | `scripts/t10_relieve_area.py` |
| Pruebas sintéticas (19): relleno y centrado sólo con entrenamiento, opción «referencia sola», criterio de empate, formato de salida, lógica de decisión (sólo B, veto del revuelto, puente) y desgloses por repetición; dispersión con `ddof=0` | `tests/test_t10_relieve_area.py` |
| Predicciones fuera del entrenamiento (formato T03 §7 más `procedimiento`, `alfa` y `referencia`), métricas, comparación emparejada, desgloses, sensibilidad sin las 24, coeficientes y α elegidos, diagnóstico sin rendimientos, predicciones de las 59 ajustadas con las 138 (sólo para T16 y la app) y manifiesto con huellas de entradas | `registro/t10/` |
| Bitácora, diagnóstico exploratorio con rendimientos, gráficos e informe de cierre | `analisis/aporte_relieve_y_area/` (se crea con la primera evidencia) |
| Registros | `D_T10_001`–`D_T10_003` en `registro/decisiones.csv`; `E_T10_001`–`E_T10_006` en `registro/experimentos.csv`; `IA_T10_001`–`IA_T10_005` en `registro/uso_ia.csv` |

## 12. Qué no afirma T10

- Que el relieve o el área causen más o menos rendimiento.
- Que el área declarada sea la superficie con la que se calculó el rendimiento (pendiente P06).
- Qué edición del relieve se usó (pendiente P05; ver la bitácora de T05, entrada del 12 de octubre).
- Que el resultado se mantenga en otra campaña: hay una sola campaña etiquetada.

## 13. Resultado

**Ninguna configuración cumple la regla de T03; se conserva la referencia `media_mun__resp_grupo`.** No se corrió el control de revuelto porque nada ganó (sección 8).

Procedimiento principal, subconjunto `sin_respaldo` (referencia: A → MAE 0.3205; B → MAE 0.3579):

| Config | ΔMAE A | IC95 celdas A | Reps que mejoran (A) | ΔRMSE A | ΔMAE B | ΔRMSE B |
|---|---|---|---|---|---|---|
| 1 elevación | +0.0012 | [−0.0006, +0.0044] | 1/5 | −0.0016 | +0.0006 | +0.0001 |
| 2 pendiente | +0.0002 | [−0.0038, +0.0057] | 2/5 | −0.0036 | +0.0025 | +0.0007 |
| 3 área | +0.0014 | [−0.0037, +0.0089] | 2/5 | −0.0026 | +0.0018 | +0.0010 |
| 4 relieve | +0.0006 | [−0.0033, +0.0068] | 2/5 | −0.0038 | +0.0017 | +0.0003 |
| 5 relieve + área | +0.0011 | [−0.0062, +0.0103] | 2/5 | −0.0052 | +0.0028 | +0.0003 |
| 6 centrado | +0.0027 | [−0.0046, +0.0117] | 1/5 | −0.0045 | +0.0022 | +0.0006 |

**Cómo leer la tabla (aclaración del 15 de octubre de 2026, `D_T10_004`).** La referencia ya contiene el promedio de cada municipio. En las configuraciones 1 a 5 las variables entran sin centrar y, como el municipio explica parte de la elevación, la pendiente y el área (sección 3), una parte de la corrección puede volver a ajustar diferencias entre municipios que la referencia ya incluía. Por eso esas cinco dicen si relieve y área *tal cual* mejoran la referencia, pero no deben leerse como aporte dentro del municipio. Sólo la configuración 6 mide ese aporte interno, y tampoco cumple la regla (ΔMAE A +0.0027; 1 de 5 repeticiones). Ni centrando ni sin centrar, relieve y área mejoran la referencia con este procedimiento. Las cifras de la tabla no cambian.

- Ajustado con las 138 parcelas, el procedimiento elige «referencia sola» en las 6 configuraciones: las predicciones para las 59 coinciden con las de T08.
- El puente (T11 v2) empeora el MAE entre +0.0097 y +0.0197 en A; el principal es mejor que el puente en las 12 comparaciones de MAE.
- Con MAE y RMSE intercambiados (si FIRA confirmara RMSE), con las predicciones actuales el principal tampoco llega al umbral (mejor ΔRMSE −0.0052). No se volvió a correr eligiendo el ajuste con error cuadrático.
- Sobre el conteo del presupuesto de T03 §5 (6 subconjuntos de 8; α y «referencia sola» elegidos dentro del entrenamiento; puente fuera del conteo) hay una aclaración posterior a los resultados en `D_T10_002`, pendiente de confirmación de Migue. Ninguna configuración cumple la regla con cualquiera de las lecturas.
- Los desgloses se calculan por repetición y luego se promedian (T03 §4); cada fila trae `n_repeticiones` y `MAE_sd_rep`.
- Desgloses, sensibilidad, tabla de las 5 parcelas con cobertura parcial, ficha de consumo para T16 y exploración con rendimientos: bitácora e informe de cierre.

## 14. Cómo reproducir

**Conteo comprobado el 12 de octubre de 2026:** 272 pruebas en la suite completa (`python -m unittest discover -s tests`), incluidas 19 de T10, todas aprobadas en Docker/Linux sobre una copia temporal del commit `5545bf5`. Se excluyeron los cambios locales de T07; el conteo es específico de esa versión. Los conteos anteriores se conservan como historia.

Desde la raíz del repositorio, con el entorno de `requirements.txt`. No se necesita el dataset: todas las entradas están en `registro/`.

```bash
python -m unittest tests.test_t10_relieve_area -v
python -m scripts.t10_relieve_area --comprobar-referencia
python -m scripts.t10_relieve_area --diagnostico --salida <carpeta_nueva>
python -m scripts.t10_relieve_area --evaluar --salida <carpeta_nueva>
python analisis/aporte_relieve_y_area/scripts/explorar_relacion_con_rendimiento.py
```

Los modos que escriben nunca sobrescriben: para comparar con lo publicado, usar una carpeta nueva y comparar sus archivos con los de `registro/t10/` (el manifiesto guarda la huella de cada uno). El script exploratorio escribe en `analisis/aporte_relieve_y_area/` y se detiene si sus salidas ya existen.

## 15. Uso en comparaciones nuevas

**Escrito el 15 de octubre de 2026, después de los resultados (`D_T10_004`).** Atiende la observación H3 de Dani del 13 de octubre: «las configuraciones 1–5 están sin centrar; la 6 ya está centrada. Conviene distinguirlas en el informe y revisar cuál utilizaremos para las nuevas comparaciones».

**Decisión.** En las comparaciones nuevas (T15), relieve y área entran **centrados por municipio** con el procedimiento común de T15 (versión v3, bloque G: `elevacion_media_m`, `pendiente_media_t10_grados` y el logaritmo de `area_ha_origen`). La razón es la pregunta, no el error: la referencia ya contiene el municipio, así que lo que interesa saber es si una parcela que difiere de las de su municipio rinde distinto. No se eligió mirando qué configuración tuvo menor error: ninguna cumplió la regla.

**La configuración 6 es un antecedente, no el procedimiento de T15.** Usan las mismas tres columnas y la misma idea, pero difieren en:

| Aspecto | T10, configuración 6 | T15 común v3 (bloque G) |
|---|---|---|
| Promedio municipal con el que se centra | Incluye a la propia parcela | Excluye a la propia parcela, igual que la referencia del residuo |
| Municipio sin parcelas en el entrenamiento | Promedio global | Promedio del grupo de registro y, si no hay, global (mismo respaldo que la referencia) |
| Término constante del Ridge | Sí (`Ridge` con intercepto por defecto) | No |
| Penalización | 9 valores fijos de α (0.1 a 10000) | 4 valores de λ (0.01, 0.1, 1 y 10) con α = n·λ |

Por eso las cifras de la configuración 6 no se presentan como resultado del bloque G de T15, ni al revés.

**Qué no cambia.** T10 no se vuelve a correr. El código, las pruebas, los archivos de `registro/t10/` y las predicciones de las 59 (iguales a la referencia de T08) quedan como están. La ficha de consumo para T16 del informe de cierre sigue vigente.

**Estado del procedimiento v3.** Está en revisión en el PR #21 (rama `t15-centrado-municipal`, aún no integrada en `dev`). Si la revisión cambia la forma de centrar, se usa la versión aprobada y se actualiza esta sección; la decisión de que relieve y área entren centrados no cambia.
