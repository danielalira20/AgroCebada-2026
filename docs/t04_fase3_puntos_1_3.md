# T04 · Fase 3: puntos 1, 2 y 3

Responsable: Dani. Revisora: Jass. Fecha: 6 de octubre de 2026.
Estado: implementación y comprobación técnica local de 3.1–3.3. T04 sigue en curso.

Dani autorizó estos tres puntos y la resolución de problemas encontrados. Se implementaron la verificación de entradas, el soporte físico para todas las parcelas y el motor mensual. La comprobación real del motor usa AGC_014 y AGC_065 en julio de 2025, tres variables: seis filas. El centroide (3.4), el piloto formal (3.5), la extracción completa y su reproducción (3.6) siguen pendientes.

## 1. Entradas verificadas

`scripts/extraer_clima.py` lee `data/raw/DataSet.zip` sin extraer ni modificar el maestro. Comprueba nombres duplicados y CRC de los ZIP, las 144 claves de mapa esperadas (48 meses por variable), metadatos, transformación, CRS, banda, tipo, NoData y valores válidos. Valida 197 geometrías poligonales, únicas y válidas, y su correspondencia por ID con el catálogo original. Conserva literalmente los IDs; no los genera ni une por posición.

El paquete usado tiene SHA256 `d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5`. Los 144 mapas son Float32, una banda, EPSG:4326, NoData -9999. Se verificaron dos cuadrículas nativas de 65 × 72, conservando sus transformaciones completas. El desplazamiento entre lluvia y temperatura requiere soportes diferentes. Tmin y Tmax se contrastaron celda a celda en sus 48 meses sobre valores válidos comunes; no se encontró Tmin > Tmax. Si en otro insumo difieren sus cuadrículas, se registra que esa comparación no se puede hacer directamente y se calculan soportes separados, sin remuestrear.

Del CSV de catálogo se leen únicamente `ID_POLIGONO` y `AREA_HA`; no se cargan ni utilizan rendimientos. El área declarada se mantiene como `area_ha_origen`, aparte de `area_parcela_m2`. Los originales tienen 197 Polygon, sin huecos ni multipartes; esas formas se cubren con pruebas sintéticas.

El manifiesto registra huellas de TIFF y geometrías, referencias dentro de los ZIP, metadatos, parámetros, dos archivos de código, commit base, Python, dependencias y versiones nativas de GDAL/PROJ. Esto identifica también el código que todavía no tiene commit. Versión del producto y disponibilidad histórica permanecen «no documentadas». La conciliación con T02 aceptada sigue pendiente.

## 2. Soporte físico y corrección de precisión

Se generaron 394 soportes: 197 parcelas × dos cuadrículas, con 460 intersecciones de área positiva. Cada soporte identifica la geometría original, CRS, transformación, dimensiones, método y paso de integración. Las celdas se obtienen mediante intersección en la cuadrícula original. Contactos lineales/puntuales aportan cero; ninguna intersección positiva se elimina por ser pequeña.

Todos los soportes reales tienen cobertura espacial completa. La clasificación se comprueba geométricamente, mediante la extensión del mapa, en vez de deducirla de un cociente casi igual a uno. Se conservan los cocientes brutos; sus extremos medidos fueron 0.9999999999978246 y 1.0000000000012161. `area_fuera_mapa_m2` es cero cuando la extensión cubre geométricamente la parcela: un residuo numérico no se presenta como terreno sin cobertura.

### Problema detectado durante la ampliación

El cálculo Geod de fase 2 había aprobado las dos parcelas de referencia y las áreas completas. Al contrastar **también cada intersección**, apareció pérdida de precisión:

| Caso | Área calculada inicialmente, m² | Referencia LAEA inicial, m² | Diferencia relativa |
| --- | --- | --- | --- |
| AGC_143, temperatura, celda 31_33 | 127.89845395187149 | 127.89831637736438 | 1.07565534e-6 |
| AGC_174, lluvia, celda 29_32 | 0.001631291328521911 | 0.001625643588293228 | 0.00347415649 |
| AGC_174, temperatura, celda 29_32 | 0.00493836474197451 | 0.004928959114652442 | 0.00190823805 |

La primera ejecución se detuvo antes de publicar la carpeta de resultados. Reducir el paso Geod por sí solo no resolvió las intersecciones diminutas de AGC_174. Son triángulos reales recortados por el borde de una celda, no errores de topología ni contactos de área cero. La diferencia porcentual de estas áreas diminutas no equivale a una diferencia del mismo tamaño en el promedio de toda la parcela.

