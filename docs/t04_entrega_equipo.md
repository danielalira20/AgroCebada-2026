# T04 · Entrega mensual al equipo y correcciones de revisión

7 de octubre de 2026. Rama de Dani: `daniela-dev`. Esta actualización incorpora las correcciones de los puntos 1–4 al PR 6 con destino `dev`, con publicación autorizada por Dani el 7 de octubre. Permanece pendiente la nueva revisión de Jass. No se integró `dev` en esta rama. Jass informó una validación independiente del cálculo; esta revisión resuelve entrega, trazabilidad y conciliación, y requiere su revisión de los cambios nuevos. No marca T04 cerrada.

## Archivos compartidos

| Archivo | Propósito |
|---|---|
| `registro/t04/clima_parcela_mes.csv` | Historia completa: 197 parcelas × 48 meses × tres variables, 28,368 filas. Nueve columnas solicitadas más centroide exterior y señal de mes posterior al corte. |
| `registro/t04/manifest.json` | Universo, corte provisional, límites de uso, huellas de los archivos y de sus fuentes. |
| `registro/t04/procedencia.json` | Identidad del maestro, catálogo, geometrías, 144 mapas, 394 soportes, métodos, código y entorno. Evita repetir huellas largas en cada fila. |
| `registro/t04/conciliacion_t02.json` | Resultado calculado y diferencias por ID frente a la revisión identificada T02. |
| `registro/t04/controles.json` | Resumen de claves, estados, señales geométricas y temporales. |
| `registro/referencia_t02_t04.json` | Ocho campos espaciales filtrados de T02, revisión/huellas de sus archivos y originales. Sin etiquetas. Permite conciliar sin integrar toda `dev`. |

Los datos completos por celda siguen en `data/processed/t04/`, ignorados. La excepción aprobada para la **tabla derivada compartida** queda en `registro/`: `data/raw/`, los ZIP y las copias QGIS conservan su organización y exclusión de Git. La entrega mensual no es todavía la tabla de ventanas para T07.

Después de publicar estos cambios, el equipo podrá usar el CSV sin volver a ejecutar el extractor ni tener el ZIP. Para comprobar integridad y reglas de la entrega basta Python, sin Docker ni paquetes geoespaciales:

```sh
python scripts/preparar_entrega_clima.py --verificar registro/t04
```

En una terminal donde sólo exista `python3`, sustituir `python` por `python3`; en Windows puede usarse `py -3.12`. El verificador comprueba archivos, claves completas, unidades, estados/ausencias, señales temporales, diferencia con centroide y referencias de mapas/soportes. No recalcula desde los GeoTIFF originales ni certifica disponibilidad histórica o aprobación humana.

Para analizar, leer IDs como texto y unir por `(id_parcela, periodo, variable)`. Antes de construir variables para el modelo, consultar [versión/disponibilidad](t04_version_disponibilidad.md) y el protocolo T03. `posterior_al_corte=False` no significa «disponible» ni «admitido». El [diccionario](t04_diccionario_columnas.md) define todas las columnas y vacíos.

## Conciliación T02 sin una integración prematura

Referencia leída desde el commit `eef8d95ae47d45d877d5a32f769ad01dec2c92fc`, bajo `analisis/auditoria_catalogo_y_etiquetas/`. Se guardan SHA-256 del catálogo, soporte, huellas de entradas y dos scripts de definición. Coinciden las huellas del catálogo original y las cinco piezas del Shapefile con el maestro usado por T04. El resultado se obtiene de nuevo en cada extracción, antes de publicar su carpeta: no se deja «conciliada» como un texto fijo.

Si las tablas T02 originales están presentes localmente, se leen sus columnas espaciales y se comprueban contra las huellas y referencia filtrada. Si cambia esa revisión, el extractor se detiene para identificar/revisar una referencia nueva. Si falta la referencia, registra `no_disponible` y no permite preparar la entrega compacta como conciliada. Esto no equivale a aprobar todos los aspectos de T02.

