# Bitácora de la evaluación de heterogeneidad municipal y contraste no lineal (T12)

> **Nota para el equipo.** Bitácora de trabajo en orden cronológico: qué se hizo en cada paso, qué se esperaba, qué se encontró y qué se decidió. El método está en [`docs/T12_heterogeneidad_municipal.md`](../../docs/T12_heterogeneidad_municipal.md) y las decisiones en `D_T12_001` (diseño, antes de correr) y `D_T12_002` (cierre, después de los resultados) en `registro/decisiones.csv`. Los resultados compartidos están en `registro/t12/`; esta carpeta guarda lo que los explica.

**Pregunta que debe quedar contestada:** ¿permitir que la relación entre las variables de una parcela y su desviación del promedio de su municipio cambie según el municipio, o que no sea una línea recta, mejora la estimación frente a la referencia `media_mun__resp_grupo` y frente a la misma corrección con una sola relación común?

Implementa: Jass. Responsable original de T12: Diego. Revisión metodológica: Migue (pendiente).

**Estado al 16 de octubre de 2026:** evaluación completa corrida (paso 4), controles C2 a C6 hechos (paso 5), auditoría independiente aprobada (paso 6), reproducción en Windows con Docker **idéntica byte a byte** (paso 7), informe y registros de cierre hechos (paso 8). **Resultado R2, señal sin umbral: no se promueve nada y se conserva la referencia.** Pendientes: reproducción en Mac (Dani o Daf) y revisión de Migue.

## Qué hay en esta carpeta

| Archivo | Qué guarda | Estado |
|---|---|---|
| `bitacora.md` | Este documento. | Creado |
| `informe_heterogeneidad_municipal.md` | Informe de cierre en lenguaje sencillo, con preguntas y respuestas y ficha de consumo para T16 y la app. | Creado (paso 8) |
| `borrador_pr.md` | Texto del pull request, listo para pegar. | Creado (paso 8) |

Dónde vive el resto: método en `docs/T12_heterogeneidad_municipal.md`; código en `scripts/t12_*.py`; pruebas en `tests/test_t12_*.py`; resultados en `registro/t12/`. Regla: lo que el equipo ejecuta o consume va en las carpetas del equipo; lo que explica o justifica va aquí.

## Reglas de esta carpeta

- Los nombres dicen lo que contiene cada cosa: minúsculas, guion bajo, sin acentos, sin nombres de persona ni «paso N».
- El dataset original no se copia, no se mueve y no se modifica.
- `scripts/t12_heterogeneidad.py` está **congelado** desde la evaluación: su huella SHA-256 (`3b4f55c7…1717`) está en `registro/t12/comprobaciones.json` y en `manifest.json`. Si cambia, hay que repetir la corrida.
- Los resultados oficiales no se sobrescriben: cada script se detiene si el archivo de salida ya existe.
- Se distingue siempre lo **verificado** de la **sospecha**.

## Plan en pasos

| Paso | Qué se hace | Estado |
|---|---|---|
| 1 | Diseño escrito antes de correr: `docs/T12_heterogeneidad_municipal.md`, `procedimiento_t12.json`, `D_T12_001`, `E_T12_001`–`008` | **Hecho** (15 oct) |
| 2 | Código de los modelos (`het`, `gb`) y pruebas sintéticas | **Hecho** (15 oct) |
| 3 | Comprobaciones con datos reales sin mirar resultados (`comprobaciones.json`) | **Hecho** (15 oct) |
| 4 | Evaluación principal: 8 procedimientos × 50 contextos, escenarios A y B; predicciones exploratorias de las 59 | **Hecho** (15 oct) |
| 5 | Controles C2 a C6: revuelto, curva de aprendizaje, desgloses, qué aprendió el modelo, parcelas extremas | **Hecho** (16 oct) |
| 6 | Auditor independiente | **Hecho** (16 oct) |
| 7 | Reproducción en entorno común y comparador | **Hecho en Windows** (16 oct); Mac pendiente |
| 8 | Informe, bitácora, cierre de experimentos, `D_T12_002`, `IA_T12_002`, borrador del PR | **Hecho** (16 oct) |

## Entradas

### 15 de octubre de 2026 — Pasos 1 a 3: diseño, código y comprobaciones

