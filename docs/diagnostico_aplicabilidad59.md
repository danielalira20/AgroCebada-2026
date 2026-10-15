# C descriptiva · aplicabilidad preliminar a las 59

14 de octubre de 2026. Diseño registrado antes del cálculo; entrega técnica local verificada. Responsable: Dani; revisión: Daf/Migue. La fase C conserva la fase 5 del diagnóstico original. No es T18 ni una nueva evaluación de modelos.

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

El diseño anterior se registró antes de calcular; las secciones siguientes documentan los resultados y su verificación, conservando ese alcance.


## Resultado técnico local

La entrega C quedó generada y verificada; revisión humana pendiente. Conserva59 IDs sin rendimiento y138 etiquetas originales. No se ejecutaron T15/T18 ni se ajustó un estimador predictivo. Se inspeccionaron15 representaciones de entradas,885 perfiles reservada/representación y1,380 contextos OOF históricos. El detalle local de20,700 perfiles OOF no aumenta el número de parcelas independientes.

| Comprobación | Resultado | Interpretación |
|---|---:|---|
| Municipio representado |59/59|Pertinencia territorial parcial de A; no garantía de rendimiento|
| Clima completo en ambas ventanas |59/59|No equivale a clima disponible históricamente al corte|
| Entradas candidatas ausentes en reservadas |0/59|D020 sigue existiendo en dos etiquetadas; no se cambia su política|
| Vecina etiquetada local <20m |24/59|Disponibilidad al usar las138; no independencia ni beneficio probado|
| Perfil climático literalmente repetido |49/59 por ventana|No son49 rendimientos conocidos ni equivalencia agronómica|
| Celda climática principal sin etiquetas |2/59|AGC_147 yAGC_174; la definición es celda principal, no toda intersección|
| Menos de cuatro etiquetas locales |1/59|AGC_120, Nanacamilpa, con una; percentil local no calculable|
| Alguna entrada fuera del rango global |9/59|Aviso por variable y candidato; magnitudes distintas|
| Alguna combinación supera su referencia q95 local |19/59|Unión de15 diagnósticos; no son19 errores ni19 probabilidades de fallo|
| Alerta de contorno T03bis |12/59|Atlas sin fecha2025; no confirma daño ni justifica excluir|

Los19 avisos de combinación y los9 de rango pueden coincidir. La cantidad depende de las representaciones inspeccionadas; no se transforma en un riesgo calibrado. Una parcela puede estar dentro de todos los rangos individuales y tener una combinación poco representada. El diagnóstico no selecciona qué modelo usar por parcela.

### Distribución territorial

| Municipio | Etiquetadas | Reservadas | Con vecina local <20m | Celda principal nueva | Con alguna entrada fuera del rango global |
|---|---:|---:|---:|---:|---:|
|Almoloya|10|4|1|0|1|
|Apan|1|0|0|0|0|
|Calpulalpan|30|14|2|1|0|
|Chignahuapan|71|29|14|0|8|
|Cuautepec de Hinojosa|5|4|3|1|0|
|Emiliano Zapata|3|0|0|0|0|
|Nanacamilpa de Mariano Arista|1|1|0|0|0|
|Singuilucan|16|7|4|0|0|
|Tepeapulco|1|0|0|0|0|

Chignahuapan concentra29 reservadas y8 de los9 casos con alguna entrada fuera del rango global. Eso orienta la inspección, pero no justifica entrenar o decidir sólo con ese municipio. AGC_120 requiere declarar soporte local escaso aun cuando comparta una celda ya observada. Las dos celdas nuevas pertenecen a municipios conocidos: nueva celda no es nuevo municipio.

### Variables fuera del rango global

La lista conserva valores originales, no recortes ni sustituciones. Una repetición del mismo máximo en ambas ventanas no son dos fallos independientes.

| Parcela | Variable | Valor reservado | Mínimo etiquetadas | Máximo etiquetadas |
|---|---|---:|---:|---:|
|AGC_036|s2_ndvi_dias_sobre_mitad_abr_oct|143|59|137|
|AGC_036|s2_ndvi_integral_jun_oct|17.6145|19.0905|58.0675|
|AGC_043|pl_ndvi_al_corte|0.795|0.325|0.773|
|AGC_043|s2_ndvi_al_corte|0.699|0.25|0.6955|
|AGC_082|s2_ndvi_integral_jun_oct|19.037|19.0905|58.0675|
|AGC_088|elevacion_media_m|2906.0395|2496.6485|2903.9904|
|AGC_091|area_ha_origen|0.35|0.38|64.3|
|AGC_136|s2_ndvi_dias_sobre_mitad_abr_oct|139|59|137|
|AGC_142|pl_ndvi_integral_jun_oct|24.75925|28.14125|62.422|
|AGC_142|pl_ndvi_max_abr_oct|0.545|0.55|0.893|
|AGC_142|pl_ndvi_max_jun_oct|0.545|0.55|0.893|
|AGC_142|s2_ndvi_max_abr_oct|0.439|0.464|0.808|
|AGC_142|s2_ndvi_max_jun_oct|0.439|0.464|0.808|
|AGC_143|pl_ndvi_integral_jun_oct|23.891|28.14125|62.422|
|AGC_153|pendiente_media_t10_grados|0.28186452|0.28767079|9.3963947|

