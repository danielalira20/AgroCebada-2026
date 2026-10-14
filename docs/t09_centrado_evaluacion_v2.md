# Reevaluación T09 R centrado v2 · pasos 3 y 4

## Problema que resuelve
R-v1 podía añadir una componente entre municipios al predecir. Esta revisión hace explícita la corrección dentro del municipio y vuelve a seleccionar sus parámetros. No atribuye causalidad al clima ni promete una mejora del error.

## Solución y registro anterior a ejecución
El diseño de pasos 1–2 permanece como registro histórico inmutable. La autorización posterior de Dani y el presupuesto están en `registro/t09/registro_R_centrado_v2.json`; ID `T09_R_centrado_v2`. Es una revisión posterior a los resultados v1, no un experimento ciego ni una confirmación con datos nuevos. Revisión humana de Migue pendiente.

Se preservan las 138 etiquetas, las 59 reservadas, todas las fuentes T07 y las particiones T03. Se buscan sólo abr_oct/jun_oct por cuatro lambda: 0.01, 0.1, 1, 10. Cada uno de 59 contextos A/B/C utiliza cuatro particiones internas; se rehacen LOO, escala global y centros municipales dentro de cada fit. alpha=n*lambda, sin intercepto ni segunda escala. Los municipios ausentes usan centros de grupo/global aprendidos con entrenamiento.

Presupuesto: 1,888 ajustes internos y 118 reajustes externos únicos, 2,006 Ridge por ejecución, más 59 referencias T. El modelo seleccionado se reutiliza en el diagnóstico de su ventana fija. No se añade referencia sola a esta búsqueda: cambiaría el diseño registrado y corresponde a un procedimiento posterior.

## Comparaciones fijadas
R_centrado seleccionado frente a T, R-v1 y TC-v1. Las dos ventanas fijas frente a T, con lambda elegida internamente. Se reutilizan los históricos compartidos v1 con sus huellas/versiones originales y se recalcula T para confirmar identidad exacta T08. No se reentrenan R-v1/TC-v1 ni se elige ventana usando error externo.

MAE, RMSE, sesgo y R² por repetición y después resumen. Diferencia de MAE emparejada por parcela tras promediar sus repeticiones elegibles; población común T08 sin respaldo. Intervalo por 5,000 remuestreos de celdas, semilla 20261006. Regla heredada sólo para R_centrado vs T, A/sin_respaldo: ΔMAE<=-0.01, IC superior<0, mejora en >=4/5 repeticiones y ΔRMSE<=0.01. Intervalos nominales, sin corrección conjunta por experimentos repetidos; el resultado no constituye evidencia independiente. C es transferencia descriptiva.

## Controles
Pruebas de aislamiento de etiquetas externas y lotes nuevos, todas las particiones, respaldos, unidades, fallo de fit y guardias de diseño/históricos/salidas. Reconstrucción NumPy independiente de todos los ajustes internos y externos, parámetros seleccionados, centros, coeficientes, OOF y reportes. Dos ejecuciones en Docker común; conservar originales. No ajustar las 59 ni cambiar T03/T15 o código de colegas. No publicar sin autorización nueva.

