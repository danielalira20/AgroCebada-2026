# T09 · Diseño del aporte climático

**Versión 1.0 · 11 de octubre de 2026. Responsable: Dani. Revisor previsto: Migue.**

**Estado:** diseño local fijado por Dani mediante su autorización para avanzar sin esperar respuesta de Migue. La revisión independiente de Migue sigue pendiente; no se afirma su conformidad. Esta sesión cierra el diseño y comprueba su viabilidad documental. No implementa estimadores, entrena modelos, genera resultados T09, modifica T03 ni publica cambios. La tarea T09 todavía no está terminada.

## 1. Problema que resuelve

Disponemos de 138 rendimientos de grano de la campaña 2025 y 59 parcelas reservadas sin rendimiento conocido. El municipio ya predice parte de las diferencias observadas. Necesitamos determinar si lluvia y temperatura aportan información útil adicional, con una evaluación que represente a esas 59 parcelas y que también revele dependencia espacial.

La pregunta principal es **si el procedimiento municipio + clima mejora sobre la referencia territorial exacta de T08**. Preguntas secundarias: cuánto predice el clima sin municipio, si una corrección de los errores de la referencia funciona y qué ocurre al evaluar celdas o municipios no vistos.

El diseño debe poder aplicarse a entradas de otra campaña compatibles con su contrato. Tener un diseño reutilizable y obtener un buen resultado en 2025 no demuestra precisión en años futuros: actualmente no hay rendimientos etiquetados de otras campañas.

## 2. Solución y decisiones cerradas

| Decisión | Contrato v1.0 |
|---|---|
| Unidad supervisada | Una parcela de 2025; 138 etiquetas para desarrollo, 59 ausentes para aplicabilidad |
| Territorio | Municipio categórico literal de T02; grupo de registro sólo en respaldo/auditoría |
| Clima | Lluvia acumulada, Tmin media y Tmax media de una sola ventana en cada ajuste |
| Ventanas | `abr_oct` y `jun_oct`, preparadas por T07; selección dentro del entrenamiento |
| Familia | Regresión lineal con penalización L2 sobre coeficientes climáticos |
| Procedimientos | T: referencia exacta; CL: clima solo; TC: municipio + clima; R: referencia + corrección residual |
| Búsqueda | 2 ventanas × 4 intensidades de regularización por procedimiento climático |
| Intensidades | λ = 0.01, 0.1, 1, 10; `alpha = n_entrenamiento × lambda` |
| Escalado | Media y desviación poblacional aprendidas sólo con cada entrenamiento, por ventana |
| Selección | MAE del rendimiento completo; población con soporte municipal en A/B |
| Evaluación | A principal, B sensibilidad obligatoria, C transferencia territorial sólo para informe |
| Reglas de promoción | T03/D019 vigentes; no escoger la métrica según el resultado |
| Elección final | T16; T09 aporta evidencia y candidatos, no declara por adelantado un ganador |

Se conserva la referencia exacta como candidato efectivo. Una penalización muy grande es una aproximación, no un sustituto de incluir T.

La propuesta 0.1 del 10 de octubre se conserva como antecedente privado. Su estado de T07, su cuadrícula de α y sus decisiones pendientes ya no describen esta versión. Las diferencias aparecen en §16.

## 3. Base común y avances del equipo revisados

Base consultada: `origin/dev` = `cb4580701b2bf28588e56ce3d73e64fbf2b6a738`; rama local `t09-diagnostico-atributos`, código previo `38401327c12a9ac9c2366338eaae00a40114e1bb`. T07 completo y fichas están integrados mediante PR14 y PR16. El manifiesto de T07 conserva su declaración histórica de cierre; la aceptación posterior se acredita por el merge identificado, sin reescribir el historial para simular una aprobación anterior.

| Frente | Evidencia consultada | Consecuencia para T09 |
|---|---|---|
| Jass · T02/T05 | Catálogo, soporte espacial, calidad, precisiones y bitácora; PR12 integrado | IDs/unidades y desgloses comunes. No incorporar relieve ni eliminar casos difíciles en este contraste |
| Migue · T03/T08 | Protocolo/D019, código y predicciones de referencia integradas | Reproducir T; conservar particiones externas, respaldos y poblaciones de decisión |
| Dani · T04/T07 | Clima por parcela, agregación por días, controles, fichas y procedencia | Utilizar el bloque publicado; no recalcular desde QGIS ni usar las 59 para ajustar |
| Daf · T06/T11 | T06 integrado; PR15 actualizado a `bfa525d003c535349ff586ebea4a51e2487a513e`, aún abierto | La revisión de código muestra que T11 v2 rehace residuos en cada entrenamiento interno. Adoptar ese control; esta lectura no equivale a reproducir ni aprobar todo el PR |
| Migue · T14 | PR13 `9dffe7639c96ded4780e1f8911b4c7fcead6ca6d`, abierto | Sus etapas abr–jun/jul–oct y promedio simple no son las ventanas T07. No reutilizar sus puntuaciones como resultados T09 ni comparar importancia sólo con Pearson |
| Diego · T12/app | Alcance previsto en el plan vigente; no resultado nuevo comprobado aquí | Otros algoritmos pertenecen al contraste no lineal; preparar una salida explicable y trazable |

