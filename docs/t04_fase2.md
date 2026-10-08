# T04 · Comprobación espacial de fase 2

Responsable: Dani. Revisora: Jass. Fecha: 6 de octubre de 2026.
Estado: comprobación técnica aprobada en Mac Apple Silicon. Pendiente abrir el nuevo proyecto en QGIS y revisión humana. T04 sigue en curso; no existe todavía la entrega completa de clima de las 197 parcelas.

## Acuerdos aplicados

Dani aceptó conservar `data/raw/DataSet.zip` como fuente original para los cálculos, preparar una copia de visualización y reutilizar pesos sólo entre cuadrículas idénticas. Se conservaron las copias históricas bajo raw y el proyecto QGIS anterior; no se restauraron ni sobrescribieron.

```text
data/
├── raw/
│   ├── DataSet.zip                         ← fuente autoritativa
│   └── DATASET_RETO_AGRO_2026/             ← copias anteriores conservadas
└── processed/qgis/DATASET_RETO_AGRO_2026/   ← copia para visualización
    ├── Parcelas_Reto_AGC_CONJUNTO.shp       ← con sus archivos acompañantes
    ├── Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025/
    └── Reto_AgroCebada_Temperatura_2022_2025/
reports/
├── t04_revision.qgz                       ← sesión anterior conservada
├── t04_revision_trabajo.qgz               ← abrir éste para continuar
└── t04_fase2_20261006/                    ← evidencia local
```

La copia contiene 153 archivos (144 GeoTIFF, componentes de parcelas y documentación/inventarios de estos tres paquetes), 2,168,268 bytes, aproximadamente 2.2 MB. Todos coinciden byte por byte con sus miembros del maestro. No incluye satélite, rendimientos ni relieve: esos insumos no se necesitan para esta visualización climática.

El proyecto nuevo conserva la vista, simbología, orden e identificadores de las cuatro capas. Sólo se cambiaron las rutas en `datasource` y en el árbol de capas. Las cuatro fuentes se abrieron con GDAL/GeoPandas; no se abrió QGIS ni se alteró la sesión activa de Dani. La validación visual se realiza abriendo el proyecto de trabajo desde Proyecto → Abrir. Guardar las siguientes sesiones en ese archivo; dejar el anterior como referencia.

## Método y precisión numérica

`scripts/t04_espacio.py` es una comprobación de dos ejemplos, no el extractor completo. Intersecta parcelas y celdas en su WGS84 nativo. Cada intersección con área positiva se mide sobre el elipsoide WGS84 en metros cuadrados; puntos/líneas aportan cero. Huecos se restan y las partes poligonales se suman. Geometrías inválidas o CRS incompatibles se rechazan sin reparación automática.

Los bordes lineales en longitud/latitud se densifican, sólo al integrar el área, con paso máximo 0.0005 grados. Esto aproxima su trayectoria nativa con segmentos geodésicos cortos y reduce la discrepancia entre área del polígono y suma de sus partes. No cambia el polígono original ni el ráster. La orientación de los anillos se normaliza antes del cálculo de área firmada.

