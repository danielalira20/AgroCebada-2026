# Diccionario de columnas

Define, **antes de calcular**, qué columnas tendrá cada tabla de esta auditoría, de dónde sale cada una y qué valores puede tomar. Si una columna cambia durante el trabajo, se cambia primero aquí y se anota el motivo en la bitácora.

**Estado:** aprobado por Jass el 5 de octubre de 2026. Ninguna tabla existe todavía.

## Reglas comunes a todas las tablas

- Una fila por parcela, salvo que la tabla diga otra cosa. Las tablas por parcela se unen por `id_parcela`; nunca por número de fila.
- Formato CSV, separado por comas, en UTF-8 con marca de inicio (BOM) para que Excel lea bien los acentos. En pandas: `pd.read_csv(ruta, encoding="utf-8-sig")`.
- Punto como separador decimal.
- **Celda vacía significa «no hay dato».** Nunca se escribe 0 en su lugar.
- Las respuestas de sí o no se escriben `si` / `no`, en minúsculas y sin acento, igual que en la tabla de revisión de contornos.
- Los valores que vienen del dataset se copian tal cual, sin corregir mayúsculas, acentos ni decimales.
- Las filas van ordenadas por `id_parcela`.

## Cómo se llama cada cosa en cada archivo

| En esta auditoría | CSV de rendimiento | Shapefile | Tabla de revisión de contornos |
|---|---|---|---|
| `id_parcela` | `ID_POLIGONO` | `ID_POLIGON` | `ID_POLIGON` |
| `area_ha_origen` | `AREA_HA` | `área_ha` | — |
| `rendimiento_t_ha` | `RENDIMIENTO_T_HA` | — | — |
| `conjunto_origen` | `CONJUNTO` | `CONJUNTO` | — |
| `municipio` | — | `Municipio` | — |
| `estado` | — | `Estado` | — |
| `cultivo_origen` | — | `Cultivo` | — |

Los cinco primeros nombres son los del contrato de datos del repositorio (`docs/contrato_datos.md`). `estado` y `cultivo_origen` no están en el contrato: son nombres nuevos que esta auditoría propone.

## Tabla principal: `tablas/catalogo_parcelas.csv`

197 filas, una por parcela.

### Identidad (etapa 1)

| Columna | Qué contiene | De dónde sale | Valores |
|---|---|---|---|
| `id_parcela` | Identificador de la parcela | CSV de rendimiento, comprobado contra el shapefile | `AGC_001` a `AGC_197`, sin repetir |
| `conjunto_origen` | A qué grupo la asignó FIRA | CSV de rendimiento, comprobado contra el shapefile | `ENTRENAMIENTO` (138) o `PREDICCION` (59), tal cual |
| `rendimiento_t_ha` | Rendimiento registrado, en toneladas por hectárea | CSV de rendimiento | El texto original, sin redondear ni rellenar; vacío en las 59 reservadas |
| `area_ha_origen` | Superficie registrada, en hectáreas | CSV de rendimiento, comprobado contra el shapefile | Número, tal cual |
| `municipio` | Municipio declarado | Shapefile | Texto original; no se verificó contra límites oficiales |
| `estado` | Estado declarado | Shapefile | `Hidalgo`, `Puebla` o `Tlaxcala` |
| `cultivo_origen` | Cómo viene escrito el campo `Cultivo` | Shapefile | `Cebada` o `CEBADA`, tal cual. Es un metadato original: no se le atribuye efecto agronómico ni un protocolo de medición distinto |

### Geometría y área (etapa 2)

| Columna | Qué contiene | Cómo se obtiene | Valores |
|---|---|---|---|
| `geometria_valida` | Si el contorno es un polígono válido y no vacío | Comprobación geométrica | `si` / `no` |
| `puntos_contorno` | Número de puntos con que está dibujado el contorno, contando el punto final que repite al primero | Conteo sobre el shapefile | Entero. Un cuadrilátero tiene 5 |
| `area_ha_geodesica` | Superficie calculada a partir del contorno, en hectáreas | Cálculo geodésico sobre el elipsoide WGS84 | Número |
| `diferencia_area_pct` | Cuánto difiere la superficie calculada de la registrada | 100 × (`area_ha_geodesica` − `area_ha_origen`) / `area_ha_origen` | Porcentaje, con signo |
| `centroide_lon` | Longitud del centro del contorno | Centroide del polígono, en grados WGS84 | Número |
| `centroide_lat` | Latitud del centro del contorno | Centroide del polígono, en grados WGS84 | Número |

