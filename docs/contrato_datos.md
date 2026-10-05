# Contrato inicial de datos

Este contrato se confirma en T01–T02 contra los archivos originales y el Shapefile. Una fila del catálogo representa una parcela de la campaña 2025. Las series por fecha y sensor se conservan aparte.

| Campo común | Fuente verificada | Regla inicial |
| --- | --- | --- |
| `id_parcela` | `ID_POLIGONO` de la tabla de área/rendimiento y tablas satelitales; `ID_POLIGON` en el Shapefile | Texto sin cambios, único en catálogo; nunca unir por número de fila. |
| `area_ha_origen` | `AREA_HA` | Conservar valor y procedencia; no sustituirlo por área calculada sin comparar. |
| `rendimiento_t_ha` | `RENDIMIENTO_T_HA` | 138 valores etiquetados, 59 vacíos; no rellenar ni redondear etiquetas. |
| `conjunto_origen` | `CONJUNTO` | Conservar literal original; verificar significado antes de usarlo como variable. |
| `municipio` | `Municipio` en el Shapefile | Conservar valor original; normalización y clave sólo tras validarlas. |
| `fecha_observada` | `fecha_captura` en Básico/PRO | Interpretar formato y zona de tiempo, registrar ventana y sensor. |
| `sensor` | `sensor` en Básico/PRO | Mantener procedencia y no equiparar índices de sensores distintos. |
| `fecha_disponible` | Metadatos/documentación del producto | Si no consta, marcar «no documentada»; no inferirla de `fecha_captura`. |

La tabla modelable tendrá 197 IDs y una fila por parcela. Los insumos por fecha/sensor, clima por parcela/mes, cobertura válida y controles de calidad quedan en tablas separadas hasta definir su integración. Un dato faltante no equivale a cero. Los rendimientos de las 59 parcelas no participan en ajustes ni validación.

Para toda extracción de ráster real: guardar fuente, versión conocida, unidades, periodo, CRS, resolución, área intersectada, cobertura válida, NoData y comparación con centroide. En rejilla geográfica, ponderar por área física, no por grados cuadrados. El ejemplo sintético del entorno no implementa esta extracción final.
