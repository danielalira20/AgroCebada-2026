# Exploración de parcelas en QGIS

**Responsable:** Jass · **Fecha:** 4 y 5 de octubre de 2026 · **Relación con el plan:** revisión previa a T02 (catálogo y etiquetas); aporta también a T05 y T06.

Se pusieron los 197 contornos del shapefile sobre una imagen satelital pública y se revisó, parcela por parcela, si cada uno cae sobre un campo agrícola real.

## Resultado

**Los 197 contornos caen sobre tierra de cultivo.** Ninguno cae sobre un pueblo, agua o monte cerrado. Pero no todos describen bien su campo:

| Categoría | Parcelas |
|---|---:|
| **A.** El contorno sigue la orilla visible del campo | 175 |
| **B.** Es campo agrícola, pero el contorno corta la orilla o deja dentro algo ajeno (casas, camino, estanque, arbolado) | 12 |
| **C.** Un solo contorno une varios campos separados por algo que no es cultivo | 10 |

Además, 107 parcelas tienen divisiones internas, 70 tienen árboles dentro y 16 son angostas o muy pequeñas. En 96 de las 197 hay algo dentro del contorno que mezcla la señal satelital.

**Límites principales:** la imagen de fondo no tiene fecha conocida; desde la imagen se distingue tierra de cultivo, no si es cebada; 160 parcelas tienen solo una primera pasada sobre imagen fija (todas en A). Las B y las C están todas confirmadas de cerca en QGIS.

No se entrenó ningún modelo y no se consultó el rendimiento al calificar.

## Qué leer y en qué orden

1. **[informe_contornos_sobre_campo_real.md](informe_contornos_sobre_campo_real.md)**: respuesta, método, hallazgos, límites y lo que quedó sin resolver. Empieza aquí.
2. **[revision_contornos/revision_contornos.csv](revision_contornos/revision_contornos.csv)**: la calificación de cada parcela. Es lo que se puede usar directamente.
3. **[bitacora.md](bitacora.md)**: el detalle cronológico de cada paso y decisión, para quien quiera revisar cómo se llegó al resultado.

## Cómo usar la tabla

Una fila por parcela, 197 filas. Se une con cualquier otra tabla por `ID_POLIGON` (así se llama el identificador en el shapefile; en el CSV de rendimiento es `ID_POLIGONO`). **No contiene el rendimiento.**

| Columna | Contenido |
|---|---|
| `ID_POLIGON` | Identificador de la parcela, `AGC_001` a `AGC_197` |
| `categoria` | `A`, `B` o `C` (ver arriba) |
| `divisiones_internas` | `si` / `no`: hay líneas, bordos o hileras que parten el campo por dentro |
| `arboles_dentro` | `si` / `no`: hay árboles o arbustos dentro del contorno |
| `construccion_dentro` | `si` / `no`: hay casa, corral, bodega o estructura dentro |
| `angosta_o_muy_pequena` | `si` / `no`: menos de unos 40 m de ancho o menos de 1 ha |
| `imagen_poco_clara` | `si` / `no`: la imagen está borrosa o no dejó confirmar |
| `nota` | Qué se vio en esa parcela |
| `etapa` | Qué tan firme es la calificación (ver abajo) |
| `confirmar_en_qgis` | `si` en 27 parcelas en A con una duda menor que no se revisó de cerca |
| `fecha_revision` | Fecha de la última revisión |

Valores de `etapa`:

- `piloto_confirmado_en_qgis` (10) y `confirmado_en_qgis` (25): revisada de cerca en QGIS.
- `revisado_en_qgis_sin_poder_confirmar` (2): se miró de cerca, pero la imagen no dejó decidir.
- `primera_pasada_sobre_imagen` (160): calificada sobre la imagen exportada, sin acercarse. Todas están en A.

El archivo está en UTF-8 con marca de inicio (BOM), para que Excel lea bien los acentos. En pandas: `pd.read_csv(ruta, encoding="utf-8-sig")`.

## Qué hay en esta carpeta

| Carpeta o archivo | Contenido |
|---|---|
| `informe_contornos_sobre_campo_real.md` | El informe |
| `bitacora.md` | Bitácora completa |
| `revision_contornos/` | La tabla de calificaciones |
| `capturas_parcelas_atlas/` | Una imagen por parcela (197), todas con el mismo encuadre: `AGC_###/AGC_###_esri.jpg` |
| `capturas_parcelas/` | Imágenes del piloto de 10 parcelas, a varias distancias |
| `capturas_comprobacion_ubicacion/` | 15 capturas sobre OpenStreetMap, por estado y municipio |
| `proyecto_qgis/` | El proyecto de QGIS y su [LEEME](proyecto_qgis/LEEME.md) |

Los archivos `.jgw` que acompañan a las imágenes guardan su ubicación y escala; permiten abrir cada imagen en QGIS en su lugar exacto.

## Avisos

- **Las imágenes muestran la ubicación de las parcelas.** Cada una lleva el contorno, el ID y su archivo de ubicación. El shapefile original está excluido de Git; estas imágenes permiten reconstruir parte de esa información. Tenerlo en cuenta si el repositorio se hace público.
- **Imagen de fondo:** Esri World Imagery, un servicio público de imágenes satelitales. Si alguna imagen se usa en el informe o en el video, hay que citar la fuente.
- **Documentos no incluidos:** el informe y la bitácora mencionan auditorías previas del dataset y un registro de decisiones que son documentos de trabajo locales de Jass. Lo necesario de ellos está resumido en el informe.
- **Copia de trabajo:** el original de esta carpeta se mantiene en la computadora de Jass. Los cambios se hacen ahí y se vuelven a copiar aquí.
