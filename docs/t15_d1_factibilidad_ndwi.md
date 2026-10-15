# T15 · D.1: factibilidad de NDWI posterior al máximo

14 de octubre de 2026. Responsable: Dani. Alcance autorizado: comprobar el punto 1 de la fase D, sin entrenar ni evaluar modelos. Diseño previo a calcular los perfiles; resultados y verificación se incorporarán después sin cambiar estas reglas por lo observado.

## Problema que resuelve

T06 y T13/T13e resumen NDWI alrededor del máximo de la curva de NDVI. Eso no comprueba si puede observarse de forma consistente un cambio posterior a ese máximo. Antes de registrar una evaluación predictiva, necesitamos saber si existe el soporte temporal, qué queda ausente y si la hipótesis duplica exactamente una representación ya probada.

## Solución y alcance

Auditar las series FIRA ya existentes para los 197 IDs y las dos ventanas, sin utilizar el rendimiento. Se parte de `dev` `97a8906b243b63f1e7c24ec85f7050642d9a98f5`, que ya incorpora T14 por PR #13. La rama del PR #21 se conserva estable; su propuesta B se cita como antecedente pendiente de revisión, no como experimento aceptado.

El [diseño estructurado](../registro/t15_d1/diseno.json) fija reglas, huellas, fuentes y controles antes del cálculo. No modifica T06/T07, etiquetas ni resultados históricos; no abre la fase de relieve ni descarga imágenes.

## Fórmula fijada

Sensor: Sentinel-2. Planet no contiene NDWI en el paquete PRO; no se obtiene ese índice de otro sensor ni se inventa.

1. Ventanas candidatas: 1-abr–31-oct y 1-jun–31-oct de 2025.
2. Cortar primero por fechas; conservar NDVI finito y nubosidad informada de 0 a 5 %, como T06. Una captura sin NDVI no entra a esta curva aunque tenga NDWI.
3. Requerir al menos cinco capturas válidas; mediana móvil centrada de tres capturas, con extremos de dos valores, como T06. Elegir la primera fecha del máximo exacto de esa curva. Un máximo observado no acredita una etapa agronómica.
4. Ancla: NDWI observado en esa fecha exacta, no la mediana de ±15 días de T06.
5. Posterior: media aritmética de NDWI en fechas válidas distintas entre máximo+15 y máximo+45 días, ambos extremos incluidos y sin superar el corte. Al menos dos fechas con NDWI finito.
6. Contraste candidato = media posterior menos NDWI del ancla. No interpolar NDWI, extrapolar, completar fechas ni sustituir un vacío por cero.

La media pondera observaciones por igual, no días. Se guardan fechas, número, separación, huecos y si el intervalo nominal llega más allá del corte. Cuando quedan dos fechas antes del corte puede calcularse el contraste, pero se declara el intervalo truncado; no se representa como observación completa de 45 días. Esa calidad necesitará una política explícita si se diseña un modelo.

Si falta soporte, se conserva la fila y su motivo. Se separan menos de cinco capturas, NDWI ausente en el ancla y menos de dos fechas posteriores. Los errores de esquema, claves duplicadas, fecha/valor malformado, sensor ajeno o fuente distinta detienen la ejecución; no se silencian como faltantes.

## Comprobaciones previstas

- Contrastar máximos y NDWI ±15 días con T06/T07 sin usar su implementación en el productor nuevo. Esa conciliación es una prueba de la regla previa, no un segundo predictor elegible.
- Auditor independiente mediante aritmética racional sobre los decimales originales; comparar anclas, fechas elegidas, conteos, vacíos y valores. Tolerancia numérica 1e-12 para índices; fechas, estados y conteos deben ser exactos.
- Probar corte antes del suavizado, nubosidad, dos extremos 15/45, NDWI ausente en ancla, cero real, duplicados, orden, empates, curva constante, intervalo truncado y falta de soporte. Una columna de rendimiento añadida o alterada no puede cambiar la salida.
- Proteger originales y tablas previas por huellas. Reproducir el alcance focalizado en Mac y Docker Linux/amd64 con Python -O; apagar Docker al terminar.
- Alcance completo: 394 perfiles Sentinel-2/parcela/ventana; no son 394 ejemplos etiquetados. Resumen separado de las 138 etiquetadas y las 59 reservadas usando sólo su pertenencia al conjunto.

## Novedad y límites

T13/T13e se examinan en [PR #20](https://github.com/danielalira20/AgroCebada-2026/pull/20), commit `50e656bdea1087be9c408cd96885cb7115abaa0e`. `t13_indices.py` usa NDWI de T06; `t13_extension_indices.py` resume las familias adicionales a ±15 días del máximo. No se encontró en esos dos scripts la media de 15–45 días posterior menos el ancla exacta. Esto acredita una diferencia en la representación inspeccionada; no una revisión universal de su PR ni una mejora de predicción.

El NDWI de FIRA se define como (B08−B11)/(B08+B11) en su documento de ecuaciones, página 1. Aquí se usan sus resúmenes originales; no se reconstruyen bandas ni se mide directamente agua del suelo. Una disminución posterior puede acompañar distintos procesos y no confirma estrés, cosecha o daño.

Los rasgos se describen con su soporte y, de forma secundaria, con variación entre/dentro de municipios y coincidencias con las entradas existentes. No se calculan correlaciones con rendimiento, MAE, selección de parámetros ni se decide qué ventana conviene. Las reglas para admitir faltantes de un predictor nuevo y su integración/evaluación quedan para una decisión posterior.

## Entregables previstos

Perfiles por ID/ventana, resúmenes por conjunto y municipio, conciliación de T06, evidencia de no duplicación, diccionario, manifiesto y auditoría; detalle por fecha local. Revisión visual de cuatro fallos compartidos y sus controles fijos, sin incluir etiquetas en los paneles ni escogerlos para favorecer el contraste. Ninguna descarga o información nueva de FIRA es necesaria para esta comprobación.

## Apoyo y fuentes

Plan unificado corregido consultado el 14-oct, revisión `AHj4eMTE…xN-rps0`; [propuesta B del PR #21](https://github.com/danielalira20/AgroCebada-2026/blob/4afabf0/docs/t15_fase_b_documental.md); [método T06](T06_satelite.md), código/entregas identificados por huellas; [ecuaciones originales de FIRA](Ecuaciones_indices_AgroCebada_FIRA_2026.pdf). Apoyo de las skills privadas T07, análisis exploratorio y pensamiento crítico científico; no son una certificación de aporte predictivo.
