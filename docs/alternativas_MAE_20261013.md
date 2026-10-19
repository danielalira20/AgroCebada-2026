# Opciones fundamentadas para reducir MAE · 13 de octubre de 2026

Este documento es una investigación y una propuesta de prioridades, **sin nuevos experimentos de rendimiento ni datos externos incorporados**. Busca causas y pruebas útiles para las138parcelas2025, evitando prometer mejoras o seleccionar repetidamente sobre las mismas OOF.

## Lo que ya sabemos de Agrocebada

La referencia municipal ya mejoró mucho frente al promedio general: MAE A/todas≈0.7509→0.31925t/ha. En la población principal con soporte municipal el MAE≈0.32049. Ese error no es una «precisión de92%» ni un límite mínimo demostrado. Tampoco conocemos el error real de las59 hasta disponer de sus etiquetas.

El documento oficial de FIRA del9-oct, `Segunda_Sesion_Preguntas_Reto.docx`, confirma: temporal, rendimiento de grano, fuente mayoritariamente comercializadora y minoritariamente productor, muestreo aleatorio estratificado, fechas de siembra/rotación/siniestros no disponibles por parcela. P14 menciona Josefa predominante y Voyager minoritaria, sin asignación individual. Las mayúsculas de `Cultivo` no identifican variedades. Estas diferencias desconocidas pueden afectar la relación entre verdor y grano; no se inventan columnas de manejo.

La transcripción de Dani permite información de consulta pública; se conserva como evidencia de la sesión, distinguida del documento oficial. Para cualquier fuente nueva se registrarán licencia, edición, soporte espacial, fecha observada y disponibilidad histórica. Agrocostos ayuda a escenarios económicos, pero no sustituye la dosis o coste real de una parcela; precios no explican directamente su rendimiento físico.

La comparación mediana/media y la contracción municipal **ya se hicieron en T08**: no se anuncian como ideas nuevas. Las dos ventanas climáticas conjuntas también se exploraron en T14. Los modelos nuevos son experimentos distintos de la comparación común de bloques.

## Prioridad propuesta

| Orden | Prueba o trabajo | Qué podría resolver | Condición para avanzar |
|---|---|---|---|
| 1 | T15 común C/G/P y contraste S | Complementariedad entre bloques; diferencia de método en históricos | Acuerdo Daf/Migue, registro previo, mismas particiones/reglas. |
| 2 | Auditoría de los mayores errores y curvas/calidad | Contornos, capturas, fechas, escalones, soporte o unión incorrecta que expliquen fallos concretos | Corregir sólo error de fuente verificable; conservar casos difíciles válidos. |
| 3 | T12 no lineal pequeño; alternativa de pérdida absoluta | Interacciones y relación no lineal; Ridge ajusta cuadrados aunque sus parámetros se elijan por MAE | Familia/presupuesto separados, mismos datos, internas espaciales, revisión de Diego/Migue. |
| 4 | Rasgos temporales de las curvas existentes de Daf | Dos parcelas con el mismo pico pueden crecer en momentos distintos | Primero auditar cobertura y definiciones sin rendimiento; no crear fases agronómicas ficticias. |
| 5 | Dos propiedades de suelo de fuente abierta | Retención de agua y variación que municipio/elevación no representan | Disponibilidad y variación dentro del municipio comprobadas; extracción física y registro nuevo. |
| 6 | Clima diario y eventos | Una media mensual puede ocultar periodos secos, frío o calor | Verificar edición/unidad/latencia, soporte espacial y ventanas fijadas sin mirar errores. |
| 7 | Nuevas bandas/radar | Información complementaria sobre agua, estructura o clorofila | Más coste de extracción y QA; sólo ante una carencia concreta y tiempo disponible. |

No ejecutaremos los siete caminos como una búsqueda abierta. Tras T15 y la auditoría de casos, elegir una sola extensión justificada, registrar lo que probará y publicar también un resultado negativo. Reusar las mismas particiones para explorar muchas alternativas hace menos independiente la evidencia del ganador; conservar la cronología y necesitar campañas futuras para validar su transferencia. [Guía oficial de validación anidada](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).

## Opciones de modelos con los datos actuales

Ridge minimiza cuadrados; elegir λ por MAE no cambia su función de ajuste. Una regresión cuantílica con q=0.5 estima la mediana condicional y optimiza una pérdida proporcional al error absoluto. Es una hipótesis razonable para reducir MAE sin eliminar valores extremos. La penalización de `QuantileRegressor` es L1 y **no debe trasladarse automáticamente α=nλ de Ridge**; registrar objetivo, escala y rejilla propios. La mediana municipal simple ya no fue suficiente en T08: esta prueba preguntaría por correcciones parcelarias, no repetiría aquella comparación. [QuantileRegressor oficial](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html).