**Qué se hizo.** Se escribió el diseño antes de tocar etiquetas: un solo candidato promovible (`t12_het_GP`), tres secundarios (`het_G`, `het_P`, `gb_GP`), cuatro controles (tres de «una sola pendiente» y uno con la mediana), la regla de promoción de T03 §4 más el revuelto (p ≤ 0.05), los cinco resultados posibles (R1 a R5) y la **exposición previa** (lo que el equipo ya sabía de T08 a T15 y las correlaciones dentro de los municipios con las mismas 138 parcelas). El código común de T15 (v3, PR #21) se importa sin cambios. Se comprobó con datos reales, sin calcular errores externos, que la referencia reproduce las 1,380 predicciones de T08 y que los controles reproducen el procedimiento v3.

**Qué se esperaba.** Una mejora pequeña, si acaso, de la pendiente por municipio en Chignahuapan, el municipio con más parcelas.

**Estado.** Registrado en `D_T12_001` y `E_T12_001`–`008` antes de correr.

### 15 de octubre de 2026 — Paso 4: evaluación principal

**Qué se hizo.** Se corrieron los 8 procedimientos en los 50 contextos externos (A y B, 5 repeticiones × 5 particiones), con la configuración de cada modelo elegida por validación interna, y se calcularon las 52 comparaciones emparejadas. Se guardaron también las predicciones exploratorias de las 59 reservadas.

**Qué se encontró.** `t12_het_GP` baja el error promedio de 0.3205 a 0.3195 t/ha en A (sin respaldo): −0.0009, IC95 [−0.0066, +0.0047], mejora en 4 de 5 repeticiones. En B empeora (+0.0071). Ninguna promoción.

**Qué se decidió.** Nada todavía: la clasificación final se hace después de los controles.

### 16 de octubre de 2026 — Paso 5: controles C2 a C6

**Qué se hizo.** Con las predicciones ya guardadas se corrieron: **C2 revuelto** (20 mezclas al azar de las variables entre las parcelas etiquetadas del mismo municipio), **C3 curva de aprendizaje** (50 %, 75 % y 100 % del entrenamiento), **C4 desgloses** (por municipio, contorno, tamaño, cuartil de error, y sin las 24 parcelas con alerta de contorno), **C5 qué aprendió** (pendiente por municipio e importancia en el boosting) y **C6 parcelas extremas** (las 20 que más mejoran y las 20 que más empeoran).

**Qué se encontró.**
- C2: ninguna de las 20 mezclas igualó al resultado real (p = 0.0476, el mínimo posible con 20). Las mezclas dieron entre 0.0000 y +0.0030; el real, −0.0009.
- C3: `het_GP` frente a la referencia, +0.0016 con 50 %, +0.0015 con 75 % y −0.0009 con todo. La curva sigue bajando, despacio.
- C4: el cuarto de parcelas con más error mejora (−0.0112), a costa de las fáciles (+0.0065 y +0.0099); el control con una sola pendiente también mejora el cuarto difícil (−0.0071). Sin las 24 con alerta, la mejora baja a −0.0005.
- C5: coeficientes muy pequeños (≈ 0.01) y del mismo signo; Chignahuapan con reglas de más o menos el doble. Importancia del boosting repartida: área (0.056), días sobre la mitad de NDVI (0.040), pendiente (0.035).
- C6: las 40 parcelas extremas cambian entre 0.03 y 0.09 t/ha; 17 de las 20 que más mejoran y 14 de las 20 que más empeoran son de Chignahuapan.

**Qué se decidió.** Clasificar como **R2** (señal sin umbral): `het_GP` mejora en 4 de 5 repeticiones, el IC incluye el cero y C1 es negativa (−0.0006). No se clasifica como R3 porque el MAE también mejora nominalmente y el control común hace lo mismo en la cola.

### 16 de octubre de 2026 — Paso 6: auditor independiente

**Qué se hizo.** `scripts/t12_auditar.py` rehízo, con NumPy y sin importar nada del código de producción, los ajustes de la familia `het` (mínimos cuadrados aumentados resueltos con la ecuación normal, no `Ridge`), la selección interna, las métricas, los ΔMAE con su IC95 y los controles C2 a C6. Comparte con la producción solo lo declarado en el diseño: la semilla y el sorteo del remuestreo de celdas, y las particiones internas de scikit-learn.

**Qué se encontró.** **Auditoría aprobada.** Diferencia máxima en predicciones 1.8e-15 (5,520 comparadas, 200 selecciones reconstruidas), en métricas 2.2e-16 (240 filas) y en comparaciones 2.2e-16 (52). Los controles coinciden con diferencia máxima 1.8e-15.

**Qué significa.** Los números están bien calculados. No dice nada sobre la calidad del modelo.

### 16 de octubre de 2026 — Paso 7: reproducción y comparador

**Qué se hizo.** Se escribió `scripts/t12_reproducir.py`, que compara una carpeta de reproducción contra `registro/t12/` con el criterio de T15 (`atol = 1e-12`, `rtol = 1e-10`), alineando las tablas por sus claves (no por posición), verificando que el manifest describa lo mismo (diseño, código, entradas) y que cada contexto elija la misma opción. Tiene 47 pruebas sintéticas y se comprobó con 24 fallas introducidas a propósito (se detectaron las 24). Después Jass volvió a correr toda la evaluación en `reports/t12_repro` con Docker sobre Windows.

**Qué se encontró.** **Idéntica byte a byte** en los 5 archivos (11,040 / 4,400 / 240 / 52 / 472 filas); 400 de 400 selecciones coinciden.

**Qué significa.** El resultado se repite sin variación con el mismo código, las mismas entradas y la misma imagen Docker. **Todavía no prueba que salga igual en otra máquina**: falta Mac. Si allí el comparador marca «contextos con otra opción», no es ruido numérico, es un desempate distinto y hay que investigarlo.

**Límite.** El comparador solo cubre lo que escribe `t12_evaluar.py`; los controles C2 a C6 ya los reconstruyó el auditor independiente.

### 16 de octubre de 2026 — Paso 8: informe y registros

**Qué se hizo.** Se escribió el informe de cierre en lenguaje sencillo (formato de T10), esta bitácora y el borrador del PR. Se cerraron `E_T12_001` a `E_T12_008` con sus métricas y conclusión; se agregaron `D_T12_002` (cierre) e `IA_T12_002` (uso de IA de los pasos 2 a 8) y se actualizó la línea de estado del documento de método. Todas las cifras del informe se recalcularon contra los CSV de `registro/t12/`.

**Una corrección del camino.** Durante la redacción se dijo, a partir de las 40 parcelas extremas, que en Chignahuapan los rendimientos van de 3.7 a 5.6 t/ha. Al verificar con las 71 parcelas etiquetadas, el rango real es de 2.15 a 5.59 t/ha. El informe usa el valor correcto.

**Ideas que se hablaron y no son decisiones.** (a) La **mediana** como observación de referencia rindió menos error en A y B (T08 ya lo había visto sin cumplir la regla): nota para T16, no decisión de T12. (b) Posibles frentes nuevos, cada uno como tarea propia con su regla escrita antes de correr: Tmax centrada con Planet, fenología fina (inicio, pico y senescencia del verdor) con las series de Planet y Sentinel-2 que ya están en el repo, e índices de borde rojo de Sentinel-2 (requieren descargar las bandas B5 a B7, que el dataset de FIRA no trae); Sentinel-1 queda para después. Antes de invertir, conviene un diagnóstico del «techo»: cuánto difieren en rendimiento parcelas vecinas casi iguales en todo lo que medimos.

**Estado.** `IA_T12_002`. Cambios documentales y de registro locales, pendientes de revisión humana; sin cambios de modelo ni de resultados numéricos.

### 16 de octubre de 2026 — Auditoría de los cambios posteriores de T15

**Por qué.** T15 (la rama sobre la que se apoya T12) siguió avanzando después de nuestro punto de partida (`4afabf0`). `D_T12_001` dice que T12 se reabre si `scripts/evaluacion_comun_*` cambia en la revisión del PR #21, así que había que comprobarlo.

**Qué se hizo.** Se bajó `origin/t15-centrado-municipal` (ahora en `cc7d0ae`: 12 commits propios más un merge de `dev` con T14) y se comparó contra `4afabf0`, sin tocar `registro/t12/` ni el código congelado. Se revisó: (a) las huellas de todo lo que fija `manifest.json`; (b) los archivos que T12 importa; (c) los documentos nuevos (contraste LOO de alertas, revisión del PR #22, contrato y ejecutor de T15); (d) si las cifras ajenas coinciden con las nuestras; (e) si la rama se puede fusionar sin choques de IDs.

**Qué se encontró.**
- **Nada de lo que T12 usa cambió.** Los 14 archivos comunes de código y datos que fija T12 son idénticos (código v3, `tabla_comun`, particiones, soporte, referencias de T03, procedimiento v3). Los 57 archivos cambiados son todos nuevos o documentos; ningún script ni prueba previo fue modificado. La condición de reapertura de `D_T12_001` **no se cumple**. Los resultados, R2 y la reproducción en Windows siguen válidos; no se repitió la corrida porque mismo código y mismas entradas dan las mismas salidas.
- **Coinciden cifras de terceros.** T14 (Migue) reporta la referencia 0.3192 en A y 0.3801 en B («todas»), igual que `metricas_t12.csv`; la revisión del PR #22 da 0.3205 en A/sin_respaldo y 659 registros en B, iguales a los nuestros. Nuestro desempate coincide con el que el PR #22 pide dejar escrito.
- **Nuestros tres controles son el menú principal de T15.** `control_comun_G`, `_P` y `_GP` tienen exactamente las mismas opciones que los procedimientos G, P y G+P del contrato de T15. T12 ya midió esas comparaciones (A/sin_respaldo: +0.0032, +0.0025 y −0.0003; ninguna cumple la regla). Consecuencias: T15 ya no es ciego para esos tres, y su corrida completa debería reproducir `registro/t12/` exactamente.
- **Falta de unidad en B.** Los `dMAE` son por parcela; en B la referencia vale 0.3579 (promedio de MAE por repetición), 0.3584 (por registro) o 0.3632 (por parcela). El signo de `gb_GP` en B cambia según la ponderación (−0.0007 por parcela, +0.0005 por repetición): es cero en la práctica. En A las tres ponderaciones coinciden.
- **Fusión.** Mi rama y la T15 nueva cambian al final los mismos tres registros (`decisiones.csv`, `experimentos.csv`, `uso_ia.csv`): choques de texto, sin IDs repetidos.

**Qué se decidió.** Dejar los resultados como están. En el informe y el borrador del PR se aclaran las unidades, se describe la coincidencia con el menú de T15 **como información** (T15 cerró su menú y `D_T15_EJECUTOR_001` rechaza alterarlo) y se quita la frase que pedía no incluir el bloque G.

**Límites.** No hubo acceso a GitHub: se revisaron commits, no comentarios de los PR. T15 aún no corrió su evaluación completa. Si T15 cambia más adelante, las compuertas de huellas de `t12_evaluar.py` lo detectan antes de correr.

### 16 de octubre de 2026 (noche) — Observaciones de revisión

**Qué llegó.** Tres observaciones sobre el borrador del PR: (1) acotar las conclusiones, (2) corregir la explicación de los árboles, (3) conciliar el estado de la revisión de Migue. Las tres se revisaron contra nuestros archivos y se aceptaron; ninguna cambia un resultado.

**Qué se cambió.**
- **Conclusión acotada.** «Se descarta que la forma del modelo sea la causa» pasó a «con estas dos formas de modelo (regla por municipio con Ridge y árboles de profundidad 2) no se logra una mejora suficiente»; no descarta otras formas ni otras variables. Con unas 110 parcelas por entrenamiento, los árboles son una prueba débil de «no lineal».
- **`init='zero'`.** `init='zero'` solo fija en cero el punto de partida de las predicciones; después las hojas de los árboles sí pueden aprender un desplazamiento constante, a diferencia del Ridge, que no tiene intercepto. Por eso los árboles tuvieron un poco más de libertad que las demás familias. Se midió el efecto: el desplazamiento medio de `gb_GP` frente a la referencia es +0.0015 t/ha en A y +0.0001 en B, así que no aprendió un sesgo sistemático, y aun con esa libertad no mejora a la referencia. No es una fuga de datos. El diseño (§5.2) y el comentario del código decían lo contrario. Como el diseño y el código están fijados antes de correr, **no se reescribieron**: se agregó una nota con fecha en el documento de diseño y se explica en el informe y el PR. El comentario del código queda como está porque cambiarlo cambia la huella y las compuertas se negarían a correr.
- **Estado de la revisión.** La condición 6 de las barreras («Migue revisó este diseño») **no se había cumplido** cuando se corrió con `--confirmo-barreras` el 15 de octubre: Jass confirmó las barreras sin una revisión previa de Migue. Migue todavía no revisó ni el diseño ni los resultados. Los resultados son válidos para el diseño tal como se registró, pero esa revisión puede pedir cambios; hasta entonces hay que leerlos como condicionales a ella.

## Pendientes

1. Reproducción en Mac (Dani o Daf): `python -m scripts.t12_evaluar --salida reports/t12_repro --confirmo-barreras --procesos 2` y luego `python -m scripts.t12_reproducir --reproduccion reports/t12_repro --etiqueta "Mac"`, con `--amd64` si se quiere comparar contra Linux amd64.
2. Revisión metodológica de Migue: aún no revisó ni el diseño ni los resultados (la barrera 6 se confirmó sin su revisión). Puntos a revisar: diseño no ciego, 13 comparaciones, IC nominales y la corrección de `init='zero'`.
3. Fusionar `origin/t15-centrado-municipal` en esta rama (conservar las dos partes en los tres registros) y abrir el PR con `borrador_pr.md`.
4. Avisar a Dani que T12 ya midió G, P y G+P con las mismas opciones que su menú, para su registro de exposición previa y como comprobación cruzada.
