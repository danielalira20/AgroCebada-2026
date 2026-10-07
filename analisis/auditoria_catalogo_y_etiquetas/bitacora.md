# Bitácora de la auditoría del catálogo y de las etiquetas de rendimiento

> **Nota para el equipo.** Esta es la bitácora de trabajo completa, en orden cronológico: qué se hizo en cada etapa, qué se decidió y por qué. Para el resultado, lee primero el [README](README.md) y el [informe](informe_catalogo_y_etiquetas.md). La bitácora menciona documentos de trabajo locales de Jass (auditorías previas del dataset y un registro de decisiones) que no están en este repositorio: lo necesario de ellos está resumido aquí o en el informe. «La carpeta local» es la carpeta de trabajo de Jass, donde se mantiene el original de esta auditoría. Las comprobaciones marcadas como «hechas solo en la carpeta local» quedan como constancia: no se pueden repetir desde el repositorio ni hace falta, porque todo lo que está en `tablas/` se regenera con los scripts.

**Objetivo:** construir el padrón confiable de las 197 parcelas y dejar auditada la etiqueta de rendimiento, de modo que otra persona pueda rehacerlo todo desde los archivos originales y obtenga lo mismo.

Corresponde a la tarea T02 del plan del equipo (responsable: Jass; revisora: Dani). Todo lo que se produzca en esta auditoría se guarda dentro de esta carpeta.

**Estado al 6 de octubre de 2026:** plan aprobado. Etapas 0 (preparación), 1 (identidad), 2 (geometría y área), 3 (calidad de contorno), 4 (precisión y procedencia de la etiqueta), 5 (cruce de contorno y rendimiento), 6 (parcelas extremas) y 7 (soporte de las 59 reservadas) cerradas. Etapa 8 (comparación con el diagnóstico de T03) cerrada. Etapa 9 (cierre) hecha: repetición completa, [informe](informe_catalogo_y_etiquetas.md) aprobado por Jass y copia al repositorio. **Auditoría terminada;** falta solo que Jass haga los commits y el pull request.

## Preguntas que deben quedar contestadas

1. ¿Las 197 parcelas están bien identificadas y unidas 1:1 a su contorno, con 138 etiquetas y 59 ausentes?
2. ¿Con qué precisión está anotado el rendimiento, y cómo cambia según el municipio y según la escritura del campo `Cultivo` (`Cebada` / `CEBADA`)?
3. ¿La calidad del contorno (A, B, C) se relaciona con el rendimiento?
4. ¿Qué parcelas son extremas, y alguna coincide con un contorno dudoso?
5. ¿Qué tan respaldadas están las 59 parcelas reservadas por las 138 conocidas?

## Qué se espera encontrar

Casi todo se calculó ya una vez en trabajos anteriores, así que las etapas 1, 2 y 4 son sobre todo confirmación. Lo nuevo es la etapa 5, la 6 con el contexto del contorno y la 7 reunida por parcela. Para la etapa 5 lo más probable es no ver una diferencia clara, porque solo hay 12 parcelas en B y 10 en C; cualquiera de los dos resultados sirve.

## Etapas

Una a la vez. No se pasa a la siguiente sin que Jass cierre la anterior.

| # | Etapa | Qué se hace | Qué deja | Estado |
|---|---|---|---|---|
| 0 | Preparación | Abrir esta bitácora, preparar el entorno fuera de las carpetas del proyecto, comprobar que los 168 archivos originales siguen intactos y escribir el diccionario de columnas antes de calcular | Bitácora y [diccionario de columnas](diccionario_columnas.md) | **Hecha** |
| 1 | Identidad | Unir el CSV de rendimiento con el shapefile por ID; comprobar 197 únicos, 138/59, y que conjunto y área coinciden entre ambos archivos | Catálogo base con los nombres del contrato | **Hecha** |
| 2 | Geometría y área | Validez, duplicados, solapamientos y contactos en los 19 306 pares; área geodésica frente a `area_ha_origen`; número de puntos del contorno | Columnas de geometría en el catálogo | **Hecha** |
| 3 | Calidad de contorno | Unir la tabla de revisión de contornos al catálogo | Columnas de categoría, marcas y firmeza | **Hecha** |
| 4 | Precisión y procedencia de la etiqueta | Decimales por valor, tamaño del redondeo por municipio y por escritura, valores repetidos, valores idénticos entre vecinas | Tabla de precisión por municipio | **Hecha** |
| 5 | Cruce de contorno y rendimiento | Comparar A, B y C, y las cinco marcas, contra el rendimiento, global y dentro de cada municipio | Tabla del cruce y su lectura | **Hecha** |
| 6 | Parcelas extremas | Distancia de cada parcela al promedio de las otras de su municipio; listar las extremas con contorno, área y vecinas | Lista de extremas con contexto | **Hecha** |
| 7 | Soporte de las 59 reservadas | Por parcela: etiquetas en su municipio, distancia a la conocida más cercana (centro a centro y orilla a orilla), celdas climáticas compartidas, disponibilidad satelital y de relieve, calidad de contorno | Tabla de soporte por parcela y resumen por municipio | **Hecha** |
| 8 | Comparación con el diagnóstico de T03 | Columna por columna contra `registro/t03/soporte_parcelas.csv` del repositorio, explicando cada diferencia | Tabla de diferencias | **Hecha** |
| 9 | Cierre | Repetir todo desde cero y comprobar que sale idéntico; escribir el informe; decidir qué se copia al repositorio | [Informe final](informe_catalogo_y_etiquetas.md) | **Hecha** |

## Reglas de esta auditoría

- **No se entrena ni se corre ningún modelo.** La etapa 6 usa un promedio por municipio; es análisis de datos, no un modelo.
- **Etapa 5 con regla escrita antes de mirar.** Antes de cruzar se anota aquí qué se compara y qué contaría como diferencia.
- **No se excluye ninguna parcela.** Una parcela extrema se señala, no se elimina.
- **Etapa 8 después de la 7.** La tabla de T03 no se abre hasta que el diagnóstico propio esté cerrado.
- **Script portable.** Recibe la ruta del dataset como argumento y usa las librerías del `requirements.txt` del repositorio.
- **Cada cifra dice si es comprobada o sospecha,** y cada tabla sale de un script guardado, con su salida en archivo.
- El dataset original no se copia, no se mueve y no se modifica.
- Nombres de archivos y carpetas: dicen lo que contienen, en minúsculas, con guion bajo, sin espacios ni acentos, sin nombres de persona ni la palabra «paso». Las subcarpetas se crean cuando se necesitan.

## Qué no entra

- Entrenar o comparar modelos, ni las referencias de T08.
- Extraer el relieve (es T05). En la etapa 7 se usa la cobertura ya calculada, marcada como provisional.
- La revisión de T03.
- Verificar el municipio contra los límites oficiales del INEGI y contrastar el rendimiento con el SIAP 2025. Quedan anotados como pendientes posibles, fuera de esta auditoría.

## Decisiones de Jass

| Decisión | Motivo |
|---|---|
| El diagnóstico de soporte se hace de forma independiente y después se compara con el de T03. | No guiarse por un resultado ajeno: construir con la evidencia propia y comparar al final. |
| La revisión de T03 queda fuera de este trabajo. | T03 todavía se declara «en revisión» en sus propios documentos. |
| Las columnas usan los nombres del contrato de datos del repositorio (`id_parcela`, `area_ha_origen`, `rendimiento_t_ha`, `conjunto_origen`, `municipio`). La escritura del campo `Cultivo` se guarda como `cultivo_origen`. | El plan pide que T02 use el contrato. `cultivo_origen` solo dice cómo venía escrito, sin afirmar cómo se registró. |
| Todo lo que se haga se incluye en lo que recibe la revisora. | Que esté enterada de todo lo realizado. |
| Las distancias se calculan con el método geodésico. No se promedian métodos. El catálogo lleva dos distancias: centro a centro y orilla a orilla. | El geodésico mide sobre la curvatura de la Tierra, sin la deformación de un mapa plano. Un promedio de métodos no se puede reproducir. En parcelas grandes el centro queda lejos de la orilla. |
| El script de la auditoría anota la huella (SHA-256) de cada archivo original que lee, en `tablas/huellas_archivos_leidos.csv`. El archivo `auditoria_paso2.json` de la carpeta local no se copia al repositorio. | Que la revisora pueda comprobar que partió de los mismos datos. El JSON local quedaría sin el script ni los documentos que lo explican. |
| Al terminar cada etapa se entrega un informe de cierre en lenguaje sencillo: qué se esperaba, qué se hizo, qué se comprobó y qué quedó pendiente. | Poder seguir y entender lo que se hizo en cada etapa. |
| El rendimiento va como columna del catálogo en la carpeta local y también en la copia del repositorio. | El contrato lo pide como columna. |
| Las celdas climáticas de la etapa 7 se recalculan en el script de esta auditoría con el mismo método ya usado (cruce del contorno con la cuadrícula, por área) y el resultado se compara contra el de una auditoría previa del dataset (trabajo local). | Recalcular no las hace más precisas, pero permite rehacer todo desde los originales con un solo script; la comparación sirve de doble verificación. Basta un mapa, porque los 21 comparten la cuadrícula. |
| Esta auditoría vive en `auditoria_catalogo_y_etiquetas/`, en la raíz de la carpeta local; su copia en el repositorio va en `analisis/auditoria_catalogo_y_etiquetas/`. Rama: `feature/auditoria-catalogo-y-etiquetas`. | Misma lógica que la exploración de parcelas en QGIS. |

## Bitácora

### 5 de octubre de 2026 — Auditoría previa y plan

- Se auditaron la carpeta local y el repositorio del equipo, solo en lectura. No se ejecutó ningún script del proyecto.
- Se ubicó la evidencia que ya existía para esta tarea en documentos de trabajo locales de Jass (un catálogo y unas relaciones entre parcelas calculados antes, cifras adelantadas en un registro de decisiones y scripts de una auditoría previa) y la tabla de revisión de contornos.
- En el repositorio, T03 (Migue) ya incluye un diagnóstico de soporte de las 59 frente a las 138 y una unión propia del CSV con el shapefile. No se usa como punto de partida (ver decisiones).
- Jass aprobó el plan de diez etapas y tomó las decisiones de la tabla de arriba.
- Jass creó esta carpeta, su par en el repositorio y la rama.