Los duplicados, solapamientos y contactos se comprueban por pares (19 306 pares). Si no aparece ninguno, no generan columna: el resultado queda en el archivo de comprobaciones. Si aparece alguno, se añade una columna y se anota aquí.

### Calidad de contorno (etapa 3)

Todas salen de `exploracion_parcelas_qgis/revision_contornos/revision_contornos.csv`, sin recalificar nada.

| Columna | Columna de origen | Valores |
|---|---|---|
| `contorno_categoria` | `categoria` | `A`, `B` o `C` |
| `contorno_divisiones_internas` | `divisiones_internas` | `si` / `no` |
| `contorno_arboles_dentro` | `arboles_dentro` | `si` / `no` |
| `contorno_construccion_dentro` | `construccion_dentro` | `si` / `no` |
| `contorno_angosta_o_muy_pequena` | `angosta_o_muy_pequena` | `si` / `no` |
| `contorno_imagen_poco_clara` | `imagen_poco_clara` | `si` / `no` |
| `contorno_firmeza` | `etapa` | `piloto_confirmado_en_qgis`, `confirmado_en_qgis`, `revisado_en_qgis_sin_poder_confirmar` o `primera_pasada_sobre_imagen` |

La nota escrita de cada parcela no se copia al catálogo; se consulta en la tabla de origen.

### Precisión de la etiqueta (etapa 4)

| Columna | Qué contiene | Cómo se obtiene | Valores |
|---|---|---|---|
| `rendimiento_decimales` | Con cuántos decimales está escrito el rendimiento | Conteo sobre el texto original del CSV | Entero; vacío en las 59 reservadas |
| `rendimiento_multiplo_de_medio` | Si el rendimiento es un múltiplo exacto de 0.5 t/ha | Comprobación sobre el valor | `si` / `no`; vacío en las 59 reservadas |

## Tabla de precisión de la etiqueta: `tablas/precision_etiqueta_por_municipio.csv` (etapa 4)

Definida el 5 de octubre de 2026, antes de calcular. 12 filas: una por municipio (9), una por cada escritura del campo `Cultivo` (2) y una del total. Solo cuenta las 138 parcelas con rendimiento. Cambio respecto a la primera versión de este diccionario, que decía «una por municipio»: se añadieron las filas por escritura y la del total para poder comparar sin hacer cuentas aparte.

| Columna | Qué contiene | Valores |
|---|---|---|
| `agrupacion` | A qué nivel corresponde la fila | `municipio`, `cultivo_origen` o `total` |
| `grupo` | Nombre del municipio, de la escritura, o `todas` | Texto |
| `estado` | Estado del municipio | Solo en filas de municipio; vacío en las demás |
| `cultivo_origen` | Escritura del campo `Cultivo` en ese municipio | Solo en filas de municipio |
| `parcelas_conocidas` | Cuántas parcelas con rendimiento tiene el grupo | Entero |
| `rendimiento_minimo` | Menor rendimiento del grupo, en t/ha | Número |
| `rendimiento_maximo` | Mayor rendimiento del grupo, en t/ha | Número |
| `valores_distintos` | Cuántos rendimientos diferentes hay en el grupo | Entero |
| `con_0_decimales` | Parcelas cuyo rendimiento está escrito sin decimales | Entero |
| `con_1_decimal` | Parcelas cuyo rendimiento está escrito con un decimal | Entero |
| `con_2_decimales` | Parcelas cuyo rendimiento está escrito con dos decimales | Entero |
| `multiplos_de_medio` | Parcelas cuyo rendimiento es múltiplo exacto de 0.5 t/ha | Entero |
| `paso_comun` | El escalón más grande (0.5, 0.1 o 0.01 t/ha) del que todos los rendimientos del grupo son múltiplos. Indica con qué finura se anotó | `0.5`, `0.1` o `0.01`; vacío si el grupo tiene menos de 3 parcelas, porque con tan pocas no se puede saber |
| `valor_mas_repetido` | El rendimiento que más se repite en el grupo. Si hay empate, el menor | Número |
| `veces_valor_mas_repetido` | Cuántas parcelas tienen ese valor | Entero |
| `parcelas_con_valor_compartido` | Parcelas cuyo rendimiento es igual al de otra parcela del mismo grupo | Entero |

