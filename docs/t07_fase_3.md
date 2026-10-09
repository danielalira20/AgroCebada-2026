# T07 · Integración del clima y del satélite por ventanas

8 de octubre de 2026. Responsable: Dani. Revisora: Jass. Rama: `t07-tabla-comun`.
Estado: implementación y comprobaciones locales completas; aceptación humana y
relieve T05 pendientes. No se entrenó ni seleccionó un modelo.

## Problema que resuelve

Los meses climáticos y las capturas satelitales no tienen la misma granularidad
que el rendimiento. Unirlos directamente puede multiplicar parcelas y etiquetas.
Además, tener un resumen numérico no implica observar toda la ventana: Landsat,
por ejemplo, tiene meses sin capturas aunque sus medianas estén disponibles.

## Solución que implementa

Unir los bloques por identificador sobre el catálogo de 197 parcelas, conservar
las columnas y cifras de origen y separar su calidad. Las ventanas climáticas
se agregan con un calendario explícito. La aceptación de una fuente se registra
aparte de la comprobación numérica y nunca se deduce de que el cálculo termine.

La base actual de catálogo + T06 es dev `9d5861c81713f2022d9fb9d1952c1feeb236a2f8`.
La actualización T04 está en la rama local `t04-actualizar-referencia-t02`,
commit `842f4c459fe85120867d8c9fd27e05fe049d3fb1`, pendiente de publicación/revisión e incorporación a dev.
El borrador climático y la evidencia de la ejecución inicial se conservan sin
reescribir en reports/t07_fase3_20261008/: identifican base `11d9470` y copia
T04 `7b2b4b4`. Sus cinco archivos de entrada T04 son idénticos a los de la
corrección actual. Ese borrador sigue siendo histórico y pendiente de aceptación.
Dani autorizó expresamente preparar este borrador con datos reales para revisión.
No se integra la rama T04 ni se modifica su estado para presentarla como aceptada.

## Ventanas y significados

| Ventana | Fechas incluidas | Meses | Días | Clima |
|---|---|---|---|---|
| abr_oct | 1 abril–31 octubre 2025 | 7 | 214 | PREC suma; Tmin/Tmax ponderadas por días |
| jun_oct | 1 junio–31 octubre 2025 | 5 | 153 | PREC suma; Tmin/Tmax ponderadas por días |

PREC se expresa en mm acumulados: se suman las medias espaciales mensuales de
T04. Tmin/Tmax se expresan en °C: `sum(media_mensual × días_mes) / días_ventana`.
No son temperaturas mínimas/máximas absolutas del periodo. Las ventanas son
candidatas de calendario; no prueban fechas reales de siembra o cosecha.

Noviembre/diciembre y los años anteriores permanecen en la fuente mensual,
pero no intervienen en estas seis columnas. Un mes ausente, NoData o con
cobertura parcial no produce un resumen principal completo. Se conserva el
vacío y el diagnóstico. En esta entrega real las 1,182 combinaciones
parcela × ventana × variable tienen cobertura completa.

T06 conserva sus 44 columnas con prefijos `pl_`, `s2_` y `ls_`. Se verifican
sensor, ventana, tipo y umbral contra su diccionario. Los umbrales ya fijados
en T06 son Planet 20 %, Sentinel-2 5 % y Landsat 5 %; T07 no los optimiza.
Los dos NDVI al corte son resúmenes de la curva en capturas del 17–31 de octubre,
y se conservan una vez, sin duplicarlos artificialmente en ambas ventanas.
La curva suavizada puede depender de capturas anteriores; no se redefine T06.

La integral NDVI tiene unidad NDVI·días; un día de inicio es día del año 2025,
no días después de siembra. La dispersión NDVI es heterogeneidad espacial,
no incertidumbre de la predicción. La nubosidad media no es cobertura espacial.
Para LAI2 y VI6T el diccionario T06 no documenta la unidad física: se conserva
el nombre del índice, se marca esa limitación en cuatro columnas y se deja
explícita su confirmación, sin atribuir unidades por suposición.

Corte observado no acredita que el producto estuviera publicado entonces.
Esta tabla permite una reconstrucción retrospectiva; no demuestra viabilidad
de un pronóstico temprano ni utiliza disponibilidad histórica no confirmada.

## Dos entregas con estados distintos

**Registro local preparado para el siguiente PR:** `registro/t07/tabla_comun.csv`
contiene catálogo + T06, 197 filas y 52 columnas. Sus ocho archivos incluyen
el diccionario, calidad satelital, contrato de roles, inventario y huellas.
T04 continúa pendiente y T05 sin entrega identificada. No se crean columnas
vacías para simular un bloque aún no integrado.

**Borrador completo local para Jass:**
`reports/t07_fase3_20261008/completa/tabla_comun.csv` contiene catálogo + seis
columnas climáticas + T06, 197 filas y 58 columnas. Sus once archivos incluyen
además las ventanas climáticas largas, anchas y sus controles. Todo queda
ignorado por Git y marcado `borrador_local_para_revision`, con
`clima_aceptado: false` y `cierre_t07: false`.

La tabla completa no es una matriz automática de entrenamiento: hay un objetivo,
33 predictores candidatos, 18 columnas de calidad, cinco metadatos y una columna
sólo de auditoría. `contrato_columnas.json` identifica esos roles sin decidir
experimentos. Las dos ventanas no crean dos rendimientos por parcela.
Se preservan las 138 etiquetas originales y las 59 ausentes, sin imputarlas.

## Comprobaciones y hallazgos

