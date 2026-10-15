# Informe de cierre · T10, aporte de relieve y área

- **Responsable:** Jass. **Revisora:** Daf. **Fecha:** 12 de octubre de 2026; actualizado el 15 de octubre de 2026 (`D_T10_004`: distinción entre combinaciones centradas y sin centrar).
- **Método:** [`docs/T10_relieve_area.md`](../../docs/T10_relieve_area.md) y decisión `D_T10_001`, escritos antes de correr.
- **Resultados:** `registro/t10/`. **Bitácora:** [`bitacora.md`](bitacora.md).

## En una frase

Con este procedimiento, estas entradas y esta campaña, **saber la elevación, la pendiente y el tamaño de una parcela no mejora la estimación que da el promedio de su municipio** según las reglas del equipo; se conserva la referencia `media_mun__resp_grupo`.

## Qué preguntamos

La referencia del equipo estima el rendimiento de una parcela con el promedio de las parcelas conocidas de su municipio. Es como tasar una casa con el precio promedio de su colonia. T10 preguntó si conocer «los metros y la inclinación del terreno» afina esa tasación o sólo añade ruido, y si eso cambia en las parcelas pequeñas o con datos de relieve incompletos.

## Qué hicimos

1. **Escribimos el diseño antes de ver resultados** (`D_T10_001`), incluida una declaración de lo que ya se había visto de estas variables durante la exploración inicial del dataset.
2. **Probamos 6 combinaciones** de elevación, pendiente y área (en logaritmo) sobre la referencia, con las mismas particiones, subconjuntos y regla de decisión de T03 que el resto del equipo.
3. **Dejamos que el propio procedimiento pudiera decir «no uses las variables»** (opción «referencia sola») y elegimos su ajuste con la misma métrica con la que se juzga (error absoluto).
4. **Corrimos en paralelo el procedimiento de T11** como «puente», sólo para comparar; nunca decide.
5. **Miramos el error por tamaño, cobertura de relieve y tipo de contorno**, y sin las 24 parcelas con alerta de contorno.
6. **Después**, como exploración, describimos la correlación de cada variable con el rendimiento.

## Qué encontramos

- **Ninguna combinación cumple la regla de T03.** En el escenario principal (A), el error promedio cambia entre +0.0002 y +0.0027 t/ha frente a un error de la referencia de 0.3205 t/ha: es decir, no mejora; en todos los casos el intervalo incluye el cero y a lo sumo 2 de 5 repeticiones mejoran. En el escenario de separación espacial (B) pasa lo mismo.
- **Hay que distinguir dos tipos de combinación** (aclaración del 15 de octubre). Las combinaciones 1 a 5 usan las variables tal cual; la 6 las compara con el promedio de su municipio («centradas»). Como la referencia ya incluye el municipio, sólo la 6 mide si relieve y área ayudan **dentro** del municipio. Las 1 a 5 responden otra pregunta: si las variables tal cual mejoran la referencia. Con ninguna de las dos lecturas se mejora la referencia.
- **El procedimiento lo confirma por su cuenta:** ajustado con las 138 parcelas, elige «referencia sola» en las 6 combinaciones. Sus predicciones para las 59 reservadas son idénticas a las de la referencia.
- **El procedimiento de T11 (puente) sale peor con estas variables:** su error promedio sube entre 0.010 y 0.020 t/ha en A, y el principal le gana en las 12 comparaciones de error promedio. Ojo: el puente y el principal se diferencian en dos cosas a la vez (la opción «referencia sola» y el criterio con que se elige el ajuste), así que esta comparación no dice cuál de las dos pesa más, y sólo se hizo con el bloque de relieve y área.
- **La relación que sí existe es débil y local.** Dentro de cada municipio, la pendiente y el área se asocian con el rendimiento con r ≈ ±0.24, casi todo en Chignahuapan; en Calpulalpan es prácticamente cero. Explica cerca del 6 % de lo que el municipio no explica, y no alcanza para predecir mejor parcelas nuevas.

## Preguntas y respuestas

**¿Relieve y área aportan algo sobre el territorio?**
No con este procedimiento. Ninguna de las 6 combinaciones mejora la referencia según la regla del equipo, ni en A ni en B, ni con ni sin las 24 parcelas con alerta de contorno.

**¿Cuál variable funcionó mejor?**
Ninguna supera a la referencia. La pendiente sola es la que menos empeora (+0.0002 t/ha en A), una diferencia sin importancia práctica. El área no añade nada sobre el relieve (combinación 5 frente a 4) y comparar cada parcela con su municipio tampoco (combinación 6 frente a 5).

