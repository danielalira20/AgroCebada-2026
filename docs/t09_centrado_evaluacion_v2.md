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

## Resultado
Pendiente de ejecutar después de completar las pruebas ampliadas. No presentar como terminado ni aprobado.