**Aviso sobre los decimales:** el CSV no guarda ceros finales (un 4.50 aparece como `4.5` y un 3.00 como `3`). Por eso contar decimales en el texto puede quedarse corto; `paso_comun` es la medida más fiable de la finura.

## Tabla del cruce: `tablas/cruce_contorno_rendimiento.csv` (etapa 5)

**Aprobada por Jass el 5 de octubre de 2026.** Escrita antes de cruzar. 7 filas: una por comparación (la principal y seis secundarias). Solo usa las parcelas conocidas. La regla completa está en la bitácora.

| Columna | Qué contiene | Valores |
|---|---|---|
| `tipo` | Si es la comparación principal o una exploratoria | `principal` o `secundaria` |
| `grupo` | Las parcelas que se examinan | Por ejemplo `B o C` |
| `referencia` | Contra quiénes se comparan | Por ejemplo `A` |
| `medida` | Qué se compara | `desviacion_municipal` (con signo) o `desviacion_municipal_absoluta` (sin signo) |
| `parcelas_grupo` | Parcelas conocidas del grupo | Entero |
| `parcelas_referencia` | Parcelas conocidas de la referencia | Entero |
| `rendimiento_medio_grupo` | Promedio directo del rendimiento del grupo, en t/ha. Solo descriptivo: mezcla municipios | Número |
| `rendimiento_medio_referencia` | Lo mismo para la referencia | Número |
| `parcelas_grupo_comparables` | Parcelas del grupo que entran en la comparación dentro del municipio | Entero |
| `parcelas_referencia_comparables` | Lo mismo para la referencia | Entero |
| `media_grupo` | Promedio de la medida en el grupo, en t/ha | Número |
| `media_referencia` | Promedio de la medida en la referencia, en t/ha | Número |
| `diferencia` | `media_grupo` menos `media_referencia`, en t/ha | Número, con signo |
| `azar_minimo` | Límite inferior de las diferencias que aparecen por casualidad (percentil 2.5 de las barajadas) | Número |
| `azar_maximo` | Límite superior (percentil 97.5) | Número |
| `casualidad_de_cada_100` | En cuántas de cada 100 barajadas aparece una diferencia igual o mayor, hacia cualquier lado | Número entre 0 y 100 |
| `lectura` | El veredicto según la regla fijada | `se ve una diferencia`, `pista`, o `no se detecta diferencia` |

## Dos tablas de apoyo del cruce, añadidas después de ver el resultado (etapa 5)

Se añadieron el 5 de octubre de 2026 **después** de conocer el resultado de la comparación principal, para poder entenderlo. Son descriptivas y no cambian el veredicto de la regla. Aprobadas por Jass el 5 de octubre.

**`tablas/cruce_contorno_por_municipio.csv`** — 8 filas: los tres municipios con parcelas conocidas en B o C, más `todos`, cada uno para el grupo `A` y para el grupo `B o C`.

| Columna | Qué contiene |
|---|---|
| `municipio` | Municipio, o `todos` (todas las parcelas conocidas con desviación municipal) |
| `grupo` | `A` o `B o C` |
| `parcelas` | Parcelas conocidas del grupo en ese municipio |
| `desviacion_media` | Promedio de la desviación municipal, en t/ha |
| `desviacion_mediana` | Mediana de la desviación municipal, en t/ha |
| `parcelas_por_encima` | Parcelas que rindieron más que el promedio de las demás de su municipio |
| `parcelas_por_debajo` | Parcelas que rindieron menos |
| `area_mediana_ha` | Mediana del área registrada, en hectáreas |

