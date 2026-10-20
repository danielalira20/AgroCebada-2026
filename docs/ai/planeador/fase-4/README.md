# Fase 4 · integración y aceptación del planeador

Fecha: 19 de octubre de 2026, hora de México; manifiestos UTC del 20 de octubre. Rama `feature/agriultor-prediccion`, cambios locales sin commit sobre `efbb2dd3c82b254550232f42e1ff7b1c51c351c0`.

Estado: **fase 4 completada en su alcance local**: 17/17 scripts aprobados, revisión visual/teclado ejecutada y zoom al 200% confirmado por el usuario. Cebi/fase 5 permanecen aplazados. Esta entrega no constituye despliegue ni aprobación científica de T16/T18.

## Correcciones demostradas

| Problema observado | Corrección y evidencia |
|---|---|
| Streamlit aplicaba 16 px a las cifras de referencia, equilibrio y tarjetas, pese a los tamaños definidos. | Selectores acotados con especificidad suficiente: referencia municipal 44 px y equilibrio/tarjetas 32 px. Medidas DOM en `evidencia/mediciones-visual.json`; comparación exploratoria en `evidencia/antes-escritorio.jpg`. |
| El encabezado de orientación abierto en claro combinaba texto `rgb(41,63,44)` con fondo `rgb(16,24,20)`. | El `summary` dentro de `glass_calculadora` usa los tokens de superficie/texto del tema. Evidencia inicial `antes-contraste.json`; capturas finales claras/oscuras y colores DOM en la matriz. Sin afectar expanders del bot. |
| Títulos visibles de la consulta, referencia y cuenta no eran encabezados semánticos. | `titulo(..., nivel=...)` permite h1/h2 en esas tres llamadas. Las demás llamadas conservan exactamente su representación `div` anterior; no se alteran módulos de Cebi. Se comprobó la estructura accesible en navegador. |
| Nanacamilpa de Mariano Arista mostraba «1 cosechas registradas». | Texto singular «1 cosecha registrada», conservando conteo y cálculo. Prueba existente ajustada y captura final `nombre-largo-claro-320.jpg`. |

Se mantuvieron Inter, paletas, vidrio, radios, controles y distribución del recorrido. No cambian datos, estimador, fórmulas, confianza, rangos ni sus retornos legacy. No se incorporaron dependencias ni se modificaron configuración científica o archivos del bot.

## Entorno y procedencia

La documentación actual de `cua_repl` permite inspección de localhost, viewport y DOM en el equipo local. Esto permitió superar la limitación descrita en las entregas anteriores, basada en una skill histórica de otro proveedor de navegador. Se usó exclusivamente ese navegador para las interacciones; servidor privado en `127.0.0.1:8503`.

También se comprobó una diferencia real entre ejecutar desde raíz y desde `app/`: sólo la segunda carga `app/.streamlit/config.toml`, incluido el tema nativo oscuro y la desactivación del watcher. La aceptación final usa **cwd `app/`**. Las primeras corridas y capturas se conservan como investigación, claramente separadas de la evidencia final.

- Suite final: `evidencia/pruebas/20261020T005812834946Z/resultado.json` y sus 17 logs. Registra directorio real de ejecución, códigos de salida, duración, versiones Python/plataforma, hashes de fuentes, pruebas, configuración y dependencias numéricas, y estabilidad de archivos/base durante la ejecución.
- Corridas exploratorias: `20261020T004424081747Z` (17 scripts) y `20261020T005017043298Z` (4 scripts tras ajustar contraste). Terminaron OK, pero no se usan como aceptación de la configuración final ni del último texto singular.
- `evidencia/entorno.json`: versiones instaladas y huellas complementarias. Las huellas cubren únicamente los archivos enumerados, no el repositorio entero, plugins, navegador o entorno operativo completo.
- Base fase 0 sin regenerar: SHA-256 `04688c4bb1694fdad14f7c5534126d0232cdfb5ca9bd44241c0e80d8c663a2e3`. El verificador compara también las fuentes activas y los resultados congelados de 197/138/59 y ambos modelos.

## Aceptación funcional y visual

La [matriz de aceptación](matriz-aceptacion.md) relaciona casos, comprobaciones y límites. La suite incluye dominio/estado del planeador, cuenta/escenarios/consulta, transiciones de producción, tema, fichas PDF, libreta, smoke test general de las dos vistas y la base numérica. No ejecuta pruebas propias de Cebi ni reentrenamiento científico.

Se guardaron 24 capturas finales: dos recorridos × dos temas × seis anchos. Cada registro contiene viewport, anchos de contenedores, tamaño de cifras, columnas, visibilidad de barra y estado/colores de los detalles. En los contenedores medidos no hubo desbordamiento horizontal; las tarjetas se apilan hasta 700 px y la barra redundante se oculta hasta 600 px. Las capturas muestran estados con faltante y cobertura; las pruebas automáticas cubren además equilibrio, vacíos, centavos, marcas coincidentes y escaso soporte.

Caso reproducible de las capturas: Chignahuapan, consulta rápida de 10 ha, precio $6,000/t y costo $30,000/ha; catálogo AGC_011 con su superficie original (7.17 ha mostradas), conservando precio/costo compartidos. Además de las mediciones de las 24 combinaciones, root inspeccionó capturas representativas de escritorio, puntos de transición y móvil. No se atribuye una revisión de cada píxel a esas mediciones.

