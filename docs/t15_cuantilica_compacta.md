# T15: cuantílica compacta municipal y satelital

## Problema que resuelve

La corrección Ridge anterior minimiza error cuadrático. Cambiar su referencia por una mediana no produce una regresión de mediana conjunta. La mediana municipal sola ya fue probada: MAE 0.312585 frente a 0.320490, mejora insuficiente bajo T03. Este experimento separa ese cambio conocido del aporte real del satélite.

## Solución que implementa

Una regresión del cuantil 0.5, con un intercepto libre por municipio y cinco pendientes satelitales comunes penalizadas L1. Se ajustan conjuntamente. Las variables se escalan y centran por municipio usando exclusivamente el entrenamiento. Ese mismo centro se aplica a la consulta. Así la corrección satelital tiene media cero en cada municipio de entrenamiento; no se exige media cero al residuo ni a las consultas. H3 no se corrige restando predicciones antiguas.

No se usa el mecanismo LOO de Ridge: en este modelo conjunto cada respuesta entrena su intercepto como en una regresión supervisada ordinaria. La evaluación externa y la selección interna mantienen separadas sus etiquetas. Un municipio con una sola observación tiene variables centradas cero y no aporta información a las pendientes. Para municipios ausentes se conserva un respaldo puro de mediana de grupo/global, sin extrapolar la corrección satelital.

El contrato JSON fija antes de nuevos OOF dos ventanas, alpha 0.001/0.01/0.1/1 y mediana sola dentro de la selección. Alpha multiplica L1 en pérdida pinball media; no es lambda ni n*lambda de Ridge. Los interceptos municipales no se penalizan. Una solución múltiple se fija minimizando lexicográficamente las cinco pendientes dentro de la cara óptima; después, cada intercepto toma la mediana central de los residuos. Este último paso evita un extremo arbitrario cuando hay un número par de observaciones.

El estimador usa programación lineal HiGHS-ds. Un auditor con otra formulación primal y un certificado dual comprueba sus cálculos. Las tolerancias LP se fijan en el contrato; la reproducción de predicciones desde estados y los comparadores históricos mantienen 1e-12. No se exige igualdad de bytes de las bases internas del optimizador.

## Evaluación y límites

Se conservan T03, A/B y las cuatro particiones internas. Sólo decide A/sin_respaldo: mejora MAE de al menos 0.01 t/ha, IC95 espacial superior menor que cero, mejora en al menos cuatro repeticiones y aumento RMSE no mayor que 0.01. B, las 138 completas y el desglose sin 24 parcelas son sensibilidades, nunca una forma de escoger el ganador. RMSE y R² se reportan por repetición; MAE da igual peso a cada parcela.

Comparadores: media municipal histórica, mediana municipal histórica y S Ridge v3. Las tres conservan su identidad y versiones. La única alternativa nueva promovible es la cuantílica S frente a la media histórica. Si el selector elige sólo mediana, se declarará expresamente. Este trabajo es exploratorio después de varias evaluaciones: no garantiza mejora ni generalización a otro año. No produce predicciones finales de las 59, no congela T16 y no publica cambios.

## Referencias

- SciPy, [linprog HiGHS dual simplex](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs-ds.html).
- scikit-learn, [QuantileRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html): confirma pérdida pinball y penalización L1; se necesita formulación propia para eximir interceptos municipales.
- Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065). Se aplicaron las skills scikit-learn y pensamiento crítico científico.


## Resultado completo y auditado · 17 de octubre de 2026

Se ejecutó el contrato 79ea3ffd en la rama `t15-cuantilica-compacta`. La corrida válida usa el código 1c0071f, después de corregir y registrar el incidente numérico descrito abajo. La fuente canónica es Linux/amd64, imagen común b2dea1bd, sin red, repositorio en lectura, 768 MiB y dos CPU. Se repitió completa en Mac/ARM y se conciliaron las 50 selecciones y los 1,850 estados. No se cambiaron ventanas, alpha, columnas, poblaciones ni reglas tras obtener resultados.

### Principal A, municipio con apoyo en el entrenamiento

| Procedimiento | Parcelas / OOF | MAE por parcela | RMSE medio por repetición | R² medio por repetición |
|---|---:|---:|---:|---:|
| Media municipal (referencia) | 135 / 675 | 0.320489710 | 0.492593095 | 0.658576745 |
| Mediana municipal sola | 135 / 675 | 0.312585185 | 0.490682747 | 0.661222527 |
| Cuantílica compacta S | 135 / 675 | 0.312538185 | 0.490174361 | 0.661921196 |
| S Ridge v3 | 135 / 675 | 0.321669551 | 0.490676981 | 0.661211591 |

La reducción observada frente a media es **0.007951525 t/ha** (aproximadamente 2.48 %, unos 8 kg/ha de reducción del error absoluto medio). El IC95 por 22 celdas es **[-0.016704073, 0.005467330]**. Mejora en 5/5 repeticiones y no empeora RMSE, pero **falla el mínimo de 0.01 y el intervalo incluye cero**. Por tanto, no cumple la promoción T03 y la referencia continúa siendo la media municipal.