T09 depende del clima T04/T07, T02/T03 y T08. No espera la aprobación de T11/T14 para redactar su diseño. No se adoptan automáticamente sus listas de parámetros o sus conclusiones.

El preflight de ejecución comprobará las huellas y roles completos T07/fichas, las identidades T02/T04 y las particiones/referencia T08. El raw canónico ya pasó el comprobador común: 166 archivos exactos y cero adicionales. `DataSet.zip` conserva SHA-256 `d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5`. QGIS utiliza su copia en `data/processed/qgis/`; no es una fuente alternativa de cálculo.

Se detectó una contradicción textual en la tabla de soporte T03 §1: llama a AGC_120 un caso con respaldo, aunque tiene una etiqueta municipal y T08 la predice con fuente municipal. T09 distingue soporte escaso de municipio ausente: las 59 salidas de T08 tienen fuente municipal. La resolución operativa y la corrección textual propuesta al revisor están en `t09_decisiones.md`; no se cambian fórmulas ni el archivo T03 en esta sesión.

## 4. Organizaciones, guías y evidencia previa

Se revisaron las pestañas vigentes del documento del equipo, la guía conceptual del 24 de septiembre, el expediente estratégico, el diseño 0.1, el análisis del mentor/organizadores y los diagnósticos históricos. Las exploraciones de septiembre/octubre y resultados de otros frentes ya fueron vistos: este diseño precede a la ejecución de T09, pero **no es una planificación ciega a las etiquetas del proyecto**. Nuevas particiones no borran ese antecedente.

El documento oficial de la segunda sesión de FIRA, 9 de octubre, confirma temporal (P1), ausencia de fecha exacta de siembra parcelaria y referencia general de principios de mayo (P2), rendimiento de grano en t/ha (P6), salida puntual con cuatro decimales (P7), asociación de etiqueta a parcela (P8), muestreo estratificado (P9), ausencia de historial de rotación (P10) y variedades sin identificación parcelaria (P14). No inventamos siembra, variedad, dosis o siniestros a partir de recomendaciones regionales.

La transcripción de Dani recoge que el reto estima una cosecha ya ocurrida, admite datos públicos y permite que el equipo elija la métrica. Se distingue ese registro oral de las respuestas escritas. MAE permanece como criterio vigente de T03: la transcripción no obliga a cambiarlo a RMSE ni R². Una nueva instrucción oficial incompatible se registra y versiona antes de otra evaluación.

Mann–Whitney y KS de área se reprodujeron ahora sobre T07, 138 frente a 59: U = 3984.5, p = 0.814490965750831 (bilateral, aproximación asintótica, corrección de empates y continuidad); KS D = 0.139400638663719, p = 0.35592922053260273 (bilateral, método automático). La cifra 0.81 tiene una explicación verificable como Mann–Whitney; no se sustituye por KS. Sus p-valores son auditorías nominales sujetas a dependencia espacial y no demuestran igualdad, disponibilidad temporal o generalización. No se usan para elegir atributos. No se editó Tab 8 en esta sesión; su aclaración posterior debe conservar este origen.

## 5. Entradas y agregación

Archivo modelable: `registro/t07/tabla_comun.csv`. Se permite sólo el municipio y estas columnas, según ventana:

| Ventana | Lluvia | Tmin | Tmax |
|---|---|---|---|
| `abr_oct` | `prec_acumulada_mm_abr_oct` | `tmin_media_c_abr_oct` | `tmax_media_c_abr_oct` |
| `jun_oct` | `prec_acumulada_mm_jun_oct` | `tmin_media_c_jun_oct` | `tmax_media_c_jun_oct` |

Abril–octubre incluye siete meses y 214 días; junio–octubre, cinco meses y 153 días de 2025. Lluvia: suma de medias espaciales mensuales ponderadas por intersección física. Temperatura: suma de media mensual × días del mes, dividida por días de la ventana. Se hereda el cálculo verificado T07; no se promedian meses como si todos tuvieran igual duración.

Las dos ventanas se consideran calendarios candidatos. Abril puede representar condiciones previas al establecimiento; junio puede omitir parte del inicio. Sin fechas parcelarias no sabemos qué representa exactamente cada una para cada cultivo. La información FIRA de mayo no justifica borrar abril, elegir junio globalmente ni inventar una ventana mayo–octubre después de observar los resultados. Tampoco equivale a disponer de etapas de floración/llenado identificadas.

Tmin/Tmax son medias de los resúmenes mensuales: no cuentan heladas, días de calor extremo ni grados-día. Los meses 2022–2024 no se convierten en rendimientos nuevos, ni prueban cultivo continuo de cebada. Los registros de noviembre/diciembre quedan fuera de este diseño.

No entran al vector predictor ID, año constante, conjunto, superficie, coordenadas, celda de evaluación, estado, calidad de contorno, escalón de etiqueta, rendimiento de vecinas, huellas ni columnas satelitales. Área y relieve corresponden a T10; satélite a T11; combinaciones a T15. El grupo `Cebada/CEBADA` se conserva como procedencia y respaldo T08, sin interpretación de variedad o manejo.

