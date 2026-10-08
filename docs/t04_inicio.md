# T04 · Clima: estado al terminar la fase 1

Responsable: Dani. Revisora: Jass. Fecha: 6 de octubre de 2026.
Estado: en revisión técnica local. Este documento conserva la evidencia histórica de fase 1. La copia QGIS y fase 2 están en [fase 2](t04_fase2.md); el extractor completo, 48 pruebas y dos ejecuciones históricas reproducidas están en [extracción completa](t04_fase3_completa.md). Ese era el estado de fase 1; la [entrega revisada del 7 de octubre](t04_entrega_equipo.md) registra la conciliación calculada con T02 identificada y los pendientes actuales.

## Alcance verificado

Se recuperaron el inventario, sus cinco pruebas y la documentación de la preparación del 5 de octubre. El stash original se conserva. Las entradas de T04 se agregaron a los registros existentes sin sustituir las de T03.

El inventario se volvió a ejecutar en Mac Apple Silicon, Python 3.12.15, con las dependencias fijadas y sin Docker:
- Cinco pruebas aprobadas: ZIP anidado/NoData, mes ausente, mes duplicado, lluvia negativa y mapa sin celdas válidas.
- Paquete original: `data/raw/DataSet.zip`.
- SHA-256: `d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5`.
- 162 archivos finales originales, sin contar carpetas ni contenedores ZIP.
- 144 capas climáticas: 48 PREC, 48 Tmin y 48 Tmax.
- Enero de 2022 a diciembre de 2025, sin periodos ausentes, extras o duplicados.
- Las 144 capas tienen banda única, EPSG:4326, 65 columnas, 72 filas, resolución de 0.05 grados y NoData=-9999.
- Las etiquetas de variable, unidad y periodo concuerdan con los nombres de los 144 mapas.
- En los 48 pares mensuales Tmin/Tmax, las máscaras coinciden y no hay celdas válidas con Tmin > Tmax.
- El nuevo inventario coincide con el anterior salvo fecha de ejecución y ruta local del paquete.

La evidencia detallada permanece local en `reports/t04_fase1_20261006/`. Los cinco casos de prueba no comprueban aún ponderación por parcela, contactos de borde o sensibilidad frente al centroide.

## Productos y unidades

| Variable | Fuente declarada en la entrega | Qué representa | Unidad |
|---|---|---|---|
| PREC | CHIRPS | Suma de precipitación diaria del mes | mm/mes |
| Tmin | CHIRTS-ERA5 | Promedio mensual de temperatura mínima diaria | °C |
| Tmax | CHIRTS-ERA5 | Promedio mensual de temperatura máxima diaria | °C |

La versión exacta del producto y su fecha histórica de disponibilidad no están documentadas en los metadatos/LEEME revisados. Se mantendrán como no documentadas, sin deducirlas del nombre del ZIP o de la modificación del archivo.

## Dos cuadrículas nativas

Lluvia y temperatura tienen el mismo CRS, resolución y dimensiones, pero no exactamente el mismo origen:
- PREC: origen norte 21.39999957382679.
- Tmin/Tmax: origen norte 21.399999275803566.
- Diferencia: 0.0000002980232239 grados.

Hay una cuadrícula para las 48 lluvias y otra para las 96 temperaturas. La propuesta para la fase de extracción es calcular intersecciones/pesos por geometría y cuadrícula, verificando su identidad antes de reutilizarlos entre meses. No se ha implementado ni se han remuestreado mapas. La validez/NoData seguirá comprobándose por mapa.

## QGIS: comprobaciones guardadas

El proyecto local `reports/t04_revision.qgz` se guardó el 6 de octubre con parcelas, PREC_2025_07, Tmin_2025_07 y Tmax_2025_07.
- AGC_065: julio de 2025, una celda de lluvia; 120.25041198730469 mm, consistente con QGIS.
- AGC_014: cruza fila 30/columna 33 y fila 31/columna 33; 151.6535186767578 y 141.4019317626953 mm, consistentes con los valores consultados por Dani.
- Los pesos y el promedio ponderado de AGC_014 aún no se calcularon.
- El porcentaje válido del ráster completo no equivale a la cobertura de una parcela.

