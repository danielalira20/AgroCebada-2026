# TASK-012 — Revisión independiente de integración y evidencia

Type: VALIDATION. Status: DONE. Owner: revisor. Fecha: 2026-10-19.
Depends On: TASK-011 correcciones iniciales; root continúa navegador y suite final.

## Objective / Inputs / Contracts
Revisar cambios fase 4 y disciplina de aceptación contra TASK-011 y contratos v1. Local-only sin commit; HEAD efbb2dd3c82b254550232f42e1ff7b1c51c351c0. Comparar sólo snapshots .agent/fase4/antes/ frente a actuales; fases previas no se atribuyen a esta fase.

## Allowed Scope
Cuatro deltas: app/assets/css/tema.css, frontend/tema/html.py, vistas/agricultor/calculadora.py y consulta_rapida.py; nueva app/herramientas/verificar_planeador.py. Leer callers/tests pertinentes y evidencia docs/ai/planeador/fase-4/ a medida que root la guarda. Revisar tamaños CSS/semántica de headings, default del helper sin alterar Cebi, integridad de runner (errores/timeouts/huellas), ausencia de cambios numéricos. Puede ejecutar --help del runner o comprobaciones de lectura, sin ejecutar suite AppTest/servidor ni navegador. Escribir sólo este contrato e informe .agent/revision-fase-4.md.

Ampliación comunicada por root: revisar la corrección singular/plural en consulta_rapida y su aserción existente (snapshot de test guardado), así como cwd=APP y huellas numéricas/configuración/requirements añadidas al runner. La evidencia visual anterior fue exploratoria al iniciar servidor desde raíz; root repetirá matriz desde app/ para cargar su configuración real. Nueva suite completa final: 20261020T005812834946Z.

## Out of Scope
No cambios a código/pruebas, Cebi/activos/pruebas propias, datos/modelo/fórmulas, commits/despliegue; no subagentes. No declarar apariencia vista por otro como inspección propia.

## Expected Outputs / Acceptance Criteria / Definition of Done
Informe español con hallazgos materiales ruta:línea, caso/impacto y refutación; o ausencia con límites. Leer deltas/nuevo archivo completos, contrastar scripts/hashes del manifiesto y contratos/callers, distinguir evidencia de root de pruebas propias. Revisar que pendientes visuales o de aprobación humana no queden marcados pasados sin evidencia. Root integra y hace segunda pasada. Notificar si requiere ampliar alcance; no reparar.

## Findings / Deviations / Final Result
Revisión completada en `.agent/revision-fase-4.md`: sin candidatos materiales, approve local limitado a fase 4. Leídos deltas/snapshots/runner ampliados, pruebas pertinentes, README y matriz final; comprobadas las 17 salidas 0, logs y hashes actuales del manifiesto final 20261020T005812834946Z desde app/. Cotejados 24 registros únicos de viewport/capturas y teclado. La comprobación de zoom procede del usuario, comunicada por root y atribuida en los registros. Sin navegador/AppTest propios ni cambios fuera de contrato/informe. Root actualiza estados administrativos de sus documentos y conserva exclusiones Cebi/T16/T18/publicación.
