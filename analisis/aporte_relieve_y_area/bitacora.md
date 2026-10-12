# Bitácora de la evaluación de relieve y área (T10)

> **Nota para el equipo.** Bitácora de trabajo en orden cronológico: qué se hizo en cada paso, qué se esperaba, qué se encontró y qué se decidió. El método está en [`docs/T10_relieve_area.md`](../../docs/T10_relieve_area.md) y la decisión de diseño en `D_T10_001` (`registro/decisiones.csv`). Los resultados compartidos están en `registro/t10/`; esta carpeta guarda la evidencia que los explica.

**Pregunta que debe quedar contestada:** ¿conocer la elevación, la pendiente y el tamaño de una parcela mejora la estimación que da el promedio de su municipio, y esa mejora se sostiene en parcelas pequeñas o con cobertura parcial?

Responsable: Jass. Revisora: Daf.

**Estado al 12 de octubre de 2026:** diseño escrito antes de correr, código y pruebas listos, diagnóstico sin rendimientos hecho. Todavía no se ha corrido ninguna configuración con datos reales.

## Qué hay (y qué habrá) en esta carpeta

| Archivo | Qué guarda | Estado |
|---|---|---|
| `bitacora.md` | Este documento. | Creado |
| Diagnóstico exploratorio con rendimientos, gráficos | Pearson de cada variable con el rendimiento, global y dentro de municipio. Exploratorio: no decide nada. | Se crea después de evaluar |
| Informe de cierre | Resultado de T10 en lenguaje sencillo. | Se crea al final |

Dónde vive el resto: método en `docs/T10_relieve_area.md`, código en `scripts/t10_relieve_area.py`, pruebas en `tests/test_t10_relieve_area.py`, resultados en `registro/t10/`. Regla: lo que el equipo ejecuta o consume va en las carpetas del equipo; lo que explica o justifica va aquí.

## Reglas de esta carpeta

- Los nombres dicen lo que contiene cada cosa: minúsculas, guion bajo, sin acentos, sin nombres de persona ni «paso N».
- El dataset original no se copia, no se mueve y no se modifica.
- Las carpetas se crean cuando se necesitan.
- Se distingue siempre lo **verificado** de la **sospecha**.

## Plan en pasos

| Paso | Qué se hace | Estado |
|---|---|---|
| 1 | Limpieza de la rama: integrar el entorno común (Docker) y fin de línea LF | **Hecho** (12 oct) |
| 2 | Actualizar documentos de T05 (bitácora y pendiente P05) | **Hecho** (12 oct) |
| 3 | Diseño escrito antes de correr: `docs/T10_relieve_area.md` y `D_T10_001` | **Hecho** (12 oct) |
| 4 | Código y pruebas sintéticas; comprobar que la referencia reproduce T08 | **Hecho** (12 oct) |
| 5 | Diagnóstico de atributos sin rendimientos | **Hecho** (12 oct) |
| 6 | Ejecución: 6 configuraciones × (principal y puente), escenarios A y B; regla de T03 | Pendiente |
| 7 | Desgloses por tamaño, cobertura y contorno; sensibilidad sin las 24; revuelto si aplica; predicciones de las 59 | Pendiente |
| 8 | Diagnóstico exploratorio con rendimientos (Pearson y gráficos) | Pendiente |
| 9 | Informe de cierre y registros (`E_T10_001`–`006`, `IA_T10_001`) | Pendiente |
| 10 | Reproducción (dos corridas idénticas, Docker) y borrador del PR para Daf | Pendiente |

## Bitácora

### 12 de octubre de 2026 — Diseño escrito antes de correr (paso 3)

**Qué se esperaba.** Fijar la pregunta, las entradas, el procedimiento, las configuraciones y la regla de decisión antes de ver ningún resultado, para que el resultado no pueda cambiar el criterio.

**Qué se hizo.** `docs/T10_relieve_area.md` y la fila `D_T10_001`. Se declaró por escrito lo que ya se había visto de relieve y área con las 138 etiquetas durante la comprensión del dataset (pendiente +0.26 y log del área −0.25 dentro de municipio, permutación p = 0.22) y el hallazgo de T02 sobre tamaño en Chignahuapan.

