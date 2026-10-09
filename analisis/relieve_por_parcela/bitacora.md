# Bitácora de la extracción de relieve por parcela (T05)

> **Nota para el equipo.** Esta es la bitácora de trabajo, en orden cronológico: qué se hizo en cada paso, qué se esperaba, qué se encontró y qué se decidió. El método está en [`docs/t05_relieve.md`](../../docs/t05_relieve.md). Los datos compartidos irán en `registro/t05/`; esta carpeta guarda la evidencia que los explica. Cada paso cierra con un breve informe con la misma estructura.

**Pregunta que debe quedar contestada:** ¿qué elevación y qué pendiente tiene cada una de las 197 parcelas, con qué cobertura de dato y con qué confianza?

Responsable: Jass. Revisora: Dani.

**Estado al 8 de octubre de 2026:** método congelado; funciones de extracción listas y cubiertas por 30 pruebas sintéticas. Falta la ejecución con los datos reales y el cierre.

## Qué hay (y qué habrá) en esta carpeta

| Archivo | Qué guarda | Estado |
|---|---|---|
| `bitacora.md` | Este documento. | Creado |
| `README.md` | Entrada corta para el equipo. | Se añade al subir la evidencia |
| Informe de calidad, casos de borde, sensibilidad | Evidencia que explica los datos compartidos. | Se crea cuando haya resultados |

Dónde vive el resto: código en `scripts/t05_relieve.py`, pruebas en `tests/test_t05_relieve.py`, tablas compartidas en `registro/t05/`. Regla: lo que el equipo ejecuta o consume va en las carpetas del equipo; lo que explica o justifica va aquí. Esta carpeta apunta a los datos y no los duplica.

## Reglas de esta carpeta

- Los nombres dicen lo que contiene cada cosa: minúsculas, guion bajo, sin acentos, sin nombres de persona ni «paso N».
- El dataset original no se copia, no se mueve y no se modifica.
- Las carpetas se crean cuando se necesitan.
- Se distingue siempre lo **verificado** de la **sospecha**.

## Plan en pasos

| Paso | Qué se hace | Estado |
|---|---|---|
| 1 | Documento del método y estructura de archivos | **Hecho** (8 oct) |
| 2 | Esqueleto de `scripts/t05_relieve.py` con funciones puras | **Hecho** (8 oct) |
| 3 | Pruebas formales con datos sintéticos | **Hecho** (8 oct) |
| 4 | Ejecución real: `relieve_parcela.csv` y `relieve_celdas.csv` (197 parcelas) | Pendiente |
| 5 | Controles sobre datos reales: T02, cálculo independiente, 5 parciales, 59 reservadas completas | Pendiente |
| 6 | Procedencia, controles, manifiesto y `--verificar`, con fin de línea LF | Pendiente |
| 7 | Registros, PR con la plantilla y reproducción por Dani | Pendiente |
| 8 | Ampliación opcional: tabla de sensibilidad | Pendiente |
| Final | Cotejo mínimo en QGIS (2–3 celdas de 2–3 parcelas y las 5 parcelas incompletas), **antes** de dar T05 por «Hecha» | **Acordado** (8 oct) |

## Bitácora

### 8 de octubre de 2026 — Paso 1: método y estructura

**Qué se hizo.**
- Se verificó en solo lectura cómo están construidos los TIFF de relieve (INEGI CEM4, EPSG:6372, celdas de 120 m, NoData −9999). La máscara de la pendiente entregada coincide con la exigencia de las nueve celdas de elevación válidas, incluso en los bordes del mapa: cero discrepancias. No se rellenaron bordes.
- Se contrastó la cobertura de las cinco parcelas incompletas (AGC_020, 023, 044, 164 y 170) con un cálculo independiente: coincide con la tabla de T02.
- Se escribió `docs/t05_relieve.md` y se revisó en tres rondas (dos revisiones de un segundo asistente de IA y la del asistente principal). Las correcciones se aplicaron con criterio, no en bloque.
- Se registró D020 en `registro/decisiones.csv`: referencia = promedios de los TIFF originales con cobertura, celdas y avisos; piso de 0.5 solo para la pendiente en T10; relleno y plano ajustado solo como sensibilidad.
- Se compararon tres estructuras de carpetas y se eligió la híbrida: código y pruebas del equipo, tablas en `registro/t05/`, evidencia aquí.

**Qué se encontró (verificado).**
- Solo 5 de 197 parcelas tienen cobertura incompleta, todas de **entrenamiento**; las 59 reservadas tienen 100 %.
- La pendiente pierde el triple de ancho que la elevación (ventana 3×3). Ejemplo: AGC_023 conserva 96 % de elevación pero solo 29 % de pendiente.
- El efecto de calcular áreas planas en lugar de físicas es despreciable: la media cambia menos de 0.0001 m en elevación y menos de 0.00001° en pendiente.
- Entre el valor por área y el del centroide hay diferencias no despreciables en pendiente (mediana 0.22°, p95 1.35°, máximo 3.05°), lo que justifica la tabla O6.
- Un desajuste de altura de 1–3 m entre los lados de la costura es del mismo orden que la pendiente de estas parcelas (0.3° a 1.7°). El relleno no puede decidir cuál pendiente es la correcta.

**Sospecha, no comprobada.** La costura NoData cerca de AGC_164, 170 y 023 corre en diagonal y separa parcelas de Tlaxcala y de Hidalgo, lo que sugiere una unión entre mapas estatales. No se comprobó con una capa oficial de límites.

