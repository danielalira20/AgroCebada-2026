# T06 · Frente satelital: nota de método

- **Responsable:** Daf. **Revisora:** Jass.
- **Estado:** En revisión. Borrador del 6 de octubre de 2026.
- **Artefactos:** `scripts/t06_satelite.py`; en `registro/t06/`, las tablas de cobertura, calidad, rasgos, comparación de ventanas y variables, y la figura.
- **Reproducir:** desde la raíz del repositorio, `python scripts/t06_satelite.py --datos RUTA/DATASET_RETO_AGRO_2026` (unos 40 s). Escribe las series en `data/interim/t06/` (no versionadas) y el resto en `registro/t06/`. Dos ejecuciones dan archivos idénticos.
- **Decisiones:** D002–D007 en `registro/decisiones.csv`. Ninguna se tomó mirando rendimientos: el script sólo lee `ID_POLIGONO` y `CONJUNTO` del catálogo.

## 1. Series por sensor

Una tabla larga por sensor (`serie_sentinel2.csv`, `serie_landsat.csv`, `serie_planet.csv`), con `ID_POLIGONO`, `fecha_observada`, `fecha_disponible`, `sensor`, `fuente`, los índices del sensor (promedio, std, mínimo y máximo), `porcentaje_nubosidad`, `tiene_dato` y `posterior_al_corte`. Básico y PRO no se unen por ID.

- `fecha_disponible` = «no documentada»: ni el diccionario ni la descripción general la informan.
- El LAI del PRO se llama `lai2` (documento de ecuaciones de FIRA, pág. 2). No se fusiona con el LAI de Sentinel-2. Ese LAI reproduce −ln((0.69 − SAVI)/0.59)/0.91, así que se conserva en la serie pero no se usa (D005).
- Un faltante queda vacío, nunca en cero. Nubosidad 100 o vacía = sin dato: en esos casos los índices vienen vacíos sin excepción.

## 2. Nubosidad

El diccionario sólo dice que «el porcentaje de nubosidad se conserva como variable de calidad». La descripción general deja el filtrado a cada equipo. No se documenta si es por escena o por parcela, ni si los índices excluyen píxeles nublados. Por eso no se interpreta 100 − nubosidad como fracción de píxeles válidos.

En los datos, la nubosidad cambia entre parcelas en la misma fecha. Además, con nubosidad parcial el NDVI cae respecto a la captura despejada más cercana: en Sentinel-2, −0.033 entre 1 y 5 % y −0.054 entre 10 y 20 %, frente a un ruido de ~0.011 entre capturas despejadas (`calidad_nubosidad.csv`). Umbrales fijados por cobertura y calidad: Sentinel-2 ≤ 5 %, Planet ≤ 20 % y Landsat ≤ 5 % (D002, D006).

## 3. Cobertura, corte y ventanas

`cobertura_mensual.csv` y `cobertura_ventana.csv` cuentan, por sensor, parcela, mes y ventana, las capturas válidas y el hueco máximo con tres umbrales candidatos (0, 5 y 20 %). El hueco incluye los bordes: del inicio de la ventana a la primera captura y de la última captura al corte.

Todo cálculo recorta primero al 31-oct-2025 y después suaviza o interpola. Las variables se calculan en las dos ventanas del protocolo, `abr_oct` y `jun_oct`, con la ventana en el nombre (D003). Landsat sólo aporta calidad y nivel de VI6T: su hueco máximo mediano es de 40 días y en septiembre a muchas parcelas les falta captura.

## 4. Rasgos observables (`rasgos_observables.csv`)

Se calculan sobre el NDVI de capturas válidas en `abr_oct`, la ventana de referencia, suavizado con una mediana móvil de 3 capturas. Base = mínimo antes del máximo; amplitud = máximo − base.

- **Inicio:** cruce ascendente de base + 20 % de la amplitud. La fecha se interpola entre las dos capturas que lo rodean y se guarda cuántos días las separan.
- **Pico:** el máximo cuenta si antes y después la curva baja al menos 20 % de la amplitud.
- **Final:** cruce descendente de base + 50 % de la amplitud.

Lo no observado queda vacío y se marca con su motivo. Se observa el final en 77/197 parcelas (Planet) y 56/197 (Sentinel-2), y el pico en 164 y 159.

Banderas de calidad (no son variables):
- `posible_ciclo_doble`: tras el inicio, la curva cae ≥ 30 % de la amplitud y vuelve a subir ≥ 30 %. Sale en 42 (Planet) y 20 (Sentinel-2). Sentinel-2 nunca la marca sin Planet.
- `meseta_en_pico`: hay capturas a ≤ 5 % de la amplitud del máximo separadas por ≥ 45 días; la fecha del pico es ambigua. Sale en 23 (Planet) y 27 (Sentinel-2).

La figura `figura_curvas_6_parcelas.png` muestra 6 parcelas elegidas sin rendimiento: dos por categoría de rasgos, una etiquetada y una reservada, en cada caso la de número de capturas más cercano a la mediana de su categoría.

