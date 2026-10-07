# Bitácora de la exploración de parcelas en QGIS

> **Nota para el equipo.** Esta es la bitácora de trabajo completa, en orden cronológico: qué se hizo en cada momento, qué se decidió y por qué. Para el resultado, lee primero el [informe](informe_contornos_sobre_campo_real.md). La bitácora menciona algunos documentos de trabajo locales de Jass (un registro de decisiones y auditorías previas del dataset) que no están en este repositorio; lo necesario de ellos está resumido aquí o en el informe. Las rutas de carpetas que aparecen corresponden a la carpeta local donde se trabajó; en el repositorio el dataset va en `data/`, que Git no sube.

**Pregunta que debe quedar contestada:** ¿cada contorno cae sobre un campo agrícola real?

Corresponde al paso 1 del plan de evidencia de Jass, previo a la tarea T02. Todo lo que se produzca en esta exploración se guarda dentro de esta carpeta.

**Estado al 5 de octubre de 2026: exploración cerrada.** La respuesta está en el [informe](informe_contornos_sobre_campo_real.md). preparación terminada, contornos cargados y comprobados, y ubicación revisada por muestra sobre OpenStreetMap. Piloto cerrado y categorías fijadas. Las 197 parcelas tienen imagen exportada y una primera calificación; 35 están confirmadas en QGIS.

## Qué hay en esta carpeta

| Carpeta o archivo | Qué guarda | Estado |
|---|---|---|
| `bitacora.md` | Este documento: pregunta, organización, reglas y bitácora. | Creado |
| `README.md` | Entrada corta para el equipo. | Añadido al subir al repositorio |
| `proyecto_qgis/contornos_sobre_imagen.qgz` | El proyecto de QGIS. Guarda qué capas están abiertas y cómo se ven; no contiene los datos, solo apunta a ellos. | Creado; con la capa de contornos |
| `capturas_comprobacion_ubicacion/` | Capturas de la comprobación de ubicación. Organizadas por mapa de fondo, estado y municipio: `openStreetMap/<Estado>/<municipio>/AGC_###_<Municipio>.png`. | Creada por Jass; 15 capturas |
| `capturas_parcelas_atlas/` | Imágenes de las 197 parcelas exportadas de forma automática con el Atlas de QGIS, todas con el mismo encuadre. Una carpeta por parcela, con `AGC_###_esri.jpg` y su archivo `.jgw` de ubicación. | Creada por Jass; 197 imágenes |
| `capturas_parcelas/` | Imágenes exportadas desde QGIS de cada parcela sobre la imagen satelital. Una carpeta por parcela (`AGC_###/`), con una o varias vistas (`AGC_###_esri.jpeg`, `_esri2`, `_esri3`: de más cerca a más lejos). Cada imagen trae un archivo `.jgw` con su ubicación geográfica. | Creada por Jass; 10 parcelas, 17 imágenes |
| `imagenes_externas/` | Imágenes descargadas de fuentes públicas, con su fuente y fecha. | Se crea cuando haga falta |
| `revision_contornos/revision_contornos.csv` | La tabla con la calificación de cada parcela: letra, cinco marcas de sí o no, nota, etapa y fecha. No contiene el rendimiento. | 197 parcelas: 35 confirmadas en QGIS, 2 revisadas sin poder confirmar y 160 con primera pasada sobre imagen |
| `informe_contornos_sobre_campo_real.md` | Respuesta final, evidencia y lo que quedó sin resolver. | Escrito el 5 de octubre |

## Reglas de esta carpeta

- Los nombres dicen lo que contiene cada cosa. No se usan nombres de persona ni la palabra «paso».
- Sin espacios ni acentos; minúsculas y guion bajo.
- Las carpetas se crean cuando se necesitan, no antes.
- El dataset original no se copia, no se mueve y no se modifica. El proyecto de QGIS solo lo lee desde `dataset/DATASET_RETO_AGRO_2026/`.
- Las capturas se nombran por ID y tipo de imagen, por ejemplo `AGC_157_mapa_base.png`.
- **Aviso:** el proyecto de QGIS localiza el dataset por su posición respecto a esta carpeta. Si esta carpeta se mueve a otro lugar, hay que volver a indicarle a QGIS dónde está el shapefile.

## Tareas de la exploración

| Tarea | Qué se hace | Estado |
|---|---|---|
| Preparación | Instalar QGIS, conocer la pantalla y guardar el proyecto. | **Hecha** |
| Cargar los contornos | Abrir el shapefile de las 197 parcelas y comprobar que se leyó completo. | **Hecha** |
| Poner la imagen de fondo | Agregar un mapa con nombres y un mapa base satelital, y comprobar que los contornos caen en la región correcta. | **Hecha** |
| Ajustar cómo se ven | Contornos sin relleno y con su ID como etiqueta; vista aparte pintada por municipio. | **Hecha** |
| Piloto | Revisar 10 parcelas para probar las categorías. | **Hecha** |
| Revisión completa | Calificar las 197 parcelas. | **Hecha** |
| Cierre | Segunda mirada a las dudosas, conteo final e informe. | **Hecha** |

