# Auditoría del sistema de investigación y procedencia

Fecha: 19 de octubre de 2026. Base de trabajo indicada: `efbb2dd`. Alcance: investigación local y lectura de artefactos; no se ejecutaron extractores, entrenamientos, evaluaciones completas ni suites de pruebas. CONFIRMED significa verificado en archivos actuales o en la comprobación descrita; una declaración histórica de una corrida se identifica como tal y no se presenta como repetida hoy. INFERRED expresa una consecuencia razonada; UNKNOWN marca evidencia no acreditada.

## Dictamen

**CONFIRMED.** El repositorio contiene dos sistemas relacionados: investigación retrospectiva sobre la cosecha 2025 y una aplicación que consume sus datos/resultados. La investigación prepara 197 parcelas, conserva 138 rendimientos conocidos y 59 objetivos vacíos, compara referencias y correcciones mediante particiones compartidas y produce una entrega de 59 valores. Los contratos rechazan mezclar las reservadas con las etiquetas de evaluación (`scripts/evaluacion_comun_contrato.py:74`, `scripts/evaluacion_comun_contrato.py:99`, `scripts/t18_predicciones_finales.py:80`).

**CONFIRMED.** T15 no promueve ningún bloque de clima, relieve/área o satélite. La mediana municipal tiene menor MAE puntual que la media, pero incumple el umbral de mejora y su intervalo espacial incluye cero. T16 propone adoptarla como excepción posterior a resultados y condicionada a aprobación; el archivo T18 ya existe y la configuración de la app ya la llama oficial. Hay una diferencia entre existencia del artefacto, elección práctica y aprobación documentada (`docs/t15_resultados.md:7`, `docs/t16_procedimiento_final.md:3`, `registro/decisiones.csv:68`, `app/agrocebada_app/config.py:16`).

**INFERRED.** La evidencia permite un resumen municipal de 2025 y cuentas condicionadas a rendimientos elegidos; no acredita un pronóstico para otra campaña, una distribución de años malos/buenos o probabilidades personales de pérdida. T16 declara una sola campaña y falta de manejo/siembra/variedad (`docs/t16_procedimiento_final.md:183`).

## Mapa de responsabilidades y productos

Los responsables de esta tabla son los registrados en los documentos; no se infiere aceptación humana por existir un CSV o un manifiesto.