La reducción adicional frente a **mediana sola** es apenas **0.000047000 t/ha**, unos 0.047 kg/ha. IC95 [-0.000886646, 0.000672000]; sólo una repetición mejora, una empeora y tres empatan. No hay evidencia de aporte relevante del satélite en esta formulación.

El selector elige explícitamente mediana sola en 21/25 contextos A. En otros dos selecciona una opción penalizada que termina con beta cero en el ajuste externo: **23/25 predicen como mediana sola**, y únicamente dos conservan pendientes satelitales activas. Por parcela, frente a mediana: 21 mejoran, 24 empeoran y 90 empatan (tolerancia de igualdad 1e-12). Los interceptos de un ajuste activo se estiman conjuntamente con sus pendientes; no son corrimientos municipales añadidos después de entrenar.

### Sensibilidad espacial B, mismas reglas de selección interna por celda

| Procedimiento | Parcelas / OOF | MAE por parcela | RMSE medio por repetición | R² medio por repetición |
|---|---:|---:|---:|---:|
| Media municipal (referencia) | 135 / 659 | 0.363187375 | 0.521985168 | 0.610963386 |
| Mediana municipal sola | 135 / 659 | 0.347481481 | 0.516424493 | 0.619179979 |
| Cuantílica compacta S | 135 / 659 | 0.352685926 | 0.516665190 | 0.618843535 |
| S Ridge v3 | 135 / 659 | 0.351920870 | 0.510406082 | 0.628092023 |

Hay 135 IDs elegibles al menos una vez y 659 predicciones elegibles; no todas las parcelas aportan cinco repeticiones. MAE por ID da el mismo peso a cada parcela. No sustituirlo por el MAE agrupado por registros ni por la media de repeticiones. Aquí la cuantílica empeora la mediana sola en aproximadamente 0.005204 t/ha; IC95 [0.000580, 0.009611]. Usa pendientes activas en 17/25 contextos, pero ello no proporciona mejora de MAE. B es sensibilidad y nunca selecciona el ganador.

### Las 138 completas: otro denominador, no el principal

| Procedimiento | Parcelas / OOF | MAE por parcela | RMSE medio por repetición | R² medio por repetición |
|---|---:|---:|---:|---:|
| Media municipal (referencia) | 138 / 690 | 0.319249800 | 0.489825740 | 0.666382384 |
| Mediana municipal sola | 138 / 690 | 0.309702899 | 0.487195950 | 0.669958848 |
| Cuantílica compacta S | 138 / 690 | 0.309656920 | 0.486695068 | 0.670634269 |
| S Ridge v3 | 138 / 690 | 0.320425278 | 0.487942733 | 0.668927939 |

Las 59 sin rendimiento no participan en ajuste ni evaluación. Las 1,380 predicciones nuevas proceden de A/B y cinco repeticiones de las mismas 138 etiquetas; no son 1,380 muestras independientes ni predicciones finales de las 59.

### Calidad y errores grandes

Se entregan 248 desgloses (municipio, grupo de registro, vecina cercana, contorno y sensibilidad sin24) y 80 métricas por repetición. Sin24 sólo cambia el resumen: **todas las parcelas permanecen en sus entrenamientos**. En A/sin_respaldo/sin24 el MAE es aproximadamente 0.320042 frente a 0.324622 de media y 0.320333 de mediana; la ventaja frente a media se reduce a unos 0.004580 t/ha. Esa revisión no autoriza excluir casos ni constituye un procedimiento nuevo.

Las predicciones evaluadas son finitas y no negativas: A rango aproximado 2.969–4.654; B 2.500–4.700 t/ha. No se aplicó recorte posterior. Esto no acredita automáticamente las 59 reservadas ni otro año.

## Comprobaciones y problema resuelto

- 18 pruebas del estimador/integración y 3 adicionales de tablas por entorno; guardias probadas con `-O`. Mac también se comprobó sin optimización.
- Dos pilotos A/B: 74 ajustes y 62 predicciones por entorno, auditados antes de la corrida completa.
- Estrés numérico adicional en Mac: 2,000 ajustes cubren todas las opciones en entrenamientos internos y externos, sin calcular MAE de evaluación ni seleccionar por resultados.
- Corrida válida: **1,800 ajustes internos + 50 externos**, 50 selecciones, 1,850 estados completos, 1,380 OOF nuevas y 4,140 OOF históricas reutilizadas con sus versiones originales. De los 1,850 ajustes, 1,621 son LP penalizados y 229 referencias de mediana.
- Auditor separado con formulación primal distinta, certificado dual y reconstrucción de preparación, medianas, H3, selección, OOF, métricas, IC5000 y regla: **218,182 comprobaciones por entorno**. Máxima diferencia Mac de reconstrucción 8.58e-11; Linux 3.84e-11, dentro de las tolerancias registradas para cada cálculo.
- Comprobación adicional de 3,568 cantidades de las tablas y sus 248 desgloses, frecuencias e incrementales; máximo 1.33e-15. Los R² indefinidos quedan vacíos, sin asignarles cero artificial.
- Reproducción Mac/Linux: diferencia máxima OOF 5.53e-12 t/ha; mismas 50 selecciones. Corrección media por municipio de entrenamiento, A máximo 6.07e-17 t/ha y B 4.39e-17. No se usa la consulta para centrar.
- Paquete comprimido revalidado sin reentrenar: 213,319 comprobaciones de integridad, estados, predicciones y reportes. Gzip corrupto y OOF alterada se rechazan. Se comprobó además respaldo global sin corrección y que introducir una columna de rendimiento en la consulta no afecta la predicción.

