# Procedimiento común centrado v2 · corrección H3

Responsable: Dani. Revisión de T15: Daf; políticas de T03 y cierre T16: Migue. Estado: implementación y controles técnicos preparados para revisión. La evaluación completa de T15 sigue pendiente de conformidad y registro previo.

## Problema que resuelve

El procedimiento común v1 ajustaba Ridge al residuo de la referencia municipal utilizando variables escaladas globalmente. Al predecir, esa misma matriz incluía tanto las diferencias entre parcelas del municipio como las diferencias entre municipios. Por ello la corrección podía añadir un componente municipal encima de una referencia que ya era municipal. No permite interpretar toda la corrección como señal interna del bloque de atributos.

Esto es una corrección de diseño e interpretación, posterior al conocimiento de resultados históricos. No implica que las fuentes estuvieran mal extraídas ni constituye evidencia nueva sobre otra campaña. No se retoca un resultado antiguo ni se describe la nueva versión como experimento ciego.

## Solución que implementa

Se conserva la referencia T08, el residuo LOO, las fuentes T07/T03, los respaldos, ventanas, búsqueda, presupuesto, divisiones y regla de decisión. Se cambia la matriz de Ridge para restar, tanto al ajustar como al predecir, los centros aprendidos exclusivamente con el entrenamiento. Se mantiene la escala global y la ausencia de intercepto.

Identidad: `comun-centrado-v2`. Diseño: [procedimiento_centrado_v2.json](../registro/evaluacion_comun/procedimiento_centrado_v2.json), SHA256 **fb4ba40497b14cc9c9c077a3e993e8d24ca559a2d1cd6ebbce168e12aebd8040**. Antecedente: `comun-v1`, SHA256 `da633adf27c7f1cf2d7760dc2f190abe38d9a912f80a976717fc6213c48f76d3`; sus archivos de diseño, propuesta y evidencia original se conservan por bytes.

Para un entrenamiento concreto:

1. Transformar el área a log natural cuando esté declarada. Rellenar la pendiente D020 con la mediana del entrenamiento y añadir su indicador fijo de ausencia.
2. Ajustar la escala global con ese entrenamiento y obtener `Z`. Se incluye el indicador en el escalado y centrado.
3. Guardar los centros `Z` por municipio y por grupo, y el centro global. Ajustar Ridge a `D = Z − centro_municipio`, sobre residuos LOO calculados sin la propia etiqueta de cada fila.
4. Predecir con la escala y los centros guardados: municipio; si no existe, grupo; si tampoco existe, global. Se conserva la misma cascada de la referencia. No se calcula un centro con el lote que se está prediciendo.
5. Sumar la corrección a la referencia. `alpha = n_entrenamiento × lambda`, con λ en 0.01, 0.1, 1 y 10. No se vuelve a estandarizar la desviación intramunicipal.

Una fila de municipio único tiene `D=0` y sigue contando en `n`; no se elimina ni se inventa información interna. Una variable constante en un municipio no genera una corrección municipal. La media de la corrección dentro de cada municipio **del entrenamiento** debe ser cero, salvo redondeo numérico. La media de la corrección de validación puede ser diferente de cero: no se fuerza ni se utiliza para recalibrar.

Los centros, escala, mediana, coeficientes, conteos, identidad y IDs de entrenamiento quedan en `estado()`. Predecir no cambia ese estado; cambiar parámetros exige reajustar. Un ajuste fallido elimina el estado anterior para impedir utilizarlo accidentalmente. `clone` y la serialización conservan la política.

## Componentes e identidad

- [evaluacion_comun_centrado.py](../scripts/evaluacion_comun_centrado.py): carga protegida, experimento v2, estimador, selección interna y entrada registrada. Todas las divisiones internas aprenden sus propios centros.
- [evaluacion_comun_centrado_auditar.py](../scripts/evaluacion_comun_centrado_auditar.py): reconstrucción NumPy independiente con parámetros fijos, sin MAE externo ni búsqueda de ganadores.
- [test_evaluacion_comun_centrado.py](../tests/test_evaluacion_comun_centrado.py): regresiones H3, imputación e indicador, respaldos, serialización, separación de etiquetas, presupuesto e identidad.

El código histórico de `evaluacion_comun_modelo.py` conserva su comportamiento numérico. Su entrada pública `seleccionar_registrado()` exige ahora `reproduccion_historica=True` para utilizar v1 explícitamente. Las nuevas comparaciones deben llamar a la entrada v2. El validador estructural compartido comprueba roles y presupuesto; por sí solo **no acredita** registro, versión ni aprobación. Cada entrada pública comprueba su esquema y huella.

El verificador de OOF sigue verificando integridad de datos, referencia y claves. Leer un CSV correcto no demuestra cómo fue entrenado. La acreditación metodológica exige además estados, búsqueda interna, código y entorno de la ejecución correspondiente.

