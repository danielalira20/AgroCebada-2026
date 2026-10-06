# Auditoría del catálogo y de las etiquetas de rendimiento

**Responsable:** Jass · **Revisora:** Dani · **Fecha:** 5 y 6 de octubre de 2026 · **Tarea del plan:** T02 (catálogo y etiquetas).

Deja un catálogo confiable de las 197 parcelas, audita cómo está anotado el rendimiento y diagnostica qué tan respaldadas están las 59 parcelas reservadas por las 138 conocidas. Todo se puede rehacer desde los archivos originales con los scripts de esta carpeta.

No se entrenó ningún modelo, no se modificó el dataset y no se excluyó ni se corrigió ninguna parcela.

## Resultado

1. **El catálogo es confiable.** 197 parcelas sin repetir, unidas una a una con su contorno; 138 con rendimiento y 59 sin él. Ningún contorno está repetido ni encimado. Se cumplen 60 de 60 comprobaciones.
2. **El área registrada es el área del contorno, redondeada.** No es un dato independiente: donde el contorno está mal trazado, el área también.
3. **El rendimiento está anotado con tres niveles de finura,** según el municipio: en escalones de 0.5, de 0.1 y de 0.01 t/ha. Donde está anotado grueso, las parcelas vecinas suelen compartir el mismo valor (7 de 8 pares de vecinas de la escritura `Cebada`).
4. **Tres de los rendimientos más altos vienen de las parcelas menos confiables:** muy pequeñas y con contorno dudoso (AGC_127, AGC_049 y AGC_055).
5. **Hay 7 parcelas extremas.** Las altas son diminutas; dos de las bajas son vecinas pegadas.
6. **Las 59 reservadas están tan respaldadas como las 138 conocidas.** 32 no tienen ningún aviso; las cinco más frágiles son AGC_120, AGC_147, AGC_173, AGC_174 y AGC_183.
7. **El diagnóstico de soporte coincide con el de T03** en todo lo que ambos miden igual. Las diferencias se deben a la definición usada, no a un error.

El detalle, con lo comprobado separado de lo que es sospecha, está en el informe.

## Qué leer y en qué orden

1. **[informe_catalogo_y_etiquetas.md](informe_catalogo_y_etiquetas.md):** respuesta, hallazgos, recomendaciones para el equipo, límites y cómo repetir todo. Empieza aquí.
2. **[tablas/catalogo_parcelas.csv](tablas/catalogo_parcelas.csv):** el catálogo. Es lo que se puede usar directamente.
3. **[diccionario_columnas.md](diccionario_columnas.md):** qué significa cada columna de cada tabla.
4. **[bitacora.md](bitacora.md):** el detalle cronológico de cada etapa y cada decisión, para quien quiera revisar cómo se llegó al resultado.

## Cómo usar el catálogo

Una fila por parcela, 197 filas y 22 columnas. Se une con cualquier otra tabla por `id_parcela`; nunca por número de fila.

| Grupo de columnas | Columnas |
|---|---|
| Identidad | `id_parcela`, `conjunto_origen`, `rendimiento_t_ha`, `area_ha_origen`, `municipio`, `estado`, `cultivo_origen` |
| Geometría | `geometria_valida`, `puntos_contorno`, `area_ha_geodesica`, `diferencia_area_pct`, `centroide_lon`, `centroide_lat` |
| Calidad de contorno | `contorno_categoria`, cinco marcas `contorno_...` y `contorno_firmeza` |
| Precisión de la etiqueta | `rendimiento_decimales`, `rendimiento_multiplo_de_medio` |

- **Nombres.** `id_parcela`, `area_ha_origen`, `rendimiento_t_ha`, `conjunto_origen` y `municipio` son los del [contrato de datos](../../docs/contrato_datos.md). El identificador se llama `ID_POLIGONO` en el CSV de rendimiento y en las tablas de T03, e `ID_POLIGON` en el shapefile y en la tabla de revisión de contornos.
- **Celda vacía significa «no hay dato».** Las 59 reservadas tienen el rendimiento vacío, nunca cero.
- **El rendimiento y el área están copiados tal cual,** sin redondear.
- **Lectura en pandas:** `pd.read_csv(ruta, encoding="utf-8-sig")`. Los archivos llevan marca de inicio (BOM) para que Excel lea bien los acentos.

## Las demás tablas