### 5 de octubre de 2026 — Preparación (etapa 0)

**Entorno de cálculo.** Se preparó fuera de las carpetas del proyecto, en un espacio temporal de Linux que se borra al terminar la sesión de trabajo. Python 3.12.15 con las dependencias del `requirements.txt` de la rama `main` del repositorio, instaladas tal como están fijadas: pandas 3.0.6, numpy 2.2.6, shapely 2.1.2, pyproj 3.8.0, geopandas 1.2.0, pyogrio 0.13.0, rasterio 1.4.4, scipy 1.18.1 y scikit-learn 1.9.1. Es el mismo entorno que usará la revisora. No se instaló nada en la carpeta del proyecto.

**Comprobado: los originales siguen intactos.** Se calculó la huella SHA-256 de los 168 archivos del dataset y se comparó con las huellas guardadas el 3 de octubre en una auditoría previa del dataset (archivo de trabajo local `auditoria_paso2.json`). Resultado: 168 de 168 idénticos; no falta ni sobra ninguno.

**Límite:** el pequeño programa de esta comprobación no se guardó en la carpeta, porque depende de un archivo de huellas que solo existe en la carpeta local. Propuesta para la etapa 1: que el script de la auditoría anote por sí mismo la huella de cada archivo que lee, para que la revisora pueda comprobar que partió de los mismos datos.

**Diccionario de columnas.** Se escribió [diccionario_columnas.md](diccionario_columnas.md) con las reglas comunes, la correspondencia de nombres entre archivos y las columnas del catálogo para las etapas 1 a 4. Las demás tablas quedan listadas y se detallan al llegar a su etapa. **Jass lo aprobó el 5 de octubre**, con lo que la etapa 0 queda cerrada.

**Decisión de Jass:** recalcular las celdas climáticas con el mismo método y comparar (ver la tabla de decisiones).

**No se hizo:** no se leyó el rendimiento, no se calculó ninguna tabla y no se modificó ningún archivo existente fuera de esta carpeta.

### 5 de octubre de 2026 — Identidad (etapa 1)

**Pregunta:** ¿las 197 parcelas están bien identificadas y unidas una a una con su contorno, con 138 etiquetas y 59 ausentes?

**Qué se esperaba:** que todo coincidiera, porque esta unión ya se había comprobado dos veces en trabajos anteriores. La sorpresa habría sido cualquier diferencia.

**Qué se hizo.** Se escribió `scripts/construir_catalogo.py`. Lee el CSV de rendimiento y el shapefile, los une por identificador (nunca por número de fila), hace 25 comprobaciones y escribe tres tablas en `tablas/`:

| Archivo | Contenido |
|---|---|
| `catalogo_parcelas.csv` | 197 filas y 7 columnas: `id_parcela`, `conjunto_origen`, `rendimiento_t_ha`, `area_ha_origen`, `municipio`, `estado`, `cultivo_origen` |
| `comprobaciones_catalogo.csv` | Cada comprobación con lo esperado, lo obtenido y si se cumple |
| `huellas_archivos_leidos.csv` | Huella SHA-256 de los seis archivos originales leídos |

**Comprobado (25 de 25 comprobaciones se cumplen):**

- El CSV tiene 197 filas y el shapefile 197 contornos; en ambos los identificadores son AGC_001 a AGC_197, sin repetir.
- Ningún identificador está en un archivo y falta en el otro. La unión empareja las 197 una a una.
- El conjunto y el área, que vienen repetidos en los dos archivos, coinciden en las 197 parcelas.
- 138 parcelas tienen rendimiento y 59 no; las 138 son exactamente las de ENTRENAMIENTO y las 59 las de PREDICCION.
- Los 138 rendimientos son números mayores que cero. Las 197 áreas también.
- El shapefile no tiene celdas vacías. La coma de sobra del CSV solo crea una columna vacía.
- El rendimiento y el área quedaron en el catálogo con el mismo texto del archivo original, sin redondear.

**Conteos:** Puebla 100 (71 conocidas y 29 reservadas), Hidalgo 51 (36 y 15), Tlaxcala 46 (31 y 15). Por municipio: Chignahuapan 100, Calpulalpan 44, Singuilucan 23, Almoloya 14, Cuautepec de Hinojosa 9, Emiliano Zapata 3, Nanacamilpa de Mariano Arista 2, Apan 1 y Tepeapulco 1. Por escritura: `CEBADA` 147 y `Cebada` 50; cada municipio tiene una sola escritura. Coinciden con una auditoría previa.

**Comprobaciones adicionales, hechas solo en la carpeta local:**

- El catálogo coincide parcela por parcela con el catálogo previo de una auditoría previa del dataset (archivo de trabajo local `catalogo_parcelas.json`) (conjunto, área, municipio, estado, escritura y si tiene etiqueta): 0 diferencias en 197.
- Las huellas de los seis archivos leídos son las mismas que se guardaron el 3 de octubre.
- Se corrió el script una segunda vez, leyendo la copia del dataset que está en `data/` del repositorio y escribiendo fuera del proyecto: las tres tablas salieron idénticas byte a byte.

**Límites:**

- Esta etapa comprueba que los archivos concuerdan entre sí. No comprueba que el municipio declarado sea el correcto ni cómo se midió el rendimiento.
- El script lee el shapefile de la carpeta descomprimida, no del `.zip`.
- El rendimiento se leyó para copiarlo al catálogo y contar cuántos hay; no se analizó.

**No se hizo:** no se entrenó ningún modelo, no se modificó ningún archivo original y no se abrió la tabla de T03.

**Jass cerró la etapa 1 el 5 de octubre.**

### 5 de octubre de 2026 — Geometría y área (etapa 2)

**Pregunta:** ¿los 197 contornos están bien formados, su superficie concuerda con la registrada y ninguno está repetido o encimado con otro?

**Qué se esperaba:** contornos válidos, ningún solapamiento en los 19 306 pares y una diferencia máxima de área de 1.261 % en AGC_069, como en las auditorías anteriores.

**Qué se hizo.** Se amplió `scripts/construir_catalogo.py` con la etapa 2. El catálogo pasó de 7 a 13 columnas: `geometria_valida`, `puntos_contorno`, `area_ha_geodesica`, `diferencia_area_pct`, `centroide_lon` y `centroide_lat`. Las 7 columnas de la etapa 1 quedaron idénticas. La tabla de comprobaciones tiene ahora 53 filas (36 comprobaciones y 17 conteos informativos).

**Comprobado (las 11 comprobaciones nuevas se cumplen):**

- El shapefile declara latitud/longitud WGS84 (EPSG:4326).
- Los 197 contornos son válidos, no están vacíos, son de una sola pieza, no tienen huecos y están cerrados. Están declarados con altura, pero toda altura vale 0.
- En los 19 306 pares no hay contornos idénticos, ni encimados, ni que se toquen.
- Ninguna parcela difiere más de 2 % entre el área calculada y la registrada. La mayor diferencia es −1.261 % en AGC_069 (0.375209 ha calculadas frente a 0.38 registradas), la misma cifra de las auditorías anteriores.
- Puntos por contorno: `Cebada` 4 / 5 / 50 y `CEBADA` 5 / 34 / 145 (mínimo / mediana / máximo). Con 5 puntos o menos hay 26 en `Cebada` (25 en Calpulalpan y 1 en Emiliano Zapata) y 3 en `CEBADA` (Singuilucan). AGC_157 es la única de 4 puntos. Los 50 contornos de `Cebada` tienen coordenadas de 6 decimales; ninguno de los 147 de `CEBADA`. Coincide con una auditoría previa.

**Hallazgo nuevo 1 (comprobado): el área registrada es el área del contorno, redondeada.** En las 197 parcelas, el área calculada a partir del contorno y redondeada a dos decimales es exactamente igual al área registrada. La mayor diferencia es de 0.005 ha, es decir, el máximo que puede producir ese redondeo. Las auditorías anteriores solo habían dicho que el caso extremo era «compatible con redondeo».

- **Lo que esto indica, sin poder comprobarlo:** que el área del dataset se calculó a partir del mismo contorno y no se midió aparte en campo. No hay documento de FIRA que lo diga.
- **Consecuencias:** el área no es un dato independiente del contorno, así que si un contorno está mal trazado (categorías B y C), su área lo está en la misma medida; y sigue sin saberse qué superficie se usó como denominador del rendimiento en t/ha.
- **Unidades:** queda confirmado que `area_ha_origen` está en hectáreas.

**Hallazgo nuevo 2 (comprobado): hay parcelas prácticamente pegadas.** Ningún par se toca, pero 9 pares tienen sus orillas a menos de 1 m, 37 a menos de 5 m y 87 a menos de 20 m. El par más cercano es AGC_085 y AGC_177, a 1 cm.

| Par | Distancia entre orillas |
|---|---:|
| AGC_085 y AGC_177 | 0.01 m |
| AGC_111 y AGC_126 | 0.06 m |
| AGC_126 y AGC_135 | 0.10 m |
| AGC_021 y AGC_097 | 0.30 m |
| AGC_109 y AGC_161 | 0.54 m |
| AGC_056 y AGC_094 | 0.81 m |
| AGC_073 y AGC_115 | 0.85 m |
| AGC_014 y AGC_116 | 0.87 m |
| AGC_024 y AGC_171 | 0.92 m |

(Las distancias por par de esta tabla vienen de una auditoría previa del dataset (archivo de trabajo local `relaciones_pares.json`); el script de esta auditoría reproduce los conteos 9 / 37 / 87 y el par más cercano.) Los nueve pares son del mismo municipio.

- **Lo que esto indica, sin poder comprobarlo:** en una separación de centímetros no cabe un camino. Podrían ser dos partes de un mismo campo registradas con dos ID, o dos campos vecinos que comparten lindero.
- **Aviso sobre un documento anterior:** el informe de la exploración en QGIS (4.6) dice que las parcelas que se ven pegadas tienen entre ellas un camino o un pasillo. Eso se vio en los ejemplos que cita (AGC_164, 170 y 023; AGC_148 y 089); para estos nueve pares no se ha revisado en la imagen.
- **Para etapas posteriores:** en la etapa 4 se verá si las parcelas pegadas tienen rendimientos idénticos; en la etapa 7 la distancia de orilla a orilla entra al diagnóstico de soporte.