T12 puede evaluar árboles poco profundos con hojas grandes y pocas opciones, para interacciones vegetación×agua/suelo. `GradientBoostingRegressor` admite `absolute_error`; su parada anticipada interna predeterminada separa aleatoriamente y no sustituye nuestras divisiones espaciales. Mantener ajuste dentro de las internas fijadas, semillas y presupuesto pequeños. No es necesario una red profunda, GPU ni modelos separados por variedad inexistente. La ausencia de un PR T12 al consultar GitHub no prueba que Diego no tenga trabajo local: coordinar antes de duplicarlo. [Documentación oficial](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingRegressor.html).

## Curvas de Daf: oportunidad y límite

T06 ya calcula inicio, pico y final observables; varios resúmenes entran en los bloques compactos. El final sólo se observa en77/197Planet y56/197S2; no recomendar «duración hasta cosecha» para todos. Se pueden estudiar fecha del pico, amplitud corregida por base y distribución del área bajo la curva antes/después del pico, usando sólo capturas hasta corte. No seleccionar fecha/umbral que reduzca el error en los peores casos; fijar definiciones por cobertura y significado antes del nuevo experimento.

Si se añaden rasgos incompletos, el contrato/modelo actuales sólo admiten faltantes de pendiente: se necesita un contrato nuevo y mediana/indicadores aprendidos en cada entrenamiento. Una fecha de pico NDVI no es automáticamente espigamiento; no asignar BBCH o fecha de siembra real sin observación. Las campañas2022–24 no generan nuevos ejemplos etiquetados de rendimiento ni identifican cebada anterior: FIRA desconoce rotaciones.

## Datos abiertos: utilidad, acceso y límites

**Suelo.** SoilGrids proporciona predicciones a250m, seis intervalos de profundidad y cuantiles de incertidumbre. Es una descripción modelada, no análisis de laboratorio por parcela; remuestrear a10m no crea información de10m. Un primer bloque pequeño podría usar arcilla y carbono orgánico en0–30cm, con promedio por espesor5/10/15cm, evitando sumar arena/limo/arcilla colineales. Un píxel250m cubre6.25ha: auditar parcelas pequeñas y soporte compartido. [Definición oficial](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs.html).

Las capas enteras requieren sus factores de conversión (arcilla g/kg→porcentaje, SOC dg/kg→g/kg), profundidad y estadístico explícitos. Conservar incertidumbre como diagnóstico, no convertirla en intervalo del rendimiento. [Unidades y capas ISRIC](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html).

La documentación de ISRIC informa que la API REST está temporalmente suspendida y no ofrece fecha de restablecimiento. Propone WCS/WebDAV como alternativas; son servicios documentados, cuyo funcionamiento concreto debe probarse antes de automatizar. Cada mapa mundial ronda5GB: solicitar recorte regional y cachear versión, sin descargar el mundo en la Mac8GB. Licencia CC BY4.0. [Acceso oficial, consultado13-oct](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html).