**Incidente numérico.** El primer intento Mac se detuvo en A/rep3/fold0/interna2, al fijar como igualdades dos pendientes compatibles con cero a la precisión del optimizador (1.69e-11 y 4.30e-11). Ese encadenamiento de desempates produjo una cara declarada inviable. Se diagnosticó que desactivar presolve o reescalar el objetivo no lo resolvía. Se canonicalizan esos ceros usando **1e-9, la tolerancia ya existente del solver**. No se amplía la tolerancia, no se cambia el objetivo, no se elige otra alpha por sus métricas. El certificado independiente comprueba el óptimo final. Una prueba conserva el caso exacto.

Se preservó el intento interrumpido Mac (396 ajustes, diez contextos completos y 276 OOF parciales), separado de esta entrega válida. El primer Docker se detuvo expresamente antes de ajustar (salida 137); no fue falta de memoria. Se regeneraron pruebas, pilotos, puerta y ambas evaluaciones completas con el código corregido en carpetas nuevas. Un error inicial del propio test aplicaba `abs` a una lista; se corrigió su conversión numérica antes de los pilotos. Ninguno de estos incidentes se usó para retocar el menú o filtrar parcelas.

## Dónde revisar y reproducir

- Contrato previo: `registro/t15_cuantilica_contrato_v1.json`, commit 550c591.
- Estimador: `scripts/t15_cuantilica_modelo.py`; runner: `scripts/t15_cuantilica_ejecutar.py`.
- Auditor numérico: `scripts/t15_cuantilica_auditar.py`; verificador adicional: `scripts/t15_cuantilica_verificar_tablas.py`.
- Datos, trazas comprimidas sin pérdida y reportes canónicos: `registro/t15_cuantilica/resultados/`.
- `registro/t15_cuantilica/entrega.json` enlaza huellas, procedencia y comprobaciones; `comparacion_por_parcela.csv` y `perfiles_contextos.csv` permiten seguir cada cambio frente a media/mediana.

Desde la raíz del repositorio con el entorno acordado:

```sh
python -O -m unittest tests.test_t15_cuantilica tests.test_t15_cuantilica_tablas -v
python -O -m scripts.t15_cuantilica_auditar --raiz . --entrada registro/t15_cuantilica/resultados --salida reports/auditoria_cuantilica_nueva.json
python -O -m scripts.t15_cuantilica_verificar_tablas --raiz . --entrada registro/t15_cuantilica/resultados --salida reports/auditoria_cuantilica_tablas_nueva.json
```

Para reproducir todos los ajustes en un destino **nuevo** y con rama limpia:

```sh
python -O -m scripts.t15_cuantilica_ejecutar --modo completa --confirmar-completa --puerta registro/t15_cuantilica/verificacion_previa/puerta.json --salida reports/cuantilica_reproduccion_nueva
```

La puerta conserva pruebas y pilotos vinculados por huellas. Si cambia código/fuente, se debe repetir la verificación previa, no modificar las huellas para eludirla. Docker se utiliza temporalmente; apagar Colima al terminar si no hay otro trabajo en curso.

El manifiesto original de ejecución conserva `completa_pendiente_auditoria`, emitido antes del auditor separado. Se preserva como evidencia original: el cierre posterior está en `entrega.json` y las dos auditorías aprobadas. Tampoco se habilita por edición el contrato histórico T15: la autorización específica de este experimento está en su contrato propio y su puerta verificada.

## Decisión y siguiente alternativa

Se cierra esta comparación como **evaluada, sin promoción**, sin modificar las evaluaciones previas ni T16. El cambio útil de diseño fue ajustar conjuntamente la mediana y el componente municipal con una verificación explícita de soluciones múltiples. Su desempeño observado casi reproduce una alternativa que ya teníamos; no demuestra una ganancia nueva relevante. No se recomienda ampliar la rejilla después de mirar este resultado.

Siguiente alternativa acotada: armonizar una familia ya existente de T13 con el procedimiento común antes de atribuirle una mejora; si se incorpora información externa, requerirá su propio piloto de cobertura y procedencia (por ejemplo suelo). La aplicabilidad final a las 59 y el ajuste/exportación T16 siguen pendientes. No se publica, fusiona ni comunica al equipo con esta autorización. La evidencia procede de una campaña y varias exploraciones previas; no acredita desempeño futuro.
