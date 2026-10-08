# Auditoría del catálogo y de las etiquetas de rendimiento

**Responsable:** Jass · **Revisora:** Dani · **Fecha:** 5 y 6 de octubre de 2026 · **Tarea del plan:** T02 (catálogo y etiquetas).

Deja un catálogo confiable de las 197 parcelas, audita cómo está anotado el rendimiento y diagnostica qué tan respaldadas están las 59 parcelas reservadas por las 138 conocidas. Todo se puede rehacer desde los archivos originales con los scripts de esta carpeta.

No se entrenó ningún modelo, no se modificó el dataset y no se excluyó ni se corrigió ninguna parcela.

## Resultado

1. **El catálogo es confiable.** 197 parcelas sin repetir, unidas una a una con su contorno; 138 con rendimiento y 59 sin él. Ningún contorno está repetido ni encimado. Se cumplen 60 de 60 comprobaciones.
2. **El área registrada coincide con el área del contorno, redondeada, en las 197 parcelas.** En estos datos no aporta información distinta de la del contorno. La coincidencia no demuestra cómo obtuvo FIRA la superficie.
3. **El rendimiento está escrito en tres tamaños de escalón,** según el municipio: 0.5, 0.1 y 0.01 t/ha. Donde el escalón es grande, las parcelas vecinas suelen compartir el mismo valor (7 de 8 pares de vecinas de la escritura `Cebada`). Esto describe cómo están escritos los valores; no prueba con qué precisión se midieron.
4. **Tres de los rendimientos más altos vienen de las parcelas menos confiables:** muy pequeñas y con contorno dudoso (AGC_127, AGC_049 y AGC_055).
5. **Hay 7 parcelas extremas.** Las altas son diminutas; dos de las bajas son vecinas pegadas.
6. **Las 59 reservadas se parecen a las 138 conocidas en la mayoría de los indicadores de soporte, pero no en todos.** Parecidas en distancia entre centros, observaciones satelitales y proporción sin avisos (54 % en los dos grupos); peor en contornos B o C (15 % frente a 9 %) y en distancia entre orillas (mediana de 51.9 m frente a 17.8 m). Las cinco más frágiles son AGC_120, AGC_147, AGC_173, AGC_174 y AGC_183. No dice que las predicciones vayan a salir igual de bien.
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
- **No uses como variables de un modelo las columnas que salen del rendimiento.** En el catálogo son `rendimiento_decimales` y `rendimiento_multiplo_de_medio`; en las demás tablas, todo lo que hable de precisión de la etiqueta, desviación, parcelas extremas, el cruce con el contorno y el aviso `etiqueta_gruesa_en_municipio`. Sirven para auditar, no para predecir. La lista completa está en el [diccionario](diccionario_columnas.md#columnas-que-salen-del-rendimiento-solo-auditoría).
- **Lectura en pandas:** `pd.read_csv(ruta, encoding="utf-8-sig")`. Los archivos llevan marca de inicio (BOM) para que Excel lea bien los acentos.

## Las demás tablas

| Tabla | Filas | Para qué sirve |
|---|---:|---|
| `comprobaciones_catalogo.csv` | 106 | Cada comprobación del catálogo, con lo esperado y lo obtenido |
| `precision_etiqueta_por_municipio.csv` | 12 | En qué tamaño de escalón está escrito el rendimiento en cada municipio |
| `pares_de_parcelas_cercanas.csv` | 87 | Pares de parcelas con orillas a menos de 20 m, para mantener juntas a las vecinas al evaluar |
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

## Cómo preparar los datos

Los scripts no leen los ZIP: necesitan una copia descomprimida del dataset. El paquete original de FIRA se guarda sin tocar en `data/raw/` y la copia de trabajo queda en `data/`. Las dos carpetas están fuera de Git.

**Paso 1.** Deja el paquete original en `data/raw/DATASET_RETO_AGRO_2026/`. Debe traer estos archivos sueltos:

```text
data/raw/DATASET_RETO_AGRO_2026/
├── ID_area_rendimiento_70_30_Reto_AgroCebada.csv
├── Conjunto_datos_BASICO_AgroCebada2026.csv
├── Conjunto_datos_PRO_AgroCebada.csv
├── Parcelas_Reto_AGC_CONJUNTO_70_30.zip
├── Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip
├── Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS.zip
├── Reto_AgroCebada_Topografia_INEGI_CEM4.zip
└── (dos documentos .docx)
```

**Paso 2.** Crea la copia descomprimida, desde la raíz del repositorio:

```sh
python analisis/auditoria_catalogo_y_etiquetas/scripts/preparar_copia_del_dataset.py --origen data/raw/DATASET_RETO_AGRO_2026 --destino data/DATASET_RETO_AGRO_2026
```

El script copia los archivos sueltos, descomprime cada ZIP en una carpeta con el nombre del ZIP y comprueba que esté lo necesario. Solo lee el origen y se niega a escribir sobre una carpeta que ya exista. Debe terminar con «Estructura comprobada».

**Cómo debe quedar:**

```text
data/DATASET_RETO_AGRO_2026/
├── ID_area_rendimiento_70_30_Reto_AgroCebada.csv
├── Conjunto_datos_BASICO_AgroCebada2026.csv
├── Conjunto_datos_PRO_AgroCebada.csv
├── Parcelas_Reto_AGC_CONJUNTO_70_30/
│   └── Parcelas_Reto_AGC_CONJUNTO.shp  (y .dbf, .shx, .prj, .cpg)
├── Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025/
│   └── …/Precipitacion_mensual/2025/PREC_2025_04.tif  (y los demás meses)
├── Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS/
└── Reto_AgroCebada_Topografia_INEGI_CEM4/
    └── …/Elevacion_INEGI_CEM4_120m.tif  y  Pendiente_INEGI_CEM4_120m_grados.tif
```

**Si descomprimes a mano,** cuida dos cosas:

- El ZIP de parcelas trae sus cinco archivos sueltos, sin carpeta. Hay que extraerlo **dentro** de una carpeta llamada `Parcelas_Reto_AGC_CONJUNTO_70_30`; si se extrae «aquí», los scripts no encuentran el shapefile.
- Los mapas se buscan por nombre en cualquier subcarpeta, así que no importa cuántos niveles de carpetas queden. Lo que no puede haber es dos copias del mismo mapa: si un ZIP se extrae dos veces, el script se detiene y lo avisa.

## Cómo repetir todo

Con el entorno del [README principal](../../README.md) (Python 3.12 y `requirements.txt`) y la copia descomprimida del paso anterior, desde la raíz del repositorio y en este orden:

```sh
python analisis/auditoria_catalogo_y_etiquetas/scripts/construir_catalogo.py --datos data/DATASET_RETO_AGRO_2026
python analisis/auditoria_catalogo_y_etiquetas/scripts/cruzar_contorno_y_rendimiento.py
python analisis/auditoria_catalogo_y_etiquetas/scripts/senalar_parcelas_extremas.py
python analisis/auditoria_catalogo_y_etiquetas/scripts/diagnosticar_soporte.py --datos data/DATASET_RETO_AGRO_2026
python analisis/auditoria_catalogo_y_etiquetas/scripts/comparar_con_soporte_t03.py --datos data/DATASET_RETO_AGRO_2026
```

Si el dataset está en otro lugar, cambia la ruta de `--datos`. Todo junto tarda menos de un minuto y vuelve a escribir las 16 tablas de `tablas/`.

**Probado en:** Linux con Python 3.12.15 y las versiones fijadas en `requirements.txt` (`pip check` sin conflictos; `scripts/verificar_entorno.py` aprobado). **Falta probar** en Mac, en Windows y dentro de Docker. La imagen de Docker actual solo incluye `verificar_entorno.py`; para correr estos scripts en ella habría que montar el repositorio, por ejemplo con `docker run --rm -v "$PWD":/proyecto agrocebada-entorno python analisis/auditoria_catalogo_y_etiquetas/scripts/construir_catalogo.py --datos data/DATASET_RETO_AGRO_2026`. Ese comando no se ha probado.

**Qué debe pasar:** el primer script termina con «Comprobaciones: 60 cumplen, 0 no cumplen». Para saber si las tablas quedaron iguales a las guardadas en Git, corre después el comparador, que solo lee:

```sh
python analisis/auditoria_catalogo_y_etiquetas/scripts/comparar_tablas_con_referencia.py
```

Debe terminar con «0 distintas» y con «0 sin esquema». La última línea también dice cuántas tablas son iguales y cuántas lo son solo dentro de la tolerancia.

**El comparador no adivina qué es cada columna: lo lee de `esquema_de_tablas.csv`,** que declara para cada columna de cada tabla su tipo (texto, entero o decimal), cuántos decimales lleva y qué diferencia se acepta. Reglas:

| Tipo declarado | Qué se acepta |
|---|---|
| Fin de línea (Windows o Mac/Linux) y marca BOM | No se toman en cuenta |
| Texto y enteros (incluidas las marcas `si`/`no` y las huellas) | Deben coincidir exactamente. Un entero que pasa a decimal (`5` a `5.1`) es una diferencia, aunque sea pequeña |
| Decimal copiado del dataset original (por ejemplo `rendimiento_t_ha`) | Debe coincidir exactamente: la tolerancia es 0. Se compara el texto, así que `3.5` y `3.50` cuentan como distintos, igual que `0.0` y `-0.0` |
| Decimal calculado | Hasta una unidad del último decimal declarado: por ejemplo 0.000001 ha en `area_ha_geodesica` o 1 m en `distancia_conocida_mas_cercana_m`. Se acepta la notación científica (`1e-05`, que es como pandas escribe los números muy chicos) y se compara por su valor |
| Cualquier número | Solo dígitos 0 a 9. Se rechazan `nan`, `inf`, `+1.0`, `.5`, `5.`, espacios y números absurdamente grandes o chicos |
| Celda vacía | Significa «no hay dato» y se acepta en cualquier tipo; que un valor aparezca o desaparezca es una diferencia |

El comparador **termina con error** (no con «0 distintas») si: una carpeta no existe o no tiene tablas; falta o sobra una tabla; una tabla no está en el esquema; las tablas de referencia no cumplen el propio esquema; la carpeta de referencia es la misma que la de las tablas nuevas (se compararía cada tabla consigo misma); o un archivo no se puede leer como CSV en UTF-8. Esto evita que una comparación vacía o trivial parezca un éxito.

Esa tolerancia existe porque el redondeo del último decimal puede cambiar con otro sistema operativo o con otra versión de las librerías. No se afirma que las tablas salgan idénticas byte a byte en cualquier computadora.

**Costo de mantener el esquema:** cada vez que se agregue, quite o cambie una columna de una tabla hay que editar también `esquema_de_tablas.csv` (una fila por columna). Si se olvida, el comparador marca la columna como «sin esquema» y la prueba `test_el_esquema_del_repositorio_describe_las_tablas_guardadas` falla. A cambio, un cambio de tipo en una columna no pasa inadvertido.

**Si una tabla sale distinta:** el comparador dice en qué tabla, línea y columna. Revisa primero las dos tablas de huellas: si la huella de un archivo cambió, ese archivo no es igual al que se usó aquí. Si las huellas coinciden y aun así hay diferencias mayores a la tolerancia, la causa está en el entorno (versiones de las librerías) o en los scripts; anota el caso en el registro en lugar de descartarlo.

**Pruebas de los scripts:** `python analisis/auditoria_catalogo_y_etiquetas/scripts/probar_area_geodesica.py` (debe terminar con «7 de 7 pruebas cumplen») y `python analisis/auditoria_catalogo_y_etiquetas/scripts/probar_comparar_tablas.py` (debe terminar con «33 de 33 pruebas cumplen»). No leen el dataset; la segunda usa carpetas temporales y solo lee `tablas/` y el esquema del repositorio. Incluye pruebas con miles de valores al azar y una que cambia una celda de cada columna de las 16 tablas reales para comprobar que el comparador lo detecta.

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
