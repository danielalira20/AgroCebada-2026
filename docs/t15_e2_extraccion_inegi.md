# T15 E2 · extracción INEGI y auditoría

## Resultado verificado · 16 de octubre de 2026

- **197/197 parcelas**, tres atributos y **591 valores finitos**, sin faltantes.
  Cobertura completa dentro de la tolerancia previa, incluyendo las 59 reservadas;
  eso no sustituye su futura evaluación de aplicabilidad predictiva.
- **67,762 intersecciones parcela-celda** auditadas, 788 desplazamientos de control
  y **1,906,004 comprobaciones por auditoría** en Mac y Linux. El auditor recalcula
  78,753 celdas distintas contando las necesarias para los controles.
- **24 pruebas** aprobadas en cada sistema; otras cuatro guardias pasan con Python
  optimizado. Cuatro corrupciones de archivos rechazadas y cuatro errores de cálculo
  detectados incluso al recalcular sus huellas. Los 27 oráculos y diez negativos del
  contrato también siguen aprobados; 34 fuentes comunes y seis originales intactos.
- Comparación Mac/Linux: **8,077 comprobaciones aprobadas**, IDs y conteos de celdas
  exactos. Diferencias máximas TPI `1.681e-11 m`, Este `7.796e-13` y Norte `5.100e-13`:
  inferiores a los límites previos `1e-6 m` y `1e-9`. La tabla compartida canónica es Linux.
- Auditor Linux frente a su recálculo independiente: TPI máximo `2.291e-12 m` y
  componentes por debajo de `3.4e-15`. Reproyección por ventana frente al raster completo:
  diferencia cero en las ventanas auditadas. Error relativo máximo de cierre de área
  `7.03e-13`; margen fuente mínimo **1,731.91 m**, superior al exigido de 210 m.

| Atributo | Mínimo | Mediana | Máximo |
|---|---:|---:|---:|
| TPI150 medio (m) | -5.580846 | -0.062519 | 4.680058 |
| Exposición Este media | -0.139472 | -0.001136 | 0.092671 |
| Exposición Norte media | -0.144775 | 0.000370 | 0.123936 |

Cada parcela toca entre 28 y 2,993 celdas con área positiva (mediana 289). En los
788 desplazamientos, la mediana del cambio absoluto de TPI es **0.04399 m**, el
percentil 95 **0.40796 m** y el máximo **1.89055 m**. No se escoge ni corrige una
geometría con esos resultados. Las coberturas brutas difieren de uno sólo por
redondeo de áreas (hasta aproximadamente `7.1e-13`); no se oculta ese redondeo.

La caché de vecindarios del auditor mantuvo exactamente las diferencias y los
controles del cálculo sin caché; la medición Mac pasó de 75.6 a 43.2 s. No es una
promesa de rendimiento en cualquier equipo. La emulación Linux tardó aproximadamente
13.6 min en extraer y 12.4 min en auditar. El paquete compacto ocupa unos **192 KiB**;
los rasters de respaldo permanecen locales. Colima quedó apagado al terminar.

**Cero modelos E2 ajustados y cero métricas predictivas E2 calculadas.** Esta etapa
verifica nuevos datos y su procedencia, no demuestra una reducción del MAE.

## Problema que resuelve

La factibilidad acreditaba cobertura del CEM, pero aún no existían los tres atributos
de relieve local para cada parcela ni una comprobación independiente de sus cálculos.
La resolución de 15 m no equivale a exactitud de 15 m ni demuestra utilidad predictiva.

## Solución que implementa

`scripts/t15_e2_extraer.py` produce una tabla lateral de 197 filas y tres atributos:
posición topográfica TPI a 150 m, componente de exposición Este y componente Norte.
`scripts/t15_e2_auditar.py` los recalcula desde originales, sin importar el extractor.
`scripts/t15_e2_comparar.py` contrasta las reproducciones Mac/Linux con las tolerancias
previas. No se incorporan etiquetas, no se eligen ventanas y no se ajustan modelos.

El contrato histórico `registro/t15_e2/contrato_tecnico_v1.json` permanece intacto,
incluidos sus indicadores de la etapa de diseño. La autorización de esta etapa está
en `registro/t15_e2_extraccion/registro_operativo_v1.json`; no habilita entrenamientos.

