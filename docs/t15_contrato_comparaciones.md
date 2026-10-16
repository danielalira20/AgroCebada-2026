# T15: contrato de comparaciones y comprobaciones previas

Fecha: 15 de octubre de 2026. Responsable: Dani; corresponsable: Daf; revisión metodológica: Migue. Registro estructurado: [contrato v1](../registro/t15_contrato/contrato_v1.json). Cierre técnico local para revisión; no equivale a aceptación humana ni habilita la evaluación completa.

## Problema que resuelve

La evaluación necesita una lista fija de comparaciones, reglas y datos, además de una traza por ajuste. El selector v3 anterior conserva puntuaciones agregadas, pero no deja en su salida los IDs, respaldos y casos de una sola etiqueta de cada ajuste interno. Las extensiones propuestas tampoco deben ampliar silenciosamente las ocho comparaciones que revisó el equipo.

## Solución que implementa

Se añade un contrato separado, con fuentes identificadas por SHA256, una comprobación de las 200 divisiones internas reales sin modelos y un selector instrumentado que conserva la matemática de v3. La propuesta histórica, los estimadores, T03/T07 y sus resultados se conservan como antecedentes identificados. Este lote no contiene un corredor de evaluación completa ni predicciones finales.

## 1. Menú principal cerrado

| Procedimiento | Bloques |
|---|---|
| C | Precipitación acumulada, Tmin, Tmax |
| G | Elevación, pendiente con regla D020, log del área original |
| P | Seis resúmenes compactos de Planet |
| CG, CP, GP, CGP | Las combinaciones aditivas de esos bloques |
| S | Cinco resúmenes compactos de Sentinel-2 |

Las columnas y los 18 pares de contraste se copian exactamente de `propuesta_t15_centrado_loo_v3.json`, cuya huella también queda fijada. Ocho contrastes frente a referencia son elegibles para la regla principal; los condicionales y S−P son descriptivos. No se elige un sensor después de comparar sus OOF. La referencia es `media_mun__resp_grupo`, con respaldo por grupo y global según entrenamiento. La mediana no sustituye la referencia de este lote.

- Dos ventanas: abril–octubre y junio–octubre de 2025; G es estático.
- Cuatro λ: 0.01, 0.1, 1 y 10; α = número de filas del entrenamiento × λ.
- Referencia sola compite dentro de cada procedimiento.
- Internas: cuatro; A estratifica municipio/otros, semilla 0; B agrupa celdas CHIRPS sin shuffle.
- Desempate: MAE redondeado a seis decimales, referencia sola, λ mayor, junio–octubre, nombre estable.
- C no entra en esta evaluación A/B; si se informa después, sus internas agrupan municipios y es diagnóstico territorial.

Población: 197 parcelas de campaña 2025, 138 etiquetas y 59 objetivos ausentes. Corte de observaciones 31 de octubre de 2025, sin acreditar por sí solo disponibilidad histórica de publicación. Ninguna parcela desaparece por tener error grande o por D020. No se usan las 59 para ajuste, selección ni evaluación. Los distintos mapas, fechas y repeticiones no crean nuevas etiquetas independientes.

## 2. Estimador y controles de ajuste

Se usa `comun-centrado-loo-v3`, diseño SHA256 `95ee8be41a60f05f797b8466c741713efcb261efb4bcdbf28af66f7895dcf7a2`:

1. Aprender log de área, imputación de pendiente e indicador y escala global con el entrenamiento del ajuste.
2. Formar residuo y centro con el mismo conjunto sin la propia fila, con respaldo municipal/grupo/global.
3. Ajustar Ridge sin intercepto; al predecir, usar los centros completos guardados del entrenamiento.
4. Mantener fijo el estado al cambiar orden o composición del lote de predicción.

Si no hay pendiente observada en un entrenamiento, se detiene la opción y se registra el fallo. No imputar cero ni eliminar una opción para continuar la búsqueda. El preflight comprueba esta condición en las 200 divisiones reales; los casos artificiales prueban el rechazo. Los ejemplos pequeños modificados de las pruebas verifican software: no se generan datos agrícolas para entrenar una entrega.

Una advertencia o error también queda en la traza y detiene la selección; no se convierte en una derrota estadística del candidato. Una corrección pequeña debe acompañarse de su magnitud y frecuencia de referencia sola para interpretar el aporte del bloque.

## 3. Qué se registra en cada ajuste

`t15_comparaciones_traza.py` añade:

- IDs exactos de entrenamiento, validación y elegibles; opción, ventana, versión, λ y α.
- Número de municipios y celdas, municipios singleton en entrenamiento y predicciones cuya referencia tiene una etiqueta.
- Fuente municipal/grupo/global de referencia y de centros LOO; faltantes/imputación de pendiente.
- Huella del estado aprendido, magnitud media/máxima de corrección y advertencias/errores.
- En selección: escenario, división interna, MAE elegible y MAE de todas las filas, con denominadores.

La función que ajusta y predice **no recibe y de validación**. Las etiquetas de validación sólo se usan después para puntuar. Las etiquetas externas tampoco se entregan al selector interno. La traza no acredita por sí sola ausencia universal de filtración: las pruebas de aislamiento y la revisión del código proporcionan la comprobación correspondiente.

Un futuro corredor completo debe añadir candidato, repetición y partición externa a las trazas, guardar también el ajuste externo seleccionado y sus IDs, y validar OOF completas antes de reportar métricas. Los fallos deben persistirse aunque la evaluación quede incompleta. Esta rama prepara esas piezas, sin ejecutarlas como una entrega T15.