**`tablas/cruce_contorno_parcelas_b_c.csv`** — 13 filas: las parcelas conocidas en B o C. Columnas: `id_parcela`, `municipio`, `contorno_categoria`, `contorno_angosta_o_muy_pequena`, `area_ha_origen`, `rendimiento_t_ha` y `desviacion_municipal` (su rendimiento menos el promedio de las demás conocidas de su municipio, en t/ha).

## Tablas de parcelas extremas (etapa 6)

Definidas el 5 de octubre de 2026, antes de calcular. Aprobadas por Jass el 5 de octubre.

**Qué se llama «extrema» (fijado antes de calcular):** una parcela conocida cuyo rendimiento queda a más de 1 t/ha, por arriba o por abajo, del promedio de las demás parcelas conocidas de su municipio. Es el mismo umbral que usó una auditoría previa. Señalar una parcela como extrema no la excluye ni la corrige.

**`tablas/desviacion_municipal_por_parcela.csv`** — 138 filas, una por parcela conocida.

| Columna | Qué contiene | Valores |
|---|---|---|
| `id_parcela` | Identificador | `AGC_###` |
| `municipio` | Municipio declarado | Texto |
| `cultivo_origen` | Escritura del campo `Cultivo` | `Cebada` o `CEBADA` |
| `rendimiento_t_ha` | Rendimiento registrado | Texto original |
| `conocidas_en_municipio` | Parcelas conocidas de su municipio, contándola | Entero |
| `promedio_demas_municipio` | Promedio del rendimiento de las demás conocidas de su municipio, en t/ha | Número; vacío si es la única |
| `desviacion_municipal` | `rendimiento_t_ha` menos `promedio_demas_municipio` | Número con signo; vacío si es la única |
| `extrema` | Si la desviación pasa de 1 t/ha | `alta`, `baja` o `no`; vacío si es la única de su municipio |
| `area_ha_origen` | Superficie registrada | Texto original |
| `contorno_categoria` | Categoría de contorno | `A`, `B` o `C` |
| `contorno_angosta_o_muy_pequena` | Marca de la revisión de contornos | `si` / `no` |
| `conocida_mas_cercana` | La parcela conocida cuyo centro está más cerca, de cualquier municipio | `AGC_###` |
| `distancia_conocida_mas_cercana_m` | Distancia geodésica entre centros a esa parcela, en metros | Número |
| `rendimiento_conocida_mas_cercana` | Rendimiento de esa parcela | Número |
| `conocidas_a_menos_de_1_km` | Cuántas parcelas conocidas tienen su centro a menos de 1 km | Entero |
| `promedio_conocidas_a_menos_de_1_km` | Promedio del rendimiento de esas parcelas, en t/ha | Número; vacío si no hay ninguna |

**`tablas/desviacion_por_tamano.csv`** — una fila por municipio y tramo de tamaño. Sirve para ver si el tamaño de la parcela se relaciona con su desviación, y si eso ocurre también entre las parcelas en A. Incluye los municipios con al menos 10 parcelas conocidas y una agrupación `todos`. Tramos fijados antes de calcular: menos de 2 ha, de 2 a 5 ha, y más de 5 ha.

| Columna | Qué contiene |
|---|---|
| `municipio` | Municipio, o `todos` |
| `tramo_area` | `menos de 2 ha`, `2 a 5 ha` o `mas de 5 ha` |
| `parcelas` | Parcelas conocidas del tramo, con desviación municipal |
| `desviacion_media` | Promedio de la desviación municipal, en t/ha |
| `desviacion_mediana` | Mediana de la desviación municipal, en t/ha |
| `alejamiento_medio` | Promedio de la desviación municipal sin importar el signo: qué tan lejos quedan en general de su municipio, en t/ha |
| `extremas_altas` | Parcelas extremas por arriba |
| `extremas_bajas` | Parcelas extremas por abajo |
| `parcelas_en_a` | Parcelas del tramo con contorno A |
| `desviacion_media_en_a` | Promedio de la desviación municipal solo entre las de contorno A |

