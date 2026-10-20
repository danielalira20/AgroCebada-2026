# TASK-008 — Revisión independiente de fase 2

Type: VALIDATION. Status: DONE. Owner: revision_fase2. Fecha: 2026-10-19.
Depends On: TASK-007 implementación y pruebas iniciales listas.

## Objective / Inputs / Contracts
Auditar únicamente fase 2 contra docs/ai/planeador/fase-0/contratos-v1.md y TASK-007. Cambios locales sin commit; HEAD efbb2dd3c82b254550232f42e1ff7b1c51c351c0 (verificar SHA con git; no suponer). Comparación exacta fase 2 disponible en .agent/fase2/antes/ con los cinco archivos previos; no atribuir cambios de fase 1 a esta fase. Archivos nuevos: componentes/escenarios/, test_escenarios.py y test_calculadora_visual.py.

## Allowed Scope
Leer completos dichos archivos y sus dependencias pertinentes: backend/dominio/planeador.py, vistas/agricultor/calculadora.py, verdor_clima.py, componentes/descargas/boton_ficha.py y assets/css/tema.css, todos bajo app/. Revisar correspondencia tarjetas/tabla/PDF, soporte escaso, referencias registradas, estados de orientación, precisión, bar con umbral externo y colisiones, accesibilidad y responsive. Puede ejecutar tests backend sin servicios. Escribir exclusivamente este contrato y .agent/revision-fase-2.md.

## Out of Scope
No modificar fuentes ni pruebas, no ejecutar AppTest/servicios, no tocar Cebi, datos/modelos/configuración, commits o ramas. No subagentes adicionales. Root ejecuta integración y hace segunda pasada. Excluir artefactos previos .pr-suggestions/ y Claude outputs/.

## Expected Outputs / Acceptance Criteria / Definition of Done
Informe en español con alcance y limitaciones; hallazgos reales con ruta:línea, caso concreto, impacto, intento de refutación y recomendación; ausencia explícita si no hay defectos materiales. Leer cambios completos, contrastar contrato/callers y registros de pruebas sin atribuir ejecución propia. Resumir a root; no afirmar validación de píxeles/navegador.

## Findings / Deviations / Final Result
Revisión terminada sin candidatos materiales confirmados. Informe en `.agent/revision-fase-2.md`; ejecución propia backend 8/8 OK, logs de root inspeccionados por separado. Sin QA visual ni AppTest propios; Cebi excluido. Confirmadas también las últimas correcciones de escape, docstring PDF y prueba $0.50. Root conserva la decisión y verificación globales.