| Tarea | Responsable / revisión registrada | Qué produce y quién lo consume | Evidencia |
|---|---|---|---|
| T01 | Dani / Diego | Entorno mínimo, contrato común y comprobación sintética geoespacial. Docker raíz prepara investigación; los originales se montan aparte. | `docs/tareas_dani.md:7`, `Dockerfile:1`, `README.md:48` |
| T02 | Jass / Dani | Catálogo único, cruce CSV–shapefile, soporte espacial, precisión de etiquetas y alertas de contorno. Alimenta T03/T07. | `docs/tareas_dani.md:15`, `docs/T03_protocolo_evaluacion.md:80`, `analisis/auditoria_catalogo_y_etiquetas/tablas/precision_etiqueta_por_municipio.csv:1` |
| T03 | Migue / Jass | Particiones por ID, diagnóstico 138/59 y reglas de evaluación/selección. Consumidor transversal T08–T16. | `docs/T03_protocolo_evaluacion.md:3`, `scripts/t03_evaluacion.py:11` |
| T04 | Dani / Jass | Inventario del maestro y agregación espacial de lluvia/Tmin/Tmax: 197 × 48 meses 2022–2025 × 3 variables = 28,368 registros; tabla compacta, calidad y procedencia. Alimenta T07/T09/T14. | `docs/tareas_dani.md:8`, `docs/t04_fase3_completa.md:11`, `docs/t04_entrega_equipo.md:11` |
| T05 | Jass / Dani | Elevación/pendiente por polígono y controles de cobertura/centroide; columna de pendiente D020 para T10/T07. | `docs/t05_relieve.md:3`, `docs/t05_relieve.md:8`, `docs/t05_relieve.md:64` |
| T06 | Daf / Jass | Series por sensor, calidad/cobertura, resúmenes compactos y ventanas. No es todavía un modelo predictivo. | `docs/t07_fichas_atributos.md:104`, `docs/T06_satelite.md:11`, `docs/T06_satelite.md:27` |
| T07 | Dani / Jass | Unión por ID y tabla común 197 × 60; roles, diccionario, calidad, huellas y fichas de disponibilidad futura. | `docs/t07_contrato.md:3`, `docs/t07_contrato.md:84`, `docs/t07_contrato.md:112` |
| T08 | Migue / Daf | Referencias globales/municipales, respaldo y contracción; OOF A/B y predicciones de referencia para las 59. | `docs/T08_referencias.md:3`, `scripts/t08_referencias.py:7` |
| T09 | Dani / Migue | Territorio frente a clima solo, municipio+clima y residuo; versiones original/centrada preservadas. No promoción climática. | `docs/tareas_dani.md:10`, `docs/tareas_dani.md:70`, `docs/t09_centrado_evaluacion_v2.md:47` |
| T10 | Jass / Daf | Aporte de relieve/área, sensibilidad por tamaño/cobertura; no promoción. Método histórico distinto de T15 v3. | `docs/T10_relieve_area.md:3`, `analisis/aporte_relieve_y_area/informe_relieve_y_area.md:26` |
| T11 | Daf / Migue | Aporte satelital y controles de calidad frente a referencia. Versión v2.1 conserva su selección histórica. | `docs/T11_aporte_satelital.md:3`, `docs/T11_aporte_satelital.md:36` |
| T12 | Implementa Jass; original Diego / Migue pendiente | Heterogeneidad municipal y boosting pequeño con controles; resultado R2, se conserva la media. | `docs/T12_heterogeneidad_municipal.md:3`, `analisis/heterogeneidad_municipal/informe_heterogeneidad_municipal.md:9` |
| T13 | Daf / Dani y Jass | Ablación de índices y extensión por familias; usa T11 histórico, no identifica causalidad agronómica. | `docs/T13_indices.md:3`, `docs/T13_indices.md:22` |
| T14 | Migue / Diego | Lluvia/Tmin/Tmax con representación propia y variantes centradas; ninguno cumple T03. | `docs/T14_clima.md:3`, `docs/T14_clima.md:17`, `docs/T14_clima.md:66` |
| T15 | Dani / Daf | Ocho combinaciones con procedimiento común v3; OOF, selección interna, trazas/estados y auditor independiente. | `docs/tareas_dani.md:11`, `docs/t15_resultados.md:74` |
| T16 | Dani / Migue en plan; propuesta redactada por Jass | Congela procedimiento y justifica excepción media→mediana, todavía condicionada en el documento actual. | `docs/tareas_dani.md:12`, `docs/t16_procedimiento_final.md:3` |
| T17 | Diego / Dani | App consumidora de referencias y límites. Esta auditoría sólo contrasta su configuración; comportamiento online corresponde al informe de app. | `docs/tareas_dani.md:15`, `docs/T08_referencias.md:79`, `app/agrocebada_app/config.py:10` |
| T18 | Dani / Migue en plan; implementación y entrega registrada por Jass | 59 predicciones de mediana, detalle y trazabilidad; depende de elección T16. | `docs/tareas_dani.md:13`, `registro/decisiones.csv:69`, `scripts/t18_predicciones_finales.py:11` |
| T19 | UNKNOWN: responsable integral no acreditado aquí; Dani aporta su frente | Informe que debe consumir identidad/limitaciones de T16/T18. No hay evidencia inspeccionada de cierre. | `docs/tareas_dani.md:15`, `docs/evaluacion_comun.md:100` |
| T20–T22 | UNKNOWN en el alcance local inspeccionado | El README y plantilla reconocen T01–T22; T21 exige plataforma amd64. No se inventan responsabilidades, entregables ni cierre ausentes. | `README.md:14`, `README.md:91`, `.github/ISSUE_TEMPLATE/tarea.yml:2` |

## Contratos de datos y evaluación

**CONFIRMED.** La unidad es parcela–campaña 2025. T07 conserva IDs, conjunto, rendimiento y metadatos de T02 literalmente; sus 60 columnas se dividen en 35 candidatas, 18 de calidad, cinco metadatos, un objetivo y una de referencia/evaluación. No todas pueden convertirse automáticamente en predictores. ID, calidad y grupo tienen restricciones explícitas; el área requiere autorización de uso. La pendiente bajo cobertura 0.5 se deja vacía en su columna T10, sin borrar la parcela (`docs/contrato_datos.md:3`, `docs/t07_contrato.md:106`, `docs/t07_contrato.md:112`, `scripts/evaluacion_comun_contrato.py:74`, `scripts/evaluacion_comun_contrato.py:195`).