## Propuesta T15 pendiente

La [propuesta centrada](../registro/evaluacion_comun/propuesta_t15_centrado_v2.json) conserva ocho procedimientos, 60 opciones con variables y los mismos contrastes. Cambia la identidad de los candidatos a `comun_centrado_v2_*`. **No está registrada como ejecutable**: el contrato la rechaza mientras tenga estado de propuesta.

Los acuerdos solicitados para v1 quedan como antecedentes; no se convierten automáticamente en aceptación de v2. Antes de ejecutar la evaluación completa:

1. Daf confirma bloques, columnas, presupuesto y centrado para T15.
2. Migue confirma las políticas propuestas de criterio, regularización e internas B para T03/T16.
3. Se guarda un registro definitivo con commit anterior a la corrida y se valida el ejecutor completo, sus estados y escritura en un destino nuevo.
4. La evaluación conserva referencia sola, scores internos, elecciones, OOF, desgloses, incertidumbre emparejada y manifest. Ninguna ampliación de búsqueda se decide para mejorar el resultado externo observado.

## Comprobaciones realizadas

65 pruebas distintas: 41 históricas y 24 nuevas, en Mac y Docker común Linux/amd64. También se comprueban con Python optimizado, sin depender de `assert` para las barreras propias. Las pruebas que emplean una copia de registro aceptable en memoria son casos aislados: no registran ni ejecutan una entrega T15 del reto.

Control matemático con **50 contextos reales A/B × cinco bloques × una λ fija = 250 ajustes técnicos** por entorno. Se contrastan 6,900 predicciones de control, centros y coeficientes con NumPy independiente. No se calcula MAE externo ni se elige sensor, ventana, bloque o ganador. Las 59 etiquetas ausentes no entran en ningún ajuste.

| Comprobación | Mac | Docker común |
|---|---:|---:|
| Diferencia máxima de predicción frente a matriz independiente | 2.67e-15 t/ha | 4.00e-15 t/ha |
| Diferencia máxima de coeficientes | 7.10e-16 | 8.16e-16 |
| Máxima media absoluta de corrección municipal del entrenamiento | 4.17e-17 t/ha | 4.17e-17 t/ha |

Mac/Docker mantienen las mismas 6,900 claves y fuentes; máxima diferencia de predicción 4.45e-15 t/ha. No se afirma identidad por bytes. Se conservan tolerancias de 1e-9 para predicción y 1e-10 para estado, sin ampliarlas.

Además, el componente común centrado reproduce técnicamente los **118 estados y 3,036 predicciones de ventanas fijas** de T09-v2 ya publicados en el commit `1c8d7eb31a0b2a5c751d949b42b07a1a9aa06cda`. En Mac, máxima diferencia de predicción 7.11e-15 t/ha y de coeficientes 3.31e-15. Docker reproduce esos mismos 118 estados y 3,036 predicciones: máxima diferencia 1.78e-15 t/ha y de coeficientes 5.28e-16. Es un contraste de equivalencia con parámetros publicados, sin nueva selección ni nuevo MAE; no sustituye la revisión humana del PR18.

La evidencia compacta está en [verificacion_centrado_v2.json](../registro/evaluacion_comun/verificacion_centrado_v2.json). Controles detallados, copias de solo lectura y logs quedan privados en el espacio de trabajo; no forman una entrega oficial T15.

## Incidencias propias y resolución

Una prueba del auditor intentó modificar una vista NumPy que pandas 3 devuelve como solo lectura. Se corrigió la prueba con una copia explícita; el estimador ya copiaba sus entradas. No se alteraron datos, dependencias ni tolerancias. Se añadió también una copia profunda del estado devuelto por el nuevo componente para que editar un informe no pueda modificar las medias o nombres internos del modelo.

## Cierre y siguiente alcance

La implementación propia y sus comprobaciones técnicas de H3 están preparadas para revisión. La aceptación humana de T09-v2 y del procedimiento común v2 sigue pendiente; T15 no tiene evaluación completa ni ganador y T16 no está congelada.

El diagnóstico de errores y aplicabilidad puede avanzar sobre T08 y T09-v2 identificados por versión, sin tratar otros históricos como ejecuciones de este método ni usar sus importancias como prueba definitiva del aporte interno de un bloque. Debe separar error, calidad, soporte espacial, alertas y limitaciones temporales. Las extracciones e integraciones no requieren repetirse sólo por H3. Toda aplicación futura conserva la limitación de tener rendimientos etiquetados de una sola campaña.

Skills de apoyo: scikit-learn y pensamiento crítico científico, ya usadas en el diseño común. Atribución: Kassis et al., *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, [DOI](https://doi.org/10.48550/arXiv.2609.00065). Son apoyo de procedimiento; no evidencia de mejor MAE.
