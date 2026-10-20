# TASK-002 — Auditar datos, dominio y estimación de app

Type: INVESTIGATION. Status: DONE. Owner: investigador backend. Fecha: 2026-10-19.
Depends On: ninguna. Blocks: síntesis de root. ADR: ninguno. Invariantes: PROBLEM_MODEL.md.
## Objective
Trazar fuentes y cálculos de la app, límites científicos, persistencia y efectos de usuario; identificar qué puede reutilizar una futura función de planificación.
## Allowed Scope
Leer app/agrocebada_app/backend/, app/agrocebada_app/config.py, app/herramientas/, app/tests/backend/, frontend/estado y llamadores necesarios. Escribir exclusivamente este contrato (resultados) y docs/ai/auditoria-backend.md.
## Out of Scope
Cambios de implementación, datos, config y pruebas. No leer planeador_campaña.md hasta terminar el mapa actual. No ejecutar pipelines, descargas, servicios ni pruebas; root valida después.
## Inputs
Código vigente efbb2dd; .agent/memory/PROBLEM_MODEL.md. Leer code-architecture-explainer SKILL.md para explicar mecanismos.
## Expected Outputs
Informe español con arquitectura efectiva; localización/carga/paquete; entrenamiento/predicción y validación; cada módulo dominio (confianza, bitácora, calculadora, cartera, clima, evidencia, etc.); seguridad carga; PDF/CSV; persistencia; límites y tests existentes. Evidencia ruta:línea.
## Contracts
Hechos CONFIRMED con evidencia; INFERRED/UNKNOWN con cómo verificar. Reutilización sólo PROPOSED; no inventar futuros contratos.
## Acceptance Criteria
Describir flujo end-to-end y efectos/alcance real de cada cálculo, separar contexto agronómico de entradas del modelo y datos guardados en sesión de datos persistentes. Señalar hallazgos relevantes para nueva campaña.
## Definition of Done
Informe guardado; exclusiones explícitas; sólo archivos permitidos escritos; resumen de hallazgos con referencias a root. Completar resultados abajo.
## Findings / Deviations / Final Result / Handoff
Informe completo: `docs/ai/auditoria-backend.md`.

- CONFIRMED: estimación mediana/media municipio → grupo → global; contexto satélite/clima/altitud/área no altera t/ha. Área sólo afecta cuentas posteriores (`app/agrocebada_app/backend/modelo/estimador.py:10-23`).
- CONFIRMED: paquete tiene prioridad y validación principal se lee de OOF registrado; carga propia valida dejando una parcela fuera (`app/agrocebada_app/backend/datos/paquete.py:13-14,62-73`; `app/agrocebada_app/backend/modelo/metricas.py:17-30`).
- CONFIRMED: bitácora vive en sesión por parcela y CSV, no alimenta entrenamiento/confianza; adjunta estimación 2025 a todos los años; importación descarta identificación y conserva derivados del CSV (`app/agrocebada_app/frontend/vistas/agricultor/bitacora.py:26-32,104-114,129-164`; `app/agrocebada_app/backend/dominio/bitacora.py:103-132`).
- CONFIRMED: rangos comparan parcelas de una campaña, no años; confianza es regla de conteo municipal y error, no probabilidad de cosecha futura (`app/agrocebada_app/backend/dominio/rangos.py:22-48`; `app/agrocebada_app/backend/dominio/confianza.py:29-108`).
- CONFIRMED: cachés PDF/ZIP excluyen contexto/datos; INFERRED: extender a campañas/datasets sin nueva clave puede devolver documentos previos (`app/agrocebada_app/frontend/componentes/descargas/boton_ficha.py:8-12`; `app/agrocebada_app/frontend/componentes/descargas/boton_cifras.py:11-18`).
- C1–C6 contrastados después de cerrar mapa actual, por indicación de root: precisar fallback global sin grupo, conteo municipal, cosecha real vs típico, conservación de estado al alternar modos y versión de datos en cachés. No se editó propuesta original.
- Verificación realizada: lectura de implementaciones, llamadores y pruebas existentes. Sin ejecución de tests/pipelines/servicios/descargas; UNKNOWN: resultados reales en este entorno. Root valida posteriormente.
- Desviaciones: ninguna de alcance; lectura de propuesta autorizada por root después del mapa. Sólo se escribieron este contrato y el informe asignado. Sin subagentes.
