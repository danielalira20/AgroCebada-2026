# T15 · Comparaciones concretas propuestas antes de ejecutar

> Antecedente histórico comun-v1. Para nuevas comparaciones se propone el [procedimiento centrado v2](evaluacion_comun_centrado_v2.md), con diseño y propuesta separados. Conserva la revisión humana pendiente y no ejecuta T15.

Fecha:13-oct2026. Responsable:Dani; corresponsable:Daf. Revisión metodológica de las extensiones a T03/T16:Migue. **Estado: propuesta escrita y comunicada; conformidad de Daf y revisión de Migue pendientes. Sin evaluación completa T15.**

## Problema que resuelve

T09,T10,T11,T14 comparten catálogo y referencia, pero difieren también en selección interna, regularización, ventanas e intercepto. Comparar sus mejores cifras directamente no permite aislar qué aporta cada bloque.

## Solución propuesta

La propuesta histórica v1 planteaba mantener `comun-v1` (huella `da633adf27c7f1cf2d7760dc2f190abe38d9a912f80a976717fc6213c48f76d3`) y cambiar únicamente el conjunto declarado de atributos. La familia, referencia, divisiones y reglas están en [procedimiento común](evaluacion_comun.md). Se conservarán los procedimientos históricos y se identificará cada resultado nuevo por su registro/código/entorno.

Se conocen resultados anteriores: es un registro previo a **la nueva corrida**, posterior a aquellos resultados. No constituye una validación externa ciega ni una prueba entre campañas. Las OOF del procedimiento ganador elegido entre varios tampoco son una prueba independiente nueva de ese ganador.

## Bloques y ocho procedimientos

| Código | Atributos y pregunta |
|---|---|
| C | Lluvia acumulada, Tmin y Tmax: ¿aporta clima sobre territorio? |
| G | Elevación, pendiente y área declarada en log natural: ¿aporta relieve/área? |
| P | Planet compacto: ¿aporta vegetación sobre territorio? |
| CG | ¿Clima y relieve/área se complementan? |
| CP | ¿Clima y vegetación se complementan? |
| GP | ¿Relieve/área y vegetación se complementan? |
| CGP | ¿Los tres bloques aportan juntos? |
| S | Sentinel-2 compacto: contraste de sensor frente a P, con iguales reglas. |

La referencia territorial sola se añade sin consumir uno de estos ocho procedimientos. Los nombres completos son `comun_v1_C`, etc. Planet se propone para el factorial de C/G/P por cobertura y continuidad T06/D006, **sin escogerlo por un MAE observado**. T06 documenta aproximadamente80capturas Planet frente a32S2; Daf debe confirmar este criterio y las columnas antes de fijar la lista. Si el equipo cambia el sensor factorial, se cambia el registro antes de evaluar.

Con siete combinaciones no vacías de C/G/P se puede preguntar por cada bloque en cuatro contextos: sobre referencia y sobre cada combinación de los otros dos. Un aporte condicional es predictivo; no equivale a un efecto causal del clima o del manejo. Este estimador es aditivo y no introduce términos de interacción explícitos.

### Columnas exactas

- C: `prec_acumulada_mm_{v}`, `tmin_media_c_{v}`, `tmax_media_c_{v}`.
- G: `elevacion_media_m`, `pendiente_media_t10_grados`, `area_ha_origen`.
- P: `pl_ndvi_max_{v}`, `pl_ndvi_integral_{v}`, `pl_lai2_max_{v}`, `pl_ndvi_dias_sobre_mitad_{v}`, `pl_ndvi_dia_inicio_{v}`, `pl_ndvi_al_corte`.
- S: `s2_ndvi_max_{v}`, `s2_ndvi_integral_{v}`, `s2_ndvi_dias_sobre_mitad_{v}`, `s2_ndwi_en_maximo_{v}`, `s2_ndvi_al_corte`.