INEGI ofrece información edafológica; queda como alternativa de inventario a verificar en resolución, edición y cobertura. Sus páginas dinámicas no devolvieron aquí contenido utilizable: no se acredita una extracción regional disponible ni perfiles medidos en nuestras parcelas. [Tema oficial](https://www.inegi.org.mx/temas/edafologia/).

**Lluvia diaria.** CHIRPS2 documenta datos diarios y resolución0.05°, en dominio público. Podría medir una racha seca o distribución de lluvia que una suma mensual pierde, pero el dato regional no es un pluviómetro dentro de cada parcela. No se presupone que FIRA usó exactamente esta edición, ni se mezclan v2/v3. Conciliar primero sumas mensuales y diagnosticar diferencias. Registrar reglas de día seco y ventanas antes de evaluar, con sensibilidad limitada y justificada. [CHIRPS oficial](https://www.chc.ucsb.edu/data/chirps), [frecuencias/unidades/latencia](https://wiki.chc.ucsb.edu/CHIRPS_FAQ).

**Temperatura y agua del suelo.** ERA5-Land ofrece información horaria desde1950, resolución aproximada9km y disponibilidad hasta unos5días antes del presente. Podría describir extremos térmicos o agua del suelo modelada; es más grueso espacialmente que nuestros mapas5km. Fijar conversión UTC→día local, Kelvin→°C, operación diaria y periodo. Temperatura a2m no mide temperatura del dosel ni demuestra una helada en la parcela. No usar una media mensual como recuento de heladas. El histórico disponible hoy no prueba su versión disponible en2025. [ECMWF oficial](https://www.ecmwf.int/en/era5-land).

CLICOM/CICESE podría aportar estaciones para comprobar eventos; sus páginas no respondieron en esta consulta. No se confirmó cobertura diaria2025 por estación, por lo que no se presenta como fuente lista para integrar. Primero catálogo, fechas, altitud/distancia y faltantes; no imputar eventos reales desde estaciones sin esa comprobación.

## Qué aprendimos de experimentos publicados

**Meroni et al.,2021.** En cereales de Argelia usa provincia×año y validación anidada dejando años fuera. Respalda seleccionar atributos/parámetros dentro de entrenamiento y mantener referencias sencillas; muchos modelos resultan peores que ellas. El error nacional≈0.16–0.20t/ha no es comparable a MAE parcelario2025. No copiamos su búsqueda extensa con138etiquetas. [Artículo completo](https://arxiv.org/pdf/2104.13246).

**Pathak et al.,2023, IGARSS.** Estudia977campos de trigo/colza/soja de tres países, agrupando validación por campo. La mejor combinación de satélite/suelo/clima/DEM cambia con cultivo y región. Apoya comprobar complementariedad, sin garantizarla aquí. Tiene mapas de cosechadora y fechas reales de ciclo, información distinta de la nuestra; interpolar capas gruesas no aumenta su información independiente. [Artículo completo y DOI editorial](https://arxiv.org/html/2308.08948v1), [10.1109/IGARSS52108.2023.10282318](https://doi.org/10.1109/IGARSS52108.2023.10282318).

**Iranzo et al.,2022.** Serie de cinco campañas de una explotación española127ha, calendario apoyado en observaciones de campo, radarCR/ópticoIRECI y clima. Genera136modelos tras filtrar variables por Pearson; describe LOOCV, sin documentar en ese pasaje selección anidada del filtro/búsqueda. Su cifra57.38kg/ha no establece un MAE alcanzable aquí. La idea útil es respetar el calendario y señales complementarias, no copiar ventanas octubre–abril a cebada sembrada en mayo. PDF editorial leído íntegramente tras fallo del acceso web. [Fuente primaria](https://polipapers.upv.es/index.php/raet/article/download/15099/14861/74533), DOI10.4995/raet.2022.15099.

**Remote Sensing2025,17,957.** Distingue clasificación de cultivo con validación por campo y una parte de rendimiento basada en correlaciones en sitios de muestreo de un campo. Las asociaciones por fases apoyan investigar rasgos, pero no prueban generalización parcelaria. El producto de superresolución1m no son mediciones nuevas independientes de1m; no se incorpora por una correlación alta. [Texto completo en archivo de autores](https://orgprints.org/id/eprint/56321/1/remotesensing-17-00957-1.pdf).

También se localizó *High-Resolution Wheat and Barley Yield Forecasting...*, Agriculture2026,16,516, pero no se recuperó su texto completo en esta sesión: no se usó para recomendar un modelo o prometer un error. Los artículos localizados y los leídos se distinguen en la evidencia.

## Recomendación para el equipo

Cerrar el acuerdo T15 y hacer esa comparación limitada; revisar después los mayores errores sin cambiar etiquetas válidas. Preparar con Diego un contraste T12 y, si se justifica, una alternativa de pérdida absoluta. En datos externos priorizar un bloque pequeño de suelo o un bloque de eventos diarios, elegido por la carencia encontrada. Una integración nueva necesitará T07/procedencia/contrato, no sólo añadir columnas al CSV.

Para uso futuro, conseguir rendimientos de otra campaña y metadatos individuales de siembra/variedad es más valioso que tratar mapas adicionales como nuevas etiquetas. Datos sintéticos sirven para comprobar código, no para demostrar que el rendimiento aprendido mejoró. No ajustar una mejora a las59 sin etiquetas ni prometer precisión perfecta con datos incompletos.

Se usaron las skills scikit-learn y pensamiento crítico científico. Referencia de software/procedimientos: Kassis,T., Agarwal,V., He,Y., Patel,D., Brueckner,A.M.(2026), [Scientific Agent Skills](https://doi.org/10.48550/arXiv.2609.00065), registro vigente consultado13-oct2026. Las hipótesis y prioridades anteriores son inferencias para Agrocebada, no resultados experimentales nuevos.