**Comprobaciones adicionales, hechas solo en la carpeta local:**

- Área calculada, diferencia de área y centroide coinciden con el catálogo previo de una auditoría previa del dataset (trabajo local) en las 197 parcelas (diferencias menores a una millonésima de hectárea, que vienen del redondeo al guardar).
- Segunda corrida leyendo la copia del dataset del repositorio: las tres tablas salieron idénticas byte a byte.

**Límites:**

- Un contorno «válido» es un dibujo bien formado; no dice si coincide con el campo real. Eso lo cubre la revisión de contornos, que se une en la etapa 3.
- El centroide se calcula sobre latitud y longitud, igual que en las auditorías anteriores. En una parcela con forma de arco o muy irregular puede caer fuera del contorno.
- Los solapamientos y distancias entre orillas se miden en metros sobre una proyección plana (UTM zona 14 norte); las áreas, sobre el elipsoide.

**No se hizo:** no se analizó el rendimiento, no se entrenó ningún modelo y no se modificó ningún archivo original.

### 5 de octubre de 2026 — Revisión visual de los nueve pares pegados

Jass revisó en QGIS, sobre la imagen satelital, los nueve pares con orillas a menos de 1 m.

**Resultado: en los nueve pares se trata de dos terrenos distintos.** En todos se alcanza a ver la división entre ambos; lo que ocurre es que los contornos se trazaron muy juntos.

| Par | Lo que vio Jass |
|---|---|
| AGC_085 y AGC_177 | Se alcanza a ver la división; son dos parcelas muy juntas |
| AGC_111 y AGC_126 | Dos parcelas separadas, trazadas casi juntas |
| AGC_126 y AGC_135 | Dos parcelas totalmente distintas; a la vista los trazos parecen un poco encimados |
| AGC_021 y AGC_097 | Dos campos distintos, bastante pegados; el polígono está trazado de forma irregular |
| AGC_109 y AGC_161 | Dos parcelas distintas |
| AGC_056 y AGC_094 | Dos parcelas distintas |
| AGC_073 y AGC_115 | Dos parcelas distintas; la división entre ellas es mínima |
| AGC_014 y AGC_116 | Dos terrenos distintos; la distancia es mínima |
| AGC_024 y AGC_171 | Dos terrenos distintos; la distancia es mínima |

**Cómo queda el hallazgo 2 de la etapa 2:**

- **Descartado para estos nueve pares:** que sean dos partes de un mismo campo registradas con dos ID.
- **Lo que queda:** son campos vecinos con lindero común, dibujados casi sin separación.
- **Precisión sobre AGC_126 y AGC_135:** en las coordenadas los contornos no se enciman (están a 0.10 m y la comprobación de encimados dio cero). Que se vean encimados es efecto del grosor de la línea en pantalla.
- **Sigue valiendo para etapas posteriores:** al estar pegadas, los píxeles satelitales de la orilla de una parcela incluyen parte de la vecina, y en cualquier separación de parcelas para evaluar, una puede quedar de un lado y su vecina inmediata del otro.

**Límites:** la imagen de fondo no tiene fecha conocida. Se revisaron los nueve pares a menos de 1 m; los otros 28 pares con orillas a menos de 5 m no se revisaron. La tabla de revisión de contornos no se modificó.

**Jass cerró la etapa 2 el 5 de octubre**, después de la revisión visual de los nueve pares.

### 5 de octubre de 2026 — Calidad de contorno (etapa 3)

**Pregunta:** ¿la calificación de contorno de la exploración en QGIS entra completa y sin alteraciones al catálogo?

**Qué se esperaba:** que las 197 parcelas recibieran su calificación y que los conteos fueran los del informe de la exploración: 175 en A, 12 en B y 10 en C.

**Qué se hizo.** Se amplió `scripts/construir_catalogo.py` con la etapa 3. Lee `exploracion_parcelas_qgis/revision_contornos/revision_contornos.csv` y lo une al catálogo por identificador. El catálogo pasó de 13 a 20 columnas: `contorno_categoria`, las cinco marcas (`contorno_divisiones_internas`, `contorno_arboles_dentro`, `contorno_construccion_dentro`, `contorno_angosta_o_muy_pequena`, `contorno_imagen_poco_clara`) y `contorno_firmeza`. Las 13 columnas anteriores quedaron idénticas. La tabla de huellas incluye ahora la de la tabla de revisión de contornos. No se recalificó ninguna parcela.

**Comprobado (las 15 comprobaciones nuevas se cumplen; 51 en total):**

- La tabla de revisión tiene 197 filas, sin identificadores repetidos, y son exactamente los del catálogo. Ninguna parcela quedó sin calificación.
- La tabla de revisión no trae ninguna columna de rendimiento.
- La categoría solo toma A, B o C; las marcas, `si` o `no`; la firmeza, sus cuatro valores.
- Conteos iguales a los del informe de la exploración: 175 / 12 / 10 en A / B / C; marcas 107 (divisiones), 70 (árboles), 8 (construcción), 16 (angosta o muy pequeña) y 6 (imagen poco clara); 35 confirmadas en QGIS, 2 revisadas sin poder confirmar y 160 de primera pasada.
- Todas las B y las C están confirmadas en QGIS, y todas las de primera pasada están en A.
- 96 parcelas tienen algo dentro del contorno que mezcla la señal satelital (están en B o C, o tienen árboles o construcción, o son angostas).

**Conteos cruzados con columnas de las etapas 1 y 2 (ninguno usa el rendimiento):**

| Grupo | A | B | C |
|---|---:|---:|---:|
| Escritura `Cebada` | 45 | 5 | 0 |
| Escritura `CEBADA` | 130 | 7 | 10 |
| ENTRENAMIENTO | 125 | 8 | 5 |
| PREDICCION | 50 | 4 | 5 |
| Contornos de 5 puntos o menos | 26 | 3 | 0 |
| Chignahuapan | 89 | 4 | 7 |
| Calpulalpan | 39 | 5 | 0 |
| Almoloya | 10 | 2 | 2 |
| Singuilucan | 22 | 1 | 0 |
| Cuautepec de Hinojosa | 8 | 0 | 1 |

Apan, Emiliano Zapata, Nanacamilpa de Mariano Arista y Tepeapulco tienen todas sus parcelas en A. Los conteos por escritura, por conjunto y por número de puntos coinciden con el informe de la exploración (4.3 y 4.5).

**Lo que se desprende al juntar esta etapa con la anterior:** como el área registrada es el área del contorno (hallazgo 1 de la etapa 2), las 22 parcelas en B o C tienen un área registrada que hereda el defecto de su contorno. De ellas, 13 son conocidas y 9 reservadas. Es una consecuencia lógica de dos hechos comprobados; no se ha medido cuánto cambia el área.

**Comprobación adicional, hecha solo en la carpeta local:** segunda corrida leyendo el dataset y la tabla de revisión desde la copia del repositorio: las tres tablas salieron idénticas byte a byte.

**Límites (heredados de la exploración en QGIS):**

- 160 parcelas tienen solo una primera pasada sobre imagen fija, todas en A.
- La imagen de fondo no tiene fecha conocida y no permite saber si lo sembrado era cebada.
- La marca de divisiones internas es la menos firme.
- La nota escrita de cada parcela no se copió al catálogo; se consulta en la tabla de origen.

**No se hizo:** no se cruzó la categoría con el rendimiento (es la etapa 5), no se entrenó ningún modelo y no se modificó la tabla de revisión de contornos ni ningún archivo original.

**Jass cerró la etapa 3 el 5 de octubre.**

### 5 de octubre de 2026 — Precisión y procedencia de la etiqueta (etapa 4)

**Pregunta:** ¿con qué finura está anotado el rendimiento, cómo cambia según el municipio y la escritura del campo `Cultivo`, y qué tanto se repiten los valores?

**Qué se esperaba:** reproducir lo adelantado en una auditoría previa: la escritura `Cebada` solo con 2.5, 3.0 y 3.5; `CEBADA` con dos decimales salvo Singuilucan; 67 valores distintos.

**Qué se hizo, en orden:**

1. Se definieron en el [diccionario](diccionario_columnas.md) las columnas de la tabla nueva, antes de calcular. Jass las aprobó el 5 de octubre.
2. Se amplió `scripts/construir_catalogo.py` con la etapa 4.
3. El catálogo pasó de 20 a 22 columnas: `rendimiento_decimales` y `rendimiento_multiplo_de_medio`. Las 20 anteriores quedaron idénticas.
4. Se creó `tablas/precision_etiqueta_por_municipio.csv`: 12 filas (9 municipios, 2 escrituras y el total).
5. La tabla de comprobaciones tiene ahora 106 filas: 60 comprobaciones, todas cumplidas, y 46 conteos informativos.

**Comprobado (las 9 comprobaciones nuevas se cumplen):**

- Rendimiento de 2.0 a 5.59 t/ha, media 3.955 y mediana 4.34. Son valores plausibles en toneladas por hectárea.
- 67 valores distintos entre los 138. Los más repetidos: 3.0 (19 veces), 3.5 (13) y 2.5 (11).
- Escritura `Cebada`: 35 de 35 son múltiplos de 0.5. Escritura `CEBADA`: 10 de 103.
- Cada municipio tiene una sola escritura.

**Comprobado: hay tres niveles de finura, no dos.**

| Escalón | Municipios | Escritura | Parcelas conocidas | Valores distintos |
|---|---|---|---:|---|
| 0.5 t/ha | Calpulalpan, Emiliano Zapata | `Cebada` | 33 | Solo 2.5, 3.0 y 3.5 |
| 0.1 t/ha | Singuilucan | `CEBADA` | 16 | 7 |
| 0.01 t/ha | Chignahuapan, Almoloya, Cuautepec de Hinojosa | `CEBADA` | 86 | 54, 9 y 5 |

Apan (3), Nanacamilpa (2.5) y Tepeapulco (4.45) tienen una sola parcela conocida: su finura no se puede determinar, aunque sus valores encajan con los de su escritura. **La escritura no equivale a la finura:** Singuilucan es `CEBADA` y está anotado en escalones de 0.1, con 9 de sus 16 valores en múltiplos de 0.5.

