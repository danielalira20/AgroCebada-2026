# T09 · Evidencia, decisiones y puntos para revisión

Fecha: 11-oct-2026. Complementa [el diseño vigente](t09_diseno.md) y `registro/t09/diseno.json`. Estado: diseño local; cero estimadores ajustados. Migue conserva el papel de revisor, sin aprobación atribuida.

## Problema que resuelve

El borrador 0.1 dependía de un acuerdo que no había llegado y describía una entrega T07 todavía pendiente. El equipo ya cuenta con una base aceptada y diagnósticos suficientes para fijar un experimento acotado. Era necesario tomar decisiones explícitas, separar hechos de propuestas y evitar que el futuro código eligiera por omisión reglas metodológicas.

## Solución que implementa

Se fija v1.0 por autorización de Dani, con cuatro procedimientos y tres experimentos climáticos de ocho configuraciones cada uno. Se registra normalización de regularización, agrupación interna según uso, contraste a ventana fija y ausencia de intercepto de corrección residual. No se entrenan modelos ni se altera el protocolo general o los resultados del equipo.

## Matriz de evidencia utilizada

| Fuente | Hecho comprobado o información recibida | Uso en diseño | Lo que no demuestra |
|---|---|---|---|
| Plan unificado corregido / Selección de atributos | T09 corresponde a Dani/Migue; territorio, clima, ambos; selección interna y presupuesto; corrección residual prioritaria | Mantener el objetivo y registrar las comparaciones | Que una familia o una entrada vaya a ganar |
| T03 §§2–5 y D019 | A principal, B obligatorio, C informe; referencia, dos poblaciones y regla por bloques | Externos/regla intactos; extensión interna B/C explícita | Independencia de parcelas o validación futura |
| T08, código y OOF | Media municipal con respaldo por grupo; máscaras A675/B659; todas las 59 con `fuente=municipio` | T exacta y soporte común incluso para CL global | Que un municipio con una etiqueta tenga soporte amplio |
| T07 y fichas, dev cb45807 | Tabla197×60, 138/59; seis columnas climáticas completas; clima agregado por días | Lista blanca de entradas y procedencia | Publicación histórica u observación de manejo individual |
| Diagnóstico Dani en Mac/Docker | Asociaciones climáticas globales e internas distintas; perfiles repetidos; cálculos consistentes | No confundir predicción de zona con aporte adicional; cautela de muestra | Que el clima carezca de señal o que Tmax deba seleccionarse |
| T02 catálogo y calidad | Grupos pequeños, redondeo, vecindad y 24 alertas | Desgloses, sensibilidad sobre predicciones comunes | Permiso para descartar casos difíciles |
| T05 aceptada | Relieve integrado y dos pendientes sin valor | No excluir parcelas por una variable que T09 no usa | Que suelo/relieve expliquen causalmente los rendimientos |
| PR15 T11 v2 bfa525d | Código rehace LOO en entrenamiento interno y compara rendimiento completo | Control de fuga adoptado; lectura de código registrada | Nueva reproducción de resultados o aprobación formal del PR |
| PR13 T14 9dffe76 | Usa etapas abr–jun/jul–oct y medias simples para temperaturas; tiene otra selección | No mezclar ventanas/ponderación ni atribuir diferencias sólo al clima | Que sus resultados sean la comparación T09 |
| FIRA segunda sesión P1/P2/P6/P7/P9/P10/P14 | Temporal; fecha de siembra/variedad individual e historial no disponibles; grano t/ha y cuatro decimales | Alcance y contrato sin atributos inventados | Equivalencia entre grupos o datos publicados al corte |
| Transcripción Dani | Reto retrospectivo, datos públicos admisibles, métrica elegida por equipo | Mantener MAE vigente y extensión externa con hipótesis | Instrucción oficial escrita para cambiar T03 |
| Guía conceptual/expediente y análisis previos | Menús amplios de modelos, agua/suelo/fenología, calidad/fechas/errores | Hipótesis y contraste incremental antes de ampliar | Que todos sus experimentos históricos sigan vigentes |
| Documentación primaria Ridge/CV/Roberts | Penalización, ajuste por entrenamiento, dependencia según uso | Derivar λ normalizada por n y separar grupos en B/C | Óptimo numérico de cuadrícula o superioridad de Ridge en este reto |

Los porcentajes climáticos de Tab8 para abril–octubre se reprodujeron y también se revisó junio–octubre. Se mantienen las tres variables por ventana: ninguna se elimina por r global o interno. El árbol de correlaciones/Pearson del mentor sirve como diagnóstico, no como regla final de selección; redes/árboles pequeños siguen como oportunidades en T12.

## Problemas detectados y su resolución

### 1. Soporte escaso no significa respaldo activado

La tabla de soporte de T03 §1 dice que AGC_120, municipio con una sola etiqueta, es un caso donde se activa respaldo. Eso contradice su §4 y la salida T08: `predicciones_59_referencias.csv`, candidato `media_mun__resp_grupo`, tiene 59 fuentes municipales; AGC_120 tiene `fuente=municipio`, predicción 2.5 y municipio Nanacamilpa de Mariano Arista.