| Tabla | Filas | Para qué sirve |
|---|---:|---|
| `comprobaciones_catalogo.csv` | 106 | Cada comprobación del catálogo, con lo esperado y lo obtenido |
| `precision_etiqueta_por_municipio.csv` | 12 | Con qué finura está anotado el rendimiento en cada municipio |
| `cruce_contorno_rendimiento.csv` | 7 | Rendimiento según la calidad de contorno, dentro de cada municipio |
| `cruce_contorno_por_municipio.csv` | 8 | Desglose por municipio de ese cruce |
| `cruce_contorno_parcelas_b_c.csv` | 13 | Las parcelas conocidas con contorno B o C, una por una |
| `desviacion_municipal_por_parcela.csv` | 138 | Qué tan lejos queda cada parcela conocida de su municipio, y cuáles son extremas |
| `desviacion_por_tamano.csv` | 15 | Esa desviación según el tamaño de la parcela |
| `soporte_por_parcela.csv` | 197 | Respaldo de cada parcela: municipio, cercanía, clima, satélite, relieve, contorno y avisos |
| `soporte_resumen_por_municipio.csv` | 17 | Reservadas frente a conocidas, por municipio |
| `comparacion_con_t03.csv` | 23 | Comparación columna por columna con `registro/t03/soporte_parcelas.csv` |
| `comparacion_con_t03_por_parcela.csv` | 411 | Parcelas donde un conteo no coincide con T03 |
| `huellas_archivos_leidos*.csv` | — | Huella SHA-256 de cada archivo que leyeron los scripts |

## Cómo repetir todo

Con el entorno del [README principal](../../README.md) (Python 3.12 y `requirements.txt`) y el dataset de FIRA **descomprimido**, desde la raíz del repositorio y en este orden:

```sh
python analisis/auditoria_catalogo_y_etiquetas/scripts/construir_catalogo.py --datos data/DATASET_RETO_AGRO_2026
python analisis/auditoria_catalogo_y_etiquetas/scripts/cruzar_contorno_y_rendimiento.py
python analisis/auditoria_catalogo_y_etiquetas/scripts/senalar_parcelas_extremas.py
python analisis/auditoria_catalogo_y_etiquetas/scripts/diagnosticar_soporte.py --datos data/DATASET_RETO_AGRO_2026
python analisis/auditoria_catalogo_y_etiquetas/scripts/comparar_con_soporte_t03.py --datos data/DATASET_RETO_AGRO_2026
```

Si el dataset está en otro lugar, cambia la ruta de `--datos`. Todo junto tarda menos de un minuto y vuelve a escribir las 15 tablas de `tablas/`.

**Probado en:** Linux con Python 3.12.15 y las versiones fijadas en `requirements.txt` (`pip check` sin conflictos; `scripts/verificar_entorno.py` aprobado). **Falta probar** en Mac, en Windows y dentro de Docker. La imagen de Docker actual solo incluye `verificar_entorno.py`; para correr estos scripts en ella habría que montar el repositorio, por ejemplo con `docker run --rm -v "$PWD":/proyecto agrocebada-entorno python analisis/auditoria_catalogo_y_etiquetas/scripts/construir_catalogo.py --datos data/DATASET_RETO_AGRO_2026`. Ese comando no se ha probado.

**Qué debe pasar:** el primer script termina con «Comprobaciones: 60 cumplen, 0 no cumplen», y las tablas quedan iguales a las que ya están en esta carpeta.

**Si una tabla sale distinta:** compara primero `tablas/huellas_archivos_leidos.csv` y `tablas/huellas_archivos_leidos_soporte.csv` con las versiones de Git. Si las huellas no coinciden, la diferencia está en tu copia del dataset, no en los scripts.

Los scripts solo leen el dataset. Además leen dos archivos del repositorio: `analisis/exploracion_parcelas_qgis/revision_contornos/revision_contornos.csv` y `registro/t03/soporte_parcelas.csv`.

## Avisos

- **Esta carpeta contiene los 138 rendimientos.** Están en `catalogo_parcelas.csv`, `desviacion_municipal_por_parcela.csv` y `cruce_contorno_parcelas_b_c.csv`. El dataset original sigue excluido de Git; tenerlo en cuenta si el repositorio se hace público.
- **Dos nombres de columna no están en el contrato de datos:** `estado` y `cultivo_origen`. Se proponen como añadidos.
- **`cultivo_origen` es el mismo dato que T03 llama `grupo_registro`** (el campo `Cultivo` del shapefile, con sus dos escrituras `Cebada` y `CEBADA`). Aquí se guarda como metadato original, sin afirmar cómo se registró ni atribuirle efecto agronómico. Conviene que el equipo elija un solo nombre.
- **Los avisos de soporte son hechos con umbral declarado, no una calificación.** No se propone un semáforo: cuánto pesa cada aviso lo decide el equipo.
- **Señalar una parcela como extrema o frágil no es excluirla.** Ninguna tiene un error comprobado.
- **La comparación con T03 cubrió solo su tabla de soporte,** no sus particiones ni su protocolo.
- **Copia de trabajo:** el original de esta carpeta se mantiene en la computadora de Jass. Los cambios se hacen ahí y se vuelven a copiar aquí.

## Límites principales

- Se comprueba que los archivos concuerdan entre sí y cómo está anotado el rendimiento; no cómo se midió. Eso solo puede responderlo FIRA.
- El municipio es el declarado en el shapefile; no se verificó contra límites oficiales.
- La calidad de contorno viene de la [exploración de parcelas en QGIS](../exploracion_parcelas_qgis/README.md) y hereda sus límites.
- Varios hallazgos descansan en pocas parcelas. El informe dice en cada caso cuántas.
