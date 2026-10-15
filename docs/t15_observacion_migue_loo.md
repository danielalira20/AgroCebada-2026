# T15 · contexto de las alertas de las 59 con referencia LOO en las 138

15 de octubre de 2026. Dani. Revisión pendiente de Migue/Daf. Complemento descriptivo del PR #21, base `4afabf081a341f3321fcd58a211d18b43ee5a3b4`.

## Problema que resuelve

Los 9/59 avisos de rango y los 19/59 de distancia local son una unión de 15 diagnósticos relacionados. Falta mostrar cuántas de las 138 etiquetadas activarían la misma regla, evaluando cada una fuera del conjunto que define su referencia. Sin ese contexto no se puede afirmar que los avisos distingan a las reservadas.

## Alcance acordado antes de calcular este complemento

[Diseño](../registro/diagnostico/aplicabilidad59/contraste_loo/diseno.json). Para cada etiquetada, referencia con las otras 137; para las reservadas, las 138. Se heredan íntegramente las 15 representaciones y reglas de C-v1, aprendiendo de nuevo las estadísticas de entradas en cada referencia. No se utilizan rendimientos para medir soporte ni se entrenan modelos predictivos.

Se comparan por representación, unión de las 15 y municipio. Se separan total, evaluables y sin diagnóstico: un q95 ausente no equivale a no tener aviso. Se conservan las salidas originales de C y se comprueban los 885 perfiles reservados al reproducirlos. La coincidencia de tasas no probaría igualdad ni eficacia predictiva. Este diseño es posterior a C y a la observación de Migue; no se presenta como análisis ciego.

La revisión del PR #22 se documentará por separado, con commit y alcance identificados. No se modifica su rama ni se integra al revisar.
