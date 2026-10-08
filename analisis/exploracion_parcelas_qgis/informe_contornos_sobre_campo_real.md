# Informe: ¿cada contorno cae sobre un campo agrícola real?

**Responsable: Jass. Revisión previa a la tarea T02 (catálogo y etiquetas).** Trabajo realizado el 4 y 5 de octubre de 2026. Este informe cierra la exploración; el detalle de cada momento está en la [bitácora](bitacora.md) de esta carpeta y la calificación de cada parcela en [revision_contornos/revision_contornos.csv](revision_contornos/revision_contornos.csv).

No se entrenó ningún modelo, no se consultó el rendimiento de las parcelas y no se modificó ningún archivo original del dataset.

---

## 1. Respuesta

**Sí: los 197 contornos caen sobre tierra de cultivo.** Ninguno cae sobre un pueblo, un cuerpo de agua o monte cerrado.

Pero no todos describen bien su campo:

| Situación | Parcelas | Proporción |
|---|---:|---:|
| **A.** El contorno sigue la orilla visible del campo | 175 | 89 % |
| **B.** Es campo agrícola, pero el contorno corta la orilla o deja dentro algo ajeno | 12 | 6 % |
| **C.** Un solo contorno une campos separados entre sí por algo que no es cultivo | 10 | 5 % |
| **D.** No parece campo agrícola | 0 | — |
| **E.** No se puede decidir | 0 | — |

**Qué significa «campo agrícola» aquí:** que en la imagen se ve tierra trabajada (surcos, rastrojo, huellas de cosecha, tono parejo). **No significa** que lo sembrado fuera cebada, ni que estuviera sembrado en 2025: eso una imagen sin fecha no lo puede decir (ver sección 6).

---

## 2. Cómo se hizo

1. **Preparación.** Se instaló QGIS 3.44 (versión estable) y se creó el proyecto `proyecto_qgis/contornos_sobre_imagen.qgz`.
2. **Carga y comprobación del shapefile.** 197 contornos, seis columnas, acentos legibles, sistema de coordenadas WGS84. Coincide con la auditoría previa de archivos.
3. **Comprobación de ubicación.** Sobre OpenStreetMap, por muestra (15 capturas), y con una vista de las 197 pintadas por municipio. Los nueve conteos municipales coinciden con la auditoría y cada municipio forma un grupo coherente.
4. **Imagen de fondo.** Esri World Imagery, una imagen satelital pública de alta resolución.
5. **Piloto de 10 parcelas**, elegidas por ser las más raras (la más chica, la más grande, el único triángulo, la más irregular…). Sirvió para ajustar las categorías.
6. **Exportación automática** de las 197 parcelas con el Atlas de QGIS, todas con el mismo encuadre.
7. **Primera pasada** sobre las 197 imágenes, poniendo a cada parcela una letra, cinco marcas y una nota.
8. **Confirmación en QGIS**, acercándose, de las parcelas donde la letra podía cambiar.

**Reglas que se siguieron:**

- **Sin ver el rendimiento.** No se cargó el CSV de rendimiento en el proyecto ni se consultó al calificar, para que saber cuánto rindió una parcela no influyera en su calificación.
- **Categorías fijadas después del piloto** y aplicadas igual a todas.
- **El shapefile original no se tocó.** Todo lo anotado está en una tabla aparte.

**Las cinco marcas**, que se anotan aparte de la letra:

| Marca | Cuándo se pone | Parcelas |
|---|---|---:|
| Divisiones internas | Hay líneas, bordos o hileras que parten el campo por dentro | 107 |
| Árboles dentro | Hay árboles o arbustos dentro del contorno | 70 |
| Angosta o muy pequeña | Menos de unos 40 m de ancho o menos de 1 ha | 16 |
| Construcción dentro | Hay casa, corral, bodega o estructura dentro | 8 |
| Imagen poco clara | La imagen está borrosa o no deja confirmar | 6 |

---

## 3. Qué tan firme es cada calificación

No todas las parcelas se revisaron con el mismo detalle. La columna `etapa` de la tabla lo indica.

| Nivel | Parcelas | Qué significa |
|---|---:|---|
| Confirmada en QGIS | 35 | Jass la miró de cerca en QGIS y confirmó o corrigió |
| Revisada en QGIS sin poder confirmar | 2 | Se miró de cerca, pero la imagen no dejó decidir (AGC_011 y AGC_090) |
| Primera pasada sobre imagen fija | 160 | Calificada sobre la imagen exportada, sin acercarse |

- **Todas las B y todas las C están confirmadas en QGIS.**
- Las 160 de primera pasada están todas en A. De ellas, 27 tienen `confirmar_en_qgis = si`: una duda menor que no se revisó.
- **Qué tan confiable fue la primera pasada:** en las 27 parcelas que después se revisaron en QGIS, la letra cambió en 4. Dos subieron de A a B (AGC_021 y AGC_109, por un camino que las cruza), una bajó de B a A (AGC_129) y una pasó de E a B (AGC_127). No es una muestra al azar: se revisaron justo las dudosas, así que entre las no revisadas se espera menos cambio, pero no cero.

