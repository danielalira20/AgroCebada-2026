# T15 · contrato técnico E2: relieve local de INEGI

16 de octubre de 2026. Responsable: Dani. Rama `t15-e2-contrato-inegi`, desde la entrega E1/Q `ce287cd`. **Especificación preparada antes de extraer E2 y de generar sus OOF. No es un permiso de ejecución completa ni una mejora demostrada.** No se atribuye aprobación a los compañeros. Dani autorizó preparar el contrato y revisar alternativas sin esperar revisiones externas.

## Problema que resuelve

La altura y pendiente anteriores no describen necesariamente si una parcela está por encima o debajo de su entorno inmediato, ni su exposición direccional. La [factibilidad INEGI](t15_inegi_factibilidad.md) ya acreditó acceso y cobertura; faltaba definir exactamente fórmulas, unidades, bordes, orientación, calidad e integración para no convertir errores geográficos en una supuesta mejora del modelo.

## Solución que implementa este contrato

Una representación compacta de **tres atributos**, obtenida con la misma regla para las 197 parcelas: posición topográfica relativa a 150 m y dos componentes de exposición que combinan orientación e inclinación. Se mantiene el procedimiento común v3 y se registra por separado la combinación con E1 y un control de disponibilidad. [Contrato estructurado](../registro/t15_e2/contrato_tecnico_v1.json), [diccionario propuesto](../registro/t15_e2/diccionario_propuesto.csv) y [comprobación previa del diseño](../registro/t15_e2/preflight_diseno.json).

Son propuestas técnicas cerradas para implementar y comprobar; el JSON conserva `ejecutable=false`. No existen todavía la tabla E2 ni nuevos resultados de rendimiento. T03, T07, el estimador v3 y las entregas anteriores permanecen intactos.

## 1. Fuente, geodesia y alcance temporal

Original: INEGI CEM 3.0, capa `cem30_workespace:cem3_r15`, TIFF regional de 29,003,701 bytes, SHA256 `5f315dd32f7984c0c8f0bdd12f8bc22c014fd097473e2497e30d3be6f648be95`. Se conserva en `data/raw/externos/inegi/cem3_r15_region.tif`, ignorado por Git. Se fijan también los cinco archivos del shapefile original y las fuentes comunes por huella. No se descarga otra edición automáticamente si una fuente cambia.

Se respeta **EPSG:4326 declarado por el archivo servido** y se transforma a **EPSG:32614**, con orden x/y explícito y PROJ sin red. No se reasigna el datum histórico ITRF92 de la ficha al archivo actual. La unidad vertical se atribuye a la ficha del producto, que especifica metros; el campo de unidad del TIFF está vacío. No se inventa una transformación vertical.

El producto existía en 2013, pero no está acreditado que los bytes descargados en 2026 fueran los mismos disponibles en octubre de 2025. E2 se declarará **covariable retrospectiva**, con esa limitación. La precisión vertical nominal y el datum no se convierten en certeza sobre desniveles pequeños. Las tres fórmulas son invariantes ante un desplazamiento vertical constante; esto no elimina errores espaciales del DEM, errores horizontales ni incertidumbre de medición.

## 2. Rejilla, remuestreo y memoria

Rejilla norte arriba de **15 × 15 m UTM**, alineada a múltiplos enteros de 15 desde (0,0). Límites: transformar los del TIFF con 21 puntos de densificación por lado y redondear mínimos hacia abajo y máximos hacia arriba. La rejilla planeada tiene **3,703 × 3,507 celdas**; su transformación está fijada en el registro. Una diferencia no se ajusta manualmente hasta obtener esa forma: se explica y versiona.

Se reproyecta **una sola vez**, bilineal, en float64; NoData de salida −9999 y máscara separada. La interpolación de una máscara 0/1, sin renormalizar ausencias, debe dar soporte ≥1−1e−12. No se convierte el −32768 original en altura ni se permite que GDAL complete silenciosamente un vecindario con los pocos datos restantes. El soporte válido se comprueba de nuevo después del remuestreo.

