# Informe de cierre · T12, heterogeneidad municipal y contraste no lineal

- **Implementa:** Jass. **Responsable original de T12:** Diego. **Revisión metodológica:** Migue, **pendiente** (aún no revisó ni el diseño ni los resultados; ver «Límites»).
- **Método:** [`docs/T12_heterogeneidad_municipal.md`](../../docs/T12_heterogeneidad_municipal.md) y decisión `D_T12_001`, escritos antes de correr.
- **Resultados:** `registro/t12/`. **Bitácora:** [`bitacora.md`](bitacora.md). **Fecha:** 16 de octubre de 2026.

## En una frase

Con este procedimiento, estas entradas y esta campaña, **dejar que cada municipio tenga su propia regla de corrección, o usar árboles en lugar de una línea recta (las dos versiones que probamos), no mejora de forma comprobable la estimación que da el promedio del municipio**; se conserva la referencia `media_mun__resp_grupo`. Hay un indicio muy pequeño a favor (resultado **R2**, «señal sin umbral»), pero con 138 parcelas no alcanza para cambiar nada.

## Qué preguntamos

La referencia del equipo estima el rendimiento de una parcela con el promedio de las parcelas conocidas de su municipio. Es como tasar una casa con el precio promedio de su colonia. Hasta ahora, todas las correcciones probadas (T08 a T15) usan **una sola regla para todos los municipios**: por ejemplo, «a más pendiente, un poco más de rendimiento», igual en todas las colonias.

T12 preguntó dos cosas:

1. ¿Y si cada municipio tuviera **su propia regla**? Si en una colonia la pendiente ayuda y en otra estorba, una sola regla promedia las dos y la variable parece inútil.
2. ¿Y si la relación **no fuera una línea recta** (por ejemplo, «más verde y además con más pendiente»)?

T12 **no buscó variables nuevas**: usó las que ya había (relieve, área y Planet) y cambió la forma de usarlas.

## Qué hicimos

1. **Escribimos el diseño antes de ver resultados** (`D_T12_001`): un solo candidato que puede ser promovido (`t12_het_GP`), tres secundarios que no, cuatro controles, y los cinco resultados posibles (R1 a R5) con su significado.
2. **Entrenamos 8 procedimientos**, todos con la misma base (la referencia más una corrección pequeña sobre su error):
   - `het_GP`, `het_G`, `het_P`: regla común más un ajuste propio, contenido, para los municipios con al menos 12 parcelas en el entrenamiento (Chignahuapan, Calpulalpan y Singuilucan), usando relieve y área (G), Planet (P) o ambos (GP).
   - `gb_GP`: un modelo de árboles de decisión que sí puede capturar relaciones que no son una recta.
   - Tres **controles «una sola regla»** (`control_comun_G`, `_P`, `_GP`): lo mismo sin el ajuste por municipio, para saber si el ajuste ayuda de verdad.
   - Un **control con la mediana** en vez de la media como referencia.
3. **Los evaluamos con las mismas reglas del equipo** (T03): 5 repeticiones de 5 particiones, en dos escenarios (A: parcelas nuevas de municipios ya conocidos; B: zonas climáticas nuevas), y con la configuración de cada modelo elegida dentro de cada entrenamiento, sin mirar las parcelas que se evalúan.
4. **Corrimos cinco controles extra** con los resultados ya guardados: ablación (¿ayuda el ajuste por municipio?), revuelto (¿pasa lo mismo si mezclamos los datos al azar?), curva de aprendizaje (¿bajaría el error con más parcelas?), desgloses (¿dónde se equivoca más?) y qué aprendió el modelo.
5. **Un auditor independiente** rehízo los cálculos con otro código y **coincidió** (diferencias menores a 1e-15).
6. **Repetimos toda la evaluación** en una carpeta nueva con Docker sobre Windows: salió **idéntica byte a byte**.

## Qué encontramos