## Hallazgo sobre las copias usadas en QGIS

El ZIP maestro `data/raw/DataSet.zip` mantiene su huella original. Las copias interiores de lluvia y temperatura bajo `data/raw/DATASET_RETO_AGRO_2026/` contienen tres archivos adicionales:
- PREC_2025_07.tif.aux.xml.
- Tmin_2025_07.tif.aux.xml.
- Tmax_2025_07.tif.aux.xml.

Sus contenidos son estadísticas auxiliares. Los 50 miembros originales de lluvia y los 98 de temperatura siguen idénticos byte por byte a los del paquete maestro; no falta ninguno. Las huellas de los contenedores sí cambiaron por estos añadidos. La situación ya existía antes de esta fase y no cambió durante las comprobaciones.

Esto es compatible con el mecanismo PAM de GDAL, que conserva metadatos auxiliares en .aux.xml ([documentación oficial](https://gdal.org/en/stable/user/configoptions.html#persistent-auxiliary-metadata-pam-options)). No se identificó el proceso escritor mediante un registro de ejecución.

No se restauraron ni movieron las copias, ni se cambió el proyecto QGIS. Propuesta para acordar antes de la siguiente fase: conservar el paquete maestro como fuente autoritativa y preparar una copia de trabajo separada para QGIS. Si se restauran las copias interiores originales, primero conservar respaldo y cerrar/revincular QGIS; no borrar auxiliares improvisadamente del ZIP.

## Dependencias y siguiente fase

La versión local de T02 revisada fue `83aba4f2816b933954e51dbb21d3cf2534f661bb`; sus 197 IDs/geometrías se verificaron y sus resultados se reprodujeron. Se pidieron ajustes antes de aprobar y su catálogo aún no está integrado en esta rama. T04 puede preparar su extracción desde los originales verificados; el cierre requiere conciliarla con la entrega T02 aceptada.

T03 conserva su protocolo y particiones sin cambios. Su corte retrospectivo es provisional; inventariar un mes no lo convierte en una entrada admisible. No se tomaron decisiones de selección de ventanas o modelos en esta fase.

Fase 2:
1. Resolver la separación de copias de visualización y originales.
2. Calcular pesos físicos y promedio de AGC_014; comprobar AGC_065.
3. Verificar borde/vértice, múltiples celdas, NoData parcial/total, ausencia de cobertura y CRS.
4. Definir la evidencia mínima antes de implementar el extractor completo en fase 3.

Para cerrar T04 todavía faltan extracción por ID/periodo, área física, cobertura válida, centroide, trazabilidad y revisión independiente de Jass.

## Reproducir esta fase

Desde la raíz del repositorio, en el entorno de `requirements.txt`:

```sh
python -m unittest discover -s tests -v
python scripts/inventariar_clima.py --paquete data/raw/DataSet.zip --salida reports/t04_comprobacion/inventario_clima.json
```

La ruta del paquete puede cambiar por equipo. El script lee los ZIP anidados y verifica CRC sin extraerlos; no usa las copias internas modificadas por auxiliares como reemplazo del paquete maestro. `data/`, `reports/` y el proyecto QGIS permanecen locales e ignorados.

## Continuidad tras el acuerdo de Dani

Dani aprobó separar la copia QGIS y reutilizar pesos por cuadrícula. La fase 2 tiene comprobación técnica aprobada: 20 pruebas y seis ejemplos parcela/variable de julio. Proyecto de trabajo: reports/t04_revision_trabajo.qgz; abrirlo en QGIS para validar visualmente. Los originales y la sesión anterior se conservaron. Siguiente trabajo: fase 3, sin iniciar aún el extractor de 197 IDs.

## Continuidad tras la extracción completa

La sección anterior conserva el estado al terminar fase 2. Después Dani confirmó la copia QGIS, autorizó la implementación de fase 3 y finalmente centroide, piloto y ejecución completa. Se generaron 28,368 registros históricos y resúmenes de fase 4; el borrador local del PR y los pendientes están documentados en [extracción completa](t04_fase3_completa.md). No se cerró T04 ni se publicaron estos cambios.