---

## 4. Hallazgos

### 4.1 Las parcelas en B (12)

| Parcela | Municipio | Qué deja dentro o corta |
|---|---|---|
| AGC_004 | Calpulalpan | Un patio con casas en la parte sur |
| AGC_173 | Calpulalpan | Un recuadro con casas o bodegas en la esquina noreste |
| AGC_183 | Calpulalpan | Un estanque y una estructura; muchos árboles |
| AGC_112 | Calpulalpan | Algo que parece un patio; no se distingue qué es |
| AGC_098 | Calpulalpan | Un brazo delgado de arbolado de barranca |
| AGC_021 | Chignahuapan | Un camino que la cruza |
| AGC_109 | Chignahuapan | Un camino que la cruza |
| AGC_186 | Chignahuapan | Una franja oscura a lo largo (agua o terreno encharcado); el contorno corta el terreno |
| AGC_127 | Chignahuapan | Árboles del bosque vecino; es un claro de menos de 1 ha |
| AGC_084 | Almoloya | Terrazas con matorral; terreno muy irregular |
| AGC_137 | Almoloya | El lado este atraviesa una terraza; desajuste pequeño frente a 24.81 ha |
| AGC_156 | Singuilucan | Una carretera o camino ancho que la cruza en diagonal |

### 4.2 Las parcelas en C (10)

AGC_049, 055, 134, 142, 149, 152, 167, 182, 188 y 191.

- Las 10 son de la escritura `CEBADA`.
- Siete están en Chignahuapan, dos en Almoloya y una en Cuautepec de Hinojosa.
- Nueve miden menos de 5 ha; la excepción es AGC_149 (8.99 ha).
- En todas, un solo ID y un solo rendimiento describen varios campos separados por arbolado, barranca o camino.

### 4.3 La sospecha de los contornos simples

Al auditar los archivos del shapefile se vio que el campo `Cultivo` tiene dos escrituras, `Cebada` (50 parcelas) y `CEBADA` (147), y que se dibujan distinto: los contornos de `Cebada` tienen una mediana de 5 puntos y los de `CEBADA`, de 34. De ahí salió una sospecha: los contornos de la escritura `Cebada`, dibujados con muy pocos puntos, podrían ser croquis que no coinciden con el campo.

**Resultado: la sospecha se sostiene solo en parte.**

- De las 29 parcelas con cinco puntos o menos (cuadriláteros y un triángulo), **26 quedaron en A**: en esas zonas los campos son rectos y cuatro puntos bastan para dibujarlos bien.
- **Tres quedaron en B** (AGC_004, 173 y 183), y las tres por lo mismo: el cuadrilátero incluye casas, bodegas o un estanque. Es el error que se esperaba de un trazo simple, pero ocurre en pocos casos.

**Cada escritura falla de una manera distinta:**

| Escritura | Parcelas | En A | En B | En C | Cómo falla |
|---|---:|---:|---:|---:|---|
| `Cebada` | 50 | 45 | 5 | 0 | Trazo simple que a veces incluye algo ajeno |
| `CEBADA` | 147 | 130 | 7 | 10 | Trazo muy detallado que a veces une varios campos |

Esto no prueba que haya dos fuentes de captura; es compatible con esa hipótesis, que sigue sin confirmarse.

### 4.4 Lo que hay dentro de los campos

- **Más de la mitad de las parcelas (107) tiene divisiones internas** y **más de un tercio (70) tiene árboles dentro**. Bordos, terrazas e hileras de árboles o arbustos son la condición normal de la zona, no una excepción.
- **16 parcelas son angostas o muy pequeñas.** Entre ellas hay cuatro franjas paralelas de unos 30 m de ancho en El Paredón (AGC_062, 073, 115 y 139).
- En varias parcelas se ven **hileras regulares de puntos oscuros** (por ejemplo AGC_072, 077, 088, 132 y 133). No se sabe qué son: podrían ser una plantación joven, magueyes o pacas.

### 4.5 Las 59 parcelas reservadas

De las 59 reservadas, 50 están en A, 4 en B y 5 en C. De las 138 de entrenamiento, 125 en A, 8 en B y 5 en C. **No se ve que las reservadas tengan contornos peores ni mejores** que las de entrenamiento.

### 4.6 Detalles del trazo

- **AGC_110** tiene un brazo muy delgado, de dos líneas casi encimadas, que corre pegado al borde de AGC_106 (a cerca de 1 m). Comprobado en las coordenadas del shapefile. No se enciman; parece un defecto del dibujo.
- **AGC_112** tiene un corte delgado que deja fuera un recuadro pequeño. Es intencional y está bien hecho.
- Las parcelas que se ven «pegadas» no se tocan: entre ellas hay un camino o un pasillo (por ejemplo AGC_164, 170 y 023; AGC_148 y 089).

