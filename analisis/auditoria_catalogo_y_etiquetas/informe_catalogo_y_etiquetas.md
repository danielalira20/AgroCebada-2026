# Informe: catálogo de parcelas y auditoría de la etiqueta de rendimiento

**Tarea T02 del plan del equipo.** Responsable: Jass. Revisora: Dani. Trabajo realizado el 5 y 6 de octubre de 2026. Este informe cierra la auditoría; el detalle de cada etapa y de cada decisión está en la [bitácora](bitacora.md) y la definición de cada columna en el [diccionario](diccionario_columnas.md).

No se entrenó ningún modelo, no se modificó ningún archivo original del dataset y no se excluyó ni se corrigió ninguna parcela.

---

## 1. Respuesta breve

1. **El catálogo es confiable.** Las 197 parcelas están identificadas sin repetir y unidas una a una con su contorno; 138 tienen rendimiento y 59 no. Ningún contorno está repetido ni encimado con otro.
2. **El rendimiento está anotado con tres niveles de finura,** según el municipio: en escalones de 0.5, de 0.1 y de 0.01 t/ha. Donde está anotado grueso, las parcelas vecinas suelen compartir el mismo valor.
3. **Tres de los rendimientos más altos del conjunto vienen de las parcelas menos confiables:** muy pequeñas y con contorno dudoso.
4. **Hay 7 parcelas extremas.** Las altas y las bajas no se parecen: las altas son diminutas y dan menos confianza; dos de las bajas son vecinas pegadas y parecen un hecho real de campo.
5. **Las 59 parcelas reservadas están tan respaldadas como las 138 conocidas.** 32 no tienen ningún aviso y 5 son claramente más frágiles.
6. **El diagnóstico de soporte coincide con el de T03** en todo lo que ambos miden igual; las diferencias se deben a la definición usada.

---

## 2. Qué pedía la tarea y dónde quedó

| Lo que pide el plan para T02 | Dónde está | Resultado |
|---|---|---|
| 197 ID únicos unidos 1:1 a las geometrías; 138 etiquetas y 59 ausentes | `tablas/catalogo_parcelas.csv`, `tablas/comprobaciones_catalogo.csv` | Cumplido; 60 de 60 comprobaciones |
| Unidades y áreas | Catálogo, columnas de área | El área está en hectáreas y es el área del contorno redondeada (sección 3.2) |
| Municipio | Catálogo | Copiado tal cual; no se verificó contra límites oficiales |
| Duplicados y solapamientos | Comprobaciones | Ninguno en los 19 306 pares |
| Precisión y procedencia de la etiqueta | `tablas/precision_etiqueta_por_municipio.csv` | Tres niveles de finura (sección 3.3) |
| Conservar `Cebada`/`CEBADA` como metadato original | Catálogo, columna `cultivo_origen` | Conservado sin atribuirle efecto ni protocolo |
| Diagnóstico de soporte de las 59 frente a las 138 | `tablas/soporte_por_parcela.csv`, `tablas/soporte_resumen_por_municipio.csv` | Sección 3.6 |
| Artefacto mínimo auditable | Cinco scripts, quince tablas y las huellas de los archivos leídos | Sección 6 |

Además de lo pedido: el cruce entre calidad de contorno y rendimiento (3.4), las parcelas extremas con su contexto (3.5) y la comparación con el diagnóstico de T03 (3.7).

---

## 3. Hallazgos

Cada hallazgo indica qué está comprobado y qué es sospecha.

### 3.1 Identidad

**Comprobado.** El CSV de rendimiento y el shapefile tienen las mismas 197 parcelas, de AGC_001 a AGC_197, sin repetir. El conjunto y el área, que vienen en los dos archivos, coinciden en las 197. Las 138 con rendimiento son exactamente las de ENTRENAMIENTO. Puebla tiene 100 parcelas (71 conocidas y 29 reservadas), Hidalgo 51 (36 y 15) y Tlaxcala 46 (31 y 15).

### 3.2 Geometría y área

**Comprobado.**

- Los 197 contornos son válidos, de una sola pieza, sin huecos y cerrados. Ningún par se encima ni se toca.
- **El área registrada es el área del contorno, redondeada a dos decimales, en las 197 parcelas.** La mayor diferencia es de 0.005 ha.
- **Hay parcelas prácticamente pegadas:** 9 pares con orillas a menos de 1 m y 37 a menos de 5 m. Los 9 pares más cercanos se revisaron sobre la imagen satelital: en todos se trata de dos terrenos distintos.
- Las dos escrituras del campo `Cultivo` se dibujan distinto: `Cebada` tiene una mediana de 5 puntos por contorno y coordenadas de 6 decimales; `CEBADA`, 34 puntos y coordenadas más largas.

