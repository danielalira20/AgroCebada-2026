# T15 · contexto de las alertas de las 59 con referencia LOO en las 138

15 de octubre de 2026. Dani. Revisión pendiente de Migue/Daf. Complemento descriptivo del PR #21, base `4afabf081a341f3321fcd58a211d18b43ee5a3b4`.

## Problema que resuelve

Los 9/59 avisos de rango y los 19/59 de distancia local son una unión de 15 diagnósticos relacionados. Falta mostrar cuántas de las 138 etiquetadas activarían la misma regla, evaluando cada una fuera del conjunto que define su referencia. Sin ese contexto no se puede afirmar que los avisos distingan a las reservadas.

## Alcance acordado antes de calcular este complemento

[Diseño](../registro/diagnostico/aplicabilidad59/contraste_loo/diseno.json). Para cada etiquetada, referencia con las otras 137; para las reservadas, las 138. Se heredan íntegramente las 15 representaciones y reglas de C-v1, aprendiendo de nuevo las estadísticas de entradas en cada referencia. No se utilizan rendimientos para medir soporte ni se entrenan modelos predictivos.

Se comparan por representación, unión de las 15 y municipio. Se separan total, evaluables y sin diagnóstico: un q95 ausente no equivale a no tener aviso. Se conservan las salidas originales de C y se comprueban los 885 perfiles reservados al reproducirlos. La coincidencia de tasas no probaría igualdad ni eficacia predictiva. Este diseño es posterior a C y a la observación de Migue; no se presenta como análisis ciego.

La revisión del PR #22 se documentará por separado, con commit y alcance identificados. No se modifica su rama ni se integra al revisar.


## Resultado del complemento

| Aviso en alguna de las 15 representaciones | Etiquetadas evaluadas LOO | Reservadas | Interpretación |
|---|---:|---:|---|
| Alguna entrada fuera del rango global |28/138 (20.3 %)|9/59 (15.3 %)|También hay extremos entre las conocidas al excluir su propia fila.|
| Distancia local por encima de q95, sólo casos evaluables |42/135 (31.1 %)|19/58 (32.8 %)|Las tasas descriptivas son próximas; no prueban igualdad ni error predictivo.|
| Sin diagnóstico local q95 |3/138|1/59|Se conserva el vacío; no se cuenta como un resultado negativo.|

Para conciliar con el informe anterior, los avisos observados sobre el total son 42/138 (30.4 %) y 19/59 (32.2 %). **Las 19 alertas anteriores no cambiaron**: 19/58 expresa su frecuencia entre quienes sí tienen diagnóstico y 19/59 su frecuencia observada en toda la cohorte. En las 138 el q95 no se define para AGC_047, AGC_048 y AGC_164; en las reservadas, para AGC_120. No se elimina ninguna parcela.

Migue tenía razón en pedir este contexto: una unión de muchos diagnósticos relacionados también produce avisos en las entradas conocidas. No podemos afirmar que las reservadas sean en conjunto más atípicas por mostrar 19 avisos, ni convertirlos en 19 predicciones erróneas. Tampoco demostramos igualdad de distribuciones, calibración de riesgo o una mejora del modelo. Se comparan referencias de 137 frente a 138 parcelas, y la mezcla de municipios es distinta.

## Desglose territorial del aviso de distancia local

| Municipio | Parcelas etiquetadas con aviso / evaluables LOO | Parcelas reservadas con aviso / evaluables |
|---|---:|---:|
| Almoloya |4/10|2/4|
| Calpulalpan |7/30|3/14|
| Chignahuapan |21/71|10/29|
| Cuautepec de Hinojosa |3/5|2/4|
| Emiliano Zapata |2/3|Sin reservadas|
| Singuilucan |5/16|2/7|
| Apan, Nanacamilpa y Tepeapulco |Sin referencia local suficiente para LOO|Sólo Nanacamilpa tiene una reservada; sin referencia local suficiente|