**CONFIRMED.** El catálogo no aporta 197 etiquetas. Son 138 conocidas y 59 vacías; la tabla climática mensual y las series no aumentan el número de cosechas independientes. El contrato exige campaña 2025, 197 IDs y 138/59; las particiones requieren 690 claves etiqueta–repetición y excluyen reservadas (`scripts/evaluacion_comun_contrato.py:76`, `scripts/evaluacion_comun_contrato.py:82`, `scripts/evaluacion_comun_contrato.py:95`, `scripts/evaluacion_comun_contrato.py:100`).

| Escenario | Separación y propósito | Limitación |
|---|---|---|
| A, principal | Cinco particiones por municipio × cinco repeticiones: parcelas en municipios conocidos, como las 59. | Vecinas/celda compartida pueden aparecer entre ajuste y evaluación. |
| B, obligatorio | Celdas CHIRPS completas en cinco particiones × cinco repeticiones. | Dos celdas con 34 parcelas dominan agrupaciones; no elimina dependencia entre celdas vecinas. |
| C, descriptivo | Dejar fuera municipios completos. | Territorio no visto; no es el caso de las 59 ni una evaluación entre años. |

CONFIRMED: definiciones y limitaciones en `docs/T03_protocolo_evaluacion.md:35`; construcción A/B con semillas fijas en `scripts/t03_evaluacion.py:36` y `scripts/t03_evaluacion.py:77`. La elección A usa soporte, no rendimientos de las 59 (`docs/T03_protocolo_evaluacion.md:39`).

**CONFIRMED.** La regla decide en A/`sin_respaldo`: 135 parcelas, 675 OOF por procedimiento; en B son 135 parcelas y 659 registros elegibles. La referencia común es `media_mun__resp_grupo`. Promover exige ΔMAE ≤ −0.01 t/ha, cota superior IC95 por celdas < 0, signo favorable en ≥4/5 repeticiones y ΔRMSE ≤ +0.01. El bootstrap utiliza 5,000 remuestras y semilla 20261006; 22 celdas en sin_respaldo. No son intervalos individuales para las 59. En B importan las ponderaciones por parcela frente a registro/repetición (`docs/T03_protocolo_evaluacion.md:54`, `docs/T03_protocolo_evaluacion.md:56`, `docs/T03_protocolo_evaluacion.md:58`, `docs/T03_protocolo_evaluacion.md:67`, `docs/t15_resultados.md:24`).

**CONFIRMED.** El respaldo general de referencia es municipio→grupo de registro→global, aprendido sólo con entrenamiento; el grupo `Cebada`/`CEBADA` es procedencia, no variedad ni causa agronómica (`scripts/t08_referencias.py:61`, `docs/T08_referencias.md:21`). Si un municipio tiene una etiqueta, una reservada sí puede usar esa etiqueta municipal; no activa respaldo. AGC_120 recibe 2.5 de la única etiqueta de Nanacamilpa, a 1.9 km. En entrenamiento residual LOO esa fila única sí necesita grupo/global (`docs/T03_protocolo_evaluacion.md:109`). La fila de soporte que dice «se activa un respaldo» para AGC_120 contradice la implementación y las aclaraciones posteriores (`docs/T03_protocolo_evaluacion.md:19`, `docs/t16_procedimiento_final.md:198`).

**CONFIRMED.** T15 v3 aprende transformaciones dentro del entrenamiento, calcula residuo y centro excluyendo la misma fila y comparte su pool municipio/grupo/global; al predecir usa centros del entrenamiento completo. Las internas A son estratificadas por municipio (mínimo cuatro; resto `otros`), y B usa cuatro GroupKFold por celda sin barajar. La referencia sola compite con las opciones de corrección. Esa versión no equivale a los métodos históricos T10/T11/T13/T14 (`scripts/evaluacion_comun_centrado_loo.py:52`, `scripts/evaluacion_comun_centrado_loo.py:95`, `scripts/evaluacion_comun_centrado_loo.py:137`, `scripts/evaluacion_comun_modelo.py:133`, `scripts/t15_comparaciones_contrato.py:49`).

## Resultados vigentes, decisión y entrega

| Población principal A/sin_respaldo | MAE t/ha | RMSE medio por repetición | R² medio por repetición |
|---|---:|---:|---:|
| Media municipal | 0.320490 | 0.492593 | 0.658577 |
| Mediana municipal | 0.312585 | 0.490683 | 0.661223 |

