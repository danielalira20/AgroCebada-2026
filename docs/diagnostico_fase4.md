# Diagnóstico de errores · fase 4: etiquetas y factores locales

**Estado: entrega técnica local preparada para revisión independiente, 14 de octubre de 2026.**

La conciliación no detectó una etiqueta alterada, una unión por ID incorrecta ni una conversión de unidades entre los originales, T02, T07 y las predicciones históricas examinadas. Sí identifica límites concretos: conocemos el rendimiento de grano, pero no la fuente de medición, superficie efectiva, humedad, variedad ni manejo **por ID**. Las cuatro fallas compartidas siguen sin una causa confirmada. Ninguna etiqueta se corrigió y no se evaluó un modelo nuevo.

El diagnóstico cubre 4.1–4.3 de la pestaña «Diagnóstico de errores y aplicabilidad», fijada en fase 0, con las mismas diez parcelas y diez controles. Los errores se leen de los resultados históricos y conservan sus versiones. Las respuestas oficiales, la transcripción oral y las fuentes externas se distinguen: ninguna sustituye una medición individual ausente.

## 4.1 · Integridad, escritura y denominador de las etiquetas

### Conciliación completa

Se leyó directamente el CSV y el DBF dentro de **DataSet.zip original**, sin utilizar la copia QGIS como fuente de cálculo. Se cruzaron las 197 identidades con el catálogo T02 y T07. Las 138 etiquetas presentes y las 59 ausentes permanecen exactamente como en origen. Áreas CSV/T02/T07 y rendimientos se contrastaron literalmente; las diferencias numéricas DBF/CSV se controlaron con el margen preestablecido de 1e-9 ha. Conjunto, municipio, estado y escritura del cultivo se comprobaron también contra el DBF.

Se revisaron las etiquetas incluidas en **71,208 registros OOF históricos**: todas coinciden con las originales. Son evaluaciones repetidas de las mismas 138 parcelas, no 71,208 muestras independientes. Este control acredita integridad del recorrido de datos; no verifica una báscula, la superficie cosechada ni la exactitud del reporte comercial.

FIRA confirma rendimiento de **grano en t/ha**, procedente mayoritariamente de comercializadoras y, en menor proporción, del productor. No identifica cuál fuente corresponde a cada ID ni detalla el denominador o ajuste de humedad. Sigue abierto **P06** de T07. Los cuatro decimales exigidos para entregar predicciones son un formato de entrega; no prueban cuatro decimales de exactitud física. Fuente: Segunda sesión de preguntas y respuestas, 9 de octubre, preguntas 5–7; localizadores y huellas en [fuentes de contexto](../registro/diagnostico/fase4_fuentes_contexto.csv).

### Granularidad observada y resolución de medición

| Municipio | Etiquetas | Valores distintos | Mayor paso compatible T02, t/ha | Interpretación |
|---|---:|---:|---:|---|
|Calpulalpan|30|3|0.5|Valores escritos 2.5, 3 y 3.5; precisión física desconocida|
|Emiliano Zapata|3|1|0.5|Todas 3.5; también compatibles con 0.1 y 0.01. Resolución no identificable|
|Singuilucan|16|7|0.1|Malla escrita, sin confirmación del método de medición|
|Chignahuapan|71|54|0.01|Malla escrita, sin confirmación de precisión de pesaje|
|Almoloya|10|9|0.01|Mismo límite|
|Cuautepec de Hinojosa|5|5|0.01|Mismo límite|
|Apan|1|1|No asignado|Muestra insuficiente|
|Nanacamilpa de Mariano Arista|1|1|No asignado|Muestra insuficiente|
|Tepeapulco|1|1|No asignado|Muestra insuficiente|

La regla T02 se reproduce: 33 etiquetas compatibles con paso 0.5, 16 con 0.1, 86 con 0.01 y 3 sin paso asignado. **Compatibilidad significa que los números encajan en esa malla; no demuestra cómo se midieron.** El matiz de Emiliano Zapata no invalida el cálculo de T02: agrega una advertencia interpretativa importante a una muestra constante. Valores repetidos tampoco prueban copias.

