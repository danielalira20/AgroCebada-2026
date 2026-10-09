# Bitácora de la extracción de relieve por parcela (T05)

> **Nota para el equipo.** Esta es la bitácora de trabajo, en orden cronológico: qué se hizo en cada paso, qué se esperaba, qué se encontró y qué se decidió. El método está en [`docs/t05_relieve.md`](../../docs/t05_relieve.md). Los datos compartidos irán en `registro/t05/`; esta carpeta guarda la evidencia que los explica. Cada paso cierra con un breve informe con la misma estructura.

**Pregunta que debe quedar contestada:** ¿qué elevación y qué pendiente tiene cada una de las 197 parcelas, con qué cobertura de dato y con qué confianza?

Responsable: Jass. Revisora: Dani.

**Estado al 8 de octubre de 2026:** método congelado; extracción real de las 197 parcelas hecha, cubierta por 37 pruebas y aprobada en los controles sobre datos reales. Publicado en `registro/t05/` con manifiesto y verificación. Faltan los registros y el PR, la revisión de Dani y el cotejo en QGIS.

## Qué hay (y qué habrá) en esta carpeta

| Archivo | Qué guarda | Estado |
|---|---|---|
| `bitacora.md` | Este documento. | Creado |
| `README.md` | Entrada corta para el equipo. | Se añade al subir la evidencia |
| `scripts/calcular_relieve_independiente.py` | Cálculo independiente para conciliar con T05, por otro camino de código. | Creado (paso 5) |
| `tablas/conciliacion_calculo_independiente.csv` | Comparación parcela por parcela entre T05 y el cálculo independiente. | Creado (paso 5) |
| `tablas/casos_de_borde.csv` | Las 29 parcelas con algún aviso, con conjunto y municipio. | Creado (paso 5) |
| Informe de calidad, sensibilidad | Evidencia que explica los datos compartidos. | Se crea cuando haya resultados |

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
| 4 | Ejecución real: `relieve_parcela.csv` y `relieve_celdas.csv` (197 parcelas) | **Hecho** (8 oct) |
| 5 | Controles sobre datos reales: T02, cálculo independiente, 5 parciales, 59 reservadas completas | **Hecho** (8 oct) |
| 6 | Procedencia, controles, manifiesto y `--verificar`, con fin de línea LF | **Hecho** (8 oct) |
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

### 8 de octubre de 2026 — Informe del paso 4: extracción real

**Qué se hizo.** Se añadió a `scripts/t05_relieve.py` la lectura de archivos y la línea de comandos. Lee el shapefile (`ID_POLIGON` → `id_parcela`), lo reproyecta a EPSG:6372, comprueba que los dos TIFF comparten cuadrícula, CRS y NoData, extrae cada parcela y escribe dos CSV con fin de línea LF y números sin redondear. Solo escribe si todo pasó los controles que detienen la entrega, y se niega a sobrescribir una carpeta con contenido. Siguiendo a T04, la salida va primero a `data/processed/t05/<ejecucion>/` (ignorada por Git); la publicación en `registro/t05/` es el paso 6. Se agregaron 3 pruebas de punta a punta con un shapefile y dos TIFF diminutos (33 en total, todas pasan).

Orden usado, desde la raíz del repositorio:

    python -m scripts.t05_relieve --extraer --salida data/processed/t05/primera_extraccion

**Qué se esperaba.** 197 IDs únicos, sin errores; cinco parcelas con cobertura incompleta (cuatro en ambas variables y AGC_044 solo en pendiente); AGC_023 y AGC_170 bajo el piso de 0.5; tres centroides fuera de su parcela.

**Qué se encontró (verificado).**
- 197 parcelas, 197 IDs únicos, 26 columnas; 2 253 filas de celdas. Tiempo: unos 7 segundos.
- Estados: 192 completas en ambas variables; 4 parciales en ambas (AGC_020, 023, 164 y 170); 1 completa en elevación y parcial en pendiente (AGC_044). Ninguna `todo_nodata` ni `sin_cobertura_espacial`.
- Coberturas de las cinco: elevación 0.9783 / 0.9590 / 1.0000 / 0.9506 / 0.7594 y pendiente 0.6525 / 0.2864 / 0.9803 / 0.5527 / 0.0210 (AGC_020, 023, 044, 164, 170). Coinciden con lo calculado antes.
- `pendiente_media_t10_grados` queda vacía exactamente en AGC_023 y AGC_170; el valor original se conserva en `pendiente_media_grados`.
- Centroide fuera de la parcela: AGC_078, AGC_152 y AGC_182, las mismas que reporta T04. Tres centroides sin dato de pendiente.
- Coherencia interna: el número de celdas por parcela coincide entre las dos tablas, y la suma de áreas por celda difiere del área de la parcela como máximo en 3 × 10⁻¹² (relativo).
- Rangos: elevación media de 2 497 a 2 906 m; pendiente media de 0.28° a 9.40°.
- Avisos: `parcela_menor_a_una_celda` 18, `pocas_celdas_validas` 17, `cobertura_parcial_pendiente` 5, `cobertura_parcial_elevacion` 4, `pendiente_bajo_piso_50` 2, `centroide_fuera_de_parcela` 3, `centroide_sin_dato_pendiente` 3.

