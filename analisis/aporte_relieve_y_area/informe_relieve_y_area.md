# Informe de cierre · T10, aporte de relieve y área

- **Responsable:** Jass. **Revisora:** Daf. **Fecha:** 12 de octubre de 2026.
- **Método:** [`docs/T10_relieve_area.md`](../../docs/T10_relieve_area.md) y decisión `D_T10_001`, escritos antes de correr.
- **Resultados:** `registro/t10/`. **Bitácora:** [`bitacora.md`](bitacora.md).

## En una frase

Con las reglas del equipo, **saber la elevación, la pendiente y el tamaño de una parcela no mejora la estimación que da el promedio de su municipio**; se conserva la referencia `media_mun__resp_grupo`.

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
- **El procedimiento lo confirma por su cuenta:** ajustado con las 138 parcelas, elige «referencia sola» en las 6 combinaciones. Sus predicciones para las 59 reservadas son idénticas a las de la referencia.
- **El procedimiento de T11 (puente) sale peor:** su error promedio sube entre 0.010 y 0.020 t/ha en A. El principal le gana en las 12 comparaciones de error promedio.
- **La relación que sí existe es débil y local.** Dentro de cada municipio, la pendiente y el área se asocian con el rendimiento con r ≈ ±0.24, casi todo en Chignahuapan; en Calpulalpan es prácticamente cero. Explica cerca del 6 % de lo que el municipio no explica, y no alcanza para predecir mejor parcelas nuevas.

## Preguntas y respuestas

**¿Relieve y área aportan algo sobre el territorio?**
No con este procedimiento. Ninguna de las 6 combinaciones mejora la referencia según la regla del equipo, ni en A ni en B, ni con ni sin las 24 parcelas con alerta de contorno.

**¿Cuál variable funcionó mejor?**
Ninguna supera a la referencia. La pendiente sola es la que menos empeora (+0.0002 t/ha en A), una diferencia sin importancia práctica. El área no añade nada sobre el relieve (combinación 5 frente a 4) y comparar cada parcela con su municipio tampoco (combinación 6 frente a 5).

**¿Cambia en parcelas pequeñas?**
Hay una pista, no un resultado. Las parcelas de menos de 2 ha son las de mayor error con cualquier procedimiento (0.388 t/ha) y ahí las variables lo bajan un poco (0.378); en las de más de 5 ha lo suben (0.318 → 0.326). Son grupos pequeños y no se probó formalmente. Queda como hipótesis para T15.

**¿Y en las parcelas con cobertura parcial de relieve?**
No se puede concluir: en el análisis principal sólo quedan 4 (Calpulalpan y Emiliano Zapata), y la referencia casi no se equivoca con ellas porque comparten etiqueta con sus vecinas.

**¿El relieve no es sólo «dónde está la parcela»?**
En parte. El municipio explica el 28 % de la variación de la elevación, el 13 % de la pendiente y el 15 % del área (en logaritmo). La correlación global de la elevación con el rendimiento (+0.29) baja a la mitad (+0.16) al comparar cada parcela con su municipio: buena parte era ubicación, y eso ya lo captura la referencia.

**¿Por qué la correlación existe pero no ayuda a predecir?**
Porque es pequeña (explica cerca del 6 % de lo que queda después del municipio), se concentra en un municipio y la empujan pocas parcelas con errores grandes. Además estas dos variables se señalaron en la exploración inicial por ser las más altas entre 269 resúmenes, lo que infla su correlación. Fuera del entrenamiento, estimarla con unas 110 parcelas se come casi toda la ganancia.

**¿Qué pasa con las 59 parcelas reservadas?**
Tienen las tres variables completas; tres quedan apenas fuera del rango de las etiquetadas (AGC_088 en elevación, AGC_153 en pendiente y AGC_091 en área, por muy poco). Como el procedimiento elige «referencia sola», sus predicciones son las mismas que las de T08.

**¿El área podría ser un error de medición (pendiente P06)?**
No hay señal de eso, pero tampoco se descarta. En los contornos B o C el error baja con relieve y área, pero baja igual con relieve solo, que no usa el área; con 13 parcelas no se puede decir más. Sigue sin confirmarse que el área declarada sea la superficie con la que se calculó el rendimiento.

**¿Cambiaría algo si FIRA eligiera el RMSE como métrica?**
No para T10. Con los papeles de MAE y RMSE intercambiados (T03 §4), el principal baja el RMSE como máximo 0.0052 t/ha en A, lejos del umbral de 0.01. Sólo el puente llega a −0.0108 en una combinación, y el puente no es elegible.

**¿Qué aprendimos del procedimiento?**
Que permitir «referencia sola» y elegir el ajuste con error absoluto evita que el modelo meta variables que no ayudan: es mejor que el procedimiento de T11 en las 12 comparaciones. Es evidencia útil para T11 y T15.

## Límites

- Una sola campaña etiquetada: el resultado no dice nada sobre otros años.
- Relieve a 120 m: muchas parcelas son más pequeñas que una celda, así que el dato es del entorno más que de la parcela.
- Edición del relieve sin confirmar (P05) y área sin confirmar como denominador (P06).
- El diseño no fue ciego: lo ya visto quedó declarado antes de correr.
- Sólo se probó un tipo de modelo (lineal sobre el residuo). Un modelo no lineal es tarea de T12.

## Para otros frentes

- **T15 (combinaciones):** relieve y área no se justifican como bloque. Si se incluyen, deberían demostrar aporte junto con otros bloques; la pista de parcelas pequeñas es la única hipótesis concreta.
- **T11 (satélite):** el procedimiento principal de T10 (opción «referencia sola» y α por error absoluto) supera al de T11 en estos datos.
- **T16 y T17 (cierre y app):** las predicciones de T10 para las 59 son las de la referencia. Para la app sirve el dato de las tres reservadas apenas fuera de rango.
- **T19 (informe):** este documento y la figura `figuras/dispersion_relieve_area_rendimiento.png` se pueden usar tal cual, aclarando que la figura es exploratoria.

## Dónde está todo

| Qué | Dónde |
|---|---|
| Método y diseño | `docs/T10_relieve_area.md`, `D_T10_001` |
| Código y pruebas | `scripts/t10_relieve_area.py`, `tests/test_t10_relieve_area.py` |
| Resultados | `registro/t10/` (manifiesto con huellas) |
| Experimentos | `E_T10_001`–`E_T10_006` en `registro/experimentos.csv` |
| Exploración con rendimientos | `scripts/`, `tablas/` y `figuras/` de esta carpeta |
| Bitácora | `bitacora.md` |