**Aclaración sobre una cifra de una auditoría previa.** Esa auditoría dice «58 tienen un decimal y 80 tienen dos». Leyendo el texto original del CSV son 20 sin decimales, 38 con uno y 80 con dos: los 58 son la suma de los dos primeros. No es un error de fondo, es otra forma de contar. Además el CSV no guarda ceros finales (un 4.50 aparece como `4.5`), así que contar decimales se queda corto; el escalón común es la medida más fiable. Por ejemplo, Chignahuapan tiene 6 valores con un decimal, que es lo esperable si son valores de dos decimales terminados en cero.

**Hallazgo nuevo (comprobado): donde el rendimiento está anotado grueso, las parcelas vecinas comparten el mismo valor.**

| Pares de parcelas conocidas con orillas a menos de 20 m | Con rendimiento idéntico |
|---|---:|
| Ambas de la escritura `Cebada` | 7 de 8 |
| Ambas de Singuilucan | 2 de 5 |
| Ambas de municipios en escalones de 0.01 | 0 de 32 |

- Como referencia, entre dos parcelas cualesquiera de un mismo municipio de escalón 0.5, el rendimiento coincide en 150 de 438 pares (34 %); entre vecinas pegadas, en 7 de 8.
- Por distancia entre centros dentro del mismo municipio: en los de escalón 0.5, 4 de 5 pares a menos de 250 m coinciden; en Singuilucan, 6 de 12 a menos de 500 m, frente a 15 de 120 a cualquier distancia; en los de escalón 0.01, 0 de 64 a menos de 500 m. Esto último confirma lo anotado en una auditoría previa.
- Los nueve pares vecinos con rendimiento idéntico: AGC_019 y 103; AGC_020 y 044; AGC_023 y 164; AGC_023 y 170; AGC_164 y 170; AGC_053 y 117; AGC_157 y 163 (escritura `Cebada`); AGC_041 y 166; AGC_089 y 148 (Singuilucan). Las 15 parcelas están en A. (Corregido el 6 de octubre: decía 16; AGC_023, 164 y 170 forman un trío y se habían contado de más.)
- AGC_023, 164 y 170 son las tres parcelas juntas sobre el límite entre Hidalgo y Tlaxcala: las tres tienen 3 t/ha, aunque una es de Apan y dos de Calpulalpan.
- AGC_089 y 148, y AGC_157 y 163, son justo los dos pares en los que el piloto de la exploración en QGIS dudó si había una orilla clara entre ambas.

**Lo que esto indica, sin poder comprobarlo:** que en esos municipios el rendimiento no se anotó parcela por parcela, sino un mismo valor para varias parcelas contiguas (por ejemplo, las de un mismo productor o un mismo lote de cosecha). No hay ningún documento de FIRA que lo diga, no hay identificador de productor y los pares son pocos y no independientes entre sí (tres de ellos son el mismo trío). Conforme a lo que pide el plan del equipo, no se afirma un protocolo de medición distinto ni se atribuye ningún efecto agronómico a la escritura: lo comprobado es la finura y la repetición entre vecinas.

**Si fuera así, qué implicaría:** en esos municipios habría menos mediciones reales que parcelas, la diferencia de rendimiento entre dos parcelas vecinas no sería observable, y al separar parcelas para evaluar, una vecina con el mismo valor podría quedar del otro lado.

**Otras tres pruebas de procedencia, sin resultado concluyente:**

- **Último dígito de los rendimientos con dos decimales.** Si alguien estimara a ojo, sobrarían los terminados en 5. No es así: los dígitos del 1 al 9 aparecen entre 6 y 13 veces cada uno. Es compatible con valores que salen de una cuenta (por ejemplo, peso entre superficie) y no de una estimación redondeada, pero no lo prueba.
- **Rendimiento por área.** Si el rendimiento saliera de dividir toneladas enteras entre el área, el producto daría casi un entero. No se ve: la distancia media al entero más cercano es 0.220, y al azar sería 0.25.
- **Valores repetidos en Chignahuapan.** 26 de sus 71 parcelas comparten valor con otra (4.55 cinco veces; 4.49 y 4.52 cuatro veces). Las que comparten valor no están cerca entre sí: el par idéntico más cercano en los municipios de escalón 0.01 está a 940 m. Los valores repetidos caen donde se concentra la mayoría (alrededor de 4.5), así que la repetición puede deberse solo a eso. No concluyente.

**Comprobación adicional, hecha solo en la carpeta local:** segunda corrida con la copia del repositorio; las cuatro tablas salieron idénticas byte a byte.

**Límites:**

- Sigue sin saberse cómo se midió el rendimiento, con qué humedad y sobre qué superficie. Esta etapa describe cómo está anotado, no cómo se obtuvo.
- Las 59 reservadas no tienen rendimiento a la vista, así que no se sabe con qué finura están anotadas; lo razonable es suponer la de su municipio, pero es una suposición.
- Dos comparaciones citadas arriba (los pares de Chignahuapan frente a lo esperable, y qué tan improbable es 7 de 8) no tienen una prueba estadística guardada en el script; se dan los conteos para que cada quien juzgue.

**No se hizo:** no se cruzó el rendimiento con el contorno (etapa 5), no se calcularon promedios por municipio ni parcelas extremas (etapa 6), no se entrenó ningún modelo y no se modificó ningún archivo original.

**Jass aprobó las columnas de la tabla de precisión y cerró la etapa 4 el 5 de octubre.**

### 5 de octubre de 2026 — Regla del cruce de contorno y rendimiento (etapa 5), escrita antes de mirar

**Estado: aprobada por Jass el 5 de octubre, sin cambios, antes de cruzar.** Lo único consultado para escribirla fue cuántas parcelas conocidas hay en cada categoría y en cada municipio; eso no usa el rendimiento.

**Pregunta:** ¿el rendimiento de una parcela se relaciona con la calidad de su contorno?

**Con qué se cuenta.** De las 138 parcelas conocidas, 125 están en A, 8 en B y 5 en C. Las B y las C conocidas están solo en tres municipios:

| Municipio | A | B | C |
|---|---:|---:|---:|
| Chignahuapan | 65 | 3 | 3 |
| Calpulalpan | 27 | 3 | 0 |
| Almoloya | 6 | 2 | 2 |

Marcas entre las 138: divisiones internas 78, árboles dentro 50, angosta o muy pequeña 13, construcción dentro 5, imagen poco clara 5.

**Por qué no basta comparar promedios directos.** Los municipios rinden distinto (Chignahuapan y Almoloya alrededor de 4.5 t/ha; Calpulalpan alrededor de 3.0) y las categorías no están repartidas por igual entre ellos. Una diferencia directa entre A, B y C podría ser solo una diferencia entre municipios. Por eso la comparación que vale es **dentro de cada municipio**.

**Qué se mide.** Para cada parcela conocida, su **desviación municipal**: su rendimiento menos el promedio de las demás parcelas conocidas de su mismo municipio (sin contarla a ella). Es positiva si rindió más que sus vecinas de municipio y negativa si rindió menos. Apan, Nanacamilpa y Tepeapulco tienen una sola parcela conocida y no entran, porque no hay con quién compararlas; las tres están en A. Es un promedio, no un modelo.

**Comparación principal (una sola):** las 13 parcelas en B o C frente a las parcelas en A, usando la desviación municipal promedio de cada grupo.

**Comparaciones secundarias (exploratorias):**

1. B sola frente a A.
2. C sola frente a A.
3. Con divisiones internas frente a sin ellas.
4. Con árboles dentro frente a sin ellos.
5. Angosta o muy pequeña frente a las demás.
6. B o C frente a A, pero midiendo qué tan lejos queda cada parcela del promedio de su municipio sin importar si es por arriba o por abajo. Responde si las parcelas con contorno dudoso son más extremas.

Construcción dentro e imagen poco clara no se comparan: con 5 parcelas cada una no hay con qué.

**Cómo se decide si una diferencia es real.** Con una prueba de barajar: se reparten al azar las etiquetas de contorno entre las parcelas del mismo municipio, 10 000 veces, y se ve qué diferencias aparecen por pura casualidad. Semilla fija, para que el resultado se pueda repetir.

**Qué cuenta como diferencia (fijado antes de mirar):**

- **Comparación principal:** se dirá «se ve una diferencia» solo si se cumplen las dos condiciones: la diferencia es de al menos 0.25 t/ha, y aparece por casualidad en menos de 5 de cada 100 barajadas. El umbral de 0.25 es la mitad del escalón más grueso con que está anotado el rendimiento (etapa 4).
- **Comparaciones secundarias:** como son seis, alguna puede salir llamativa por casualidad. Solo se señalará una si aparece por casualidad en menos de 1 de cada 100 barajadas, y aun así como pista, no como resultado.
- **Si no se cumple:** se dirá «no se detecta diferencia», que no es lo mismo que «no hay diferencia». Se informará qué tamaño de diferencia se habría podido detectar con tan pocas parcelas.

**Qué no cambia, salga lo que salga:** no se excluye ninguna parcela, no se cambia ninguna calificación de contorno y no se corrige ningún rendimiento.

**Qué se espera:** lo más probable es «no se detecta diferencia», porque 13 parcelas solo permiten ver diferencias grandes.

**Qué dejaría:** `tablas/cruce_contorno_rendimiento.csv`, una fila por comparación, con las columnas propuestas en el [diccionario](diccionario_columnas.md).

### 5 de octubre de 2026 — Cruce de contorno y rendimiento (etapa 5)

**Pregunta:** ¿el rendimiento de una parcela se relaciona con la calidad de su contorno?

**Qué se esperaba:** «no se detecta diferencia», porque solo hay 13 parcelas conocidas en B o C. **No fue lo que salió.**

**Qué se hizo.** Con la regla ya aprobada, se escribió `scripts/cruzar_contorno_y_rendimiento.py`. Lee el catálogo, calcula la desviación municipal de cada parcela conocida y hace las siete comparaciones con 10 000 barajadas cada una (semilla fija 20261005). Escribe `tablas/cruce_contorno_rendimiento.csv`. Después de ver el resultado se añadieron dos tablas descriptivas para entenderlo: `cruce_contorno_por_municipio.csv` y `cruce_contorno_parcelas_b_c.csv`.