## 6. Procedimientos exactos

Sea Z el clima estandarizado utilizando exclusivamente el entrenamiento del ajuste. Cada fila tiene el mismo peso; no se pondera por hectáreas. Sólo se penalizan los coeficientes climáticos β.

### T · referencia territorial

`media_mun__resp_grupo`, exactamente T08: media del municipio del entrenamiento; si no existe, media del grupo de registro; si tampoco existe, media global. No tiene ventana ni parámetro climático. Tiene una sola configuración efectiva. Sus OOF A/B deben coincidir con los archivos publicados, incluidos `fuente`, real e identidad.

### CL · clima solo

Minimizar `media((y − b − Zβ)²) + λ Σβ²`, con intercepto global b sin penalizar. Se utilizará Ridge/SVD con `fit_intercept=True` y `alpha=nλ`. No recibe municipio, grupo, coordenadas o celda para predecir. Esos metadatos pueden organizar particiones y reportes; no se usan para modificar el valor numérico. `fuente=global`.

### TC · municipio y clima, ajustados conjuntamente

Minimizar `media((y − b_municipio − Zβ)²) + λ Σβ²`. Los interceptos municipales no se penalizan. Implementación prevista: medias municipales de Z e y del entrenamiento; centrar ambas dentro del municipio; resolver β con SVD sin intercepto; reconstruir `b_m = media_m(y) − media_m(Z)β`.

No estandarizar de nuevo las desviaciones dentro de municipio: hacerlo cambiaría la penalización y podría amplificar fluctuaciones pequeñas de variables casi territoriales. No penalizar una matriz one-hot municipal con Ridge convencional. Un vector de α de Ridge no asigna penalizaciones por columna.

Municipio no visto: `b_respaldo = media_grupo(y − Zβ)` del entrenamiento; si falta grupo, media global de ese residuo. Después sumar `Z_nueva β`. Con β=0 se recupera exactamente T y su respaldo. Si el clima es constante por municipio en entrenamiento, TC no puede identificar un aporte interno; debe reducirse a T para casos con municipio observado. Eso no autoriza afirmar equivalencia de extrapolación fuera de esos municipios.

### R · corrección climática de la referencia

Experimento complementario previsto desde esta versión; no se añade después de ver que TC pierda. Cada entrenamiento produce `residuo_i = y_i − T(entrenamiento sin i, fila i)`. La propia etiqueta nunca forma parte de su referencia. Los respaldos del LOO también se calculan sin esa fila.

Ajustar `media((residuo − Zβ)²) + λ Σβ²`, sin intercepto adicional (`fit_intercept=False`). Para predecir: referencia T calculada sólo con el entrenamiento + `Z_nueva β`. Así no aparece un desplazamiento global de corrección que sobreviva cuando se contraen los coeficientes. La referencia exacta T sigue presente: λ=10 no garantiza β=0.

Se usa escalado global del entrenamiento, igual que CL/TC; no se añade un segundo centrado territorial a R. R y TC son procedimientos distintos. El factor n/(n−1) de los residuos LOO dentro de municipios pequeños y los respaldos impiden tratarlos como dos implementaciones equivalentes.

Durante la selección interna de R, rehacer el LOO **sólo con el entrenamiento interno**. Para puntuar su validación, sumar la referencia de ese entrenamiento a la corrección y comparar con el rendimiento real. No puntuar un residuo de validación construido con su propia etiqueta ni cortar un vector de residuos calculado con todo el entrenamiento externo.

## 7. Parámetros, presupuesto y desempates

Se fijan cuatro λ logarítmicos: 0.01, 0.1, 1, 10. La normalización por n mantiene la misma relación entre pérdida media y penalización cuando cambia el tamaño de entrenamiento. Es una decisión de diseño derivada del objetivo de Ridge, no una garantía de que esa cuadrícula contenga el óptimo.

Ejemplo: con n=100, los α efectivos son 1, 10, 100 y 1000; con n=50, 0.5, 5, 50 y 500. Se registra λ y α efectivo en cada ajuste interno/externo/final. n cuenta todas las filas de entrenamiento, no sólo las elegibles para puntuar, ni grados de libertad del municipio.

| Experimento preregistrado localmente | Procedimiento | Configuraciones distintas |
|---|---|---:|
| `T09_TC_v1` · principal | TC frente a T | 8 = 2 ventanas × 4 λ |
| `T09_CL_v1` · diagnóstico | CL y contrastes TC/CL | 8 |
| `T09_R_v1` · residual | R frente a T/TC | 8 |
| Referencia | T exacta, compartida | 1; sin búsqueda |

Hay **24 configuraciones climáticas en tres experimentos explícitos**, no ocho en todo T09. T03 §5 permite registrar una búsqueda mayor como otro experimento. No se combina su menú en una búsqueda única de 24 para decir que sólo se probaron ocho. Ventanas, subconjuntos, λ y arquitectura consumen búsqueda; aquí no se añaden Huber, interacciones, filtros Pearson, PCA, ponderaciones ni conjuntos climáticos reducidos. T14 conserva su pregunta por variables.