## Bitácora

### 4 de octubre de 2026 — Preparación

- Se descargó QGIS desde el sitio oficial, `https://qgis.org/download/`. Se eligió la versión de largo plazo **LTR 3.44** para Windows, por ser la estable. No se eligió la 4.2 (más nueva, menos probada) ni el instalador OSGeo4W (para usuarios avanzados).
- Se instaló con las opciones por defecto.
- Al primer intento se abrió por error Qt Linguist, una herramienta auxiliar que viene en el mismo instalador. Se cerró sin guardar. El programa correcto es «QGIS Desktop 3.44».
- QGIS abrió en español. El sistema de coordenadas del proyecto es EPSG:4326 (latitud/longitud WGS84), el mismo que declara el archivo `.prj` de las parcelas.
- Se creó un proyecto nuevo vacío y se guardó como `proyecto_qgis/contornos_sobre_imagen.qgz`.
- Jass creó a mano la carpeta `exploracion_parcelas_qgis/` y la subcarpeta `proyecto_qgis/`.

**Decisiones de Jass en esta etapa:**

- La evidencia de esta exploración vive en una carpeta en la raíz de `Agrocebada/`, con un nombre que diga lo que se busca.
- Los nombres no llevan su nombre ni «paso N».
- Las subcarpetas se crean conforme se vayan necesitando.
- Jass hace los clics en QGIS; la guía se da paso a paso, y cuando se analicen datos se dice qué se quiere ver o comprobar.

### 4 de octubre de 2026 — Cargar los contornos

- Se abrió `Parcelas_Reto_AGC_CONJUNTO.shp` desde la carpeta descomprimida del dataset (no desde el `.zip`), con el menú Capa → Añadir capa → Añadir capa vectorial.
- **Comprobado en la tabla de atributos de QGIS:**
  - «Objetos totales: 197». Están todas las parcelas.
  - Seis columnas: `Cultivo`, `ID_POLIGON`, `área_ha`, `Municipio`, `Estado`, `CONJUNTO`.
  - `área_ha` se lee con su acento, sin símbolos extraños.
  - La columna `Cultivo` muestra las dos escrituras, `Cebada` y `CEBADA`.
  - El sistema de coordenadas del proyecto sigue siendo EPSG:4326.
- Coincide con la auditoría previa de archivos: QGIS leyó los cinco archivos del shapefile.
- **Observado en el mapa, todavía sin interpretar:** los contornos aparecen en varios grupos separados entre sí, y al menos uno tiene forma de arco delgado. A qué municipio corresponde cada grupo se confirma al poner la imagen de fondo.

### 4 de octubre de 2026 — Comprobación de ubicación sobre OpenStreetMap

**Qué se hizo.** Jass agregó OpenStreetMap como fondo, lo dejó debajo de la capa de parcelas y usó la herramienta «Identificar objetos espaciales» sobre parcelas de distintos grupos. Guardó 15 capturas en `capturas_comprobacion_ubicacion/openStreetMap/`, ordenadas por estado y municipio.

**Alcance, dicho por Jass:** es una muestra, no las 197. De Puebla revisó varias y todas las que vio están en Chignahuapan. De Hidalgo y Tlaxcala hay parcelas en varios municipios y solo capturó algunas. Capturó además parcelas que se ven casi pegadas entre sí en Tlaxcala e Hidalgo.

| Estado | Municipio | Parcelas capturadas |
|---|---|---|
| Hidalgo | Almoloya | AGC_137 |
| Hidalgo | Apan | AGC_164 |
| Hidalgo | Cuautepec de Hinojosa | AGC_083 |
| Hidalgo | Emiliano Zapata | AGC_044, AGC_196 |
| Puebla | Chignahuapan | AGC_018, AGC_024, AGC_033, AGC_172, AGC_189 |
| Tlaxcala | Calpulalpan | AGC_023, AGC_061, AGC_170, AGC_187 |
| Tlaxcala | Nanacamilpa de Mariano Arista | AGC_048 |

Sin captura todavía: Singuilucan y Tepeapulco (Hidalgo).

**Comprobado en las capturas revisadas** (9 de las 15: AGC_023, 024, 044, 048, 083, 137, 164, 170 y 196):

- Los contornos caen en la región esperada, entre Hidalgo, Puebla y Tlaxcala. Ninguno aparece en un lugar absurdo.
- El grupo de Tlaxcala rodea la ciudad de Calpulalpan.
- Las dos parcelas de Emiliano Zapata capturadas están al oeste y suroeste del pueblo de Emiliano Zapata, a pocos kilómetros al norte de Calpulalpan.
- El grupo grande de Puebla está alrededor de la localidad El Paredón, junto al límite entre Hidalgo y Puebla. La ficha de AGC_024 dice Chignahuapan, Puebla.
- Las parcelas de Almoloya están al sur de ese grupo; AGC_137 (24.81 ha) es la parcela con forma de arco delgado que se había visto al cargar los contornos.
- AGC_083 (Cuautepec de Hinojosa, Hidalgo) está al noroeste de El Paredón.

