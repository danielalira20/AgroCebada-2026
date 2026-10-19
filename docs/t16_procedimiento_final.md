# T16 · Procedimiento final: mediana municipal (propuesta de excepción a T03)

18 de octubre de 2026 · Redacta: Jass · Estado: **PROPUESTA. Solo queda vigente si Dani y Migue la aprueban en el PR** (decisión `D_T16_DECISION_001`). Este documento no atribuye aprobación a nadie.

Base: rama `t16-modelo-v1` (incluye T15 y la revisión de Dani del 16-oct, y `dev` a esa fecha). Predicciones de partida: `registro/t03/predicciones_59_referencias.csv`, versión `T08-v1`.

## 1. En corto

- **Qué se propone:** que el modelo final para las 59 parcelas sea la **mediana municipal** (`mediana_mun__resp_grupo`): cada parcela recibe la mediana del rendimiento de las parcelas con cosecha de su mismo municipio.
- **Por qué:** es la que tiene el menor MAE en la población que decide (A/sin_respaldo: 0.312585 t/ha frente a 0.320490 de la media) y ningún modelo con clima, satélite, relieve o ensambles la supera.
- **Lo que NO se dice:** que sea una mejora confirmada. **No cumple la regla de T03**: la mejora (−0.0079 t/ha) no llega al umbral de −0.01 y el intervalo por celdas cruza cero. Adoptarla es una **excepción explícita**, decidida **después** de ver los resultados.
- **Frase segura para el informe:** «Entre las referencias municipales evaluadas, la mediana obtuvo el menor MAE (0.3126 frente a 0.3205 t/ha en validación sobre 135 parcelas). La diferencia es pequeña y su intervalo de incertidumbre incluye cero, por lo que se adopta como decisión práctica y no como mejora estadísticamente confirmada.»

## 2. Ficha de decisión

En corto: aquí están, en una sola tabla, las piezas que el plan pide dejar escritas al cerrar T16.

| Renglón | Valor | Fuente |
|---|---|---|
| Procedimiento elegido | `mediana_mun__resp_grupo` (T08-v1) | `scripts/t08_referencias.py` |
| Métrica primaria | MAE; RMSE como control. **FIRA no ha confirmado por escrito qué métrica usará** (las bases dicen «RMSE, MAE, r² u otras definidas por el Comité») | T03 §4; bases |
| Umbral de diferencia práctica | ΔMAE ≤ −0.01 t/ha | T03 §4 |
| Estabilidad entre repeticiones | mejora en ≥ 4 de 5. Resultado: 5 de 5 | T03 §4 |
| Población que decide | A/sin_respaldo: 135 parcelas, 675 predicciones fuera de entrenamiento | D019 |
| Desempate de T03 | si nada cumple la regla gana el procedimiento más simple, y D019 conservó la media. **Aquí nos desviamos de ese desempate** | T03 §4; D019 |
| Disponibilidad para las 59 | 59 IDs, 59 predicciones finitas, las 59 con fuente `municipio` (no se activa ningún respaldo) | `predicciones_59_referencias.csv` |
| Diferencia frente a la referencia | ΔMAE −0.007905 t/ha; IC95 por celdas [−0.016298, +0.005805] | `registro/t16_revision_mediana/contrastes.csv` |
| Rivales | ver secciones 7 y 8 | |

## 3. Procedimiento congelado

En corto: no hay modelo con variables; es un valor típico por municipio.

