# T04 · Diccionario de columnas

Los CSV usan UTF-8, coma como separador y punto decimal. La clave única es **(id_parcela, periodo, variable)**; un ID aparece 144 veces en la historia completa. Se conservan los números exportados con precisión completa. Un campo vacío representa ausencia, nunca cero. Las unidades de temperatura se escriben literalmente `grados Celsius`; representan °C.

## Tabla completa local · 30 columnas

Archivo: `data/processed/t04/<ejecucion>/clima_parcela_mes.csv`. La procedencia detallada y los controles de celdas están junto a él.

| Columna | Significado | Unidad/tipo | Si está vacía |
|---|---|---|---|
| id_parcela | ID original, sin renumerar ni usar posición de fila para unir. | Texto | Error estructural. |
| periodo | Mes de observación en formato YYYY-MM. No es la fecha de publicación. | Texto | Error estructural. |
| variable | PREC, Tmin o Tmax. | Categoría | Error estructural. |
| soporte_id | SHA-256 de geometría, CRS, cuadrícula y método/parámetros de área. Enlaza con soportes y detalle por celda. | Texto hexadecimal | Error estructural. |
| cuadricula_id | SHA-256 del CRS, dimensiones y transformación nativa. Lluvia y temperatura tienen cuadrículas distintas. | Texto hexadecimal | Error estructural. |
| sha256_raster | SHA-256 de los bytes del GeoTIFF original leído dentro del maestro. | Texto hexadecimal | Error estructural. |
| unidad | PREC: mm/mes; Tmin/Tmax: grados Celsius. | Texto | Error estructural. |
| area_ha_origen | AREA_HA del catálogo original. No se sustituye por área calculada. | ha | Error estructural. |
| media_ponderada | Media espacial del valor mensual, ponderada por área física de las intersecciones válidas y renormalizada sólo entre ellas. | Unidad de la variable | No existe área con dato válido; consultar estado/motivo. |
| estado | cobertura_completa, cobertura_parcial, todo_nodata o sin_cobertura_espacial. La completitud se determina por geometría y máscara. | Categoría | Error estructural. |
| area_parcela_m2 | Área física WGS84 del polígono completo, incluidos todos sus componentes y descontando huecos. Bordes lineales nativos. | m² | Error estructural. |
| area_intersectada_m2 | Suma de áreas positivas dentro de la extensión del mapa, con o sin dato. Contactos de punto/línea aportan cero. | m² | Error estructural; cero indica falta de intersección positiva. |
| area_valida_m2 | Suma de áreas de celdas no enmascaradas para ese mapa/mes. | m² | Error estructural; cero es admisible sin dato. |
| area_nodata_m2 | Área intersectada menos área válida. Sólo cubre NoData dentro del mapa. | m² | Error estructural. |
| cobertura_espacial_completa | La extensión geométrica del mapa cubre toda la parcela; no garantiza que sus celdas tengan dato. | True/False | Error estructural. |
| cobertura_espacial_bruta | area_intersectada_m2 / area_parcela_m2, sin limitar a uno. Puede superar uno por diferencias numéricas diminutas dentro de la tolerancia. | Fracción, no porcentaje | Error estructural. |
| area_fuera_mapa_m2 | Cero si la extensión cubre toda la geometría; de otro modo max(0, área de parcela − área intersectada). No equivale a área NoData. | m² | Error estructural. |
| cobertura_valida_bruta | area_valida_m2 / area_parcela_m2 sin limitar a uno. Se conserva para auditoría numérica. | Fracción | Error estructural. |
| cobertura_valida | min(1, cobertura_valida_bruta). Se refiere a la parcela completa, no sólo a su parte dentro del mapa. No impone un umbral de aceptación. | Fracción entre 0 y 1 | Error estructural; cero indica ausencia de área válida. |
| motivo | Explicación de cobertura completa, parcial por extensión/NoData, todo NoData o ausencia espacial. | Texto | Error estructural. |
| centroide_lon | Longitud del centroide calculado en EPSG:6372 y transformado a EPSG:4326, conservando la definición de T03. | Grados | Error estructural. |
| centroide_lat | Latitud del mismo punto. | Grados | Error estructural. |
| centroide_dentro_parcela | El polígono cubre el punto, incluido su borde. Un centroide puede quedar fuera en parcelas cóncavas; se conserva y señala. | True/False | Error estructural. |
| fila_centroide | Índice nativo de fila, desde cero. Puede estar fuera del rango si el punto está fuera del mapa. | Entero | Error estructural. |
| columna_centroide | Índice nativo de columna, desde cero. Bordes internos se asignan a derecha/abajo; borde exterior inferior/derecho excluido. | Entero | Error estructural. |
| centroide_en_mapa | Índices del punto dentro de las dimensiones del mapa. No garantiza dato válido ni pertenencia a la parcela. | True/False | Error estructural. |
| estado_centroide | valido, nodata o fuera_raster. | Categoría | Error estructural. |
| valor_centroide | Valor de la celda del punto, sin ponderación por parcela. Puede existir aunque el punto esté fuera del polígono. | Unidad de la variable | Centroide fuera del mapa o celda NoData. |
| diferencia_media_menos_centroide | media_ponderada − valor_centroide. El signo se conserva. | Unidad de la variable | Falta uno o ambos valores. |
| diferencia_abs_centroide | Valor absoluto de la diferencia anterior. Es diagnóstico, no una medida de exactitud predictiva. | Unidad de la variable | Falta uno o ambos valores. |

NoData de los mapas actuales es −9999: se interpreta como máscara, no se exporta como lluvia/temperatura válida ni se reemplaza por cero. La media de PREC es una media **espacial** de la precipitación acumulada de ese mes; Tmin/Tmax son valores mensuales de temperatura mínima/máxima diaria agregada según los metadatos del proveedor, no extremos absolutos del mes.

## Tabla compartida · 11 columnas

Archivo: `registro/t04/clima_parcela_mes.csv`.

Las primeras nueve columnas son `id_parcela`, `periodo`, `variable`, `unidad`, `media_ponderada`, `estado`, `cobertura_valida`, `valor_centroide` y `diferencia_media_menos_centroide`. Tienen exactamente las definiciones y reglas de vacío de la tabla anterior, y sus valores se copian literalmente. La décima, `centroide_dentro_parcela`, conserva la advertencia geométrica con la misma definición.

| Columna adicional | Significado | Tipo | Si está vacía |
|---|---|---|---|
| posterior_al_corte | El último día del mes observado es posterior al corte provisional explícito del manifiesto (actualmente 2025-10-31). No filtra filas ni certifica disponibilidad histórica: False no implica que el producto estuviera publicado. | True/False | Error estructural. |

La tabla compartida no incluye etiquetas, ventanas ni decisiones de admisibilidad. Los metadatos que se repiten en la tabla completa se conservan una sola vez en `procedencia.json`: cada (variable, periodo) identifica el mapa; cada (id_parcela, cuadricula_id) identifica el soporte/huella geométrica. `manifest.json` vincula sus huellas con los archivos fuente y con el código. Los valores por celda permanecen locales y se regeneran desde el maestro.

El diccionario de la referencia filtrada T02 está en su campo `definiciones`; contiene sólo ocho campos espaciales, no rendimiento ni conjunto. El informe de conciliación distingue la definición/redondeo T02 de las medidas T04. Véanse [entrega al equipo](t04_entrega_equipo.md) y [versión/disponibilidad](t04_version_disponibilidad.md).
