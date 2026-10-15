# T15 · contrato propuesto de E1: observación, calidad y faltantes

14 de octubre de 2026. Responsable: Dani. Revisión propuesta: Daf y Migue. Estado: **propuesta versionada, no ejecutable**. Amplía la especificación de E1 sin cambiar el código ni el contrato congelado del [PR #21](https://github.com/danielalira20/AgroCebada-2026/pull/21), commit `4afabf081a341f3321fcd58a211d18b43ee5a3b4`.

## Problema que resuelve

D.1 verificó 169 contrastes calculables: 119 etiquetadas y 50 reservadas. Hay 28 ausencias y 18 cálculos con intervalo nominal truncado por el corte. El borrador B y el método v3 sólo describían el rasgo propuesto y el faltante previo D020; no definían qué hacer con esos casos, qué podía aprender el modelo ni cómo distinguir información de agua de información de calidad de observación.

## Solución propuesta

Separar tres capas y mantener 197 IDs:

1. **Evidencia observada:** D.1 permanece intacta, con sus 169 valores, vacíos, fechas y calidad.
2. **Admisibilidad de E1:** una tabla aparte indica cuándo ese valor entra como observación comparable y cuándo queda ausente para el experimento principal.
3. **Tratamiento del modelo:** mediana y escalado se aprenderían sólo dentro de cada entrenamiento, con un indicador fijo. Esta capa no se implementa ni ajusta en esta entrega.

[Contrato estructurado](../registro/t15_e1/contrato_propuesto_v1.json). Se redacta después de D.1 y de los diagnósticos previos, antes de evaluar esta extensión. No se presenta como diseño ciego ni como aprobación de los revisores.

## 1. Observación y significado físico

Se conserva exactamente la fórmula D.1: NDWI original en la primera fecha del máximo de NDVI suavizado; media de observaciones válidas entre +15 y +45 días, inclusivos, menos ese NDWI de ancla. Se mantienen Sentinel-2, nube ≤5 %, al menos cinco capturas para la curva y dos fechas posteriores distintas. No se interpolan observaciones ni se amplía el corte de 31-oct-2025.

Las dos ventanas tienen el mismo E1 en D.1. Eso no produce dos señales independientes: se propone una sola columna del contraste y un único indicador. Se conservan las dos opciones de ventana para las cinco columnas base S, que sí pueden diferir.

El índice no es agua radicular medida. Captura observada no demuestra publicación histórica; la entrega sigue siendo retrospectiva mientras no se documente esa disponibilidad.

## 2. Intervalos completos y parciales

Para el primer experimento se propone admitir como valor E1 observado sólo un contraste calculable cuyo máximo+45 días no supere el corte. La política es fija, no un parámetro elegido por menor MAE. «Completo» significa que el intervalo nominal está dentro del corte, no que se observe cada día ni toda el área sin nubes.

| Estado propuesto | Etiquetadas | Reservadas | Total | Valor original D.1 | Columna E1 principal |
|---|---:|---:|---:|---|---|
| Calculable, intervalo nominal completo |106|45|151|Se conserva|Se conserva observado|
| Calculable, intervalo truncado |13|5|18|Se conserva con calidad|Ausente para el primer experimento|
| No calculable por soporte insuficiente |19|9|28|Ausente con motivo|Ausente|

Por tanto, la entrada candidata tiene **32 ausencias entre las 138 y 14 entre las 59**, aunque la observación D.1 tenga sólo 19 y 9. Es una decisión conservadora propuesta sobre el uso del dato; no una corrección de D.1 ni la afirmación de que esos 18 cálculos sean erróneos.

No se borran esas 46 parcelas del entrenamiento ni de las métricas. La representación S de base sigue disponible para todas. No se convierte un contraste parcial en uno completo mediante reescalado por días, ni se busca otro intervalo después de ver errores. Usar los parciales sería una futura política distinta que necesitaría registro propio; no se añade ahora como otra variante para competir.

## 3. Columnas, vacío y calidad

La tabla propuesta conserva `valor_observado_D1` como auditoría. `e1_ndwi_post15_45` contiene el valor sólo en el estado admisible; el vacío sigue siendo vacío. Un cero observado es válido.

`e1_no_utilizable` es 1 cuando falta un E1 admisible y 0 cuando existe. Siempre tiene su columna, aunque un entrenamiento concreto no tenga ausencias. La fecha de máximo, número de capturas, truncamiento, motivo y demás metadatos son calidad/auditoría; no se incorporan automáticamente como predictores.

Un ID/ventana duplicado, una fecha fuera del corte, un estado contradictorio, un valor no finito, una fuente distinta o una tabla incompleta detienen la validación. No se encubren errores de contrato como si fueran una ausencia de observación.

## 4. Tratamiento dentro de cada entrenamiento

Si se acepta e implementa el experimento, cada entrenamiento interno y externo sigue este orden:

1. Aplicar la regla fija de admisibilidad, sin mirar etiquetas ni errores.
2. Construir el indicador con nombre y posición fijos.
3. Calcular la mediana E1 **sólo entre los valores admisibles de ese entrenamiento**. Usarla en la copia numérica del modelo, nunca escribirla en D.1/T07 ni llamarla una medición.
4. Aprender la escala global en ese entrenamiento. Después aplicar el centrado LOO del mismo conjunto de otros IDs y el mismo respaldo que usa la referencia residual v3, también al indicador.
5. Predecir reutilizando mediana, escala y centros guardados; las 59 o el lote de validación no reajustan esos valores. Dentro de cada división interna se repite el proceso desde su propio entrenamiento.

Se usa una mediana global de entrenamiento para evitar inventar una política municipal con grupos de una etiqueta o sin observaciones E1. El coeficiente Ridge conserva α=n·λ contando **todas** las filas de entrenamiento, no sólo las admisibles.

Si un entrenamiento no tiene ningún E1 admisible, no existe una mediana que estimar. La especificación conserva la forma de la matriz con columna técnica neutra e indicador constante, desactiva el aporte de E1 y exige comprobar equivalencia con S para esa misma configuración. Ese cero técnico no se registra como NDWI observado. Constantes y municipios pequeños requieren controles propios.

La imputación no garantiza que la corrección atribuida por el modelo a una fila sin dato sea cero. Por eso se deben reportar esos casos y no presentar sus resultados como sustentados por una observación E1 parcelaria. Garantizar una corrección E1 exactamente apagada por fila requeriría otro estimador con respaldo condicionado; no se promete que la mediana haga eso.

La documentación oficial recomienda aprender las transformaciones únicamente en entrenamiento. También permite conservar columnas totalmente vacías y construir indicadores para todas las columnas, evitando que cambie su forma cuando aparece un faltante nuevo. Estas herramientas no justifican por sí solas la política científica elegida. [Prevención de filtraciones](https://scikit-learn.org/stable/common_pitfalls.html), [imputación y forma de la matriz](https://scikit-learn.org/stable/modules/impute.html), [indicadores fijos](https://scikit-learn.org/stable/modules/generated/sklearn.impute.MissingIndicator.html).

## 5. Control de calidad separado del valor

Una ausencia puede señalar calendario o condiciones de observación y, por tanto, ubicación. Que el procedimiento completo mejore no basta para afirmar que mejoró por el valor de NDWI. Se proponen estos tres procedimientos:

| Procedimiento | Entradas por opción | Pregunta |
|---|---:|---|
| S, base ya prevista |5 resúmenes Sentinel-2|Referencia para el aporte incremental|
| Q, control diagnóstico |S + indicador fijo: 6 columnas|¿Ayuda sólo saber que E1 no es utilizable?|
| E1 |S + indicador + E1 tratado: 7 columnas|¿Añade algo el valor del contraste además de la calidad?|

Contrastes obligatorios: E1−S, E1−Q, Q−S y E1−referencia territorial. Se reportan en la misma población, con máscaras y diferencias emparejadas por ID. Q es un control, **no un nuevo ganador elegible por observar luego una cifra favorable**. Si no hay evidencia favorable frente a Q, no se atribuye una eventual ganancia al valor NDWI; se declara su ambigüedad.

La regla de promoción T03 frente a la referencia y la preferencia por simplicidad se conservan. E1−S informa la mejora incremental; E1−Q informa atribución dentro de estos procedimientos, no causalidad. No se crean p-valores adicionales para escoger una configuración. Todas las comparaciones y sus limitaciones se declaran antes de ejecutarlas.

## 6. Presupuesto: qué cambia y qué permanece

Ventanas abril–octubre/junio–octubre, cuatro λ [0.01, 0.1, 1, 10], α=n·λ, opción referencia sola, cuatro divisiones internas y 50 contextos externos A/B. La selección/desempate siguen v3; no se optimiza la política de faltantes con errores externos.

| Alcance | Opciones con variables | Máximo Ridge internos | Máximo Ridge externos |
|---|---:|---:|---:|
| T15 principal, ocho procedimientos |60|12,000|400|
| E1 que proponía B |8|1,600|50|
| E1 + Q propuestos ahora |16|3,200|100|
| Incremento por Q |8|1,600|50|

Las referencias pueden compartirse por contexto: hasta 200 internas y 50 externas para el par Q/E1. S sólo se reutiliza si coincide exactamente en método, fuentes, divisiones y versión. Si no existe esa evaluación compatible, primero hay que generarla y contabilizarla; no se reutilizan resultados T11/T13 históricos como si fueran S-v3.

Este aumento es una **propuesta explícita pendiente de acuerdo**, separada de las 60 opciones principales. No se acepta ni ejecuta al guardar este contrato. Tampoco activa E2 ni otras fuentes.

## 7. Pruebas, informes y revisión pendientes

Esta entrega valida el contrato, clasifica los 394 perfiles sin imputar y conserva las 197 parcelas. No implementa medianas, escaladores, Ridge o predicciones. Por tanto, los controles de aprendizaje sólo con entrenamiento, aislamiento de y/entradas externas, matriz independiente, casos sin observados y puente S-v3 quedan como requisitos para la implementación posterior; no se marcan aprobados por escribirlos.

El informe futuro debe separar estados completo/truncado/no calculable, reportar n por municipio, cobertura, frecuencia de referencia sola, parámetros, medianas y número de admisibles por entrenamiento, y las métricas T03 en la población común. No presenta intervalos de comparación como intervalos de una parcela. El tratamiento y la política final se congelan antes de T18, con trazabilidad de toda exploración.

Daf revisa comparador, calidad y presupuesto; Migue revisa compatibilidad con protocolo y grupos pequeños. Los comentarios favorables sobre v2 del PR #21 no aprueban esta extensión, que tiene versión y revisión independientes. T15 principal no queda bloqueado por este candidato opcional.

## Alternativas consideradas y recomendación

- Eliminar las 46 parcelas: se rechaza; cambia población y deja reservadas sin resolver.
- Rellenar con la media de las 197, con cero observado o con datos de la validación: se rechaza; mezcla fuentes o inventa una observación.
- Usar parciales con más banderas y tiempos como predictores: posible hipótesis, pospuesta para evitar otra búsqueda y mezclar exposiciones distintas.
- Respaldo por fila a un modelo S separado: alternativa conservadora, pero cambia el estimador y el coste y requiere validar la selección completa. No se implementa como atajo.

**Recomendación:** conservar D.1 íntegra, proponer E1 con intervalo nominal completo, mediana de entrenamiento e indicador fijo, y un control Q que permita interpretar la contribución. Primero revisar contrato/presupuesto; después implementar y verificar el preprocesamiento; sólo entonces evaluar. No hay mejora de MAE nueva por esta ampliación.