Dentro de cada entrenamiento, concatenar los errores absolutos elegibles de las cuatro validaciones internas. Elegir el menor MAE; empate después de redondear a seis decimales: λ mayor y después `jun_oct`. El último desempate prioriza requerir cinco meses en vez de siete cuando el criterio interno no distingue; no afirma que junio sea mejor agronómicamente. Guardar los valores completos antes del redondeo y todas las opciones, también las perdedoras.

CL, TC y R pueden seleccionar ventanas diferentes. La comparación principal mide sus procedimientos de selección completos. Para interpretar el bloque climático, añadir contrastes secundarios **con ventana fija**: elegir internamente λ para cada ventana y reportar TC frente a T y TC frente a CL en ambas. Reutilizan las mismas ocho configuraciones y particiones; sólo requieren los reajustes de cada ventana. No usar luego el mejor resultado externo de esas ventanas para decidir cuál publicar como ganador.

Si suele ganar un extremo de la cuadrícula, se informa la limitación. Ampliarla exige otra versión y otro registro; se declara la reutilización de datos. No se abre la búsqueda hasta conseguir que el clima gane.

## 8. Separación externa e interna

Las particiones externas T03 por ID son inmutables: A tiene 25 entrenamientos (5×5), B otros 25; C deja fuera cada uno de nueve municipios. El ajuste para las 59 añade un contexto, sólo después de completar y revisar la evaluación.

| Escenario | Uso | Selección interna fijada en T09 v1 |
|---|---|---|
| A | Parcela nueva en municipio conocido; principal | 4 `StratifiedKFold`, semilla 0; municipio con ≥4 etiquetas, los demás `otros` |
| B | Evaluación de celdas no vistas; sensibilidad | 4 `GroupKFold(shuffle=False)` por celda CHIRPS del centroide; ninguna celda compartida internamente |
| C | Municipio no visto; sólo informe | 4 `GroupKFold(shuffle=False)` por municipio; ningún municipio compartido internamente |
| Ajuste final para 59 | Municipios conocidos actuales | Política interna de A sobre las 138 etiquetas |

Ordenar por ID antes de partir; congelar biblioteca 1.9.1 y listas de IDs. GroupKFold equilibra aproximadamente tamaños, no garantiza igualdad ni representatividad municipal. Ni sus grupos ni las semillas se eligen con rendimientos.

**Extensión explícita a T03 §5:** ese protocolo prescribe cuatro particiones internas estratificadas por municipio; T09 mantiene esa política en A y registra agrupación interna en B/C para corresponder al uso evaluado. No se afirma cumplimiento literal de esa frase en B/C ni se cambia silenciosamente el protocolo común. Dani autoriza fijar esta extensión en el diseño; Migue debe conocerla al revisar. Es una política de selección predefinida por escenario, no una alternativa que se elija por métricas. B evalúa la política para celdas nuevas, no el mismo ajuste numérico de A transferido sin cambiar parámetros. No demuestra transferencia temporal.

Las comparaciones con T08 siguen válidas porque T es determinista, no tiene selección climática y se evalúa en los mismos IDs. Resultados T11/T14 con otra política interna no se describirán como experimentos idénticos: en T15 deberá unificarse la política para atribuir diferencias sólo a bloques, o conservar esa diferencia metodológica explícita.

En A/B, puntuar internamente sólo filas cuyo municipio tiene etiquetas en su entrenamiento interno, con una máscara común a los tres candidatos climáticos. Entrenar siempre con **todas** las filas del entrenamiento, incluidos municipios pequeños. Registrar también MAE de todas, activaciones y casos elegibles. En C, no existe soporte municipal en validación interna por construcción: puntuar todas y marcar `sin_respaldo` como no aplicable. No escribir error cero para una población vacía.

Verificación realizada sin estimadores: 60 contextos, 240 particiones internas; todas completas y disjuntas, sin grupos compartidos en B/C, cero advertencias. A tiene 26–28 casos elegibles por validación interna, B 5–34, C 10–71 (todas), ajuste final A 33–35. La partición B con sólo cinco elegibles es una limitación: concatenar errores evita ponderarla como un cuarto del criterio; no la elimina ni permite inventar otro reparto.

## 9. Secuencia que seguirá cada ajuste

1. Reservar la evaluación externa y verificar sus IDs; sus etiquetas sólo se leerán al medir el resultado.
2. Construir las cuatro separaciones internas correspondientes al escenario únicamente sobre su entrenamiento externo.
3. Para cada ventana/λ, ajustar escalado y procedimiento con cada entrenamiento interno. Para R, rehacer también referencia LOO y residuos allí.
4. Puntuar rendimiento completo de validación con las máscaras ya fijadas, sin transformar el criterio según el candidato.
5. Elegir configuración por el desempate §7; guardar las ocho puntuaciones y las ganadoras por ventana.
6. Reajustar ganadora(s) con todo el entrenamiento externo. Predecir y evaluar una vez sus parcelas externas. No reutilizar su resultado para cambiar las ocho opciones.
7. Repetir A/B y C con las políticas declaradas. Una segunda ejecución reproduce el mismo diseño, no constituye nuevos datos.