**Observado, todavía sin comprobar:**

- **Tres parcelas juntas sobre el límite estatal.** AGC_164 (Apan, Hidalgo), AGC_170 y AGC_023 (Calpulalpan, Tlaxcala) forman un grupo de tres contornos contiguos, justo donde OpenStreetMap dibuja el límite entre Hidalgo y Tlaxcala. A esta escala no se distingue de qué lado cae cada una.
- **Coincidencia con el relieve incompleto.** Las cinco parcelas con cobertura parcial de relieve detectadas en una auditoría previa del dataset son AGC_020, AGC_023, AGC_044, AGC_164 y AGC_170. Tres de ellas son justo ese grupo, y las otras dos son de Emiliano Zapata, municipio vecino. **Sospecha:** el mapa de relieve tiene un hueco a lo largo del límite entre estados. Se revisa en el paso de relieve.
- AGC_048 dice Nanacamilpa de Mariano Arista, pero se ve al sureste de Calpulalpan y el mapa no muestra el pueblo de Nanacamilpa cerca. OpenStreetMap, a esta escala, no deja ver los límites municipales.
- En el grupo de El Paredón hay varios contornos muy delgados y paralelos, como franjas.

**Corrección a una suposición previa de la guía:** se había supuesto que el grupo de arriba a la izquierda era Singuilucan. No se ha comprobado; no hay captura de ese grupo.

**Sobre las parcelas «casi pegadas»:** una auditoría previa del dataset comprobó que entre los 19 306 pares posibles no hay contornos que se encimen ni que se toquen. Están cerca, pero separados. Hay 46 pares con centroides a menos de 250 m.

**Límite de esta comprobación:** con OpenStreetMap se confirma la región y el pueblo cercano, no el municipio exacto de cada parcela. Para eso harían falta los límites municipales oficiales.

### 4 de octubre de 2026 — Imagen satelital de fondo

- Se agregó una conexión de teselas XYZ llamada «Esri World Imagery», con la dirección `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`.
- Orden de capas, de arriba hacia abajo: Parcelas_Reto_AGC_CONJUNTO, Esri World Imagery, OpenStreetMap.
- **Comprobado:** la imagen se dibuja debajo de los contornos y ambos coinciden en posición a simple vista (zona de El Paredón, escala 1:44 462).
- **Límite:** la imagen no tiene fecha conocida; puede ser de un año distinto a 2025. Sirve para ver el terreno, no para confirmar qué estaba sembrado en la campaña.
- Incidente: el mapa quedó en blanco porque la vista se había desplazado lejos de las parcelas (coordenada −45°, 12°; escala 1:61 millones). Se resolvió con clic derecho sobre la capa de parcelas → «Zoom a la capa». No se perdió nada.
- El proyecto quedó guardado.

### 4 de octubre de 2026 — Ajuste de la vista y vista por municipio

**Contornos.** En la capa `Parcelas_Reto_AGC_CONJUNTO` se cambió la simbología a relleno «Sin relleno», borde amarillo de 0.6 de ancho, y se activaron etiquetas con el campo `ID_POLIGON` (texto blanco, tamaño 8, con buffer). La imagen se ve a través de cada parcela.

**Vista por municipio.** Se duplicó la capa dentro del proyecto con el nombre «Parcelas Por Municipio», con simbología «Categorizado» por el campo `Municipio`, relleno sólido y sin etiquetas. Es otra forma de ver el mismo archivo; el shapefile no se duplicó ni se modificó. Las dos vistas se prenden y apagan según haga falta.

**Comprobado: los conteos por municipio coinciden con la auditoría previa de archivos.**

| Municipio | En QGIS | Esperado |
|---|---:|---:|
| Chignahuapan | 100 | 100 |
| Calpulalpan | 44 | 44 |
| Singuilucan | 23 | 23 |
| Almoloya | 14 | 14 |
| Cuautepec de Hinojosa | 9 | 9 |
| Emiliano Zapata | 3 | 3 |
| Nanacamilpa de Mariano Arista | 2 | 2 |
| Apan | 1 | 1 |
| Tepeapulco | 1 | 1 |
| Sin municipio | 0 | 0 |
| **Total** | **197** | **197** |

**Observado en la vista de conjunto (escala lejana, sobre la imagen satelital):**

- Singuilucan forma el grupo de arriba. Queda resuelta la duda anterior.
- Tepeapulco es una sola parcela, aislada entre los grupos; por su posición parece ser AGC_047, falta confirmarlo con la herramienta de identificar.
- Chignahuapan forma el grupo grande de la derecha y Almoloya queda debajo de él.
- Calpulalpan forma el grupo de abajo, con las parcelas de Apan, Emiliano Zapata y Nanacamilpa en sus orillas.
- Cuautepec de Hinojosa es el más disperso: sus parcelas aparecen en varios puntos separados entre sí.
- No se ve ninguna parcela de un color metida dentro del grupo de otro municipio.