## Tablas del diagnóstico de soporte (etapa 7)

**Aprobada por Jass el 5 de octubre de 2026.** Escrita antes de calcular. Los criterios están en la bitácora.

**`tablas/soporte_por_parcela.csv`** — 197 filas, una por parcela. «Conocida» es una parcela con rendimiento. Para una parcela conocida, todos los conteos y distancias excluyen a la propia parcela.

| Columna | Qué contiene | Valores |
|---|---|---|
| `id_parcela` | Identificador | `AGC_###` |
| `conjunto_origen` | Grupo asignado por FIRA | `ENTRENAMIENTO` o `PREDICCION` |
| `municipio` | Municipio declarado | Texto |
| `area_ha_origen` | Superficie registrada | Texto original |
| **Municipio compartido** | | |
| `conocidas_en_municipio` | Otras parcelas conocidas en su municipio | Entero |
| `escalon_etiqueta_municipio` | Finura con que está anotado el rendimiento en su municipio (etapa 4) | `0.5`, `0.1`, `0.01`, o vacío si hay menos de 3 conocidas |
| **Cercanía** | | |
| `conocida_mas_cercana` | La conocida cuyo centro está más cerca | `AGC_###` |
| `distancia_centros_m` | Distancia geodésica entre centros a esa parcela, en metros | Número |
| `mas_cercana_en_su_municipio` | Si esa parcela es de su mismo municipio | `si` / `no` |
| `conocida_mas_cercana_por_orilla` | La conocida cuya orilla está más cerca (puede ser otra) | `AGC_###` |
| `distancia_orillas_m` | Distancia entre orillas a esa parcela, en metros (UTM zona 14 norte) | Número |
| `conocidas_a_menos_de_500_m` | Conocidas con centro a menos de 500 m | Entero |
| `conocidas_a_menos_de_1_km` | Conocidas con centro a menos de 1 km | Entero |
| **Clima compartido** | | |
| `celdas_clima_tocadas` | Celdas del mapa de lluvia que el contorno toca con alguna superficie | Entero |
| `celda_clima_principal` | La celda donde cae la mayor parte del contorno, como fila_columna | Texto, por ejemplo `30_33` |
| `fraccion_en_celda_principal` | Parte del contorno que cae en esa celda | Número entre 0 y 1 |
| `conocidas_que_comparten_celda` | Conocidas que tocan al menos una de sus celdas | Entero |
| **Disponibilidad de entradas** | | |
| `s2_observaciones_con_dato` | Observaciones de Sentinel-2 con NDVI, del 1 de abril al 31 de octubre de 2025 | Entero |
| `s2_meses_con_dato` | Meses de abril a octubre con al menos una de esas observaciones | 0 a 7 |
| `s2_hueco_maximo_dias` | Mayor número de días seguidos sin observación con dato, del 1 de junio al 31 de octubre | Entero |
| `planet_observaciones_con_dato`, `planet_meses_con_dato`, `planet_hueco_maximo_dias` | Lo mismo para Planet (NDVI) | |
| `landsat_observaciones_con_dato`, `landsat_meses_con_dato`, `landsat_hueco_maximo_dias` | Lo mismo para Landsat (VI6T) | |
| `cobertura_elevacion` | Parte del contorno que tiene dato en el mapa de elevación | Número entre 0 y 1 |
| `cobertura_pendiente` | Parte del contorno que tiene dato en el mapa de pendiente | Número entre 0 y 1 |
| **Calidad de observación** | | |
| `contorno_categoria` | Categoría de contorno | `A`, `B` o `C` |
| `contorno_mezcla_senal` | Si hay algo dentro que mezcla la señal: está en B o C, o tiene árboles o construcción dentro, o es angosta o muy pequeña | `si` / `no` |
| **Resumen** | | |
| `avisos` | Lista de avisos que le aplican, separados por punto y coma | Texto; vacío si no tiene ninguno |
| `numero_de_avisos` | Cuántos avisos tiene | Entero |

