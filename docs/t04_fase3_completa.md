# T04 · Extracción completa y revisión de calidad

Dani · Revisora independiente: Jass · 6 de octubre de 2026.

Estado: puntos 3.4–3.6 y revisión técnica de fase 4 terminados localmente. Borrador de PR preparado. T04 pendiente de conciliación con T02 aceptada y revisión independiente de Jass. No hubo commit, push ni publicación de PR.

Dani autorizó continuar con centroide, fases siguientes y ejecución completa, resolviendo los problemas encontrados. La base metodológica y la corrección de áreas de los puntos 3.1–3.3 se conservan en [el informe anterior](t04_fase3_puntos_1_3.md).

## Resultado

Se generaron **28,368 registros reales**: 197 parcelas × 48 meses (2022–2025) × lluvia, Tmin y Tmax. Cada fila identifica parcela, periodo, variable, unidad, mapa, soporte, áreas, cobertura, estado y comparación con centroide. El detalle contiene **33,120 registros de valores de celda** y **460 intersecciones de soporte** para 394 pares parcela/cuadrícula.

Se procesó el maestro original `data/raw/DataSet.zip` con huella `d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5`. No se usaron rendimientos para extraer, seleccionar el piloto ni analizar sensibilidad. Se conservaron originales, copias QGIS, código/particiones de T03, dependencias e instrucciones privadas.

Las ejecuciones locales son:

| Ejecución bajo `data/processed/t04/` | Alcance |
| --- | --- |
| `20261006_piloto` | Nueve parcelas × cinco meses × tres variables = 135 filas. |
| `20261006_completa_a` | Primera extracción histórica de 28,368 filas. |
| `20261006_completa_b` | Repetición independiente en otra carpeta, con las mismas entradas/código. |

Las ejecuciones previas de comprobación siguen preservadas. Las carpetas finales sólo aparecen después de validar sus archivos exportados. Los datos y la evidencia siguen ignorados por Git.

## 3.4 · Centroide y reglas de celda

Se conserva la definición de T03: geometría original EPSG:4326, transformación a EPSG:6372, centroide planar y vuelta a EPSG:4326. Se guarda longitud/latitud del punto, si está dentro de la parcela, fila/columna por cuadrícula, valor consultado, estado y diferencias con la media por área.

Las diferencias se expresan en mm/mes o °C, mediante `diferencia_media_menos_centroide` y `diferencia_abs_centroide`. No se aplican porcentajes relativos en Celsius. Un punto fuera del mapa o sobre NoData conserva el motivo y valor vacío; no se busca una celda vecina ni se sustituye el centroide.

### Regla de bordes protegida

`scripts/t04_control.py:celda_punto` usa los intervalos de los bordes originales, equivalentes a redondear hacia abajo en coordenadas de píxel. Un borde interno pertenece a la derecha/abajo; el límite exterior superior/izquierdo está incluido y el inferior/derecho queda fuera.

Dividir diferencias de coordenadas por el tamaño de píxel puede convertir un borde representable en 0.99999999999994. La búsqueda ordenada en los bordes nativos evita esa ambigüedad sin desplazar el punto ni introducir un epsilon espacial. Las pruebas verifican bordes exactos y sus vecinos inmediatos representables, incluidos los de la transformación real. En la comprobación de las esquinas de la cuadrícula de lluvia, la inversión utilizada por Rasterio no presentó diferencias; esta protección no implica que los centroides de T03 estuvieran mal.

Se contrastaron las **197 asignaciones de celda de centroide** con `registro/t03/soporte_parcelas.csv`: **cero diferencias**. T03 no se modificó.

### Hallazgo geométrico

Los centroides de **AGC_078, AGC_152 y AGC_182** quedan fuera de su propio polígono. Esto puede ocurrir por la forma cóncava de una parcela y no invalida automáticamente su geometría ni la media ponderada. Se conserva la definición acordada y se marca `centroide_dentro_parcela=False`, visible en cada registro y en el resumen de revisión. No se sustituyeron por puntos interiores. Todos los centroides reales están dentro del mapa y tienen dato válido en estos 144 insumos.

## 3.5 · Piloto antes de producción

La selección se hizo únicamente a partir de geometría, soporte y máscaras, antes de calcular las medias del piloto. Se incluyeron:

| Parcela | Razón |
| --- | --- |
| AGC_014 y AGC_065 | Referencias de fase 2: dos celdas y una celda. |
| AGC_047 | Mayor área geométrica. |
| AGC_091 | Menor área geométrica. |
| AGC_123 | Mayor número de celdas intersectadas. |
| AGC_174 | Menor intersección positiva, investigada por precisión. |
| AGC_143 y AGC_191 | Casos investigados en el contraste de áreas. |
| AGC_078 | Primer ID con centroide fuera de la parcela. |

Meses: enero de 2022, 2023 y 2024, julio y diciembre de 2025. Las reglas, desempates y selección quedan en `manifest.json`. El piloto incluyó 135 registros y 225 detalles de celda, con cobertura completa.