**Sospecha.** Que el área se calculó a partir del mismo contorno y no se midió aparte en campo. Ningún documento de FIRA lo dice.

**Consecuencia.** El área no es un dato independiente del contorno: en las 22 parcelas con contorno B o C (13 conocidas y 9 reservadas), el área hereda el defecto. Sigue sin saberse qué superficie se usó como denominador del rendimiento.

### 3.3 Precisión y procedencia de la etiqueta

**Comprobado.**

- El rendimiento va de 2.0 a 5.59 t/ha, con media 3.955 y mediana 4.34. Hay 67 valores distintos.
- **Tres niveles de finura:**

| Escalón | Municipios | Escritura | Parcelas conocidas |
|---|---|---|---:|
| 0.5 t/ha | Calpulalpan, Emiliano Zapata | `Cebada` | 33 |
| 0.1 t/ha | Singuilucan | `CEBADA` | 16 |
| 0.01 t/ha | Chignahuapan, Almoloya, Cuautepec de Hinojosa | `CEBADA` | 86 |

- Apan, Nanacamilpa y Tepeapulco tienen una sola parcela conocida; su finura no se puede determinar.
- La escritura no equivale a la finura: Singuilucan es `CEBADA` y está anotado más grueso que el resto de esa escritura.
- **Donde el rendimiento está anotado grueso, las vecinas comparten valor.** Entre pares de parcelas conocidas con orillas a menos de 20 m: 7 de 8 pares de la escritura `Cebada` y 2 de 5 de Singuilucan tienen exactamente el mismo rendimiento; en los municipios de escalón 0.01, 0 de 32.

**Sospecha.** Que en esos municipios se anotó un mismo valor para varias parcelas contiguas, por ejemplo las de un mismo productor. No hay identificador de productor ni documento que lo confirme, y los pares son pocos. No se afirma un protocolo de medición distinto ni se atribuye efecto agronómico a la escritura.

**Consecuencia, si fuera así.** En esos municipios habría menos mediciones reales que parcelas; el error de cualquier estimación no puede leerse igual que en los municipios de etiqueta fina (un error de 0.2 t/ha está por debajo de lo que la etiqueta distingue); y al separar parcelas para evaluar, una vecina con el mismo valor puede quedar del otro lado.

**Sigue sin saberse.** Cómo se midió el rendimiento, con qué humedad y sobre qué superficie.

### 3.4 Calidad de contorno y rendimiento

La regla de lectura se fijó por escrito antes de mirar el resultado.

**Comprobado.**

- Dentro de su municipio, las 13 parcelas conocidas con contorno B o C rindieron en promedio 0.356 t/ha más que las de contorno A. Una diferencia así aparece por casualidad en 0.9 de cada 100 repartos al azar. Según la regla fijada, se ve una diferencia.
- **La diferencia está casi toda en tres parcelas de Chignahuapan:** AGC_127 (B, 5.57 t/ha, 0.91 ha), AGC_049 (C, 5.53 t/ha, 0.87 ha) y AGC_055 (C, 5.45 t/ha, 1.37 ha), cada una alrededor de 1 t/ha por encima de su municipio. En Calpulalpan no hay ninguna diferencia y en Almoloya es pequeña. En la mediana casi no la hay.
- Las divisiones internas, los árboles dentro y las parcelas angostas no muestran diferencia.

**Cómo debe leerse.** No como «un contorno dudoso da más rendimiento», sino como: tres parcelas muy pequeñas con contorno dudoso están entre los rendimientos más altos del conjunto.

**No comprobado.** La causa. El tamaño solo no lo explica (3.5). La prueba usada trata a las parcelas de un municipio como intercambiables y no modela su cercanía.

### 3.5 Parcelas extremas

Se llama extrema a la parcela conocida que queda a más de 1 t/ha del promedio de las demás conocidas de su municipio.

**Comprobado.** Hay 7 extremas: cuatro bajas (AGC_171, AGC_015 y AGC_024 en Chignahuapan; AGC_034 en Singuilucan) y tres altas (AGC_049, AGC_127 y AGC_162, en Chignahuapan). Tres parcelas no se pueden juzgar por ser las únicas conocidas de su municipio (AGC_047, AGC_048 y AGC_164).

