# Proyecto de QGIS: cómo abrirlo y qué tener en cuenta

`contornos_sobre_imagen.qgz` es el proyecto con el que se hizo la exploración. **No hace falta abrirlo para usar los resultados**: la tabla y las imágenes ya están en esta carpeta. Sirve para mirar una parcela de cerca o para repetir la exportación de imágenes.

## Qué es un proyecto de QGIS

Es una receta: guarda qué capas se abren y cómo se ven, pero **no contiene los datos**. Por eso pesa muy poco y por eso necesita encontrar el shapefile en tu computadora.

## Requisitos

- **QGIS 3.44** (la versión estable, LTR) o posterior. Se descarga gratis en `https://qgis.org/download/`. Al abrirlo, elegir «QGIS Desktop», no las herramientas auxiliares que vienen en el mismo instalador.
- **El shapefile de parcelas del dataset de FIRA** (`Parcelas_Reto_AGC_CONJUNTO.shp` con sus archivos `.dbf`, `.shx`, `.prj` y `.cpg`, los cinco juntos en la misma carpeta).
- **Conexión a internet**, para las imágenes de fondo.

## Al abrirlo: aviso de capa no encontrada

El proyecto se creó en otra carpeta y busca el shapefile en una ruta que en el repositorio no existe. Es normal que al abrirlo aparezca una ventana de **capas no disponibles**. Para arreglarlo:

1. En esa ventana, seleccionar la capa que falla y elegir **Explorar**.
2. Buscar en tu computadora `Parcelas_Reto_AGC_CONJUNTO.shp`, dentro de la carpeta `Parcelas_Reto_AGC_CONJUNTO_70_30` del dataset.
3. Aceptar y aplicar los cambios.
4. Guardar el proyecto **con otro nombre o fuera del repositorio** (Proyecto → Guardar como), para no subir tu ruta personal a Git.

El proyecto tiene dos capas que usan ese mismo shapefile; puede pedir la ruta para las dos.

## Qué trae el proyecto

| Capa | Qué muestra |
|---|---|
| `Parcelas_Reto_AGC_CONJUNTO` | Los 197 contornos en amarillo, sin relleno, con su ID |
| `Parcelas Por Municipio` | Los mismos contornos, rellenos de un color por municipio |
| `Esri World Imagery` | Imagen satelital de fondo (viene de internet) |
| `OpenStreetMap` | Mapa con nombres de pueblos y caminos (viene de internet) |

Las capas se prenden y apagan con su casilla en el panel **Capas**. Para revisar parcelas conviene tener prendidos los contornos amarillos y la imagen satelital, y apagada la vista por municipio.

**Si el mapa se ve en blanco:** clic derecho sobre la capa de parcelas → **Zoom a la capa**.

**Para ir a una parcela:** clic derecho sobre la capa de parcelas → **Abrir tabla de atributos** → clic derecho sobre la fila → **Zoom al objeto espacial**.

## Repetir la exportación de imágenes

Menú **Proyecto → Composiciones → atlas_parcelas**. En la ventana que se abre, **Atlas → Exportar atlas como imágenes**. Genera una imagen por parcela, nombrada con su ID. Se usó: formato JPG, 100 ppp, margen del 40 % alrededor de cada parcela y archivo de georreferenciación activado.

## Límites

- **El archivo conserva por dentro la ruta de la computadora donde se creó.** No afecta su uso.
- **La imagen satelital no tiene fecha conocida** y no es de una sola fecha. Sirve para ver el terreno, no para saber qué había sembrado en 2025.
- **El proyecto no carga el rendimiento.** La revisión se hizo a propósito sin verlo.
- **No modificar el shapefile original** desde QGIS: no activar la edición de la capa.
- Los nombres de los menús pueden variar un poco entre versiones de QGIS.