**¿Qué combinaciones están centradas y cuál se usará en las comparaciones nuevas?**
Sólo la 6 está centrada: a cada variable se le resta el promedio de su municipio, calculado con el entrenamiento. Así la variable deja de decir «esta parcela está en un municipio alto» (eso ya lo sabe la referencia) y pasa a decir «esta parcela está más alta que las de su municipio». Las combinaciones 1 a 5 no están centradas, y una parte de lo que aprenden puede ser volver a contar diferencias entre municipios. En las comparaciones nuevas de T15, relieve y área entrarán centrados con el procedimiento común de T15 (v3), no con el código de T10. La combinación 6 es un antecedente parecido, pero no idéntico: el procedimiento de T15 excluye a la propia parcela al calcular el promedio, usa el promedio del grupo antes que el global cuando falta el municipio, no usa término constante y prueba otra rejilla de penalización. Se eligió centrar por la pregunta que se quiere responder, no por el error. Detalle en la sección 15 del método y en `D_T10_004`.

**¿Cambia en parcelas pequeñas?**
Hay una pista, no un resultado. Las parcelas de menos de 2 ha son las de mayor error con cualquier procedimiento (0.388 t/ha) y ahí las variables lo bajan un poco (0.378); en las de más de 5 ha lo suben (0.318 → 0.326). Son grupos pequeños y no se probó formalmente. Queda como hipótesis para T15.

**¿Y en las parcelas con cobertura parcial de relieve?**
No se puede concluir: hay 5 parcelas etiquetadas con cobertura parcial (tabla más abajo), en el análisis principal quedan 4 (Calpulalpan y Emiliano Zapata) y la referencia casi no se equivoca con ellas porque comparten etiqueta con sus vecinas. Con 4 casos, cualquier diferencia entre procedimientos es anecdótica.

**¿El relieve no es sólo «dónde está la parcela»?**
En parte. El municipio explica el 28 % de la variación de la elevación, el 13 % de la pendiente y el 15 % del área (en logaritmo). La correlación global de la elevación con el rendimiento (+0.29) baja a la mitad (+0.16) al comparar cada parcela con su municipio: buena parte era ubicación, y eso ya lo captura la referencia.

**¿Por qué la correlación existe pero no ayuda a predecir?**
Porque es pequeña (explica cerca del 6 % de lo que queda después del municipio) y se concentra en un municipio. Varias explicaciones son compatibles con los datos, y no probamos cuál pesa más: (a) la empujan pocas parcelas con errores grandes; (b) estas dos variables se señalaron en la exploración inicial por ser de las más altas entre 269 resúmenes, lo que puede inflar su correlación (esa exploración se reporta desde el contexto local del equipo y no se reproduce en el repositorio); (c) estimar una relación así con unas 110 parcelas de entrenamiento por ronda deja mucho ruido en el coeficiente.

**¿Qué pasa con las 59 parcelas reservadas?**
Tienen las tres variables completas; tres quedan apenas fuera del rango de las etiquetadas (AGC_088 en elevación, AGC_153 en pendiente y AGC_091 en área, por muy poco). Como el procedimiento elige «referencia sola», sus predicciones son las mismas que las de T08.

**¿El área podría ser un error de medición (pendiente P06)?**
No hay señal de eso, pero tampoco se descarta. En los contornos B o C el error baja con relieve y área, pero baja igual con relieve solo, que no usa el área; con 13 parcelas no se puede decir más. Sigue sin confirmarse que el área declarada sea la superficie con la que se calculó el rendimiento.

**¿Cambiaría algo si FIRA eligiera el RMSE como métrica?**
Con las predicciones actuales tampoco se alcanza el umbral. Con los papeles de MAE y RMSE intercambiados (T03 §4), el principal baja el RMSE como máximo 0.0052 t/ha en A, por debajo de 0.01. Sólo el puente llega a −0.0108 en una combinación, y el puente no es elegible. Matiz: no se volvió a correr el procedimiento eligiendo el ajuste con error cuadrático, así que esto no descarta que con RMSE como métrica primaria saliera algo distinto.

**¿Qué aprendimos del procedimiento?**
Que, con relieve y área, el procedimiento principal (opción «referencia sola» y ajuste elegido con error absoluto) queda mejor que el de T11 en las 12 comparaciones, y que eligió «referencia sola» en las 59 predicciones. No separa qué parte se debe a la opción y cuál al criterio. Es una pista para T11 y T15, no una prueba de que convenga cambiar T11.

## Las 5 parcelas con cobertura parcial de relieve

Son las etiquetadas con aviso `cobertura_parcial` en `registro/t07/calidad_relieve.csv`. Error = valor absoluto de (predicción − real), promedio de las 5 repeticiones. «Principal» es la combinación 5 (relieve + área) del procedimiento principal; «puente» es la misma combinación con el procedimiento de T11.

