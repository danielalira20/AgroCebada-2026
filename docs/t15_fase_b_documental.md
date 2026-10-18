# T15 · B documental: comparaciones propuestas

14 de octubre de 2026. Responsable: Dani. Revisión T15: Daf; protocolo/cierre: Migue.
**Borrador local para revisión. No es un registro experimental aceptado ni habilita entrenamientos.**

## Problema que resuelve

Las propuestas de mejora mezclaban información nueva, procesamiento de observaciones y cambios de estimador. Además se recibieron exploraciones de vecindad que no deben presentarse como si aún no se hubieran observado. Hace falta una cartera limitada con comparadores, presupuestos y criterios explícitos.

## Solución que implementa

[Borrador estructurado](../registro/t15_plan/borrador_fase_b.json): conserva íntegra la propuesta principal v3 de fase A; separa tres extensiones posibles y sus dependencias. No modifica T03, D019, el registro aceptado de otra tarea ni los resultados históricos. La nueva implementación v3 necesita revisión independiente; la conformidad de Daf/Migue con la versión anterior no se traslada automáticamente.

## Principal: ocho procedimientos y una referencia

C = clima, G = relieve y área actuales, P = Planet, S = Sentinel-2. Procedimientos C, G, P, CG, CP, GP, CGP y S; referencia exacta `media_mun__resp_grupo`. Se conserva la lista de columnas de fase A, con dos ventanas —abril–octubre y junio–octubre— salvo G estático. Cuatro lambda: 0.01, 0.1, 1 y 10; Ridge con alpha = n·lambda. La referencia sola compite en la selección interna. Área logarítmica, imputación D020, escala y centrado siguen el contrato de v3, aprendidos en cada entrenamiento.

Son 60 opciones con variables, 50 contextos externos A/B, hasta 12,000 ajustes Ridge internos y 400 externos. La referencia externa compartida se calcula una vez por contexto. Esto no incluye un ajuste final con las 138 ni la entrega de las 59. La frecuencia de referencia sola tendrá denominador y completitud: apagar un bloque no prueba aporte de ese bloque.

## Extensiones: decisiones separadas

| ID | Pregunta | Comparador | Búsqueda propuesta | Condición previa |
|---|---|---|---|---|
| V20 | ¿Las vecinas etiquetadas añaden información local? | Referencia territorial | Peso 0, .25, .5, .75, 1; radio fijo <20 m | Script de Daf, trazabilidad y aislamiento de residuos |
| E1 | ¿Un contraste de agua posterior al máximo añade señal temporal? | S con sus cinco resúmenes actuales | Dos ventanas × cuatro lambda; referencia sola | Soporte y no duplicación con T13/T13e; contrato de faltantes |
| E2 | ¿El relieve local a 15 m añade detalle útil? | S con los mismos cinco resúmenes | Dos ventanas × cuatro lambda; referencia sola | Fuente exacta, QA y contrato de las columnas nuevas |

**No se combinan ganadores externos de estas extensiones.** No se añaden sus opciones a las 60 principales sin un registro separado aceptado. E1/E2 permiten hasta 3,200 ajustes Ridge internos y 100 externos en conjunto; V20 es un procedimiento espacial distinto, no Ridge y no necesita duplicarse por ventana.

### V20

Predicción = referencia + w·media de los residuos LOO de todas las vecinas admisibles. Deben ser del mismo municipio, estar en el entrenamiento y tener distancia entre orillas en EPSG:32614 estrictamente menor que 20 m. Sin vecina se devuelve exactamente la referencia. No se utiliza como predictor la bandera estática de T07.

La referencia y los residuos de las vecinas se reconstruyen en cada entrenamiento interno y externo. Filtrar vecinas después de calcular residuos con las 138 no sería suficiente. Las distancias puramente geométricas pueden cachearse una vez, y después enmascarar los IDs disponibles. El peso se selecciona por MAE en las validaciones elegibles de A/B; empate a cero y después al menor peso. Máximo: 1,000 puntuaciones internas sobre 200 conjuntos de entrenamiento, más 50 contextos externos.