**Decisiones de Jass.** El método queda congelado; los cambios posteriores deben responder a un fallo reproducible, una prueba o un requisito incumplido. Estructura híbrida. Las columnas de mínimo y máximo se incluyen como auditoría. Comparar áreas planas con físicas es un control, no una decisión de método.

### 8 de octubre de 2026 — Informe del paso 2: funciones de extracción

**Qué se hizo.** Se escribió `scripts/t05_relieve.py` (184 líneas) con funciones puras: soporte de celdas por parcela, comprobación de áreas, resumen de una variable, piso de la pendiente para T10, valor en el centroide y avisos. No lee archivos ni usa los TIFF reales; se probó con mapas inventados de 1 a 2 celdas, de respuesta conocida.

**Qué se esperaba.** Que el código hiciera lo que dice el método: promediar por área solo con celdas válidas, dar el estado correcto en cada caso, aplicar el piso de 0.5 sin redondear y detenerse si faltan celdas.

**Qué se encontró (verificado, comprobación a mano).**
- 80 % en una celda de 100 y 20 % en una de 200 da **120**, no 150: pondera por área.
- Con la segunda celda sin dato: media 100, cobertura 0.8, estado parcial.
- Mitad de la parcela fuera del mapa: cobertura 0.5. Totalmente fuera: `sin_cobertura_espacial`, valores vacíos. Todo NoData: `todo_nodata`.
- Una celda que solo toca el borde no cuenta.
- Piso: 0.5 exacto da valor; 0.4999… da vacío.
- Si se omite una celda a propósito, el control de áreas detiene la ejecución («Suma de intersecciones distinta del área directa»).
- Un CRS distinto al del ráster se rechaza.

**Decisión de este paso.** A diferencia de T04, una parcela sin cobertura espacial o con todo NoData **no detiene el programa**: recibe un estado y valores vacíos, para que una parcela problemática no impida extraer las otras 196.

**Qué no demuestra todavía.** Nada sobre los datos reales (pasos 4 y 5). La prueba fue a mano, no un archivo repetible por Dani (paso 3). Corrió en un entorno con Python 3.10; el repositorio está fijado para 3.12, así que las pruebas formales deben correrse también allí.

**Lo que sigue.** Paso 3: convertir estos casos y los que faltan en `tests/test_t05_relieve.py`.

### 8 de octubre de 2026 — Cotejo en QGIS acordado

**Decisión de Jass.** El cotejo mínimo en QGIS forma parte del cierre de T05: se hace al final, antes de dar la tarea por «Hecha». Motivo: todas las demás comprobaciones usan las mismas bibliotecas (`rasterio`, `pyproj`, `shapely`); QGIS es el único control con otro programa y otra lectura del archivo, y protege de un error común a todas, como un desfase de fila o columna. Se añadió a `docs/t05_relieve.md`.

### 8 de octubre de 2026 — Informe del paso 3: pruebas formales

**Qué se hizo.** Se escribió `tests/test_t05_relieve.py` (30 pruebas) con la misma convención que T04: `unittest`, rásters en memoria con `MemoryFile` e importación desde `scripts.`. Cada prueba fabrica un mapa de 1 a 4 celdas en EPSG:6372 con valores elegidos, de modo que el resultado correcto se calcula a mano. Están agrupadas por tema: áreas y bordes (6), comprobación de áreas (4), NoData y cobertura (5), piso de la pendiente (3), centroide (2), avisos (3) y errores que deben detener la ejecución (7).

**Qué se esperaba.** Que las funciones del paso 2 pasaran todas, y que los casos nuevos (multipolígono con hueco, parcela menor a una celda, cuadrícula rotada o geográfica, valor no finito) se comportaran según el método.

**Qué se encontró (verificado).**
- **Las 30 pruebas pasan**, y la suite completa del repositorio también (98 pruebas: 68 existentes y 30 nuevas). Las de T05 pasan aun tratando los avisos de obsolescencia como errores.
- **Al diseñar las pruebas apareció una debilidad en el código del paso 2 y se corrigió:** `comprobar_areas` confiaba en el total de área guardado en lugar de volver a sumar las celdas, y no detectaba de forma explícita una celda repetida. Ahora vuelve a sumar desde la lista y rechaza duplicados. Dos pruebas (`test_celda_duplicada_detectada` y `test_total_guardado_alterado_detectado`) lo cubren.
- **Se ajustó la forma de aplicar la transformación del mapa** (`t @ (x, y)` en lugar de `t * (x, y)`), que es la de T04 y la que acepta sin aviso la versión de `affine` fijada en el repositorio.
- Una regla que quedó fija y probada: si el centroide cae exactamente en el borde entre dos celdas, se toma la de la derecha (o la de abajo). Es determinista y no interpola.

**Qué no demuestra todavía.** Que el método aplicado a los TIFF reales dé lo esperado (pasos 4 y 5). Las pruebas corrieron con Python 3.10; el repositorio está fijado para 3.12, así que conviene repetirlas en ese entorno.

**Cómo repetirlas.** Desde la raíz del repositorio: `python -m unittest discover -s tests -v`.

**Lo que sigue.** Paso 4: leer los TIFF y el shapefile, extraer las 197 parcelas y escribir `relieve_parcela.csv` y `relieve_celdas.csv`.

