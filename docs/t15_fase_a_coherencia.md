# T15: fase A de coherencia y versiones

Fecha: 14 de octubre de 2026. **Implementación y verificación técnicas locales listas; revisión de la nueva v3 pendiente.** No se ejecutó T15 completo, eligió un ganador, calculó nuevo MAE externo ni ajustó/predijo la entrega final de las 59. No hubo push, merge remoto, comentarios externos o edición del GoogleDoc.

Problema que resuelve: el procedimiento común y las tareas recién integradas tenían referencias de versión desactualizadas; la referencia residual y el centro de entrada de v2 usaban convenciones distintas de exclusión de fila. Además, faltaba un resumen que distinguiese aportar información de elegir apagar un bloque.

Solución que implementa: rama `t15-fase-a-coherencia` desde `dev` 1a9507d, integración local de la rama propia del PR21 y una versión LOO separada, con pruebas, contraste independiente, inventario y estados de revisión. Las ramas de diagnósticos y PR21 conservan sus commits anteriores.

## 1. Versiones, fuentes y conciliación

Se consultó el Plan unificado corregido actual y GitHub. Dev incorporó T09 corregida, T10, T11 y Docker. T13 y T14 siguen abiertos; PR21 permanece abierto/en borrador. Integración en dev y aprobación formal específica de una revisión son hechos distintos: PR18 aparece MERGED y no tiene revisiones formales en la API consultada; esto no descarta revisiones del equipo por otros medios.

El [inventario](../registro/evaluacion_comun/inventario_fase_a.csv) identifica 13 frentes/versiones. Las once fuentes que guarda el contrato común siguen idénticas, incluida la tabla T07 de 197 IDs, 138 rendimientos conocidos y 59 ausentes. No hace falta reextraer clima/relieve ni regenerar T07 por el centrado.

La integración local tuvo conflictos en README, decisiones y uso de IA. Se conservaron las dos secciones de README y todas las filas de ambos lados por ID; no existía colisión con contenido diferente. Antes de añadir la decisión propia de fase A, quedaron 53 decisiones y49 registros IA. Ningún ID fue renumerado. El control final detectó además IA_T07_012 repetida dos veces, con contenido idéntico, ya en dev1a9507d. Se conservó una sola ocurrencia sin cambiar sus campos; quedaron54 decisiones y49 registros IA únicos, incluida la entrada de fase A. Se conserva la [evidencia](../registro/evaluacion_comun/conciliacion_bitacoras_fase_a.json).

Los archivos numéricos principales de T09, T10, T11 y T13 son idénticos a los antecedentes revisados. T14 sí cambió y añade variantes centradas: no se acredita su versión actual a partir de la revisión anterior. No se ejecutó ni modificó su código en esta fase.

## 2. Corrección de la convención LOO

La [versión v3](evaluacion_comun_centrado_loo_v3.md) calcula el centro de cada fila con el mismo conjunto de otros IDs que su referencia residual: municipio, grupo o global. Para municipios con al menos dos ejemplos, alinea el factor n/(n−1) de entradas y residuos. Mantiene escala global, n·lambda, ausencia de intercepto y todos los ejemplos.

El caso más delicado es un municipio con una sola etiqueta en el entrenamiento. En ajuste se usa el grupo/global sin esa fila, igual que su referencia residual; en predicción el municipio conocido utiliza su centro del entrenamiento completo. En esos casos el contraste de ajuste es respecto al respaldo, no un contraste intramunicipal que no puede observarse. Está documentado, se guarda el pool exacto y se probó frente a eliminación explícita. La conformidad del equipo debe abarcar también esta política.

La predicción guarda centros y referencia de entrenamiento; no aprende centros del lote evaluado. Se comprobaron orden/lote, constancia de estado, clone/joblib, etiquetas/entradas externas alteradas, ausencia de propia fila en pools, respaldo de grupo/global, constantes, log de área, indicador D020, errores de contrato y ajuste fallido. Una corrección con sólo una fila de entrenamiento se rechaza porque LOO es indefinible; la referencia sola sí se admite.

v1/v2 y la evaluación aceptada de T09 se conservan. Sus resultados no se transforman retroactivamente ni pasan a identificarse como v3. Adoptar esta formulación para otro procedimiento requiere repetir su selección interna y ajuste, con versión explícita.

## 3. Referencia sola y guardias de versión

Se implementó frecuencia de referencia sola por candidato/escenario, con denominador, número de selecciones y estado completo/parcial. Una ausencia de selecciones no se convierte en frecuencia cero y se rechazan duplicados o banderas incoherentes. Los 25 contextos por escenario siguen siendo el denominador de una comparación completa.

Se probó con dos selecciones internas reales de Sentinel-2, una de A y otra de B: 64 ajustes Ridge internos y ocho referencias internas, sin ajustes externos o de59. Ambas eligieron una corrección en ese control; el reporte queda **parcial, 1/25 contextos por escenario**. No informa la frecuencia global de T15 ni demuestra mejora externa.

Incidencia propia resuelta antes de ejecutar una comparación completa: al preparar la propuesta v3, los procedimientos tenían nombres nuevos pero algunos contrastes conservaban nombres v2. Se actualizaron todos y se añadió una guardia/regresión que rechaza comparadores ajenos a la versión. La propuesta sigue pendiente/no ejecutable; no se escribió una inscripción experimental aceptada en disco.

Se optimizó el cálculo de centros mediante posiciones NumPy manteniendo la media de los IDs explícitos. El contraste independiente verificó la equivalencia; no se usó una resta de sumas que pudiera introducir cancelación al excluir la fila.