**Límites de esta comprobación:**

- A esa escala las parcelas pequeñas casi no se distinguen; una excepción pequeña podría pasar inadvertida.
- Los colores de Emiliano Zapata, Nanacamilpa y Apan quedaron muy parecidos entre sí (verdes y amarillo).
- Muestra que los grupos son coherentes, no que la línea municipal oficial pase por donde debe.

### 4 de octubre de 2026 — Reglas de la revisión y lista del piloto

**Confirmación pendiente resuelta.** La parcela de Tepeapulco es AGC_047 (64.3 ha, la más grande del conjunto), según la tabla del shapefile.

**Decisiones de Jass:**

1. **La revisión se hace sin ver el rendimiento.** No se carga el CSV de rendimiento en el proyecto ni se consulta mientras se califica. Motivo: el rendimiento no ayuda a ver si un contorno cae sobre un campo, y conocerlo puede inclinar la calificación sin que uno lo note. El cruce entre categoría y rendimiento se hará después, con la tabla ya cerrada, al auditar la etiqueta.
2. **Se empieza con cinco categorías**, que el piloto sirve para ajustar:

| Letra | Significa |
|---|---|
| A | Campo agrícola y el borde coincide |
| B | Campo agrícola, pero el borde está corrido o incluye algo ajeno (camino, árboles, construcción) |
| C | Abarca varios campos distintos |
| D | No parece campo agrícola |
| E | No se puede decidir |

3. **Regla para cambiar categorías:** durante el piloto se cambian libremente; al terminar el piloto se fijan con una definición escrita; si después hay que añadir una, se recalifican las parcelas ya revisadas. Cada cambio se anota aquí con su motivo.

**Límite reconocido:** algunos rendimientos ya se conocen por los documentos del proyecto (AGC_001 y AGC_046 del caso de estudio, y nueve parcelas de rendimiento extremo identificadas en una auditoría previa). No se pueden olvidar; sí se evita tenerlos a la vista.

**Lista del piloto.** Se eligieron 10 parcelas por su forma, tamaño, municipio y escritura, usando solo la tabla del shapefile. No se consultó el rendimiento para elegirlas y se evitaron a propósito las nueve parcelas extremas, salvo las dos del caso de estudio.

| # | Parcela | Municipio | Escritura | Conjunto | Área (ha) | Puntos | Por qué se eligió |
|---|---|---|---|---|---:|---:|---|
| 1 | AGC_001 | Calpulalpan | Cebada | Entrenamiento | 7.61 | 9 | Parcela del caso de estudio; punto de partida conocido |
| 2 | AGC_046 | Calpulalpan | Cebada | Entrenamiento | 7.92 | 5 | Cuadrilátero; vecina de AGC_001 en el caso de estudio |
| 3 | AGC_157 | Calpulalpan | Cebada | Entrenamiento | 1.18 | 4 | El único triángulo |
| 4 | AGC_164 | Apan | Cebada | Entrenamiento | 11.84 | 8 | Una de las tres juntas sobre el límite estatal; relieve incompleto |
| 5 | AGC_091 | Chignahuapan | CEBADA | Predicción | 0.35 | 35 | La más pequeña |
| 6 | AGC_115 | Chignahuapan | CEBADA | Entrenamiento | 1.93 | 15 | Una de las franjas delgadas y paralelas (junto a AGC_062, AGC_073 y AGC_139) |
| 7 | AGC_182 | Chignahuapan | CEBADA | Predicción | 4.13 | 132 | La de forma más irregular |
| 8 | AGC_137 | Almoloya | CEBADA | Entrenamiento | 24.81 | 17 | La de forma de arco |
| 9 | AGC_047 | Tepeapulco | CEBADA | Entrenamiento | 64.30 | 33 | La más grande y la única de su municipio |
| 10 | AGC_148 | Singuilucan | CEBADA | Entrenamiento | 2.46 | 5 | Cuadrilátero dentro de la escritura `CEBADA` |

Composición: 4 de escritura `Cebada` y 6 de `CEBADA`; 8 de entrenamiento y 2 de predicción; seis municipios. No hay ninguna de Cuautepec de Hinojosa, Emiliano Zapata ni Nanacamilpa.

**Qué se mira en cada parcela:**

1. Qué hay dentro del contorno: tierra de cultivo, o árboles, construcciones, agua.
2. Si el borde del contorno sigue una orilla visible del terreno.
3. Si incluye algo ajeno: camino, hilera de árboles, casa, barranca.
4. Si dentro se ve un solo campo o varios separados.
5. Si la imagen se ve con claridad suficiente para decidir.

### 4 de octubre de 2026 — Piloto: lectura de las 10 parcelas

**Qué se hizo.** Jass exportó desde QGIS 17 imágenes de las 10 parcelas del piloto, con contorno amarillo sobre Esri World Imagery, y las guardó en `capturas_parcelas/`. Se revisaron las 17. La lectura de abajo se hizo sobre esas imágenes, sin consultar el rendimiento. **Es provisional:** falta que Jass confirme cada una mirando en QGIS a más detalle.

