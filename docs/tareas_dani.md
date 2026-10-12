# Tareas de Dani

Consulta de la pestaña [Plan unificado corregido](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk/edit?tab=t.q0k09ka9rtmy), 5 de octubre de 2026. Las fechas siguientes son las metas del plan aprobado; no indican que la entrega ya esté hecha.

| Tarea | Fecha objetivo | Entrega de Dani | Revisor |
| --- | --- | --- | --- |
| T01 · espacio común | 3–4 oct | Entorno, contrato y repositorio compartido. Pruebas locales aprobadas; pendiente validar equipo, accesos, capitán y revisión. | Diego |
| T04 · clima | 3–5 oct | Lluvia, Tmin y Tmax por polígono y periodo; área física, cobertura, unidades, disponibilidad y comparación con centroide. | Jass |
| T07 · tabla común | 4–6 oct | Catálogo primero; integrar clima, relieve y satélite por bloques: 197 IDs únicos, 59 etiquetas ausentes y trazabilidad. | Jass |
| T09 · aporte climático | 6–8 oct | Territorio, clima solo y ambos: mismas particiones, estimador y presupuesto; métricas y predicciones por ID. | Migue |
| T15 · combinaciones | 8–9 oct | Comparaciones pequeñas predefinidas con territorio, clima, relieve y satélite; conservar referencia sola. | Daf |
| T16 · cierre del procedimiento | 9–12 oct | Consolidar selección y evaluación; congelar entradas, procesamiento y modelo con ficha de decisión. | Migue |
| T18 · ejecución final | 12–15 oct | Ajustar el procedimiento congelado con 138 etiquetas y producir exactamente 59 predicciones; cotejar con app y guardar trazabilidad. | Migue |

Dani revisa T02 (catálogo de Jass), T05 (relieve de Jass) y T17 (app de Diego). Aporta a T19 evidencia y texto de su frente. **T14 es responsabilidad de Migue**, quien recibe las entregas T04 y T09 de Dani.

## Orden inmediato

1. T04: inventariar el ZIP completo de originales. La carpeta extraída previamente no contenía toda la lluvia; no usarla como única fuente.
2. La versión 83aba4f de T02 ya se revisó y reprodujo; se solicitaron ajustes antes de aprobar. Conciliar con el catálogo aceptado antes del cierre de T04. Los IDs y geometrías originales verificados permiten preparar las comprobaciones espaciales.
3. Implementar ponderación espacial en áreas físicas, NoData y tabla de calidad; comparar con centroide. No imponer una celda única ni sumar lluvia de celdas vecinas.
4. T07: integrar por ID los bloques entregados sin esperar a que estén todos. Referencias de Migue pueden avanzar desde T02–T03.
5. T09: recibir particiones y reglas de T03, referencias de T08 y acordar el experimento antes de evaluar.

## Uso de memoria

Trabajar habitualmente con `.venv`; Docker no necesita estar encendido. Para una comprobación Docker usar `colima start --vm-type vz`; al terminar usar `colima stop`. Esto conserva los archivos y las imágenes.

## Inicio reproducible de T04

Desde la raíz del repositorio, sin Docker:

```sh
source .venv/bin/activate
python scripts/inventariar_clima.py --paquete data/raw/DataSet.zip --salida reports/t04_comprobacion/inventario_clima.json
```

En Windows se activa con `.\.venv\Scripts\Activate.ps1` y se pasa la ruta local del ZIP entre comillas si contiene espacios. Con este comando el informe queda en `reports/t04_comprobacion/inventario_clima.json`, excluido de Git. El script comprueba CRC al leer cada archivo, calcula hashes, registra documentación original y lee los 144 mapas climáticos; rechaza meses faltantes, extras o duplicados. No modifica ni extrae los originales, ni decide su admisibilidad temporal. Las unidades se verifican en los LEEME y metadatos de cada producto, no por el nombre del ZIP.

## Continuidad del 6 de octubre

Fase 1 recuperada y verificada: cinco pruebas aprobadas, 144 mapas inventariados y proyecto QGIS guardado con cuatro capas. El detalle está en [inicio de T04](t04_inicio.md). Los pesos físicos de AGC_014 y el extractor completo siguen pendientes.

Se detectaron auxiliares de estadísticas añadidos a las copias interiores usadas en QGIS; los GeoTIFF originales coinciden con el ZIP maestro, que permanece intacto. Antes de cambiar rutas o restaurar esas copias, acordar con Dani la separación entre originales y copia de visualización. La fuente autoritativa del inventario es data/raw/DataSet.zip.

La fase 2 ya tiene comprobación técnica aprobada y copia QGIS preparada. Consulta [fase 2 de T04](t04_fase2.md). Abrir reports/t04_revision_trabajo.qgz para continuar la visualización; el siguiente desarrollo corresponde al extractor completo de fase 3.

## Estado tras las fases 3–4 · 6 de octubre

Las notas anteriores describen etapas previas. El [informe completo de T04](t04_fase3_completa.md) registra centroide, piloto, 28,368 filas reales, controles y reproducción en dos ejecuciones. Pasaron 48 pruebas; originales y T03 se conservaron. El borrador del PR queda local hasta que Dani revise y autorice los archivos concretos.

Siguiente revisión de Dani/Jass: conciliar con T02 aceptada; inspeccionar AGC_078, AGC_152 y AGC_182 por centroide exterior y AGC_145 por diferencia de lluvia. Coordinar con Migue/Jass las celdas compartidas entre particiones espaciales de T03 antes del modelado. Una extracción disponible no acredita la disponibilidad histórica del producto: las ventanas admisibles siguen sujetas al protocolo. T07 integra por ID los bloques aceptados; T09 todavía requiere su experimento acordado. Docker sigue siendo bajo demanda.

## Correcciones de entrega · 7 de octubre

Jass informó validación independiente del cálculo T04. El PR 6 existe con destino dev; las notas del 6 de octubre conservan estados históricos. La [entrega mensual al equipo](t04_entrega_equipo.md) incorpora tabla compacta, conciliación calculada con T02 identificada y diccionario. Las medias originales permanecen idénticas. Dani autorizó publicar estas correcciones en el PR 6 hacia dev el 7 de octubre; la nueva revisión de Jass y el cierre de T04 siguen pendientes.

La [revisión temporal](t04_version_disponibilidad.md) diferencia observación, publicación y edición del producto. No fija ventanas ni cambia T03. Siguiente conversación: punto 5, responsable y reglas de agregación por ventana/documento para T07. T09 no empieza por disponer del CSV: requiere protocolo y experimento acordados.

## Diseño T09 fijado · 11 de octubre de 2026

Dani autorizó cerrar el diseño sin esperar respuesta de Migue. [Diseño v1.0](t09_diseno.md), [razones y evidencia](t09_decisiones.md) y [configuración](../registro/t09/diseno.json): referencia exacta, clima solo, municipio + clima y corrección residual; ventanas/regularización/selección fijadas. La revisión independiente sigue pendiente; la fase de diseño no entrena modelos ni cierra T09. El siguiente paso es preflight y desarrollo de estimadores con controles de fuga, antes de evaluación oficial.

## Estimadores T09 verificados · 12 de octubre de 2026

Rama `t09-territorio-clima`: [implementación y pruebas](t09_estimadores.md) de los cuatro procedimientos del diseño. Pasan 299 pruebas Mac y 59 Docker; fuente/diseño intactos. Las comprobaciones numéricas son controles, no resultados de la evaluación completa. Próximo paso: ejecutor externo y reportes, ejecución según diseño y revisión de Migue. No hay ganador ni entrega definitiva para las 59.
