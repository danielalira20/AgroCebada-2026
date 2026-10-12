# Bitácora de la evaluación de relieve y área (T10)

> **Nota para el equipo.** Bitácora de trabajo en orden cronológico: qué se hizo en cada paso, qué se esperaba, qué se encontró y qué se decidió. El método está en [`docs/T10_relieve_area.md`](../../docs/T10_relieve_area.md) y la decisión de diseño en `D_T10_001` (`registro/decisiones.csv`). Los resultados compartidos están en `registro/t10/`; esta carpeta guarda la evidencia que los explica.

**Pregunta que debe quedar contestada:** ¿conocer la elevación, la pendiente y el tamaño de una parcela mejora la estimación que da el promedio de su municipio, y esa mejora se sostiene en parcelas pequeñas o con cobertura parcial?

Responsable: Jass. Revisora: Daf.

**Estado al 12 de octubre de 2026:** evaluación completa corrida (pasos 6 y 7). Ninguna configuración cumple la regla de T03: relieve y área no aportan sobre la referencia territorial con este procedimiento. Diagnóstico exploratorio, informe de cierre y registros hechos (pasos 8 y 9). Reproducción comprobada en Linux y en Docker sobre Windows (paso 10). Queda la revisión de Daf.

## Qué hay (y qué habrá) en esta carpeta

| Archivo | Qué guarda | Estado |
|---|---|---|
| `bitacora.md` | Este documento. | Creado |
| `scripts/explorar_relacion_con_rendimiento.py` | Diagnóstico exploratorio con rendimientos (Pearson y Spearman, global, dentro de municipio y por municipio). No decide nada. | Creado (paso 8) |
| `tablas/correlaciones_con_rendimiento.csv` | Resultado de ese diagnóstico. | Creado (paso 8) |
| `figuras/dispersion_relieve_area_rendimiento.png` | Dispersión global y dentro de municipio de las tres variables. | Creado (paso 8) |
| `informe_relieve_y_area.md` | Informe de cierre en lenguaje sencillo, con preguntas y respuestas. | Creado (paso 9) |

Dónde vive el resto: método en `docs/T10_relieve_area.md`, código en `scripts/t10_relieve_area.py`, pruebas en `tests/test_t10_relieve_area.py`, resultados en `registro/t10/`. Regla: lo que el equipo ejecuta o consume va en las carpetas del equipo; lo que explica o justifica va aquí.

## Reglas de esta carpeta

- Los nombres dicen lo que contiene cada cosa: minúsculas, guion bajo, sin acentos, sin nombres de persona ni «paso N».
- El dataset original no se copia, no se mueve y no se modifica.
- Las carpetas se crean cuando se necesitan.
- Se distingue siempre lo **verificado** de la **sospecha**.

## Plan en pasos

| Paso | Qué se hace | Estado |
|---|---|---|
| 1 | Limpieza de la rama: integrar el entorno común (Docker) y fin de línea LF | **Hecho** (12 oct) |
| 2 | Actualizar documentos de T05 (bitácora y pendiente P05) | **Hecho** (12 oct) |
| 3 | Diseño escrito antes de correr: `docs/T10_relieve_area.md` y `D_T10_001` | **Hecho** (12 oct) |
| 4 | Código y pruebas sintéticas; comprobar que la referencia reproduce T08 | **Hecho** (12 oct) |
| 5 | Diagnóstico de atributos sin rendimientos | **Hecho** (12 oct) |
| 6 | Ejecución: 6 configuraciones × (principal y puente), escenarios A y B; regla de T03 | **Hecho** (12 oct) |
| 7 | Desgloses por tamaño, cobertura y contorno; sensibilidad sin las 24; revuelto si aplica; predicciones de las 59 | **Hecho** (12 oct) |
| 8 | Diagnóstico exploratorio con rendimientos (Pearson y gráficos) | **Hecho** (12 oct) |
| 9 | Informe de cierre y registros (`E_T10_001`–`006`, `IA_T10_001`) | **Hecho** (12 oct) |
| 10 | Reproducción (dos corridas idénticas, Docker) y borrador del PR para Daf | **Hecho** (12 oct) |

## Bitácora

### 12 de octubre de 2026 — Diseño escrito antes de correr (paso 3)

