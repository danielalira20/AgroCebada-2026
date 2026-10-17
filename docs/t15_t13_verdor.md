# T15: familia de verdor de T13 con el procedimiento común

## Problema que resuelve

T13 anterior no acredita esta comparación bajo centrado H3/LOO coherente y selección espacial interna en B. Se conserva su entrega original del [PR20](https://github.com/danielalira20/AgroCebada-2026/pull/20), head `d6db802d40060d0705c51b12858322c1024a1ca0`, fusionado el 17-oct. No es una revisión integral de todas las familias de T13.

## Solución que implementa

Un candidato: cinco rasgos S de abril–octubre más la familia original EVI/SAVI/FAPAR/MRA de T13e CONFIGS[1]. Su control usa exactamente los mismos cinco rasgos S y la misma ventana. Cada procedimiento compara referencia sola y cuatro lambda comunes, con selección independiente dentro del entrenamiento. Los S de junio–octubre no se mezclan con la familia de abril–octubre: eso rompería el contraste simétrico. El S anterior que elegía entre ambas ventanas se conserva sólo como contexto descriptivo.

La familia se fijó por representación compacta original y disponibilidad de datos, no por ser la de menor MAE histórico. Ya conocemos resultados anteriores: ésta es evidencia exploratoria retrospectiva de una sola campaña, no una confirmación externa ciega ni una garantía futura. MRA carece de definición física acreditada en la documentación consultada; se conserva por identidad de la familia, sin atribuirle un mecanismo o importancia causal.

## Registro y fases

El contrato se guardó en 34bb8ad antes de generar nuevas OOF, implementación en e31398c, mejoras de memoria/reporte en c8dbac8 y puerta Mac/Linux en 96523af. Ambos completos identifican este último commit. Contrato SHA256 `620b9e497a4d97df02d23162c9c96f1d1f56f980cd0803c73a4b7e22a3b81156`.

1. Fuentes/versiones, ventana, comparadores y criterios fijados antes de ejecución.
2. Cotejo directo contra el CSV del ZIP original, sin rendimiento ni funciones T06/T13.
3. Pruebas de H3 y aislamiento, piloto real A/B y reconstrucción independiente Mac/Linux.
4. Evaluación completa de 50 contextos y auditoría de selección, ajuste, reportes y decisión.
5. Conservación de datos, resultados, incidencias y límites de interpretación.

## Datos y calidad

197 IDs conservados, 138 rendimientos conocidos y 59 objetivos ausentes. Las 59 no participan en ajustes, selección interna ni evaluación; su presencia en el cotejo de resúmenes sin rendimiento no es entrenamiento. Los 197 resúmenes coinciden en 1,576 comprobaciones con diferencia cero contra el ZIP original. Las capturas se limitan a 2025-04-01..2025-10-31, Sentinel-2 y nubosidad<=5%; NDVI con mediana móvil de 3, primer máximo en empate y mediana de cada índice en ±15 días de ese máximo. No se fabrican índices desde bandas o promedios no equivalentes.

Hay 25–38 capturas válidas por parcela en temporada y 1–8 alrededor del máximo; una parcela tiene sólo una en ese intervalo. Se conserva y se declara, sin cambiar umbrales ni excluir por su error. Las fechas de publicación original no están acreditadas; esta prueba tampoco certifica disponibilidad prospectiva al corte. Los índices resumen las medias parcelarias entregadas por FIRA, no nuevos píxeles de Sentinel-2.

## Ajuste y controles de filtración

Núcleo `comun-centrado-loo-v3` intacto: escala global aprendida sólo con entrenamiento; residuo y centro LOO usan el mismo pool sin la propia fila; en consulta se usan centros municipio/grupo/global del entrenamiento completo. Ridge SVD sin intercepto, alpha=n_entrenamiento*lambda, lambda=[.01,.1,1,10]. No imputación de S/familia. IDs, duplicados, fuentes y valores no finitos se rechazan antes del ajuste.

A/B mantienen 5 repeticiones × 5 externas y 4 internas. A estratifica municipio/otros con semilla 0; B separa celdas CHIRPS dentro y fuera. MAE de selección sólo sobre municipios conocidos; empate MAE redondeado a 6 decimales prioriza referencia sola y luego lambda mayor. No se usa etiqueta externa ni reservada para seleccionar/preparar. Los centros y coeficientes no se actualizan al consultar datos nuevos.

Por entorno: 2,100 ajustes (2,000 internos, 100 externos), 1,600 Ridge internos, 100 selecciones, 2,760 OOF nuevas. Se conservan literalmente 4,140 OOF de media, mediana y S anterior: 6,900 en total. No son 6,900 parcelas independientes. Referencia sola se elige de nuevo dentro de cada procedimiento; no se fuerza a utilizar los índices.

## Resultados principales

A/sin_respaldo: 135 parcelas, 675 OOF por procedimiento. MAE por parcela; RMSE y R² promediados entre las cinco repeticiones. MAE/RMSE en t/ha; R² sin unidad. No se promedian predicciones antes de medir errores.

| Procedimiento | MAE | RMSE | R² |
|---|---:|---:|---:|
| Media municipal | 0.320489710 | 0.492593095 | 0.658576745 |
| Mediana municipal (contexto, T08-v1) | 0.312585185 | 0.490682747 | 0.661222527 |
| S anterior con selección de dos ventanas (contexto) | 0.321669551 | 0.490676981 | 0.661211591 |
| Control simétrico S abril–octubre | 0.322500454 | 0.492654943 | 0.658483503 |
| S abril–octubre + verdor T13 | 0.323550368 | 0.493433732 | 0.657402228 |

| Contraste de S+verdor | ΔMAE | IC95 por celdas del ΔMAE | ΔRMSE | Repeticiones que mejoran MAE |
|---|---:|---|---:|---:|
| Frente a Media municipal | +0.003060658 | [+0.000092907, +0.007425484] | +0.000840636 | 0/5 |
| Frente a Control simétrico S abril–octubre | +0.001049914 | [+0.000112991, +0.002915478] | +0.000778788 | 1/5 |
| Frente a Mediana municipal (contexto, T08-v1) | +0.010965183 | [-0.000112653, +0.018361797] | +0.002750984 | 0/5 |
| Frente a S anterior con selección de dos ventanas (contexto) | +0.001880818 | [+0.000019465, +0.004580052] | +0.002756750 | 1/5 |

ΔMAE positivo significa empeoramiento. Los intervalos reproducen 5,000 remuestras de celdas CHIRPS, semilla 20261006; 22 celdas en el principal. El IC no elimina la exposición acumulada a experimentos anteriores ni acredita una campaña futura.

La familia no cumple T03 frente a media ni la guardia adicional de aporte frente al control simétrico: se mantiene la referencia municipal y no se incorpora este bloque a la entrega actual. No se cambian la rejilla, la ventana, MRA ni la regla para buscar una cifra distinta después de ver el resultado. Esta conclusión se limita a esta familia/resumen/procedimiento, no a todos los índices o al satélite en general.

## Cuánto se utilizó y dónde cambió

| Procedimiento/escenario | Referencia sola | Con corrección | Total |
|---|---:|---:|---:|
| S abril–octubre + verdor T13, A | 17 | 8 | 25 |
| S abril–octubre + verdor T13, B | 12 | 13 | 25 |
| Control simétrico S abril–octubre, A | 13 | 12 | 25 |
| Control simétrico S abril–octubre, B | 11 | 14 | 25 |

En A, frente al control, 57 parcelas reducen su error medio, 72 lo aumentan y 6 empatan dentro de 1e-12. Se mantienen las 135 de la comparación; no se selecciona un modelo distinto para cada parcela mirando su etiqueta. [Errores por ID](../registro/t15_t13/perfiles_linux.csv).

La corrección absoluta media del candidato en A/sin_respaldo es 0.013316 t/ha frente a la media municipal; consulta las frecuencias para distinguir una referencia elegida de una corrección pequeña.

Como descriptivo posterior sin objetivos, los cuatro índices presentan correlación de Pearson intramunicipal de 0.901 a 0.923 con el máximo NDVI. Es compatible con redundancia de representación; no demuestra que la correlación sea la única causa del resultado ni que todas las señales nuevas sean inútiles. No se utilizó este cálculo para cambiar variables o selección. Valores y cálculo escalar en `redundancia_verificada_sin_etiquetas.json` y `redundancia_t13.py`.

## Sensibilidad espacial B

B/sin_respaldo conserva 135 IDs y 659 predicciones elegibles por procedimiento; no debe confundirse el peso por ID con el promedio por registro. No decide la promoción.

| Procedimiento | MAE por ID | RMSE medio por repetición | R² medio por repetición |
|---|---:|---:|---:|
| S anterior con selección de dos ventanas (contexto) | 0.351920870 | 0.510406082 | 0.628092023 |
| Media municipal | 0.363187375 | 0.521985168 | 0.610963386 |
| Mediana municipal (contexto, T08-v1) | 0.347481481 | 0.516424493 | 0.619179979 |
| S abril–octubre + verdor T13 | 0.363609156 | 0.519348572 | 0.614939444 |
| Control simétrico S abril–octubre | 0.360319183 | 0.516967997 | 0.618471824 |

Se incluyen además población completa, municipio, grupo de registro, contorno, tamaño/forma, escalón de etiqueta, vecina cercana y sensibilidad sin las 24, sólo como desgloses de las mismas OOF. No se excluyen esas 24 del entrenamiento ni se transforma un desglose favorable en un nuevo ganador.

## Verificación e incidencias

44 pruebas aprobadas por entorno (18 nuevas y 26 de LOO común), también con Python -O. Cada completo fue auditado con ecuaciones normales y pools explícitos, sin importar el productor ni sklearn: 717,346 comprobaciones en Mac y 717,346 en Linux, más 5,780 verificaciones escalares de métricas por entorno. Coinciden selección interna, coeficientes, centros, OOF, MAE/RMSE/R², intervalos, frecuencias y decisión. Máxima diferencia Mac/auditor 1.45e-14; Linux/auditor 1.42e-14; tolerancia 1e-12 intacta. Cotejo entre plataformas: 7,290,354 campos, máximo 1.42e-14; mismas 100 selecciones.

La prueba adversarial quita H3 y recompone la suma de predicción: el auditor la rechaza. Inyectar etiquetas en consultas, alterar su escala o su orden no permite aprender de ellas. Duplicados/faltantes e intento de usar rendimiento como predictor también se rechazan. Esto aporta evidencia de integridad, no una garantía absoluta de ausencia de cualquier defecto.

Se corrigieron dos problemas antes de la evaluación completa: lectura innecesaria de todo el CSV en memoria (primer Linux terminó con 137; OOM no acreditado directamente porque el contenedor se eliminaba) y conexión de reportes que exigía una sola versión, incompatible con conservar la mediana T08-v1. Lectura por filas y SHA por bloques permitió completar la misma prueba con 768 MiB; el reportador verifica versiones por candidato sin reetiquetar ni alterar OOF previas. [Detalle de incidencias](../registro/t15_t13/verificacion_previa/incidencias.json).

Además se fijó LF explícito en el CSV derivado de perfiles y su escritor tras el aviso de normalización de Git; no cambió ningún valor. El inventario se verifica también contra los bytes guardados por Git para que funcione al clonar. Los resultados y manifiestos originales permanecen intactos.

## Archivos y reproducción

- [Contrato y fuentes](../registro/t15_t13/contrato_v1.json): registro anterior a nuevas OOF y fuentes exactas del PR20.
- [Puerta previa](../registro/t15_t13/verificacion_previa/puerta.json): pruebas, cotejo ZIP y pilotos Mac/Linux.
- [OOF completas](../registro/t15_t13/resultados/predicciones_oof.csv), [métricas](../registro/t15_t13/resultados/metricas_resumen.csv), [contrastes](../registro/t15_t13/resultados/contrastes.csv), [decisión](../registro/t15_t13/resultados/decision.json).
- [Paquete e inventario](../registro/t15_t13/entrega.json): resultados canónicos Linux/amd64, trazas comprimidas sin pérdida, auditorías, comparador entre plataformas y perfiles. Originales inmutables.

Desde raíz, dentro del entorno fijado (salidas nuevas en reports/):

```bash
python -O -m unittest tests.test_t15_t13 tests.test_evaluacion_comun_centrado_loo
python -O -m scripts.t15_t13_datos --salida reports/t13_cotejo_nuevo.json
python -O -m scripts.t15_t13_ejecutar --modo prueba --salida reports/t13_piloto_nuevo
python -O -m scripts.t15_t13_ejecutar --modo completa --puerta registro/t15_t13/verificacion_previa/puerta.json --salida reports/t13_completa_nueva
python -O -m scripts.t15_t13_auditar --raiz . --entrada reports/t13_completa_nueva --salida reports/t13_auditoria_nueva.json
```
El cotejo de originales requiere DataSet.zip. Reproducción de modelos/OOF usa el resumen compacto verificado, sin volver a ejecutar T13 histórico. Docker usa imagen fijada `sha256:b2dea1bd162fb607dedb4e1a670edde239743db940d2868e2167f7414e8875aa`, Linux/amd64, sin red, repo de sólo lectura, 768 MiB y un hilo BLAS. Se conserva el entorno medido en los manifiestos. Los manifiestos y decision.json preservan el estado previo a las auditorías; entrega.json vincula sus huellas con las auditorías aprobadas y registra el estado técnico final sin reescribir la corrida original.

## Qué sigue pendiente

La alternativa 2 queda evaluada técnicamente y sin promoción; no se declara una revisión humana externa. Suelo, nueva representación temporal, eventos diarios y bandas/radar requieren hipótesis y pilotos propios; no se abren por cambiar esta conclusión. Aplicabilidad final a 59, decisión T16, entrenamiento con 138, CSV y aplicación siguen pendientes. Esta rama es local: no hubo push, PR ni merge de este lote.

## Fuentes metodológicas

[Documentación oficial Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html) y [prevención de filtraciones](https://scikit-learn.org/stable/common_pitfalls.html). Apoyo de skills scikit-learn y scientific-critical-thinking. Kassis, T.; Agarwal, V.; He, Y.; Patel, D.; Brueckner, A.M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. [Registro vigente](https://doi.org/10.48550/arXiv.2609.00065), metadatos verificados 17-oct-2026. Su uso no demuestra mejora predictiva.
