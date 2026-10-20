# TASK-006 — Revisión independiente de fase 1

Type: VALIDATION. Status: DONE. Owner: revisor. Fecha: 2026-10-19.
Depends On: implementación TASK-005 lista para revisar. Root continúa validación y documentación.
## Objective
Buscar regresiones funcionales/contractuales en la extracción de calculadora, referencia municipal y estado de sesión; contrastar con contratos congelados de fase 0 y promesa de no cambiar apariencia/resultados.
## Allowed Scope
Sólo lectura de fuentes y pruebas; escribir exclusivamente este contrato (resultados) y .agent/revision-fase-1.md. Revisar archivos nuevos backend/dominio/planeador.py, frontend/estado/planeador.py, cambios en estado/sesion.py y vistas/agricultor/calculadora.py; tres pruebas nuevas test_planeador.py/test_estado_planeador.py/test_calculadora_base.py. Todos bajo app/. Leer dependencias necesarias, base y contratos. Ampliación REV-01 autorizada por root: revisar también diff final del lector componentes/descargas/boton_ficha.py y regresión ampliada.
## Out of Scope
No arreglar código; no tocar Cebi/activos/pruebas propias; no ejecutar AppTest ni servicios; no publicar ni cambiar ramas. Excluir cambios previos de fase 0 y artefactos locales .pr-suggestions y Claude outputs. Sin subagentes adicionales: root integra la revisión y realiza su propia segunda pasada.
## Inputs / Contracts
TASK-005 y docs/ai/planeador/fase-0/contratos-v1.md. Base local para diff de tracked: efbb2dd3c82b254550232f42e1ff7b1c51c351c0; cambios de fase 1 son locales, sin commit. Contratos y APIs existentes prevalecen; no marcar preferencia de estilo como fallo.
## Expected Outputs
Hallazgos accionables con ruta:línea, mecanismo, caso reproducible y prioridad; o ausencia de hallazgos materiales con límites explícitos. Comprobar captura/vacío/cero, migración de sesión, widgets desmontados, PDF antes de calculadora, orden de llamadas, valores grandes/no finitos, datos de entrenamiento y soporte nulo. No confundir baseline de números con verificación visual.
## Acceptance Criteria / Definition of Done
Leer diff y nuevos archivos completos, contratos y llamadores; intentar refutar cada candidato con evidencia; distinguir hecho/inferencia y no atribuir test no ejecutado. Guardar informe y resumir a root. Si requiere decisión o ampliar alcance, reportar sin implementar.
## Findings / Deviations / Final Result
Revisión completa, veredicto approve en el alcance local limitado. F-1 [P2] inicial: limpiar área conservaba None y dejaba pendiente la calculadora, pero el PDF sustituía por área del catálogo. Root corrigió REV-01 con get(clave, default) y evaluar_cuenta. Releídos lector/diff y regresión ampliada antes/después de montaje, desmontaje y restauración: F-1 cerrado, ningún hallazgo material abierto. Informe .agent/revision-fase-1.md. Sin ejecución de pruebas/AppTest, cambios de fuentes, servicios ni subagentes por este revisor; root realiza pruebas y segunda revisión. No acredita visuales ni integración Cebi.