- **Predicción:** mediana de `RENDIMIENTO_T_HA` de las parcelas de ENTRENAMIENTO del mismo municipio (138 etiquetas).
- **Respaldo** si un municipio no tuviera etiquetas: mediana de su grupo de registro (`Cebada`/`CEBADA`) y, si tampoco, mediana global. **En las 59 no se activa nunca.**
- **Entradas:** solo las 138 etiquetas del CSV oficial de FIRA (`ID_area_rendimiento_70_30_Reto_AgroCebada.csv`) y el municipio y grupo de registro de cada parcela. No entran clima, satélite, relieve ni área.
- **Caso AGC_120** (Nanacamilpa): tiene una sola etiqueta; su predicción, 2.5 t/ha, es la etiqueta de AGC_048, a 1.9 km.
- **Comprobación independiente (18-oct):** se recalculó la mediana por municipio directamente desde el CSV oficial y se comparó con las 59 predicciones de `T08-v1`: diferencia máxima 0. Las etiquetas de `registro/t07/tabla_comun.csv` coinciden con las del CSV oficial (138), y los 59 IDs son exactamente los del conjunto PREDICCION.
- **Pendiente:** reproducir la generación completa en Docker `--amd64` y sellarla en T18 (commit, huellas de datos y fecha). Este documento no afirma que eso ya se hizo.

## 4. Evidencia

En corto: la mediana gana por poco y de forma consistente, pero el margen es menor que la incertidumbre.

**Población que decide (A/sin_respaldo, 135 parcelas, 675 predicciones).** MAE y RMSE en t/ha; RMSE y R² son promedio por repetición.

| | MAE | RMSE | R² | Sesgo |
|---|---:|---:|---:|---:|
| Media municipal (referencia vigente) | 0.320490 | 0.492593 | 0.658577 | +0.000338 |
| Mediana municipal | 0.312585 | 0.490683 | 0.661223 | +0.038037 |
| Diferencia (mediana − media) | −0.007905 | −0.001910 | | |

Intervalo: 5,000 remuestras por celdas CHIRPS, semilla 20261006, 22 celdas. A nivel de parcela, 86 mejoran, 45 empeoran y 4 empatan.

**Las cuatro condiciones de T03 §4:**

| Condición | Resultado de la mediana | ¿Cumple? |
|---|---|---|
| ΔMAE ≤ −0.01 | −0.007905 | No |
| Cota superior del IC95 por celdas < 0 | [−0.016298, +0.005805] | No |
| Mejora en ≥ 4 de 5 repeticiones | 5 de 5 | Sí |
| ΔRMSE ≤ +0.01 | −0.001910 | Sí |

**Otras poblaciones (no deciden; se muestran por separado para no mezclarlas):**

| Escenario / población | Parcelas | MAE media → mediana | ΔMAE | IC95 por celdas |
|---|---:|---|---:|---|
| A / todas | 138 | 0.319250 → 0.309703 | −0.009547 | [−0.018213, +0.002877] |
| B / sin_respaldo | 135 | 0.363187 → 0.347481 | −0.015706 | [−0.044325, +0.020661] |
| B / todas | 138 | 0.380101 → 0.363007 | −0.017093 | [−0.044694, +0.017115] |

En B/sin_respaldo el ΔMAE sí pasa el umbral de −0.01, pero el intervalo cruza cero. Según T03 §4, solo A/sin_respaldo puede acreditar una promoción.

**Tamaño del margen:** el intervalo por celdas mide unos ±0.011 de semiancho; la diferencia observada (0.0079) es menor. Con 138 parcelas no se pueden detectar diferencias de ese tamaño con confianza.

## 5. Dónde gana y dónde pierde

En corto: la mejora viene de dos municipios; en otros dos empeora.

A/sin_respaldo, MAE por municipio (t/ha):

| Municipio | Parcelas | Media | Mediana | ΔMAE |
|---|---:|---:|---:|---:|
| Calpulalpan | 30 | 0.2869 | 0.2667 | −0.0203 |
| Chignahuapan | 71 | 0.3801 | 0.3678 | −0.0123 |
| Almoloya | 10 | 0.1412 | 0.1362 | −0.0050 |
| Cuautepec de Hinojosa | 5 | 0.1430 | 0.1490 | +0.0060 |
| Singuilucan | 16 | 0.3467 | 0.3737 | +0.0271 |
| Emiliano Zapata | 3 | 0.0000 | 0.0000 | 0 (solo 3 parcelas) |

