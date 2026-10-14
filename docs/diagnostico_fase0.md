# Diagnóstico de errores y aplicabilidad · fase 0

Responsable de integración: Dani. Rama propia: t15-diagnostico-fase0, desde dev b93e34b3294cb8e9496f24982f41d257b837e26e. Estado: preparación técnica para revisión; no cierra T15/T16 ni inicia la interpretación de fase 1. No se crean asignaciones nuevas.

## Problema que resuelve

Las entregas usan formatos, versiones, variantes y estados de revisión diferentes. Unirlas sólo por ID podría mezclar ventanas, repeticiones, referencias o modelos históricos como si fueran una misma evaluación. También podría confundirse una ausencia prevista con un dato perdido, o una fecha de observación con disponibilidad para predecir.

## Solución que implementa

Un inventario con commits y huellas, un validador completo de las predicciones existentes y reglas explícitas de preguntas, casos, controles y uso temporal. Las fuentes se materializan como copias de sólo lectura; no se ejecuta código de otro frente. La normalización conserva procedimiento, variante, versión, escenario, repetición, partición e ID. No modifica las predicciones originales ni ajusta modelos.

La fuente operativa es [Diagnóstico de errores y aplicabilidad](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk/edit?tab=t.r7d5h4run1h6), revisión documental AHj4eMSFLmYEF7CYIvTbLALD8ve4wa8-06EpI7_LaFiYFnONCEQbNfexjFuh-mfzxisrOSmDarxg51VpNPnrm3xM3StGejRCOuycu4eOPN0. Se conserva un snapshot privado de la pestaña. Su incorporación al documento no acredita un modelo ni una revisión humana.

Diseño previo a esta ejecución: [fase0_diseno.json](../registro/diagnostico/fase0_diseno.json), SHA256 90f2789e1f385967bfa51beb1d7944f6ced2231f48239aa88af6b93dbbca455f, commit bac74ed. Las etiquetas y resultados ya habían sido explorados: fijar ahora estas reglas conserva la cronología; no vuelve ciego el análisis.

## 0.1 · Identidad y compatibilidad de las entradas

[fase0_fuentes.json](../registro/diagnostico/fase0_fuentes.json) identifica 154 archivos de fuentes por commit, tamaño, SHA256, tarea y estado observado. Su huella es f8cf1e2bc8b088d925acdff9693707d1fd513ad535ec32bc8d145995df55132a. Las entregas pendientes se pueden inspeccionar como históricos identificados; no se integran automáticamente como fuentes aprobadas de un modelo nuevo.

| Fuente | Versión Git fijada | Estado observado |
|---|---|---|
| Base T02–T08 | b93e34b3294cb8e9496f24982f41d257b837e26e | dev integra T11; T03/T07 y referencia conservados |
| T09 | 1c8d7eb31a0b2a5c751d949b42b07a1a9aa06cda | PR18 abierto, corrección centrada pendiente de revisión |
| T10 | 57268aa8ac60d143c0585d501308997cc726f4ce | PR17 abierto; revisión formal anterior en d92cb700 |
| T11 | 39082140d908697f35252ee08ff7e641bd7844dc | PR15 fusionado; último cambio respecto a8e67293 es documental |
| T13/T13e | d2aa10b5c770ac1786d2f1f99c7640d01ddeee4a | PR20 abierto |
| T14 | 78324bf5cb4fe8176d2e77f3476877a992939c3c | PR13 abierto |
| Común centrado | e152abbc959796eccddbe9ded7e5645aa463342a | PR21 borrador; todavía sin evaluación completa T15 |

El archivo de fuentes registra el estado observado, no una vigilancia en tiempo real. Una actualización se revisará por contenido y tendrá una identidad nueva; no se sustituye silenciosamente el snapshot. Un PR fusionado tampoco transforma sus resultados históricos en ejecuciones del método común.

Se verifican las tablas y particiones idénticas entre fuentes, el manifiesto de T07, sus 197 IDs, 138 rendimientos y 59 objetivos vacíos, área de origen y metadatos frente al catálogo. Se preservan los dos vacíos de pendiente admitidos por D020, contrastando la cobertura válida menor de 0.5; no se rellenan para este diagnóstico.

La verificación recorre los 71,208 registros OOF completos de 51 series históricas. No usa muestras ni valida sólo un prefijo. Cada serie conserva sus variantes; las ventanas fijas de T09 y las seleccionadas son series diferentes. Rechaza duplicados, filas faltantes, etiquetas distintas, alias de ID contradictorios, números no finitos, referencia o respaldo incompatible y mezclas de versión dentro de una serie. Las 59 no entran en estas predicciones de error.