**Qué se esperaba.** Fijar la pregunta, las entradas, el procedimiento, las configuraciones y la regla de decisión antes de ver ningún resultado, para que el resultado no pueda cambiar el criterio.

**Qué se hizo.** `docs/T10_relieve_area.md` y la fila `D_T10_001`. Se declaró por escrito lo que ya se había visto de relieve y área con las 138 etiquetas durante la comprensión del dataset (pendiente +0.26 y log del área −0.25 dentro de municipio, permutación p = 0.22) y el hallazgo de T02 sobre tamaño en Chignahuapan.

**Decisiones.**
- Procedimiento principal = el de T11 v2 con dos cambios: opción «referencia sola» en la selección interna (O7) y α elegido por error absoluto (la métrica primaria de T03 es el MAE).
- Procedimiento puente = T11 v2 exacto, sólo descriptivo: nunca decide ni consume presupuesto (consulta enviada a Migue sobre esta lectura de T03 §5).
- 6 configuraciones de 8; las 2 restantes no se usan y no se agregan después de ver resultados.
- Control de revuelto (20, dentro de municipio) sólo si alguna configuración cumple la regla.

### 12 de octubre de 2026 — Código y pruebas (paso 4)

**Qué se esperaba.** Un script que haga exactamente lo de `D_T10_001` y pruebas que demuestren que nada de la evaluación se filtra al entrenamiento.

**Qué se hizo.** `scripts/t10_relieve_area.py` (modos `--comprobar-referencia`, `--diagnostico` y `--evaluar`; ninguno sobrescribe archivos) y 13 pruebas sintéticas en `tests/test_t10_relieve_area.py`.

**Qué se comprobó.**
- 13 de 13 pruebas nuevas y 266 de 266 en la suite completa.
- La referencia de T10 reproduce las 1,380 predicciones de T08 (diferencia máxima 8.9e-16) con las mismas fuentes de respaldo (15 en A, 31 en B).
- El puente elige el mismo α que el código real de T11 v2 en 100 de 100 casos (configuraciones 1 y 3, las 50 particiones). Para eso se corrió la selección de α con datos reales; sólo se compararon los α elegidos, no se calculó ni se miró ningún error.

**Qué no se comprobó.** Que el puente coincida con T11 v2 en las configuraciones con pendiente (2, 4, 5 y 6): el código de T11 no admite faltantes.

### 12 de octubre de 2026 — Diagnóstico de atributos sin rendimientos (paso 5)

**Qué se esperaba.** Saber, sin mirar rendimientos, cuánto de cada variable es «ubicación», cuánto se parecen entre sí y si las 59 reservadas caen dentro de lo que el modelo verá al entrenar.

**Qué se hizo.** `python -m scripts.t10_relieve_area --diagnostico --salida registro/t10`, que escribe `registro/t10/diagnostico_atributos_t10.csv`. Sólo usa municipio y las tres variables.

**Qué se encontró (comprobado, 138 etiquetadas).**

| Variable | Parte explicada por el municipio | Faltantes |
|---|---|---|
| Elevación | 28 % | 0 |
| Pendiente (D020) | 13 % | 2 (AGC_023 y AGC_170) |
| Log del área | 15 % | 0 |

- Correlaciones entre variables: elevación–pendiente 0.51; pendiente–log del área −0.30; elevación–log del área −0.09. Con las 197 parcelas el patrón es el mismo (0.45, −0.27 y −0.04).
- Las tres variables son en su mayor parte variación **dentro** de cada municipio, no un sustituto de la ubicación. Eso permite que puedan aportar algo sobre la referencia municipal; no demuestra que lo hagan.
- Elevación y pendiente comparten información (0.51): por eso la configuración 4 las junta y las configuraciones 1 y 2 las prueban por separado.

**Corrección al documento del método.** El documento decía que el municipio explica el 53 % del área. Ese valor es del área **sin** logaritmo; la entrada del modelo es el logaritmo, y para él la cifra es 15 %. La diferencia la causan unas pocas parcelas grandes concentradas en pocos municipios. Se corrigió `docs/T10_relieve_area.md` §3. No cambia el diseño: el logaritmo ya estaba decidido por la forma de la distribución, no por esta cifra.