Se reconstruyeron 50 entrenamientos externos A/B y 450 grupos municipales, excluyendo íntegramente las etiquetas de su evaluación. En B, Singuilucan llega a tener sólo tres etiquetas de entrenamiento, con dos valores diferentes compatibles con 0.5, aunque el municipio completo tiene paso 0.1. En otra repetición sólo tiene dos etiquetas y no se asigna paso. **Una muestra parcial puede parecer más gruesa sin que cambie el instrumento de medición.** Por eso no se proponen pesos de confianza, deduplicaciones ni exclusiones basados en esa malla.

El desglose retrospectivo T08 A/sin_respaldo, con igual peso por ID, da MAE 0.3385 para paso 0.01 (86 IDs), 0.3467 para 0.1 (16) y 0.2609 para 0.5 (33). No aparece un aumento general del error al escribir en pasos más gruesos. Municipio, tamaño de muestra y repetición de valores confunden esta comparación; no demuestra que escribir fino o grueso cause el error. Se entregan también B y los desgloses de entrenamiento. Los IDs pueden cambiar de grupo entre repeticiones; no sumar sus conteos como grupos disjuntos.

### Siete etiquetas extremas y diez errores grandes son preguntas distintas

T02 compara cada rendimiento con la media de **todas las otras etiquetas** de su municipio y marca diferencias estrictamente mayores que 1 t/ha. Reproducimos siete: bajas AGC_015, AGC_024, AGC_034 y AGC_171; altas AGC_049, AGC_127 y AGC_162. La fase 0 seleccionó diez por error OOF T08, cuya referencia sólo utiliza el entrenamiento de cada partición. Se conservan ambas definiciones.

AGC_069 está a +0.996714 t/ha de la media de las otras etiquetas, a 0.003286 del umbral histórico. No es extrema según T02, aunque su MAE OOF es 1.0164. AGC_055 y AGC_026 tampoco cumplen ese umbral. Esto no es una contradicción ni un motivo para moverlo o retirar casos.

### Sensibilidad nominal al redondeo de área

Se calculó una magnitud condicional para **las 138 etiquetas**, con dos variaciones por parcela (276 filas). Sólo si el área realmente fue redondeada a centésimas de hectárea y la masa de grano permanece constante, variar el denominador en ±0.005 ha produce una magnitud de cambio `abs(y × delta_area / (area + delta_area))`. No se afirma que ése sea el error real de área, ni que el área dibujada equivalga a lo cosechado. No se generó una etiqueta ajustada.

| Caso fijo | Rendimiento original, t/ha | Área declarada, ha | Extrema histórica T02 | MAE OOF A, t/ha | Mayor magnitud nominal ±0.005 ha, t/ha |
|---|---:|---:|---|---:|---:|
|AGC_171|2.15|11.63|baja|2.3665|0.000925|
|AGC_015|2.64|1.97|baja|1.8516|0.006718|
|AGC_024|3.03|11.53|baja|1.4593|0.001315|
|AGC_034|2|8.09|baja|1.1774|0.001237|
|AGC_162|5.59|4.93|alta|1.1080|0.005675|
|AGC_127|5.57|0.91|alta|1.0885|0.030773|
|AGC_049|5.53|0.87|alta|1.0555|0.031965|
|AGC_069|5.46|0.38|no|1.0164|0.072800|
|AGC_055|5.45|1.37|no|0.9794|0.019963|
|AGC_026|3.55|5.49|no|0.9422|0.003236|

El máximo nominal del conjunto es 0.0728 t/ha en AGC_069. En los cuatro fallos compartidos es aproximadamente 0.000925, 0.006718, 0.001315 y 0.001237 t/ha respectivamente, muy por debajo de sus errores OOF. **El pequeño redondeo, bajo ese supuesto, no explica por sí solo los errores grandes.** Una diferencia entre superficie total, sembrada y cosechada podría ser mayor; carecemos del denominador real para comprobarla. No se descuenta la sensibilidad nominal del MAE ni se declara un límite irreducible de error.

## 4.2 · Factores locales observados y no registrados

La reunión aporta contexto útil: cultivo de temporal, referencia general de siembra en los primeros días de mayo y predominio de Josefa, con Voyager en menor proporción. No proporciona esas fechas o variedades por parcela. Tampoco registra por ID dosis de semilla, rotación 2022–2024 o siniestros de 2025. «No disponible» no significa que no hubo daño, ni que todas las parcelas se manejaron igual. La distinción se conserva en [14 factores no observados](../registro/diagnostico/fase4_factores_no_observados.csv).

