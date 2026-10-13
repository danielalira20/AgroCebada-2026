# T09 · Estimadores y controles antes de la evaluación completa

**12 de octubre de 2026 · Dani · Rama `t09-territorio-clima`.**

**Nota del 13 de octubre:** este documento conserva la fase histórica de componentes v1. Su evaluación posterior está en [la entrega v1](t09_evaluacion.md). La corrección H3 se prepara como [R centrado v2](t09_R_centrado_v2.md), con identificador y estado separados; los resultados v1 no se sustituyen.

Estado: implementación y comprobación de componentes aprobadas; revisión humana de Migue pendiente. No se ejecutó la comparación completa T09, no se eligió ganador ni se generó una entrega nueva para las 59. Los ajustes de pruebas usan datos reales para comprobar algoritmos; no son resultados oficiales de los tres experimentos.

## Problema que resuelve

El [diseño v1.0](t09_diseno.md) fija comparaciones, ventanas, presupuesto y criterios, pero faltaban estimadores que lo implementaran sin mezclar etiquetas, compartir ajustes entre particiones o penalizar inadvertidamente el municipio. Antes de medir desempeño necesitamos verificar las matemáticas y los respaldos con pruebas que detecten errores reales.

## Solución que implementa

Tres módulos reutilizables, sin un ejecutor de evaluación externa:

| Archivo | Responsabilidad |
|---|---|
| `scripts/t09_entradas.py` | Verificar diseño, huellas/roles/unidades T07, fichas, 138/59, uniones por ID y particiones T03; entregar variables y etiquetas separadas |
| `scripts/t09_estimadores.py` | T exacta y los tres procedimientos Ridge; escalado propio de cada ajuste, respaldo y descomposición de la predicción |
| `scripts/t09_seleccion.py` | Cuatro particiones internas según escenario, ocho opciones por experimento, MAE concatenado, máscaras comunes y desempates del diseño |
| `tests/test_t09_estimadores.py` | 33 pruebas nuevas: contratos, matriz independiente, LOO, fugas, constantes, serialización y selección |

`registro/t09/diseno.json` permanece intacto, SHA-256 `1072e4196df68359fa3728e504f23ec28dd94b637715854a6635d36d4478081f`. El nuevo [registro de implementación](../registro/t09/implementacion.json) resume lo comprobado, sin sustituir el manifiesto de una ejecución oficial futura. Los tres experimentos de `registro/experimentos.csv` siguen planificados, no ejecutados oficialmente.

## 1. Entrada y ajuste por identidad

La rama se creó desde `origin/dev` `cb4580701b2bf28588e56ce3d73e64fbf2b6a738` e incorporó por avance directo el diseño/diagnóstico local `b99100b`; no se importó código de los PR abiertos de T11/T14. El Google Doc mantiene la revisión identificada en el diseño. No cambió el menú de variables o parámetros ni el protocolo general T03.

El preflight lee la entrega T07 aceptada y sus fichas, verifica unidades, ventanas y huellas, y cruza municipio/grupo/celda T03 por ID. Las etiquetas se entregan únicamente para las 138 conocidas; la tabla de reservadas contiene sólo entradas. Los dos faltantes de relieve no excluyen parcelas, porque T09 no usa relieve.

Los estimadores aceptan `X` como DataFrame con índice igual a `id_parcela` y `y` como Series con los mismos IDs y orden. No aceptan etiquetas anónimas por posición. Etiqueta/predicción dentro de X, ID duplicado, clima ausente/no finito, metadato territorial vacío o parámetro inválido bloquean el ajuste. No se imputa rendimiento o clima ni se cambian unidades.

La identidad del diseño se comprueba antes de la búsqueda: una ampliación o cambio de política requiere una nueva versión explícita. La comprobación de procedencia congelada no reextrae mapas ni cambia los archivos anteriores.

## 2. Procedimientos implementados

| Procedimiento | Ajuste | Respaldo/origen |
|---|---|---|
| T · `MediaTerritorial` | Media municipal literal de entrenamiento | Municipio → grupo de registro → global, como T08 |
| CL · `RidgeClimatico('CL')` | Tres entradas climáticas y un intercepto global | No utiliza municipio/grupo/celda para predecir; `fuente=global` |
| TC · `RidgeClimatico('TC')` | Coeficientes climáticos con interceptos municipales sin penalizar | Centrado de X/y dentro del entrenamiento; respaldo del intercepto a grupo/global |
| R · `RidgeClimatico('R')` | Corrección de residuos LOO de la referencia | La fila no calcula su propia referencia; corrección sin intercepto adicional |

Cada `fit` crea su pipeline de escalado con los datos de ese entrenamiento. `alpha=n×lambda` y SVD siguen el diseño. TC no vuelve a escalar las desviaciones municipales ni penaliza indicadores municipales. R rehace el LOO en cada entrenamiento interno y se puntúa sobre rendimiento completo: referencia de entrenamiento + corrección, frente a etiqueta de validación.

