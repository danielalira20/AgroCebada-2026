# T05 · Relieve: método de extracción por parcela

Responsable: Jass. Revisora: Dani. Fecha: 8 de octubre de 2026.
Estado: **método congelado como base de implementación, script sin escribir.** Este documento fija qué se calculará y cómo se comprobará. Los cambios posteriores deben responder a un fallo reproducible, a una prueba o a un requisito incumplido. Las decisiones de uso están en D020 de `registro/decisiones.csv`.

## Qué se entrega y cuándo se cierra T05

Elevación y pendiente por parcela (197 IDs), con su cobertura válida, número de celdas, detalle por celda, comparación con el centroide y avisos de calidad. La variable se entrega trazable; **T05 no promete que mejore el modelo.** Eso se comprueba en T10.

**T05 se cierra con la extracción principal y sus controles.** La tabla de sensibilidad (pendiente con hueco rellenado) es una ampliación: no condiciona el cierre.

## Entradas

- `Elevacion_INEGI_CEM4_120m.tif`: m s.n.m.
- `Pendiente_INEGI_CEM4_120m_grados.tif`: grados, método Horn 3×3 (según el LEEME de la entrega).
- Ambos en EPSG:6372 (ITRF2008 / LCC), celdas de 120 m, NoData −9999, misma cuadrícula.
- Contornos: `Parcelas_Reto_AGC_CONJUNTO.shp` (EPSG:4326). Su columna `ID_POLIGON` se lee como `id_parcela`, el nombre del contrato de datos.
- Se leen del dataset original, sin modificarlo. Se registra el SHA-256 de cada archivo, y en la procedencia: CRS, resolución y unidades de cada producto.

## Método principal

1. Reproyectar cada polígono a EPSG:6372.
2. Identificar todas las celdas con intersección de área positiva. Los contactos de borde sin área no cuentan.
3. Media de cada variable ponderada por el área de intersección **de las celdas válidas**. Las celdas NoData no entran en la media.
4. Cobertura válida = área de intersección válida / área total de la parcela, ambas en EPSG:6372. Es una fracción de 0 a 1.

**Áreas.** Se usan áreas planas en EPSG:6372, y el campo se llama `area_parcela_6372_m2` para no confundirlo con el área geodésica ni con el área del catálogo. El área plana resulta entre 0.61 % y 0.71 % menor que el área física WGS84, con una variación de solo 0.10 % entre parcelas. Eso no basta para concluir nada sobre los pesos, así que se comprobó el efecto directo en las medias: en las 197 parcelas, ponderar con áreas físicas en lugar de planas cambia la media de elevación en menos de 0.0001 m, la de pendiente en menos de 0.00001°. La cobertura difiere como máximo 0.00003 (mediana 0.0000004), pero esa diferencia no viene de los pesos: un borde recto en EPSG:6372 no es exactamente recto en latitud y longitud, y al sumar los pedazos en el otro sistema la suma no cierra perfecto. El máximo aparece en AGC_073, una franja delgada. Como T05 calcula todo en un solo sistema, sus coberturas son coherentes. La extracción repite esta comparación y guarda los máximos en `controles.json`. Como la cuadrícula está proyectada, no se aplica la regla de O6 de áreas físicas para rejillas geográficas.

**Reutilización de T04.** `preparar_pesos` de `scripts/t04_espacio.py` exige EPSG:4326, así que no se puede usar tal cual. T05 tendrá su propio script con la misma estructura.

**Estados** (por variable): `cobertura_completa`, `cobertura_parcial`, `todo_nodata` y `sin_cobertura_espacial` (la parcela cae fuera de la cuadrícula; no es lo mismo que caer sobre NoData). Si no hay área válida, la media y los extremos quedan vacíos.

**Alternativas descartadas como principal:** valor del centroide (se usa solo como sensibilidad, lo pide O6); celdas cuyo centro cae dentro del polígono (las parcelas pequeñas se quedarían sin celdas); interpolación bilineal (estima valores entre celdas sin aportar nuevas observaciones).

## Centroide (O6)