AGC_088 supera la elevación máxima conocida en unos2.05m; AGC_091 tiene0.35ha frente al mínimo0.38ha; AGC_153 tiene una pendiente apenas inferior al mínimo. Esos casos no deben equipararse automáticamente con AGC_142, cuyo máximo NDVI e integral de algunas ventanas son inferiores a los rangos conocidos. No se diagnostica un daño, etiqueta o cosecha a partir de esas diferencias. AGC_043 conserva verdor al corte superior al rango observado; no se declara mejor rendimiento por ello.

### Correspondencia con A y B

Con todas las138 disponibles,24/59 reservadas tienen una vecina local <20m:40.7%. En las evaluaciones A/sin_respaldo,309/675 registros históricos tienen esa disponibilidad:45.8%. En B/sin_respaldo son45/659:6.8%. Son contextos parcela/repetición, no675 o659 parcelas diferentes. La condición puede cambiar entre repeticiones, y un ID puede aparecer en ambos grupos.

La cercanía de esos porcentajes apoya la pertinencia de A respecto a esta dimensión concreta de soporte. No valida por sí sola toda la distribución de las59, confirma independencia ni demuestra generalización futura. B sigue siendo obligatorio como sensibilidad espacial; los pocos ejemplos de un municipio, celdas nuevas y calidad de entradas se conservan como dimensiones separadas.

### Cuidado con la unidad de agregación del error

[Complemento de agregación](../registro/diagnostico/aplicabilidad59/agregacion_por_parcela/error_por_soporte_unidad_parcela.csv) conserva ambas unidades y la media por repetición. Primero se calcula la pérdida dentro de cada ID y luego se promedia entre IDs para la comparación por parcela; RMSE usa pérdidas cuadráticas y nunca el error de promediar predicciones.

| Referencia histórica, sin_respaldo | MAE por parcela | MAE por registro | Media MAE por repetición |
|---|---:|---:|---:|
| A |0.320489710387|0.320489710387|0.320489710387|
| B |0.363187374908|0.358432042728|0.357867408564|

B tiene135 IDs y659 registros elegibles; algunos IDs aportan cuatro repeticiones y otros cinco. Las cifras difieren por ponderación: no son predicciones distintas ni una mejora nueva. En los desgloses una misma parcela puede cambiar de grupo entre repeticiones; no sumar tamaños/MAE de grupos como si fueran poblaciones independientes.

Diccionario del complemento: `n_registros` cuenta filas; `n_parcelas` cuenta IDs; los campos `n_repeticiones_por_parcela_min/max` muestran el peso variable. `MAE_por_parcela_t_ha`, `RMSE_por_parcela_t_ha` y `sesgo_por_parcela_t_ha` promedian primero la pérdida/error dentro de cada ID; `MAE_por_registro_t_ha` y `RMSE_por_registro_t_ha` ponderan filas igualmente. `MAE_media_repeticiones_t_ha` promedia los MAE de repeticiones con datos. Escenario, representación, subconjunto, dimensión y categoría tienen las definiciones del diccionario C principal. Son métricas de T08 ya existente; no desempeño del método v3.

## Escenarios para la app y siguiente trabajo

- Municipio representado y entradas completas: describir el número de etiquetas, sin declarar confianza alta sólo por pertenecer al municipio.
- Vecina local: mostrar disponibilidad y advertir dependencia; no copiar su rendimiento ni activar V20 antes de su evaluación.
- Celda principal nueva o combinación poco representada: indicar los bloques implicados y su soporte, sin rechazo automático.
- Municipio con una etiqueta: declarar que no se observa variación local suficiente; percentil ausente con motivo.
- Contorno/observación: mostrar el dato de calidad y su procedencia; no diagnosticar siniestros, fecha de cosecha o pureza de píxel.
- Otra campaña o corte más temprano: uso diferente, sin validación temporal etiquetada. La disponibilidad de observación y publicación siguen separadas.

La selección del modelo, cualquier respaldo por riesgo o umbral de acción necesita diseño y validación dentro del entrenamiento; esta tabla no decide ninguno. H actualizará la aplicabilidad con el procedimiento congelado. C no espera una respuesta nueva de FIRA ni una fuente externa.