- **Calpulalpan:** sus etiquetas toman solo tres valores (3.0 en 14 parcelas; 3.5 y 2.5 en 8 cada una; todas múltiplos de 0.5). La mediana (3.0) cae en el mejor valor posible: su MAE de 0.2667 es el piso para un solo número en ese municipio. Parte de la ventaja viene, entonces, del redondeo de las etiquetas.
- **Sesgo:** la mediana sobreestima en promedio (+0.038 t/ha); la media casi no tiene sesgo.
- **Sin las 24 parcelas con alerta de contorno** (111 parcelas): ΔMAE −0.004288, IC95 [−0.012450, +0.008490], mejora en solo 3 de 5 repeticiones y el RMSE empeora +0.002445.
- **Quitar una celda a la vez** (solo del resumen): el ΔMAE queda entre −0.009971 y −0.002821. Conserva el signo, pero nunca llega al umbral.
- **Dónde está el error:** 62 % del error de la referencia está en Chignahuapan, y las 10 parcelas con más error concentran 30 %. El mejor MAE posible con un solo valor por municipio es ≈0.3004 (calculado con las mismas etiquetas que se evalúan, así que es optimista).

## 6. Efecto sobre las 59

En corto: cambian 44 de las 59, todas hacia arriba, y casi todo el cambio está en dos municipios.

| Municipio | Parcelas a predecir | Media | Mediana |
|---|---:|---:|---:|
| Chignahuapan (Puebla) | 29 | 4.477 | 4.520 |
| Calpulalpan (Tlaxcala) | 14 | 3.000 | 3.000 |
| Singuilucan (Hidalgo) | 7 | 3.081 | 3.200 |
| Almoloya (Hidalgo) | 4 | 4.521 | 4.530 |
| Cuautepec de Hinojosa (Hidalgo) | 4 | 4.598 | 4.610 |
| Nanacamilpa (Tlaxcala) | 1 | 2.500 | 2.500 |

Singuilucan es el municipio donde más sube la predicción (+0.12 t/ha) y justo donde la mediana validó peor (+0.0271 de MAE).

## 7. Rivales con variables (T09–T15)

En corto: ningún bloque de variables llegó siquiera a la media, menos a la mediana.

T15 comparó ocho procedimientos con la misma evaluación (A/sin_respaldo, contra la media). Ninguno cumple la regla de promoción (`D_T15_COMPLETA_001`):

| Procedimiento | MAE | ΔMAE frente a la media |
|---|---:|---:|
| Referencia municipal (media) | 0.320490 | 0 |
| Clima | 0.322328 | +0.001838 |
| Relieve y área | 0.323662 | +0.003172 |
| Planet | 0.322987 | +0.002497 |
| Clima + relieve/área | 0.322684 | +0.002195 |
| Clima + Planet | 0.323068 | +0.002579 |
| Relieve/área + Planet | 0.320189 | −0.000300 |
| Clima + relieve/área + Planet | 0.320428 | −0.000062 |
| Sentinel-2 | 0.321670 | +0.001180 |

El mejor (Relieve/área + Planet) queda en 0.3202; la mediana, en 0.3126. También quedan sin promoverse el clima de T09 (`D_T09_EVAL_001`) y de T14 (`D_T14_001`). La **mediana contraída** de T08 eligió «sin contracción» (k = 0) en 48 de 51 ajustes, así que coincide con la mediana en A y empeora en B.

## 8. Búsquedas posteriores a los resultados (exploratorias)

En corto: se intentó bajar el MAE por debajo de la mediana en cinco rondas; ninguna lo logró. **Todo esto se hizo después de conocer los resultados de T08–T15, y se reporta como exploratorio.**

Cómo se hicieron: cada ronda tiene un archivo de reglas escrito antes de correr, con fecha interna y huella SHA-256. Las huellas de los seis archivos coinciden con su contenido actual, y las marcas de tiempo de los archivos de resultados son posteriores a las de sus reglas (la ronda 5 quedó en el mismo minuto). No hay sello de tiempo externo, así que esto es evidencia razonable pero no una pre-inscripción verificable por terceros. **Los scripts, reglas y resultados están en carpetas locales que Git ignora (`context/` y `reports/`); un revisor no puede reproducirlos desde el repo.**