### 4.7 Ubicación

- Los nueve municipios forman grupos coherentes; ninguna parcela aparece dentro del grupo de otro municipio.
- AGC_164 (Apan, Hidalgo), AGC_170 y AGC_023 (Calpulalpan, Tlaxcala) están juntas sobre el límite entre los dos estados.
- **Sospecha para el paso de relieve:** las cinco parcelas con relieve incompleto (AGC_020, 023, 044, 164 y 170) están todas en esa franja fronteriza o en el municipio vecino. El mapa de relieve podría tener un hueco a lo largo del límite estatal. En esta exploración las cinco quedaron en A: su problema no es el contorno.

---

## 5. Lo que este paso deja para los siguientes

**Para el catálogo y la auditoría de la etiqueta (T02):**

- Una columna de calidad de contorno por parcela (letra y marcas), lista para unirse al catálogo por `ID_POLIGON`.
- En las 10 parcelas en C, el rendimiento es un solo número para varios campos.
- **El cruce entre categoría y rendimiento todavía no se ha hecho.** Se dejó para después a propósito. Como las categorías se pusieron sin ver el rendimiento, ese cruce será una comprobación limpia.

**Para el análisis satelital (T06):**

- Los índices de una parcela son el promedio de todo lo que hay dentro del contorno. En 96 de las 197 parcelas hay algo que no es cultivo o que mezcla señal: están en B o C, o tienen árboles o construcción dentro, o son angostas. Las otras 101 están en A sin ninguna de esas marcas.
- En las parcelas angostas o muy pequeñas casi todos los píxeles de Sentinel-2 (10 m) son de orilla.
- Esto ayuda a leer la desviación estándar dentro de la parcela: una parcela con árboles tendrá dispersión alta por lo que contiene, no por el estado del cultivo.

**Para el relieve (T05):** la sospecha del hueco en el límite estatal (4.7).

---

## 6. Límites de esta exploración

- **La imagen no tiene fecha conocida** y no es de una sola fecha: en El Paredón se ven campos verdes y encharcados, y en Calpulalpan, rastrojo seco. Sirve para ver el terreno, no para saber qué había sembrado en la campaña de 2025.
- **No se sabe si es cebada.** Desde la imagen se distingue tierra de cultivo, no el cultivo.
- **160 parcelas tienen solo primera pasada**, sobre imagen fija. Lo fino solo se ve acercándose.
- **La marca de divisiones internas es la menos firme:** a veces no se distingue un bordo de una huella de maquinaria.
- **El municipio de cada parcela no se comprobó contra los límites oficiales**; solo se comprobó que los grupos son coherentes.
- **No se revisó el dueño ni el productor** de cada parcela; una imagen no lo muestra.
- Algunos rendimientos ya se conocían por documentos anteriores (AGC_001, AGC_046 y nueve parcelas de rendimiento extremo identificadas en una auditoría previa). No se consultaron al calificar, pero no se pueden olvidar.

---

## 7. Lo que quedó sin resolver

1. Qué es el patio de AGC_112. Si resulta ser parte del campo, pasaría a A.
2. Si AGC_011 y AGC_090 están cruzadas por un arroyo o canal.
3. Qué son las hileras de puntos oscuros.
4. Si la franja oscura de AGC_186 es agua.
5. Las 27 parcelas en A con duda menor sin revisar.
6. Una imagen con fecha de 2025 (por ejemplo Sentinel-2) para las 22 parcelas en B y C. No se hizo; queda como opción.

---

## 8. Dónde está la evidencia

| Qué | Dónde |
|---|---|
| Calificación de las 197 parcelas | `revision_contornos/revision_contornos.csv` |
| Bitácora completa, con cada decisión y su motivo | `bitacora.md` |
| Imagen de cada parcela (197) | `capturas_parcelas_atlas/AGC_###/` |
| Imágenes del piloto (10 parcelas, 17 imágenes) | `capturas_parcelas/AGC_###/` |
| Capturas de la comprobación de ubicación (15) | `capturas_comprobacion_ubicacion/openStreetMap/` |
| Proyecto de QGIS, con las dos vistas y el Atlas | `proyecto_qgis/contornos_sobre_imagen.qgz` (leer antes `proyecto_qgis/LEEME.md`) |

**Para repetir la exportación:** abrir el proyecto, entrar a Proyecto → Composiciones → `atlas_parcelas` y usar Atlas → Exportar atlas como imágenes.

**Columnas de la tabla:** `ID_POLIGON`, `categoria` (A, B o C), cinco marcas de sí o no, `nota`, `etapa` (qué tan firme es), `confirmar_en_qgis` y `fecha_revision`. La tabla no contiene el rendimiento.

**Límite de reproducibilidad:** los conteos de este informe se calcularon uniendo la tabla con el shapefile original en un entorno temporal. No se guardó un script.