**Observaciones de Jass:** en algunas la imagen está borrosa; la mayoría no incluye nada ajeno; en la primera vio muchas líneas con árboles; en una vio una casa pequeña dentro.

| Parcela | Qué hay dentro | Cómo queda el borde | Lectura provisional |
|---|---|---|---|
| AGC_001 | Campo de cultivo cruzado por unas seis hileras de árboles o arbustos, paralelas | Sigue los caminos y orillas visibles por los cuatro lados | Borde coincide; vegetación interna en hileras |
| AGC_046 | Tres tramos de cultivo separados por dos líneas de arbustos | Cuadrilátero que sigue el camino al oeste y las orillas visibles | Borde coincide; dividida en tres por dentro |
| AGC_157 | Un solo tramo de cultivo con las huellas de cosecha | Triángulo real: una cuña entre un camino diagonal y campos rectos. No se distingue una orilla clara con AGC_163, al norte | Borde coincide en lo visible; lado norte por confirmar |
| AGC_164 | Cultivo con manchas de tono distinto y unas marcas curvas | Sigue el camino al oeste y un cambio de tono al este | Borde coincide; interior desigual |
| AGC_091 | Un solo campo pequeño entre hileras de árboles | Muy ajustado a la orilla; tiene un pico pequeño en la parte de arriba que cae sobre árboles | Borde coincide; pico menor sobre árboles |
| AGC_115 | Franja larga de cultivo, de unos 30 m de ancho | Paralelo a las franjas visibles; la imagen muestra manchas verdes y encharcadas que cruzan varias franjas | Borde coincide; franja muy angosta |
| AGC_182 | Tres campos oscuros separados por arbolado | Un solo contorno une los tres campos mediante pasillos delgados que atraviesan el arbolado | Abarca varios campos |
| AGC_137 | Terrazas largas al pie de un cerro, con líneas de árboles | Coincide al oeste; al este es un trazo grueso sobre las terrazas | Campo agrícola con borde aproximado |
| AGC_047 | Un campo muy grande, con una línea diagonal que lo cruza y una construcción pequeña con un parche verde cerca de la orilla oeste | Muy ajustado; rodea y deja fuera unas construcciones al oeste | Borde coincide; inclusión menor |
| AGC_148 | Un solo campo de tono parejo; imagen algo borrosa | Cuadrilátero que sigue el camino y dos líneas de árboles. No se ve una orilla física con AGC_089, al sur | Borde coincide; posible mismo campo que AGC_089 |

**Comprobado en estas 10:**

- Las 10 caen sobre tierra de cultivo. Ninguna cae en monte, pueblo o agua.
- AGC_164, AGC_170 y AGC_023 no se tocan: las separa un camino de terracería. Coincide con la auditoría previa.
- Los contornos de la escritura `CEBADA` siguen la orilla del terreno con mucho detalle (AGC_091, AGC_047, AGC_182).

**Sobre la sospecha de los contornos simples.** Las cuatro parcelas de la escritura `Cebada` revisadas (AGC_001, 046, 157 y 164) coinciden con campos reales: en esa zona los campos son rectos y un cuadrilátero los describe bien. **En esta muestra la sospecha no se sostiene.** Son solo cuatro parcelas; la revisión completa lo dirá.

**Hallazgos que afectan a pasos posteriores:**

- **Vegetación interna.** AGC_001, AGC_046 y AGC_137 tienen hileras de árboles o arbustos dentro del contorno. Sus índices satelitales promedian cultivo y árboles.
- **Un ID, varios campos.** AGC_182 reúne tres campos con un solo rendimiento.
- **Parcelas angostas o muy pequeñas.** AGC_115 mide unos 30 m de ancho, es decir, unos tres píxeles de Sentinel-2; AGC_091 mide 0.35 ha. Casi todos sus píxeles son de orilla.
- **Posible campo partido en dos ID.** AGC_148 y AGC_089.
- **La imagen no es de una sola fecha.** En Calpulalpan se ve rastrojo seco; en El Paredón, verde y encharcado. La fecha de cada zona es desconocida.

**Lo que mostró el piloto sobre las categorías.** Las letras A a E mezclan dos preguntas distintas: si el borde coincide y qué hay dentro. Varias parcelas tienen buen borde y, aun así, algo que anotar por dentro. Propuesta pendiente de decisión de Jass: conservar la letra para la pregunta principal y añadir marcas de sí o no (vegetación interna, construcción, varios campos, angosta o muy pequeña, imagen poco clara).

**Dudas por confirmar en QGIS:**

1. AGC_157: si hay una orilla visible entre ella y AGC_163.
2. AGC_137: el lado este, visto de más cerca.
3. AGC_164: si la línea tenue que cruza la parte alta divide dos campos.
4. AGC_148 y AGC_089: si entre ambas hay alguna separación física.
5. En qué parcela vio Jass la casa pequeña.

