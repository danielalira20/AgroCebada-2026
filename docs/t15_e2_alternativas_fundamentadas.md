# Alternativas después de E1: evidencia y prioridades

16 de octubre de 2026. Investigación dirigida por Dani para preparar decisiones; **no añade datos al entrenamiento, no ejecuta modelos ni promete una reducción del MAE**. Se distingue una idea aplicada en otro estudio de una solución comprobada para Agrocebada. Las propuestas siguientes requieren contrato propio; no se incorporan al menú E2.

## Punto de partida y preguntas

Nuestra referencia principal tiene MAE 0.320490 t/ha en 135 parcelas de 2025. E1/Q no cumple promoción. El diagnóstico no acreditó corrupción de etiquetas que podamos corregir legítimamente. Quedan causas plausibles —información de cada parcela, representación y función de ajuste—, sin evidencia para declarar un techo irreducible del error.

La pregunta útil es qué hipótesis distinta podemos probar con información verificable y un presupuesto limitado. Aumentar el número de modelos, usar millones de píxeles o encontrar un artículo con R² alto no aumenta nuestras 138 etiquetas independientes ni sustituye una validación pertinente.

## Qué se leyó y qué permite concluir

| Fuente primaria | Unidad y diseño relevante | Qué rescatamos y qué limita su transferencia |
|---|---|---|
| Heil, Heinemann y Schmidhalter (2018), [barley, suelo y topografía](https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2018.00146/full) | Ensayo de fertilización de larga duración; regresiones/ANOVA/ANCOVA con conductividad aparente, relieve y manejo conocido. | Suelo y relieve pueden complementar el manejo en cebada. Aquí no tenemos aquellas mediciones de conductividad ni tratamientos individuales; SoilGrids sería una fuente modelada distinta. El ajuste del ensayo no acredita nuestro MAE fuera de muestra. |
| Ksantini et al. (2025), [resolución espacial y rendimiento de cebada](https://oa.upm.es/96158/) | PDF completo recuperado; métodos y validación inspeccionados: una parcela experimental de 3.5 ha, datos de cosechadora y conductividad, resolución 6/12/24 m; separación 70/30 estratificada por cuartiles de rendimiento. | Motiva evaluar información local y escala, pero su validación dentro de un campo no es una validación entre nuestras parcelas o campañas. Moran/SSIM describen patrones espaciales; no convierten automáticamente esa separación en particiones espaciales independientes. |
| Amin et al. (2024), [series Sentinel-2 y pronóstico dentro de campo](https://doi.org/10.1016/j.jag.2023.103636) | Resumen del artículo publicado en [ETH](https://www.research-collection.ethz.ch/entities/publication/ba04c2b3-548d-4762-bfef-c44d4f5cac72): tres años, kNDVI, reconstrucción GPR y alineación por grados-día; la transferencia a años no vistos empeora. | Motiva estudiar la curva completa y el calendario. El resumen no basta para acreditar todos los detalles de selección o partición; no se copia su pipeline ni su error como objetivo. Requeriríamos temperatura diaria y una definición agronómica justificable. |
| Pathak et al. (2023), [fusión satélite–suelo–clima–DEM](https://arxiv.org/html/2308.08948v1) | Métodos y resultados consultados: 977 campos de varios cultivos/países, mapas de rendimiento de cosechadora y validación agrupada por campo; la combinación más útil cambia por contexto. | Respalda probar complementariedad, no añadir todas las fuentes a la vez. Conocen siembra/cosecha y disponen de mapas de rendimiento; sus muestras por píxel y su arquitectura no son equivalentes a 138 rendimientos parcelarios. Remuestrear SoilGrids no crea información fina. |
| Meroni et al. (2021), [predicción con pocos datos en cereales](https://arxiv.org/abs/2104.13246) | Métodos de validación consultados: provincia×año, incluyendo cebada, selección y evaluación anidadas dejando años fuera y comparación con referencias sencillas. | Apoya limitar complejidad y evaluar una temporada realmente no vista para uso futuro. Su error a escala provincial/nacional no es comparable al error parcelario de Agrocebada. No copiamos su rejilla extensa de búsquedas con esta muestra. |

La descripción de la procedencia del DEM en §2.2.2 del estudio de Ksantini requiere cautela: menciona terrain correction de una adquisición Sentinel-1. Ese pasaje no justifica que una imagen SAR aislada proporcione por sí sola un nuevo DEM de terreno. Nuestra decisión usa un **DEM oficial independiente**, no ese atajo. El filtrado de atributos de otro artículo tampoco autoriza filtrar con todas nuestras etiquetas antes de validar.

Se localizaron además estudios recientes de trigo/cebada y combinaciones con modelos de cultivo cuyo texto completo no se recuperó en esta consulta. Se mantienen como lectura pendiente, sin atribuirles una demostración ni recomendar una arquitectura a partir del título o de su resumen.

## Qué ya hizo el equipo: evitar repeticiones disfrazadas

Se consultaron las versiones actuales de los PR el 16-oct, sin modificarlos:

- **T13, PR20 `a176d2e`**: ambos scripts inspeccionados coinciden por huella con los leídos en D.1; cambió su documentación. Hay familias de verdor, agua, residuos, labranza y senescencia, con resúmenes alrededor del máximo o máximos de curva. «Probar EVI/SAVI/FAPAR» no es una idea nueva. Su documento identifica pendientes de método/selección espacial; esta revisión no los corrige ni declara una reproducción integral de T13.
- **T12, PR24 `1331e4f`**: ya incluye heterogeneidad municipal y boosting con pérdida absoluta. Su revisión previa encontró concordancia de controles con T15. Añadir simplemente otro árbol o decir «usar MAE en boosting» duplicaría una línea ya ensayada; cambiar entradas o familia sería otra comparación.
- **Exploraciones de Migue, PR23 `fd4120a`**: hay PCA, red pequeña, vecinos, historial NDVI, alineación SOS y LAD con clima. Se conserva su condición exploratoria; las cifras no se elevan a evaluación común verificada. **LAD climática no equivale a una cuantílica compacta con entradas satelitales ni a un diseño conjunto de mediana condicional territorial.**
- **E1/Q propios, `ce287cd`**: la representación posterior al pico se probó con ausencia controlada y ancla sensible. No se reabre la ventana o el filtro de nubes para perseguir una cifra favorable.

Las conclusiones anteriores se limitan a las versiones y archivos inspeccionados, no a trabajos privados de compañeros que no hayamos recibido.

## Alternativas concretas, por prioridad y condición

### 1. Relieve relativo de INEGI, ya preparado para implementar

Carencia: posición respecto al entorno y exposición local, distinta de repetir altura municipal. El [contrato E2](t15_e2_contrato_inegi.md) fija TPI150 y dos componentes de orientación ponderadas por inclinación. El cambio de representación se justifica geométricamente y tiene antecedentes ambientales [Ramji et al., 2024](https://doi.org/10.5061/dryad.2rbnzs7x4); no demuestra aporte al rendimiento. El control E2Q separará disponibilidad de NDWI de su valor en la combinación.

Ventaja práctica: fuente ya descargada, 197 parcelas cubiertas y tres columnas. Condición: pesos, bordes, metadatos y QA independientes antes de entrenar. No añadimos TWI: necesita otra definición y QA de drenaje. Prioridad inmediata por preparación, no porque sepamos que ganará.

### 2. Una alternativa compacta cuyo ajuste responda al error absoluto

Ridge ajusta cuadrados aunque λ se elija por MAE. [QuantileRegressor, q=0.5](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html), ajusta una mediana condicional con penalización L1. Es una pregunta distinta del Ridge satelital y de LAD con clima de Migue, con poco coste de datos.

Propuesta posterior: una familia, entradas compactas fijadas, pocas opciones y la misma evaluación anidada. Diseñar primero los interceptos/componentes territoriales y sus respaldos dentro del entrenamiento. **No sustituir media por mediana en v3 ni copiar α=nλ de Ridge**: cambian objetivo y penalización. Tampoco asumir que la optimalidad teórica de la mediana garantiza que una mediana estimada con pocos ejemplos gane. Mediana municipal sola ya fue revisada y no cumple la regla vigente.

La priorizaría después de E2 si el plazo permite una comprobación seria. No exige esperar una nueva fuente, pero sí un diseño y auditor propio; no se implementa en este contrato.

### 3. Armonizar una familia existente de T13, sin confundirlo con índices nuevos

El documento actual de T13 reconoce que su Ridge anterior tenía intercepto y que las internas de B no estaban separadas por celda. Su propuesta de repetición con el método común sigue siendo una pregunta distinta de afirmar que todos sus índices se evaluaron bajo v3. Podría hacerse una comparación limitada de una familia ya definida —por ejemplo, verdor ampliado con EVI/SAVI/FAPAR/MRA— frente a un control simétrico, con entradas/versiones fijadas y coste acotado.

La familia no se escogería por ser la de menor MAE externo histórico. Hay que declarar esa exposición, fijar una justificación de representación y rehacer selección/ajuste con v3; no basta corregir las predicciones anteriores. Es una alternativa con datos existentes, no una nueva recolección ni evidencia de mejora. La responsabilidad original de T13 sigue con su autor; esta revisión no cambia su código ni convierte la idea en ejecución autorizada. No ejecutaría simultáneamente toda la extensión, varias pérdidas y nuevas bandas.

### 4. Suelo abierto: piloto pequeño de arcilla y carbono orgánico

Hipótesis: diferencias en almacenamiento de agua y propiedades del suelo que relieve y vegetación no describen completamente. Proponer sólo arcilla y carbono orgánico 0–30 cm, con capas/unidades/edición y promedio por espesor explícitos. No inferir dosis de fertilizante ni suelos medidos por parcela.

[SoilGrids](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs.html) proporciona predicciones de 250 m; las parcelas pequeñas pueden compartir soporte. La [documentación de acceso consultada hoy](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html) mantiene la pausa de REST y recomienda WCS/WebDAV. Eso no acredita que una consulta concreta funcione ni su cobertura: faltaría un recorte acotado, disponibilidad histórica, incertidumbre y variación local. Se pospone si esos controles no caben; no descargamos mapas globales.

### 5. Señal temporal más estable o bandas distintas, sólo con una carencia concreta

La sensibilidad del ancla permite plantear posteriormente una representación de curva que no dependa de una captura exacta: resúmenes de intervalos de calendario fijados o una base temporal pequeña. Antes hay que contrastarla con las integrales de T06, los máximos de T13 y SOS de Migue, para que aporte una pregunta distinta. No se optimizan decenas de fechas, umbrales y suavizados contra los errores externos.

Un índice de borde rojo como NDRE/IRECI necesitaría bandas y un pipeline óptico verificable; no basta renombrar un índice del CSV. Asimismo, una transformación no lineal del NDVI medio parcelario **no equivale** al promedio del índice transformado píxel a píxel. La literatura de kNDVI es una pista de representación, no autorización para fabricar ese producto a partir de una media no equivalente.

Una GPR pequeña podría ser computacionalmente viable con 138 etiquetas, pero no es un sustituto directo del Ridge residual: requiere resolver media territorial, centrado, kernel y calibración dentro de entrenamiento. Sus incertidumbres tampoco serían intervalos de rendimiento validados automáticamente. Frente a muchas familias nuevas, preferimos cerrar primero la prueba de pérdida absoluta.

## Lo que no priorizaría en esta recta final

Redes profundas, muchos modelos por municipio, una batería de radios/índices, superresolución para aumentar artificialmente la muestra, entrenar con etiquetas inventadas o traer etiquetas extranjeras sin controlar unidades/variedad/manejo. Modelos de cultivo pueden ser útiles, pero requieren entradas y calibración que no hemos acreditado. Datos económicos de Agrocostos sirven para escenarios de la app; no son fertilización real ni rendimiento físico por parcela.

No se reduce el umbral de promoción al ver una mejora pequeña, ni se elige el mejor promedio externo de un conjunto de pruebas tardías. Los intervalos adicionales de la familia E2 son una protección local conservadora; no convierten esta búsqueda acumulada en una confirmación independiente. El siguiente año etiquetado sigue siendo necesario para comprobar uso futuro.

## Orden que recomiendo

**Implementar y auditar E2 → registrar códigos/tablas → evaluar E2/E12/E2Q con todos sus resultados → decidir.** Después, como máximo una alternativa compacta de pérdida absoluta si puede completarse su validación. La armonización acotada de T13 queda como otra opción con datos existentes; no se ejecutan ambas automáticamente. Suelo o bandas/curvas nuevas requieren primero un piloto de calidad y una razón concreta; no son tareas obligatorias simultáneas.

En paralelo al cierre conviene reservar tiempo para aplicabilidad final a las 59, T16, ajuste con las 138, CSV, app e informe. Si ninguna extensión pasa, entregar una referencia reproducible con límites explícitos sigue siendo la decisión respaldada por nuestros datos. No hay evidencia para garantizar que una alternativa reduzca MAE antes de probarla.

## Procedencia de esta revisión

Registro de fuentes y alcance: [fuentes de alternativas](../registro/t15_e2/fuentes_alternativas.json). PDF completo local de Ksantini recuperado, métodos/tabla y validación de las páginas 3–5 revisados; páginas 4–5 inspeccionadas visualmente. Secciones relevantes de Heil, Pathak y Meroni consultadas en texto web/PDF; Amin se limita al resumen publicado en el repositorio de autores. No se redistribuyen PDFs de terceros ni se publican sus archivos como propios. Revisión dirigida, no búsqueda sistemática exhaustiva ni metaanálisis.

Apoyo de pensamiento crítico científico, scikit-learn, GeoPandas y PDF. Kassis et al. (2026), [Scientific Agent Skills](https://doi.org/10.48550/arXiv.2609.00065), registro vigente verificado 16-oct-2026. Su uso no sustituye las pruebas ni una revisión humana externa.
