# T04 · Plan de fase 3: extractor climático por parcela y mes

Responsable: Dani. Revisora independiente: Jass. Fecha: 6 de octubre de 2026.
Estado actualizado: Dani autorizó continuar con 3.4, fases siguientes y ejecución completa. Los puntos 3.1–3.3 están en [su informe](t04_fase3_puntos_1_3.md); 3.4–3.6, revisión técnica de fase 4 y preparación local del PR están en [extracción completa](t04_fase3_completa.md). T04 sigue pendiente de conciliación con T02 aceptada y revisión de Jass. No hay autorización de push para estos cambios.

## Objetivo y alcance

Producir una tabla histórica reproducible de lluvia, Tmin y Tmax para las 197 parcelas y los 48 meses de enero de 2022 a diciembre de 2025. Conservar 28,368 claves únicas (parcela, periodo, variable), incluso cuando alguna no tenga dato válido. Cada promedio deberá poder reconstruirse a partir de las áreas, pesos y valores de sus celdas originales.

El resultado se preparará para la revisión de calidad de fase 4. T04 seguirá en curso hasta la revisión independiente de Jass. La selección de ventanas/variables para modelos y la conciliación de particiones se harán en sus tareas correspondientes; una extracción histórica completa no acredita disponibilidad histórica de todos los meses para una predicción.

## Base disponible

Fase 1: inventario íntegro de 144 mapas y cinco pruebas aprobadas. Fase 2: 15 controles espaciales adicionales, dos parcelas por tres variables de julio, comparación independiente de áreas y proyecto QGIS separado. Dani ya confirmó que el nuevo proyecto se ve como el anterior; esa comprobación no se solicita de nuevo.

Se reutilizarán las funciones y pruebas de `scripts/t04_espacio.py`, revisando lo necesario para ampliar su alcance. En la versión de partida, ese archivo era una comprobación de dos ejemplos: lanza excepciones tanto para ausencia de cobertura como para errores. La entrega completa debe distinguir ambos resultados antes de ampliarse.

## 3.1 · Verificar entradas y registrar la versión de partida

Leer `data/raw/DataSet.zip` y su inventario; comprobar integridad, huella y correspondencia de los 144 mapas con las variables/meses esperados. Leer las geometrías originales desde el maestro y comprobar 197 IDs únicos, validez, CRS y correspondencia con el catálogo disponible.

Separar área declarada y área calculada. No se necesita cargar rendimientos para extraer clima. La fuente para geometrías es el original verificado; cuando T02 aceptada esté disponible se comprobarán IDs y geometrías contra ella. Si cambia una geometría, recalcular el soporte y las salidas afectadas, conservando las ejecuciones anteriores.

Registrar huellas de entrada, identidad del código, parámetros de cálculo y versiones de las dependencias. Si el código sigue sin commit, registrar huellas de los archivos utilizados además del commit base; el commit solo no identifica cambios locales.

**Comprobación de salida:** entradas enumeradas y verificadas, catálogo identificado y discrepancias explícitas. Un archivo ausente/corrupto, un ID duplicado o una geometría inválida detienen la ejecución; no se corrigen eliminando filas o inventando IDs.

## 3.2 · Ampliar el cálculo de soporte físico

Calcular intersecciones con área positiva para cada geometría y cada cuadrícula realmente encontrada. Con los insumos verificados se esperan dos cuadrículas, pero se verificará cada imagen sin asumirlo por su nombre o resolución. Si aparece otra transformación, registrar el cambio y recalcular; no tratarla silenciosamente como una cuadrícula anterior.

Conservar el método de fase 2: intersección en WGS84 nativo y área elipsoidal en m², con bordes lineales densificados sólo al integrar el área. Paso de referencia 0.0005 grados; contraste a 0.00025. Los originales no se densifican ni se remuestrean. Contactos de línea/vértice aportan cero, los huecos se restan y las partes poligonales se suman.

Identificar cada soporte mediante geometría, CRS, transformación, dimensiones y versión/parámetros del método. Reutilizarlo únicamente cuando coincidan. Las máscaras/valores del mes no forman parte del soporte geométrico reutilizable.

Controlar área de parcela, suma de intersecciones y cobertura espacial. Diferenciar cobertura espacial completa por geometría de una pequeña discrepancia de integración numérica. Registrar los cocientes brutos; no convertir cualquier área pequeña en cero ni elevar la tolerancia para ocultar un fallo.

Contrastar áreas de los 197 polígonos mediante proyección equivalente elipsoidal con bordes suficientemente densos. Comparar también áreas de intersección y suma ponderada en la muestra piloto mediante ese método independiente. Ampliar el contraste a todos los casos que fallen o tengan mayor discrepancia; no limitarse a repetir la misma función.

**Comprobación de salida:** tabla de soporte por ID/cuadrícula/celda, conservación de huecos/partes y controles de precisión. Si no se cumple la tolerancia acordada, informar del caso y resolverlo antes de considerar aceptado el cálculo.

## 3.3 · Extraer los mapas y conservar los casos sin dato

