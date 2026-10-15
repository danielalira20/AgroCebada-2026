# C descriptiva · aplicabilidad preliminar a las 59

14 de octubre de 2026. Diseño local antes de calcular. Responsable: Dani; revisión: Daf/Migue. La fase C conserva la fase 5 del diagnóstico original. No es T18 ni una nueva evaluación de modelos.

## Problema que resuelve

Compartir municipio o clima no garantiza condiciones equivalentes. El diagnóstico climático T09 no cubre por sí solo los atributos satelitales, terreno, calidad y disponibilidad de vecinas que necesitan T15 y la app.

## Solución propuesta y límites

Se conserva la tabla T07 de 197 IDs, 138 etiquetas y 59 ausentes, y se producen perfiles de soporte por ID, bloque y ventana. Las 15 representaciones son las ocho candidatas de T15 sin duplicar lambda ni G estático. La referencia a un candidato identifica sus columnas; no acredita una evaluación nueva de ese candidato.

Para las 59 se utilizan sólo las entradas de las 138 como población de referencia, sin sus rendimientos para construir el soporte. Para contextualizar el diagnóstico se reconstruyen los 50 entrenamientos externos A/B de T03 y se relaciona soporte con errores históricos T08 ya calculados. Son 1,380 contextos parcela/evaluación, no nuevas parcelas. No se vuelve a entrenar ningún estimador.

## Reglas fijadas antes de mirar los resultados C

- Huellas de 17 fuentes, ZIP original identificado por T04 y 15 representaciones en [diseno.json](../registro/diagnostico/aplicabilidad59/diseno.json). Una fuente diferente detiene el cálculo, no actualiza las huellas automáticamente.
- Distancias entre orillas en EPSG:32614; centroides de T02 en WGS84 con distancia geodésica. Cercanía <20 m, general y de mismo municipio separadas. Celda significa celda principal T02; no se confunde con todas las celdas intersectadas.
- Rangos marginales globales y del municipio sobre valores originales, sin imputar. Las tolerancias numéricas se fijan por unidad; no representan incertidumbre física de medición.
- Soporte conjunto: distancia RMS de atributos estandarizados con desviación poblacional del entrenamiento. Área en log natural. Sólo D020 admite imputación de mediana del entrenamiento más indicador fijo, en la copia destinada a medir distancia; T07 no se modifica. No se aprende centrado residual ni un modelo nuevo.
- Se identifica el vecino de atributos global y del mismo municipio. La referencia de distancia local se obtiene entre filas del entrenamiento del mismo municipio, excluyendo la propia fila, con la escala del entrenamiento completo. No se ajusta nada con las entradas externas ni con las 59.
- Percentil estricto de distancia y comparación contra cuantíl95 `higher` +1e−12: una distancia cero empatada con otras cero no debe producir una falsa alerta p95. Mostrar n de referencia; con una sola etiqueta local el percentil es ausente, no cero. No convertir ese percentil en probabilidad de acierto ni en rechazo automático.
- La disponibilidad de entradas, los indicadores de observación y el soporte territorial se informan separados. Un faltante en una columna que el candidato no usa no se presenta como riesgo de ese candidato.
- Se conservan los resultados anteriores de T02/T09 y se concilian sus definiciones. Exactitud de perfil climático significa igualdad literal de las tres entradas de la ventana, igual que T09; no igualdad de rendimiento.
- Calidad estática, intervalos al corte y número de capturas no confirman máscara de nube, fecha de cosecha o disponibilidad histórica de publicación. Sólo la campaña 2025 está etiquetada.

## Entregables

Perfil legible de 59 IDs; soporte de sus 15 representaciones; soporte de las 138 por evaluación histórica; desgloses descriptivos de error sin intervalos nuevos; conciliación T02/T09; resumen por municipio; diccionario, manifiesto y auditoría. El detalle de 20,700 filas de atributos/evaluación se conserva local, separado del derivado compacto.

No se genera un semáforo de confianza calibrada. Para la app se proponen mensajes con razones concretas: pocas etiquetas locales, combinación poco representada, observación incompleta o dato histórico no acreditado. El dictamen final se actualizará cuando exista un procedimiento congelado y revisado.

## Comprobación prevista

Pruebas de exclusión de propias filas/evaluadas, invariancia al cambiar etiquetas, separación de escalas entrenadas, faltantes no admitidos, empates/constantes, municipios con 0/1/2 ejemplos y conservación de 59 IDs. Auditor separado de cálculos numéricos, conciliación con T02/T09 y reproducción Mac/Docker común. Destinos nuevos; originales y resultados anteriores inmutables.

Las secciones de resultados, incidencias y reproducción se añadirán tras el cálculo. El diseño no afirma que ya se haya ejecutado.