MAE en A/sin_respaldo (135 parcelas), mismas particiones de T15. «Δ vs M0» es frente a la mediana sola. Ninguna cumple la regla de T03 contra la media.

| Intento | MAE | Δ vs media | Δ vs M0 |
|---|---:|---:|---:|
| Media (vigente) | 0.3205 | 0 | +0.0079 |
| Mediana sola (M0) | 0.3126 | −0.0079 | 0 |
| H1: verdor Sentinel-2, sobre la media | 0.3177 | −0.0028 | ≈ +0.0051 |
| H2: verdor compuesto, sobre la media | 0.3170 | −0.0035 | ≈ +0.0044 |
| MH2: mediana + H2 | 0.3148 | −0.0057 | +0.0022 |
| E1: promedio de M0, H1 y H2 | 0.3137 | −0.0068 | +0.0011 |
| E2: E1 más MH2 | 0.3132 | −0.0073 | +0.0007 |
| E3: promedio de M0, vecinas, Ridge clima/relieve y boosting de satélite | 0.3209 | +0.0004 | +0.0083 |
| MH3: mediana + labranza y residuos antes de sembrar | 0.3130 | −0.0075 | +0.0004 |
| MH4: mediana + historial de NDVI 2022–2024 | 0.3130 | −0.0075 | +0.0004 |

- Con las 8 pruebas (H1, H2, MH2, E1, E2, E3, MH3, MH4) ningún intervalo con corrección de Bonferroni queda por debajo de cero.
- Los ensambles tienen errores casi idénticos entre sí (correlación 0.989–0.998), por eso promediarlos no aporta. En MH3 y MH4 la selección interna eligió «referencia sola» en 18 y 24 de 25 ajustes: en la práctica son la mediana.
- Los miembros nuevos de E3 son peores que la mediana por sí solos (vecinas 0.3515, boosting 0.3394).
- **Chequeo con bosque aleatorio** (300 árboles, particiones A de T03, solo exploratorio, no decide): solo satélite MAE 0.429 (R² 0.51); satélite + clima + relieve sin municipio 0.403; solo municipio 0.343; todo + municipio 0.398. El municipio explica cerca de 69 % de la varianza del rendimiento (la parte «dentro del municipio» es 31 %). Las variables que más usa el bosque son de zona (temperatura mínima, lluvia, nubosidad, número de capturas), no de cultivo.

## 9. Por qué es una excepción y no una mejora

En corto: hay buenas razones para elegirla y buenas razones para no hacerlo; el equipo decide con eso a la vista.

**A favor de adoptarla**
- Menor MAE en las dos poblaciones principales de A y en B, con mejora en 5 de 5 repeticiones; RMSE y R² tampoco empeoran.
- Es lo más simple: no necesita entradas extra ni ajustes con variables.
- Todos los intentos de mejora quedan en 0.3130 o más; ninguno la supera.
- La diferencia práctica con la media es pequeña (≈0.008 t/ha), así que equivocarse en cualquiera de las dos direcciones cuesta poco.

**En contra, o lo que no sabemos**
- No cumple dos de las cuatro condiciones de T03, y el intervalo por celdas cruza cero.
- Si FIRA califica con RMSE, la ventaja es de apenas −0.0019.
- La ventaja se concentra en Calpulalpan (etiquetas redondeadas) y Chignahuapan; en Singuilucan y Cuautepec empeora.
- Sin las 24 parcelas con alerta, la mejora baja a la mitad y el RMSE empeora.
- Sobreestima en promedio (+0.038 t/ha).
- Se elige después de ver los resultados.