## Verificación e incidencias

28 pruebas aprobadas en Mac y Docker Linux/amd64, estas últimas con Python-O. El auditor independiente, sin importar productor/modelos, verificó297,889 comparaciones en cada entorno sobre las197 geometrías y21,585 registros de atributos (885 reservadas más20,700 OOF). Usó `statistics` y `cdist`, y una proyección explícita con distancias escalares para contrastar la matriz geográfica.

Diferencia máxima frente al auditor en atributos/estado/errores:2.274e−12; geométrica:4.55e−11m. Entre Mac y Docker:4.44e−16 en los valores no geométricos y2.544e−9m en distancias, dentro de sus tolerancias por unidad. Se realizaron661,916 comparaciones entre entornos/estados y1,239 transferencias adicionales de calidad. Las745 huellas de archivos previos protegidos, incluido DataSet.zip, se conservaron.

Incidencias propias resueltas:

1. El primer auditor no reconocía un booleano NumPy y lo comparó como texto. Se amplió la lectura de tipos booleanos; no se cambiaron cálculos o valores. El control completo posterior pasó en ambos entornos.
2. La primera clasificación de unidades del comparador no reconocía el nombre extendido de la diferencia de centros T02 y le asignó tolerancia adimensional. Se corrigió la identificación de la unidad métrica, conservando el límite geométrico1mm y el numérico1e−9; no se ampliaron indiscriminadamente.
3. Se distinguieron promedios de registros, parcelas y repeticiones mediante un complemento auditable. No se reescribieron los resultados anteriores ni se pretendió resolver esa diferencia cambiando predicciones.
4. El diccionario se completó sin tocar resultados: seis tablas numéricas permanecieron idénticas entre la primera generación y la final.

Empates en distancia cero, escala constante, municipio ausente/único, propios IDs, duplicados, faltantes D020, mutación de X evaluada, etiquetas irrelevantes al soporte, destinos existentes y peso desigual entre repeticiones tienen controles. Una comprobación esencial confirmó las ocho comparaciones y60 opciones principales de B y que la propuesta pendiente sigue rechazada por el ejecutor común.

Docker se usó sólo para la comprobación y se apagó al terminar. El detalle queda local; la entrega compacta incluye tablas, diccionario, manifiesto y verificación. Revisión humana de C y de la implementación v3 pendiente. No hubo push, publicación, merge remoto ni edición del GoogleDoc.

## Reproducción

Desde la raíz del repositorio, en el entorno común, usando destinos nuevos:

```text
python -m scripts.diagnostico_aplicabilidad59 --salida data/processed/t15_aplicabilidad/nueva --detalle data/processed/t15_aplicabilidad/nueva_detalle
python -m scripts.auditar_aplicabilidad59 --salida data/processed/t15_aplicabilidad/nueva --detalle data/processed/t15_aplicabilidad/nueva_detalle --evidencia data/processed/t15_aplicabilidad/auditoria_nueva.json
python -m scripts.aplicabilidad_agregacion --compactos data/processed/t15_aplicabilidad/nueva --detalle data/processed/t15_aplicabilidad/nueva_detalle --salida data/processed/t15_aplicabilidad/agregacion_nueva
python -m unittest tests.test_diagnostico_aplicabilidad59 tests.test_aplicabilidad_agregacion
```

Los cuatro comandos pueden ejecutarse mediante los lanzadores Docker comunes del README. El análisis lee directamente DataSet.zip identificado, sin alterar la copia QGIS. No requiere descargar datos externos ni cargar un modelo guardado. Los destinos existentes se rechazan para conservar evidencia.

## Fuentes y apoyo

T02/T03/T04/T05/T06/T07/T08/T09 identificadas por huellas en el diseño/manifiesto; propuesta común v3 de fase A; plan unificado corregido consultado el14oct2026, revisión AHj4eMTE…xN-rps0. Datos de calidad de T06 no acreditan por sí solos la máscara exacta de nube ni la disponibilidad histórica. La incidencia de interpolación AGC114 continúa asignada a Daf; C usa la tabla compartida y no reextrae esa variable.

Apoyo de las skills privadas T07, análisis exploratorio y GeoPandas, junto con los criterios de pensamiento crítico/scikit-learn ya utilizados. Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. [arXiv:2609.00065](https://arxiv.org/abs/2609.00065), [DOI](https://doi.org/10.48550/arXiv.2609.00065), versión vigente v2 consultada el14oct2026. Apoyo procedimental, no evidencia de mejora agronómica. [Separación entrenamiento/evaluación, documentación primaria](https://scikit-learn.org/stable/common_pitfalls.html).