**Decisiones.**
- Procedimiento principal = el de T11 v2 con dos cambios: opción «referencia sola» en la selección interna (O7) y α elegido por error absoluto (la métrica primaria de T03 es el MAE).
- Procedimiento puente = T11 v2 exacto, sólo descriptivo: nunca decide ni consume presupuesto (consulta enviada a Migue sobre esta lectura de T03 §5).
- 6 configuraciones de 8; las 2 restantes no se usan y no se agregan después de ver resultados.
- Control de revuelto (20, dentro de municipio) sólo si alguna configuración cumple la regla.

### 12 de octubre de 2026 — Código y pruebas (paso 4)

**Qué se esperaba.** Un script que haga exactamente lo de `D_T10_001` y pruebas que demuestren que nada de la evaluación se filtra al entrenamiento.

**Qué se hizo.** `scripts/t10_relieve_area.py` (modos `--comprobar-referencia`, `--diagnostico` y `--evaluar`; ninguno sobrescribe archivos) y 13 pruebas sintéticas en `tests/test_t10_relieve_area.py`.

**Qué se comprobó.**
- 13 de 13 pruebas nuevas y 266 de 266 en la suite completa.
- La referencia de T10 reproduce las 1,380 predicciones de T08 (diferencia máxima 8.9e-16) con las mismas fuentes de respaldo (15 en A, 31 en B).
- El puente elige el mismo α que el código real de T11 v2 en 100 de 100 casos (configuraciones 1 y 3, las 50 particiones). Para eso se corrió la selección de α con datos reales; sólo se compararon los α elegidos, no se calculó ni se miró ningún error.

**Qué no se comprobó.** Que el puente coincida con T11 v2 en las configuraciones con pendiente (2, 4, 5 y 6): el código de T11 no admite faltantes.

### 12 de octubre de 2026 — Diagnóstico de atributos sin rendimientos (paso 5)

**Qué se esperaba.** Saber, sin mirar rendimientos, cuánto de cada variable es «ubicación», cuánto se parecen entre sí y si las 59 reservadas caen dentro de lo que el modelo verá al entrenar.

**Qué se hizo.** `python -m scripts.t10_relieve_area --diagnostico --salida registro/t10`, que escribe `registro/t10/diagnostico_atributos_t10.csv`. Sólo usa municipio y las tres variables.

**Qué se encontró (comprobado, 138 etiquetadas).**

| Variable | Parte explicada por el municipio | Faltantes |
|---|---|---|
| Elevación | 28 % | 0 |
| Pendiente (D020) | 13 % | 2 (AGC_023 y AGC_170) |
| Log del área | 15 % | 0 |

- Correlaciones entre variables: elevación–pendiente 0.51; pendiente–log del área −0.30; elevación–log del área −0.09. Con las 197 parcelas el patrón es el mismo (0.45, −0.27 y −0.04).
- Las tres variables son en su mayor parte variación **dentro** de cada municipio, no un sustituto de la ubicación. Eso permite que puedan aportar algo sobre la referencia municipal; no demuestra que lo hagan.
- Elevación y pendiente comparten información (0.51): por eso la configuración 4 las junta y las configuraciones 1 y 2 las prueban por separado.

**Corrección al documento del método.** El documento decía que el municipio explica el 53 % del área. Ese valor es del área **sin** logaritmo; la entrada del modelo es el logaritmo, y para él la cifra es 15 %. La diferencia la causan unas pocas parcelas grandes concentradas en pocos municipios. Se corrigió `docs/T10_relieve_area.md` §3. No cambia el diseño: el logaritmo ya estaba decidido por la forma de la distribución, no por esta cifra.

**Reservadas fuera del rango etiquetado.** Tres, cada una en una sola variable y por muy poco: AGC_088 en elevación (2,906.0 m frente a un máximo de 2,904.0 m), AGC_153 en pendiente (0.282° frente a un mínimo de 0.288°) y AGC_091 en área (0.35 ha frente a un mínimo de 0.38 ha). No es una extrapolación relevante; se anota para el aviso de la app (T17). El documento del método decía que sólo había un caso (elevación); se corrigió.

**Qué no dice este diagnóstico.** Nada sobre si las variables ayudan a predecir: eso se mide en el paso 6, con la regla de T03.