El cálculo focal precede al recorte de cada parcela. TPI necesita hasta diez celdas alrededor; Horn, una. Se fija halo de diez celdas por bloque y **210 m de margen de fuente alrededor de las parcelas**, incluyendo espacio de intersección y remuestreo. Esta comprobación de geometría ya pasó en las 197, ampliando los 175 m de la primera factibilidad. La disponibilidad del margen no sustituye la comprobación posterior de la máscara reproyectada.

Procesamiento por bloques de 256 celdas, caché GDAL 32 MiB, un hilo y VM de 768 MiB. Los rasters derivados van a disco, no a matrices gigantes simultáneas. El original no se modifica. Cambiar tamaño de bloque no debe cambiar el interior calculado.

## 3. Atributo 1: posición relativa a 150 m

Para cada centro de celda se consideran los desplazamientos enteros `(dr,dc)` que cumplen `0 < dr²+dc² ≤100`: **316 vecinos**, excluyendo el centro. La distancia se mide sobre la rejilla UTM de 15 m; no es un radio geodésico exacto. No se buscan otros radios.

`TPI150 = z_centro − suma(z_316_vecinos)/316`.

Es una diferencia de altura en metros: positiva por encima del entorno, negativa por debajo. La media del vecindario da igual peso a sus celdas UTM; la agregación posterior de la parcela sí usa intersecciones por área. Deben ser válidos el centro y los 316 vecinos. No se ignoran NoData ni se completan bordes, y no se divide por una desviación estándar casi nula.

No se usará directamente `gdaldem TPI`, cuyo vecindario es distinto, ni `r.neighbors` sin retirar el centro de su promedio. La definición completa evita esa ambigüedad. TPI no mide acumulación de agua, humedad ni encharcamiento; tampoco es TWI.

## 4. Atributos 2–3: exposición direccional estable

La propuesta inicial hablaba de medias de seno/coseno de orientación sin ponderar por inclinación. **Se precisa ahora, antes de extraer o evaluar E2**, para evitar imponer orientación fuerte en zonas casi planas y tener que escoger un umbral de pendiente.

Para el vecindario norte arriba:

```text
a b c
d e f
g h i

p = ((c+2f+i) − (a+2d+g)) / (8×15)    # dz/dEste UTM
q = ((a+2b+c) − (g+2h+i)) / (8×15)    # dz/dNorte UTM
```

Son derivadas Horn; las nueve celdas deben ser válidas. Se registra el factor de escala local `k` y la convergencia de meridianos `γ` de PROJ, convirtiendo γ de grados a radianes. Se exige una transformación conforme disponible, sin ballpark, y `|k−1|≤0.001`; una operación no disponible detiene el proceso.

```text
D = sqrt(1 + (k×p)² + (k×q)²)
E = (−k×p×cosγ − k×q×sinγ) / D
N = ( k×p×sinγ − k×q×cosγ) / D
```

Equivalen a `sin(inclinación)×sin(azimut verdadero)` y `sin(inclinación)×cos(azimut verdadero)`. Signos: Este/Norte positivos, Oeste/Sur negativos. Un plano da **(0,0) observado**, sin inventar azimut norte. Se mantienen componentes en [−1,1], con norma ≤1. No son radiación solar medida, temperatura o humedad.