### 4 de octubre de 2026 — Piloto: confirmaciones de Jass en QGIS

Jass revisó en QGIS las cinco dudas, acercándose más de lo que permiten las imágenes exportadas.

| Duda | Lo que confirmó Jass | Cómo queda |
|---|---|---|
| AGC_157 frente a AGC_163 | La imagen está algo borrosa, pero sí hay una línea divisoria entre las dos | El triángulo tiene orilla visible por sus tres lados |
| AGC_137, lado este | El contorno sigue la división de las terrazas y la corta un poco; lo considera un error mínimo. Envió una imagen más cercana | En esa imagen se ve que el lado este es un trazo recto que atraviesa una de las terrazas y deja dentro algunos árboles y matorral. Borde aproximado |
| AGC_164, línea en la parte alta | Es una división real, no una sombra | Parcela con una división interna |
| AGC_148 frente a AGC_089 | No se ve nada físico con claridad por lo borroso, pero aparece la división como un caminito | Se tratan como dos campos distintos |
| La casa pequeña | Estaba en AGC_047 | Coincide con la construcción vista en la imagen |

**Diferencia de apreciación anotada:** para AGC_137, Jass ve el corte como mínimo; en la imagen cercana la línea atraviesa una terraza completa. Se deja como borde aproximado y se anota que el desajuste es pequeño frente a las 24.81 ha de la parcela.

### 4 de octubre de 2026 — Cierre del piloto y categorías fijadas

**Decisiones de Jass:**

1. **Se fijan cinco letras y cinco marcas.** Valen para toda la revisión. Si hubiera que cambiarlas, se recalifica lo ya revisado.
2. **AGC_137 queda en B.**

**Letras (una por parcela):**

| Letra | Definición |
|---|---|
| A | Campo agrícola y el contorno sigue la orilla visible |
| B | Campo agrícola, pero el contorno corta la orilla o deja dentro una franja ajena |
| C | Un solo contorno une campos separados entre sí por algo que no es cultivo |
| D | No parece campo agrícola |
| E | No se puede decidir con esta imagen |

**Marcas de sí o no (se anotan aparte de la letra):**

| Marca | Cuándo se pone |
|---|---|
| Divisiones internas | Hay líneas, bordos o hileras que parten el campo por dentro |
| Árboles dentro | Hay árboles o arbustos dentro del contorno |
| Construcción dentro | Hay casa, corral o bodega dentro |
| Angosta o muy pequeña | Menos de unos 40 m de ancho o menos de 1 ha |
| Imagen poco clara | La imagen está borrosa o con sombra |

**Cambio respecto a las categorías iniciales y su motivo.** Las letras A a E del inicio mezclaban dos preguntas: si el borde coincide y qué hay dentro. El piloto mostró parcelas con buen borde y algo que anotar por dentro (AGC_001). Además, «abarca varios campos» no distinguía un campo con divisiones internas (AGC_046) de varios campos separados por arbolado (AGC_182). Por eso C se redefinió y lo de dentro pasó a las marcas.

**Resultado del piloto (10 parcelas):** A, ocho (AGC_001, 046, 047, 091, 115, 148, 157 y 164); B, una (AGC_137); C, una (AGC_182); D y E, ninguna. El detalle está en `revision_contornos/revision_contornos.csv`.

**Qué significa y qué no.** Las 10 se eligieron por ser casos raros, no al azar: el resultado no es una proporción válida para las 197.

### 4 de octubre de 2026 — Exportación automática de las 197 parcelas

**Decisión de Jass:** revisar las 197 parcelas, usando la exportación automática de QGIS en lugar de capturar a mano. Motivo: la respuesta general ya la dio el piloto, pero el dato por parcela sirve para el catálogo, para el análisis satelital y para las 59 reservadas.

**Cómo se hizo (Atlas de QGIS):**

- Composición de impresión llamada `atlas_parcelas`, con un mapa que ocupa toda la hoja.
- Atlas activado con capa de cobertura `Parcelas_Reto_AGC_CONJUNTO`, nombre de página `ID_POLIGON` y nombre de archivo `"ID_POLIGON" || '_esri'`.
- Mapa «controlado por atlas», con margen del 40 % alrededor de cada parcela.
- Exportación como imágenes JPG a 100 ppp (1169 × 826 píxeles, calidad 90 %), con archivo de georreferenciación.
- QGIS mostró un aviso sobre capas que vienen de internet; es solo informativo.
- Jass ordenó después las imágenes en una carpeta por parcela.

**Comprobado:** hay 197 imágenes y 197 archivos `.jgw`, una por cada ID de AGC_001 a AGC_197, sin faltantes. Ninguna salió con el fondo en blanco.

### 4 de octubre de 2026 — Primera pasada sobre las 197 imágenes

**Qué se hizo.** Se miraron las 197 imágenes del Atlas, una por una, y a cada parcela se le puso letra, marcas y una nota. Las 10 del piloto conservan su calificación confirmada. Las otras 187 quedan como **primera pasada provisional**: se hicieron sobre una imagen fija, sin poder acercarse, y sin consultar el rendimiento.