- Se calcula sobre el polígono ya proyectado a EPSG:6372, y se toma el valor de la celda que lo contiene, sin interpolar. T02 calcula sus centroides en coordenadas geográficas, así que no se asume que ambas construcciones sean idénticas.
- `diferencia_*_centroide` = media ponderada **menos** valor del centroide.
- Si el centroide cae sobre NoData, se marca y no se desplaza. Los avisos son separados para elevación y pendiente.

## Dónde vive cada cosa

| Qué | Dónde |
|---|---|
| Código | `scripts/t05_relieve.py` |
| Pruebas | `tests/test_t05_relieve.py` |
| Tablas compartidas (las que consumen T07 y T10) | `registro/t05/`, única copia de los datos |
| Método | este documento |
| Evidencia: bitácora, informe de calidad, casos de borde, sensibilidad exploratoria y comparaciones independientes | `analisis/relieve_por_parcela/`, que se crea cuando haya la primera evidencia que guardar. Apunta a `registro/t05/` y no duplica los datos. |

**Regla:** lo que el equipo ejecuta o consume va en las carpetas del equipo; lo que explica o justifica va en `analisis/`. Las pruebas viven en `tests/` porque `unittest discover` no encuentra las que se nombran `probar_*.py` dentro de `analisis/`.

## Archivos de salida (`registro/t05/`)

Todos con fin de línea LF, CSV incluido, para no repetir el fallo del verificador de T04 con CRLF. Los valores se escriben sin redondear.

### `relieve_parcela.csv` (una fila por parcela)

| Grupo | Columnas |
|---|---|
| Identidad | `id_parcela`, `area_parcela_6372_m2`, `cobertura_espacial` (fracción del polígono dentro de la cuadrícula) |
| Elevación | `elevacion_media_m`, `elevacion_cobertura_valida`, `elevacion_celdas_intersectadas`, `elevacion_celdas_validas`, `elevacion_area_valida_m2`, `elevacion_min_m`, `elevacion_max_m`, `estado_elevacion` |
| Pendiente | `pendiente_media_grados`, `pendiente_cobertura_valida`, `pendiente_celdas_intersectadas`, `pendiente_celdas_validas`, `pendiente_area_valida_m2`, `pendiente_min_grados`, `pendiente_max_grados`, `estado_pendiente` |
| Entrada para T10 | `pendiente_media_t10_grados`: igual a `pendiente_media_grados` si la cobertura válida es ≥ 0.5; vacía si no (D020). La elevación no usa este piso. |
| Centroide | `elevacion_centroide_m`, `pendiente_centroide_grados`, `diferencia_elevacion_centroide_m`, `diferencia_pendiente_centroide_grados`, `centroide_dentro_parcela` |
| Avisos | `avisos` (lista separada por `;`) |

`*_min_*` y `*_max_*` son el mínimo y el máximo entre las celdas válidas intersectadas, a 120 m. No son el relieve real dentro de la parcela.

**Avisos y umbral de cada uno** (son diagnósticos; ninguno excluye parcelas por sí mismo):
- `pendiente_bajo_piso_50`: cobertura válida de pendiente < 0.5.
- `cobertura_parcial_elevacion` / `cobertura_parcial_pendiente`: estado `cobertura_parcial`.
- `pocas_celdas_validas`: 4 celdas válidas o menos en elevación o pendiente. Es un aviso de baja resolución espacial, no un segundo criterio de exclusión.
- `parcela_menor_a_una_celda`: área < 14 400 m² (120 m × 120 m).
- `centroide_fuera_de_parcela`, `centroide_sin_dato_elevacion`, `centroide_sin_dato_pendiente`.

El valor original de cualquier parcela bajo el piso se conserva siempre en `pendiente_media_grados`; solo la columna de T10 queda vacía.

### `relieve_celdas.csv` (una fila por parcela y celda intersectada)

Columnas: `id_parcela`, `fila`, `columna`, `area_interseccion_m2`, `elevacion_m`, `elevacion_valida`, `pendiente_grados`, `pendiente_valida`.

Como ambos TIFF comparten cuadrícula, una sola geometría de intersección guarda los dos valores y sus máscaras. Con esta tabla se puede reconstruir cualquier media y localizar exactamente el NoData (O6).