Referencias de implementación: [área elipsoidal en PyProj](https://pyproj4.github.io/pyproj/stable/api/geod.html#pyproj.Geod.geometry_area_perimeter) y [densificación en Shapely](https://shapely.readthedocs.io/en/stable/reference/shapely.segmentize.html).

Se comprobó convergencia con paso 0.00025 y se contrastaron las áreas mediante una proyección equivalente LAEA elipsoidal con bordes más densos. Máxima diferencia relativa frente a LAEA: 1.09e-8. En los seis ejemplos la diferencia de media al refinar el paso fue inferior a 2.2e-8 en las unidades de cada variable. No se sustituyó el área declarada de origen por esta área calculada.

Los pesos espaciales usan área intersectada total. Los pesos del promedio se normalizan únicamente entre áreas con dato válido del mapa. NoData se conserva como ausente, nunca como cero. Cobertura válida = área con dato / área física del polígono; se registra también el cociente bruto. Sólo un exceso numérico sobre 1, dentro de la tolerancia relativa 1e-6, se limita a 1. Esta tolerancia es numérica y no un umbral de calidad de datos. Los contactos con área cero no entran en los pesos.

La identidad de cuadrícula exige igualdad de CRS, transformación completa y dimensiones. Una diferencia de origen exige pesos nuevos. El soporte se crea para una geometría concreta cuya huella se registra; no se reutiliza entre parcelas. Las máscaras de NoData se revisan en cada mapa. En esta fase se reutilizó el soporte de Tmin para Tmax; la reutilización entre todos los meses corresponde al extractor de fase 3.

## Resultados de julio de 2025

| ID | Variable | Celdas con área positiva | Media ponderada | Unidad | Cobertura válida aproximada |
|---|---|---|---:|---|---:|
| AGC_014 | PREC | 30_33, 31_33 | 144.240709787 | mm/mes | 100 % |
| AGC_014 | Tmin | 30_33, 31_33 | 13.446963205 | °C | 100 % |
| AGC_014 | Tmax | 30_33, 31_33 | 22.990844240 | °C | 100 % |
| AGC_065 | PREC | 32_32 | 120.250411987 | mm/mes | 100 % |
| AGC_065 | Tmin | 32_32 | 12.716031075 | °C | 100 % |
| AGC_065 | Tmax | 32_32 | 22.677114487 | °C | 100 % |

AGC_014, lluvia:

| Celda | Área intersectada (m²) | Peso válido | Valor (mm/mes) |
|---|---:|---:|---:|
| 30_33, superior | 20,595.012244 | 0.276911082 | 151.653518677 |
| 31_33, inferior | 53,779.086820 | 0.723088918 | 141.401931763 |

La media es 151.653518677 × 0.276911082 + 141.401931763 × 0.723088918 = 144.240709787. La parcela no se divide en mitades iguales, por lo que no corresponde promediar las dos celdas a partes iguales ni sumar sus lluvias.

Área calculada de AGC_014: 74,374.099606 m². La suma de intersecciones difiere en aproximadamente 0.000541 m²; cobertura bruta 0.9999999927. Es una diferencia numérica, no evidencia de una franja sin dato. AGC_065 ocupa una celda y su media coincide exactamente con el valor consultado por Dani en QGIS.

En temperatura, AGC_014 tiene pesos 0.277039836 y 0.722960164; difieren ligeramente de lluvia porque las cuadrículas tienen distinto origen. Se conserva esta diferencia.

## Pruebas y evidencia

20 pruebas aprobadas: cinco de inventario y 15 espaciales. Las nuevas comprueban ponderación conocida 80/20, NoData parcial y total, cobertura espacial parcial y ausente, contactos de línea/vértice, cuatro celdas, CRS incompatible, cuadrícula desplazada, cambios mensuales de máscara, huecos/multipolígonos/colecciones, geometría inválida, valores no finitos y contraste independiente del área.

Evidencia local en `reports/t04_fase2_20261006/`: `pruebas.log`, `casos_reales.json`, `copia_qgis.json`, `verificacion_final.json` y logs de ejecución. Durante la revisión se corrigieron referencias duplicadas del árbol de QGIS y el uso obsoleto de multiplicación Affine en el código nuevo; la iteración inicial se conservó como respaldo. Persiste únicamente el aviso de biblioteca ya observado en las pruebas del inventario; no produjo fallos.

Los 18 archivos protegidos mantienen sus huellas: originales, proyecto QGIS anterior, T03, dependencias e instrucciones privadas. Commit, stash e índice se conservaron. No hubo publicación remota ni se inició Docker.

## Reproducir

Desde la raíz del repo con el entorno local activado:

```sh
python scripts/preparar_qgis.py
python -m unittest discover -s tests -v
python scripts/t04_espacio.py --paquete data/raw/DataSet.zip --salida reports/t04_comprobacion/casos_reales.json
```

El primer comando requiere una sesión previa guardada en `reports/t04_revision.qgz` con estas cuatro capas. Prepara la copia desde el maestro y conserva el proyecto anterior. Si encuentra una copia o proyecto de trabajo diferente, se detiene para no sobrescribir cambios; no debe usarse para descartar una sesión de QGIS guardada posteriormente. Las rutas del proyecto son relativas al repositorio.

## Siguiente fase

Fase 3: implementar extracción de los 197 IDs por variable/mes, reutilización verificada por cuadrícula, tabla de celdas/pesos, cobertura y trazabilidad, y comparación con centroide. Conciliar el catálogo T02 aceptado; conservar disponibilidad/versiones no documentadas y el protocolo provisional T03. No elegir ventanas, filtros de calidad ni cambiar particiones durante esta comprobación. Cierre de T04 y PR requieren la revisión independiente de Jass y autorización específica de Dani para push.