**Resultado provisional (197 parcelas):**

| Letra | Parcelas |
|---|---:|
| A: campo agrícola y el contorno sigue la orilla | 176 |
| B: campo agrícola, pero el contorno corta la orilla o deja dentro algo ajeno | 10 |
| C: un contorno une campos separados | 10 |
| D: no parece campo agrícola | 0 |
| E: no se puede decidir | 1 |

| Marca | Parcelas |
|---|---:|
| Divisiones internas | 106 |
| Árboles dentro | 70 |
| Angosta o muy pequeña | 16 |
| Construcción dentro | 8 |
| Imagen poco clara | 4 |

**Parcelas que no quedaron en A:**

- **B:** AGC_004, 084, 098, 112, 129, 137, 156, 173, 183 y 186.
- **C:** AGC_049, 055, 134, 142, 149, 152, 167, 182, 188 y 191.
- **E:** AGC_127 (un claro dentro del bosque; no se distingue si es cultivo).

**Por escritura** (dato del shapefile, no del rendimiento): `Cebada`, 45 en A y 5 en B; `CEBADA`, 131 en A, 5 en B, 10 en C y 1 en E. **Por conjunto:** entrenamiento, 127 en A, 5 en B, 5 en C y 1 en E; predicción, 49 en A, 5 en B y 5 en C.

**Lo que se observa, todavía provisional:**

- Ninguna parcela cae sobre un pueblo, un cuerpo de agua o monte cerrado. La única duda de fondo es AGC_127.
- **Sobre la sospecha de los contornos simples:** en la escritura `Cebada`, tres de los cuadriláteros (AGC_004, 173 y 183) dejan dentro construcciones o un estanque. Son pocos casos, pero es el tipo de error que se esperaba de un trazo simple. Los problemas de `CEBADA` son de otro tipo: contornos muy detallados que unen varios campos (las 10 en C son todas `CEBADA`).
- Más de la mitad de las parcelas tiene divisiones por dentro y más de un tercio tiene árboles dentro. Es la condición normal de la zona, no una excepción.
- En varias parcelas se ven hileras regulares de puntos oscuros (por ejemplo AGC_072, 077, 088, 132 y 133). No se sabe qué son: podrían ser una plantación joven, magueyes o pacas.
- AGC_187 y AGC_196 están junto a un parque de paneles solares.
- En la zona de El Paredón la imagen muestra campos verdes y encharcados; en Calpulalpan, rastrojo seco. Son fechas distintas.

**Dos detalles del trazo comprobados en las coordenadas del shapefile:**

- **AGC_110** tiene un brazo muy delgado, de dos líneas casi encimadas, que corre pegado al borde de AGC_106 (a cerca de 1 m). No se enciman, pero parece un defecto del trazo.
- **AGC_112** tiene un corte delgado desde su borde este que deja fuera un recuadro pequeño.

**Límites de esta pasada:**

- Es una lectura sobre imagen fija; lo fino solo se ve acercándose en QGIS.
- La imagen no tiene fecha conocida.
- La marca «divisiones internas» es la menos firme: a veces no se distingue un bordo de una huella de maquinaria.
- La diferencia entre B y C, y entre C y «A con divisiones», depende de si lo que separa es o no cultivo; por eso casi todas las B y C están marcadas para confirmar.

**Pendiente:** 54 parcelas tienen `confirmar_en_qgis = si` en la tabla. Son las B, las C, la E y las A con algo dudoso.

### 4 de octubre de 2026 — Primeras confirmaciones de Jass en QGIS

Jass revisó en QGIS 11 parcelas de la primera pasada: las nueve B nuevas, la E y AGC_110.

| Parcela | Primera pasada | Lo que vio Jass | Queda |
|---|---|---|---|
| AGC_004 | B | En la parte sur hay un patio con casas | B |
| AGC_084 | B | Terreno muy irregular; observaciones correctas | B |
| AGC_098 | B | El contorno deja fuera un brazo de árboles, pero otro brazo delgado queda dentro. Envió imagen | B |
| AGC_112 | B | El recuadro pequeño queda bien excluido; a la derecha se ve algo como un patio, sin distinguir qué es | B |
| AGC_129 | B | El contorno no entra al bosque: cae justo en el límite donde empieza | **A** |
| AGC_156 | B | Una línea lo cruza por completo y queda dentro | B |
| AGC_173 | B | Se ve un recuadro con casas | B |
| AGC_183 | B | Observaciones correctas (estanque y estructura dentro) | B |
| AGC_186 | B | Franja oscura dentro; no distingue si es agua. Forma irregular; el contorno parece cortar el terreno | B |
| AGC_127 | E | Sí se distingue cultivo, pero el área trazada incluye árboles | **B** |
| AGC_110 | A | El brazo delgado parece un defecto del trazo | A |

**Dos correcciones a la primera pasada:**