## 4. Criterios y presupuesto

Se mantienen exactamente T03/v3:

- Decisión en A/sin_respaldo, con ΔMAE medio por parcela ≤ −0.01 t/ha.
- Límite superior del IC95 por celdas < 0; 5,000 remuestras, semilla 20261006.
- Al menos cuatro de cinco repeticiones con ΔMAE < 0.
- ΔRMSE medio por repetición ≤ +0.01 t/ha; B obligatorio como sensibilidad.

La regla permite cierto aumento de RMSE. Se informa si hay mejora conjunta o intercambio entre métricas, sin introducir un veto nuevo después de observar resultados. R² se reporta y no decide; si el objetivo es constante, se marca indefinido. Se añaden sesgo, p90 del error absoluto y número de errores >1 t/ha como diagnósticos, con población y unidad explícitas. No se confunden MAE por parcela, por registro o por repetición, especialmente en B. No se promedian predicciones de repeticiones antes de calcular el error del procedimiento.

Presupuesto principal: 60 opciones con variables × 200 divisiones = hasta 12,000 ajustes Ridge internos, y hasta 400 externos. Referencia sola aporta 1,600 valoraciones internas si se repite por candidato; sus 200 ajustes internos y 50 externos se pueden compartir con identidad exacta de fuentes/divisiones. Cuando gana referencia sola, no se ajusta un Ridge externo: por eso son cotas máximas. No se amplían semillas, rejillas ni bloques según resultados.

## 5. Extensiones separadas

| Extensión | Diseño y estado | Cota adicional propuesta |
|---|---|---|
| SG | S compacto + G exactos; ocho opciones. Requiere conformidad explícita | 1,600 internos, 50 externos |
| Q/E1 | Indicador de ausencia y contraste NDWI postmáximo. Contrato conservador previo: 151 observados y 46 ausentes; 45/14 entre reservadas. Preprocesamiento aún pendiente | 3,200 internos, 100 externos |
| Cuantil 0.5 con S | Reserva; falta cerrar identificabilidad, penalización, respaldo y pruebas matemáticas. No se fija una rejilla α arbitraria | Hasta 1,600 internos, 50 externos |
| Datos externos, interacción, ensamble, T12 | Cartera que necesita registro propio; no se ejecuta por figurar aquí | Fuera de esta cota |

Las tres primeras sumarían hasta 20,000 ajustes internos/600 externos junto con el principal; **no es un único experimento ya aceptado**. E1/Q requiere integrar su sidecar por ID sin cambiar T07, implementar el aprendizaje dentro de cada entrenamiento y probar el puente con S. Antes de evaluar se revisará la estabilidad de su ancla retirando una captura cercana, recalculando mediana móvil y máximo sólo con observaciones anteriores al corte y sin usar y. Esa QA no inventa una fecha de cosecha ni optimiza umbrales contra MAE.

Migue comunicó una comprobación de Tmax en B el 15 de octubre y recomendó congelar las ocho comparaciones. Se conserva ese menú. SG y otras extensiones son propuestas posteriores a esa exposición; su B requiere revisión explícita y se informa como tal, sin presentarlo como diseño ciego. Nada en este documento garantiza una mejora ni acredita otra campaña.

## 6. Revisiones reales y puertas restantes

- [Daf, PR21](https://github.com/danielalira20/AgroCebada-2026/pull/21): conformidad con bloques, presupuesto y antecedente v2, con observaciones de centro LOO y frecuencia de referencia sola.
- [Migue, comentario del 15 de octubre](https://github.com/danielalira20/AgroCebada-2026/pull/21#issuecomment-6195698971): acepta la alineación LOO; pide el complemento de tasas sobre las 138 y congelar B. El complemento está en la base local c9015e4 y todavía necesita publicación autorizada y revisión del lote.
- [PR22](https://github.com/danielalira20/AgroCebada-2026/pull/22) en f73f376d: siguen pendientes las precisiones de interna C y desempate; no se observó nueva revisión al consultar.

Las pruebas y fuentes se identifican en el informe de verificación de esta rama. **Cerrar el contrato técnico no equivale a aprobarlo en nombre de Daf o Migue.** El comando de comprobación devuelve `evaluacion_habilitada=false`; `--exigir-ejecucion` rechaza. La aceptación y el registro anterior a la corrida necesitan un registro nuevo con sus evidencias y commit exacto, no un booleano escrito manualmente. El programa no autentica opiniones humanas.

Mientras se revisa, se pueden completar QA del ancla E1 y pruebas del futuro preprocesamiento en su rama propia. El principal no depende de E1/cuantil/datos externos. La autorización de este trabajo no autoriza un push.

## 7. Reproducción

Desde la raíz del repo, con dependencias fijadas:

```bash
python -m scripts.t15_comparaciones_contrato --salida reports/t15_contrato/preflight.json
python -m unittest tests.test_t15_comparaciones tests.test_evaluacion_comun_centrado_loo
```

La primera orden no ajusta modelos. La segunda ajusta modelos de comprobación limitados y no publica OOF ni genera las 59 finales. No sobrescribir evidencia anterior; usar destino nuevo. Docker común debe ejecutar las mismas comprobaciones con el repositorio de sólo lectura y detenerse al terminar. Una imagen distinta no constituye otra validación estadística.

Apoyo metodológico: skills scikit-learn y scientific-critical-thinking. Kassis, T.; Agarwal, V.; He, Y.; Patel, D.; Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. [Registro vigente](https://arxiv.org/abs/2609.00065). Esta referencia corresponde al procedimiento de trabajo, no a una mejora de rendimiento.