La regla real distingue municipio ausente de municipio con pocos ejemplos. Con una etiqueta la media municipal existe y T08 la usa. **Resolución en T09:** tomar soporte/máscara de las identidades y regla T08, registrar soporte escaso aparte; no inventar respaldo para AGC_120 ni eliminarla. El texto de esa celda T03 merece corregirse a «soporte municipal escaso; no se activa respaldo al ajustar con 138». No se editó T03 ni se atribuye esa corrección a Migue. Las fórmulas/predicciones no necesitan cambiar por esta contradicción textual.

### 2. Presupuesto y modelo residual

Ocho combinaciones por procedimiento no son ocho para todo el frente. Se registran prospectivamente tres experimentos: principal TC, diagnóstico CL y residual R, ocho cada uno; 24 totales, permitidos como experimentos separados por T03 §5. Ninguno se añade como reacción a un resultado. T exacta no consume ocho ajustes repetidos.

La corrección con intercepto adicional propuesta en 0.1 puede mantener un desplazamiento incluso con regularización enorme. Se decide R sin ese intercepto, sin declarar equivalencia con T11/T14. La referencia exacta sigue siendo candidato. Ésta es una decisión nueva que el revisor podrá comprobar; no es una corrección numérica de datos previos.

### 3. Dependencia espacial interna y puntuación

En A se mantiene estratificación T03. En B se agrupa por celda y en C por municipio, dentro de cada entrenamiento externo. Se declara extensión a la selección interna del protocolo, sin reemplazar las particiones externas ni esconder la diferencia frente a otros frentes. La política es fijada antes de resultados y no se cambia según quién gane.

La comprobación de viabilidad produjo60 contextos × 4 validaciones = 240, sin entrenamiento ni advertencias. Las cuatro validaciones internas B pueden tener cantidades elegibles distintas (mínimo 5), por lo que se concatenan errores; no se promedia cuatro MAE dando un cuarto de peso a cada partición. C usa todas porque excluye municipios; `sin_respaldo` es no aplicable. T15 deberá unificar políticas si quiere atribuir diferencias entre frentes exclusivamente a sus entradas.

### 4. Penalización según tamaño de entrenamiento

Ridge minimiza suma de cuadrados + α×penalización. El mismo α representa contracción relativa distinta cuando cambia n. Se fija λ sobre pérdida media y se transforma α=nλ en cada ajuste. Las cuatro λ no se escogieron mediante una ejecución exploratoria de T09. Se reconoce que el menú limitado puede omitir un óptimo; no se amplía por ver un resultado desfavorable.

### 5. Confusión de p=0.81

Jass precisó por chat que su registro §3.6 usa Mann–Whitney. Se comprobó ahora el valor sobre la misma área declarada T07, usando SciPy 1.18.1: U = 3984.5, p = 0.814490965750831; KS D = 0.139400638663719, p = 0.35592922053260273. El origen documental §3.6 se recibe de Jass; no se afirma haber localizado esa sección en el registro del repositorio.

**Resolución:** ambos resultados son compatibles como dos pruebas distintas. La retirada previa del 0.81 como resultado KS se conserva como historia, y esta explicación la completa. No se interpreta ninguno como «no hay diferencias», ni probabilidad de igualdad del81%. No se usa para escoger modelos. La cifra KS ya pasó Mac/Docker; la reproducción adicional Mann–Whitney de esta sesión es local, no se afirma haber ejecutado de nuevo Docker para ella.

### 6. Disponibilidad y finalidad del modelo

FIRA confirmó temporal y objetivo retrospectivo, pero no hay una acreditación de publicación histórica de la edición de cada producto climático. Octubre observado no equivale a octubre disponible al31-oct. Se conserva el corte y etiqueta retrospectiva; se fija contrato para otra campaña sin prometer transferencia. No se hacen nuevos ejemplos etiquetados a partir de clima 2022–2024.

## Elecciones consideradas y descartadas para v1

| Alternativa | Motivo para no adoptarla ahora |
|---|---|
| Escoger sólo Tmax por r dentro de municipios | Asociación descriptiva no prueba beneficio predictivo; rompería el contraste inicial de tres variables |
| Usar las seis columnas climáticas juntas | Mezcla ventanas y aumenta dimensionalidad/colinealidad antes del primer contraste |
| Cambiar a una red o boosting en T09 | Confundiría aporte del bloque con algoritmo; el plan dispone de T12 |
| Penalizar municipio junto con clima | Alteraría la referencia municipal y dificultaría atribuir diferencias |
| Escoger el mismo α fijo para cualquier n | Su relación con la pérdida cambia con tamaño; se prefirió λ normalizada |
| Declarar R y TC equivalentes | LOO/respaldo y objetivos distintos; se registran por separado |
| Filtrar CL por `fuente=municipio` | CL tiene fuente global por definición y perdería la población entera |
| Imputar relieve/clima y eliminar atípicas | Relieve no entra y clima está completo; etiquetas difíciles permanecen |
| Optimizar para las59 | No hay etiquetas disponibles; son destinatarias, no criterio de selección |
| Añadir mayo, clima diario, suelo, anomalías ya | Reabriría presupuesto/fuentes antes de demostrar una carencia con las entradas actuales |
| Prometer intervalos individuales o utilidad económica | Requiere validación de cobertura o supuestos/uso económico; no se deduce del IC de ΔMAE |