- **Las altas:** los cinco rendimientos más altos de Chignahuapan van juntos, de 5.45 a 5.59. Cuatro de las cinco parcelas miden menos de 1.4 ha y tres tienen contorno B o C. No forman una zona: están a entre 1.5 y 4 km entre sí, y sus vecinas rinden lo normal.
- **Las bajas:** AGC_171 (2.15) y AGC_024 (3.03) son vecinas con las orillas a 0.92 m, miden unas 11.5 ha cada una y tienen contorno A. Sus vecinas promedian 4.2.
- **El tamaño:** en Chignahuapan, las parcelas pequeñas con contorno A están en el promedio del municipio (−0.009); las de más de 5 ha quedan 0.23 t/ha por debajo.

**Sospecha.** Que en las parcelas diminutas la cifra de t/ha sea frágil, porque un pequeño error de superficie la mueve mucho; y que a las dos bajas pegadas les haya ocurrido algo real en campo.

**Diferencia con una auditoría previa,** que listaba nueve extremas: las siete de aquí están entre esas nueve. AGC_048 no tiene aquí con quién compararse y AGC_069 queda a +0.997 t/ha, tres milésimas por debajo del umbral.

### 3.6 Soporte de las 59 reservadas

**Comprobado.**

| Medida | 59 reservadas | 138 conocidas |
|---|---|---|
| En municipio con parcelas conocidas | 59 de 59 | — |
| Distancia entre centros a la conocida más cercana (mediana; máxima) | 350.5 m; 1 915.6 m | 399.8 m; 4 777.8 m |
| Sin ninguna conocida a menos de 1 km | 7 | 21 |
| Observaciones con dato, Sentinel-2 / Planet / Landsat (mediana) | 37 / 94 / 18 | 37.5 / 94 / 19 |
| Relieve incompleto | 0 | 5 |
| Contorno en B o C | 9 (15 %) | 13 (9 %) |

- 14 reservadas tienen una conocida con la orilla a menos de 5 m, y 35 a menos de 100 m.
- 32 reservadas no tienen ningún aviso, 22 tienen uno y 5 tienen dos o tres.
- **Las cinco más frágiles:** AGC_120 (Nanacamilpa: una sola conocida en su municipio, la más cercana a 1.3 km y de otro municipio), AGC_173 y AGC_183 (Calpulalpan: lejos de toda conocida, etiqueta gruesa y contorno B), AGC_147 (Calpulalpan) y AGC_174 (Cuautepec de Hinojosa: ninguna conocida comparte su celda de lluvia).
- Las cinco parcelas con relieve incompleto (AGC_020, 023, 044, 164 y 170) son todas conocidas.

**Límite.** El soporte dice si hay ejemplos cercanos y datos disponibles; no dice si la estimación de una parcela saldrá bien.

### 3.7 Comparación con el diagnóstico de T03

El diagnóstico de aquí se hizo sin mirar el de T03 y se comparó después.

**Comprobado.** Las 9 columnas que ambos definen igual coinciden en las 197 parcelas. En las 7 que se definen distinto, al repetir aquí la definición de T03 se obtiene su mismo valor en las 197: ninguna diferencia viene de un error. La única conclusión que cambia es la de reservadas en celda de lluvia sin conocidas (2 en T03, 1 aquí), por la definición.

**No se comparó** el resto de T03: particiones, selección interna y cálculo de la incertidumbre.

---

## 4. Recomendaciones para el equipo

Son recomendaciones; ninguna se aplicó aquí.

1. **No excluir parcelas.** Ninguna tiene un error comprobado.
2. **Llevar la calidad de contorno y el área junto a cada parcela,** como datos de calidad.
3. **Reportar los resultados de cualquier modelo con y sin las parcelas frágiles** (contorno B o C, o muy pequeñas). Si un modelo solo mejora gracias a ellas, no es una mejora real.
4. **Leer el error por separado según la finura de la etiqueta.** En los municipios de escalón 0.5, un error menor a 0.25 t/ha está por debajo de lo que la etiqueta distingue.
5. **No tratar a las parcelas vecinas como independientes** al evaluar ni al calcular incertidumbre, sobre todo en los municipios de etiqueta gruesa.
6. **Mostrar cautela en la aplicación** para las reservadas con avisos, en especial las cinco más frágiles.
7. **Añadir al contrato de datos** los campos `estado` y `cultivo_origen`, y decidir un solo nombre para el identificador y para la escritura del cultivo (T03 usa `ID_POLIGONO` y `grupo_registro`).