**Resultado de la comparación principal, según la regla fijada: se ve una diferencia.**

- Las 13 parcelas en B o C rindieron en promedio 0.322 t/ha **más** que las demás de su municipio; las 122 en A, 0.034 menos. Diferencia: **+0.356 t/ha**.
- Una diferencia así de grande aparece por casualidad en 0.9 de cada 100 barajadas. Las diferencias que da el azar van de −0.282 a +0.242.
- Cumple las dos condiciones fijadas (al menos 0.25 t/ha y menos de 5 de cada 100).

**Resultado de las seis comparaciones secundarias: ninguna llega a pista.**

| Comparación | Diferencia (t/ha) | Por casualidad, de cada 100 |
|---|---:|---:|
| B frente a A | +0.245 | 11.8 |
| C frente a A | +0.535 | 2.3 |
| Con divisiones internas frente a sin ellas | −0.096 | 27.0 |
| Con árboles dentro frente a sin ellos | +0.051 | 56.1 |
| Angosta o muy pequeña frente a las demás | +0.229 | 11.0 |
| B o C frente a A, sin importar el signo | +0.007 | 95.3 |

La de C sola es la más llamativa, pero no alcanza el nivel exigido a las secundarias (menos de 1 de cada 100). La última dice que las B o C no quedan más lejos de su municipio que las A; lo que cambia es que casi todas quedan del lado de arriba.

**Lo que muestra el desglose (comprobado, descriptivo, añadido después de ver el resultado):**

| Municipio | A: parcelas y desviación media | B o C: parcelas y desviación media |
|---|---|---|
| Chignahuapan | 65 parcelas; −0.058 | 6 parcelas; +0.627 |
| Almoloya | 6 parcelas; −0.071 | 4 parcelas; +0.107 |
| Calpulalpan | 27 parcelas; 0.000 | 3 parcelas; 0.000 |

- **La diferencia está en Chignahuapan.** En Calpulalpan no hay ninguna: sus tres B tienen 3.0 t/ha, igual que el promedio del municipio. En Almoloya es pequeña.
- **Y dentro de Chignahuapan, en tres parcelas:** AGC_127 (B, 5.57 t/ha, 0.91 ha), AGC_049 (C, 5.53 t/ha, 0.87 ha) y AGC_055 (C, 5.45 t/ha, 1.37 ha) están cada una alrededor de 1 t/ha por encima de su municipio. Las otras diez B o C están entre −0.001 y +0.469.
- **En la mediana casi no hay diferencia:** +0.064 en B o C frente a +0.013 en A.
- **Signo:** de las 13 en B o C, 9 están por encima de su municipio, 1 por debajo (por una milésima) y 3 exactamente en el promedio. De las 122 en A, 62 por encima y 46 por debajo.
- **Las B o C de Chignahuapan son más chicas:** mediana de 1.92 ha frente a 3.84 ha de las A.

**Cómo debe leerse.** Lo comprobado no es «un contorno dudoso da más rendimiento», sino algo más acotado: **tres parcelas muy pequeñas de Chignahuapan con contorno dudoso están entre los rendimientos más altos de todo el conjunto**, y eso basta para mover el promedio de un grupo de 13.

**Lo que no se sabe, y las explicaciones posibles (sospechas, ninguna comprobada):**

1. **El tamaño, no el contorno.** Una auditoría previa ya anotaba que dentro de un municipio las parcelas pequeñas tienden a rendir algo más. Las B o C son más chicas, así que el contorno podría estar funcionando como señal de tamaño. Este cruce no separa las dos cosas.
2. **El denominador del rendimiento.** En una parcela de menos de 1 ha, un error pequeño en la superficie cambia mucho las toneladas por hectárea. Pero la dirección no cuadra del todo: un contorno que incluye algo ajeno (B) o une varios campos (C) da una superficie mayor que la cultivada, y dividir entre una superficie mayor daría un rendimiento **menor**, no mayor. Sigue sin saberse qué superficie usó FIRA.
3. **Casualidad concentrada.** Con tres parcelas no se puede descartar.

**Qué no cambia:** no se excluyó ninguna parcela, no se cambió ninguna calificación de contorno y no se corrigió ningún rendimiento, como se fijó en la regla.

**Para etapas posteriores:** la etapa 6 (parcelas extremas) retoma estas tres parcelas junto con las demás extremas y mira el tamaño. Para el equipo: la calidad de contorno y el área merecen acompañar a cada parcela como datos de calidad, sin usarse para descartar casos.

**Comprobación adicional, hecha solo en la carpeta local:** segunda corrida escribiendo fuera del proyecto; las tres tablas salieron idénticas byte a byte.

**Límites:**

- Son 13 parcelas en B o C, y la diferencia descansa en tres de ellas.
- La desviación municipal en Calpulalpan casi no dice nada, porque sus rendimientos solo toman 2.5, 3.0 y 3.5.
- La prueba de barajar dice que la diferencia no es casualidad del reparto de etiquetas; no dice cuál es la causa.
- Las dos tablas de apoyo y la lectura por municipio se hicieron después de ver el resultado. Son descriptivas y no forman parte de la regla.
- **Límite añadido el 5 de octubre, al cerrar la etapa 8:** la prueba de barajar trata a las parcelas de un mismo municipio como intercambiables y no tiene en cuenta qué tan cerca están unas de otras. Si las parcelas de contorno dudoso estuvieran agrupadas en una zona donde todo rinde más, la prueba exageraría la certeza. Se cree que aquí el efecto es pequeño por tres hechos ya comprobados: las tres parcelas que mueven el resultado están a entre 1.5 y 4 km unas de otras (etapa 6), las conocidas que las rodean rinden lo normal del municipio (etapa 6) y en los municipios de escalón 0.01 ningún par de parcelas cercanas comparte rendimiento (etapa 4). No se rehízo la prueba barajando por zonas; la conclusión de esta etapa no descansa en ese número, sino en un hecho que se lee directo en la tabla.
- Las 59 reservadas no entran: no tienen rendimiento a la vista.

**Sobra un archivo:** al revisar el resultado se creó sin querer la carpeta `scripts/__pycache__/`, con un archivo temporal de Python. No es parte de la auditoría y se puede borrar; el repositorio ya ignora esas carpetas.

**No se hizo:** no se entrenó ningún modelo y no se modificó ningún archivo original.

**Jass aprobó las dos tablas de apoyo y cerró la etapa 5 el 5 de octubre.** Cómo queda entendido el resultado: no es bueno ni malo para el proyecto, es una advertencia útil. Tres de los rendimientos más altos vienen de las parcelas menos confiables (muy pequeñas y con contorno dudoso); las parcelas se conservan, viajan marcadas en el catálogo, y se recomienda al equipo reportar los resultados de cualquier modelo con y sin ellas y tener más cautela con las 9 reservadas en B o C.

### 5 de octubre de 2026 — Parcelas extremas (etapa 6)

**Pregunta:** ¿qué parcelas tienen un rendimiento muy alejado del de su municipio, y qué las rodea (contorno, tamaño, vecinas)?

**Qué se esperaba:** reencontrar las nueve parcelas duna auditoría previa, y ver si el tamaño explica las tres del cruce de la etapa 5.

**Qué se hizo, en orden:**

1. Se fijó en el [diccionario](diccionario_columnas.md), antes de calcular, qué se llama «extrema»: una parcela a más de 1 t/ha del promedio de las demás conocidas de su municipio (el umbral usado en una auditoría previa). También los tramos de tamaño: menos de 2 ha, de 2 a 5 ha y más de 5 ha.
2. Se escribió `scripts/senalar_parcelas_extremas.py`.
3. Se crearon `tablas/desviacion_municipal_por_parcela.csv` (138 filas) y `tablas/desviacion_por_tamano.csv` (15 filas).

**Comprobado: con esta regla hay 7 parcelas extremas de 138; 128 no lo son y 3 no se pueden juzgar.**

| Parcela | Municipio | Rendimiento | Promedio de las demás | Desviación | Área (ha) | Contorno |
|---|---|---:|---:|---:|---:|---|
| AGC_171 | Chignahuapan | 2.15 | 4.51 | −2.36 | 11.63 | A |
| AGC_015 | Chignahuapan | 2.64 | 4.50 | −1.86 | 1.97 | A |
| AGC_024 | Chignahuapan | 3.03 | 4.50 | −1.47 | 11.53 | A |
| AGC_034 | Singuilucan | 2.00 | 3.15 | −1.15 | 8.09 | A |
| AGC_049 | Chignahuapan | 5.53 | 4.46 | +1.07 | 0.87 | C |
| AGC_127 | Chignahuapan | 5.57 | 4.46 | +1.11 | 0.91 | B |
| AGC_162 | Chignahuapan | 5.59 | 4.46 | +1.13 | 4.93 | A |

Seis de las siete son de Chignahuapan. En Calpulalpan, Almoloya y Cuautepec ninguna parcela puede pasar el umbral: sus rendimientos varían menos de 1 t/ha alrededor del promedio.

**Diferencia con una auditoría previa, que lista nueve.** Las siete de arriba están entre las nueve. Las otras dos:

- **AGC_048** (Nanacamilpa, 2.5 t/ha): es la única conocida de su municipio, así que aquí no tiene con quién compararse. Esa auditoría previa la comparó con otra referencia. No se contradicen: cambia la definición.
- **AGC_069** (Chignahuapan, 5.46 t/ha): queda a +0.997 t/ha, tres milésimas por debajo del umbral.

No se eligió una versión: ese documento no se modificó, y aquí se aplica la regla tal como se fijó.

**Comprobado: el umbral corta un grupo que va junto.** Los cinco rendimientos más altos de Chignahuapan van de 5.45 a 5.59 y el siguiente es 5.19. De esos cinco, tres pasan el umbral y dos se quedan a milésimas (AGC_069, +0.997, y AGC_055, +0.987).

| Parcela | Rendimiento | Área (ha) | Contorno | ¿Extrema por la regla? |
|---|---:|---:|---|---|
| AGC_162 | 5.59 | 4.93 | A | Sí |
| AGC_127 | 5.57 | 0.91 | B | Sí |
| AGC_049 | 5.53 | 0.87 | C | Sí |
| AGC_069 | 5.46 | 0.38 | A | No, por 3 milésimas |
| AGC_055 | 5.45 | 1.37 | C | No, por 13 milésimas |