**Las primeras preguntas deben ir a AGC_171/024 y sus controles.** Son vecinas por orillas, a 0.92 m, con rendimientos bajos, pero otros vecinos cercanos de AGC_171 tienen errores pequeños. No hay una causa uniforme por ubicación. AGC_171/197, AGC_015/124 y AGC_024/100 tienen las seis entradas climáticas iguales y NDVI visualmente parecido en las fechas comunes, mientras sus rendimientos difieren en −2.37, −2.41 y −1.47 t/ha. Los datos de fase 3 permanecen fijados por huella. Las curvas no son idénticas, el verdor no mide directamente grano y no tenemos observaciones completas del final de ciclo. Estos pares orientan preguntas sobre fechas, manejo, eventos y medición; no prueban una etiqueta falsa ni imposibilidad de mejora con todas las entradas.

**Para AGC_127/049/055/069 conviene confirmar superficie efectiva y regla de extracción.** El atlas previo muestra riesgo de mezcla de contornos o vegetación y AGC_069 tiene sólo 0.38 ha. Sus imágenes no documentan fecha de adquisición: no confirman qué hubo dentro de cada polígono durante 2025. No se modifica la categoría A/B/C de Jass, ni el área, ni los atributos satelitales. Si llega una corrección técnica respaldada, debe aplicarse con regla común y revalidarse en todo su alcance, no sólo en las diez parcelas con peor error.

Se conservan los 87 pares de vecindad T02; 45 tienen ambas etiquetas conocidas y 9 comparten valor, involucrando 15 IDs. No conocemos claves de productor o lote comercial que permitan confirmar una medición compartida. La respuesta oficial establece asociación de cada registro con su parcela; la transcripción oral niega una medición agrupada, pero no añade una ficha por ID. Ninguna de las dos acredita independencia espacial. Se mantienen los escenarios T03, sin deduplicar por igualdad de rendimiento ni inferir productor de la escritura Cebada/CEBADA.

### Fuentes externas: utilidad real y límites