`{v}` es `abr_oct` o `jun_oct`. En cada opción temporal todos los bloques usan la misma ventana. G es estático y no se duplica por ventana. Los atributos al corte son idénticos en las dos opciones. La pendiente añade su indicador fijo de ausencia en el transformador; no se convierte un vacío en cero observado. `area_explicita=true` sólo en procedimientos G; `calidad_explicita=false` en los ocho. No se añaden etiquetas, escalones, IDs, contornos, nubosidad o vecinos como predictores.

## Búsqueda y presupuesto

Cada procedimiento temporal tiene ocho opciones: dos ventanas×cuatroλ, con λ0.01/0.1/1/10 y α=n_entrenamiento×λ; G tiene cuatro. Cada uno puede elegir también referencia sola. MAE interno en la población con soporte municipal A/B; internas A municipales/otros y B por celda. Empate: MAE6dec→referencia→mayorλ→jun_oct. No se amplía búsqueda tras ver OOF.

| Unidad de trabajo, corrida A/B | Cantidad máxima |
|---|---:|
| Contextos externos T03 | 50 |
| Opciones con variables, sumadas entre los ocho procedimientos | 60 |
| Valoraciones opción×división interna | 13,600 |
| De ellas, valoraciones de referencia sola | 1,600 |
| Ajustes Ridge internos | 12,000 |
| Ajustes Ridge externos | 400 |
| Referencias externas compartidas | 50 |
| OOF: nueve procedimientos incluida referencia×1,380 claves | 12,420 |
| Ajustes finales sobre138/predicciones finales59 en este registro | 0 |

«Referencia sola» no ajusta un Ridge. Compartir referencias y divisiones reduce cálculo duplicado sin cambiar los scores. Si se cuenta cómputo realmente ejecutado, documentar también cachés y referencias reutilizadas; no confundir esta cota de comparaciones con ajustes únicos. Docker se usará sólo durante la ejecución y se apagará al terminar.

## Contrastes fijados

Ocho contrastes frente a referencia son los elegibles para promoción. Nueve contrastes condicionales son descriptivos: CG−G,CP−P,CGP−GP; CG−C,GP−P,CGP−CP; CP−C,GP−G,CGP−CG. El contraste S−P es descriptivo de sensor. Son18pares únicos, reportados en A/B y todas/sin_respaldo:72filas. Los tres aportes sobre vacío del factorial ya están incluidos entre los ocho contrastes frente a referencia.

Conservar ΔMAE primero por parcela, bootstrap5000celdas/semilla20261006, signos por repetición, ΔRMSE y R²; desgloses de T03§4bis y sensibilidad sin24, sin retirar esas24 del entrenamiento. Promoción: A/sin_respaldo, ΔMAE≤−0.01, límite superior IC95celdas<0, mejora≥4/5, ΔRMSE≤0.01. B obligatorio como sensibilidad. No se trata a cada uno de18intervalos como garantía familiar de error5%; tampoco se usa un contraste descriptivo para promover otra búsqueda no registrada.

## Coordinación y cierre del acuerdo

Solicitud y propuesta completas enviadas a [Daf en PR15](https://github.com/danielalira20/AgroCebada-2026/pull/15#issuecomment-6147012073), con confirmación solicitada de método, columnas, sensor factorial y lista. Extensiones metodológicas solicitadas a [Migue en PR18](https://github.com/danielalira20/AgroCebada-2026/pull/18#issuecomment-6147012434). Los comentarios contienen el método sin exigir acceso a la rama local aún no publicada.

No se registró una respuesta inexistente. El JSON [propuesta](../registro/evaluacion_comun/propuesta_t15_comparaciones.json) conserva `propuesto_pendiente_conformidad_Daf_y_revision_Migue`, y el contrato lo rechaza como ejecutable. La comprobación estructural de una copia en memoria confirmó8procedimientos/60opciones; no se guardó esa copia ni se ajustó ningún modelo.

Antes de ejecutar: incorporar respuestas verificables, versionar el diseño si cambió, guardar registro definitivo y commit previo, validar el ejecutor y destino nuevo, y conservar manifiesto al completar. Si no llegan las respuestas, se puede terminar documentación y controles; la nueva evaluación conjunta queda pendiente. La revisión de esta propuesta no aprueba T09 ni T11 automáticamente.