La referencia se reconstruye por entrenamiento externo, excluyendo todas las parcelas evaluadas en esa partición. Para B se comprueba separación por celda. Los 59 contextos guardados de T09 y sus divisiones internas se verifican por pertenencia y ausencia de solapamiento. C conserva los nueve municipios excluidos como diagnóstico adicional.

| Escenario | Registros canónicos | Sin respaldo municipal | Con respaldo |
|---|---:|---:|---:|
| A | 690 | 675 | 15 |
| B | 690 | 659 | 31 |
| C, disponible en T09 | 138 | 0 | 138 |

Estos son registros de repeticiones de 138 parcelas, no 1,518 ejemplos independientes. La población principal sigue siendo A/sin_respaldo; se conservan todas las parcelas y los respaldos aparte. La compatibilidad de datos no prueba equivalencia de estimadores, ausencia de toda fuga o aporte causal de un bloque. H3 sigue identificado por método; no se rebautizan los históricos como común v2.

## 0.2 · Preguntas y selección previa de casos

Se registran cinco preguntas, todavía sin responder: persistencia del error; fallos compartidos y soporte municipal; asociación con calidad; evidencia de etiquetas y factores ausentes; y aplicabilidad a reservadas/futuro. Se fijan las evidencias y entregables posteriores en [preguntas_y_entregables.csv](../registro/diagnostico/fase0/preguntas_y_entregables.csv).

Las tablas y figuras que se prepararán después quedan registradas en [entregables previstos](../registro/diagnostico/fase0_entregables_previstos.csv). Este complemento explicita el plan documental existente antes de ejecutar fase1; no modifica el diseño previo, los casos elegidos ni los umbrales. Incluye observado/predicho, error firmado, distribución y estabilidad, además de la matriz de procedimientos y fichas de calidad.

El ranking principal toma los 10 mayores promedios de error absoluto de T08 en A/sin_respaldo, usando todos los registros elegibles. Desempata por ID. Se calcula el error en cada repetición antes de promediar: promediar primero las predicciones podría cancelar errores de signos opuestos. Se conserva este criterio aunque otro modelo ordene los casos de otra manera.

[casos_preseleccionados.csv](../registro/diagnostico/fase0/casos_preseleccionados.csv) fija los 10 IDs y la regla aplicada. No es todavía un diagnóstico causal ni la distribución completa del error de fase 1. Las conclusiones generales posteriores deberán usar las 138, y B y respaldos deberán mostrarse con sus propios denominadores.

Se obtiene un control para cada caso, sin reutilización, del mismo municipio y fuera de los diez principales. La selección usa exclusivamente metadatos: primero discrepancias de contorno, parcela angosta/pequeña y ausencia de pendiente; después diferencia de log área; después diferencia de capturas Planet abr_oct; por último ID. No consulta rendimiento ni error del control. Una prueba altera esos valores y verifica que la elección no cambia.

Los diez controles disponibles quedan en [controles_preseleccionados.csv](../registro/diagnostico/fase0/controles_preseleccionados.csv). Son los mejores disponibles bajo la regla, no una certificación de equivalencia. Se muestran las distancias y discrepancias. Si no hubiera candidatos del mismo municipio se conservaría la ausencia; no se inventaría un control ni se buscaría por su buen resultado. No se añadieron umbrales aprendidos mirando el MAE.

## 0.3 · Alcance temporal y de uso

[alcance_temporal.csv](../registro/diagnostico/fase0/alcance_temporal.csv) conserva los 60 campos de T07: rol, producto, unidad declarada, periodo, fin de observación explícito, significado del vacío y evidencia de disponibilidad. Señala cuatro unidades físicas todavía pendientes, LAI2 Planet y VI6T Landsat en ambas ventanas. No les atribuye unidades nuevas.

El uso comprobado de este diagnóstico es reconstrucción retrospectiva de la campaña 2025, con el corte observacional provisional 31-oct-2025. Los resúmenes abr_oct/jun_oct llegan a octubre; los atributos al_corte usan observaciones del 17 al 31 de octubre. No se mueve el corte por un resultado.

Una fecha de observación no demuestra la primera publicación ni la versión disponible entonces. Se reutiliza la declaración de T07/T04: disponibilidad histórica del paquete FIRA no documentada. El inventario mantiene disponible_al_corte como no acreditado; no fabrica fechas con el mes del archivo o su fecha de descarga.

