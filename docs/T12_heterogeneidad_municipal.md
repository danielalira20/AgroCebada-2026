# T12 · Heterogeneidad municipal y contraste no lineal

- **Implementa:** Jass. **Responsable original de T12:** Diego. **Revisión metodológica:** Migue.
- **Estado (16 de octubre de 2026):** diseño registrado el 15 de octubre **antes de correr** (decisión `D_T12_001`, experimentos `E_T12_001` a `E_T12_008`). **Cerrado el 16 de octubre: resultado R2, se conserva la referencia** (decisión `D_T12_002`; informe en `analisis/heterogeneidad_municipal/`). Este documento no se reescribió después de ver resultados; solo cambió esta línea.
- **Usa:** el procedimiento común v3 de T15 (Dani, PR #21, commit `4afabf0`) sin modificarlo; T03 con la extensión §5 bis (D026, Migue); la referencia T08 `media_mun__resp_grupo` (D019); la tabla común T07.
- **Registro técnico:** `registro/t12/procedimiento_t12.json`. Su huella SHA-256 está en `D_T12_001` y el script la comprueba antes de correr.
- **Plan:** «T12 · contraste no lineal: un candidato pequeño, mismas entradas y evaluación; búsqueda acotada y fallos registrados. Usa T03, T07–T08. No bloquea app ni T16.»

## 1. Pregunta

¿Permitir que la relación entre las variables de una parcela y su desviación del promedio de su municipio **cambie según el municipio**, o que **no sea una línea recta**, mejora la estimación frente a la referencia? ¿Y frente a la misma corrección con una sola relación para todos?

Todas las correcciones de T08 a T15 usan una sola pendiente para todos los municipios. Cambian las variables, pero no la forma de usarlas. Si una variable empuja el rendimiento hacia arriba en un municipio y hacia abajo en otro, una sola pendiente las promedia y la variable parece inútil. T12 prueba la forma del modelo y deja fijas las variables y las reglas.

## 2. Lo que ya se vio antes (declaración)

Este diseño **no es ciego**. Antes de escribirlo se conocían:

- **Los resultados de T08 a T15.** Ninguna corrección supera a la referencia en A/`sin_respaldo`. Las mejores cifras en B salen con variables centradas: T11 configuración 8, −0.0028; T14 Tmax centrado con internas por celda, −0.0079. Ninguna cumple la regla.
- **T10 configuración 6** (relieve y área centrados, pendiente común): A/`sin_respaldo` ΔMAE +0.0027. Es, aproximadamente, el control `t12_control_comun_G`.
- **Correlaciones dentro del municipio con las 138 etiquetas.** Se eligieron entre unas 40 variables, así que pueden estar infladas:
  - en Chignahuapan, integral de NDVI −0.30, pendiente +0.31 y log(área) −0.27;
  - en Singuilucan, NDVI máximo Planet +0.63.

  **Estas cifras son las que motivan la hipótesis de pendiente por municipio. No la prueban.**
- **Media frente a mediana como referencia.** T08 da ΔMAE −0.0079 en A/`sin_respaldo` (IC95 celdas −0.0163 a +0.0058), que no cumple la regla. Un cálculo simplificado del 15 de octubre da 0.330 frente a 0.323. Por eso se mantiene la media y la mediana va como control (sección 6).
- **Qué parte de la variación de cada variable está dentro del municipio.** Se calculó sin rendimientos, con los 197 IDs:

  | Variable | Dentro del municipio |
  |---|---:|
  | Pendiente | 90 % |
  | log(área) | 87 % |
  | Planet | 71–85 % |
  | Elevación | 77 % |
  | Tmax | 77 % |
  | Lluvia | 38 % |
  | Tmin | 13 % |

**No se ha visto ningún resultado de las familias `het` ni `gb`.**

Para que lo anterior no incline el resultado:

- solo un procedimiento puede promoverse, y se fijó por razón, no por resultado (sección 6);
- se exige además el control de revuelto (sección 8);
- todos los procedimientos se reportan, ganen o no;
- nada del diseño se cambia después de ver resultados. Si algo falla, se registra como falla.

## 3. Qué se hereda de T15 v3 sin cambios

| Elemento | Qué es |
|---|---|
| Datos | `registro/t07/tabla_comun.csv`: 197 IDs, 138 etiquetas y 59 sin etiqueta |
| Particiones externas | `registro/t03/particiones.csv`: A y B, 5 repeticiones × 5 particiones = 50 contextos |
| Referencia | `media_mun__resp_grupo` (D019), con respaldo municipio → grupo de registro → global |
| Residuo | Valor real menos la referencia calculada **sin la propia fila** (`residuos_loo`) |
| Transformaciones | log del área, mediana de la pendiente con indicador (D020) y estandarización, todo aprendido solo en el entrenamiento |
| Centro | v3: el mismo grupo de IDs que la referencia, sin la fila. Al predecir se usa el centro del entrenamiento completo |
| Intercepto | Ninguno |
| Internas en A | 4 particiones estratificadas por municipio, semilla 0, estrato `otros` |
| Internas en B | 4 particiones por celda CHIRPS, sin barajar (T03 §5 bis, D026) |
| MAE interno | Sobre las predicciones internas concatenadas, contando solo las filas cuyo municipio está en el ajuste interno |
| "Referencia sola" | Compite en cada selección interna |
| Comparación externa | `comparar`: ΔMAE por parcela, IC95 por 5,000 remuestreos de celdas (semilla 20261006), repeticiones que mejoran y ΔRMSE |

El código común se **importa**, no se copia ni se modifica. El JSON guarda las huellas de `evaluacion_comun_centrado_loo.py` y `evaluacion_comun_modelo.py` en el commit base:

- Si cambian en la revisión del PR #21 **antes** de ejecutar, se actualizan las huellas en un commit nuevo, antes de correr.
- Si cambian **después**, se repite la ejecución.

## 4. Entradas

| Bloque | Columnas | Por qué entra |
|---|---|---|
| **G** relieve y área | `elevacion_media_m`, `pendiente_media_t10_grados`, `area_ha_origen` (en log). No depende de la ventana | Varía mucho dentro del municipio (77–90 %) |
| **P** Planet compacto | Las 6 de T15 por ventana: `pl_ndvi_max_{v}`, `pl_ndvi_integral_{v}`, `pl_lai2_max_{v}`, `pl_ndvi_dias_sobre_mitad_{v}`, `pl_ndvi_dia_inicio_{v}` y `pl_ndvi_al_corte` | Es el sensor del factorial de T15; varía 71–85 % dentro del municipio |
| **GP** | G + P de la misma ventana | Para ver si se complementan |

La ventana `abr_oct` o `jun_oct` se elige en la selección interna, como en T15.

**Lo que queda fuera, y por qué:**

- Clima: varía entre celdas de unos 5 km, no entre parcelas (T09).
- Sentinel-2: el contraste de sensor es de T15.
- Calidad y nubosidad: son de T11 y T13.
- Vecinas: son la extensión V20 de Daf.

## 5. Familias de modelo

### 5.1 `het`: pendiente común más desviación municipal contraída

La corrección es "pendiente común + ajuste propio del municipio". El ajuste propio solo existe para municipios con suficientes parcelas, y se penaliza más que la pendiente común. Así, si no hay evidencia, el modelo vuelve a la pendiente común de T15, y si tampoco la hay, a la referencia sola.

- Para cada fila *i* del entrenamiento: `r_i ≈ D_i·β + D_i·γ_g(i)`. Aquí `r_i` es el residuo v3, `D_i` son las variables transformadas menos su centro v3, y `γ = 0` para los municipios sin pendiente propia.
- **Penalización:** `n·λ·(‖β‖² + κ·Σ_g ‖γ_g‖²)`, sin intercepto. Se implementa con un solo `Ridge(alpha = n·λ, fit_intercept = False, solver = 'svd')` sobre la matriz `[D | D·1{g=g1}/√κ | D·1{g=g2}/√κ | …]`. Escalar un bloque por `1/√κ` equivale exactamente a penalizarlo κ veces más.
- **Pendiente propia:** solo los municipios con **al menos 12 filas en el entrenamiento externo** del contexto. Los ajustes internos de ese contexto **heredan la misma lista**, para que la selección interna evalúe la misma estructura que se usa fuera. Con las 138, la lista esperada es Chignahuapan, Calpulalpan y Singuilucan.
- **Predicción:** referencia + `D_nueva·(β + γ_m)` si el municipio *m* tiene pendiente propia. Si no, referencia + `D_nueva·β`.
- **Opciones internas:** λ ∈ {0.01, 0.1, 1, 10} × κ ∈ {1, 10} × ventana. Son 16 en P y GP, y 8 en G, más la referencia sola.
- **Desempate**, en este orden: MAE interno a 6 decimales, referencia sola, mayor λ, mayor κ, `jun_oct` y nombre.

### 5.2 `gb`: boosting con pérdida absoluta

Es el contraste no lineal: puede capturar interacciones como "más verde y además con más pendiente".

- `GradientBoostingRegressor(loss='absolute_error', max_depth=2, min_samples_leaf=10, learning_rate=0.05, subsample=0.8, init='zero', random_state=20261015)`.
- **Entradas:** los mismos `D_i` de v3, más indicadores 0/1 de los municipios con pendiente propia (misma regla de 12 filas).
- **Objetivo:** los mismos `r_i`.
- `init='zero'` mantiene la política de no añadir un término constante. Así una mejora no puede venir solo de calibrar.
- **Opciones:** `n_estimators` ∈ {50, 150} × ventana, más la referencia sola.
- **Desempate:** MAE, referencia sola, menos árboles, `jun_oct` y nombre.

## 6. Procedimientos y presupuesto

| Experimento | Procedimiento | Familia | Bloque | Papel | ¿Puede promoverse? |
|---|---|---|---|---|---|
| E_T12_001 | `t12_het_GP` | het | GP | **Principal** | **Sí** |
| E_T12_002 | `t12_het_G` | het | G | Secundario | No |
| E_T12_003 | `t12_het_P` | het | P | Secundario | No |
| E_T12_004 | `t12_gb_GP` | gb | GP | Secundario (no lineal) | No |
| E_T12_005 | `t12_control_comun_GP` | v3 sin cambios | GP | Control de ablación | No |
| E_T12_006 | `t12_control_comun_G` | v3 sin cambios | G | Control de ablación | No |
| E_T12_007 | `t12_control_comun_P` | v3 sin cambios | P | Control de ablación | No |
| E_T12_008 | `t12_control_mediana_het_GP` | het | GP | Control de referencia (mediana) | No |

**Por qué el principal es `t12_het_GP`.** El plan pide "un candidato pequeño", así que se fija uno solo para no ganar por azar entre varios. Se elige `het` porque es la hipótesis con un mecanismo concreto y se puede interpretar: una pendiente por municipio. Se elige GP porque reúne las dos fuentes con más variación dentro del municipio. El boosting queda como contraste secundario: con unas 110 filas por entrenamiento tiene más riesgo de ruido y es más difícil de explicar.

**Presupuesto:**

- Son 8 procedimientos comparados fuera, el máximo de T03 §5. Las opciones internas no cuentan como configuraciones (aclaración del 15 de octubre).
- Los controles `t12_control_comun_X` usan las mismas opciones que `comun_centrado_loo_v3_X` de T15. Si Dani publica antes sus predicciones, se comprueba que coinciden.
- Se reporta que T15 propone otros 8 procedimientos sobre los mismos datos.

**Control de mediana.** Es idéntico a `t12_het_GP`, salvo que la referencia (y por tanto los residuos sin la fila) es la mediana municipal con respaldo grupo → global. Responde si la conclusión depende de usar la media.

## 7. Regla de decisión

**`t12_het_GP` se promueve a T16 solo si cumple las dos condiciones:**

1. La regla de T03 §4 en A/`sin_respaldo`: ΔMAE ≤ −0.01, límite superior del IC95 por celdas < 0, mejora en al menos 4 de 5 repeticiones y ΔRMSE ≤ +0.01.
2. El control de revuelto C2 da p ≤ 0.05.

**Lo demás:**

- B es sensibilidad obligatoria. Se reporta y T16 decide.
- Los secundarios y los controles **nunca se promueven**. Si uno cumple la regla de T03, se reporta como indicio (R2).

## 8. Controles

| # | Control | Cómo se hace | Qué responde |
|---|---|---|---|
| C1 | Ablación | `comparar` de cada `het` contra su `control_comun` del mismo bloque, y de `gb_GP` contra `control_comun_GP`. En A y B, en todas y en `sin_respaldo` | Si permitir reglas por municipio ayuda **más que** una regla común |
| C2 | Revuelto | Solo `t12_het_GP` en A. Hay 20 permutaciones (semillas 20261015 + k, con k de 1 a 20). Antes de particionar, se barajan las filas completas de las columnas de GP (ambas ventanas) entre las etiquetadas **del mismo municipio**; las 59 no se tocan. Se repite todo el procedimiento con las mismas particiones e internas. p = (b + 1) / 21, donde b = número de permutaciones con un ΔMAE igual o mejor que el observado | Si la mejora se distingue del azar |
| C3 | Curva de aprendizaje | Solo en A, para la referencia, `t12_control_comun_GP` y `t12_het_GP`. En cada uno de los 25 contextos se submuestrea el entrenamiento al 50 % y al 75 % (semillas 20261015, 20261016 y 20261017). Solo se submuestrean los municipios con al menos 10 filas, y los pequeños se conservan completos para no vaciar el estrato `otros`. La validación no cambia | Si el error sigue bajando con más parcelas (faltan datos) o ya se aplanó (falta señal) |
| C4 | Desgloses | Los cortes de T03 §4 bis (municipio, grupo, contorno, angosta, escalón y vecina < 20 m), más el cuartil del error de la referencia. Sensibilidad sin las 24 parcelas con alerta, solo en la evaluación | Dónde ayuda o estorba |
| C5 | Qué aprendió | `het`: β + γ_m por municipio y variable en los 25 contextos de A, con la fracción de contextos con el mismo signo. `gb`: importancia promedio, solo descriptiva | Si la relación al revés entre municipios es estable o era ruido |
| C6 | Parcela por parcela | Las 20 que más mejoran y las 20 que más empeoran frente a la referencia | Material para revisar en QGIS y para el informe |

## 9. Resultados posibles, definidos antes de correr

| Resultado | Condición | A dónde va |
|---|---|---|
| **R1. Promoción** | `t12_het_GP` cumple la sección 7 | T16 decide; T18 lo ajusta con las 138 |
| **R2. Señal sin umbral** | `t12_het_GP` con ΔMAE < 0 en al menos 4 de 5 repeticiones, IC que incluye el cero y C1 < 0; o un secundario cumple T03 §4 | Informe: hay indicio, pero con 138 parcelas no alcanza. No cambia el modelo |
| **R3. Mejora en las colas** | ΔRMSE < 0, o mejora en el cuartil de errores grandes, sin mejorar el MAE | App: avisos por parcela. No cambia el modelo |
| **R4. Nada, curva plana** | Ningún ΔMAE < 0 estable, C2 con p alto y C3 plana | Informe: el límite son los datos; es un argumento para la referencia |
| **R5. Nada, curva que baja** | Como R4, pero C3 muestra que el error baja con más parcelas | Informe: recomendación sobre datos futuros |

## 10. Antes de ejecutar (barreras)

1. Este documento y `procedimiento_t12.json` están en un commit anterior a cualquier salida con etiquetas.
2. Las pruebas sintéticas del paso 2 pasan en Docker.
3. Las comprobaciones del paso 3 están guardadas en `registro/t12/comprobaciones.json`.
4. Dani confirma que `scripts/evaluacion_comun_*` no cambiará en la revisión del PR #21, o el PR ya se integró.
5. Dani y Jass aceptan D026.
6. Migue revisó este diseño.

## 11. Qué no afirma ni hace

- No cambia la referencia, T03 §4, T15 ni los resultados anteriores.
- No usa clima, Sentinel-2, nubosidad ni vecinas.
- No genera la entrega final de las 59. Las predicciones de las 59 de T12 son exploratorias; la entrega es T18.
- No elimina parcelas ni corrige etiquetas.
- No interpreta pendientes como causas. Una pendiente distinta por municipio puede reflejar manejo, variedad o forma de medir, que no tenemos.
- Un resultado positivo es un **indicio** con 138 parcelas de una sola campaña. No hay datos de prueba independientes: las 59 no tienen etiqueta.