**Diferencia explicada.** Antes se dijo que 17 parcelas medían menos de 1.44 ha; el aviso marca 18. La diferencia es AGC_032: el catálogo le da 1.44 ha (redondeado a dos decimales, justo en el límite) y en EPSG:6372 mide 1.426 ha, porque el área plana es un 0.7 % menor. El aviso compara la parcela con una celda de 120 m × 120 m en el mismo sistema, así que 18 es lo coherente. No es un error.

**Qué no demuestra todavía.** La conciliación formal con T02 y con un cálculo independiente, la comprobación de que las 59 reservadas están completas y la comparación de áreas planas contra físicas son el paso 5. Las medias de pendiente de las parcelas parciales difieren algo de unas estimaciones rápidas hechas antes con un método aproximado (subdivisión de celdas); se concilian contra el cálculo exacto en el paso 5.

**Incidente menor.** Al preparar las pruebas se creó por accidente un archivo vacío, `tests/test_t05_relieve.py.tmp`, que el asistente no puede borrar. No afecta a las pruebas; debe borrarse a mano.

**Lo que sigue.** Paso 5: controles sobre los datos reales.

### 8 de octubre de 2026 — Informe del paso 5: controles sobre datos reales

**Qué se hizo.**
- Se añadió a `scripts/t05_relieve.py` el modo `--controlar`. Lee los CSV escritos (lo que usará el equipo) y escribe `controles.json` junto a ellos con: IDs frente al catálogo de T02, coherencia entre las dos tablas, que las 59 reservadas estén completas, conciliación de coberturas con T02 y comparación de pesos de área plana frente a física. Se agregaron 4 pruebas (37 en total, todas pasan).
- Se escribió un cálculo independiente reproducible, `scripts/calcular_relieve_independiente.py` en esta carpeta, por otro camino de código: lee el shapefile con `pyogrio` sin `geopandas`, reproyecta los vértices a mano con `pyproj`, calcula las intersecciones de forma vectorizada y **lee cada valor por la coordenada del centro de su celda**, no por fila y columna. El resultado está en `tablas/conciliacion_calculo_independiente.csv`.
- Se armó `tablas/casos_de_borde.csv` con las parcelas que tienen algún aviso.

Órdenes usadas, desde la raíz del repositorio:

    python -m scripts.t05_relieve --controlar --salida data/processed/t05/primera_extraccion
    python analisis/relieve_por_parcela/scripts/calcular_relieve_independiente.py --t05 data/processed/t05/primera_extraccion/relieve_parcela.csv --salida analisis/relieve_por_parcela/tablas/conciliacion_calculo_independiente.csv

**Qué se esperaba.** Los 197 IDs del catálogo; las 59 reservadas completas; coberturas iguales a las de T02 dentro del redondeo a cuatro decimales; un cálculo independiente que coincida; y diferencias despreciables entre áreas planas y físicas.

**Qué se encontró (verificado).**
- **Resultado de los controles: `aprobado`, sin avisos.** 197 parcelas, IDs idénticos al catálogo de T02; las 59 reservadas tienen cobertura completa en elevación y pendiente.
- **T02:** diferencia máxima de cobertura 0.000047, dentro de la tolerancia de 0.00005; ninguna discrepancia.
- **Cálculo independiente:** las medias difieren como máximo 9 × 10⁻¹³ m en elevación y 3 × 10⁻¹⁵° en pendiente; las coberturas, 2 × 10⁻¹²; y el número de celdas intersectadas y válidas coincide en las 197 parcelas. Como lee por coordenada, también descarta un desfase de fila o columna en la extracción principal.
- **Tablas:** el área de las celdas suma el área de la parcela con un error relativo máximo de 3 × 10⁻¹².
- **Áreas plana frente a física:** las medias cambian como máximo 0.00006 m (elevación) y 0.000007° (pendiente). La cobertura difiere hasta 0.00003 (mediana 0.0000004); la diferencia no viene de los pesos, sino de que un borde recto en EPSG:6372 no es exactamente recto en latitud y longitud, y al sumar pedazos en el otro sistema la suma no cierra perfecto. El máximo aparece en AGC_073, una franja delgada. El documento del método decía «menos de 0.000002», medido con otro denominador, y se corrigió.
- **Casos de borde:** 29 parcelas con algún aviso, 22 de entrenamiento y 7 reservadas. **Ninguna de las 7 reservadas tiene datos faltantes**; sus avisos son de resolución espacial (5 menores a una celda, 3 con 4 celdas válidas o menos) y AGC_182 tiene el centroide fuera de su contorno. En esas 7, el relieve resume muy pocas celdas.