No existen huecos, multipartes, falta de cobertura espacial ni NoData parcial/total sobre las parcelas reales de estos insumos. Las máscaras tampoco cambian entre meses dentro de cada variable. No se inventaron ejemplos reales para esas categorías: se mantienen sus controles sintéticos y la prueba de cambio de máscara.

El piloto pasó el refinamiento de áreas, el contraste independiente LAEA y la reconstrucción CSV. La diferencia máxima de media al refinar fue 9.9475983e-12; frente a LAEA, 3.0935922e-8, ambas inferiores al límite 1e-6 en la unidad de su variable. Las seis referencias de julio de fase 2 se conservaron dentro de la tolerancia documentada previamente. El resumen del piloto se presentó a Dani antes de ejecutar todo; la aprobación independiente sigue pendiente.

La inspección QGIS ya confirmada por Dani para AGC_014/065 y la copia de trabajo se conserva como evidencia visual. Los tres nuevos casos de centroide exterior quedan identificados para que Dani/Jass puedan inspeccionarlos en QGIS; no se atribuye esa inspección a una acción que no se haya realizado.

## 3.6 · Producción, controles y reproducción

Cada ejecución verifica el conjunto exacto de claves esperado y registra huellas de originales, mapas, geometrías y **tres archivos de código**, incluyendo el núcleo espacial y el controlador. También conserva commit base, Python, dependencias, versiones de PROJ/GDAL, método y parámetros.

`validar_exportacion` vuelve a leer las tablas y comprueba:

- Las 28,368 claves, sin ausencias, extras ni duplicados.
- Referencias de soporte/mapa y correspondencia de ID, cuadrícula, celda, área, peso y unidades.
- Valores y máscaras contra las matrices originales, además de reconstrucción de medias a partir del CSV.
- Áreas válida/NoData, pesos normalizados, coberturas brutas y estados de ausencia.
- Punto e índices del centroide, valor original, estado y diferencias exportadas.

Se aplican tolerancias de suma de pesos y reconstrucción absoluta de **1e-12**; el contraste de medias por refinamiento/LAEA conserva **1e-6** en la unidad de cada variable. Son tolerancias numéricas; no se eligieron filtros de cobertura ni decisiones agronómicas.

| Control | Resultado en las dos ejecuciones completas |
| --- | --- |
| Claves históricas | 28,368 correctas; cero duplicados o faltantes. |
| Estado climático | 28,368 con cobertura válida completa. |
| Medias y centroides ausentes | Cero en estos originales. |
| Reconstrucción de la media desde CSV | Diferencia máxima cero en este equipo. |
| Contraste de valores/máscaras con originales | Aprobado. |
| Refinamiento 0.0005° → 0.00025° | Diferencia máxima de media 5.2551741e-11. |
| Media con áreas independientes LAEA | Diferencia máxima 7.8369851e-8. |
| Contraste de áreas completas/intersecciones | Error relativo máximo 4.6184162e-8, inferior a 1e-6. |
| Suite de pruebas | 48 pruebas aprobadas. |
| Conservación de originales, T03 y QGIS | Huellas verificadas sin cambios. |

La cobertura completa se refiere al área de las parcelas. El porcentaje válido del ráster completo puede ser mucho menor porque incluye terrenos exteriores a estas parcelas. Los blancos visibles en QGIS no implican por sí solos faltantes en nuestra tabla.

### Reproducción

A y B produjeron archivos **idénticos byte por byte**: `clima_parcela_mes.csv`, `soporte_celdas.csv`, `valores_celdas.csv`, `soportes.json`, `controles_soporte.json`, `controles.json` y `estado.json`. Los manifiestos sólo difieren en fecha UTC, duración y pico de memoria, propios de cada ejecución. Entradas, código, parámetros y dependencias coinciden.

Esta reproducción corresponde al Mac Apple Silicon de Dani. No acredita Mac Intel/Windows. En otra plataforma se exigirán las mismas claves/estados y se medirán diferencias numéricas; referencias iniciales: 1e-6 relativo para áreas y 1e-6 absoluto para medias en su unidad. No se declara comprobada una plataforma no ejecutada.

### Recursos medidos

Medición externa de todo el proceso, incluida exportación/verificación:

| Ejecución | Duración | RSS máximo del proceso |
| --- | --- | --- |
| Piloto | 3.47 s | 164.02 MB |
| Completa A | 9.18 s | 305.09 MB |
| Completa B | 7.91 s | 310.36 MB |

La cifra de memoria en el manifiesto se mide antes de exportar; los valores de la tabla vienen de la medición externa y abarcan la ejecución entera. Las 144 matrices y máscaras ocupan 3.37 MB. El consumo total incluye Python, GeoPandas, tablas y controles. No se inició Docker ni se instalaron dependencias. No queda un proceso de extracción en ejecución.

## Fase 4 · Sensibilidad y observaciones de calidad