- **Ningún procedimiento cumple la regla de promoción de T03.** En el escenario A (sin respaldo), el candidato principal `t12_het_GP` baja el error promedio de 0.3205 a 0.3195 t/ha (**−0.0009**) y mejora en 4 de las 5 repeticiones. Pero el rango de confianza (IC95) va de −0.0066 a +0.0047: **incluye el cero**, así que no podemos asegurar que sea una mejora real. La regla pedía como mínimo −0.01 con el rango entero por debajo de cero.
- **El revuelto sí distingue el efecto del azar, pero el efecto es minúsculo.** En las 20 mezclas al azar, el cambio fue siempre cero o positivo (entre 0.0000 y +0.0030); el real, −0.0009, fue mejor que todas (p = 0.0476). Es la señal más fuerte del estudio, y aun así equivale a menos del 0.3 % del error. Con 20 mezclas ese es el valor de p más pequeño posible.
- **El ajuste por municipio ayuda poco o nada frente a una sola regla.** Frente al control `_GP`: −0.0006 (rango [−0.0021, +0.0011]). Donde sí se nota es en relieve y área solos: `het_G` baja −0.0045 frente a `control_comun_G`. La causa es que la regla común de relieve y área **empeora** a la referencia (+0.0032), y repartirla por municipio solo la repara; `het_G` queda en −0.0014 frente a la referencia, sin significancia.
- **El modelo no lineal tampoco gana.** `gb_GP` queda en +0.0019 en A y prácticamente en cero en B (−0.0007 por parcela, +0.0005 por repetición: el signo depende de cómo se promedie, así que no se lee como mejora), y en el ajuste final con las 138 parcelas elige no corregir nada.
- **En el escenario B no hay ninguna mejora.** `het_GP` empeora (+0.0071 por parcela; +0.0078 por repetición). La referencia es difícil de superar para zonas climáticas nuevas. B se usa solo como sensibilidad: en sus particiones internas muchas parcelas de validación no tienen referencia municipal propia (según la revisión del PR #22, 206 de 2,760 registros no tienen ninguna y 360 tienen una sola), así que la elección de configuración allí es más ruidosa.
- **Casi no hay heterogeneidad real.** Los coeficientes que aprende el modelo son muy pequeños (del orden de 0.01 en escala estandarizada) y los de relieve y área tienen el mismo signo en todos los contextos donde existen. Solo Chignahuapan tiene reglas más fuertes que el resto, de más o menos el doble. Por eso las predicciones casi no se mueven de la referencia: como máximo 0.07 t/ha, en promedio 0.02.
- **Más parcelas podrían ayudar un poco.** Con la mitad de los datos, `het_GP` es peor que la referencia (+0.0016); con tres cuartos, también (+0.0015); con todos, mejor (−0.0009). La curva sigue bajando, aunque despacio.
- **La media contra la mediana (nota para T16).** Con la mediana municipal como observación de referencia, el error es menor en A (0.3126 contra 0.3205) y en B (0.3398 contra 0.3579). Es lo mismo que ya se había visto en T08 (−0.0079, rango [−0.0163, +0.0058], sin cumplir la regla); T12 lo reproduce, no lo descubre.

## Resultado según las reglas escritas antes de correr

| Resultado | ¿Se cumple? | Por qué |
|---|---|---|
| R1. Promoción | **No** | El rango de confianza de `t12_het_GP` cruza el cero y el cambio (−0.0009) está lejos de −0.01 |
| **R2. Señal sin umbral** | **Sí** | `het_GP` mejora en 4 de 5 repeticiones, su rango incluye el cero y la ablación (C1) es negativa (−0.0006) |
| R3. Mejora en las colas | Parcial (se anota) | Baja un poco el error en el cuarto de parcelas más difíciles, pero el MAE también mejora nominalmente, y el control común hace lo mismo |
| R4 / R5. Nada | No | Hay una señal estable, aunque pequeña |

**Decisión:** no cambia el modelo. La referencia se queda.

## Tabla de resultados (escenario A, sin respaldo, 135 parcelas)

Error promedio de la referencia: **0.3205** t/ha. `dMAE` = cambio del error promedio frente a la referencia (negativo = mejor). `IC95` = rango en el que probablemente cae la diferencia real; si incluye el cero, no se puede asegurar que haya mejora.

**Unidades.** Todos los `dMAE` y sus IC95 son «por parcela»: primero se promedia el error de cada parcela entre las repeticiones en que fue evaluada, y luego entre parcelas (así lo define T03 §4). En A las tres formas de promediar dan lo mismo (0.3205). En B no: la referencia vale 0.3579 si se promedia el MAE de cada repetición (cifra que se cita en este informe junto con las de la mediana), 0.3584 por registro y 0.3632 por parcela, porque 16 de las 135 parcelas solo se evalúan en 4 repeticiones. No es una mejora ni un empeoramiento, solo una ponderación distinta; por eso en B se compara siempre con la misma forma de promediar.

| Procedimiento | dMAE | IC95 | Repeticiones que mejoran (de 5) | dRMSE |
|---|---|---|---|---|
| `t12_het_GP` (principal) | −0.0009 | [−0.0066, +0.0047] | 4 | −0.0054 |
| `t12_het_G` | −0.0014 | [−0.0063, +0.0042] | 5 | −0.0053 |
| `t12_het_P` | +0.0033 | [−0.0010, +0.0081] | 0 | +0.0001 |
| `t12_gb_GP` | +0.0019 | [−0.0041, +0.0085] | 0 | −0.0002 |
| `t12_control_comun_GP` | −0.0003 | [−0.0054, +0.0051] | 4 | −0.0038 |
| `t12_control_comun_G` | +0.0032 | [−0.0045, +0.0119] | 1 | −0.0040 |
| `t12_control_comun_P` | +0.0025 | [−0.0019, +0.0069] | 1 | −0.0002 |
| `t12_control_mediana_het_GP` (referencia mediana) | −0.0061 | [−0.0150, +0.0078] | 4 | −0.0035 |

## Preguntas y respuestas

**¿Hay que cambiar el modelo?**
No. Ningún procedimiento cumple la regla del equipo. La referencia `media_mun__resp_grupo` se conserva.

**¿Entonces la idea no sirve?**
Sirve como diagnóstico, no como modelo. Nos dice que, con relieve, área y Planet, **darle a cada municipio su propia regla no añade información útil**. Eso es un resultado, no un fracaso: con una prueba definida de antemano, **no encontró apoyo** para una hipótesis razonable. No prueba que otra forma de modelo, más profunda o con más datos, tampoco funcione.

**¿Por qué no mejora?**
No lo probamos, y varias explicaciones son compatibles con los datos: (a) dentro de un mismo municipio, los rendimientos varían mucho (en Chignahuapan, de 2.15 a 5.59 t/ha entre sus 71 parcelas etiquetadas) y las variables disponibles no explican esa diferencia; (b) lo que sí la explicaría (variedad, fecha de siembra, manejo) no está en nuestros datos; (c) con unas 110 parcelas por entrenamiento, estimar reglas separadas por municipio deja mucho ruido.

**¿Qué pasó con las parcelas de error grande?**
Prácticamente nada. Las que más mejoran lo hacen 0.03 a 0.09 t/ha; las que más empeoran, 0.03 a 0.07. Las parcelas que se alejan 1 t/ha de la referencia siguen igual. De las 20 que más mejoran, 17 son de Chignahuapan; de las 20 que más empeoran, 14.

**¿Dónde se equivoca más el modelo?**
En el cuarto de parcelas con más error (el 25 % más difícil) el error es de unos 0.79 t/ha, contra 0.03 en el cuarto más fácil. `het_GP` baja el error del cuarto difícil en 0.0112, pero lo sube en las parcelas fáciles (+0.0065 y +0.0099). El control con una sola regla hace algo parecido (−0.0071 en el cuarto difícil), así que esa mejora no se debe al ajuste por municipio.

**¿Qué pasa sin las 24 parcelas con alerta de contorno?**
La mejora de `het_GP` se reduce de −0.0009 a −0.0005 (111 parcelas). Parte de la señal viene de esas parcelas.

**¿Y si FIRA eligiera el RMSE como métrica?**
Tampoco se alcanza el umbral. La mayor baja de RMSE frente a la referencia es 0.0054 t/ha en A y 0.0092 en B (control con mediana), siempre menor que 0.01. No se volvió a elegir la configuración con error cuadrático, así que esto no descarta que saliera algo distinto con RMSE como métrica principal.

**¿Se puede confiar en estos números?**
Los cálculos, sí: un auditor independiente, con otro código, coincide en las 5,520 predicciones de la familia por municipio que reconstruyó, en las 240 métricas y en las 52 comparaciones (diferencia máxima 1.8e-15), y la corrida repetida en Windows con Docker es idéntica byte a byte. Falta la corrida en Mac (Dani o Daf). También se comprobó, el 16 de octubre, que los cambios posteriores de T15 (hasta el commit `cc7d0ae`) no tocan nada de lo que T12 usa: el código común v3 y las 14 entradas fijadas en `manifest.json` son idénticos, así que los resultados no cambian ni hace falta repetir la corrida. Lo que **no** garantiza todo eso es que el modelo sea bueno: solo que los números están bien calculados.

**¿Qué pasa con las 59 parcelas reservadas?**
Sus predicciones de T12 son **exploratorias**: ajustadas con las 138 etiquetadas, no se pueden evaluar hasta que FIRA publique los valores reales. En el ajuste final, `gb_GP` y el control con mediana eligen no corregir nada (predicciones iguales a su referencia); `het_GP` corrige como máximo 0.071 t/ha. Para la app se siguen usando las de la referencia.

## Qué queda establecido con este estudio

Antes de T12 había una duda abierta: ¿las variables de T10, T11, T14 y T15 no ayudaban porque no sirven, o porque las usábamos de una forma limitada (una sola regla para todos los municipios y en línea recta)? T12 contesta esa duda para relieve, área y Planet. Los resultados que siguen se pueden citar porque están definidos de antemano, auditados y reproducidos.

| Qué podemos afirmar | Con qué números | Qué tan firme |
|---|---|---|
| **Darle su propia regla a cada municipio no rescata a estas variables.** | Ninguno de los 8 procedimientos cumple la regla de T03 §4: 0 de 8 en A y 0 de 8 en B. El mejor caso, `het_GP`, queda en −0.0009 con IC95 [−0.0066, +0.0047]. | Firme para estas variables, esta campaña y 138 parcelas. |
| **Un modelo que no es una línea recta tampoco las rescata.** | `gb_GP`: +0.0019 en A y ≈0 en B frente a la referencia (−0.0007 por parcela, +0.0005 por repetición); en el ajuste final con las 138 elige no corregir nada. | Firme, mismas condiciones. |
| **Con estas dos formas de modelo, lo que vieron T10, T11, T14 y T15 no mejora.** | T10 dejó anotado que un modelo no lineal era tarea de T12. Resultado: ni la regla por municipio (Ridge) ni árboles de profundidad 2 (50 o 150 árboles) logran una mejora suficiente. | Firme solo para esas dos variantes, relieve, área y Planet, 138 parcelas y una campaña. **No** descarta otras formas de modelo (árboles más profundos, más datos) ni otras variables. |
| **La regla común de relieve y área perjudica a la referencia.** | `control_comun_G`: +0.0032 en A y +0.0092 en B (IC95 [+0.0031, +0.0249], todo por encima de cero). T10 había visto +0.0027. | Bastante firme: coincide con T10 y en B el rango no toca el cero. |
| **Repartir esa regla por municipio repara la pérdida, pero no gana.** | `het_G` frente a `control_comun_G`: −0.0045 [−0.0083, −0.0011], mejora en 5 de 5 repeticiones. Frente a la referencia queda en −0.0014 [−0.0063, +0.0042]. | Firme como diagnóstico; no como mejora del modelo. |
| **El promedio municipal es una referencia difícil de superar.** | 8 alternativas probadas con la misma regla, cada una repetida 25 veces por escenario, y ninguna la supera de forma comprobable. | Firme para lo probado. Respalda seguir con ella en la app y en T16. |
| **La mediana reproduce lo de T08.** | A: 0.3126 contra 0.3205; B: 0.3398 contra 0.3579. Con la corrección encima empeora (+0.0018 en A), así que la ventaja viene de la mediana, no de la corrección. | Consistente con T08, que no cumplió la regla. Hay que probarla en T16 con su propia regla. |

**Una aclaración sobre «lo lineal».** T12 no demuestra que lo lineal sea mejor que lo no lineal. Lo que se confirma es que **lo simple, la referencia, no se supera**. Entre las dos formas de corregir no hay un ganador claro: en A el modelo de árboles queda 0.0022 peor que su control lineal (rango [−0.0013, +0.0063], incluye el cero); en B queda 0.0108 mejor por parcela (0.0097 por repetición; rango [−0.0335, −0.0009]), pero ese control lineal ya estaba +0.0100 peor que la referencia. Es decir, el modelo de árboles solo mejora a un control que ya empeoraba.

**Lo que NO queda establecido.**

- Que el mínimo −0.0009 de `het_GP` sea un efecto real: es una pista, no una prueba.
- Que la causa del límite sean la variedad, la fecha de siembra o el manejo: es una hipótesis compatible con los datos, no probada.
- Que más parcelas ayuden: la curva de aprendizaje lo sugiere (`het_GP` solo supera a la referencia con todas las parcelas), pero no se probó.
- Que otras variables (clima, Sentinel-2, borde rojo, fenología fina) no sirvan: no se probaron en T12.
- Que el resultado valga para otras campañas, y que salga igual en Mac (pendiente).

**Por qué no fue tiempo perdido.**

1. Responde, de forma acotada, una pregunta que T10 y T11 dejaron abierta, con una prueba definida antes de ver resultados.
2. Deja evidencia que otra persona puede repetir y comprobar: código congelado con huellas, auditor independiente y comparador de reproducciones.
3. Es un argumento de metodología para el reto: se probó lo razonable, con rigor, y se reporta el resultado negativo con honestidad.
4. Deja tres insumos concretos: la nota de la mediana para T16, la información sobre relieve y área para T15 (ver más abajo), y la curva de aprendizaje para T18.
5. Deja herramientas reutilizables (auditor, comparador, controles) para los frentes siguientes.

## Límites

- **Una sola campaña etiquetada** y 138 parcelas: el resultado no dice nada sobre otros años.
- **Diseño no ciego.** Antes de correr, el equipo ya conocía los resultados de T08 a T15 y correlaciones dentro de los municipios calculadas con las mismas 138 parcelas. Los intervalos de confianza son **nominales**: no corrigen que se hayan mirado muchas variables ni que se hagan 13 comparaciones.
- **La señal de `het_GP` depende en parte de pocas parcelas** (Chignahuapan y las parcelas con alerta de contorno).
- **El revuelto usó 20 permutaciones**, lo mínimo para que p ≤ 0.05 sea posible (p = 0.0476). No es una prueba fina.
- **Solo se probaron dos formas de modelo** (regla por municipio y árboles de decisión) y las variables de relieve, área y Planet. No se probaron variables de clima, Sentinel-2, calidad ni vecinas (eso es de otras tareas).
- **Corrida en Mac pendiente** (Dani o Daf).
- **La forma del modelo quedó poco explorada.** Solo se probaron una regla por municipio con Ridge y árboles de profundidad 2 con unas 110 parcelas por entrenamiento, que es una prueba débil de «no lineal». La conclusión se limita a esas dos variantes.
- **Los árboles tuvieron más libertad que el Ridge.** `init='zero'` solo fija en cero el punto de partida de las predicciones; después las hojas de los árboles sí pueden aprender un desplazamiento constante, a diferencia del Ridge, que no tiene intercepto. Por eso los árboles tuvieron un poco más de libertad que las demás familias. Se midió el efecto: el desplazamiento medio de `gb_GP` frente a la referencia es +0.0015 t/ha en A y +0.0001 en B, así que no aprendió un sesgo sistemático, y aun con esa libertad no mejora a la referencia. No es una fuga de datos. El diseño decía lo contrario (nota con fecha en `docs/T12_heterogeneidad_municipal.md`, §5.2); el comentario equivalente de `scripts/t12_heterogeneidad.py` no se corrige porque el archivo está congelado por su huella.
- **Estado de la revisión.** La condición 6 de las barreras («Migue revisó este diseño») **no se había cumplido** cuando se corrió con `--confirmo-barreras` el 15 de octubre: Jass confirmó las barreras sin una revisión previa de Migue. Migue todavía no revisó ni el diseño ni los resultados. Los resultados son válidos para el diseño tal como se registró, pero esa revisión puede pedir cambios; hasta entonces hay que leerlos como condicionales a ella.

## Para otros frentes

- **T16 (cierre) y T17 (app):** se mantiene la referencia. Nota para T16: la **mediana** municipal como observación de referencia rindió menos error que la media en A y B (T08 ya lo había visto, sin cumplir la regla); vale la pena una prueba con su propia regla escrita antes. No es decisión de T12.
- **T15 (combinaciones):** T15 cerró su menú de ocho comparaciones y no se pide cambiarlo. Los tres controles `control_comun_G`, `_P` y `_GP` de T12 usan **exactamente las mismas opciones** (ventana, λ y columnas) que los procedimientos G, P y G+P de ese menú, con el mismo código v3. Dos consecuencias: (1) T15 ya no es ciego para esos tres, porque T12 midió que en A/sin_respaldo dan +0.0032 (G), +0.0025 (P) y −0.0003 (G+P), ninguno cumple la regla, y en B ninguno mejora; conviene decirlo en su registro de exposición previa. (2) Es una comprobación gratis: cuando T15 corra su evaluación completa, esos tres deberían salir idénticos a los de `registro/t12/`; si no, hay un error en uno de los dos lados. La regla común de relieve y área (G) es la que más empeora a la referencia (+0.0032 en A, +0.0092 en B).
- **T18 (ajuste final con las 138):** en la curva de aprendizaje, la ventaja de `het_GP` aparece solo con todas las parcelas (con la mitad o tres cuartos era peor que la referencia). Si FIRA entrega más parcelas etiquetadas, vale la pena repetir la prueba.
- **Daf (vecinas, V20) y Migue:** antes de invertir en variables nuevas, conviene un diagnóstico del «techo»: cuánto difieren en rendimiento parcelas vecinas casi iguales en todo lo que medimos. Si difieren mucho, el límite está en lo que no medimos.
- **T19 (informe del reto):** este documento y los controles se pueden citar tal cual como una prueba hecha con rigor cuyo resultado es negativo.

## Ficha de consumo para T16 y la app

- **Qué usar para las 59 parcelas:** las predicciones de la referencia `media_mun__resp_grupo` (T08). T12 **no las sustituye**.
- **Archivo con las predicciones de T12:** `registro/t12/predicciones_59_t12.csv` (472 filas = 59 parcelas × 8 procedimientos). Todas llevan `exploratoria = True`.
- **Qué no usar:** ninguna fila de `t12_*` como predicción oficial. Sirven para auditar y comparar.
- **Filas que repiten la referencia:** `t12_gb_GP` y `t12_control_mediana_het_GP` eligen «referencia sola» en el ajuste final.
- **Máxima corrección de `t12_het_GP`:** 0.071 t/ha (promedio 0.022), con la opción `jun_oct_l10_k1`.
- **Estas predicciones se ajustaron con las 138 etiquetadas;** no hay forma de evaluarlas hasta que FIRA publique los valores reales.

## Dónde está todo

| Qué | Dónde |
|---|---|
| Método y diseño | `docs/T12_heterogeneidad_municipal.md`, `D_T12_001`, `registro/t12/procedimiento_t12.json` |
| Código y pruebas | `scripts/t12_heterogeneidad.py` (congelado), `t12_evaluar.py`, `t12_controles.py`, `t12_auditar.py`, `t12_reproducir.py` y `tests/test_t12_*.py` |
| Resultados | `registro/t12/` (`manifest.json` con huellas) |
| Controles | `control_revuelto_t12.csv`, `curva_aprendizaje_t12.csv`, `desglose_error_t12.csv`, `sensibilidad_sin_alerta_t12.csv`, `pendientes_por_municipio_t12.csv`, `importancia_gb_t12.csv`, `parcelas_extremas_t12.csv` |
| Auditoría | `registro/t12/auditoria_t12.json` |
| Reproducción | `reports/t12_repro/reproduccion_t12.json` (local, no versionada) |
| Experimentos | `E_T12_001` a `E_T12_008` en `registro/experimentos.csv` |
| Bitácora | `bitacora.md` |