Abrir cada mapa una vez y procesar sus parcelas con el soporte correspondiente. Mantener ejecución secuencial y medir recursos durante el piloto; no iniciar Docker ni introducir dependencias adicionales por defecto.

Para cada parcela/mes/variable, leer valores y máscara, calcular área válida, normalizar pesos entre celdas válidas y obtener la media. Lluvia: promedio espacial de la suma mensual en mm/mes. Temperatura: promedio espacial de la media mensual de extremos diarios en °C. No sumar lluvias de celdas vecinas ni inferir días de helada/calor a partir de promedios mensuales.

Tratamientos propuestos:

| Situación | Registro y acción |
|---|---|
| Cobertura válida completa | Media, áreas, pesos, cobertura y estado explícito. |
| Cobertura válida parcial | Media sobre área válida, fracción cubierta y motivo; sin imputación ni descarte automático. |
| Parcela sin intersección espacial | Conservar la clave con media ausente, área intersectada/cobertura cero y motivo. |
| Intersección con todo NoData | Conservar la clave con media ausente, área válida/cobertura cero y motivo distinto. |
| Archivo corrupto, CRS inesperado, geometría inválida o valor válido no finito | Detener y diagnosticar; no convertirlo en un faltante ordinario ni presentar la ejecución como aprobada. |

La clasificación de cobertura completa/parcial tendrá en cuenta la geometría y la máscara; una diferencia mínima de integración no se presentará como franja real sin dato. Los avisos describen el resultado, sin fijar un umbral agronómico de aceptación.

**Comprobación de salida:** claves completas, estados inequívocos, NoData preservado y controles matemáticos por fila.

## 3.4 · Comparar con el centroide

Propuesta: conservar la definición que usa T03, calculando el centroide en EPSG:6372 y regresando a EPSG:4326 para consultar cada cuadrícula. Este cálculo describe una sensibilidad y no modifica las particiones existentes.

Registrar punto, fila/columna, valor del centroide y diferencia frente a la media ponderada en la unidad de la variable. La diferencia relativa en porcentajes no se usará por defecto, especialmente para temperaturas Celsius. Si el punto cae fuera del mapa o en NoData, conservar el motivo y dejar ausente esa comparación, sin buscar una celda vecina para completar el dato.

Probar una regla uniforme de límites: índice obtenido desde la transformación original con redondeo hacia abajo; en un borde interno se asigna la celda a la derecha/abajo. Los límites exteriores derecho/inferior quedan fuera. Conservar el punto original sin desplazarlo para forzar una asignación. En polígonos cóncavos o multipartes, registrar si el centroide cae fuera de la parcela; no sustituirlo por un punto interior sin acuerdo.

**Comprobación de salida:** comparación trazable en ambas cuadrículas, motivos de ausencia y ejemplos con diferencias explicables. Una diferencia grande es un caso a investigar, no prueba automática de error ni de superioridad predictiva.

## 3.5 · Ejecutar primero una muestra piloto

Seleccionar la muestra antes de mirar los promedios, a partir de geometrías, soporte y máscaras. Incluir AGC_014 (dos celdas), AGC_065 (una celda), parcela pequeña/grande, multiparte/huecos y cobertura parcial si existen. Selección reproducible: ordenar IDs y usar reglas explícitas para elegir representantes. Si un caso no existe en los datos reales, indicarlo y conservar su prueba sintética.

Incluir julio de 2025 y meses de otros años/condiciones de máscara elegidos mediante metadatos del inventario, sin emplear rendimientos. Probar cambio mensual de NoData usando los mismos pesos, y que cambiar geometría/cuadrícula invalida su reutilización.

Reproducir los valores de referencia de fase 2 con su precisión original; mostrar a Dani el resumen del piloto y los casos investigados. Contrastarlos en QGIS cuando aporten una comprobación nueva; no repetir la revisión ya confirmada de la copia del proyecto. Si hay un fallo significativo, resolverlo antes de la ejecución completa e informar de cambios metodológicos pendientes.

**Comprobación de salida:** muestra documentada, referencias conservadas, controles independientes aprobados y medición inicial de duración/memoria. El piloto no acredita todavía los 28,368 registros.

## 3.6 · Ejecutar todo y validar la salida exportada

Generar las 28,368 claves esperadas, ordenadas de manera determinista. Comprobar el producto completo de IDs/meses/variables, duplicados y estados, además del total de filas. Validar por mapa los metadatos y máscaras, y por registro las áreas, pesos, rango del promedio y correspondencia con su detalle de celdas.

Una mejora propuesta es volver a leer las tablas exportadas y reconstruir los promedios a partir de ellas. Esto comprueba pérdidas de precisión, enlaces equivocados o diferencias entre lo calculado y lo guardado; no sustituye el contraste independiente del método de áreas.

Repetir la extracción en dos carpetas distintas. Las tablas de datos deberían coincidir con las mismas entradas/código/entorno; fechas y rutas de ejecución se comparan por separado. Verificar que los originales siguen intactos y registrar cualquier diferencia antes de presentar una reproducción aprobada. La comprobación en este Mac no certifica otras plataformas.