**Dos errores encontrados y corregidos en este paso.**
- El primer intento del cálculo independiente trataba como válidos los valores sin dato (al convertirlos a número se perdía su marca). Lo delataron coberturas absurdas, de hasta 0.98 de diferencia. Se corrigió y el resumen ahora deja ver cualquier `NaN` en lugar de esconderlo.
- Unas «estimaciones rápidas» de pendiente mencionadas en el paso 4 diferían de T05 entre 0.004° y 0.06°. Venían de un método aproximado (subdividir cada celda en 8 × 8 puntos) que pierde precisión donde hay pocas celdas válidas: AGC_023 tiene 4 y AGC_170 tiene 2. Un cálculo exacto anterior coincide con T05 hasta 3 × 10⁻¹⁵°. No había error en T05.

**Qué no demuestra todavía.** Todos estos controles usan las mismas bibliotecas (`rasterio`, `pyproj`, `shapely`); el cotejo en QGIS al final es el que cubre ese riesgo común. `controles.json` vive todavía en `data/processed/`; se publica en el paso 6.

**Lo que sigue.** Paso 6: publicar en `registro/t05/` con procedencia, controles, manifiesto y `--verificar`.

### 8 de octubre de 2026 — Informe del paso 6: publicación y verificación

**Qué se hizo.**
- `.gitattributes`: se reescribió con fin de línea LF (la primera línea tenía un retorno de carro), se conservaron las dos reglas de T04 y se agregó `registro/t05/* text eol=lf`. Comprobado con `git check-attr`.
- Se añadieron a `scripts/t05_relieve.py` los modos `--publicar` y `--verificar` (con `--reproducir` opcional). Publicar vuelve a correr los controles, copia las dos tablas y `controles.json`, y escribe `procedencia.json` y `manifest.json`. Verificar distingue los dos controles acordados: **integridad** (hashes de todos los archivos excepto el propio manifiesto, columnas, conteos y coherencia entre tablas) y **reproducción numérica** (extrae de nuevo en una carpeta temporal y compara valor por valor con tolerancia relativa de 10⁻⁹).
- `procedencia.json` guarda: hashes y tamaños de los cuatro componentes del shapefile y de los dos TIFF, cuadrícula, unidades, CRS, método de áreas, tolerancias, piso de T10, hash del script y versiones del entorno. Usa rutas relativas al dataset; no contiene rutas locales.
- Se añadieron 6 pruebas de publicación y verificación, entre ellas una que simula la conversión a CRLF de un checkout de Windows y comprueba que la verificación la detecta. Total: 43 pruebas de T05; la suite completa del repositorio, 111, pasa.
- Se publicó en `registro/t05/` y se añadió al documento del método la sección «Cómo reproducir y verificar».

**Qué se esperaba.** Una entrega que Dani pueda verificar con una orden, que detecte cualquier alteración y que no repita el fallo de fin de línea de T04.

**Qué se encontró (verificado).**
- Controles al publicar: `aprobado`. Verificación de integridad: `integridad_aprobada` (197 parcelas, 2 253 celdas). Verificación con reproducción: `aprobada`, en unos 6 segundos.
- Los cinco archivos publicados están en LF, sin retornos de carro.
- La verificación detecta en las pruebas: un archivo alterado, una conversión a CRLF, un cambio en un TIFF fuente (reproducción distinta) y un destino con contenido previo.
- Una discrepancia con T02 deja publicar, pero el manifiesto y los controles registran `aprobado_con_avisos_t05_no_cerrada`, como se acordó.

**Límite importante.** Esta publicación se generó en el entorno del asistente, que **no** es el fijado en `requirements.txt`: Python 3.10.12 (fijado 3.12), `geopandas` 1.1.4 (fijado 1.2.0) y `pyproj` 3.7.1 (fijado 3.8.0); `numpy`, `rasterio`, `shapely` y `pyogrio` coinciden. `procedencia.json` lo declara tal cual. Hace falta correr `--verificar registro/t05 --reproducir` en el entorno fijado para confirmar que da los mismos valores.