Cuatro de las cinco miden menos de 1.4 ha y tres tienen contorno B o C. AGC_069 es la parcela conocida más pequeña del conjunto.

**Comprobado: las cinco más altas no forman una zona.** Están a entre 1.5 y 4 km unas de otras, salvo AGC_162 y AGC_049, a 425 m. Las parcelas conocidas que cada una tiene a menos de 1 km promedian entre 4.0 y 4.8 t/ha, es decir, lo normal del municipio. No es un rincón donde todo rinde más.

**Comprobado: dos de las más bajas son vecinas pegadas.** AGC_171 (2.15) y AGC_024 (3.03) tienen sus centros a 300 m y sus orillas a 0.92 m: es uno de los nueve pares que Jass revisó en QGIS. Las dos miden unas 11.5 ha y están en A. Las demás conocidas a menos de 1 km de ellas promedian 4.2 t/ha. AGC_015 (2.64) está aparte, a más de 3.5 km de esas dos.

**Sobre el tamaño (comprobado, descriptivo).** Desviación municipal media en Chignahuapan:

| Tramo | Todas las parcelas | Solo las de contorno A | Alejamiento medio |
|---|---|---|---:|
| Menos de 2 ha | 21 parcelas; +0.143 | 18 parcelas; −0.009 | 0.477 |
| De 2 a 5 ha | 22 parcelas; +0.160 | 19 parcelas; +0.154 | 0.287 |
| Más de 5 ha | 28 parcelas; −0.233 | 28 parcelas; −0.233 | 0.375 |

- **Las parcelas grandes rinden algo menos.** Las de más de 5 ha quedan 0.23 t/ha por debajo del promedio de su municipio.
- **Las pequeñas con contorno A no rinden más.** Quedan en −0.009, prácticamente en el promedio. Lo que sube el promedio de las pequeñas son las de contorno B o C.
- **Las pequeñas se alejan más de su municipio, hacia cualquier lado** (0.477 frente a 0.287 de las medianas).

**Qué responde esto a la pregunta pendiente de la etapa 5 (¿contorno o tamaño?).** El tamaño solo no explica las tres parcelas: entre las pequeñas de Chignahuapan, las de buen contorno están en el promedio. Pero son 3 parcelas en B o C frente a 18 en A, así que queda como indicio, no como conclusión.

**Lo que indica todo junto, sin poder comprobarlo:**

- **Las altas:** rendimientos muy altos en parcelas diminutas, sin que sus vecinas rindan más. Es lo que se vería si en parcelas tan chicas la cifra de t/ha fuera frágil, por ejemplo porque un pequeño error de superficie la mueve mucho. No se sabe qué superficie usó FIRA.
- **Las bajas pegadas (AGC_171 y AGC_024):** dos parcelas grandes, contiguas, las dos muy por debajo de sus vecinas. Es lo que se vería si algo real les ocurrió a ambas (daño local, mismo manejo, mismo productor). Apunta más a un hecho de campo que a un error de anotación, pero no hay con qué confirmarlo.

**Las tres que no se pueden juzgar** (únicas conocidas de su municipio): AGC_047 (Tepeapulco, 4.45), AGC_048 (Nanacamilpa, 2.5) y AGC_164 (Apan, 3.0). AGC_164 tiene a 351 m a AGC_170, con el mismo rendimiento; AGC_048 tiene su conocida más cercana a 965 m (3.5 t/ha); AGC_047 la tiene a 4.8 km.

**Qué no cambia:** ninguna parcela se excluyó ni se corrigió. La columna `extrema` es una señal para leer con cuidado esos casos, no una instrucción de quitarlos.

**Comprobación adicional, hecha solo en la carpeta local:** segunda corrida escribiendo fuera del proyecto; las dos tablas salieron idénticas byte a byte.

**Límites:**

- El umbral de 1 t/ha es una convención y deja fuera por milésimas a dos parcelas del mismo grupo.
- Es un umbral fijo: en municipios con rendimientos muy parejos (Almoloya, Cuautepec) una parcela puede ser rara para su municipio sin llegar a 1 t/ha.
- En Calpulalpan el rendimiento solo toma tres valores, así que la desviación informa poco.
- La distancia a las vecinas es entre centros, y solo cuenta parcelas conocidas.
- No se miró el satélite de estas parcelas; eso corresponde a T06.

**No se hizo:** no se entrenó ningún modelo y no se modificó ningún archivo original ni ningún documento previo.

**Jass aprobó las columnas de las dos tablas y cerró la etapa 6 el 5 de octubre.**

### 5 de octubre de 2026 — Criterios del diagnóstico de soporte (etapa 7), escritos antes de calcular

**Estado: aprobada por Jass el 5 de octubre, sin cambios, antes de calcular.** Para escribirla solo se miraron los nombres de las columnas de las tablas satelitales y las características de los mapas (cuadrícula, proyección y valor de «sin dato»).

**Pregunta:** ¿qué tan respaldada está cada una de las 59 parcelas reservadas por las 138 conocidas, y con qué calidad de entradas cuenta?

**Qué significa «soporte».** Que para estimar una parcela reservada haya ejemplos conocidos parecidos y cercanos de los cuales aprender, y que la propia parcela tenga datos utilizables. No usa el rendimiento de ninguna parcela, salvo para saber cuáles son conocidas.

**Una fila por parcela, las 197.** Para las 59 reservadas es lo que importa. Para las 138 conocidas se calcula lo mismo sin contarse a sí mismas, y sirve de vara de medir: si las reservadas se parecen a las conocidas, lo que se compruebe con las conocidas vale para las reservadas.

**Cinco bloques, que son los que pide el plan del equipo para T02:**

1. **Municipio compartido:** cuántas conocidas hay en su municipio y con qué finura está anotado el rendimiento ahí (etapa 4).
2. **Cercanía:** la conocida más cercana, de centro a centro y de orilla a orilla, y cuántas conocidas hay a menos de 500 m y de 1 km.
3. **Clima compartido:** qué celdas del mapa de lluvia toca y cuántas conocidas comparten alguna.
4. **Disponibilidad de entradas:** observaciones satelitales con dato por sensor, meses cubiertos y hueco más largo; y qué parte del contorno tiene dato de relieve.
5. **Calidad de observación:** la categoría de contorno y si hay algo dentro que mezcle la señal.

**Criterios que requieren decisión de Jass:**

1. **Distancias.** De centro a centro, geodésica (decisión ya tomada). De orilla a orilla, en metros sobre la proyección UTM zona 14 norte, igual que en la etapa 2: no existe un cálculo geodésico sencillo entre orillas, y esa proyección encoge cerca de 0.03 %, es decir, 3 cm en 100 m.
2. **Ventana del satélite.** Del 1 de abril al 31 de octubre de 2025 para contar observaciones y meses, que es el periodo que documenta FIRA y el que usaron las auditorías anteriores. El hueco más largo se mide del 1 de junio al 31 de octubre, cuando hay cultivo según el NDVI (registro, 3.7). Es solo para describir la disponibilidad: no fija la ventana que usará el equipo, que sigue sin decidirse.
3. **Sin umbral de nubosidad.** Se cuenta «observación con dato» cuando el índice de referencia no está vacío (NDVI en Sentinel-2 y Planet; VI6T en Landsat). No se aplica el corte de 20 % de nubosidad, porque el plan lo deja como candidato y no como regla.
4. **Relieve: recalcular la cobertura, no reutilizarla.** El plan de esta auditoría decía reutilizar la cobertura ya calculada. Se propone cambiarlo, por la misma razón que con las celdas climáticas: que todo salga de los originales con un solo script. Se calcularía solo qué fracción del contorno tiene dato en los mapas de elevación y de pendiente, y se compararía con lo ya calculado en una auditoría previa del dataset (trabajo local). Los valores de elevación y pendiente por parcela no se calculan aquí: son de T05.
5. **Avisos en lugar de una calificación.** No se propone un semáforo ni un puntaje único, porque obligaría a decidir cuánto pesa cada cosa y eso le corresponde al equipo. Se propone una columna `avisos` que liste hechos con umbral declarado:

| Aviso | Cuándo se pone |
|---|---|
| `pocas_conocidas_en_municipio` | Menos de 5 conocidas en su municipio |
| `sin_conocida_a_menos_de_1_km` | Ninguna conocida con centro a menos de 1 km |
| `celda_clima_sin_conocidas` | Ninguna conocida comparte alguna de sus celdas de lluvia |
| `etiqueta_gruesa_en_municipio` | El rendimiento de su municipio está anotado en escalones de 0.5 t/ha |
| `relieve_incompleto` | Menos del 99 % del contorno tiene dato de elevación o de pendiente |
| `contorno_b_o_c` | Su contorno está en B o C |
| `angosta_o_muy_pequena` | Tiene esa marca en la revisión de contornos |

Los umbrales (5 conocidas, 1 km, 99 %) son una propuesta; son fáciles de cambiar.

**Qué se espera:** que las 59 reservadas resulten tan respaldadas como las 138 conocidas, como adelantan las auditorías previas; y que los avisos se concentren en pocas parcelas.

**Qué dejaría:** `tablas/soporte_por_parcela.csv` (197 filas) y `tablas/soporte_resumen_por_municipio.csv`, con las columnas propuestas en el [diccionario](diccionario_columnas.md), y un script nuevo, `scripts/diagnosticar_soporte.py`.

**Qué no se hace:** no se abre la tabla de T03 (eso es la etapa 8), no se extraen valores de clima ni de relieve, no se construyen variables para modelar y no se entrena nada.

### 5 de octubre de 2026 — Soporte de las 59 reservadas (etapa 7)

**Pregunta:** ¿qué tan respaldada está cada parcela reservada por las 138 conocidas, y con qué calidad de entradas cuenta?

**Qué se esperaba:** que las 59 resultaran tan respaldadas como las 138, y que los avisos se concentraran en pocas parcelas. **Se cumplió.**

**Qué se hizo, en orden:**