### Procedencia y verificación

`procedencia.json` (fuentes, SHA-256, CRS, resolución, unidades, método de áreas), `controles.json` y `manifest.json` con hashes de todos los archivos.

## Lista de columnas candidatas para T10

- **Candidatas:** `elevacion_media_m` y `pendiente_media_t10_grados`. T10 declara de antemano cuáles usa. El área de la parcela viene del catálogo, no de T05.
- **Solo auditoría:** pendiente original, extremos, valores y diferencias de centroide, coberturas, celdas, estados y avisos. Incorporar cualquiera de ellos al modelo requiere una decisión expresa, registrada antes de ver resultados.
- La pendiente se toma **exclusivamente** de `pendiente_media_t10_grados`. Seleccionar todas las columnas numéricas se salta D020.
- Los dos valores vacíos se tratan dentro del entrenamiento de cada partición, para no filtrar información.

## Tabla de sensibilidad (aparte, estimada)

`relieve_sensibilidad.csv`, solo para las parcelas con cobertura parcial, marcada como **estimada**. Sirve para ver cuánto cambia el resultado; **no determina cuál pendiente es la correcta.** Método fijado de antemano:

1. **Control previo:** recalcular la pendiente Horn 3×3 desde el DEM original (celda de 120 m, resultado en grados, sin cálculo de bordes) y compararla con el TIFF entregado en las celdas válidas comunes. Así se distingue una diferencia de implementación del efecto de recuperar superficie. La máscara debe coincidir exactamente con la exigencia de nueve celdas válidas.
2. **Máscara del hueco:** solo el NoData interior, es decir, los grupos de celdas sin dato **no conectados** con la gran zona exterior sin dato (conectividad de 8 vecinos). El borde del mapa no se rellena. Sobre los TIFF originales esta regla identifica 690 celdas interiores, de las cuales 687 tienen al menos 5 vecinos originales válidos.
3. **Una sola pasada:** cada celda del hueco recibe el promedio de sus vecinos válidos **originales** (mínimo 5 de 8). Los valores recién rellenados no alimentan otros rellenos.
4. **Recalcular la pendiente sobre el mapa completo**, con las celdas vecinas externas a la parcela. Recortar el DEM al polígono crearía bordes artificiales.
5. **Resumen:** media ponderada por área, igual que la principal. Contar solo las celdas rellenadas que intersectan la parcela subestima la dependencia del relleno (AGC_044 no tiene ninguna, pero 3 celdas rellenables caen en la ventana de sus vecinos y afectan su pendiente). Por eso la tabla reporta por parcela: las celdas de elevación rellenadas que influyen en su cálculo (las de la ventana 3×3 de alguna celda intersectada), la fracción del área de la parcela cuya pendiente depende de alguna altura estimada, y las coberturas de pendiente original y con relleno.
6. **Control:** las celdas rellenadas que afectan a cada parcela deben pertenecer a huecos interiores, nunca al borde exterior.

El ajuste de un plano por parcela es diagnóstico opcional, no condiciona el cierre de T05, y no es comparable de forma directa con el promedio de pendiente por celda.

## Tolerancias y qué pasa si un control falla

| Control | Tolerancia |
|---|---|
| Balance y suma de intersecciones frente a área directa | Relativa de 1e-6, la misma que usa T04 (`TOLERANCIA_AREA_REL`) |
| Cobertura frente a T02 | Diferencia máxima de 0.00005 (redondeo a 4 decimales) más 1e-9 |
| Decidir «cobertura completa» | Cobertura ≥ 1 − 1e-9; nunca igualdad exacta con 1 |
| Piso de 0.5 de la pendiente | Se aplica al valor sin redondear |

**Se detiene la entrega** (no se escriben los archivos finales): IDs duplicados o faltantes, cuadrículas no alineadas, fallo del balance de áreas, o suma de intersecciones distinta del área calculada directamente.

**Se emite aviso y la ejecución termina con diagnóstico**, pero **T05 no se da por cerrada** hasta explicar la discrepancia: diferencias con T02 mayores que la tolerancia.