| Ancho | Rápida clara | Rápida oscura | Catálogo claro | Catálogo oscuro |
|---|---|---|---|---|
| 320 | [captura](evidencia/rapida-claro-320.jpg) | [captura](evidencia/rapida-oscuro-320.jpg) | [captura](evidencia/catalogo-claro-320.jpg) | [captura](evidencia/catalogo-oscuro-320.jpg) |
| 375 | [captura](evidencia/rapida-claro-375.jpg) | [captura](evidencia/rapida-oscuro-375.jpg) | [captura](evidencia/catalogo-claro-375.jpg) | [captura](evidencia/catalogo-oscuro-375.jpg) |
| 600 | [captura](evidencia/rapida-claro-600.jpg) | [captura](evidencia/rapida-oscuro-600.jpg) | [captura](evidencia/catalogo-claro-600.jpg) | [captura](evidencia/catalogo-oscuro-600.jpg) |
| 700 | [captura](evidencia/rapida-claro-700.jpg) | [captura](evidencia/rapida-oscuro-700.jpg) | [captura](evidencia/catalogo-claro-700.jpg) | [captura](evidencia/catalogo-oscuro-700.jpg) |
| 900 | [captura](evidencia/rapida-claro-900.jpg) | [captura](evidencia/rapida-oscuro-900.jpg) | [captura](evidencia/catalogo-claro-900.jpg) | [captura](evidencia/catalogo-oscuro-900.jpg) |
| 1400 | [captura](evidencia/rapida-claro-1400.jpg) | [captura](evidencia/rapida-oscuro-1400.jpg) | [captura](evidencia/catalogo-claro-1400.jpg) | [captura](evidencia/catalogo-oscuro-1400.jpg) |

Nombre largo y una sola cosecha: [320 px](evidencia/nombre-largo-claro-320.jpg). Las imágenes representan el viewport de la sección; no son capturas completas de toda la página. El nombre seleccionado puede abreviarse dentro del combo, pero se presenta completo en el encabezado y el resumen.

Teclado: flecha y Espacio cambian recorrido; escritura/flecha/Enter eligen municipio; Tab confirma valores; Enter abre y Espacio cierra el detalle. Se comprobó foco visible sin quedar tapado en el detalle, y se preservan las entradas al cambiar de recorrido/tema/vista. Evidencia `teclado.json`.

**Zoom al 200%:** el agente intentó el atajo del navegador integrado sin cambio observable y no presenta una prueba de viewport como zoom real. El usuario confirmó en este chat «Sí, funciona al 200%» al consultar legibilidad y uso de campos, tarjetas y detalles. Se acepta como comprobación manual **atribuida al usuario**, sin atribuir navegador/OS/versiones no comunicadas ni inspección propia. Registro en `zoom.json`.

La revisión de interfaz contrastó etiquetas, foco, jerarquía y contraste con las [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md), adaptadas a la implementación Streamlit existente. Esto no constituye certificación exhaustiva WCAG ni revisión de todos los componentes del repositorio.

## Reproducir la validación

Desde la raíz, con las dependencias y el paquete local disponibles:

```powershell
.venv/Scripts/python.exe -B -X utf8 app/herramientas/verificar_planeador.py
```

El ejecutor cambia a `app/` para cada proceso, asigna un temporal dentro de la carpeta de evidencia y conserva logs de errores/timeouts. No modifica datos ni regenera la base. Sale con error si falla un script, cambia una fuente durante la ejecución o cambia la base. `--caso` permite repetir sólo un script; `--timeout` ajusta el límite por proceso. Un cierre interrumpido deja el manifiesto `EN_CURSO`, no un aprobado.

La app puede revisarse con `streamlit run app.py` desde `app/`. Reiniciar el proceso después de cambios de código/CSS: el watcher está desactivado en esta configuración y el CSS se lee al importar el módulo de estilos.

## Contenido y límites de aceptación

La orientación conserva los tres pasos mínimos de contratos v1 cerrados en fase 0. Es condicional, usa los números capturados y no promete apoyos, seguros, crédito ni cosechas. No se agregó contenido que requiera validar un programa externo. Las cifras y el contexto mantienen su procedencia de 2025.

Revisión independiente: `.agent/revision-fase-4.md`, contrato TASK-012; root integra pruebas y observación de navegador. La evidencia puede apoyar T19; no implica aceptación formal del equipo ni publicación.

Resultado de revisión: sin defectos materiales. El revisor contrastó manifiesto final 17/17, logs, huellas del árbol actual, estabilidad de base/fuentes, los 24 registros/archivos y atribución del teclado/zoom. Root completó la segunda pasada y verificó enlaces locales. Las advertencias conocidas de ScriptRunContext en AppTest y R² con varianza cero en fixture no se presentan como fallos nuevos ni se modificaron para esta entrega.

No se certifica funcionamiento de Cebi tras el trabajo paralelo, interacción de mapas externos, lector de pantalla real, otros navegadores/dispositivos físicos, Docker o instalación pública. T16 y la anomalía histórica de huella T18 siguen pendientes en sus propios alcances. Fase 5 completa permanece aplazada; no se inició ni se hicieron commits/despliegues.