**Reservadas fuera del rango etiquetado.** Tres, cada una en una sola variable y por muy poco: AGC_088 en elevación (2,906.0 m frente a un máximo de 2,904.0 m), AGC_153 en pendiente (0.282° frente a un mínimo de 0.288°) y AGC_091 en área (0.35 ha frente a un mínimo de 0.38 ha). No es una extrapolación relevante; se anota para el aviso de la app (T17). El documento del método decía que sólo había un caso (elevación); se corrigió.

**Qué no dice este diagnóstico.** Nada sobre si las variables ayudan a predecir: eso se mide en el paso 6, con la regla de T03.

### 12 de octubre de 2026 — Evaluación completa (pasos 6 y 7)

**Qué se esperaba.** Saber si alguna de las 6 configuraciones mejora la referencia `media_mun__resp_grupo` según la regla de T03 §4, en el subconjunto `sin_respaldo`, y cómo se comporta el error por tamaño, cobertura y contorno.

**Qué se hizo.** `python -m scripts.t10_relieve_area --evaluar --salida registro/t10` (25 segundos; Linux x86_64, Python 3.12.14). Se corrió primero en una carpeta temporal fuera del repositorio y después se copiaron los archivos a `registro/t10/`; el manifiesto coincide con los 10 archivos. Antes de evaluar, el script volvió a comprobar que la referencia reproduce las 1,380 predicciones de T08.

**Resultado principal (comprobado).** Ninguna configuración cumple la regla, en ningún escenario ni subconjunto. Por eso no se corrió el control de revuelto (`control_revuelto_t10.csv` queda sólo con el encabezado, como fija el diseño).

Referencia en `sin_respaldo`: A → MAE 0.3205, RMSE 0.4926; B → MAE 0.3579, RMSE 0.5220.

| Config | ΔMAE A | IC95 celdas (sup.) | Reps que mejoran | ΔRMSE A | ΔMAE B | ΔRMSE B |
|---|---|---|---|---|---|---|
| 1 elevación | +0.0012 | +0.0044 | 1/5 | −0.0016 | +0.0006 | +0.0001 |
| 2 pendiente | +0.0002 | +0.0057 | 2/5 | −0.0036 | +0.0025 | +0.0007 |
| 3 área | +0.0014 | +0.0089 | 2/5 | −0.0026 | +0.0018 | +0.0010 |
| 4 relieve | +0.0006 | +0.0068 | 2/5 | −0.0038 | +0.0017 | +0.0003 |
| 5 relieve + área | +0.0011 | +0.0103 | 2/5 | −0.0052 | +0.0028 | +0.0003 |
| 6 centrado | +0.0027 | +0.0117 | 1/5 | −0.0045 | +0.0022 | +0.0006 |

(Procedimiento principal, `sin_respaldo`. Positivo = peor que la referencia.)

**Cómo leerlo.** Las diferencias en MAE son de milésimas de t/ha y casi todas desfavorables; ningún intervalo queda por debajo de cero. En A el RMSE baja un poco (hasta −0.005 en la configuración 5), señal de que el modelo corrige algunos errores grandes a costa de empeorar ligeramente muchos pequeños; no alcanza la regla, que se decide con MAE. En B (separación espacial) no hay ni eso.

**La selección interna lo confirma por su cuenta.** Ajustado con las 138 parcelas, el procedimiento principal elige «referencia sola» en las 6 configuraciones: sus predicciones para las 59 son idénticas a las de la referencia. En las particiones externas eligió «referencia sola» en 4–6 de 25 ajustes en A y en 13–19 de 25 en B; el resto, α grandes.

**Puente (T11 v2, descriptivo).** Empeora el MAE más que el principal: de +0.010 a +0.020 en A y de +0.005 a +0.017 en B. El principal es mejor que el puente en las 12 comparaciones de MAE; en A el intervalo por celdas queda por debajo de cero en 5 de 6 configuraciones. A cambio, el puente baja algo más el RMSE en A (hasta −0.011, configuración 5). Es la diferencia esperada entre elegir α con error absoluto y con error cuadrático. Evidencia para T11 y T15; no cambia la conclusión de T10.