Los cuatro procedimientos tienen `fit`, `predict` y `predict_with_details`. Esta última devuelve ID, valor, origen, referencia/intercepto y corrección. Facilita comprobar cómo se construye cada predicción y preparar la explicación de la app; los componentes no prueban causalidad ni efectos de intervenciones agronómicas.

Los estimadores pueden clonarse, usarse como componente de `Pipeline` y guardarse/cargarse con joblib; esas operaciones se probaron en ambos entornos. Su interfaz por ID es deliberadamente más estricta que la de matrices anónimas genéricas. Para seleccionar se utiliza nuestro método MAE explícito; no se sustituye por el `score` R² predeterminado de scikit-learn.

Cambiar parámetros después de ajustar obliga a reajustar. Un intento de ajuste inválido elimina el estado anterior: no puede reutilizarse silenciosamente una predicción de otro ajuste.

## 3. Selección interna y controles contra filtración

Se implementaron exactamente las políticas del diseño: A estratifica por municipio y `otros`; B conserva celdas completas; C conserva municipios completos. La agrupación interna B/C es la extensión T09 ya documentada, no una modificación nueva de T03. Se verificaron 60 contextos y 240 particiones, incluidas las que se utilizarían al ajustar para 59; esa comprobación no ajusta un modelo para ellas.

Para A/B la máscara depende del soporte municipal de la referencia, también para CL, cuyo origen numérico es global. C puntúa todas porque no tiene soporte municipal en su validación. Se concatenan errores elegibles: no se da igual peso a particiones internas de tamaños distintos. Se conservan las ocho puntuaciones y el ganador de cada ventana, para los futuros contrastes de ventana fija.

Las pruebas alteran únicamente copias en memoria:

- Cambiar etiquetas externas deja iguales entrenamiento, selección y predicciones de control.
- Cambiar etiquetas de una validación interna deja iguales escalas, referencias, residuos, coeficientes y predicciones de una opción entrenada sin ella. Sí puede cambiar su puntuación: ésa es la función legítima de la validación.
- El control positivo calcula el método antiguo incorrecto (LOO externo cortado después) y confirma que una etiqueta de validación cambia residuos internos. Así la prueba realmente puede detectar esa fuga.
- Cambiar municipio/grupo/celda/superficie al consultar CL no altera su valor numérico.
- Cambiar después los objetos de entrada utilizados en `fit` no altera el modelo ya ajustado: no conserva vistas mutables de esas tablas.

Ninguna prueba fabrica rendimientos para ampliar la muestra, cambia etiquetas originales o presenta perturbaciones como evidencia predictiva. Los controles acotan los fallos examinados; no son una garantía universal de ausencia de cualquier error futuro.

## 4. Verificación matemática independiente

La referencia reproduce los 50 contextos A/B y 1380 predicciones publicadas T08, incluidas fuente/etiqueta. La diferencia máxima fue **0.0**. Las máscaras siguen A675/B659.

Además se verificaron **72 ajustes climáticos por entorno**: tres contextos representativos A/B/C × dos ventanas × cuatro λ × CL/TC/R. No se eligieron según su desempeño; no se calcularon métricas externas para escoger un modelo.

Para CL/TC se construyó una matriz completa con interceptos y penalización sólo de las tres columnas climáticas. Las pruebas usan ecuaciones normales; una comprobación adicional usa mínimos cuadrados de un sistema aumentado. Es una formulación distinta del centrado municipal de producción. R se contrastó con LOO por exclusión explícita de cada fila y su sistema lineal sin intercepto. Se probaron también respaldos, clima constante, serialización y desempates.

| Comprobación | Mac ARM | Docker linux/amd64 | Límite fijado |
|---|---:|---:|---:|
| Predicción frente a solución matricial independiente, máximo | 8.57e-14 t/ha | 7.77e-14 t/ha | 1e-9 t/ha |
| Referencia LOO frente a exclusión explícita, máximo | 1.78e-15 t/ha | 1.78e-15 t/ha | 1e-10 t/ha |
| Referencia T frente a T08 | 0.0 | 0.0 | 1e-12 de lectura/representación |

Estas son diferencias de **cálculo**, no el error del modelo contra la cosecha. Un cálculo consistente puede tener mal desempeño predictivo; eso se comprobará en la fase siguiente.

## 5. Entorno y conservación de fuentes