Los grupos pequeños requieren mostrar n: 2/3 y 2/4 no se interpretan como tasas de fallo estimadas. El detalle por cada representación y municipio se entrega separado para evitar que una unión oculte qué variable motiva el aviso. Ningún umbral se escogió mirando rendimientos o resultados nuevos.

## Qué se añadió y qué se conservó

- Columna de referencia LOO en las dos filas pertinentes del informe C, con denominadores y unidades explícitos.
- Tablas de comparación por representación y municipio y perfil de unión de los 197 IDs, con diccionario. Los encabezados de conteos nuevos dicen `n_parcelas`; las sumas por particiones de la revisión PR22 son registros, no nuevas parcelas.
- Conservación de los CSV originales C y sus 885 perfiles reservada/representación. Se reprodujeron 15,930 campos contra la entrega anterior: estados y conteos exactos; diferencia numérica máxima 4.98e-14, con límite previo 1e-9. Los avisos reservados son los mismos.
- No se tocaron T07, las etiquetas, los resultados históricos, las particiones ni el procedimiento común. No se entrenó ningún modelo, no se escogieron parámetros y no hay nuevas predicciones ni MAE.

## Verificación y reproducción

Pasan **47 pruebas en Mac y 47 en Docker Linux/amd64, con Python `-O`**: 19 nuevas y 28 heredadas pertinentes. El auditor separado usa `statistics`, distancias `cdist` y cuantiles por orden, sin importar el productor ni estimadores. Reconstruye 2,085 espacios de referencia de entradas y verifica 2,955 perfiles con **42,364 comprobaciones por entorno**. Diferencia máxima frente al productor: 5.69e-14 <1e-9.

Los cuatro CSV compactos son idénticos byte por byte entre Mac y Docker, igual que la traza de particiones de PR22. Los atributos del detalle también coinciden numéricamente de forma exacta. La pequeña diferencia entre entornos de 3.71e-10 **metros** aparece en la distancia geodésica de la revisión PR22; no en los avisos ni en las entradas modelables. Docker se apagó y se confirmó la parada.

[Conteos y proporciones](../registro/diagnostico/aplicabilidad59/contraste_loo/comparacion_138_59.csv), [municipios](../registro/diagnostico/aplicabilidad59/contraste_loo/comparacion_por_municipio.csv), [perfil por parcela](../registro/diagnostico/aplicabilidad59/contraste_loo/perfil_union_197.csv), [diccionario](../registro/diagnostico/aplicabilidad59/contraste_loo/diccionario.csv), [verificación](../registro/diagnostico/aplicabilidad59/contraste_loo/verificacion.json) y [revisión del PR22](revision_pr22_protocolo.md).

Desde la raíz, con dos destinos nuevos y separados:

```text
python -O -m unittest tests.test_aplicabilidad_contraste_loo tests.test_diagnostico_aplicabilidad59 tests.test_aplicabilidad_agregacion -v
python -O -m scripts.aplicabilidad_contraste_loo --salida reports/contraste_loo_nuevo --detalle reports/contraste_loo_detalle_nuevo
python -O -m scripts.auditar_aplicabilidad_contraste_loo --salida reports/contraste_loo_nuevo --detalle reports/contraste_loo_detalle_nuevo --evidencia reports/auditoria_contraste_loo_nueva.json
```

El código conserva las salidas existentes: si un destino ya existe, se detiene. Los ajustes de estadísticas de entradas son diagnósticos, no entrenamientos predictivos. La revisión humana y la publicación de este complemento siguen pendientes; los logs y detalle completos quedan como evidencia local, no como CI anunciada.

Apoyo metodológico: skills privadas EDA y pensamiento crítico científico. Kassis, T., Agarwal, V., He, Y., Patel, D. y Brueckner, A. M. (2026), *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, versión consultada v2, [DOI](https://doi.org/10.48550/arXiv.2609.00065). Esta referencia explica el apoyo procedimental; no certifica el análisis ni demuestra eficacia predictiva.