**Comparaciones descriptivas.** Añadir el área al relieve (5 frente a 4) y centrar por municipio (6 frente a 5) no cambian nada distinguible: todas las diferencias son ≤ 0.002 en MAE y sus intervalos incluyen el cero.

**Sensibilidad por tamaño y cobertura (`desglose_error_t10.csv`; A, `sin_respaldo`, principal; descriptivo).**

| Grupo | Parcelas | MAE referencia | MAE config 5 |
|---|---|---|---|
| Menos de 2 ha | 29 | 0.388 | 0.378 |
| 2 a 5 ha | 41 | 0.277 | 0.274 |
| Más de 5 ha | 65 | 0.318 | 0.326 |
| Menor a una celda de 120 m | 13 | 0.450 | 0.435 |
| Cobertura parcial de relieve | 4 | 0.012 | 0.039 |
| Contorno B o C | 13 | 0.329 | 0.316 |

- Las parcelas pequeñas son las de mayor error con cualquier procedimiento, y es ahí donde las variables restan algo (−0.01); en las grandes suman (+0.008). Los grupos son pequeños y las diferencias no se probaron formalmente: es una pista, no un resultado.
- Las 4 parcelas con cobertura parcial (Calpulalpan y Emiliano Zapata) tienen un error casi nulo con la referencia, porque comparten etiqueta con sus vecinas; las variables sólo pueden empeorarlo. Con 4 parcelas no se concluye nada.
- **Control del pendiente P06.** En los contornos B o C el error baja de 0.329 a 0.316 con la configuración 5, pero también baja con la 4, que no usa el área (0.318). No es la firma de un efecto de medición del área; con 13 parcelas tampoco se descarta.

**Sensibilidad sin las 24 parcelas con alerta de contorno.** Ninguna configuración mejora a la referencia (todas las ΔMAE siguen siendo positivas, de +0.0006 a +0.0042) y la referencia sigue en primer lugar en A y B. El orden entre configuraciones cambia un poco en A, lo esperable con diferencias de milésimas.

**Nota técnica.** Las ΔMAE de `sensibilidad_sin_alerta_t10.csv` (promedio de las métricas de cada repetición) pueden diferir en la cuarta cifra decimal de las de `comparacion_emparejada_t10.csv` (promedio por parcela, como T08), porque en `sin_respaldo` no todas las repeticiones tienen el mismo número de predicciones. La decisión usa la comparación emparejada.

**Conclusión de T10 (para el informe de cierre).** Con este procedimiento, elevación, pendiente y área no aportan información útil sobre la referencia municipal para estimar el rendimiento de estas parcelas. Se conserva la referencia. La pista en parcelas pequeñas queda como hipótesis para T15, no como hallazgo.

**Qué no se comprobó todavía.** La reproducción en otro equipo y en Docker (paso 10). La relación exploratoria con el rendimiento (paso 8).

### 12 de octubre de 2026 — Diagnóstico exploratorio con rendimientos (paso 8)

**Qué se esperaba.** Describir la relación lineal de cada variable con el rendimiento, global y dentro de municipio, como pide el anexo de selección de atributos (§2.2). Es **exploratorio**: se corrió después de la evaluación y no cambia configuraciones, entradas ni la conclusión de T10.

**Qué se hizo.** `python analisis/aporte_relieve_y_area/scripts/explorar_relacion_con_rendimiento.py` con las 138 etiquetadas. «Dentro de municipio» resta a cada variable y al rendimiento la media de su municipio, sólo en los 5 municipios con al menos 5 etiquetas (132 parcelas; 130 en pendiente por los 2 faltantes de D020, que se excluyen del par, no se rellenan).

**Qué se encontró.**

| Variable | r global | r dentro de municipio | r en Chignahuapan (71) | r en Calpulalpan (30) |
|---|---|---|---|---|
| Elevación | +0.29 | +0.16 | +0.20 | +0.02 |
| Pendiente | +0.30 | +0.24 | +0.32 | +0.01 |
| Log del área | −0.25 | −0.24 | −0.32 | −0.04 |