Una etiqueta de validación interna puede cambiar la puntuación y qué opción gana: ése es su cometido. No puede cambiar escalas, residuos, referencia o coeficientes de una opción entrenada sólo con la otra parte. Alterar etiquetas externas no debe cambiar ninguna selección interna ni predicción externa. Distinguir estos dos controles evita escribir una prueba que prohíba la selección legítima.

## 10. Métricas, fuentes y decisión

Error firmado = predicción − real. MAE primaria; RMSE, sesgo y R² global secundarias. Evaluar cada repetición completa y después media/desviación de cinco repeticiones; no promediar 25 particiones como independientes. R² es no definido con menos de dos casos o respuesta constante (`force_finite=False` y estado explícito); no utilizar ceros ficticios.

`fuente` describe el origen del intercepto/referencia: T/TC/R usan municipio/grupo/global; CL usa global. La máscara externa `municipio_con_soporte` procede de la referencia T08, no de la fuente de CL. Es la misma para todos: 675 predicciones A, 659 B. Las poblaciones `todas` tienen 690 por escenario. C no tiene `sin_respaldo` y no decide para las 59.

Comparación principal: TC contra T. Secundarias predefinidas: CL contra T; TC contra CL; R contra T y TC; contrastes de ventana fija. Informar todas, favorables o desfavorables. Los intervalos de comparaciones secundarias son nominales; ver varios intervalos y escoger uno favorable no demuestra una confirmación independiente. La selección final de frentes en T16 tiene más incertidumbre que un único contraste.

Aplicar exactamente T03/D019:

- Para cada parcela, promediar diferencias de error absoluto en las repeticiones elegibles. `ΔMAE_regla` es el promedio de esos promedios por parcela. Guardar cuántas repeticiones contribuyen: en B puede no equivaler exactamente a promediar diferencias de MAE por repetición con tamaños variables.
- Bootstrap de celda CHIRPS del centroide: 5000 réplicas, semilla 20261006, percentiles 2.5/97.5. Remuestrear celdas y sumar pérdidas/conteos de sus parcelas; intervalo por parcela sólo como referencia. Recalcular contra T08 para validar la implementación.
- Promover frente a referencia: ΔMAE ≤ −0.01 t/ha; límite superior IC95_celdas < 0; mejora en ≥4 de 5 repeticiones; empeoramiento medio RMSE ≤0.01 t/ha, en `sin_respaldo` de A.
- Si nada cumple, conservar T. Si varios cumplen, seguir el desempate de MAE B de T03; no sustituirlo por R² o el mejor municipio. Para empate numérico, preferir menos pasos/entradas: T, CL, TC, R, con justificación de respaldo/aplicabilidad.

R/CL se entregan como candidatos secundarios predefinidos para T15/T16, sin reinterpretar una derrota de TC como victoria de la hipótesis principal. T09 no determina por sí sola el modelo final del proyecto. La regla de 0.01 es un criterio del equipo, no una tolerancia de error que FIRA o un productor hayan confirmado.

El bootstrap respeta la dependencia dentro de celda, no toda la de celdas vecinas; hay pocos bloques y dos muy grandes. No es intervalo de predicción parcelario. Cinco repeticiones siguen reutilizando las mismas 138 etiquetas. Informar magnitud, estabilidad y alcance, no certeza absoluta de mejora.

## 11. Calidad y explicaciones

Mantener las 138 parcelas en el ajuste principal. ID incorrecto/duplicado, unidad/campaña incompatible, clima faltante/no finito, referencia o huella incompatibles detienen la ejecución. No rellenar clima con cero, imputar rendimiento o retirar extremos. Las dos pendientes de relieve no afectan las tres entradas climáticas; no exigen excluir esas parcelas de T09.

Desgloses obligatorios T03: municipio, grupo, contorno A frente a B/C, angosta/muy pequeña, escalón de etiqueta y vecina etiquetada a menos de 20 m. Contar parcelas únicas, predicciones y casos con n<5. La sensibilidad sin las 24 alertas **recalcula métricas sobre las mismas predicciones**, sin volver a entrenar ni escoger parámetros sobre ese subconjunto. No altera la promoción principal.

Informar variación climática entre/dentro del municipio, columnas constantes, coeficientes estandarizados por ajuste, frecuencias λ/ventana y perfiles climáticos distintos. El diagnóstico previo encuentra 43 perfiles entre etiquetadas y 53 en total usando las seis columnas; son perfiles de entradas, no tamaño muestral independiente certificado. No convertir número de filas o correlaciones en evidencia de exposición independiente.

Los coeficientes no miden efectos causales. Un aumento de Tmin en la app no permite recomendar una intervención que garantice subir rendimiento. Para TC/R se podrá mostrar referencia, corrección total y aportes lineales de la ventana elegida, indicando su carácter descriptivo y la dependencia entre entradas. Para CL, intercepto global y aportes. No presentar un único coeficiente como respuesta al bonus de importancia T14.

