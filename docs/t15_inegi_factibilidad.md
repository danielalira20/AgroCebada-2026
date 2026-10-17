# T15 · INEGI: acceso y cobertura del relieve local

16 de octubre de 2026. Responsable: Dani. Estado: **factibilidad comprobada; E2 aún no extraído ni evaluado**. Fuente: INEGI, Continuo de Elevaciones Mexicano 3.0 (CEM 3.0), servicio de 15 m. La QA siguiente es elaboración del equipo, no una validación ni respaldo del INEGI.

## Problema que resuelve

El relieve anterior no comprueba posición topográfica local ni orientación con mayor detalle. Antes de añadir columnas necesitamos una fuente oficial accesible, soporte real alrededor de las 197 parcelas y metadatos suficientes para no confundir resolución, precisión, datum y disponibilidad histórica.

## Solución y acceso

Se consultó el [portal oficial de elevaciones](https://www.inegi.org.mx/app/geo2/elevacionesmex/) y sus metadatos públicos. Se mantuvo la autorización previa de Dani: sólo región rectangular aproximada, sin enviar IDs, rendimientos, polígonos individuales ni archivos originales. Toda la conciliación de geometrías se hizo localmente.

La API de descargas por estado respondió HTTP 200 con cuerpo vacío para las tres consultas; eso no es un ZIP válido ni demuestra que los archivos estatales no existan. Se usó el WCS oficial anunciado por el portal: `https://gaia.inegi.org.mx/geoserver/wcs`, capa `cem30_workespace:cem3_r15`. Se descargó sólo la región necesaria, alineada a la rejilla nativa descrita por el servicio y con vecino más próximo. Límite de descarga: 100 MiB. No se descargó el país ni se abrió otra familia de productos por una cifra de MAE.

El original permanece inmutable y fuera de Git en `data/raw/externos/inegi/cem3_r15_region.tif`. Solicitud detallada y respuesta técnica quedan en los informes locales; el paquete compartible no incluye cabeceras de sesión, cookies ni rutas personales. La huella fija identifica exactamente el archivo probado; una descarga futura distinta exige registrar y comprobar la nueva fuente.

## Resultado de cobertura

| Comprobación | Resultado |
|---|---|
| Archivo |29,003,701 bytes, unos 29 MB decimales |
| Dimensiones |3,601 × 3,601; una banda int16 |
| Resolución angular servida |0.000138888889 grados, producto nominal de 15 m |
| CRS declarado por el servicio/archivo |EPSG:4326 |
| NoData |−32768 |
| Celdas regionales válidas |12,967,201 / 12,967,201 |
| Geometrías válidas y catálogo conciliado |197 / 197, sin reparaciones |
| Parcelas completas dentro del recorte |197 / 197 |
| Parcelas con margen de 175 m alrededor |197 / 197 |
| Distancia mínima al borde del recorte |1,731.906 m, calculada en EPSG:32614 |
| Celdas tocadas por parcela, sólo QA |mínimo 27, mediana 288, máximo 3,009 |
| Parcelas con todos esos valores enteros idénticos |0 |

Huella SHA256 del TIFF: `5f315dd32f7984c0c8f0bdd12f8bc22c014fd097473e2497e30d3be6f648be95`. La rejilla solicitada coincide con la nativa dentro de 1e−6 píxel. Mac y Docker Linux/amd64 producen los mismos conteos y CSV de soporte; el informe geométrico también coincide exactamente en esta comprobación. Se fijan las huellas de SHP, SHX, DBF, PRJ y CPG para detectar cambios de geometría, orden, IDs y referencia.

La cuenta `all_touched` sólo acredita soporte de celdas para QA. **No es una media ponderada por área ni un predictor E2.** El rango entero de alturas tampoco acredita relieve medido con exactitud a escala de parcela. No se usan rendimientos para decidir cobertura o transformar el raster.

## Metadatos y límites que importan

La ficha histórica oficial describe CEM 3.0 publicado en 2013, resolución de 15 m, Z enteras en metros y EMC nominal 4.9 m; su referencia horizontal original es ITRF92 época 1988.0 / GRS80. Véase [Informe INEGI 2013, cuadro 6.9, página impresa 298](https://www.inegi.org.mx/contenidos/programas/entic/2013/doc/inf2013.pdf#page=298).

La respuesta actual del servicio declara WGS84/EPSG:4326. No documenta en el TIFF la transformación desde aquella referencia histórica ni el datum vertical específico; la unidad Z tampoco aparece en el campo de unidad de banda. Se atribuyen los metros a la ficha del producto, no a un metadato que el TIFF no tiene. **No se sobrescribe el CRS actual para forzarlo al histórico.** La resolución nominal de 15 m no significa precisión vertical de 15 m ni certeza sobre diferencias de pocos metros.

La existencia del producto en 2013 no acredita que estos bytes servidos en 2026 fueran exactamente los disponibles al corte de octubre de 2025. El futuro piloto se declarará retrospectivo con esa limitación; no se presentará como prueba histórica operativa. Si se requiere esa garantía, habrá que conseguir una distribución original fechada con metadatos completos; no inventar una fecha de disponibilidad.

El margen de 175 m acredita espacio suficiente para el piloto propuesto de vecindario de 150 m y un halo inicial de derivadas. Su suficiencia definitiva depende del núcleo exacto de cálculo y del remuestreo que se registren. No se afirma que pendientes, orientaciones o TPI ya estén calculados o verificados.

## Reproducción local sin consultar servicios

`scripts/t15_inegi_verificar_recorte.py` lee únicamente el TIFF fijado, originales vectoriales y los IDs de T07. Rechaza otro archivo/huella o salida existente, apaga la red de PROJ, verifica CRS y geometrías y produce dos archivos en una salida nueva. Con dependencias del proyecto, desde la raíz:

```bash
python -O scripts/t15_inegi_verificar_recorte.py --raster data/raw/externos/inegi/cem3_r15_region.tif --salida reports/t15_inegi_revision_nueva
```

La descarga original no se repite al verificar. El uso de Docker común se hace con el repo de sólo lectura y un directorio de evidencia escribible. El TIFF debe estar disponible localmente para reproducir; no llega mediante Git.

## Siguiente piloto propuesto

1. Fijar un contrato E2 sin mirar etiquetas: rejilla métrica y resolución, remuestreo único documentado, derivadas, halo y ponderación física por intersección. Conservar original angular. No calcular derivadas tratando grados como metros.
2. Priorizar una representación compacta: posición relativa en un entorno de 150 m y orientación como dos componentes circulares; definir la ausencia de dirección en planos. Son propuestas, no tres columnas ya aceptadas ni una búsqueda de radios por menor MAE.
3. Verificar resultados de forma independiente con superficies de pendiente conocida, planos, bordes y NoData; comprobar soporte real por parcela y ambos entornos. Las pruebas artificiales de geometría comprueban fórmulas; no se convierten en nuevas observaciones de rendimiento.
4. Registrar antes de nuevas OOF los comparadores S+E2 y, si pasa calidad/coste, S+E1+E2, con S, E1 y referencia como controles. Declarar exposición previa a E1. El valor individual de E1 no decide por sí solo si merece probarse la combinación; no activar una búsqueda ilimitada de variables.
5. Sólo entonces evaluar con v3, las particiones originales y las mismas reglas. Aplicabilidad de los predictores retenidos a las 59 y T16 siguen después de esa decisión.

Los [términos de libre uso de INEGI](https://www.inegi.org.mx/inegi/terminos.html) permiten usar y transformar con crédito, conservar metadatos y distinguir las transformaciones del equipo de la información original. Que exista cobertura y variación no demuestra información predictiva adicional ni garantiza bajar MAE.

Apoyo: skill GeoPandas para conciliación espacial y pensamiento crítico científico para límites de inferencia; [referencia del apoyo procedimental](t15_e1_evaluacion.md#fuentes-y-apoyo).