**`tablas/soporte_resumen_por_municipio.csv`** — una fila por municipio y conjunto, más las filas `todos`. Compara las reservadas con las conocidas.

| Columna | Qué contiene |
|---|---|
| `municipio` | Municipio, o `todos` |
| `conjunto_origen` | `ENTRENAMIENTO` o `PREDICCION` |
| `parcelas` | Parcelas del grupo |
| `distancia_centros_mediana_m` | Mediana de la distancia entre centros a la conocida más cercana |
| `distancia_centros_maxima_m` | La mayor de esas distancias |
| `distancia_orillas_mediana_m` | Mediana de la distancia entre orillas |
| `sin_conocida_a_menos_de_1_km` | Parcelas sin ninguna conocida a menos de 1 km |
| `celda_clima_sin_conocidas` | Parcelas cuyas celdas no comparte ninguna conocida |
| `s2_observaciones_mediana` | Mediana de observaciones de Sentinel-2 con dato |
| `planet_observaciones_mediana` | Mediana de observaciones de Planet con dato |
| `landsat_observaciones_mediana` | Mediana de observaciones de Landsat con dato |
| `relieve_incompleto` | Parcelas con menos del 99 % de cobertura de elevación o de pendiente |
| `contorno_b_o_c` | Parcelas en B o C |
| `contorno_mezcla_senal` | Parcelas con algo dentro que mezcla la señal |
| `con_algun_aviso` | Parcelas con al menos un aviso |

**`tablas/huellas_archivos_leidos_soporte.csv`** — una fila por archivo original que lee el script de soporte, con las mismas columnas que `huellas_archivos_leidos.csv`: `archivo`, `bytes` y `sha256`.

## Tablas de la comparación con el diagnóstico de T03 (etapa 8)

Definidas el 5 de octubre de 2026, antes de abrir la tabla de T03 (`registro/t03/soporte_parcelas.csv` del repositorio). Solo se conocían los nombres de sus columnas, vistos en la auditoría inicial. Aprobadas por Jass el 5 de octubre.

**`tablas/comparacion_con_t03.csv`** — una fila por columna de la tabla de T03.

| Columna | Qué contiene | Valores |
|---|---|---|
| `columna_t03` | Nombre de la columna en la tabla de T03 | Texto |
| `columna_auditoria` | Columna equivalente en esta auditoría | Texto; vacío si no hay equivalente |
| `misma_definicion` | Si las dos columnas miden lo mismo de la misma manera | `si`, `no` o `sin equivalente` |
| `parcelas_comparadas` | Parcelas con valor en ambas tablas | Entero |
| `parcelas_iguales` | Parcelas donde el valor coincide (en números con decimales, con una tolerancia de 0.05) | Entero |
| `diferencia_mediana` | Mediana de (valor de T03 menos valor de esta auditoría), en columnas numéricas | Número |
| `diferencia_maxima` | La mayor diferencia en valor absoluto | Número |
| `iguales_al_reproducir_t03` | Cuando la definición es distinta: en cuántas parcelas se obtiene el valor de T03 al repetir su definición con el script de esta auditoría. Sirve para comprobar la explicación | Entero; vacío si no aplica |
| `explicacion` | Por qué coinciden o difieren | Texto |

**`tablas/comparacion_con_t03_por_parcela.csv`** — una fila por parcela y columna donde el valor no coincide, solo para las columnas de conteo o de categoría (no para distancias, que difieren en todas por el método). Columnas: `id_parcela`, `conjunto_origen`, `municipio`, `columna_t03`, `valor_t03`, `columna_auditoria` y `valor_auditoria`.

**`tablas/huellas_archivos_leidos_comparacion.csv`** — huella de la tabla de T03 que se comparó, con las columnas `archivo`, `bytes` y `sha256`. Como esa tabla sí está en Git, el tamaño y la huella se calculan sin los retornos de carro, para que den lo mismo en Windows, Mac y Linux.

## Tablas que se definen al llegar a su etapa

Sus columnas se escriben aquí al empezar la etapa correspondiente, antes de calcular.

| Tabla | Etapa | Filas | Para qué |
|---|---|---|---|