Se analizaron las tablas terminadas con el apoyo de Spreadsheets y su Python incluido. Se conserva la tabla de extracción como fuente y se generan resúmenes de lectura en CSV; no se creó otro motor de cálculo en Excel.

En **31 parcelas** hay al menos una diferencia absoluta entre media por área y centroide superior a 1e-6 en la unidad de su variable. Ese límite sólo distingue diferencias numéricas en el resumen; no es un filtro de calidad ni una prueba de mejor rendimiento predictivo. La mediana de la diferencia es cero en las tres variables.

| Variable | Registros | Diferencias > 1e-6 | Diferencia absoluta máxima | Caso máximo |
| --- | --- | --- | --- | --- |
| Lluvia | 9,456 | 1,412 | 45.36351586 mm/mes | AGC_145, 2025-09 |
| Tmin | 9,456 | 1,440 | 0.26831823 °C | AGC_059, 2025-07 |
| Tmax | 9,456 | 1,440 | 0.19634562 °C | AGC_059, 2025-08 |

### Investigación del caso de lluvia

AGC_145 cruza dos celdas en septiembre de 2025:

| Celda | Lluvia, mm/mes | Peso físico |
| --- | --- | --- |
| 36_27 | 196.58642578125 | 0.6640674382737086 |
| 37_27 | 331.6239929199219 | 0.3359325617262914 |

El centroide consulta la primera celda. El promedio de ambas, con sus pesos físicos, da **241.94994164 mm/mes**, de ahí la diferencia de 45.36351586. Valores y áreas fueron contrastados con el original, refinamiento y LAEA. La diferencia es explicable por soporte espacial; no se eliminó ni imputó.

### Conciliación espacial con T03

Las parcelas intersectan **29 celdas distintas en cada cuadrícula**, de modo que muchas comparten fuente climática. Se preparó `celdas_compartidas.csv`, con número de parcelas e IDs por celda, y una tabla de celdas de lluvia con áreas positivas en más de una partición espacial de T03.

Por repetición de T03 se observaron **11, 8, 11, 7 y 11 celdas compartidas entre particiones espaciales**. Esto confirma la observación previa: agrupar sólo por celda del centroide no garantiza separación de todas las celdas usadas por el promedio ponderado. El efecto y las reglas del experimento se concilian con Migue/Jass antes de modelar; no se cambiaron las particiones ni se descartaron intersecciones pequeñas para ocultarlo.

### Archivos para revisión humana

Bajo `reports/t04_fase4_20261006/`:

- `resumen_por_variable.csv`: tres filas con cobertura, faltantes y diferencias, conservando unidad.
- `resumen_por_parcela_variable.csv`: 591 filas (197 × tres variables), para localizar casos por ID.
- `casos_para_revisar.csv`: mayores diferencias por variable y tres centroides fuera de parcela.
- `celdas_compartidas.csv`: soporte común por cuadrícula/celda.
- `celdas_compartidas_entre_particiones_t03.csv`: evidencia para la conciliación espacial.
- `resumen.json` y `revision.md`: controles, reproducción, resultados y pendientes.

Evidencia de piloto/producción: `reports/t04_fase3/20261006_piloto_completa/`. Las figuras/resultados de QGIS anteriores permanecen intactos.

## Fase 5 · Revisión y preparación del PR

Se preparó localmente un título, descripción, validaciones y lista concreta de archivos propuestos para publicar. No se creó todavía un PR en GitHub porque publicar requiere el push previamente autorizado por Dani. La propuesta incluye código, pruebas, documentación y registros de T04; excluye todos los datos, reportes, proyectos QGIS, instrucciones privadas y skill personal.

Antes de cerrar T04: conciliar IDs/geometrías con T02 aceptada y obtener la revisión independiente de Jass. La versión exacta/disponibilidad histórica de productos sigue no documentada; seleccionar ventanas para T09/T07 requiere su protocolo, no basta con que un mes esté extraído. No se inició modelado ni se rellenaron las 59 etiquetas.

## Reproducir

En el entorno local activado y desde la raíz del repo:

```sh
python -m unittest discover -s tests -v
python scripts/extraer_clima.py --paquete data/raw/DataSet.zip --salida data/processed/t04/piloto_<nombre_nuevo> --piloto
python scripts/extraer_clima.py --paquete data/raw/DataSet.zip --salida data/processed/t04/completa_<nombre_nuevo> --completa
```

Sustituir `<nombre_nuevo>` por un nombre de ejecución sin los signos `< >`. Las carpetas existentes se rechazan para conservar resultados. El modo `--piloto` fija la selección mediante las reglas documentadas; `--completa` utiliza las 197 parcelas y los 48 meses. No combinarlos con selección manual de IDs/periodos. Los CSV usan UTF-8, punto decimal, precisión de float completa y campo vacío para valor ausente.

El nombre histórico `filas_muestra` del breve mensaje de consola cuenta las filas de cualquier ejecución. En producción el alcance autoritativo está explícito en `manifest.json` y `controles.json:exportacion.filas_clima`; no significa que los 28,368 registros sean sintéticos.