Se promedian los componentes por área; no se promedian azimuts ni se normaliza el vector resultante para forzarlo a longitud uno. Su cancelación puede reflejar distintas exposiciones o superficies planas: pendiente y fracción plana se guardan como QA, sin añadirlas automáticamente al modelo. La representación tiene antecedentes en análisis ambiental [Ramji et al., 2024](https://doi.org/10.5061/dryad.2rbnzs7x4); no es una innovación universal nueva ni evidencia de rendimiento de cebada.

La comprobación previa comparó los signos de la rotación con desplazamientos geodésicos norte/este de un metro en nueve puntos de prueba de la región. Diferencia máxima 2.32e−9, tolerancia fijada 1e−7; convergencia regional aproximada 0.116–0.292 grados y escala 0.999617–0.999698. Son pruebas del sistema de ejes, no atributos extraídos de parcelas.

## 5. Agregación física y cobertura

Se densifican los segmentos geográficos a un máximo de 0.0001 grados antes de transformar geometrías; sin reparar, ajustar con snap, agrandar parcelas ni unir vecinas. Una geometría inválida detiene el cálculo.

Para cada celda, `a_i = área(P ∩ celda_i)` en EPSG:32614. Contacto sólo por línea o punto tiene peso cero. `w_i=a_i/suma(a_i válidas)`; cada atributo de parcela es `suma(w_i×valor_i)`. La suma de intersecciones debe conciliar el área del polígono con tolerancia relativa 1e−8. Son áreas métricas UTM; se registra su pequeña distorsión, sin presentarlas como áreas elipsoidales exactas.

**No se promedian todos los píxeles tocados por igual.** El criterio `all_touched` de factibilidad sólo era QA. Una parcela que cruza dos celdas con 80 % y 20 % recibe esos pesos, y un borde común no aporta área doble. Parcelas distintas se procesan por separado, sin disolverlas.

La primera versión exige cobertura ≥1−1e−8 para cada atributo en **las 197 parcelas**. Es una tolerancia geométrica; no permite una pérdida material de cobertura. Si alguna falla, se conservan ID, vacío y motivo en la salida de diagnóstico, pero **no se evalúa esta versión**. No se eliminan filas ni se añade de improviso imputación E2. La cobertura ya comprobada hace razonable esta condición, sin garantizarla antes de reproyectar.

## 6. Tabla y modelo

Salida futura: una fila por `id_parcela`, con `e2_tpi150_media_m`, `e2_exposicion_este_media` y `e2_exposicion_norte_media`. Son atributos estáticos; no se duplican como observaciones nuevas por mes o ventana. Se conserva 197/138/59 y se une por ID, sin escribir sobre T07. CSV UTF-8/LF, números finitos con 17 cifras significativas; ninguna columna se llena con datos ficticios para anticipar la entrega.

Los metadatos, áreas, cobertura, conteos y sensibilidades son QA, no predictores por defecto. Columnas constantes se conservan; su escalado y el resto de transformaciones se aprenden sólo dentro de cada entrenamiento.

La preparación E1 existente conserva mediana y bandera por entrenamiento; E2 no admite faltantes en esta versión. Después se usa **v3 sin cambios**: residuo y centrado del vector comparten el mismo pool sin la fila; las consultas usan centros guardados del entrenamiento. Se centran también E2 y las banderas. No se calcula un centro con las 197, ni con validación o reservadas; no se vuelve al R de H3. Se exige puente matemático y predictivo con S/E1/Q existentes antes de nuevas OOF.

## 7. Comparaciones, presupuesto y decisión

| Procedimiento propuesto | Columnas numéricas | Promovible |
|---|---:|---|
| E2 = S + relieve E2 |8|Sí|
| E12 = S + E2 + valor E1 + bandera E1 |10|Sí|
| E2Q = S + E2 + bandera E1 |9|No: control|

El control E2Q evita atribuir a NDWI una ganancia que proceda de su disponibilidad al combinarlo con relieve. Su inclusión aumenta explícitamente el presupuesto respecto a la propuesta de sólo dos procedimientos. No se reescribe el contrato anterior para ocultar ese incremento.

Cada procedimiento conserva dos ventanas × cuatro λ [0.01,0.1,1,10], α=n del entrenamiento×λ, cuatro divisiones internas y referencia sola. A/B × cinco repeticiones × cinco particiones externas: **4,800 Ridge internos**, hasta 600 referencias internas si no se cachean y **150 ajustes externos** en total. Hasta 4,140 OOF nuevas. S, E1 y referencia se reutilizan sólo si sus huellas y métodos coinciden; de lo contrario se detiene y registra el cambio. No se adopta el mejor modelo de cada parcela.

Se fijan siete contrastes: E2−referencia, E12−referencia, E2−S, E12−E2, E12−E1, E12−E2Q y E2Q−E2. Con A/B y todas/sin_respaldo son 28 filas de contraste. La combinación se activa por cobertura, QA y coste **antes de conocer el MAE E2**; no sólo si E2 gana individualmente.

La regla T03 se conserva: principal A/sin_respaldo, ΔMAE≤−0.01, IC95 por celdas con extremo superior <0, al menos 4/5 repeticiones mejores y ΔRMSE≤+0.01. B, sin24 y casos individuales no eligen ganador. Se reportan también R² y sesgo, con denominadores y ponderaciones explícitos.

**Protección adicional propuesta para esta familia:** al haber dos candidatos promovibles, exigir también que el intervalo espacial individual de 97.5 % de cada contraste frente a la referencia quede por debajo de cero: percentiles 1.25/98.75 de las mismas 5,000 réplicas y semilla 20261006. Es una guardia Bonferroni más conservadora, fijada antes de resultados, además de T03; no modifica retrospectivamente las reglas de T15/E1. El bootstrap con pocos bloques no garantiza un control exacto de error familiar. Tampoco borra las muchas exploraciones anteriores del proyecto.

Entre candidatos elegibles, menor MAE redondeado a seis decimales; empate a E2 por menor complejidad. Si ninguno cumple, se mantiene la referencia. No se cambia MAE por RMSE al ver el resultado.

## 8. Pruebas y puertas de ejecución

Antes de OOF: plano, rampas cardinales, cuenco analítico, desplazamiento constante de Z, signos norte/este y convergencia, circularidad 359°/1°, norma vectorial, intersección parcial y borde sin área, propagación de NoData bilineal/focal, invariancia por tamaño de bloque y auditor de las 197 agregaciones independiente del productor. Las superficies analíticas son pruebas de fórmulas, **no rendimientos simulados ni nuevas observaciones**.

Se prevé QA descriptiva desplazando las geometrías ±15 m en Este/Norte, sin ajustar la fuente ni elegir la variante por rendimiento. El original sigue siendo la única geometría candidata. Esta sensibilidad no estima una incertidumbre horizontal real conocida.

La extracción canónica futura será en Docker Linux/amd64. La repetición Mac debe concordar en TPI dentro de 1e−6 m y componentes dentro de 1e−9, con IDs y estados exactos. El entrenamiento utilizará el mismo CSV canónico fijado: **no se amplía la tolerancia OOF de 1e−12** para disimular diferencias de extracción entre equipos. Fechas, huellas y particiones son exactas.

Para ejecutar faltan: extractor y QA; tabla canónica con huella; adaptador/modelo y auditor independiente verificados; registro operativo que fije sus códigos y entradas; solicitud de evaluación completa. Las puertas permanecen falsas. Publicar este contrato tampoco habilita esas etapas.

## 9. Entregas y límites

Se entregarán al implementar: TIFF métrico y derivados locales inmutables; tabla E2 y calidad por ID; pesos/intersecciones locales; manifiesto con fuentes, CRS, pipeline, unidades, algoritmo y soporte; auditoría independiente; pruebas y diferencias Mac/Linux. Sólo tras pasar esa etapa se generarán selecciones, estados, trazas y reportes de evaluación.

Fuera de este contrato: TWI/SPI, drenaje, radios adicionales, nuevas curvaturas, otra familia de modelo, suelo/radar/clima diario, cambios de etiquetas o eliminación de extremos, predicciones finales de las 59 y T16. La [investigación de alternativas](t15_e2_alternativas_fundamentadas.md) prepara decisiones posteriores, no amplía silenciosamente esta comparación.

## Fuentes y apoyo

[GDAL: pendiente, orientación y vecindarios](https://gdal.org/en/stable/programs/gdaldem.html); [Rasterio: reproyección explícita](https://rasterio.readthedocs.io/en/stable/topics/reproject.html); [PROJ/pyproj: factores cartográficos](https://pyproj4.github.io/pyproj/stable/api/proj.html); [GRASS: vecindarios y centro incluido](https://grass.osgeo.org/grass-stable/manuals/r.neighbors.html). Las fórmulas y tolerancias de este contrato son decisiones explícitas del equipo, no valores universales recomendados por esas herramientas. Datos/licencia y límites históricos en el informe de factibilidad INEGI.

Apoyo de GeoPandas, scikit-learn y pensamiento crítico científico. Kassis, T.; Agarwal, V.; He, Y.; Patel, D.; Brueckner, A. M. (2026), [Scientific Agent Skills](https://doi.org/10.48550/arXiv.2609.00065), registro vigente v2 verificado el 16-oct-2026. Procedimiento de apoyo, no certificación externa ni evidencia predictiva.