## Separación de datos y trazabilidad

- Fuente única: CEM3.0 INEGI previamente descargado, huella `5f315dd3…648be95`.
  Ninguna descarga ni consulta nueva de ubicaciones.
- Cinco archivos vectoriales originales protegidos por huella y los mismos 197 IDs
  de `registro/t07/catalogo_base.csv`. Se lee sólo `ID_POLIGON` y geometría del vector;
  del catálogo sólo se utiliza el ID. Las 34 fuentes comunes se comprueban por huella,
  sin usar sus valores de rendimiento en los cálculos.
- Fuentes, T07, particiones, resultados anteriores y contrato permanecen intactos.
  Los tres atributos estáticos no multiplican ejemplos ni filas por ventana.
- Derivados completos, rasters y detalle de pesos están en `reports/` ignorado por Git.
  Las tablas compactas y sus verificaciones se conservan en la entrega local de registro.

## Fórmulas aplicadas

Rejilla UTM14 EPSG:32614, 15 m, 3703×3507, alineada al origen fijo. Reproyección
bilineal única en float64. Una máscara original 0/1 se remuestrea sin interpretar
el cero como NoData: soporte menor que `1−1e−12` invalida la altura. Cero de altura,
TPI o exposición observado no se convierte en faltante.

TPI = altura de la celda menos media de sus 316 vecinos cuyos centros se encuentran
dentro del radio de 150 m; se excluye la celda central. Centro y todos los vecinos
deben ser válidos. No es el TPI de ventana predeterminada de otro programa.

La orientación usa Horn 3×3 con escala UTM local y corrección de convergencia al
norte verdadero. Se promedian las componentes `sin(inclinación)×sin(azimut)` y
`sin(inclinación)×cos(azimut)`, nunca los ángulos. Un plano da dos ceros válidos.
No se aplica umbral predictivo de pendiente ni se normaliza a longitud uno la
resultante media. Las fórmulas exactas constan en el contrato y en las pruebas.

La agregación pondera por área estrictamente positiva de intersección entre celda
y parcela en UTM. Un contacto de borde pesa cero. Se exige cierre relativo de área
`1e−8` y cobertura de cada atributo `≥1−1e−8` en cada parcela. Un faltante se conserva
con su ID y motivo, y bloquea esta versión: nunca se imputa ni elimina una parcela.

## Hallazgos durante la implementación y resolución

1. El primer guard bloqueó correctamente el shapefile por contener PolygonZ. La
   inspección comprobó 197 polígonos y 6,431 vértices, todos con Z=0. Ahora se retira
   sólo esa dimensión constante al leer, preservando X/Y y el archivo. Z no nula
   requiere revisión y detiene el proceso; no se confunde con elevación del CEM.
2. La documentación de WarpedVRT permite por defecto una aproximación de 0.125 píxel
   en la transformación. Se fijó `tolerance=1e−12` antes de obtener atributos, para
   reducir aproximaciones dependientes de ventanas. No se cambió ningún criterio
   por resultados de MAE. La auditoría vuelve a reproyectar ventanas desde el original.
3. Se comprobó con una superficie conocida que GDAL puede devolver altura interpolada
   cuando falta un contribuyente; la máscara independiente evita aceptarla como
   soporte completo. TPI y Horn también propagan los faltantes de sus vecindarios.

No hubo cambios en etiquetas, protocolo, particiones, alturas del original ni
datos meteorológicos/satelitales. Ninguno de estos hallazgos implica un fallo en
las predicciones anteriores: esta es una fuente adicional todavía no evaluada.

## Auditoría y controles

El productor usa convolución para TPI, operaciones matriciales para Horn, componentes
cartesianas e intersecciones vectorizadas. El auditor usa vecindarios enumerados,
`math.fsum`, productos con los dos stencils Horn, inclinación/azimut polar e
intersecciones escalares. Recalcula todos los agregados y pesos, las doce columnas
de calidad y los 788 desplazamientos de ±15 m Este/Norte. Comprueba también margen
completo de 210 m, archivos, IDs y ausencia de pesos duplicados o extra.