**CONFIRMED.** La mediana mejora −0.007905 t/ha, con IC95 por celdas [−0.016298, +0.005805], favorable en cinco repeticiones; falla dos criterios de T03. La referencia en A/todas da 0.319250, que no debe reemplazar 0.320490 para decidir. T15 tiene ocho bloques más la referencia, 12,420 OOF, 400 selecciones y 450 estados externos; la mejor reducción puntual es GP −0.000300 y no promueve (`docs/t16_procedimiento_final.md:49`, `docs/t16_procedimiento_final.md:60`, `docs/t15_resultados.md:11`, `docs/t15_resultados.md:25`, `docs/t15_resultados.md:81`).

**CONFIRMED como registro histórico, no repetido hoy.** La auditoría independiente publicada informa 554,410 controles y reconstrucción de 282 Ridge externos sin importar productor. Ello respalda álgebra, particiones y reportes; el propio dictamen excluye validación externa ciega, exactitud de medición en campo y otra campaña (`registro/t15_resultados/auditoria_independiente.json:2`, `registro/t15_resultados/auditoria_independiente.json:21`, `registro/t15_resultados/auditoria_independiente.json:25`).

**CONFIRMED.** T18 usa el CSV oficial y municipio/grupo cruzados con shapefile; exige 138 etiquetas, 59 reservadas vacías, municipios con ejemplos, IDs/orden y valores finitos/positivos; contrasta mediana pandas, estimador T08 y referencias T08. Sus 59 valores se asignan por municipio, sin clima, satélite, relieve ni área como predictor; el área se copia al archivo de entrega (`scripts/t18_predicciones_finales.py:72`, `scripts/t18_predicciones_finales.py:89`, `scripts/t18_predicciones_finales.py:117`). La traza registra Linux x86_64, Python 3.12.15, commit `9e13b02…` y fecha 2026-10-19; no observa rendimientos reales de las 59 (`registro/t18/trazabilidad.json:28`, `registro/t18/trazabilidad.json:58`, `registro/t18/trazabilidad.json:69`).

**UNKNOWN.** No se verificó en servicios externos la aprobación de T16 ni la aceptación del formato por FIRA. El documento/decisión vigentes aún dicen propuesta condicionada, y la fila T18 mantiene esa dependencia (`registro/decisiones.csv:68`, `registro/decisiones.csv:69`). La plantilla original no está versionada según esa misma fila.

## Procedencia: defecto verificable de bytes en T18

**CONFIRMED, comprobación local de lectura.** `registro/t18/predicciones_finales.csv` contiene BOM UTF-8 y 60 saltos LF, ninguno CRLF. Su SHA-256 actual es `4cbe214d056e79b8c81d890a0c27b078a2f78807c3b397f4027f366a8e712d7c`. La traza declara CRLF y `27bc277d10b4dd730c277f3a1e71f9f1a473b9ca5f1e02ad31ba4b76ecc7c9c7` (`registro/t18/trazabilidad.json:56`, `registro/t18/trazabilidad.json:73`).

Se convirtió LF→CRLF **sólo en memoria** y se obtuvo exactamente el hash de la traza. El detalle y ambos scripts T08/T18 sí coinciden con sus huellas registradas. La política `.gitattributes:4` normaliza texto a LF, carece de excepción T18 y `git ls-files --eol` confirma LF en índice y copia. **INFERRED, causa altamente sustentada:** normalización de Git después de generar la entrega; no hay evidencia de cambio de valores. Esto rompe identidad de bytes/formato declarado aunque conserve los datos.

La función generadora siempre escribe CRLF (`scripts/t18_predicciones_finales.py:153`), y las pruebas reales exigen CRLF, reproducción exacta y hash coincidente (`tests/test_t18_predicciones_finales.py:201`, `tests/test_t18_predicciones_finales.py:233`, `tests/test_t18_predicciones_finales.py:237`). **INFERRED:** esas aserciones fallarían con este archivo cuando la clase real esté habilitada; su ejecución depende de originales locales (`tests/test_t18_predicciones_finales.py:191`). No se ejecutó la prueba ni se reparó el archivo. Se debe conciliar política de almacenamiento/formato/traza al abordar esa entrega.

## Disponibilidad temporal y espacial de fuentes