**Cómo ha cambiado la regla desde T08 (hechos del registro, sin interpretarlos)**
- `D018` (7-oct, Migue): la regla pasó de usar el intervalo por parcelas a usar el intervalo por celdas. Lo escribió después de ver los resultados de T08 y lo describe como más estricto. En A/sin_respaldo el intervalo por parcelas de la mediana es [−0.0159, +0.0002], así que tampoco cumpliría con ese criterio. En B/sin_respaldo el intervalo por parcelas ([−0.0281, −0.0039]) sí excluiría cero.
- `D019` (8-oct, Migue, a partir de la revisión de Daf): la referencia pasó a `media_mun__resp_grupo` y la decisión se toma en sin_respaldo. En «todas» y frente a la base de entonces (`media_mun__resp_global`) la mediana sí cumplía (ΔMAE −0.0254); casi toda esa ventaja venía de 15 predicciones con respaldo en tres parcelas que no representan a las 59.
- En ambos casos el cambio fue hacia una regla más exigente para la mediana.

## 10. Límites y alcance

- **Una sola campaña** (2025) y una sola cosecha por parcela: el modelo no puede aprender el efecto del año. No predice otros años.
- **Territorio:** Hidalgo, Puebla y Tlaxcala, y en la práctica solo los seis municipios donde están las 59 y que tienen etiquetas.
- **138 etiquetas.** No hay información de manejo, fecha de siembra ni variedad, y FIRA no entregará más datos.
- **Etiquetas redondeadas** en varios municipios (Calpulalpan: todas múltiplos de 0.5; Singuilucan: 56 %).
- **24 parcelas con alerta de contorno** (T03).
- **Municipios nuevos (sensibilidad descriptiva, no afecta a las 59):** al dejar un municipio completo fuera (9 municipios, 138 parcelas), la media global tuvo MAE 1.067; la mediana global, 1.209 (peor, mejora en solo 3 de 9); la media global más un Ridge con lluvia, temperaturas y elevación, 0.577 (mejora en 7 de 9). Con 9 municipios es solo orientativo. Consecuencia para la app: para un municipio sin etiquetas, la mediana **no** es un buen respaldo.
- **No usa percepción remota en la predicción.** Esto es importante para el informe: la evidencia (secciones 7 y 8) muestra que, con estos datos y 138 parcelas, el satélite no aporta sobre la referencia municipal, pero el modelo final no es un modelo satelital.

## 11. Pendientes abiertos

1. Aprobación de la excepción por Dani y Migue en el PR (o, si no la aprueban, se conserva la media).
2. Confirmación de la métrica por parte de FIRA: no existe por escrito.
3. T18: formato de entrega de las 59 (las bases no lo fijan), reproducción en Docker `--amd64` y archivo de trazabilidad.
4. Decidir qué se hace con las búsquedas exploratorias (subirlas al repo o declararlas como no reproducibles desde él).
5. Al fusionar con `dev` (donde todavía no está T15): revisar conflictos en `registro/decisiones.csv`, `experimentos.csv` y `uso_ia.csv`.
6. Corregir en T03 la fila de AGC_120 («se activa respaldo»): `docs/t09_decisiones.md` ya señaló que no se activa.
7. App: cambiar `MODELO_OFICIAL` solo cuando la decisión esté aprobada.

## 12. Fuentes consultadas

`docs/t16_revision_mediana.md` y `registro/t16_revision_mediana/` (metricas, contrastes, por_municipio, influencia_celdas) · `registro/t03/comparacion_emparejada.csv` y `predicciones_59_referencias.csv` · `docs/T08_referencias.md` · `docs/T03_protocolo_evaluacion.md` · `docs/t15_resultados.md` · `registro/decisiones.csv` (D018, D019, D_T09_EVAL_001, D_T14_001, D_T15_COMPLETA_001, D_T16_REVISION_001, D_T16_DECISION_001) · `registro/t07/tabla_comun.csv` · CSV oficial de FIRA · reglas y resultados locales de las rondas 0–5 (`context/Agrocebada/Fase*-reglas-*.md` y `reports/fase*`, no versionados).