| Comprobación | Resultado |
|---|---|
| Pruebas | 124 aprobadas en implementación inicial; 16 de compatibilidad tras actualizar dev |
| Unión | 197 IDs; 8,668 valores satelitales conservados literalmente |
| Cobertura T06 | 1,182 controles conciliados con su tabla independiente |
| Clima | 28,368 registros leídos; 1,182 agregaciones contrastadas con Decimal |
| Diferencia numérica máxima | 1.02e-13; tolerancia 1e-9 en la unidad de cada variable |
| Reproducción | Dos ejecuciones idénticas: ocho archivos satélite; once completos |
| Diccionario | 75 definiciones en entrega satelital; 109 en borrador completo |
| Fuentes protegidas | DataSet.zip, QGIS, particiones T03 y entrega compartida T04 intactos |

La auditoría recalcula con Decimal y un calendario independiente del agregador.
Comprueba las tres representaciones de cada resumen: larga, ancha y tabla común.
Las pruebas detectan cifras, etiquetas o roles incorrectos aunque se actualicen
las huellas de los archivos. Otra prueba cambia las 24,231 filas mensuales fuera
de las ventanas y confirma que ningún resumen cambia.

Se detectó y corrigió un fallo durante la implementación: la definición del ID
se duplicaba al trasladar catálogo y clima al diccionario de la tabla común.
La validación detuvo la salida antes de publicarla. Ahora el ID se define una
sola vez por archivo y existe una prueba específica.

Se registran siete parejas de columnas numéricamente iguales entre ventanas.
Se conservan ambas: es una igualdad observada en esta entrega, no una regla
universal ni una selección basada en el rendimiento. Seis son índices/rasgos
y una es el hueco máximo de Sentinel-2. El diagnóstico queda en controles.json.

| Sensor | Capturas medianas abr_oct / jun_oct | Hueco máximo mediano | Mayor hueco | Parcelas con algún mes sin captura |
|---|---|---|---|---|
| Planet | 82 / 45 | 20 días | 27 días | 0 |
| Sentinel-2 | 31 / 20 | 25 días | 35 días | 0 |
| Landsat | 15 / 9 | 40 días | 72 días | 58 |

Estos hallazgos no prueban que una ventana o sensor prediga mejor. Una ausencia
satelital queda vacía, identificada por columna y en su control; cero conserva
su significado numérico. La presencia de todas las cifras actuales no borra
los huecos de observación ni garantiza calidad suficiente para cada experimento.

La sincronización posterior con dev reejecutó catálogo + T06 y su verificador
sobre la base actual, dos veces. Los ocho archivos nuevos son reproducibles;
seis son idénticos a la etapa inicial, incluida tabla_comun.csv. Sólo cambian
inventario_fuentes.json y manifest.json para identificar dev y el protocolo T03.
No se repite el cálculo climático ni se traslada el borrador al registro.
Evidencia nueva: reports/t04_t07_sincronizacion_dev_20261008/ y
[registro de sincronización](t07_sincronizacion.md).

## Reproducción y revisión

Desde la raíz del repositorio, usando el entorno local existente:

```sh
.venv/bin/python -m unittest discover -s tests -v

.venv/bin/python scripts/t07_integrar.py --sin-clima \
  --base-dev 9d5861c81713f2022d9fb9d1952c1feeb236a2f8 \
  --salida reports/t07_revision_nueva/satelite

.venv/bin/python scripts/t07_verificar.py \
  --entrega reports/t07_revision_nueva/satelite
```

Para revisar el borrador real T04, sin fusionar su rama:

```sh
.venv/bin/python scripts/t07_preparar_insumos.py \
  --revision-t04 842f4c459fe85120867d8c9fd27e05fe049d3fb1 \
  --estado-t04 en_revision --salida reports/t07_revision_nueva/entrada_t04

.venv/bin/python scripts/t07_integrar.py \
  --base-dev 9d5861c81713f2022d9fb9d1952c1feeb236a2f8 \
  --clima reports/t07_revision_nueva/entrada_t04 \
  --revision-t04 842f4c459fe85120867d8c9fd27e05fe049d3fb1 \
  --para-revision --salida reports/t07_revision_nueva/completa

.venv/bin/python scripts/t07_verificar.py \
  --entrega reports/t07_revision_nueva/completa \
  --clima reports/t07_revision_nueva/entrada_t04
```

Las salidas deben ser nuevas. El modo de borrador sólo escribe dentro de
`reports/`; una entrega T04 en revisión se rechaza sin ese modo explícito.
No se cambia a `aceptada` para desbloquear la publicación. Las referencias
T02 incompatibles siguen deteniendo el proceso. El revisor necesita el commit
local T04; antes de publicarlo, Dani debe autorizar ese lote por separado.
Tras su aceptación e integración en dev, se identifica la nueva base/revisión,
se vuelve a comprobar compatibilidad y se regeneran los derivados compartidos.

Evidencia local: `reports/t07_fase3_20261008/validacion_final.json`,
`verificacion_completa.json`, `verificacion_satelite.json` y `pruebas.log`.

## Pendientes y límites de alcance

Jass debe revisar T04 y esta integración. T05 se añadirá como otro bloque cuando
llegue su entrega. El PR #10 ya está fusionado: T03 recoge D019, reporta todas
y sin_respaldo y decide en sin_respaldo frente a media_mun__resp_grupo.
Se identifica el texto vigente; no se modifican las fechas de las ventanas ni
se recalculan métricas o se decide un modelo en T07.

Las guías sirven para justificar hipótesis antes de fijar variables. El siguiente
hito para evaluar datos externos es la primera evaluación T09 frente a T08,
con una carencia e hipótesis explícitas y los mismos controles de evaluación.
No se añadieron ahora sensores, suelo o clima externo ni se promete mejora de
predicción. Antes de congelar T16 se revisará nuevamente esa decisión.