**Comprobación de salida:** completitud, reconstrucción, controles y reproducción aprobados, o lista concreta de fallos que impiden aceptar la entrega técnica.

## Entregables propuestos

Resultados locales bajo `data/processed/t04/<ejecucion>/`; evidencia bajo `reports/t04_fase3/<ejecucion>/`. Cada ejecución conserva su carpeta; no sobrescribir originales ni revisiones anteriores. Los nombres siguientes son una propuesta de organización, compatible con las carpetas acordadas.

| Archivo | Función |
|---|---|
| `clima_parcela_mes.csv` | 28,368 registros: ID, periodo, variable, media, unidad, áreas, cobertura, estado/motivo, referencia de soporte/mapa y comparación con centroide. |
| `soporte_celdas.csv` | ID, cuadrícula, celda, área física y peso espacial; incluye referencia del método y geometría. Número de filas variable. |
| `valores_celdas.csv` | Valores y máscara por mapa/celda utilizada, con los pesos válidos o referencias suficientes para reconstruirlos por parcela. |
| `manifest.json` | Huellas, miembros originales, metadatos, parámetros, versiones y procedencia. Disponibilidad/versiones no documentadas quedan explícitas. |
| `controles.json` | Resultado de cada criterio, casos problemáticos, contrastes y reproducción. |
| `resumen_revision.md` | Lectura breve para Dani/Jass: alcance, calidad, ejemplos, límites y pendientes. |

Mantener precisión suficiente en CSV y un esquema documentado de valores ausentes/unidades. Evitar mezclar documentación de una ejecución con datos de otra. El código y las pruebas se podrán proponer posteriormente para revisión; no se añaden datos ignorados, instrucciones privadas ni la skill al contenido publicable.

## Criterios medibles

| Criterio | Evidencia requerida |
|---|---|
| Completitud | Exactamente el conjunto de 197 × 48 × 3 claves; cero duplicados; ausencias conservadas con motivo. |
| Reconstrucción | Promedios reconstruidos desde tablas exportadas dentro de tolerancia; referencias a celdas/mapas existentes. |
| Precisión física | Convergencia y contraste independiente de áreas. Referencia: error relativo 1e-6; diferencia absoluta de media al refinar 1e-6 en su unidad. |
| Consistencia matemática | Pesos válidos suman uno; promedio dentro del rango válido; mapa constante conservado; cobertura y áreas coherentes. |
| Robustez espacial | Pruebas de bordes/vértices, partes/huecos, cobertura/NoData y cuadrículas desplazadas. |
| Reproducción | Dos ejecuciones comparadas, originales intactos, entorno/código/entradas identificados. |
| Revisión | Resumen del piloto y tabla final de controles para Dani; aprobación independiente de Jass para cierre de T04. |

Las tolerancias numéricas no son umbrales de calidad agronómica. Antes del piloto se documentarán también las tolerancias de suma de pesos, reconstrucción CSV y comparación entre plataformas, acordes con los errores medidos y precisión utilizada. No ajustarlas después para declarar éxito sin explicación.

## Revisión de fase 4 y límites de esta fase

Spreadsheets ya está disponible como apoyo para analizar o presentar tablas de cobertura, faltantes y sensibilidad. Se utilizará cuando ayude a la revisión; un libro adicional no se crea por defecto ni se convierte en otro motor de extracción. QGIS aporta contraste visual sobre la copia separada. No se necesita instalar otra herramienta para empezar.

La tabla de soporte permitirá identificar parcelas que comparten celdas y cuantificar sus pesos. Esa evidencia ayudará a conciliar T04 con Migue/Jass; no autoriza reagrupar folds ni asegura independencia espacial del modelo.

Al terminar la fase 3 habrá una entrega técnica para revisar en fase 4. Permanecen como condiciones del cierre la conciliación con T02 aceptada, las limitaciones de disponibilidad/versiones y la revisión independiente. El PR pertenece a fase 5: primero presentar cambios concretos, después obtener autorización de Dani para push y preparar la revisión de Jass.

## Qué debe acordarse antes de implementar

Dani aprobó los criterios generales, el maestro como fuente y la separación/reutilización por cuadrícula. Autorizó primero 3.1–3.3 y después 3.4, fases siguientes y ejecución completa, resolviendo problemas. Este plan conserva los criterios y la progresión piloto → ejecución completa; el informe enlazado registra la implementación y evidencia. La autorización de trabajo local no incluye un nuevo push. No es necesario reinstalar el entorno ni volver a comprobar la copia QGIS ya confirmada.

## Corrección numérica durante 3.1–3.3

El contraste de todas las intersecciones encontró pérdida de precisión Geod en AGC_143 y AGC_174. Se resolvió mediante integración estable de la misma área física WGS84 sobre bordes lineales originales, con método identificado como `wgs84_borde_lineal_cuadratura8_v2`. Se conservaron pasos, tolerancias y cuadrículas. El [informe](t04_fase3_puntos_1_3.md) describe causas, controles independientes de los 197 polígonos/460 intersecciones y diferencias frente a las seis referencias de fase 2. Este cambio exige nueva identidad de soporte; no reutilizar soportes del método anterior.