| Fuente | Qué acredita la entrega | Qué no acredita para operar otra campaña |
|---|---|---|
| Etiquetas | Una cosecha 2025; precisión y repetición municipal documentadas. | Protocolo/humedad/denominador de rendimiento, manejo, siembra/variedad, representatividad anual. |
| Clima | 48 meses 2022–2025, lluvia mensual y temperaturas; agregación espacial por área física en rejilla geográfica, cobertura/NoData y centroide. | Variante científica exacta y primera publicación de los TIFF; fecha histórica de acceso a esa edición. Octubre observado no implica disponible al 31-oct. |
| Relieve | INEGI CEM4 a 120 m, EPSG:6372; media por área válida; pendiente Horn según LEEME y piso D020. | Fecha de adquisición/edición y acceso futuro; detalles reales dentro de una parcela menores que una celda. |
| Satélite | Series Sentinel-2/Planet/Landsat, corte primero al 31-oct-2025 y después suavizado; ventanas abr_oct/jun_oct y calidad por sensor. | Publicación/latencia histórica, acceso equivalente futuro y todas las unidades físicas de LAI2/VI6T; nubosidad no es automáticamente superficie válida. |

CONFIRMED: `docs/t04_version_disponibilidad.md:7`, `docs/t04_version_disponibilidad.md:17`, `docs/t04_version_disponibilidad.md:36`, `scripts/t04_espacio.py:91`, `docs/t05_relieve.md:14`, `docs/t05_relieve.md:23`, `docs/T06_satelite.md:21`, `docs/T06_satelite.md:27`, `docs/t07_fichas_atributos.md:87`, `docs/t07_fichas_atributos.md:105`.

**CONFIRMED.** T07 conserva pendientes explícitos por fuente y requisitos futuros; una huella identifica el archivo usado, no su publicación histórica. `ndvi_al_corte` requiere la curva anterior al periodo final de resumen por el suavizado; la base antes del máximo no prueba suelo desnudo o siembra. El documento T06 todavía afirma «la base es el suelo antes de la siembra», matizado por las fichas posteriores (`docs/T06_satelite.md:84`, `docs/t07_fichas_atributos.md:77`, `docs/t07_fichas_atributos.md:91`).

**INFERRED.** Antes de un uso prospectivo harían falta una fecha de decisión explícita, insumos disponibles entonces, identidad/versiones, control espacial, nuevas etiquetas y evaluación entre campañas. La mera incorporación de clima 2022–2024 sin rendimientos no permite estimar el efecto del año ni calibrar pérdida de cosecha. Los resúmenes de fin de temporada no existen a mitad del ciclo (`docs/T11_aporte_satelital.md:63`, `docs/t16_procedimiento_final.md:183`).

## Infraestructura y verificación realmente presentes

**CONFIRMED.** El Dockerfile raíz usa Python 3.12.15, dependencias fijadas y UTF-8; copia únicamente el verificador de entorno como comando por defecto, no empaca la app ni los originales (`Dockerfile:1`, `Dockerfile:5`, `Dockerfile:20`). Los lanzadores construyen imagen, montan el repositorio, comprueban datos y después ejecutan el comando; sin comando descubren pruebas en `tests/`, no `app/tests/` (`ejecutar.ps1:15`, `ejecutar.ps1:22`, `ejecutar.ps1:29`). No hay workflow CI bajo `.github/` en el inventario inspeccionado: sólo plantilla de PR e issue.

**CONFIRMED.** El control de datos verifica `data/raw/DataSet.zip` frente a T04 y archivos extraídos frente al ZIP; si ambos faltan avisa y permite continuar. No significa originales comprobados. El T18 por defecto lee otra ruta, `data/DATASET_RETO_AGRO_2026`, aunque admite `--datos`; por tanto no debe inferirse que el preflight de los lanzadores verifique esa copia concreta (`scripts/comprobar_datos.py:67`, `scripts/comprobar_datos.py:72`, `scripts/t18_predicciones_finales.py:158`). T18 registra huellas de sus entradas, pero no exige en ese punto su igualdad con un maestro esperado.

**CONFIRMED.** Existe cobertura de software para corrupción de etiquetas/roles y fuentes T07; LOO y matrices independientes; aislamiento de validación externa; GroupKFold sin celdas compartidas; guardias del ejecutor; formato y comparación de T18 (`tests/test_t07_verificar.py:54`, `tests/test_evaluacion_comun_centrado_loo.py:59`, `tests/test_evaluacion_comun_centrado_loo.py:221`, `tests/test_t15_comparaciones.py:98`, `tests/test_t15_ejecutor.py:81`, `tests/test_t18_predicciones_finales.py:103`). La auditoría portable T15 verifica fuentes/artefactos y puede reconstruir resultados sin repetir selección/entrenamientos (`scripts/t15_auditar_entrega.py:1`, `scripts/t15_auditar_entrega.py:55`).