- Spearman da el mismo signo y magnitud parecida en las tres.
- La correlación global de la elevación baja a la mitad al restar el municipio: buena parte era «dónde está la parcela».
- Pendiente y área conservan una relación débil dentro de municipio, pero **casi toda viene de Chignahuapan**. En Calpulalpan, el segundo municipio, es prácticamente cero; en los demás los grupos son demasiado pequeños para leer algo.
- Coincide con lo visto antes de diseñar T10 (pendiente +0.26 y log del área −0.25 dentro de municipio): la cifra no es nueva, y por eso quedó declarada en `D_T10_001`.

**Por qué una correlación de 0.24 no se convierte en una mejor predicción.**
- Una correlación de 0.24 explica cerca del 6 % de la variación que deja el municipio. Aun aprovechándola completa, el error bajaría muy poco, y fuera del entrenamiento hay que estimarla con unas 110 parcelas por partición, lo que se come la mayor parte de esa ganancia.
- Se concentra en un municipio. En el escenario B, donde Chignahuapan queda en bloques completos, no aparece ni siquiera la pequeña baja de RMSE de A.
- Estas dos variables se señalaron en la exploración original por ser las más altas entre 269 resúmenes. Escoger «la mejor» de muchas infla su correlación con los mismos datos: la cifra de esta tabla es optimista por construcción.
- En la figura, parte de la pendiente de la línea la mueven unas pocas parcelas con error grande (rendimiento 1.5–2.3 t/ha por debajo de su municipio). Eso explica que en la evaluación el RMSE bajara un poco y el MAE no.

**Conclusión del paso.** La descripción es compatible con el resultado de la evaluación: hay una asociación débil y local, no una señal que mejore la estimación de parcelas nuevas. Ninguna cifra de este paso se usa para elegir nada; el valor p no es puerta de entrada (anexo §2.2).

### 12 de octubre de 2026 — Cierre y registros (paso 9)

**Qué se hizo.**
- `informe_relieve_y_area.md`: resultado en lenguaje sencillo, con una sección de preguntas y respuestas, límites y qué significa para T11, T15, T16, T17 y T19.
- `docs/T10_relieve_area.md`: estado actualizado y secciones nuevas 13 (resultado) y 14 (cómo reproducir). El diseño (secciones 1–12) no cambió.
- `registro/experimentos.csv`: `E_T10_001`–`E_T10_006`, una fila por configuración del procedimiento principal, con sus cifras en `sin_respaldo`. El puente no tiene filas propias porque no es elegible; queda descrito en cada fila y en `D_T10_001`.
- `registro/uso_ia.csv`: `IA_T10_001`.

**Al integrar con T11.** La rama de T11 también agrega filas al final de `decisiones.csv`, `experimentos.csv` y `uso_ia.csv`. Git marcará conflicto en esos tres archivos; se resuelve conservando las filas de ambos lados.

### 12 de octubre de 2026 — Reproducción (paso 10)

**Qué se esperaba.** Que la evaluación diera exactamente los mismos archivos al repetirla, en otro momento y en el entorno común del equipo.

**Qué se hizo.**
1. Segunda corrida en Linux (Python 3.12.14), en una carpeta aparte.
2. Corrida de Jass en Windows con el entorno común: `.\ejecutar.ps1 python -m scripts.t10_relieve_area --evaluar --salida reports/t10_docker` (Docker, Python 3.12.15, x86_64). Antes, `ejecutar.ps1` comprobó que los datos originales son el paquete de FIRA (166 archivos idénticos al ZIP) y la referencia volvió a coincidir con T08 (1,380 predicciones, diferencia máxima 8.9e-16).

**Qué se comprobó.** En las dos corridas, los 9 archivos de resultados son idénticos byte a byte a los de `registro/t10/`. El manifiesto sólo difiere en el entorno y el tiempo; sus huellas de entradas y de código coinciden.

**Qué no se comprobó.** Una corrida en Mac (ARM). La revisión independiente de Daf.

### 12 de octubre de 2026 — Correcciones tras la auditoría externa (Codex): decisión y desgloses

**Por qué.** Antes del PR, Jass pidió una auditoría independiente con Codex. Reprodujo todo (266 pruebas, los 9 archivos de resultados idénticos) y señaló tres defectos en el código. Ninguno cambia el resultado de T10, pero los tres son reales y se corrigieron.