Resultados: mismos 197 IDs, áreas de origen idénticas, celda de lluvia principal y número de celdas iguales en los 197, fracción de celda principal igual a los cuatro decimales publicados. Los centroides T02 se verifican con su definición planar lon/lat y siete decimales; T04 sigue usando EPSG:6372→4326, igual que T03.

**Hallazgo:** las diferencias no son todas redondeo. El máximo de área T04 frente al área publicada T02 es aproximadamente 0.0028061 % (AGC_073); frente a Geod sin redondear sigue siendo 0.0027912 %, por la definición de borde/área. El máximo de coordenada es 1.1486e-7 grados (AGC_137), incluyendo el método del centroide. La fracción difiere como máximo 4.99984e-5 (AGC_033), dentro de su semipaso de publicación y con igualdad a cuatro decimales.

Cinco áreas Geod quedan tan cerca del punto medio de redondeo que cambia el último decimal al recalcular. La comprobación usa el intervalo publicado de ±0.5e-6 ha y un margen numérico relativo Geod de 1e-8 entre entornos, separado de las tolerancias del motor T04. Es compatibilidad con la precisión de la referencia, no igualdad de texto. Los controles físicos T04 de área relativa 1e-6 y media absoluta 1e-6 permanecen intactos, y ninguna media se recalcula con el método T02.

## Reproducir los cálculos y la entrega

Para recalcular se necesita el entorno del repositorio y `data/raw/DataSet.zip` original con la huella del manifiesto. Los nombres de salida siguientes deben ser nuevos; no se sobrescriben ejecuciones ni la entrega compartida:

```sh
python -m unittest discover -s tests
python scripts/extraer_clima.py --paquete data/raw/DataSet.zip --salida data/processed/t04/completa_equipo_nueva --completa
python scripts/preparar_entrega_clima.py --origen data/processed/t04/completa_equipo_nueva --salida reports/t04_entrega_equipo_nueva --corte 2025-10-31
python scripts/preparar_entrega_clima.py --verificar reports/t04_entrega_equipo_nueva
```

En Mac se activa `.venv` normalmente; Windows usa su activación de PowerShell. El corte debe indicarse explícitamente: el script no cambia ni interpreta por sí mismo el protocolo T03. La copia CSV conserva literalmente los valores originales, incluidos vacíos, signo y precisión; sólo añade la señal de calendario.

## Evidencia de esta revisión

Pasaron 68 pruebas (48 anteriores y 20 nuevas), el piloto de 135 filas y dos extracciones completas. Los siete archivos reproducibles de resultados/control son idénticos byte a byte entre ejecuciones y a los del 6 de octubre. Una lectura independiente con Python/pandas del runtime de Spreadsheets comprobó las 28,368 filas y la igualdad literal de los diez campos compartidos; el campo adicional es sólo el indicador de calendario. CSV completo: 14,668,141 bytes; compacto: 3,318,106 bytes (77.38 % menos). Los cinco archivos de entrega ocupan 3,753,232 bytes.

Las tablas compactas, procedencia, conciliación y controles se reprodujeron con huellas idénticas. El manifiesto de cada reproducción conserva la huella de su manifiesto fuente, que varía por fecha/tiempo/memoria de ejecución. El verificador también pasó usando Python sin paquetes externos (`-S`). Se conservaron las huellas del maestro, ejecuciones anteriores, QGIS, T03 y AGENTS local. No se certifican otras plataformas ni una mejora predictiva.

La evidencia local de esta revisión está en `reports/t04_revision_jass_20261007/`; no se sube. Las ejecuciones del 6 de octubre se conservan intactas. La validación independiente de Jass informada por Dani es evidencia de la revisión previa; las pruebas/evidencia nuevas se registran aparte y no se atribuyen a Jass.

Pendiente: revisión de esta entrega; confirmación temporal donde no consta; discutir responsabilidad, reglas y documento de las ventanas del punto 5. No se agregaron ventanas, no se usaron etiquetas para ajustar y no se modificaron particiones ni modelos.