**UNKNOWN.** No se afirma que esas pruebas pasen en este checkout: no se ejecutaron hoy. Conteos y aprobaciones históricos tienen fecha/entorno propios; las pruebas reales pueden omitirse si faltan originales. Tampoco se verificó despliegue, servicio remoto o estado productivo. Datos originales, resultados locales, exploraciones de `context/` y paquete generado de app quedan ignorados por Git (`.gitignore:2`, `.gitignore:35`, `.gitignore:38`).

## Contraste científico de la propuesta de planeador

La propuesta se leyó sólo después de construir el mapa actual y por instrucción expresa de root. No se modifica ni se implementa (`context/planeador_campaña.md`).

1. **Años bajos/altos. CONFIRMED + INFERRED.** La propuesta define sus extremos con percentiles entre parcelas cosechadas en 2025 (`context/planeador_campaña.md:169`, `context/planeador_campaña.md:491`). Son variación entre parcelas de una sola campaña, no variación de una parcela entre años. Llamarlos «año bajo/alto» induce un significado que los datos no identifican, aun con aviso general. Rótulos fieles: «rendimiento bajo/central/alto observado en parcelas de 2025»; para pocos datos, «menor/mayor cosecha registrada». Ninguno es intervalo predictivo, escenario climático o probabilidad de que al agricultor le toque ese valor.
2. **Año normal. INFERRED.** Cambiar el título a «frente a un año normal» (`context/planeador_campaña.md:223`) no queda sustentado por tres años 2022–2024 de contexto climático sin cosechas. Puede decirse «frente al promedio 2022–2024» si ésa es realmente la base de cálculo. Tres años disponibles no certifican una normal climática ni un año agronómico típico. No se buscó una definición normativa externa porque el contrato excluye web.
3. **Comparador equivocado. CONFIRMED.** El resumen propone que T13/T14/T15 no mejoraron frente a la mediana (`context/planeador_campaña.md:57`); los experimentos citados comparan contra `media_mun__resp_grupo` (`docs/T13_indices.md:22`, `docs/T14_clima.md:6`, `docs/t15_resultados.md:11`). El resultado observado es «ninguno cumplió la regla frente a la referencia media con esos procedimientos»; no prueba inutilidad del satélite/clima ni una comparación formal nueva contra mediana.
4. **Municipio y respaldo. CONFIRMED + INFERRED.** Municipio basta para calcular el estadístico cuando existen etiquetas del municipio. El fallback T08 requiere grupo de registro; no se deduce de un municipio nuevo desconocido. C4 propone fallback global (`context/planeador_campaña.md:244`), que sería otra política en ese caso. Para los nueve municipios actuales hay etiquetas; para las 59 actuales no altera nada. Fuera de ese soporte se necesita limitar el alcance o declarar expresamente la nueva referencia regional, sin atribuirle validación local/T18. El grupo es procedencia, no un atributo agronómico inferible para cualquier usuario (`scripts/t08_referencias.py:61`, `docs/T08_referencias.md:21`).
5. **Equilibrio. INFERRED.** Costo por hectárea / precio por tonelada es una identidad contable bajo esos supuestos. Multiplicar rendimiento por hectáreas da producción condicionada al rendimiento elegido. La fracción de parcelas 2025 que superó el umbral describe la muestra, no probabilidad de no perder en otra campaña ni para una parcela nueva. Debe quedar claro qué costos ingresó el usuario y que el cálculo no estima costos omitidos ni precio futuro; no requiere convertirlo en una recomendación financiera.
6. **Confianza y soporte. INFERRED.** Cantidad de etiquetas, MAE histórico, rango observado y probabilidad futura son conceptos distintos. A/sin_respaldo evalúa 135 parcelas y no demuestra calidad específica de municipios con una etiqueta. Una coherencia numérica con T18 comprueba regla e identidad, no validez prospectiva. En Emiliano Zapata tres etiquetas idénticas pueden dar rango nulo sin demostrar ausencia de riesgo.

## Soporte municipal útil para revisar lenguaje y escenarios