**1. El control de revuelto no frenaba la promoción.** El script calculaba si la mejora resistía el revuelto, pero la bandera final no lo usaba: una configuración que fallara el revuelto habría salido como «se promueve». **2. El escenario B podía promover solo.** La bandera no exigía el escenario A, que es el principal según T03 §3.
- Cambio: la decisión va en dos tiempos. `candidata_a_promover` = principal, frente a la referencia, cumple la regla en `sin_respaldo` **y en A**. `promueve` = candidata **y** supera el control de revuelto. Cada fila guarda `supera_revuelto` y un `motivo` explícito.
- Pruebas nuevas: ganar sólo en B no promueve; el revuelto frena la promoción (y la permite si se sostiene); sin revuelto no se promueve; el puente y `todas` nunca promueven.

**3. Los desgloses juntaban las 5 repeticiones antes de calcular.** T03 §4 pide métricas por repetición y después su promedio; los desgloses calculaban sobre las predicciones juntas.
- Cambio: cada grupo se calcula por repetición y se promedia; se agregan `n_repeticiones` y `MAE_sd_rep`. Prueba nueva con un caso calculable a mano.
- Efecto: en A con `sin_respaldo` (de donde salen todas las cifras de tamaño, cobertura y contorno de esta bitácora y del informe) el MAE es idéntico, porque cada parcela aparece una vez por repetición. Cambian sobre todo los RMSE (máximo 0.086 t/ha: Singuilucan, B, `todas`, config 4, de 0.859 a 0.781) y algunos MAE de B (máximo 0.0012). T11 v2 calcula sus desgloses del mismo modo anterior; se le avisa a Daf.

**Regeneración.** Se corrió la evaluación completa en una carpeta temporal: 8 de los 10 archivos idénticos a los publicados; cambian `comparacion_emparejada_t10.csv` (sólo agrega las 3 columnas nuevas; los valores existentes son idénticos y ninguna fila se promueve) y `desglose_error_t10.csv`. Se copiaron esos dos y el manifiesto, que coincide con los 10 archivos y con el código nuevo.

**Pruebas.** 18 de T10 (5 nuevas) y la suite completa aprueban.

### 12-oct · Paso 3 de las correcciones: D_T10_002 (unidad de conteo del presupuesto)

- Se registró `D_T10_002` en `registro/decisiones.csv`, fechada y marcada como **posterior a los resultados y a la auditoría externa**. No reescribe `D_T10_001`.
- Qué aclara: el presupuesto de T03 §5 se cuenta en subconjuntos de variables (6 de 8). El α y la opción «referencia sola» se eligen dentro de cada entrenamiento y no cuentan como configuraciones. La lectura estricta alternativa (6 × 9 = 54 combinaciones) queda escrita.
- Por qué no cambia nada: ninguna configuración cumplió la regla, así que la decisión de no promover es la misma con cualquier lectura. Se declara que la aclaración no se usó para elegir ni descartar variables.
- Queda pendiente la confirmación de Migue (él interpreta T03 §5), tanto para esta lectura como para que el puente quede fuera del conteo.

### 12-oct · Paso 4 de las correcciones: informe más prudente y material de apoyo

- **Frases suavizadas en el informe:** resumen («con este procedimiento, estas entradas y esta campaña»); RMSE («con las predicciones actuales tampoco se alcanza el umbral», sin descartar que con RMSE como métrica primaria saliera algo distinto); explicación de la correlación que no ayuda (tres causas compatibles en lugar de una); puente frente a principal (se cambian dos cosas a la vez y sólo se probó con relieve y área); y propuesta para T11 como propuesta, no conclusión.
- **Agregado:** tabla de las 5 parcelas con cobertura parcial (AGC_020, 023, 044, 164, 170) con cobertura, pendiente imputada, fuente de la referencia y errores en A y B; explica por qué AGC_164 está en `todas` y no en `sin_respaldo`.
- **Agregado:** ficha de consumo para T16 (qué filas de `predicciones_59_t10.csv` usar y cuáles no).
- **Aclarado:** la exploración de los 269 resúmenes se reporta desde el contexto local del equipo y no se reproduce en el repositorio.
- **Bitácora de T05:** «casi no cambia» se reemplazó por «el cálculo usa los mismos TIFF verificados; no se comparó con otra edición».