1. Jass aprobó los cinco criterios y las columnas antes de calcular.
2. Se escribió `scripts/diagnosticar_soporte.py`. Lee el catálogo, el shapefile, un mapa de lluvia, los dos mapas de relieve y las dos tablas satelitales.
3. Se crearon `tablas/soporte_por_parcela.csv` (197 filas), `tablas/soporte_resumen_por_municipio.csv` (17 filas) y `tablas/huellas_archivos_leidos_soporte.csv` (huella de los seis archivos originales leídos).
4. Se comparó cada bloque contra lo ya calculado en la carpeta local.

**Un error propio, detectado y corregido antes de cerrar.** La primera corrida marcó 22 parcelas con relieve incompleto. Al comparar con lo ya calculado en una auditoría previa del dataset, que marcaba 5, se vio que 17 eran falsas: el script leía un recuadro del mapa demasiado justo y a algunos contornos les faltaba una franja. Se corrigió la lectura (ahora toma una celda de margen por cada lado) y el resultado coincide con el anterior. Es justo para lo que servía recalcular y comparar.

**Comprobado: las reservadas están tan respaldadas como las conocidas, o más.**

| Medida | 59 reservadas | 138 conocidas (sin contarse a sí mismas) |
|---|---|---|
| En municipio con parcelas conocidas | 59 de 59 | — |
| Distancia entre centros a la conocida más cercana (mediana; máxima) | 350.5 m; 1 915.6 m | 399.8 m; 4 777.8 m |
| Distancia entre orillas (mediana) | 51.9 m | 17.8 m |
| Sin ninguna conocida a menos de 1 km | 7 (12 %) | 21 (15 %) |
| Sin ninguna conocida que comparta celda de lluvia | 1 | 3 |
| Observaciones con dato, Sentinel-2 / Planet / Landsat (mediana) | 37 / 94 / 18 | 37.5 / 94 / 19 |
| Meses con dato de abril a octubre, Sentinel-2 y Planet | 7 de 7 en todas | 7 de 7 en todas |
| Hueco más largo de junio a octubre, Sentinel-2 / Planet (mediana) | 20 / 19 días | 20 / 19 días |
| Relieve incompleto | 0 | 5 |
| Contorno en B o C | 9 (15 %) | 13 (9 %) |
| Con algo dentro que mezcla la señal | 29 (49 %) | 67 (49 %) |

- Las cifras de distancia entre centros (350.5 y 1 915.6 m) son las que Jass había fijado como referencia en una decisión previa.
- **Muchas reservadas tienen una conocida pegada:** 14 tienen una conocida con la orilla a menos de 5 m, 24 a menos de 20 m y 35 a menos de 100 m.
- Las reservadas están en 6 municipios: Chignahuapan 29, Calpulalpan 14, Singuilucan 7, Almoloya 4, Cuautepec de Hinojosa 4 y Nanacamilpa 1.
- La única diferencia desfavorable es el contorno: hay proporcionalmente más reservadas en B o C.

**Comprobado: los avisos entre las 59 reservadas.**

| Aviso | Reservadas |
|---|---:|
| Etiqueta gruesa en su municipio (escalones de 0.5) | 14 |
| Contorno B o C | 9 |
| Sin conocida a menos de 1 km | 7 |
| Angosta o muy pequeña | 3 |
| Pocas conocidas en su municipio | 1 |
| Celda de lluvia sin conocidas | 1 |
| Relieve incompleto | 0 |

32 de las 59 no tienen ningún aviso, 22 tienen uno y 5 tienen dos o tres. Las 14 de etiqueta gruesa son todas las de Calpulalpan.

**Las cinco reservadas con más de un aviso:**

| Parcela | Municipio | Avisos |
|---|---|---|
| AGC_120 | Nanacamilpa | Pocas conocidas en su municipio (una sola); sin conocida a menos de 1 km; angosta o muy pequeña. Su conocida más cercana está a 1 259 m y es de otro municipio |
| AGC_173 | Calpulalpan | Sin conocida a menos de 1 km (1 699 m); etiqueta gruesa; contorno B |
| AGC_183 | Calpulalpan | Sin conocida a menos de 1 km (1 087 m); etiqueta gruesa; contorno B |
| AGC_147 | Calpulalpan | Sin conocida a menos de 1 km (1 170 m); etiqueta gruesa |
| AGC_174 | Cuautepec de Hinojosa | Sin conocida a menos de 1 km (1 643 m); ninguna conocida comparte su celda de lluvia |

Las otras dos sin conocida a menos de 1 km son AGC_065 (Almoloya, 1 916 m) y AGC_118 (Singuilucan, 1 074 m).

**Relieve.** Las cinco parcelas con relieve incompleto (AGC_020, 023, 044, 164 y 170) son todas conocidas: ninguna reservada tiene ese problema. AGC_044 tiene la elevación completa y solo le falta parte de la pendiente.

**Lo que se desprende al juntar esta etapa con la 4 (consecuencia lógica, no comprobada).** En los municipios de etiqueta gruesa las vecinas pegadas suelen compartir el mismo rendimiento. De las 14 reservadas de Calpulalpan, 2 tienen una conocida con la orilla a menos de 20 m (AGC_025 y AGC_071). Para esas dos, el rendimiento de la vecina es un candidato fuerte; para las demás no hay esa pista.

**Comparación con lo ya calculado en la carpeta local (todo coincide):**

| Bloque | Contra qué se comparó | Resultado |
|---|---|---|
| Conocida más cercana | Archivo de trabajo local `auditoria_paso3.json` | Misma parcela en las 197; diferencia máxima de 6 cm |
| Celdas de lluvia | Archivo de trabajo local `soporte_climatico.json` | Mismas celdas en las 197; 29 celdas distintas en total; 31 parcelas tocan más de una |
| Observaciones y meses con dato | Archivo de trabajo local `catalogo_parcelas.json` | Idénticos en las 197 y los tres sensores |
| Cobertura de relieve | Mismo archivo | Las mismas 5 parcelas; diferencia máxima de 0.005 % |

También se hizo una segunda corrida leyendo la copia del dataset del repositorio: las tres tablas salieron idénticas byte a byte.

**Límites:**

- El soporte describe si hay ejemplos cercanos y datos disponibles; no dice si la estimación de una parcela saldrá bien.
- Que reservadas y conocidas se parezcan en estas medidas no prueba que sean iguales en todo, ni que el reparto 70/30 fuera al azar.
- «Observación con dato» no significa observación limpia: no se aplicó ningún corte de nubosidad.
- La ventana de abril a octubre y el tramo de junio a octubre son solo para describir; el equipo no ha decidido la ventana.
- El municipio es el declarado en el shapefile, no verificado contra límites oficiales.
- AGC_174 toca una segunda celda de lluvia con un fragmento diminuto (menos de 0.01 m²). Se contó porque el criterio es «cualquier superficie»; no cambia ninguno de sus avisos.
- Los umbrales de los avisos (5 conocidas, 1 km, 99 %) son una convención.
- La distancia entre orillas es sobre proyección plana; la diferencia con la geodésica es de unos 3 cm cada 100 m.

**No se hizo:** no se abrió la tabla de T03 (etapa 8), no se extrajeron valores de clima ni de relieve, no se construyeron variables para modelar, no se entrenó ningún modelo y no se modificó ningún archivo original.

**Jass cerró la etapa 7 el 5 de octubre.**

**Decisión de Jass (5 de octubre):** las etapas 8 y 9 se terminan en la carpeta local y la copia al repositorio se hace una sola vez, al final. Motivo: mantener un solo original, no adaptar dos veces las referencias a documentos locales, y porque la comparación no necesita hacerse desde el repositorio. Al copiar se ajustará la copia (README corto para el equipo, bitácora aparte, referencias locales reescritas); la carpeta local no se toca.

### 5 de octubre de 2026 — Comparación con el diagnóstico de T03 (etapa 8)

**Pregunta:** el diagnóstico de soporte hecho aquí de forma independiente, ¿coincide con el de T03 (Migue)? Y donde no coincide, ¿por qué?

**Qué se esperaba:** que coincidiera en lo que se define igual y difiriera poco en lo demás, por el método (distancia plana frente a geodésica; celda del centro frente a celdas por superficie).

**Qué se hizo, en orden:**

1. Se definieron en el [diccionario](diccionario_columnas.md) las columnas de las tablas de comparación, antes de abrir la tabla de T03.
2. Se abrió por primera vez `registro/t03/soporte_parcelas.csv` (197 filas, 24 columnas), en la rama `feature/auditoria-catalogo-y-etiquetas` del repositorio. Se comprobó que es igual a la versión de la rama `main` (commit `ba96fe5`), salvo el fin de línea que pone Git en Windows. Solo se leyó.
3. Se escribió `scripts/comparar_con_soporte_t03.py`. Compara columna por columna y, donde la definición es distinta, repite la definición de T03 para comprobar la explicación.
4. Se crearon `tablas/comparacion_con_t03.csv` (23 filas, una por columna de T03), `tablas/comparacion_con_t03_por_parcela.csv` (411 filas) y `tablas/huellas_archivos_leidos_comparacion.csv`.

**Resultado, en una frase: las dos versiones coinciden en todo lo que miden igual, y todas las diferencias se explican por la definición.**

**Comprobado: 9 columnas con la misma definición coinciden en las 197 parcelas.**

| Columna de T03 | Columna de esta auditoría | Iguales |
|---|---|---:|
| `CONJUNTO` | `conjunto_origen` | 197 |
| `municipio` | `municipio` | 197 |
| `estado` | `estado` | 197 |
| `grupo_registro` | `cultivo_origen` | 197 |
| `area_ha` | `area_ha_origen` | 197 |
| `etiquetas_municipio` | `conocidas_en_municipio` | 197 |
| `s2_capturas_con_dato` | `s2_observaciones_con_dato` | 197 |
| `pl_capturas_con_dato` | `planet_observaciones_con_dato` | 197 |
| `ls_capturas_con_dato` | `landsat_observaciones_con_dato` | 197 |

**Comprobado: 7 columnas con definición distinta. En las 7, al repetir aquí la definición de T03 se obtiene su mismo valor en las 197 parcelas.** Es decir, ninguna diferencia viene de un error de alguna de las dos partes.