- **Mac:** 299 pruebas del proyecto aprobadas, incluidas las 33 nuevas. No se afirma que esas 299 se hayan ejecutado en Docker.
- **Docker:** 59 pruebas aprobadas (33 T09 +13 diagnóstico +13 fichas), imagen común `agrocebada-diagnostico-comun:amd64`, ID `sha256:f47077f5bfdd4e6e05d17b8c5056bcbb79498f277ab5d38fee117a0bab5221f5`.
- Python 3.12.15, NumPy 2.2.6, pandas 3.0.6, SciPy 1.18.1 y scikit-learn 1.9.1 en ambos; Mac arm64 y Linux x86_64.
- Dos comprobaciones numéricas Docker idénticas: JSON y CSV de controles coinciden byte por byte. Frente a Mac, diferencia máxima entre coeficientes **4.53e-15**; se mantuvo rtol=1e-10/atol=1e-12.
- **401 archivos protegidos intactos:** originales/copia raw, visualización QGIS, proyectos guardados, datos del equipo, particiones y diseño. No se mezclaron datos externos ni se modificaron T07/T03.

No se instalaron dependencias nuevas ni se utilizó GPU. Cada cálculo se limita a un hilo; Docker se usa para comprobar portabilidad y se detiene al terminar. No se mide ni promete todavía el tiempo de toda la evaluación de 6120 ajustes; esa cifra del diseño es un presupuesto, no una duración.

## 6. Problemas detectados y resueltos

1. **Estado antiguo tras fallo de `fit`.** El prototipo mantenía coeficientes anteriores si una entrada inválida detenía el nuevo ajuste. Una prueba reprodujo el riesgo en los cuatro procedimientos. Se añadió reinicio de estado aprendido al comenzar; ahora una predicción posterior a un ajuste fallido exige reajustar.
2. **Máscaras ambiguas.** El prototipo admitía cadenas/números como elegibilidad booleana. Se exigen booleanos, longitud correcta y casos elegibles; no se aceptan conversiones silenciosas de `"false"` o 1. Las pruebas muestran el fallo anterior y el bloqueo corregido.
3. **Prueba Docker sin espacio temporal.** La primera ejecución montó todo el repo en sólo lectura; los 33 controles nuevos pasaron, pero una prueba anterior del diagnóstico no pudo crear su directorio temporal en `reports`. Se resolvió con un tmpfs de 256 MB para esa batería; datos/código siguen en sólo lectura. No se cambiaron cálculos o tolerancias para pasar.

Los logs de los intentos fallidos se conservan como historia, separados de los finales aprobados. No afectaron los originales ni una entrega oficial, porque la evaluación completa todavía no se ejecutó.

## 7. Reproducir esta fase

Desde la raíz, en el entorno común:

```bash
python -m scripts.t09_entradas
python -m unittest tests.test_t09_estimadores -v
```

Para la batería Docker que incluye el diagnóstico anterior, dar a `reports` una carpeta temporal escribible; no es necesario habilitar escritura de los datos originales. El entorno común y sus montajes deben seguir el contrato del equipo. La fuente compartida contiene los controles matemáticos; el runner auxiliar de evidencia está localmente en `reports/t09_estimadores_20261012/verificar_calculos.py`.

Evidencia local válida: `pruebas_completas_mac.log`, `pruebas_docker_corregidas.log`, `mac_final/`, `docker_1/`, `docker_2/`, `validacion_final.json`. `mac_1/` identifica la versión anterior de las pruebas (31); se conserva y no se presenta como la batería final 33. `controles_fallidos_prototipo.log` y `pruebas_docker.log` son intentos fallidos, no aprobaciones.

## 8. Qué queda y recursos revisados

Falta implementar el ejecutor de evaluación externa/reportes completos, ejecutar A/B/C según diseño, calcular incertidumbre/desgloses/sensibilidad y aplicabilidad, interpretar resultados y obtener revisión esencial. No hay todavía MAE/RMSE T09 completos, modelo ganador, intervalo de predicción individual, validación entre años o entrega final59. La selección final es T16 y la entrega definitiva T18.

T11 v2 y T14 siguen como referencias de coordinación, con los alcances/observaciones de [las decisiones](t09_decisiones.md). No se aprueban sus PR por haber implementado T09. La guía conceptual y las respuestas FIRA orientan el contrato: temporal y grano confirmados; siembra/variedad/manejo parcelarios no inventados; 2022–2024 no crea nuevas etiquetas. Suelo/clima diario permanecen como extensiones ante una carencia concreta tras la primera evaluación; Agrocostos/NAX no se incorporaron como entradas.

Se emplearon las skills scikit-learn y scientific-critical-thinking. La bibliografía y su referencia están en [el diseño §17](t09_diseno.md#17-fuentes-y-trazabilidad). Se verificaron de nuevo las fuentes primarias de [Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html), [prevención de filtraciones](https://scikit-learn.org/stable/common_pitfalls.html) y [GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html). La adaptación por ID, normalización y descomposición es del proyecto; las herramientas no certifican su futuro desempeño.

Esta fase deja componentes verificables y reutilizables para el siguiente paso. La revisión humana sigue pendiente. No se hizo push, PR, merge remoto, mensajes externos ni cambios al Google Doc. AGENTS.md, skills y evidencia local permanecen fuera de Git.