Aplicadas las skills privadas scikit-learn y scientific-critical-thinking: aislamiento de entrenamiento, dependencia espacial y cautela con inferencias posteriores a resultados. Referencia de la metodología de skills: [Scientific Agent Skills](https://doi.org/10.48550/arXiv.2609.00065).

## Resultado canónico · 13 de octubre de 2026

Pasos 3 y 4 verificados técnicamente. Revisión humana de Migue pendiente. No se publica, fusiona ni ejecuta T15 con esta entrega. El diseño/implementación de pasos 1–2 conservan su estado histórico; el estado de esta nueva ejecución está en `registro/t09/centrado_v2/verificacion.json`.

La corrección municipal de H3 queda implementada y comprobada en R_centrado. No supera a T en MAE ni cumple la regla de promoción. R-v1 permanece identificado como histórico: no se borran ni se reinterpretan sus predicciones como centradas.

| MAE, t/ha | T: referencia municipal | R-v1: anterior | R_centrado: nuevo | TC-v1: ya centrado |
|---|---:|---:|---:|---:|
| A, población principal | 0.320490 | 0.321987 | 0.321691 | 0.321623 |
| B, sensibilidad espacial | 0.357867 | 0.363272 | 0.371470 | 0.371038 |
| C, municipios ausentes | 0.695923 | 0.666509 | 0.702455 | 0.702730 |

A/B usan la población común cuya referencia T08 tiene soporte municipal (sin respaldo de grupo/global). Los MAE de la tabla son promedios por repetición. La regla utiliza diferencias emparejadas por parcela: en A, ΔMAE frente a T = +0.0012013546513, IC95 por celdas [-0.001533, +0.005159], mejora sólo en 2/5 repeticiones y ΔRMSE=-0.0009267172621. Falla la mejora mínima -0.01, el intervalo superior<0 y 4/5 repeticiones. El pequeño descenso en RMSE no cambia la decisión basada en MAE.

En B, ΔMAE por parcela frente a T=+0.013186 y frente a R-v1=+0.006711. No coinciden exactamente con restar los MAE de la tabla porque varía la población elegible entre repeticiones. C es descriptivo: no decide ganador ni acredita funcionamiento en una campaña futura.

La diferencia respecto a R-v1 en A es sólo -0.000296 t/ha; el intervalo nominal incluye cero. En B y C el MAE aumenta respecto a R-v1. Una corrección metodológica no garantiza mejor puntuación. La comparación preliminar manteniendo los parámetros anteriores no era esta evaluación: aquí se volvieron a elegir parámetros internamente; cambió la configuración en 10/25 contextos A, 12/25 B y 9/9 C. No se reajustó la búsqueda mirando OOF.

## Qué aprendió y cuánto actuó el clima

En A se eligió lambda=1 en 7 contextos y lambda=10 en 18: abr_oct en 15 y jun_oct en 10. La corrección absoluta media es 0.014077 t/ha (máxima 0.172937), frente a un MAE cercano a 0.32. Sigue siendo una contribución pequeña. En B se eligieron cuatro lambda=1, dieciséis lambda=10 y cinco lambda=0.01; estos últimos con jun_oct. En C: dos lambda=0.01, tres lambda=1 y cuatro lambda=10. No añadir nuevos parámetros después de conocer estas cifras.

El máximo de la media de corrección por municipio de entrenamiento fue 4.3021e-17 t/ha. No se obliga a que esa media sea cero en evaluación: un lote nuevo puede desviarse legítimamente del centro aprendido. Para municipios ausentes, el centro de grupo/global es un respaldo estimado con entrenamiento, no una media observada del municipio nuevo.

Este resultado respalda únicamente que este procedimiento y estas entradas climáticas no aportaron la mejora exigida. No demuestra que todo producto climático o toda campaña carezca de información útil. Hay una sola campaña etiquetada (2025); las mediciones de años anteriores no son nuevas etiquetas.

## Evidencia y controles

- 79 pruebas distintas cubiertas por entorno: suite completa Mac; 76 base Docker más las regresiones nuevas incluidas en sus 21 pruebas finales con Python optimizado. No se desactivan controles al ejecutar con -O.
- Dos ejecuciones canónicas Linux/amd64 con la imagen fijada: 12 archivos idénticos byte a byte. Selecciones, máscaras y contextos coinciden con Mac; diferencia máxima en CSV1.9540e-14 y estados4.7795e-14, dentro de tolerancias1e-9/1e-10 sin ampliarlas.
- Auditor independiente: NumPy, sin importar estimadores ni el evaluador de producción. Reconstruye1,888 ajustes internos,118 externos,6,072 predicciones nuevas+referencia (4,554 de R_centrado y1,518 de T), centros, coeficientes,472 puntuaciones internas y las opciones elegidas. Scikit-learn sólo genera las particiones fijadas.
- Reconstrucción independiente de168 métricas por repetición,40 resúmenes,25 contrastes y3,420 diferencias por parcela. Comprueba denominadores e intervalos por celdas. También se conservan exactamente3,036 filas R/TC-v1.
- Siete alteraciones deliberadas en copias temporales fueron rechazadas: huella, centro, parámetro elegido, MAE interno, celda vacía, etiqueta e intervalo. No se alteraron datos oficiales.
- 1,380 referencias A/B reproducen exactamente T08. Las387 fuentes/archivos históricos protegidos permanecen intactos. Las59 reservadas no entran en entrenamiento, selección ni evaluación; no hay ajuste final T18.

## Incidencias y solución

1. El nuevo adaptador comparaba Series.equals y exigía igual tipo interno para fuente. Los textos object y str coincidían exactamente, pero el control rechazó la unión al terminar los59 contextos. La guardia impidió crear una entrega. Se detuvo la segunda reproducción incompleta, se conservaron logs y se corrigió la comparación exacta por ID/valores. La regresión rechaza cambios de fuente, máscaras de texto y hasta un bit diferente de predicción. No se relajaron tolerancias ni se cambió la fórmula.
2. El auditor nuevo suponía que celda_chirps estaba en T07. Su fuente congelada es T03. Se corrigió la unión por ID, verificando138 IDs/690 particiones y la celda constante entre repeticiones. Se añadió una regresión y se aprobaron las auditorías completas Mac y Docker. No cambian datos ni modelos.

Las ejecuciones fallida/interrumpida no se presentan como resultados acreditados. Tras las correcciones hay una ejecución Mac de control y dos Docker canónicas idénticas. La búsqueda permanece registrada y fija; no hubo selección adicional a partir de los errores externos.

## Archivos y reproducción

La entrega completa está en `registro/t09/centrado_v2/`: OOF, selección/puntuaciones internas, coeficientes, estados con centros e IDs, contextos, métricas, contrastes, diferencias por parcela, manifiesto, resultado y auditorías. En las filas históricas, fuente_centrado vacía significa «no aplicable a esa versión», no cero ni dato imputado. version/candidato conservan el origen v1 o v2. Los diagnósticos abr_oct/jun_oct no son experimentos extra ni una ventana elegida externamente.

Dentro del entorno común, con los mismos insumos locales:

```bash
python -m scripts.t09_centrado_evaluar --salida reports/t09_centrado/ejecuciones/nueva
python -m scripts.t09_centrado_verificar --resultados registro/t09/centrado_v2 --salida reports/t09_centrado/auditoria_publicada.json
```

El ejecutor exige una salida nueva y verifica huellas antes de calcular. El auditor rechaza modificaciones de fuentes/código/diseño/resultados. Las huellas de producción en procedencia.json permiten ligar el reporte a su código exacto.

## Qué queda pendiente

Migue debe revisar la nueva versión y su conclusión. Después: auditar las variantes de T10/T11/T14 y versionar el procedimiento común para T15 con los acuerdos pendientes; no asumir que esta validación acredita esas tareas. La referencia sola ya prevista en el procedimiento común es una alternativa explícita para un bloque que no ayuda, pero no se añadió retrospectivamente al experimento T09.

No se ejecutó T15, no se modificó código de colegas/protocolo T03/GoogleDoc, no se eligió ganador T16 ni se generaron59 predicciones finales. La publicación requiere un lote explicado y autorización nueva de Dani.