**Preguntas para FIRA:** cómo se midió el rendimiento y con qué humedad; qué superficie se usó como denominador; si el área del dataset se calculó a partir del contorno; si en algunos municipios se anotó un mismo valor para varias parcelas; qué significan las dos escrituras del campo `Cultivo`.

---

## 5. Límites

- La auditoría comprueba que los archivos concuerdan entre sí y describe cómo está anotado el rendimiento. No comprueba cómo se midió.
- El municipio y el estado son los declarados; no se verificaron contra límites oficiales.
- La calidad de contorno hereda los límites de la exploración en QGIS: 160 parcelas con solo una primera pasada (todas en A) e imagen de fondo sin fecha conocida.
- Las comparaciones de rendimiento dentro del municipio informan poco en Calpulalpan, donde el rendimiento solo toma tres valores.
- Varios hallazgos descansan en pocas parcelas: 13 en B o C con rendimiento, 8 pares de vecinas de la escritura `Cebada`, 3 parcelas en el cruce de contorno.
- Los umbrales (1 t/ha para extremas; 5 conocidas, 1 km y 99 % para los avisos) son convenciones.
- «Observación con dato» no significa observación limpia: no se aplicó corte de nubosidad.
- Las 59 reservadas no tienen rendimiento a la vista; nada de lo dicho sobre la etiqueta se pudo comprobar en ellas.

---

## 6. Dónde está la evidencia y cómo repetirla

| Qué | Dónde |
|---|---|
| Entrada corta para el equipo | `README.md` |
| Bitácora completa, con cada decisión y su motivo | `bitacora.md` |
| Definición de cada columna | `diccionario_columnas.md` |
| Catálogo de las 197 parcelas (22 columnas) | `tablas/catalogo_parcelas.csv` |
| Las 60 comprobaciones y 46 conteos del catálogo | `tablas/comprobaciones_catalogo.csv` |
| Finura de la etiqueta por municipio | `tablas/precision_etiqueta_por_municipio.csv` |
| Cruce de contorno y rendimiento | `tablas/cruce_contorno_rendimiento.csv`, `cruce_contorno_por_municipio.csv`, `cruce_contorno_parcelas_b_c.csv` |
| Desviación de cada parcela conocida y extremas | `tablas/desviacion_municipal_por_parcela.csv`, `desviacion_por_tamano.csv` |
| Soporte por parcela y resumen | `tablas/soporte_por_parcela.csv`, `soporte_resumen_por_municipio.csv` |
| Comparación con T03 | `tablas/comparacion_con_t03.csv`, `comparacion_con_t03_por_parcela.csv` |
| Huellas de los archivos leídos | `tablas/huellas_archivos_leidos.csv`, `huellas_archivos_leidos_soporte.csv`, `huellas_archivos_leidos_comparacion.csv` |

**Para repetirla,** con Python 3.12 y las dependencias del `requirements.txt` del repositorio, desde la raíz del repositorio y en este orden:

```sh
python analisis/auditoria_catalogo_y_etiquetas/scripts/construir_catalogo.py --datos data/DATASET_RETO_AGRO_2026
python analisis/auditoria_catalogo_y_etiquetas/scripts/cruzar_contorno_y_rendimiento.py
python analisis/auditoria_catalogo_y_etiquetas/scripts/senalar_parcelas_extremas.py
python analisis/auditoria_catalogo_y_etiquetas/scripts/diagnosticar_soporte.py --datos data/DATASET_RETO_AGRO_2026
python analisis/auditoria_catalogo_y_etiquetas/scripts/comparar_con_soporte_t03.py --datos data/DATASET_RETO_AGRO_2026
```

El dataset debe estar descomprimido. El primer script y el último buscan por omisión la tabla de revisión de contornos y la tabla de T03 en su lugar dentro del repositorio; si están en otro sitio, se indican con `--contornos` y `--t03`.

**Comprobación de cierre (6 de octubre).** Se repitió todo desde cero en una carpeta vacía con la misma estructura del repositorio y los cinco scripts con sus opciones por omisión: las 15 tablas salieron idénticas byte a byte. Después de copiar la carpeta al repositorio se repitió desde su raíz, con el mismo resultado. Los 168 archivos originales del dataset siguen idénticos a como estaban el 3 de octubre.

**Si una tabla no sale igual:** comparar primero las huellas de los archivos leídos. Si no coinciden, la diferencia está en la copia del dataset y no en los scripts.