Ambos comparten GDAL, PROJ y GEOS: es independencia del cálculo y de implementación,
no una certificación independiente de esos motores ni del levantamiento original.
La auditoría tampoco certifica agronómicamente los valores del terreno.

Los desplazamientos son una sensibilidad descriptiva, no una estimación de error
real de ubicación ni una búsqueda de geometría mejor. Se conservan las geometrías
originales como única candidata. Sus resultados nunca filtran parcelas.

La caché del auditor se limita a coordenadas globales de celda de este mismo DEM
fijo: no mezcla fuentes, parcelas ni ventanas. Los pesos y agregados se calculan
por cada geometría de forma independiente.

Las pruebas usan planos, rampas, un cuenco con solución exacta, orientación cardinal,
offset vertical, píxeles 80/20, contacto de borde, faltantes bilineales/TPI/Horn,
distintos tamaños de tile, IDs repetidos, fuentes alteradas, Z no nula y salidas
existentes. Son superficies matemáticas; no son rendimientos simulados.

Los resultados finales y diferencias numéricas figuran en
`registro/t15_e2_extraccion/resumen_QA.json` y sus auditorías.

## Reproducir

Desde la raíz, con los originales locales acreditados y las dependencias fijadas:

```bash
.venv/bin/python -m unittest discover -s tests -p test_t15_e2.py -v
.venv/bin/python scripts/t15_e2_extraer.py --salida reports/e2_entrega_nueva
.venv/bin/python scripts/t15_e2_auditar.py --entrega reports/e2_entrega_nueva --salida reports/e2_auditoria_nueva.json
.venv/bin/python scripts/t15_e2_comparar.py --a reports/e2_entrega_nueva --b reports/e2_entrega_linux --salida reports/e2_comparacion_nueva.json
```

Cada salida debe ser nueva; no se sobrescribe evidencia. La entrega canónica es la
de Linux/amd64 con la imagen común `b2dea1bd…5aa`, sin red, 768 MiB y dos CPU como
límites del contenedor, un hilo GDAL/BLAS y caché de 32 MiB. El repositorio se monta
de sólo lectura y una carpeta de resultados separada permite las escrituras.
No se necesita mantener Docker encendido para consultar estas tablas.

## Límites y próximo paso

Los metros verticales se atribuyen a la ficha del producto; el datum vertical y
la disponibilidad de estos mismos bytes al corte de 2025 no están acreditados.
No se asigna el CRS histórico de otra ficha al TIFF actual EPSG:4326. La invariancia
a un offset Z constante no resuelve posibles errores espaciales ni de datum.

No se sabe todavía si E2 reduce MAE, RMSE o mejora R². Primero hay que adaptar y
auditar el modelo común v3 con estas columnas, verificar el centrado H3 dentro
de cada entrenamiento, registrar código y tabla canónica y solicitar la evaluación
completa de E2/E12/E2Q ya prevista. No se generan aún las 59 predicciones finales.

## Referencias técnicas y asistencia metodológica

- [INEGI, portal oficial de elevaciones](https://www.inegi.org.mx/app/geo2/elevacionesmex/)
  y [ficha histórica 2013, cuadro 6.9](https://www.inegi.org.mx/contenidos/programas/entic/2013/doc/inf2013.pdf#page=298).
  Procedencia de esta descarga en `registro/t15_inegi_factibilidad/procedencia.json`;
  cobertura y límites históricos en `docs/t15_inegi_factibilidad.md`. Los atributos
  derivados son cálculo del equipo; no son mediciones ni una validación de INEGI.

- [Rasterio WarpedVRT](https://rasterio.readthedocs.io/en/stable/api/rasterio.vrt.html):
  interpolación, tipo de trabajo y tolerancia del transformador.
- [Rasterio warp](https://rasterio.readthedocs.io/en/stable/api/rasterio.warp.html):
  límites densificados y tratamiento de NoData.
- [pyproj Proj](https://pyproj4.github.io/pyproj/stable/api/proj.html): factores locales.
- Kassis, T.; Agarwal, V.; He, Y.; Patel, D.; Brueckner, A. M. (2026).
  [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
  Skills GeoPandas y pensamiento crítico usadas para procedencia, geometría,
  unidades e interpretación; referencia actual comprobada el 16-oct-2026.