## 12. Tiempo y futuras campañas

La salida principal se rotula **estimación retrospectiva de rendimiento de grano 2025 con observaciones hasta 31-oct-2025**. El corte observacional no acredita que todos los productos estuvieran publicados ese día. T04 conserva versiones/ediciones y disponibilidad histórica del paquete no confirmadas. La latencia diaria CHIRTS-ERA5 no certifica nuestros mensuales; la publicación final CHIRPS posterior al mes tampoco certifica la edición FIRA.

Para otra campaña se requerirá el mismo cálculo espacial, unidades, ventanas, geometrías/municipios compatibles, trazabilidad de producto y evidencia de publicación a la fecha de consulta. Las etiquetas futuras deberán validar y, cuando proceda, actualizar tanto interceptos municipales como relación climática. Interceptos de 2025 pueden volverse obsoletos aunque el municipio sea conocido.

No simular validación entre años con 2022–2024 de clima sin rendimientos. Antes de llamar pronóstico a una salida temprana, fijar fecha de decisión y construir ventanas con productos realmente disponibles, con otra versión y evaluación. No ampliar ahora a agosto/septiembre para elegir el corte de menor error retrospectivo.

Para las 59 y entradas futuras, entregar alertas sobre faltantes, municipio no visto/escaso soporte, variable fuera de rango y combinación climática sin vecinos de entrenamiento próximos. Guardar conteos/rangos; estar dentro de cada rango no demuestra soporte conjunto. Los umbrales de una distancia, si se añadieran, deben aprenderse con entrenamiento y validarse; esta versión no convierte distancias en probabilidades o confianza calibrada.

No recortar predicciones negativas/extremas para mejorar métricas; conservar y señalar. La app informa un valor puntual, calidad de entradas y error histórico pertinente, sin prometer un intervalo individual no validado. El archivo compatible con FIRA utiliza cuatro decimales; los cálculos/OOF guardan precisión completa. Cuatro decimales son formato, no precisión científica demostrada. No convertir automáticamente t/ha en producción total sin conocer la superficie usada en el denominador del rendimiento.

## 13. Innovación y recursos externos con propósito

La innovación de este diseño consiste en separar señal territorial y aporte adicional, probar una corrección residual bien controlada, comparar ventanas de forma honesta y medir soporte/estabilidad. Ninguna se anuncia como mejora predictiva antes de evaluarla.

| Recurso | Uso ahora | Condición para incorporarlo al modelo |
|---|---|---|
| Guías INIFAP/AHDB | Hipótesis sobre calendario, agua y desarrollo; contexto, sin asignar manejo parcelario | Medición válida del atributo; no copiar calendario/recomendaciones como si fueran observaciones |
| SoilGrids | Candidato de suelo si clima/topografía dejan una carencia concreta | Un bloque pequeño, profundidad/unidades/versión/cobertura, contraste con igual presupuesto y sensibilidad B/C; 250 m no es laboratorio parcelario |
| Clima diario | Posible distribución de lluvia/eventos térmicos en otra versión | Producto adecuado, cobertura y disponibilidad; no reconstruir días de helada con medias mensuales |
| Historia 2022–2024 | Hipótesis de anomalías comparativas | Otra versión registrada; tres años no son una normal climatológica ni etiquetas nuevas |
| Agrocostos FIRA | Contexto económico de la app por región, ciclo y tecnología | Costos/precios como escenarios explícitos; no inferir dosis o gasto real de cada parcela ni introducir un rendimiento supuesto como predictor |
| NAX | Aclarar metodología de índices, nubes, bordes y acceso con el proveedor confirmado | El documento institucional FIRA menciona NAX; no confirma proveedor de cada archivo del reto, permiso de reutilización ni servicio gratuito |
| Redes/árboles/DBSCAN | Conservar oportunidades del mentor en sus tareas | Otro algoritmo en T12, presupuesto explícito. DBSCAN no sustituye regresión t/ha ni autoriza excluir ruido |

El hito para reconsiderar un bloque externo es después de la primera evaluación completa T09/T08 y antes de congelar T16. Cada extensión debe registrar carencia → hipótesis → fuente/unidad/versión/publicación → acceso/coste → cobertura 197 → comparación con/sin bloque → criterio de aceptación. No esperar ese hito para utilizar las guías como contexto: ya se utilizaron.

La Agenda de Hidalgo 2017 figura en las guías previas; su PDF institucional no abrió en la consulta actual. No se atribuye una nueva lectura íntegra ni recomendaciones actuales. AHDB aporta fisiología; sus calendarios británicos no se trasladan a México. La mejora ambiental/financiera del agricultor no se deduce de una métrica del modelo: requiere validar utilidad con el usuario de la app.

## 14. Implementación, pruebas y entregables posteriores

La próxima fase abrirá `t09-territorio-clima` desde el dev identificado entonces e incorporará explícitamente este diseño/diagnóstico, preservando ramas de otras tareas. No utilizar `daniela-dev` ni copiar código abierto de T11/T14 sin revisión. Antes de ejecutar, comprobar si cambió dev/configuración Docker y registrar el commit real. La configuración común Jass `87467c7d9833474ff19753d87390efe88cbea82e` se utilizó para verificar el diagnóstico; su lectura no equivale a integrar esa rama.