**Lo que sigue.** Paso 7: registro en `uso_ia.csv` (T05 no entrena modelos, así que `experimentos.csv` no aplica), PR con la plantilla y reproducción por Dani.

### 8 de octubre de 2026 — Publicación regenerada en el entorno oficial

**Qué se hizo.** Jass corrió en Windows, dentro de la imagen Docker del repositorio (Python 3.12.15 y las versiones de `requirements.txt`), la suite completa de pruebas y la verificación con reproducción de la publicación hecha por el asistente. Después borró `registro/t05/` y la regeneró en ese mismo entorno. Órdenes, en PowerShell desde la raíz del repositorio:

    docker build -t agrocebada-entorno .
    docker run --rm -v "${PWD}:/proyecto" -w /proyecto agrocebada-entorno python -m unittest discover -s tests -v
    docker run --rm -v "${PWD}:/proyecto" -w /proyecto agrocebada-entorno python -m scripts.t05_relieve --extraer --salida data/processed/t05/extraccion_docker
    docker run --rm -v "${PWD}:/proyecto" -w /proyecto agrocebada-entorno python -m scripts.t05_relieve --publicar --salida data/processed/t05/extraccion_docker
    docker run --rm -v "${PWD}:/proyecto" -w /proyecto agrocebada-entorno python -m scripts.t05_relieve --verificar registro/t05 --reproducir

**Qué se esperaba.** Las 111 pruebas aprobadas y los mismos valores que la publicación anterior.

**Qué se encontró (verificado).**
- 111 pruebas aprobadas en Docker sobre Windows. Verificación de la publicación anterior: integridad y reproducción aprobadas.
- La nueva extracción da los mismos estados (192 / 1 / 4), controles `aprobado` y verificación con reproducción aprobada.
- `relieve_parcela.csv`, `relieve_celdas.csv` y `controles.json` son **idénticos byte por byte** a los generados en el entorno del asistente (Python 3.10). Solo cambian `procedencia.json` (entorno) y `manifest.json` (su huella).
- `procedencia.json` declara ahora el entorno fijado: Python 3.12.15, `geopandas` 1.2.0, `pyproj` 3.8.0, `numpy` 2.2.6, `rasterio` 1.4.4, `shapely` 2.1.2, `pyogrio` 0.13.0. Los cinco archivos están en LF.

**Queda resuelto** el límite anotado en el paso 6: la entrega no depende del entorno en que se genere.

**Relación con T01.** Es una ejecución exitosa de la imagen Docker en Windows y sirve como evidencia de apoyo, pero **no** es la comprobación que pide el README para cerrar T01: esa es `docker run --rm agrocebada-entorno`, que corre `scripts/verificar_entorno.py`. T01 es responsabilidad de Dani.

### 8 de octubre de 2026 — Corrección de tres controles tras una auditoría independiente

**Qué se hizo.** Jass pidió a otra herramienta (Codex) una auditoría. Reprodujo las 197 parcelas y no halló valores incorrectos, pero señaló tres fallos en los controles. El asistente los comprobó en el código y corrigió `scripts/t05_relieve.py`.

**Qué se encontró (verificado).**
1. `comprobar_tablas` solo contrastaba conteos y áreas: una media o la columna para T10 alteradas en una tabla pasaban publicación e integridad (solo la reproducción las detectaba). Ahora rehace desde las celdas medias, extremos, coberturas, estados y la regla D020, y la diferencia con el centroide.
2. `_iguales` daba «iguales» a 2500 e `inf` (con infinito, la tolerancia también es infinita). Reproducido. Ahora `inf`, `-inf` y `nan` nunca son iguales a nada, y las tablas con valores no finitos se rechazan.
3. Una parcela totalmente fuera del mapa (cero celdas) hacía fallar la comparación de IDs entre tablas. Ahora se admite su ausencia en la tabla de celdas solo si el resumen declara cero celdas y `sin_cobertura_espacial`; celdas de IDs desconocidos o repetidas siguen deteniendo.

**Comprobación.** 15 pruebas nuevas; ejecutadas contra el código anterior, 14 fallan y 1 da error (confirma que detectan los defectos); contra el código nuevo pasan. Suite completa: 126 pruebas OK en el entorno del asistente (Python 3.10). `--verificar registro/t05` sigue aprobando con los datos reales sin tocarlos.

**Qué no demuestra.** La reconstrucción no cubre el centroide ni los avisos (dependen de los ráster; los cubre `--reproducir`). Falta repetir las pruebas y la publicación en Docker.

**Consecuencia.** Cambió la huella de `scripts/t05_relieve.py`, así que `procedencia.json` y `manifest.json` deben regenerarse en Docker. Se espera que las dos tablas y `controles.json` salgan idénticos byte por byte.
