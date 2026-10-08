# T04 · Versión, disponibilidad y uso temporal

Revisión documental: 7 de octubre de 2026. Este documento aporta evidencia y una propuesta de interpretación; no modifica T03, ventanas, particiones ni modelos. El corte observacional 2025-10-31 continúa siendo provisional. La extracción sigue siendo histórica/descriptiva.

## Qué se conoce del paquete FIRA

| Elemento | Lluvia | Temperatura |
|---|---|---|
| Fuente declarada en los mapas | CHIRPS | CHIRTS-ERA5 |
| Variables/unidades | PREC; mm/mes | Tmin y Tmax; grados Celsius |
| Agregación declarada | Suma de precipitación diaria | Promedio mensual |
| Número de versión del producto | No documentado | No documentado |
| Variante preliminar/final | No documentada | No documentada |
| Primera publicación de cada archivo/versión recibida | No documentada | No documentada |
| Identidad reproducible de la entrega | SHA-256 del maestro y de cada GeoTIFF en procedencia | Mismo control |

La huella permite identificar **nuestro insumo exacto**, pero no determina el número de versión científica ni su fecha histórica de publicación. El nombre del ZIP, la modificación del archivo y la fecha de descarga no prueban primera disponibilidad. No asignamos CHIRPS v2/v3 al paquete basándonos en su año o resolución.

## Qué indica la documentación oficial

Según la [FAQ oficial CHIRPS2](https://wiki.chc.ucsb.edu/CHIRPS2_FAQ), el producto final se publica durante la tercera semana del mes siguiente; el rápido tiene otro calendario y otras entradas. La [documentación oficial CHIRPS v3](https://chc.ucsb.edu/data/chirps3) también describe finales normalmente en la tercera semana siguiente y preliminares por péntada. Son plazos generales del proveedor, consultados ahora; **no están confirmados por FIRA para sus archivos**. No los convertimos en una fecha exacta ni suponemos que el paquete contiene preliminares.

La [página oficial CHIRTS-ERA5](https://www.chc.ucsb.edu/data/chirts-era5) indica cinco días de retraso para Tmin/Tmax **diarios**. Describe los productos mensuales mediante medias mensuales de ERA5 como entrada al proceso de corrección. Por ello ese plazo diario no certifica una fecha de publicación para nuestros TIFF mensuales. Tampoco reconstruimos los mensuales promediando mapas diarios ajenos a la entrega.

La [documentación oficial ERA5](https://confluence.ecmwf.int/pages/viewpage.action?pageId=384141176) indica que ERA5T publica medias mensuales aproximadamente cinco días después del mes y que, en CDS, el mes se reemplaza por ERA5 final alrededor de dos meses después. Esto demuestra la necesidad de distinguir publicaciones iniciales y posteriores en el insumo upstream; **no prueba que los archivos CHIRTS-ERA5 de FIRA se hayan revisado**, ni qué insumo concreto emplearon.

## La distinción necesaria para evaluar una predicción

Hay cuatro fechas/identidades diferentes:

1. Periodo observado: qué mes describe el dato.
2. Primera publicación: cuándo se pudo obtener el producto.
3. Versión o edición disponible en ese momento: preliminar/final y posibles revisiones.
4. Fecha objetivo de predicción y regla del concurso: qué información se permite usar.

Quitar noviembre/diciembre no demuestra que octubre estuviera disponible al cerrar octubre. Tampoco una tabla descargada hoy prueba los valores exactos que estaban publicados en 2025. Un modelo puede obtener una métrica atractiva usando información que entonces no existía; ese resultado no certificaría una predicción operacional reproducible.

La mejor evaluación debe corresponder al uso que pretende FIRA. El protocolo local T03 admite por ahora una reconstrucción retrospectiva con observaciones hasta octubre. Para una predicción en tiempo real hay que verificar publicación y edición del dato, además del mes. Estos dos objetivos pueden producir conjuntos de entradas distintos; no se decide entre ellos desde el extractor.

## Lo implementado sin decidir el modelo

La tabla compartida conserva los 28,368 registros y añade `posterior_al_corte`, comparando el **fin del mes observado** con el corte explícito del manifiesto. Con 2025-10-31, noviembre/diciembre suman 1,182 registros posteriores. Octubre aporta otros 591 registros: su indicador es False, pero su disponibilidad histórica sigue sin confirmarse. Los registros anteriores tampoco reciben una certificación automática de disponibilidad de su versión concreta.

El manifiesto dice `disponibilidad_historica_fira: no documentada`. No existe una columna `disponible_al_corte=True` inferida de plazos generales. La señal temporal no es una variable predictiva, no elimina filas y no reemplaza la selección acordada en T03/T07. Las medias, cuadrículas y tolerancias físicas permanecen iguales.

## Qué conviene confirmar antes de elegir entradas

Con Migue/Jass y, cuando proceda, FIRA: si el objetivo es retrospectivo o operacional; fecha/instante de predicción autorizado; número y variante de los productos recibidos; si octubre completo está permitido; y si se dispone de fechas de publicación o archivos históricos de esas ediciones. No se enviaron consultas en esta revisión.

Si la publicación exacta continúa desconocida, se puede documentar esa limitación y predefinir una sensibilidad con meses cuya disponibilidad se pueda sustentar. La propuesta deberá acordarse antes de comparar modelos, usando las mismas particiones y sin seleccionar cortes por los mejores resultados. No se implementó esa sensibilidad ni se eligieron ventanas en este cambio.

La mejora aquí es distinguir evidencia, inferencia e incertidumbre y conservar la edición de cada entrada. No hemos entrenado modelos ni demostrado una mejora de rendimiento predictivo. El punto 5 (agregaciones por ventana y su incorporación al documento) se discutirá después de revisar esta entrega.