## 4. Evidencia de verificación

[Verificación técnica](../registro/evaluacion_comun/verificacion_centrado_loo_v3.json):

| Comprobación | Resultado |
|---|---|
| Suite focalizada Mac |91 pruebas aprobadas:65 históricas y26 nuevas |
| Misma suite Linux/amd64 con Python -O |91 aprobadas, sin desactivar guardias |
| Suite completa Mac |466 distintas aprobadas en conjunto:464 en primera ejecución y2 repetidas con permisos adecuados |
| Matriz independiente por entorno |250 ajustes técnicos, 50 contextos A/B ×5 bloques, lambda fija0.1 |
| Valores de predicción de comprobación por entorno |6,900; no son ejemplos independientes nuevos |
| Diferencia máxima contra matriz independiente |2.6645352591003757e−15 t/ha en ambos entornos |
| Diferencia máxima Mac–Docker |4.440892098500626e−15 t/ha |
| Pools/centros sin fila y residuos frente a eliminación explícita |Coinciden; fuentes/conteos de pools idénticos en bytes Mac–Docker |
| Media municipal de corrección al predecir entrenamiento |Máximo3.122502256758253e−17; no se impone esa media a validación |
| Verificador de originales Docker |166 archivos extraídos idénticos a DataSet.zip |
| Protección de archivos previos |176 huellas sin cambios; incluye originales y componentes/documentos históricos fijados |

Las dos interrupciones de la suite amplia fueron `PermissionError` al crear carpetas temporales en reports desde el entorno restringido. Se repitieron exactamente esas dos pruebas con autorización de ejecución en esa ruta: ambas pasaron. No se modificaron pruebas ni tolerancias. Se conservan los logs de fallo y éxito en la evidencia privada.

Docker se construyó desde el Dockerfile común actual, plataforma Linux/amd64, con imagen `agrocebada-entorno:fase-a-amd64`, identidad b2dea1bd. Se montó el repo sólo para lectura en las comprobaciones Docker y se limitó memoria por proceso. Colima se detuvo tras terminar. Las diferencias observadas son de redondeo, dentro de los límites previos de1e−9 en predicción y1e−10 en estado/matriz; no se ampliaron esos límites.

## 5. Alcance y pendientes específicos del equipo

- **Daf y Migue:** revisar el commit nuevo v3, la política LOO de singletons y la interpretación del reporte de referencia sola. Su conformidad sobre e152abb/v2 está registrada con sus observaciones; no acredita automáticamente código v3 todavía no publicado.
- **Daf, T06:** la duración AGC114 continúa con la incidencia 98 Mac/99 compartido y Docker. Probar días relativos y empate explícito; contrastar los8,668 valores de ambas ventanas/sensores. Si se conserva la tabla compartida, no repetir modelos; si cambia un predictor usado, nueva versión y sólo consumidores afectados. No se modificó su archivo.
- **Migue, T03:** documentar internas B por celda como extensión prospectiva del acuerdo del PR21. El protocolo actual aún no contiene esa extensión. No reescribir la evaluación histórica.
- **Migue, T14 actual:** requiere revisión propia porque cambió el código. Su variante centrada escala después de centrar, retiene intercepto y usa alpha absoluto; es un procedimiento distinto de v3. Esto no demuestra un cálculo erróneo. Observación descriptiva adicional: líneas291–293 clasifican cada valor por divisibilidad y lo llaman precisión. Un4.00 es compatible con mallas0.5/0.1/0.01, pero eso no acredita la precisión de medición. Proponer renombrar como compatibilidad aritmética o usar el contexto municipal T02 con su límite interpretativo; no introducir pesos por supuesta precisión. Esa aclaración sola no exige recalcular modelos.
- **T09/T10/T11/T13 históricos:** su método queda identificado. No se solicitan repeticiones automáticas por esta fase; si incorporan v3 o cambian entradas utilizadas, la selección/ajuste afectados se repiten y versionan.

El [registro de revisiones y alcance](../registro/evaluacion_comun/revisiones_y_alcance_fase_a.json) separa decisiones locales, comentarios del antecedente, integración y revisión actual pendiente. No se enviaron mensajes ni solicitudes nuevas.

## 6. Condición para avanzar

A.1 inventario, A.2 implementación propia y A.5 verificaciones están listos técnicamente. A.3 tiene el alcance definido y la incidencia de Daf identificada; A.4 conserva la conformidad del antecedente y **queda pendiente la revisión de la implementación nueva**. La fase A no se declara aceptada por el equipo ni T15 cerrado.

Se puede preparar la fase B como propuesta documental con esta versión; antes de ejecutar T15, cerrar la revisión del método, registrar definitivamente comparaciones/presupuesto y verificar el ejecutor. La primera aplicabilidad de las59 sigue en C, sin anticipar la entrega final T18. Esta fase demuestra coherencia y reproducción de cálculos, **no una reducción de MAE**.

## Fuentes

Plan unificado corregido, revisión consultada el14oct2026 y conservada en evidencia privada; [documento operativo](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk/edit?tab=t.q0k09ka9rtmy). [PR21](https://github.com/danielalira20/AgroCebada-2026/pull/21), [T03](T03_protocolo_evaluacion.md), [diseño v3](../registro/evaluacion_comun/procedimiento_centrado_loo_v3.json) y fuentes/huellas en su verificación. Apoyo de Scientific Agent Skills citado en el documento del método v3; no evidencia agronómica de ganancia.