### Resolución en `area_fisica` de `scripts/t04_espacio.py`

Se reemplazó la evaluación Geod de área por integración estable de la superficie WGS84 sobre los bordes lineales nativos. La versión queda explícita: `wgs84_borde_lineal_cuadratura8_v2`; los soportes anteriores no comparten su identidad de método. El respaldo del núcleo anterior se conserva en la evidencia local.

Se integra la densidad superficial `M × N × cos(latitud)`, donde `M` y `N` son los radios de curvatura del elipsoide. Equivale a `a²(1-e²)cos(φ)/(1-e²sin²(φ))²`. Un abanico de triángulos con signo conserva anillos cóncavos, y los huecos se restan. La cuadratura Gauss–Legendre de ocho nodos por dirección evalúa esta función suave. Las diferencias de coordenadas se toman antes de convertirlas a radianes, evitando la resta de contribuciones geodésicas grandes para obtener áreas diminutas.

Esta corrección conserva la magnitud física acordada, los bordes originales y las cuadrículas. Se mantiene el paso 0.0005° y su contraste 0.00025° para verificar la integración; la subdivisión sólo vive en el cálculo de área. No modifica geometrías guardadas, imágenes, resolución, filtros, particiones o tolerancias. No requiere dependencias nuevas.

Se contrastaron las áreas completas **de los 197 polígonos y las 460 intersecciones** mediante LAEA elipsoidal, con bordes a 0.0001°, centrada localmente para reducir errores numéricos de la propia referencia. Es un procedimiento distinto del integrador. [PROJ documenta LAEA y su forma elipsoidal](https://proj.org/en/stable/operations/projections/laea.html).

El error relativo máximo, considerando contraste independiente y refinamiento, fue **4.618416202523308e-8**, inferior a la tolerancia 1e-6. El máximo corresponde a una intersección de AGC_191, lluvia, celda 30_34. AGC_174 conserva sus pequeñas áreas: 0.0016256435781776713 m² en lluvia y 0.004928959069581078 m² en temperatura. Se añadió una prueba con el triángulo real de AGC_174 para proteger esta corrección.

## 3. Motor mensual y casos sin dato

`cargar_entradas` lee cada matriz climática una sola vez. Mantiene esas matrices pequeñas en memoria y cierra los archivos; `extraer` reutiliza las matrices y los soportes sin volver a abrir un ráster por parcela. Las 144 matrices y sus máscaras ocupan 3,369,600 bytes, aproximadamente 3.37 MB; esta cifra no representa la memoria total de Python/GeoPandas ni es la medición del piloto formal. Se trabajó en `.venv`, sin iniciar Docker ni cambiar dependencias.

En cada mapa se valida su máscara. Para cada parcela se normalizan los pesos entre áreas válidas y se calcula la media espacial. Los pesos válidos suman uno dentro de 1e-12; la media se comprueba contra el rango de los valores utilizados. Los pesos geométricos no se modifican al aplicar una máscara mensual.

| Estado | Media y tratamiento |
| --- | --- |
| `cobertura_completa` | Media con geometría cubierta y todas las celdas utilizadas válidas. |
| `cobertura_parcial` | Media sobre áreas válidas; motivo distingue fuera del mapa, NoData o ambos. |
| `sin_cobertura_espacial` | Clave conservada, media vacía, áreas intersectada/válida y cobertura cero. |
| `todo_nodata` | Clave conservada, media vacía, intersección positiva pero área válida cero. |

Un mapa legible completamente NoData también se conserva. Este caso se separa de la regla histórica del inventario de fase 1, que rechazaba mapas sin valores: se usa el validador del extractor, sin debilitar silenciosamente el inventario anterior. Un archivo corrupto, una clave ausente/duplicada, CRS/metadatos inesperados, geometría inválida, precipitación válida negativa o valor válido no finito detienen el proceso. No se capturan excepciones genéricas para convertir errores en faltantes.

Lluvia es la media espacial de acumulados mensuales en mm/mes; temperatura, la media espacial del promedio mensual de extremos diarios en °C. NoData no se sustituye por cero ni se eligen umbrales de cobertura para modelado.

### Comprobación real de seis filas

| ID | Julio 2025: lluvia, mm/mes | Tmin, °C | Tmax, °C |
| --- | --- | --- | --- |
| AGC_014 | 144.24070970529212 | 13.446963202665529 | 22.990844239824458 |
| AGC_065 | 120.25041198730469 | 12.716031074523926 | 22.677114486694336 |

Frente a fase 2, la diferencia máxima fue 8.195561918e-8 mm/mes; las temperaturas difirieron como máximo 2.374299868e-9 °C. Las seis filas cumplieron también el contraste de medias con áreas LAEA y paso refinado dentro de 1e-6 en su unidad. Su reconstrucción desde el CSV de celdas dio diferencia cero en este equipo. Son controles de esta muestra técnica; la comprobación de todas las medias reales sigue pendiente.

### Archivos locales y protección de ejecuciones

La verificación final está en `data/processed/t04/20261006_verificacion_3_1_3_3_v2/`. Se conservó la primera comprobación exitosa en otra carpeta: la versión final agrega trazabilidad del entorno. No se sobrescribieron esas ejecuciones. Los dos intentos que fallaron antes de exportar no dejaron una carpeta presentada como aprobada.

- `manifest.json`: entradas, metadatos, entorno, código, parámetros, alcance y pendientes.
- `soportes.json`: 394 soportes con áreas parcelarias y área declarada; también puede representar soporte sin celdas.
- `soporte_celdas.csv`: 460 filas de soporte, con fila/columna, área, peso e identidad del método.
- `controles_soporte.json`: contraste independiente y refinamiento de todos los soportes.
- `clima_parcela_mes.csv`: seis filas reales, estados, motivo, unidades, áreas, coberturas y enlaces a mapas/soportes.
- `valores_celdas.csv`: valores, validez y pesos utilizados en esas seis filas.
- `estado.json`: alcance técnico explícito y `cierre_t04: false`.

CSV en UTF-8, decimales con punto, precisión completa de los floats; valor ausente = campo vacío. `valida` y `cobertura_espacial_completa` se exportan como `True`/`False`. Los valores -9999 enmascarados no aparecen como observación válida ni participan en la media. Ambas áreas están identificadas por su unidad: hectáreas de origen frente a m² calculados.

La carpeta final sólo aparece tras escribir todos sus archivos en una carpeta temporal. Se rechaza una salida existente y la consola limita el destino a una ejecución nueva bajo `data/processed/t04/`. Un fallo de escritura elimina la carpeta temporal. La publicación aquí es sólo local: datos y reportes siguen ignorados por Git.

## Pruebas y reproducción del alcance autorizado

Pasaron **37 pruebas**: 20 existentes y 17 nuevas. Cubren unión por ID, faltantes/duplicados, estados, máscaras, límites/huecos/multipartes, cambio de geometría/cuadrícula/parámetros, metadatos y valores inválidos, escritura fallida y precisión de la intersección diminuta. Una prueba sintética verifica 197 × 48 × 3 = 28,368 claves y conserva las 144 claves de una parcela sin cobertura. Esto comprueba el motor; no es la producción real completa.

En el entorno local activado, desde la raíz del repo:

```sh
python -m unittest discover -s tests -v
```

Para verificar entradas y soporte sin extraer meses:

```sh
python scripts/extraer_clima.py --paquete data/raw/DataSet.zip --salida data/processed/t04/preparacion_<nombre_nuevo>
```

Para una muestra técnica explícita, usar otra carpeta nueva:

```sh
python scripts/extraer_clima.py --paquete data/raw/DataSet.zip --salida data/processed/t04/muestra_<nombre_nuevo> --ids AGC_014 AGC_065 --periodos 2025-07
```

Sustituir `<nombre_nuevo>` por un identificador de ejecución sin los signos `< >`; las carpetas existentes se preservan. El modo de preparación verifica todos los soportes y entradas aunque la selección de meses sea pequeña.

La evidencia de esta fase vive en `reports/t04_fase3/20261006_puntos_1_3/`: estado previo, respaldo del núcleo/registros, incidencias, log de pruebas, controles de muestra, comparación de áreas y verificación final de archivos protegidos.

## Próximo punto

Continuar con 3.4: comparación con centroide según el plan. Después seleccionar el piloto por geometría/soporte/máscaras, medir recursos y revisar sus resultados; sólo entonces generar y reproducir los 28,368 registros reales. Siguen pendientes la conciliación con T02 aceptada y la revisión independiente de Jass. No se hicieron commit, push, PR ni mensajes a otras personas durante estos puntos.