## 5. Variables compactas (`variables_satelitales.csv`)

Una fila por parcela, 197 filas, sin rendimiento ni faltantes. Las definiciones están en `variables_satelitales_diccionario.csv` (D007).

| Grupo | Planet (`pl_`) | Sentinel-2 (`s2_`) | Landsat (`ls_`) |
|---|---|---|---|
| Compactas, por ventana | `ndvi_max`, `ndvi_integral`, `lai2_max`, `ndvi_dias_sobre_mitad`, `ndvi_dia_inicio` | `ndvi_max`, `ndvi_integral`, `ndvi_dias_sobre_mitad`, `ndwi_en_maximo` | `vi6t_mediana` |
| Al corte, sin ventana | `pl_ndvi_al_corte` | `s2_ndvi_al_corte` | — |
| Heterogeneidad | `ndvi_std_en_maximo` | `ndvi_std_en_maximo` | — |
| Calidad, por ventana | `capturas`, `hueco_max`, `nubosidad_media` | igual | igual |

- `nubosidad_media` promedia todas las capturas con nubosidad informada, incluidas las de 100. Puede actuar como indicador de zona.
- Todos los máximos de NDVI caen después del 1-jun. Por eso `ndvi_max`, `lai2_max`, `ndwi_en_maximo` y `ndvi_std_en_maximo` son idénticos en ambas ventanas. Entre `abr_oct` y `jun_oct` sólo cambian la integral, los días sobre la mitad, el día de inicio y la calidad.
- Sin variables de senescencia: el final del ciclo no se observa en la mayoría de las parcelas.
- Las imputaciones, el escalado y el centrado por municipio (configuración 8) se hacen en T11, dentro de cada entrenamiento externo.

## 6. Diagnósticos (`diagnosticos_variables.csv`)

Se calcula la correlación de Spearman entre parcelas de cada variable con la versión al corte.

- **Campaña hasta el 31-dic frente al corte:** los máximos no cambian (1.0). Las integrales y los días sobre la mitad sí (0.88–0.94). Las variables «al corte» miden otra cosa (0.30–0.32). Lo posterior al 31-oct añade información, y el corte la excluye.
- **Fechas barajadas dentro de cada parcela, con los valores intactos (5 semillas):** la calidad no cambia (1.0). Las variables que dependen del orden temporal sí: día de inicio ≈ 0, al corte ≈ 0.02, integrales 0.13–0.46. Así se comprueba que esas variables usan de verdad la secuencia temporal. El efecto sobre el error del modelo se mide en T11.

## 7. Presupuesto de T11

Ocho configuraciones fijadas antes de ver resultados (D004); la referencia territorial no cuenta.

| # | Configuración |
|---|---|
| 1 | Territorio + calidad de Planet en `abr_oct` (`pl_capturas`, `pl_hueco_max`, `pl_nubosidad_media`) |
| 2 | Territorio + Sentinel-2 compacto, `jun_oct` |
| 3 | Territorio + Sentinel-2 compacto, `abr_oct` |
| 4 | Territorio + Planet compacto, `jun_oct` |
| 5 | Territorio + Planet compacto, `abr_oct` |
| 6 | Territorio + Planet compacto `abr_oct` + calidad `abr_oct` (mejora A) |
| 7 | Territorio + Planet compacto `abr_oct` + `pl_ndvi_std_en_maximo_abr_oct` (mejora B) |
| 8 | Territorio + Planet compacto `abr_oct` centrado por municipio, con el promedio municipal calculado sólo con el entrenamiento de cada partición externa |

- **Sensor de 1 y 6–8, fijado por cobertura:** Planet tiene ~80 capturas válidas por parcela frente a ~32 de Sentinel-2.
- **Ventana de 1 y 6–8, fijada por estabilidad de la base de la curva** (`comparacion_ventanas.csv`, corrección tras la revisión de Jass). Al recortar a `jun_oct`, la base del NDVI de Planet sube +0.066 de mediana y nunca baja. El día de inicio se corre +5 días de mediana, hasta +36. En 59 de 197 parcelas la curva de `jun_oct` ya empieza por encima del umbral de inicio de `abr_oct`, porque el verdor empezó antes del 1-jun. En `abr_oct` la base es el suelo antes de la siembra, así que la integral, los días sobre la mitad y el día de inicio no dependen de dónde empieza la ventana.
- Las dos elecciones se hicieron antes de cualquier resultado de T11 y sin rendimientos. Las configuraciones 2–5 siguen comparando ambas ventanas.

## 8. Pendientes

- FIRA: cómo se calcula `porcentaje_nubosidad`, fecha de disponibilidad de las imágenes y si se admiten observaciones posteriores al 31-oct.
- Repetir la ejecución en Mac y en Docker. `matplotlib` se añadió a `requirements.txt`; la imagen Docker se construye con él.