Para un pronóstico operacional deben acreditarse las entradas y también los rendimientos disponibles para entrenar la referencia en la fecha de decisión. Estimar parcelas reservadas utilizando etiquetas de la misma campaña no demuestra que esas etiquetas estuvieran disponibles antes de cosechar. Es una pregunta de cronología pendiente, no una afirmación de que FIRA las hubiera publicado tarde.

Una campaña futura necesita validación temporal con nuevos rendimientos. C evalúa transferencia a municipios no vistos; no sustituye otra campaña. La inspección de soporte de las 59 no inventa errores reales ni intervalos de confianza individuales. Recuperar índices ya existentes o investigar datos externos después requerirá una carencia e hipótesis explícitas, no una búsqueda para acertar los diez casos seleccionados.

## Reproducción y controles

Desde el repositorio, con los commits declarados disponibles localmente:

~~~sh
python -m scripts.diagnostico_fase0 --preparar-fuentes --fuentes reports/diagnostico_fuentes_v1
python -m scripts.diagnostico_fase0 --fuentes reports/diagnostico_fuentes_v1 --salida reports/diagnostico_fase0_v1
AGRO_DIAG_FUENTES=reports/diagnostico_fuentes_v1 python -m unittest tests.test_diagnostico_fase0
~~~

La preparación usa Git para leer blobs exactos; no accede a la red ni ejecuta modelos. Si falta un commit se debe recuperar el declarado y repetir en un destino nuevo. La validación posterior sólo usa la biblioteca estándar de Python; puede ejecutarse en Docker con la copia de fuentes y repositorio de sólo lectura.

Se rechazan rutas que escapan del root, symlinks, entradas no regulares, CSV no rectangulares, JSON con claves duplicadas o NaN/Infinity y archivos que exceden el límite de lectura. Una salida se publica atómicamente sólo tras superar todos los controles; no se sobreescribe un destino previo. Las barreras usan excepciones explícitas y funcionan con Python optimizado.

Hay 23 regresiones concretas. Las pruebas unitarias alteradas son copias aisladas, no ejemplos ficticios de entrega. La evidencia de Mac, Docker, reproducción y auditor independiente está en [fase0_verificacion.json](../registro/diagnostico/fase0_verificacion.json).

La salida completa local contiene el ledger normalizado regenerable. Sólo se conservan en Git los ocho archivos compactos identificados como publicables, diseño, fuentes y evidencia. El manifiesto distingue el archivo local no publicable; no afirma que sus filas sean datos de entrenamiento nuevos ni un resultado T15.

## Incidencias y resolución

El primer inventario se detuvo por el CSV vacío de control revuelto T10. Se verificó su activación: ninguna fila es candidata_a_promover, por lo que la tabla sin resultados corresponde a un control no activado. No basta encontrar un archivo vacío; se añadió una prueba que rechaza la ausencia si el control sí debía activarse. Las OOF obligatorias siguen exigiendo filas y cobertura completa.

Nuestro adaptador inicial esperaba NaN y ausencia física de pendiente. La fuente conserva un vacío porque la cobertura está bajo el piso D020, aunque exista una media física parcial. Se corrigió el adaptador consultando esa cobertura, sin imputar, eliminar ni editar registros originales.

La bitácora de decisiones de dev no terminaba en salto de línea. Se añadió únicamente el separador necesario antes de la entrada propia; su prefijo original se conserva exactamente, sin reescribir filas ni renumerar entradas.

T11 se fusionó durante el avance del equipo y T10 incorporó esa rama. Se fijó dev actualizado y las huellas exactas, sin reutilizar la copia de revisión anterior como si fuera la vigente. No se cambió el código de los responsables.

## Cierre de alcance

La fase 0 prepara inventario, preguntas, máscaras, selección de casos/controles y límites temporales. No ejecuta la interpretación, gráficos o explicaciones de fase 1; no entrena, congela un ganador ni genera las 59 predicciones finales. La aceptación humana se conserva pendiente. El siguiente alcance es distribución, dirección y estabilidad del error sobre estas entradas identificadas.

Skills utilizadas: análisis exploratorio, pensamiento crítico científico y scikit-learn. Referencia de su biblioteca: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents. [DOI](https://doi.org/10.48550/arXiv.2609.00065), versión consultada v2. Constituye apoyo de procedimiento; no evidencia de mejor MAE.