## Cómo se comprobará

**Casos sintéticos** (valores y pesos de área conocidos): NoData parcial y total, contactos de borde sin área, parcela parcialmente fuera de la cuadrícula, parcela totalmente fuera, parcela menor a una celda. Para el piso: cobertura justo por debajo de 0.5, exactamente 0.5 y por encima, aplicado antes de redondear.

**Datos reales:**
- 197 IDs únicos y coincidencia con el catálogo.
- Alineación de ambos TIFF, unidades, CRS y procedencia.
- **Conservación de áreas:** área válida + área NoData dentro del mapa + área fuera del mapa = área de la parcela, dentro de la tolerancia de la sección de tolerancias. No basta con que las intersecciones no excedan el área.
- **Comprobación independiente de áreas:** la suma de las intersecciones por celda debe coincidir con el área calculada directamente como intersección entre la parcela y la extensión del ráster. Así se detectan celdas omitidas o duplicadas, que el balance anterior no vería si el área «fuera del mapa» se calculara como residuo.
- Conciliación de la cobertura con `soporte_por_parcela.csv` de T02 y con un cálculo independiente. Las coberturas de T02 están redondeadas a cuatro decimales: se compara con la tolerancia de la sección de tolerancias, no con igualdad exacta.
- Las cinco parcelas con cobertura parcial (AGC_020, 023, 044, 164 y 170) se comportan como se espera.
- Las 59 parcelas reservadas conservan cobertura completa.

**Cotejo mínimo en QGIS** (al final, antes de dar T05 por «Hecha»): con «Identificar», comparar 2–3 celdas de 2–3 parcelas contra `relieve_celdas.csv`, y mirar las cinco parcelas incompletas sobre los TIFF. Es el único control que no pasa por las mismas bibliotecas (`rasterio`, `pyproj`, `shapely`), así que protege de un error común a todas, como un desfase de fila o columna. No se usa «Estadísticas de zona» para comparar promedios: cuenta celdas por su centro y no pondera por área.

**Reproducción.** El script tendrá `--extraer` y `--verificar`, y se distinguen dos controles:
- **Integridad:** el manifiesto contiene los hashes de los archivos de entrega, exceptuando el propio manifiesto. Comprueba que los archivos publicados no cambiaron.
- **Reproducción numérica:** una nueva extracción se compara con la publicada con las tolerancias declaradas. La identidad byte a byte solo se exige si se usa el mismo entorno y una serialización determinista; el fin de línea LF ayuda, pero por sí solo no la garantiza.

La procedencia guarda además las versiones del entorno (Python y bibliotecas usadas) y los hashes de los componentes del shapefile que se leen (`.shp`, `.shx`, `.dbf` y `.prj`, es decir, geometría, atributos y proyección).

## Lo que este documento no afirma

- **La causa de la raya NoData.** Cerca de AGC_164, 170 y 023 corre en diagonal y separa parcelas de Tlaxcala y de Hidalgo. Es una **sospecha** de que coincide con una unión entre mapas estatales; no se comprobó con una capa oficial de límites.
- **El algoritmo exacto con que se generó la pendiente.** Lo verificado es que la máscara de pendiente coincide con la exigencia de las nueve celdas de elevación válidas en el interior del mapa y en los bordes, es decir, sin cálculo de bordes.
- **Que el relleno recupere una pendiente fiable.** Un desajuste de altura entre los lados de la raya puede producir cambios angulares relevantes a esta resolución, según su distribución y el algoritmo; no es un error medido.
- **Que la pendiente o la elevación mejoren la predicción.** Se evalúa en T10, con las mismas parcelas y particiones.

## Pasos siguientes

1. Revisión de este método por Dani.
2. Script `scripts/t05_relieve.py` y sus pruebas.
3. Ejecución, conciliación con T02 y tabla de casos de borde.
4. Registros y PR con la plantilla. Agregar `registro/t05/* text eol=lf` a `.gitattributes`.
5. Ampliación: tabla de sensibilidad.
6. Cotejo mínimo en QGIS, antes de dar T05 por «Hecha».