Ejecutar el futuro cálculo canónico en Docker común `linux/amd64`, bibliotecas fijadas, SVD y un proceso/hilo de cálculo. En Mac de 8 GB, evitar paralelizar búsquedas. Las comprobaciones de portabilidad ARM usarán tolerancias declaradas y registrarán arquitectura/BLAS; no se confunde equivalencia numérica con igualdad binaria universal. Docker sólo se inicia cuando haga falta y se detiene al terminar.

Se podrán reutilizar matrices escaladas dentro de un mismo entrenamiento interno/ventana y referencias dentro de ese mismo contexto; nunca escalas/residuos entre particiones. Se necesitan, como máximo, 60×3×(8×4+2) = **6120 ajustes climáticos** para las políticas completas, ventanas fijas y ajuste final de candidatos; son matrices de tres entradas. Es una cuenta planificada, no una medición de tiempo/RAM. Si una ganadora se reutiliza, no se reajusta otra vez ni se contabiliza una predicción como ajuste nuevo.

Pruebas esenciales antes de entrenar:

| Control | Resultado exigido |
|---|---|
| Contrato/datos | 197 IDs únicos, 138 rendimientos intactos/59 ausentes; huellas/roles/unidades correctos; cero pérdidas |
| T exacta | OOF A/B y respaldo iguales a T08; máscara 675/659 común a todos |
| TC independiente | Coincide con matriz completa y penalización sólo climática; tolerancia absoluta 1e-9 t/ha |
| Referencia LOO | Coincide con excluir fila explícitamente, tolerancia 1e-10 |
| Separación | IDs/grupos disjuntos según escenario; ningún reservado en selección/evaluación |
| Fuga externa/interna | Etiquetas externas no cambian ajuste; una validación interna no cambia una opción entrenada sin ella |
| Clima solo | Metadatos municipales no cambian predicción de CL ya ajustado |
| Penalización | α=nλ por entrenamiento; referencia presente; cero intercepto de corrección R |
| Clima constante | TC recupera T en municipios observados si no hay variación interna identificable |
| Evaluación | Métricas/errores/intervalos reproducidos independientemente; R² indefinido explícito |
| Robustez | Faltantes/IDs/unidades incompatibles bloquean, no se convierten en ceros o filas descartadas |
| Reproducción | Dos ejecuciones canónicas con salidas/selecciones idénticas; portabilidad rtol=1e-10/atol=1e-12 documentada, sin ampliar tolerancia para ocultar fallos |

Controles sobre copias pequeñas no fabrican rendimientos para evaluar AgroCebada. Las ejecuciones oficiales usan exclusivamente los datos reales. Un candidato que no mejora es un resultado válido; una falla computacional se investiga antes de emitir resultados.

Entregables futuros compactos en `registro/t09/`: manifiesto de ejecución, configuración, OOF A/B, C separado, ajustes únicos, puntuaciones internas, métricas por repetición/población, contrastes emparejados, desgloses, sensibilidad sin24, ventana fija, soporte y salidas de candidatos para59. Detalle voluminoso en `data/processed/t09/`; evidencia en `reports/`, según estructura existente. No subir raw/QGIS/privados.

OOF conserva las nueve columnas T03: `ID_POLIGONO,repeticion,particion,escenario,real,prediccion,candidato,version,fuente`. Ventana/λ/α/máscara van en auxiliares con claves explícitas. Las cuatro salidas principales contienen 5520 filas A+B (138×5×2×4) y 552 en C (138×4). No son 6072 ejemplos nuevos independientes. Salidas de candidatos59, cuando corresponda, no sustituyen el modelo congelado y entrega T18.

## 15. Fases siguientes y revisión

| Fase | Trabajo | Condición de salida |
|---|---|---|
| 0 · Diseño | Documento/configuración/registros y viabilidad | Completada localmente en esta sesión; revisión de Migue pendiente |
| 1 · Preflight | Rama de implementación, base común y entrada identificada | Todos los contratos/huellas correctos |
| 2 · Estimadores | T, CL, TC, R y controles de fuga/solución independiente | Pruebas esenciales aprobadas, sin resultados oficiales todavía |
| 3 · Evaluación | Búsqueda interna, A/B, C y reportes fijos | Población/presupuesto íntegros; ningún resultado descartado |
| 4 · Reproducción | Segunda ejecución, contraste numérico, aplicabilidad59 | Evidencia independiente y diferencias explicadas |
| 5 · Entrega | Interpretación, PR hacia dev y revisión esencial | Publicación autorizada, revisión humana; T09 no es T16/T18 |

Migue revisará métodos, extensión interna B/C, población/criterio y presupuesto. No se espera su respuesta para fijar esta propuesta autorizada; tampoco se registra que la aprobó. Jass conserva catálogo/calidad; Daf recibe ventanas/OOF legibles para T11/T15; Diego recibe alcance de la salida para la app. No se enviaron mensajes a ninguno.