## Qué tiene de distinto y útil

1. **Dos lecturas del aporte.** La comparación de procedimientos permite elegir la ventana internamente; los contrastes con ventana fija permiten interpretar el bloque sin atribuirle una diferencia debida sólo al calendario.
2. **Penalización comparable entre tamaños.** λ expresa pérdida media frente a contracción; se registra α efectivo para que pueda auditarse la implementación.
3. **Corrección residual controlada.** LOO se rehace dentro de cada entrenamiento y no añade un intercepto de corrección que sobreviva a la contracción.
4. **Validación que corresponde al uso.** A, B y C tienen agrupaciones internas declaradas; el alcance de cada política queda visible.
5. **Datos/revisión trazables.** Listas de entradas, presupuesto, respaldo y fuentes están en configuración machine-readable y registros antes de resultados. No es certificación de innovación científica o mejora predictiva.

## Recursos externos y revisión bibliográfica

Se revisaron fuentes primarias para interpretar herramientas y oportunidades: Ridge/GroupKFold/validación anidada, Roberts 2017, CHIRPS2/CHIRTS-ERA5, AHDB, SoilGrids, Agrocostos y plataforma PAT de FIRA. Los enlaces están en el diseño. No se descargaron insumos externos ni se introdujeron columnas nuevas. INIFAP Hidalgo 2017 no estuvo accesible en esta consulta; sus notas en guías anteriores son antecedentes, sin afirmar nueva lectura íntegra.

NAX aparece en el documento institucional FIRA Premio ALIDE 2025, pp. 13/17 del PDF numeradas en el documento, como proveedor de la PAT. Es una oportunidad para consultar metodologías, disponibilidad y acceso, no prueba de que haya generado los archivos del reto. No se contrató ni contactó al proveedor. Agrocostos estima escenarios por región/tecnología; no acredita dosis o costos de nuestras parcelas. SoilGrids a 250 m justifica estudiar soporte/resolución antes de incorporarlo. La extensión requiere comparación predictiva propia y presupuesto explícito.

Skills utilizadas: scikit-learn y scientific-critical-thinking. Referencia incorporada a §17 del diseño: Kassis/Agarwal/He/Patel/Brueckner 2026, arXiv:2609.00065, versión actual v2 consultada. Las skills aportan procedimientos y cautelas, no validación empírica del futuro predictor.

## Verificación realizada y limitaciones

- Datos completos:197 × 60, 138 etiquetas/59 ausentes y seis columnas de clima finitas.
- Viabilidad:25 contextos A, 25 B, 9 C y 1 ajuste final futuro;240 particiones internas, IDs disjuntos, B/C sin grupos compartidos, cero advertencias y n elegible positivo.
- Máscara externa:675/659 como T08; predicciones de 59 de T08 con 59 fuentes municipales.
- Las fuentes protegidas del informe local conservan sus SHA-256. Diseño no modifica DataSet, T07, T03, QGIS ni scripts del equipo.
- Ningún estimador se ajustó, ningún modelo produjo nuevas predicciones. Las pruebas matemáticas/de fuga y la medición de recursos son condiciones futuras; no se presentan como ya aprobadas.
- El diseño no es ciego a exploraciones previas; los intervalos secundarios serán nominales, existen pocos bloques y sólo una campaña etiquetada.
- El esquema JSON fue contrastado con el texto: dos ventanas, cuatro λ, 24 configuraciones, políticas/máscaras/reportes,6120 ajustes máximos planificados,5520 filas A/B y 552 C.

Evidencia detallada local: `reports/t09_diseno_20261011/`. Su script de comprobación sólo lee entradas y genera particiones de viabilidad/estadísticas nominales; no es el futuro motor T09 ni crea datos de rendimiento.

## Coordinación posterior sin esperar para redactar

Dani fija alcance/implementación; Migue revisa tres decisiones nuevas (penalización normalizada, extensión interna B/C y presupuesto explícito), además de pruebas de referencia/selección. Se le debe señalar la celda de soporte AGC_120 y la aclaración Mann–Whitney/KS. Daf necesita el contrato de ventanas y poblaciones para integrar T11/T15; Jass conserva su revisión de fuentes/calidad; Diego el contrato de salida/app. No se enviaron mensajes externos ni se cambió asignación de revisores.

Esta entrega permite continuar con preflight y desarrollo del código cuando se inicie la siguiente fase. La revisión de Migue sigue pendiente para cerrar T09; su ausencia no se interpreta como aprobación ni impide tener un diseño concreto que pueda revisar.