- **AGC_129** pasó de B a A. Sobre la imagen fija parecía entrar al bosque; de cerca se ve que sigue su orilla.
- **AGC_127** pasó de E a B. Sobre la imagen fija no se distinguía el cultivo; de cerca sí. Se puso B, y no A con la marca de árboles, porque lo que queda dentro es arbolado del bosque vecino y no hileras propias del campo. Esta lectura la propuso la guía; Jass puede cambiarla.

**Pendiente de AGC_112:** queda en B por el patio, pero no se sabe qué es. Si resulta ser parte del campo, pasaría a A.

**Totales después de estas confirmaciones:** A, 177; B, 10; C, 10; D, 0; E, 0. Confirmadas en QGIS: 21 (las 10 del piloto y estas 11). Por confirmar: 43 (9 en C y 34 en A).

**Lo que enseñan estas 11:** la primera pasada acertó la letra en 9 de 11. Los dos cambios fueron por detalle fino en la orilla del bosque, justo lo que una imagen fija no deja ver.

### 5 de octubre de 2026 — Confirmación de las parcelas en C

Jass revisó en QGIS las nueve parcelas que la primera pasada había puesto en C (AGC_049, 055, 134, 142, 149, 152, 167, 188 y 191). Comprobó visualmente cada una y confirmó las notas, sin cambios ni observaciones nuevas.

**Queda confirmado:** las 10 parcelas en C (estas nueve y AGC_182, del piloto) son contornos que unen bajo un solo ID varios campos separados entre sí por algo que no es cultivo.

- Las 10 son de la escritura `CEBADA`.
- Siete están en Chignahuapan, dos en Almoloya y una en Cuautepec de Hinojosa.
- Cinco son de entrenamiento (AGC_049, 055, 134, 152 y 167) y cinco de predicción (AGC_142, 149, 182, 188 y 191).

**Totales:** A, 177; B, 10; C, 10; D, 0; E, 0. Confirmadas en QGIS: 30. Con primera pasada sin confirmar: 167, de las cuales 34 están marcadas con alguna duda menor; todas en A.

**Por qué importa para pasos posteriores:** en estas 10 parcelas un solo rendimiento describe varios campos, y sus índices satelitales promedian campos distintos junto con las orillas de arbolado que los separan.

### 5 de octubre de 2026 — Últimas confirmaciones y cierre de la revisión

**Decisión de Jass:** de las 34 parcelas en A con duda menor, revisar en QGIS solo las siete que podían cambiar de letra, y dejar las demás como primera pasada.

| Parcela | Duda | Lo que vio Jass | Queda |
|---|---|---|---|
| AGC_021 | Un camino la cruza | Sí la cruza un camino | **B** |
| AGC_109 | Un camino la cruza | Sí la cruza un camino | **B** |
| AGC_011 | Una cárcava o arroyo la cruza | La imagen no permite confirmarlo | A, sin confirmar |
| AGC_090 | Un canal o arroyo la cruza | La imagen no permite confirmarlo | A, sin confirmar |
| AGC_016 | Estructura pequeña en el centro | Observación confirmada | A, con marca de construcción |
| AGC_034 | Construcción entre árboles, al norte | Observación confirmada | A, con marcas de construcción y árboles |
| AGC_080 | Estructura circular dentro | Observación confirmada | A, con marca de construcción |

**Criterios aplicados, para que la tabla sea pareja:**

- **Camino que cruza y queda dentro: B.** Es el mismo criterio de AGC_156. Por eso AGC_021 y AGC_109 pasan a B. La regla la aplicó la guía a partir de lo que Jass confirmó; Jass puede revertirla.
- **Estructura pequeña dentro de un campo: A con la marca.** Es el mismo criterio de AGC_047 en el piloto. Se reserva B para predios con casas, bodegas o estanque (AGC_004, 173 y 183).
- **Lo que no se pudo confirmar se queda como estaba** y se le añade la marca de imagen poco clara.

**AGC_127:** Jass decidió dejarla en B.

**Totales finales de la revisión:**

| Letra | Parcelas |
|---|---:|
| A | 175 |
| B | 12 |
| C | 10 |
| D | 0 |
| E | 0 |

**Firmeza de cada calificación** (columna `etapa` de la tabla): 35 confirmadas en QGIS (10 del piloto y 25 después), 2 revisadas en QGIS sin poder confirmar y 160 con primera pasada sobre imagen fija. Todas las B y las C están confirmadas en QGIS. Quedan 27 parcelas en A con `confirmar_en_qgis = si`: tienen alguna duda menor que no se revisó.

### 5 de octubre de 2026 — Cierre

Jass dio por terminada la exploración y pidió el informe. Se escribió `informe_contornos_sobre_campo_real.md` con la respuesta, el método, los hallazgos, los límites y lo que queda sin resolver, y se anotó el cierre en el registro de decisiones local de Jass.

## Decisiones todavía abiertas

- Qué cuenta como «campo agrícola real» y si hace falta una imagen de 2025 para las dudosas.
- Si la comprobación de municipio se deja como está (muestra con capturas más vista por municipio de las 197) o se completa con los límites municipales oficiales.