- **Suelo:** SoilGrids ofrece propiedades predichas a 250 m y cuantiles de incertidumbre. Una celda nominal equivale a 6.25 ha; 118 de las 197 parcelas, incluidas 82 de las 138 conocidas, son menores según su área declarada. Ser pequeña no implica tocar una sola celda. No se extrajo suelo ni se adjudicó una medición a cada parcela. Podría justificar una hipótesis posterior, con soporte espacial, versión, temporalidad y control territorial explícitos. [ISRIC](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html).
- **Agrocostos:** son paquetes paramétricos por región y tecnología; ayudan a formular escenarios de manejo y costos, pero no confirman fertilización o costos reales de estas parcelas. No se convierten en atributos individuales observados. [FIRA Agrocostos](https://www.fira.gob.mx/Nd/Agrocostos.jsp).
- **NAX:** el documento institucional de FIRA menciona NAX y Cropwise en su plataforma; su ejemplo de rendimiento usa caña con datos de variedad, fechas y cosecha del proveedor. No confirma que NAX haya producido estas etiquetas de cebada ni un permiso para obtener datos adicionales. Sirve para pedir metodología al proveedor del reto. [FIRA, postulación ALIDE 2025, páginas 17 y 26](https://www.fira.gob.mx/Files/PremioALIDE2025.pdf).
- **Guías agronómicas:** la referencia INIFAP «Maravilla» estudia una variedad forrajera y distingue rendimiento de grano de biomasa. No es Josefa/Voyager ni una calibración de las etiquetas 2025. Se evita trasladar cifras de forraje al objetivo de grano o recortar rendimientos por rangos de otra variedad. [Artículo primario INIFAP](https://cienciasagricolas.inifap.gob.mx/index.php/agricolas/article/download/317/547/1917).

## 4.3 · Hallazgos, acciones y evidencia

El [registro de 14 hallazgos](../registro/diagnostico/fase4_hallazgos.csv) distingue patrón descriptivo, limitación de observación, hipótesis pendiente, causa no identificada con las entradas disponibles y error técnico confirmado. Cada fila tiene fuente, comprobación, alcance, certeza, responsable propuesto y acción. Los responsables indican quién puede aportar o revisar evidencia; no se envió un encargo a nadie.

El error técnico confirmado sigue siendo **la discrepancia T06 de AGC_114, 98 días en Mac frente a 99 en Linux**. Es evidencia heredada de fase 3, no un nuevo defecto de etiqueta. Daf debe revisar interpolación en días relativos y política explícita de igualdad, contrastando los 8,668 valores. Si la entrada compartida queda igual, ese cambio de reproducibilidad no requiere repetir modelos; si cambia, hay que versionar y verificar el alcance. No se modificó el código de su tarea.

Las [seis preguntas para FIRA](../registro/diagnostico/fase4_preguntas_FIRA.csv) quedan **preparadas, no enviadas**. Prioridad 1: procedencia y cálculo de rendimiento, factores/eventos de AGC_171/024 y denominador efectivo de las parcelas pequeñas. Prioridad 2: resolución y agrupación de registros, datos agronómicos por ID y extracción satelital. Si el dato no existe, se pide registrar desconocido; no se presupone que los organizadores puedan recuperarlo.

### Problemas encontrados y resueltos durante esta fase

El lector inicial esperaba la columna `con_1_decimales`, pero T02 publica `con_1_decimal`. Se corrigió el adaptador y se comprobó el esquema real, sin tocar la tabla de Jass. Las parcelas de municipios con una sola etiqueta no tienen media de otras parcelas; se hizo explícito `no_identificable`, conservando el vacío histórico. Ambos controles abortaron antes de una entrega válida. La conciliación final no encontró daño técnico en etiquetas, áreas o uniones existentes.

La mejora de método fue comprobar granularidad con **entrenamiento propio por partición**, además del catálogo completo retrospectivo, y cuantificar el escenario nominal de área con un auditor aritmético independiente. Se reduce así el riesgo de convertir decimales, constancia o redondeo en una supuesta certeza de campo. No es una mejora predictiva medida.

### Verificación y reproducción

Se añadieron 27 pruebas, aprobadas sin omisiones en Mac y en Docker común Linux/amd64 con `-O`. Cubren esquemas, identidades, vacíos, denominadores, mallas, muestras constantes, conservación de etiquetas y perturbación de evaluación sin efecto en su entrenamiento. Un auditor separado, sin importar el productor ni ejecutar modelos, recalculó etiquetas y fórmulas con aritmética racional: **72,563 contrastes**, diferencia máxima **4.482758620689655e-28**, frente a tolerancia **1e-12**. Las siete tablas numéricas y su manifiesto son idénticos en bytes entre Mac y Docker.

La [entrega numérica](../registro/diagnostico/fase4/manifest.json) conserva 197 conciliaciones, 9 municipios, 450 grupos de entrenamiento, 30 desgloses de error, 276 sensibilidades nominales, 138 contextos individuales y 87 pares. El [diccionario](../registro/diagnostico/fase4_diccionario.csv) define sus 97 columnas. Las tablas interpretativas tienen un [manifiesto separado de evidencia](../registro/diagnostico/fase4_manifest_evidencia.json); no se presentan como resultados emitidos por el extractor numérico. [Verificación final](../registro/diagnostico/fase4_verificacion.json).

```text
python -m scripts.diagnostico_fase4 --ledger LEDGER_FASE0_FIJADO --salida DIRECTORIO_NUEVO
python -O -m scripts.auditar_diagnostico_fase4 --ledger LEDGER_FASE0_FIJADO --salida DIRECTORIO_GENERADO
```

El ledger completo sigue local y se reconstruye con el procedimiento de fase 0; su SHA256 fijado es `199fed965f34033e94716c8c0edaef189ac94e186ec5a28e8325496269fbdea0`. No sobrescribir entregas anteriores. El código usa la biblioteca estándar y no añade dependencias. Docker se detuvo al terminar las comprobaciones.

**Siguiente alcance propuesto:** fase 5 de aplicabilidad a las 59 reservadas y a campañas futuras. Después, registrar hipótesis concretas y su presupuesto antes de comparar modelos con selección interna y el procedimiento común. Estos hallazgos no autorizan corregir etiquetas, elegir modelos por los errores externos ni usar observaciones posteriores al corte. Las revisiones independientes de las fases previas y del procedimiento común continúan pendientes; no se cierra T15/T16 aquí.

Apoyo de procedimiento: skills de análisis exploratorio y pensamiento crítico científico; Kassis et al. (2026), *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, [DOI](https://doi.org/10.48550/arXiv.2609.00065), versión 2 consultada el 14 de octubre de 2026. Es apoyo metodológico, no evidencia de reducción de MAE. No se publica esta rama ni se edita el GoogleDoc.