| Parcela | Municipio | Real (t/ha) | Cobertura válida elevación / pendiente | Pendiente usada | Fuente de la referencia | Error referencia A / B | Error principal A / B | Error puente A / B |
|---|---|---|---|---|---|---|---|---|
| AGC_020 | Emiliano Zapata | 3.5 | 98 % / 65 % | medida | municipio | 0.000 / 0.000 | 0.058 / 0.028 | 0.163 / 0.156 |
| AGC_023 | Calpulalpan | 3.0 | 96 % / 29 % | **imputada** (mediana del entrenamiento) | municipio | 0.029 / 0.016 | 0.042 / 0.028 | 0.107 / 0.113 |
| AGC_044 | Emiliano Zapata | 3.5 | 100 % / 98 % | medida | municipio | 0.000 / 0.000 | 0.002 / 0.003 | 0.040 / 0.017 |
| AGC_164 | Apan | 3.0 | 95 % / 55 % | medida | **grupo** | 0.026 / 0.035 | 0.071 / 0.032 | 0.127 / 0.166 |
| AGC_170 | Calpulalpan | 3.0 | 76 % / 2 % | **imputada** (mediana del entrenamiento) | municipio | 0.017 / 0.016 | 0.055 / 0.029 | 0.125 / 0.118 |

- AGC_164 (Apan) está en el subconjunto `todas`, pero no en `sin_respaldo`: es la única parcela etiquetada de su municipio, así que su referencia sale del grupo y no de vecinas del municipio (D019). Por eso en el análisis que decide quedan 4 de las 5.
- Las cuatro restantes comparten la etiqueta de sus vecinas (3.5 y 3.0 t/ha), y por eso la referencia casi no falla.
- La referencia tiene el menor error en 9 de los 10 casos (parcela × escenario); la única excepción es AGC_164 en B, donde el principal queda 0.003 t/ha mejor, diferencia sin importancia. El principal elige «referencia sola» en parte de las rondas y un ajuste muy suavizado en el resto; el puente es el que más se aparta.
- Ninguna de estas cinco está entre las 59 reservadas (esas tienen las tres variables completas).

## Límites

- Una sola campaña etiquetada: el resultado no dice nada sobre otros años.
- Relieve a 120 m: muchas parcelas son más pequeñas que una celda, así que el dato es del entorno más que de la parcela.
- Edición del relieve sin confirmar (P05) y área sin confirmar como denominador (P06).
- El diseño no fue ciego: lo ya visto quedó declarado antes de correr.
- Sólo se probó un tipo de modelo (lineal sobre el residuo). Un modelo no lineal es tarea de T12.

## Para otros frentes

- **T15 (combinaciones):** relieve y área no se justifican como bloque. Si se incluyen, deberían demostrar aporte junto con otros bloques; la pista de parcelas pequeñas es la única hipótesis concreta. Entran **centrados por municipio** con el procedimiento común v3 (bloque G), no con la combinación 6 de T10 (`D_T10_004`).
- **T11 (satélite):** con relieve y área, el procedimiento principal de T10 supera al de T11. Con las variables de satélite no se probó; adoptar el principal en T11 es una propuesta para Daf y Dani, no una conclusión.
- **T16 y T17 (cierre y app):** las predicciones de T10 para las 59 son las de la referencia (ver ficha de consumo más abajo). Para la app sirve el dato de las tres reservadas apenas fuera de rango.
- **T19 (informe):** este documento y la figura `figuras/dispersion_relieve_area_rendimiento.png` se pueden usar tal cual, aclarando que la figura es exploratoria.

## Ficha de consumo para T16 (y la app)

- **Archivo:** `registro/t10/predicciones_59_t10.csv` (767 filas = 59 parcelas × 13 combinaciones: la referencia más 6 combinaciones × 2 procedimientos).
- **Qué usar:** las filas con `procedimiento == "referencia"` y `config == 0` (59 filas). Son idénticas a las de T08, que es lo que decide T10.
- **Qué no usar:** las filas de `puente_t11`. Son descriptivas, nunca decidieron nada y empeoran el error en validación.
- **Filas `t10` con `config` 1 a 6:** en las 6 combinaciones el procedimiento eligió «referencia sola» (`opcion`), por lo que repiten la referencia. Se publican sólo para auditar.
- **Los 59 IDs:** son las parcelas reservadas sin rendimiento; el `ID_POLIGONO` va en la columna `ID_POLIGONO`.
- **Pendiente para T17:** AGC_088 (elevación), AGC_153 (pendiente) y AGC_091 (área) quedan fuera del rango de las etiquetadas. La referencia finalmente elegida no usa estas variables; esto no garantiza el comportamiento de un modelo futuro. Casos, alcance y criterios de aceptación en [la ficha de seguimiento](../../docs/T10_seguimiento_T17.md).
- **Estas predicciones se ajustaron con las 138 etiquetadas;** no hay forma de evaluarlas hasta que FIRA publique los valores reales.

## Dónde está todo

| Qué | Dónde |
|---|---|
| Método y diseño | `docs/T10_relieve_area.md`, `D_T10_001` (diseño) y `D_T10_004` (centrado, posterior a los resultados) |
| Código y pruebas | `scripts/t10_relieve_area.py`, `tests/test_t10_relieve_area.py` |
| Resultados | `registro/t10/` (manifiesto con huellas) |
| Experimentos | `E_T10_001`–`E_T10_006` en `registro/experimentos.csv` |
| Exploración con rendimientos | `scripts/`, `tablas/` y `figuras/` de esta carpeta |
| Bitácora | `bitacora.md` |
