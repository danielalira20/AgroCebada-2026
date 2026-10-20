# Fase 3 · consulta rápida sin parcela

Estado: **implementada y verificada funcionalmente**, 19 de octubre de 2026, rama `feature/agriultor-prediccion`. Inspección visual en navegador pendiente. No se inicia fase 4; fase 5 y Cebi completo siguen aplazados.

## Recorrido disponible

CONFIRMED por implementación y AppTest:

1. Agricultor abre en **Parcela del catálogo**, conservando el recorrido anterior. Un selector visible permite pasar a **Consulta rápida**.
2. La consulta empieza con municipio y superficie vacíos. Ofrece los nueve municipios del conjunto de entrenamiento, incluyendo aquellos sin parcelas reservadas. Explica que la cobertura se limita al catálogo disponible.
3. Al elegir municipio, muestra referencia histórica t/ha de 2025, número de cosechas, nivel de confianza y motivo. Las toneladas aparecen sólo con superficie válida; la referencia sigue visible aunque no se hayan capturado precio/costo.
4. Precio y costo alimentan la calculadora común de fases 1–2: respuesta, equilibrio, escenarios, orientación y tabla. La superficie se captura una sola vez antes del resumen; la calculadora recibe esa misma área.
5. Al regresar al catálogo se recuperan municipio, parcela, encuadre y área por ID. Precio/costo son compartidos entre los dos recorridos; el municipio y superficie rápidos son independientes del catálogo. Limpiar un campo conserva el vacío al regresar.

La consulta no solicita ni fabrica ID, no muestra mapa/verdor/clima de una parcela vecina, no genera ficha municipal y no escribe en el catálogo. El PDF de una parcela sigue recibiendo precio/costo vigentes y su propia área.

## Cambios y diseño

- `app/agrocebada_app/frontend/vistas/agricultor/consulta_rapida.py`: nueva vista; compone referencia y confianza existentes y llama `calculadora_base(..., area_editable=False)`.
- `.../vistas/agricultor/vista.py`: selector y enrutamiento; el cuerpo anterior del catálogo queda en `_mostrar_catalogo`.
- `.../estado/planeador.py`: separa controles temporales de modo/municipio canónicos y conserva selección del catálogo mientras sus widgets no están montados. `agri_modo` retiene su significado del contrato; `agri_modo_control` es sólo su widget. La copia opcional `seleccion_catalogo` guarda `agri_muni`, `agri_parcela` y `encuadre_agri`; su restauración respeta valores nuevos de callbacks.
- `app/agrocebada_app/backend/dominio/planeador.py`: helper `municipios_disponibles`, basado exclusivamente en entrenamiento y validación de cosechas. No depende de `ctx.pred` ni amplía respaldo territorial.
- `app/assets/css/tema.css`: estilos nuevos `rapida-*` y contenedor de recorrido; resumen en dos columnas que se apila a 700 px. Se mantienen Inter, tokens, vidrio, radios y controles nativos de la app, sin dependencias ni animaciones nuevas.

Se reutiliza `estimacion_municipio(ctx.d, municipio, ctx.modelo)` y `confianza_parcela(ctx.conf, municipio, fuente)`. Cabecera sigue pasando el modelo oficial a Agricultor aunque el usuario haya elegido otro en Analista. No se modifican fórmulas, datos, estimador, confianza ni rangos.

## Comprobaciones ejecutadas

Python local de `.venv`. Las pruebas AppTest se ejecutaron en proceso autorizado fuera del aislamiento que bloquea los sockets internos de Streamlit en Windows. Sin servidor ni publicación.

| Comprobación | Resultado |
|---|---|
| `app/tests/backend/test_municipios_planeador.py` | 2 pruebas OK: municipio con entrenamiento sin reservadas, exclusión de municipios sin cosechas, catálogo vacío y rechazo de cosechas inválidas. |
| `app/tests/frontend/test_estado_consulta.py` | 4 pruebas OK: modo inicial/retención, municipio independiente, invalidación por cobertura y selección del catálogo sin sobrescribir clics nuevos. |
| `app/tests/frontend/test_consulta_rapida.py` | AppTest OK: nueve municipios, referencia/n y texto/nivel de confianza contra validación A municipal real, contexto sin `pred`/sin ID, área única, vacíos y limpieza, overflow y falta de soporte. Sin mapa ni descarga. |
| `app/tests/frontend/test_recorridos_agricultor.py` | AppTest del programa real con observador del lector PDF: catálogo→rápida→catálogo, municipio/parcela, tema, Analista y modelo alternativo→Agricultor oficial. Áreas 10/8 ha por parcela frente a 7 ha rápida, None retenido, cifras PDF correctas y catálogo inmutable. |
| `test_planeador.py`, `test_estado_planeador.py`, `test_escenarios.py` | Regresiones de fases 1–2: 7 + 5 + 8 pruebas OK. |
| `test_calculadora_base.py`, `test_calculadora_visual.py` | AppTest de cuentas/estado/escenarios y contexto sin clima OK. |
| `test_tema.py`, `test_descargas_ficha.py` | Contraste de tokens y alternancia de tema/vista OK; descargas de ambas vistas, ambos modelos en Analista y PDF de una página OK. |
| `test_calculadora.py`, `test_rangos.py`, `test_confianza.py` | Regresiones OK. Advertencia conocida de R² con varianza cero en fixture, sin cambio en la fórmula. |
| `app/herramientas/verificar_base_planeador.py` | OK: 197/138/59, ambos modelos, métricas, rangos, confianza y cuentas conservados. |
| Revisión independiente y segunda pasada de root | Sin defectos materiales confirmados. Informe `.agent/revision-fase-3.md`, contrato TASK-010. |
| `git diff --check` | OK. |

Los scripts sin prefijo de ruta de las filas de regresión están en `app/tests/backend/` o `app/tests/frontend/`, según su responsabilidad. Logs locales: `.agent/fase3-backend.log`, `fase3-consulta.log`, `fase3-recorridos.log` y `fase3-regresion-{cuenta,escenarios,tema,ficha}.log`. Las advertencias ScriptRunContext del runtime de testing no impidieron finalizar en OK.

La base de fase 0 no se regeneró. SHA-256 de `base.json`: `04688c4bb1694fdad14f7c5534126d0232cdfb5ca9bd44241c0e80d8c663a2e3`. Snapshots anteriores exactos para aislar esta fase de cambios previos sin commit: `.agent/fase3/antes/`.

## Límites y continuidad

UNKNOWN: apariencia renderizada a 320–1400 px, zoom, foco/teclado y lector de pantalla real. El navegador disponible en la sesión no permite validar el servidor local; no se sustituye esa aceptación por AppTest. No se ejecutó Docker ni se verificó publicación.

No se modificaron ni ejecutaron pruebas propias de Cebi. El catálogo conserva su recorrido existente; esto no certifica compatibilidad con los cambios paralelos del bot. T16 y huella histórica T18 siguen pendientes según fase 0.

La siguiente fase es 4: integración y aceptación, especialmente revisión visual/teclado y evidencia para T19. No se ha iniciado ni se hizo commit o despliegue.