Sensibilidades <5 y <100 m: se conserva el peso elegido con 20 m, sin volver a optimizarlo, sin competir por promoción; son 100 contextos externos adicionales. Si el principal cumple la regla, un control diagnóstico con 20 reasignaciones de vecinas dentro de municipio/entrenamiento, semilla 20261014, conserva disponibilidad y número de vecinos; no usa etiquetas de validación para construir los residuos. Añade hasta 1,000 contextos de control, no configuraciones elegibles. Un resultado comparable bajo reasignación exige aclararlo antes de promover; el control no prueba causalidad.

Daf ya reportó pesos .5/1, radios descriptivos 1/5/20/100/500 m y resultados externos. Se conserva esa exposición. Su ΔMAE +.0021, ΔRMSE −.0174 e intervalo de RMSE que cruza cero no se convierten en mejora aceptada. Falta aclarar el conteo «70 pares» y recibir el código; T02/T07 distinguen pares únicos de parcelas involucradas.

### E1

Un solo atributo propuesto: NDWI medio observado de 15–45 días después del máximo de la curva NDVI de T06 menos NDWI observado en ese máximo. Primera fecha en máximos empatados; al menos dos fechas posteriores válidas y distintas y NDWI válido en el máximo. Corte 31-oct antes de suavizar/resumir; no extrapolar ni llamar a ese intervalo una etapa agronómica confirmada.

Los rasgos existentes de heterogeneidad y valor al corte no se presentan como nuevos. La factibilidad se comprueba sin etiquetas. Si faltan valores, se conserva el vacío y su razón: cualquier imputación/indicador del modelo necesita una versión de contrato aprendida sólo en entrenamiento. El contrato v3 actual sólo admite D020; no basta con añadir una columna vacía.

### E2

Propuesta compacta: posición topográfica relativa con radio métrico fijo de 150 m y medias de seno/coseno de orientación ponderadas por área. Conservar planos sin orientación y cobertura. Requiere fijar activo INEGI, edición, datum, licencia y evidencia de publicación histórica. No se ha seleccionado ni descargado ese activo por redactar este borrador.

TWI queda fuera de la primera cartera: requiere contexto de drenaje, manejo de planos/depresiones y QA hidrológica. Una superficie pequeña respecto a una celda no prueba por sí sola inutilidad. La extracción se aplicaría a las 197 con una misma regla, sin escoger parcelas según rendimiento.

## Regla y honestidad del resultado

Se decide en A/sin_respaldo según T03: ΔMAE ≤ −.01 t/ha, límite superior IC95_celdas <0, mejora en al menos cuatro de cinco repeticiones, ΔRMSE ≤+.01 t/ha. Escenario B obligatorio; 5,000 réplicas por celdas, semilla 20261006. Se reportan también RMSE, R² interpretable y sesgo. No cambiar la métrica por una mejora observada ni tratar repeticiones/pares como muestras independientes.

Una ganancia en E1/E2 incluye su representación y cualquier procesamiento/faltantes que cambien: no demuestra que sólo cambió información física. Las comparaciones son posteriores al diagnóstico de errores; un nuevo registro o selección interna no borran las exploraciones previas ni equivalen a validación en otra campaña. Sin mejora elegible prevalece el procedimiento más simple según T03.

## Pospuestas y condiciones de reapertura

- Óptica cruda: sólo ante un defecto observacional concreto que justifique el coste.
- SoilGrids: soporte, variación local, incertidumbre y publicación histórica pendientes; no se declara inútil.
- Cuantílica: hipótesis distinta de la comparación territorial D019; pospuesta por presupuesto, no «ya probada».
- Radar/meteorología diaria: carencia concreta y factibilidad antes de abrir otro frente.

## Revisión pendiente y siguiente acción

Daf revisa comparación/presupuesto y entrega el script de vecinas; Migue confirma la extensión prospectiva de internas B por celda en T03 y la política para grupos pequeños. La implementación v3 todavía local debe publicarse con autorización de Dani para revisar su código. Este documento y el JSON son propuestas revisables; no son un permiso técnico para ejecutar T15.

Mientras llegan esas revisiones se puede completar [C descriptiva](diagnostico_aplicabilidad59.md), preparar QA de fuentes y revisar trazabilidad. No se generan predicciones finales, no se cambian las 59 y no se solicitan respuestas nuevas de FIRA como dependencia.