Una revisión puede modificar v1 antes del entrenamiento; después de resultados requiere nueva versión con antecedente explícito. Ni el código ni la ausencia de respuesta deciden por omisión. Los próximos commits separarán validadores, estimadores, residual, evaluación y entrega. Antes de cada push se presentará su lote para autorización.

## 16. Cambios frente al borrador y problemas resueltos

| Problema/decisión pendiente | Resolución v1.0 | Alcance |
|---|---|---|
| Migue sin respuesta | Dani autoriza cerrar diseño; revisión pendiente documentada | No se inventa aprobación del revisor |
| T07 aparecía pendiente en borrador | Base dev con PR14/16 integrados identificada | No se vuelve a esperar datos ya aceptados |
| Presupuesto podía confundirse con ocho totales | Tres registros prospectivos de ocho, 24 totales | No expansión silenciosa después de resultados |
| Intercepto residual no se apaga con α grande | R sin intercepto adicional y T exacta siempre presente | Diferente de R propuesto con intercepto en v0.1/T11; no se afirma equivalencia |
| α fijo significa contracción distinta según n | λ normalizada con α=nλ y cuadrícula fija | Decisión matemática, no un óptimo comprobado |
| Ventanas distintas complican atribuir el bloque | Contraste principal de procedimientos + diagnósticos de ventana fija | No seleccionar ventana por error externo |
| B/C internos no respetaban grupos de uso | Extensión de cuatro particiones agrupadas; 240 particiones viables | No cambio a externos T03; diferencia frente a T11/T14 registrada |
| Fuente global de CL podía vaciar su máscara | Soporte municipal común tomado de T08 | Conserva poblaciones comparables |
| Residuos externos podrían contaminar internos | LOO nuevo por entrenamiento interno; puntuar rendimiento completo | T11 v2 ya contiene esa corrección en código revisado |
| 0.81 atribuido a KS sin origen | Mann–Whitney 0.814491 y KS 0.355929 reproducidos | Corrige explicación; no demuestra equivalencia |
| Guías/futuro podían convertirse en atributos ficticios | Fuente/observación/disponibilidad separadas y hito de extensión | Temporal confirmado; fecha/variedad individual no inventadas |

## 17. Fuentes y trazabilidad

Consultadas el 11/10/2026 salvo antecedente explícito. `t09_decisiones.md` amplía la matriz de evidencia y límites.

- [Plan unificado y anexo de selección del equipo](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk); tabs `t.q0k09ka9rtmy`, `t.54o9r0m39lsv`, `t.xgecwo5w1w3m`, `t.1k0611huk4yx`, revisión `AHj4eMR0sjbrunizHISe3ww4c2SxEhduCUf3UaXsXzJMUC6O4CbQz9WHFmUalxWPQ-r2IAjdYCDyBCCWvqtQqasnZyrnKFE_DGIPFg_w9vk`.
- Fuentes locales: T03/T08/T04/T07 y fichas, diagnósticos de Dani; preguntas escritas FIRA y transcripción recibidas; guías históricas. Se preservan sus identidades en evidencia local.
- [Ridge, documentación oficial](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html); objetivo y SVD. La normalización λ, interceptos municipales y decisiones de este diseño son adaptaciones propias.
- [Validación cruzada](https://scikit-learn.org/stable/modules/cross_validation.html), [GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html), [validación anidada](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html), [prevención de fugas](https://scikit-learn.org/stable/common_pitfalls.html). Documentación primaria de las herramientas; no certifica el desempeño de AgroCebada.
- Roberts y colaboradores (2017), [Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure](https://doi.org/10.1111/ecog.02881). Fundamenta examinar separación y dependencia según el uso, sin convertir separación espacial en evidencia entre años.
- [FAQ CHIRPS2](https://wiki.chc.ucsb.edu/CHIRPS2_FAQ) y [CHIRTS-ERA5](https://www.chc.ucsb.edu/data/chirts-era5). Plazos generales y productos; no identifican la edición ni publicación histórica FIRA.
- [Guía de crecimiento de cebada AHDB](https://ahdb.org.uk/knowledge-library/barley-growth-guide). Contexto fisiológico. INIFAP Hidalgo2017 es antecedente de las guías; acceso actual fallido al PDF institucional, sin nueva lectura completa.
- [SoilGrids, ISRIC](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs.html), [Agrocostos FIRA](https://www.fira.gob.mx/Nd/Agrocostos.jsp), [Plataforma de asesoría técnica FIRA, Premio ALIDE2025](https://www.fira.gob.mx/Files/PremioALIDE2025.pdf). Oportunidades y límites, no entradas incorporadas.
- Kassis, T.; Agarwal, V.; He, Y.; Patel, D.; Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065), registro actual v2. Skills scikit-learn/pensamiento crítico usadas como apoyo procedural; no equivalen a revisión humana o evidencia de mejora.

**Cierre de esta sesión:** diseño/configuración/registros locales y viabilidad aprobada sin entrenamiento. Originales, T07, particiones y QGIS intactos; Google Doc no editado, sin push/PR/merge ni mensajes externos. Docker no se inició para esta redacción.
