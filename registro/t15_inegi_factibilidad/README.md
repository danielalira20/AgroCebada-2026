# INEGI · factibilidad de relieve local

[Informe y límites de datum/disponibilidad histórica](../../docs/t15_inegi_factibilidad.md).

`procedencia.json` identifica el TIFF original CEM3.0 descargado de la fuente oficial. `verificacion_recorte.json` y `soporte_raster_por_parcela.csv` acreditan cobertura, geometrías y celdas válidas. `comparacion_entornos.json` distingue la reproducción de QA entre Mac y Linux. Las cinco huellas vectoriales impiden reutilizar esta QA si cambian IDs, geometría o referencia.

Estos conteos **no son atributos de un modelo**. En particular, `all_touched` sirve sólo como diagnóstico de soporte; no sustituye ponderación por área. No se ha calculado TPI, orientación ni su aporte al MAE.

El TIFF de unos 29 MB se conserva localmente, ignorado por Git, en `data/raw/externos/inegi/cem3_r15_region.tif`. Se necesita el mismo archivo para repetir la QA; no llega con este paquete. La URL detallada de la solicitud regional y las cabeceras de sesión permanecen privadas. El informe enlaza el portal y servicio oficiales para localizar la fuente; una descarga distinta exige registrar otra huella.

Crédito: **Fuente: INEGI, Continuo de Elevaciones Mexicano 3.0, consulta 16-oct-2026.** Recorte y QA elaborados por el equipo; no implican respaldo oficial del INEGI. No se retiraron metadatos del original.