| Columna de T03 | Iguales tal cual | Por qué difieren |
|---|---:|---|
| `dist_etiquetada_mas_cercana_m` | 0 de 197 | T03 mide sobre un mapa plano (EPSG:6372), que encoge las distancias de esta zona entre 0.26 % y 0.52 %. Diferencia mediana de 1.3 m y máxima de 16.3 m. La mediana de las reservadas es 349.3 m en T03 y 350.5 m aquí |
| `celda_chirps` | 197 de 197 | T03 toma la celda del centro; aquí, la celda con la mayor parte de la superficie. En este conjunto resultan ser siempre la misma |
| `celdas_chirps_tocadas` | 197 de 197 | T03 cuenta también las celdas que el contorno solo roza; aquí, las que tienen alguna superficie. Coinciden en todas, incluido el fragmento diminuto de AGC_174 |
| `etiquetadas_en_misma_celda` | 28 de 197 | T03 cuenta las conocidas cuyo centro cae en la misma celda; aquí, las que comparten al menos una celda tocada. El conteo de aquí nunca es menor |
| `s2_hueco_max_dias_jun_oct` | 117 de 197 | T03 mide el hueco solo entre observaciones con nubosidad de 20 % o menos y sin contar los extremos del periodo; aquí se usan todas las observaciones con dato y sí se cuentan los extremos. El de T03 sale igual o mayor: mediana de las reservadas 25 días frente a 20 |
| `pl_hueco_max_dias_jun_oct` | 126 de 197 | Lo mismo: 20 días frente a 19 |
| `ls_hueco_max_dias_jun_oct` | 106 de 197 | Lo mismo: 40 días frente a 32 |

**7 columnas de T03 sin equivalente aquí:** `etiquetas_grupo_registro` y, por cada sensor, las observaciones despejadas y los meses sin observación despejada. Estas últimas usan el corte de 20 % de nubosidad, que esta auditoría decidió no aplicar.

**Lo que tiene esta auditoría y T03 no:** la distancia de orilla a orilla, las conocidas a menos de 500 m y de 1 km, la finura de la etiqueta en el municipio, la cobertura de relieve, la calidad de contorno y los avisos.

**Dónde cambia una conclusión, y dónde no:**

| Conclusión | T03 | Esta auditoría | ¿Cambia? |
|---|---|---|---|
| Reservadas en municipios con parcelas conocidas | 59 de 59 | 59 de 59 | No |
| Reservada con una sola conocida en su municipio | AGC_120 | AGC_120 | No |
| Reservadas a más de 1 km de una conocida | 7 | 7 | No |
| Conocidas a más de 1 km de otra conocida | 21 | 21 | No |
| Reservadas en celda de lluvia sin conocidas | 2 (AGC_174 y AGC_147) | 1 (AGC_174) | Sí, por la definición |

En el último renglón, AGC_147 tiene su centro en una celda donde no cae el centro de ninguna conocida, pero hay una conocida cuyo contorno sí alcanza esa celda. Las dos cifras son correctas con su definición.

**Sobre la decisión que T03 tomó con su diagnóstico.** T03 eligió su escenario principal de evaluación porque todas las reservadas están en municipios conocidos, no están más aisladas que las conocidas y muy pocas caen en celdas sin ejemplos. El diagnóstico independiente da esas mismas tres lecturas. No se revisó el resto de T03: las particiones, el protocolo y la regla de decisión quedan fuera de este trabajo.

**Dos diferencias que no son de cifras, para decidir con el equipo:**

- **El nombre `grupo_registro`.** El dato es idéntico, pero el nombre afirma un origen de registro que el plan del equipo (O5) pide no afirmar. Aquí se guarda como `cultivo_origen`.
- **Los nombres de columna.** T03 usa `ID_POLIGONO` y `area_ha`; el contrato de datos y esta auditoría usan `id_parcela` y `area_ha_origen`.

**Comprobaciones adicionales, hechas solo en la carpeta local:** segunda corrida leyendo el dataset desde la copia del repositorio y la tabla de T03 tal como está en `main` (con fin de línea de Mac/Linux): las tres tablas salieron idénticas byte a byte. La huella guardada de la tabla de T03 se calcula sin retornos de carro, para que dé lo mismo en cualquier sistema.

**Límites:**

- Se comparó una sola tabla de T03 (`soporte_parcelas.csv`). No se compararon `soporte_resumen.csv` ni `particiones.csv`.
- Que las dos versiones coincidan dice que ninguna tiene un error de cálculo en lo comparado; no dice cuál definición conviene más. Eso es una decisión del equipo.
- La tolerancia para dar por iguales dos números con decimales fue de 0.05.

**No se hizo:** no se modificó ningún archivo de T03 ni del repositorio, no se usó Git para escribir, no se entrenó ningún modelo y no se modificó ningún archivo original.

### 5 de octubre de 2026 — Tres observaciones sobre T03 y cierre de la etapa 8

Una integrante del equipo señaló tres observaciones sobre el protocolo de T03. Se comprobaron contra los archivos del repositorio, solo en lectura. **Las tres son correctas. Son observaciones sobre T03, no sobre esta auditoría, y no cambian ningún resultado de aquí.**

| Observación | Qué se comprobó |
|---|---|
| El protocolo dice que las cinco repeticiones del escenario espacial dan la misma asignación | No es así: en `particiones.csv` hay cinco agrupaciones distintas. Los dos grupos grandes (34 parcelas cada uno) se repiten; los otros tres cambian, aunque siempre miden 24, 23 y 23 |
| Falta la regla para los municipios con muy pocas etiquetas | Tepeapulco, Nanacamilpa y Apan tienen una sola parcela conocida. En las cinco repeticiones, AGC_047, AGC_048 y AGC_164 se evalúan sin ningún ejemplo de su municipio; también ocurre en las particiones internas. El protocolo menciona respaldos, pero no fija la regla para cada candidato |
| Falta especificar cómo se calculará la incertidumbre respetando la cercanía | El protocolo remuestrea las 138 parcelas como independientes; el plan del equipo (O4) pide respetar la dependencia espacial |

**Evidencia de esta auditoría que sirve para la segunda y la tercera:** entre las 59 reservadas, la falta de ejemplos del municipio toca a una sola (AGC_120, etapa 7); AGC_164 tiene el mismo rendimiento que sus dos vecinas pegadas de otro municipio (etapa 4); y las parcelas no son independientes: 7 de 8 pares de vecinas de la escritura `Cebada` comparten rendimiento (etapa 4) y hay 37 pares con orillas a menos de 5 m (etapa 2).

**Lo que la comparación de la etapa 8 no cubrió:** las particiones, la selección interna y el cálculo de la incertidumbre de T03. La coincidencia encontrada vale para la tabla de soporte, no para el protocolo completo.

**Decisión de Jass:** el plan de esta auditoría no cambia. Se añade un límite a la etapa 5 (arriba, en su apartado) y esta nota. La revisión de T03 sigue fuera de este trabajo.

**Jass aprobó las columnas de las tablas de comparación y cerró la etapa 8 el 5 de octubre.**

### 6 de octubre de 2026 — Cierre (etapa 9): repetición completa e informe

**Qué se hizo, en orden:**

1. **Repetición desde cero.** En una carpeta vacía, fuera del proyecto, se reprodujo la estructura del repositorio (`analisis/auditoria_catalogo_y_etiquetas/scripts/`, la tabla de revisión de contornos en `analisis/exploracion_parcelas_qgis/` y la tabla de T03 en `registro/t03/`) y se corrieron los cinco scripts en orden, con sus opciones por omisión y leyendo el dataset de `data/` del repositorio.
2. **Comprobado:** los cinco terminaron sin errores ni advertencias y las 15 tablas salieron idénticas byte a byte a las de esta carpeta.
3. **Comprobado:** los 168 archivos originales del dataset siguen idénticos a las huellas del 3 de octubre.
4. Se escribió [informe_catalogo_y_etiquetas.md](informe_catalogo_y_etiquetas.md) con la respuesta, los hallazgos, las recomendaciones, los límites y cómo repetir todo.

**Qué hay en esta carpeta al cierre:**

| Carpeta o archivo | Contenido |
|---|---|
| `README.md` | Entrada corta para el equipo (solo en el repositorio) |
| `bitacora.md` | Esta bitácora (en la carpeta local se llama `README.md`) |
| `informe_catalogo_y_etiquetas.md` | El informe de cierre |
| `diccionario_columnas.md` | Definición de cada columna de cada tabla |
| `scripts/` | Cinco scripts |
| `tablas/` | Quince tablas |

**Orden de los scripts:** `construir_catalogo.py`, `cruzar_contorno_y_rendimiento.py`, `senalar_parcelas_extremas.py`, `diagnosticar_soporte.py` y `comparar_con_soporte_t03.py`.

**Sobra:** la carpeta `scripts/__pycache__/`, creada sin querer en la etapa 5. Se puede borrar.

**Pendiente de esta etapa:** que Jass revise el informe; definir con ella qué se copia al repositorio y con qué ajustes; actualizar el registro de decisiones local de Jass cuando ella lo pida.

### 6 de octubre de 2026 — Copia al repositorio

**Jass aprobó el informe** y copió la carpeta completa de su carpeta local a esta ubicación del repositorio, en la rama `feature/auditoria-catalogo-y-etiquetas`.

**Comprobado antes de ajustar:** los 24 archivos copiados eran idénticos byte a byte a los del original.

**Ajustes hechos solo en esta copia del repositorio:**

- La bitácora, que en la carpeta local se llama `README.md`, pasó a llamarse `bitacora.md`, con una nota inicial para el equipo. Las referencias a documentos de trabajo locales se reescribieron como «una auditoría previa», sin rutas ni números de sección.
- Se añadió un `README.md` corto para el equipo.
- En el informe y en el diccionario se cambiaron las mismas referencias y los enlaces a la bitácora.
- Los scripts y las tablas no se tocaron.

**Ajuste hecho en las dos carpetas:** dos comentarios de los scripts que mencionaban el nombre del archivo de la bitácora y un documento local. No cambia ningún cálculo; así los cinco scripts son idénticos en ambas carpetas.

**Comprobado después de ajustar,** desde la raíz del repositorio y con el entorno del `requirements.txt`: los cinco scripts corren con sus opciones por omisión y las 15 tablas salen idénticas a las copiadas.

**El original de esta auditoría se mantiene en la carpeta local de Jass.** Si algo cambia, se cambia ahí primero y se vuelve a copiar aquí.
