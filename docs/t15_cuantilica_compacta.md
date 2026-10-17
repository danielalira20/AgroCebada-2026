# T15: cuantílica compacta municipal y satelital

## Problema que resuelve

La corrección Ridge anterior minimiza error cuadrático. Cambiar su referencia por una mediana no produce una regresión de mediana conjunta. La mediana municipal sola ya fue probada: MAE 0.312585 frente a 0.320490, mejora insuficiente bajo T03. Este experimento separa ese cambio conocido del aporte real del satélite.

## Solución que implementa

Una regresión del cuantil 0.5, con un intercepto libre por municipio y cinco pendientes satelitales comunes penalizadas L1. Se ajustan conjuntamente. Las variables se escalan y centran por municipio usando exclusivamente el entrenamiento. Ese mismo centro se aplica a la consulta. Así la corrección satelital tiene media cero en cada municipio de entrenamiento; no se exige media cero al residuo ni a las consultas. H3 no se corrige restando predicciones antiguas.

No se usa el mecanismo LOO de Ridge: en este modelo conjunto cada respuesta entrena su intercepto como en una regresión supervisada ordinaria. La evaluación externa y la selección interna mantienen separadas sus etiquetas. Un municipio con una sola observación tiene variables centradas cero y no aporta información a las pendientes. Para municipios ausentes se conserva un respaldo puro de mediana de grupo/global, sin extrapolar la corrección satelital.

El contrato JSON fija antes de nuevos OOF dos ventanas, alpha 0.001/0.01/0.1/1 y mediana sola dentro de la selección. Alpha multiplica L1 en pérdida pinball media; no es lambda ni n*lambda de Ridge. Los interceptos municipales no se penalizan. Una solución múltiple se fija minimizando lexicográficamente las cinco pendientes dentro de la cara óptima; después, cada intercepto toma la mediana central de los residuos. Este último paso evita un extremo arbitrario cuando hay un número par de observaciones.

El estimador usa programación lineal HiGHS-ds. Un auditor con otra formulación primal y un certificado dual comprobará sus cálculos. Las tolerancias LP se fijan en el contrato; la reproducción de predicciones desde estados y los comparadores históricos mantienen 1e-12. No se exige igualdad de bytes de las bases internas del optimizador.

## Evaluación y límites

Se conservan T03, A/B y las cuatro particiones internas. Sólo decide A/sin_respaldo: mejora MAE de al menos 0.01 t/ha, IC95 espacial superior menor que cero, mejora en al menos cuatro repeticiones y aumento RMSE no mayor que 0.01. B, las 138 completas y el desglose sin 24 parcelas son sensibilidades, nunca una forma de escoger el ganador. RMSE y R² se reportan por repetición; MAE da igual peso a cada parcela.

Comparadores: media municipal histórica, mediana municipal histórica y S Ridge v3. Las tres conservan su identidad y versiones. La única alternativa nueva promovible es la cuantílica S frente a la media histórica. Si el selector elige sólo mediana, se declarará expresamente. Este trabajo es exploratorio después de varias evaluaciones: no garantiza mejora ni generalización a otro año. No produce predicciones finales de las 59, no congela T16 y no publica cambios.

## Referencias

- SciPy, [linprog HiGHS dual simplex](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs-ds.html).
- scikit-learn, [QuantileRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html): confirma pérdida pinball y penalización L1; se necesita formulación propia para eximir interceptos municipales.
- Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065). Se aplicaron las skills scikit-learn y pensamiento crítico científico.
