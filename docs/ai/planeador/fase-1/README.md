# Fase 1 · calculadora común y referencia municipal

Estado: **implementada y verificada**, 19 de octubre de 2026, rama `feature/agriultor-prediccion`. No se implementaron fases 2–5. Cebi completo continúa aplazado por trabajo paralelo.

## Qué cambió

- `backend/dominio/planeador.py` agrega `estimacion_municipio(d, municipio, modelo)`: devuelve los ocho campos del contrato v1, usa sólo ENTRENAMIENTO, valida etiquetas/modelo y distingue falta de soporte sin asignar respaldo regional. Se reutiliza el estadístico vigente; no se cambia `predecir`.
- `evaluar_cuenta(...)` prepara la cuenta común con `columnas`, `cuentas`, `rango_municipio` y `equilibrio` existentes. Distingue captura pendiente, inválida y calculada; rechaza valores no finitos/booleanos/desbordamientos y no redondea cifras antes de operar.
- `frontend/vistas/agricultor/calculadora.py` conserva `calculadora(ctx,pid)` como adaptador y extrae `calculadora_base(...)`, que recibe municipio, rendimiento, etiqueta y área sin buscar un ID. Con `area_editable=False` recibe una superficie ya capturada y no dibuja un segundo campo. Aún no hay pantalla de consulta rápida en producción.
- `frontend/estado/planeador.py` conserva precio/costo y áreas por parcela en un diccionario independiente de los widgets. Migra claves anteriores, restaura valores al volver a la vista y conserva None cuando se limpia un campo. `iniciar_sesion()` hidrata lectores antes de dibujar el panel/PDF.
- El lector económico de `componentes/descargas/boton_ficha.py` ahora usa la misma evaluación y distingue área no inicializada (valor del catálogo) de área borrada (sin cuenta). La corrección evita exportar una cuenta distinta a la que ve el usuario.

Rutas anteriores relativas a `app/agrocebada_app/`. Las fórmulas originales, modelo oficial, datos, T18, CSV, CSS, paletas y estructura del recorrido se conservaron. El área ahora admite quedar vacía: la cuenta se considera pendiente y el PDF omite sus filas económicas, conforme al contrato de captura. Su superficie registrada no se borra ni se modifica.

## Diseño y arquitectura

Se mantuvieron los mismos controles, textos, tres columnas del flujo de parcela, contenedor `glass_calculadora`, estilos compartidos y tabla plegada. Los avisos y tarjetas nuevas, el título histórico de temporada y los escenarios visuales siguen para fase 2.

La lógica de referencia/validación/cuentas vive en backend y no importa Streamlit. La gestión de sesión puede probarse con un mapping simple; el frontend sólo monta controles, sincroniza captura y presenta el resultado. No se incorporaron dependencias ni una nueva arquitectura de servicios.

El estado implementa el contrato `planeador` de fase 0; incorpora una marca interna opcional `_area_rapida_inicializada` para distinguir un área nunca inicializada de otra borrada explícitamente. No es un dato de usuario ni una API de dominio. Si no existe la marca y sí existe una superficie canónica, se conserva ésta. Los nombres de compatibilidad `calc_precio`, `calc_costo`, `calc_area_{pid}` permanecen.

## Qué queda fuera de Cebi

No se cambian preguntas, respuestas, diálogo, recursos, animaciones, contenidos ni pruebas propias del bot. La pregunta nueva de C7/fase 5 y cualquier integración adicional están aplazadas. Mantener nombres de claves compartidas y hacer consistente el PDF no equivale a modificar el bot ni certifica su compatibilidad tras los cambios paralelos.

Cuando ese trabajo termine, revisar sus lectores de estado contra este contrato en una tarea separada. La referencia numérica no depende de archivos del bot; por eso los cambios de Cebi no invalidan por sí mismos la base de fase 0.

## Verificación realmente ejecutada

Entorno local de Python 3.12; dependencias de la app ya instaladas. Las pruebas AppTest se ejecutaron en un proceso autorizado fuera del aislamiento que bloqueaba el event loop Windows. No se alteró Python/Streamlit para hacerlas pasar, no se inició servidor ni navegador.

| Comprobación | Resultado |
|---|---|
| `tests/backend/test_planeador.py` | 7 pruebas OK: 0/1/2/3/9/10 cosechas, exclusión de PREDICCION, falta de soporte, modelo/etiquetas inválidos, no finitos/overflow, rango nulo, cosecha registrada fuera del rango, nueve municipios y las 59 en ambos modelos. |
| `tests/frontend/test_estado_planeador.py` | 5 pruebas OK: migración legacy, remontaje, áreas independientes, borrado None y marca interna opcional. No necesita runtime Streamlit. |
| `tests/frontend/test_calculadora_base.py` | AppTest OK: predicción y cosecha registrada, cuenta municipal con contexto sin `pred`/sin ID, campo de área único, precio/costo/área, cambio de vista y vuelta, precio/área borrados, retención y lector PDF antes/después de montar calculadora. |
| `tests/backend/test_calculadora.py` | Regresión existente OK con datos sintéticos/reales; no cambió su código. |
| `tests/backend/test_rangos.py`, `test_confianza.py` | Regresiones existentes OK; temporales de lectura dentro del workspace. Advertencia de R² con varianza cero en fixture conocida, no introducida por esta fase. |
| `tests/frontend/test_descargas_ficha.py` | Regresión existente OK tras el arreglo de área: agricultor/analista, ambos modelos, registrado, confianza y respaldo; PDF de una página en memoria. |
| `tests/frontend/test_tema.py` | Regresión existente OK: contraste de tokens, cambio de tema, conservación de cifras/filtros/vista. No es prueba visual de píxeles. |
| `herramientas/verificar_base_planeador.py` | OK: 59 filas por modelo, métricas, confianza, rangos, cuentas y huellas conservados contra la base inmutable de fase 0. |
| Revisión técnica | Revisión independiente con `pre-pr-review`, seguida de revisión de root; único hallazgo material, área borrada en PDF, corregido y cubierto. Sin hallazgos materiales abiertos. |

Rutas de pruebas/herramienta relativas a `app/`. Evidencia de AppTest en `.agent/fase1-calculadora.log`, `.agent/fase1-descargas.log` y `.agent/fase1-tema.log`; revisión en `.agent/revision-fase-1.md`. Las advertencias `missing ScriptRunContext` corresponden a ejecución de testing y no impidieron finalizar en OK.

## Cambios de alcance registrados

REV-01 de TASK-005 amplió mínimamente el alcance al lector económico del PDF: el campo de área vaciable expuso un fallback que revivía la cuenta con AREA_HA. La interfaz y el lector ahora usan la misma validación; se mantiene el default de catálogo sólo cuando todavía no existe la clave. No se cambió el generador de PDF ni su composición visual.

## Límites y siguiente paso

No se realizó inspección visual en navegador ni pruebas en Docker. El cambio de tema y el formulario sí se ejecutaron con AppTest; no se declara aceptación visual de pantallas futuras. No se reentrenó el modelo ni se resolvieron aprobación T16/huella histórica T18.

La siguiente fase es 2: escenarios visibles, equilibrio, bloque de faltante y lenguaje histórico. Fase 3 agregará el selector y la consulta rápida que consuman este componente. No están implementadas en esta entrega; fase 5/todo Cebi siguen aplazados.
