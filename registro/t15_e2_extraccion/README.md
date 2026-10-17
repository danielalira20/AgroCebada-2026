# E2 · entrega compacta local

197 filas y tres atributos estáticos INEGI, más calidad y sensibilidad descriptiva.
Resultado canónico: Linux/amd64 imagen común b2dea1bd…5aa. No se han ajustado modelos
con E2 ni demostrado reducción de MAE. Consulta docs/t15_e2_extraccion_inegi.md.

- atributos_parcela.csv: ID y tres columnas candidatas; sin etiquetas.
- calidad.csv: doce diagnósticos, no predictores automáticos.
- sensibilidad.csv: 788 desplazamientos de QA; no cambia geometría candidata.
- diccionario_columnas.csv: definiciones y ausencia, heredado del contrato inmutable.
- auditoria_mac.json / auditoria_linux.json: cálculos independientes del productor.
- comparacion_plataformas.json: límites previos sin relajar.
- negativos_*.json: evidencia alterada, y cálculos incorrectos con huella recalculada.
- resumen_QA.json: cifras descriptivas; ninguna métrica predictiva nueva.
- registro_operativo_v1.json: autorización de extracción, no de entrenamiento.
- entrega.json: huellas del paquete compacto y del código.

El manifest_extraccion.json original enumera también rasters y pesos grandes que
permanecen locales en reports/t15_e2_extraccion_20261016/linux_1_parent/linux_1/.
No son archivos faltantes de esta entrega compacta: para auditar desde originales
se ejecuta el extractor en una carpeta nueva, seguida del auditor sobre esa carpeta.
GDAL/PROJ/GEOS son bibliotecas compartidas; no se afirma independencia del motor GIS.
Las coberturas brutas pueden diferir de uno por ~1e-12 debido al cierre de áreas;
se conserva ese redondeo y se comprueba el límite previo 1e-8.
No se interpreta Z=0 del vector como altitud; no se modifica ningún original.
No sobrescribe T07, no incorpora pendientes de suelo/clima ni predicciones finales.