**CONFIRMED.** Valores mínimo/máximo y conteos salen del resumen compacto T02, no de nuevas estadísticas sobre originales. No son límites posibles de otra campaña.

| Municipio | Etiquetas 2025 | Mín–máx t/ha | Consecuencia para presentación |
|---|---:|---:|---|
| Chignahuapan | 71 | 2.15–5.59 | Más soporte, sigue siendo una campaña. |
| Calpulalpan | 30 | 2.50–3.50 | Sólo tres valores distintos; todas las etiquetas múltiplos de 0.5. |
| Singuilucan | 16 | 2.00–3.70 | Siete valores distintos; no probabilidad anual. |
| Almoloya | 10 | 4.14–4.87 | Justo en el umbral propuesto para percentiles; rango descriptivo. |
| Cuautepec de Hinojosa | 5 | 4.40–4.79 | Mín/máx muestral con pocos datos. |
| Emiliano Zapata | 3 | 3.50–3.50 | Rango nulo por tres etiquetas iguales, no riesgo nulo. |
| Apan | 1 | 3.00–3.00 | No hay distribución local estimable. |
| Nanacamilpa de Mariano Arista | 1 | 2.50–2.50 | Misma limitación; una de las 59 depende de esta sola etiqueta. |
| Tepeapulco | 1 | 4.45–4.45 | No hay distribución local estimable. |

Fuente por filas: `analisis/auditoria_catalogo_y_etiquetas/tablas/precision_etiqueta_por_municipio.csv:2` a `:10`; conteos coinciden con `registro/t18/trazabilidad.json:35`. Las 59 se reparten en seis municipios (29/14/7/4/4/1), no los nueve del conjunto completo (`docs/t16_procedimiento_final.md:106`).

## Contradicciones y riesgos para integrar

| Prioridad | Hallazgo verificado | Consecuencia / decisión necesaria |
|---|---|---|
| Alta | La mediana es «oficial» en config y T18 está generado, pero T16/decisión siguen como propuesta condicionada. | No atribuir aprobación ni promoción estadística. Root debe separar estado documental y comportamiento implementado. |
| Alta | Bytes LF actuales de entrega no coinciden con traza CRLF; causa compatible exactamente con `.gitattributes`. | Afecta cadena de custodia y reproducción exacta; conciliar antes de certificar archivo de entrega. |
| Alta | Escenarios de parcelas 2025 nombrados como años; «año normal» para base breve. | Corregir semántica antes de presentar utilidad prospectiva. |
| Media | README:5 afirma no existir finales; T18 actual existe. T08 conserva instrucciones de media previa a T16. | Conservar historia con fecha, añadir estado actual sin reescribir resultados antiguos. |
| Media | Propuesta atribuye comparaciones históricas a mediana; comparador real es media. | Corregir justificación; no inventar evaluación nueva. |
| Media | T18 por defecto y verificador maestro leen copias distintas de originales. | No certificar integridad de esa copia por haber pasado otro preflight. |
| Media | B y los métodos históricos no siempre tienen internas/centrado equivalentes; T12 mantiene observaciones de revisión. | Citar versión y ponderación; evitar ranking conjunto sin conciliación (`docs/revision_t15_t12_cierre.md:17`). |
| Media | Exploraciones adicionales de T16 están en `context/`/`reports/` ignorados. | Sus cifras no son reproducibles sólo desde el repo; no usarlas como validación independiente (`docs/t16_procedimiento_final.md:144`). |

## Exclusiones y entrega

Se inspeccionaron scripts y contratos T03/T07/T08/T15/T18, componentes comunes v3, pruebas seleccionadas, resúmenes/manifiestos compactos, documentación T01–T18 e informes T10/T12, infraestructura raíz y plantilla GitHub. La propuesta se inspeccionó tras el mapa. Sólo se leyó `app/agrocebada_app/config.py` para contraste; no se pretende auditar aquí el comportamiento online ni el código completo de app.

No se leyeron originales privados masivamente, ni se reprodujo geoprocesamiento, entrenamientos, pipelines o pruebas. No se usó web, no se verificaron GitHub/Drive/servicios productivos, no se cambió propuesta/código/datos/configuración y no se enviaron mensajes externos. La comprobación adicional fue únicamente de huellas/formato local de archivos T18 y conversión CRLF en memoria. Las escrituras de esta subtarea se limitan a este informe y el contrato TASK-003.
