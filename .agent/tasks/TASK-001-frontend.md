# TASK-001 — Auditar funcionamiento visible y UI/UX

Type: INVESTIGATION. Status: DONE. Owner: investigador frontend. Fecha: 2026-10-19.
Depends On: ninguna. Blocks: síntesis de root. ADR: ninguno. Invariantes: PROBLEM_MODEL.md.

## Objective
Explicar profundamente qué se muestra y qué acciones ocurren en cada vista y módulo de la app, con reglas visuales reales para ampliar su experiencia coherentemente.
## Allowed Scope
Leer app/agrocebada_app/frontend/, app/assets/, app/tests/frontend/, app/.streamlit/, app/app.py y dependencias de backend necesarias. Escribir exclusivamente este contrato (secciones de resultado) y docs/ai/auditoria-frontend.md.
## Out of Scope
Implementación, modificaciones a fuentes, datos, configuración o pruebas; leer la propuesta de planeador antes de terminar el mapa actual; ejecutar servidores o pruebas que muten datos. No usar navegador ni abrir servicios.
## Inputs
Código vigente en efbb2dd; .agent/memory/PROBLEM_MODEL.md. Usar code-architecture-explainer y ui-ux-pro-max según corresponda, leyendo sus SKILL.md. No se necesita investigación web para explicar código local.
## Expected Outputs
Informe en español por pantalla/submódulo: contenido, controles, flujos, filtros y estado, responsive, tokens, patrones reutilizables, accesibilidad, riesgos y pruebas. Referencias ruta:línea.
## Contracts
Cada afirmación factual: CONFIRMED + evidencia. Recomendaciones: PROPOSED. Incertidumbre: UNKNOWN/INFERRED. No rediseñar ni fijar contratos futuros.
## Acceptance Criteria
Cubrir bienvenida/cabecera, agricultor completo, todas las pestañas del analista, datos propios, mapas/gráficas/descargas, estado y estética claro/oscuro/móvil. Diferenciar observado en código de verificado en navegador.
## Definition of Done
Informe guardado; fuentes revisadas; exclusiones declaradas; sólo archivos permitidos escritos; resumen a root de hallazgos importantes con evidencias. Completar resultados abajo.
## Findings / Deviations / Final Result / Handoff
Estado de resultado: COMPLETE (2026-10-19).

Informe: `docs/ai/auditoria-frontend.md`. Incluye flujo de entrada/bienvenida/cabecera, Agricultor completo, siete pestañas del Analista, carga propia, mapas/gráficas/descargas, estado, tokens claro/oscuro, responsive, accesibilidad y cobertura leída de catorce scripts de frontend. Cada comportamiento se apoya en rutas y líneas; ejecución visual y resultado actual de pruebas quedan UNKNOWN.

Hallazgos de mayor impacto: F-01 promesa de libreta «sólo navegador/no servidor» incompatible con datos en código Python/session_state; F-02 comparación histórica aplica referencia 2025 a cualquier año; F-03 importación de libreta descarta identidad y asigna filas al ID abierto. También se registran selección naranja inexistente, alcance de filtros/encuadre, vocabulario de escenarios, plantilla insuficiente, cero/vacío, reducción informativa móvil y deduplicación por nombre/tamaño.

Desviación autorizada: después de completar mapa actual, root indicó leer `context/planeador_campaña.md`. Se añadió exclusivamente contraste de encaje visual/UX PROPOSED: dos modos frente a tres etapas, área única, default como decisión de producto, barra móvil/etiquetas coincidentes, no llamar típico al rendimiento registrado, retención de widgets al alternar modos y lenguaje de una sola campaña. No se fijan contratos futuros.

Verificación: lectura estática; sin servidores, navegador, ejecución de pruebas, generación PDF, cambios de fuentes/datos/configuración/dependencias ni commits. Archivos escritos por este agente: sólo este contrato y el informe. Hallazgos críticos y resumen comunicados a root mediante mensajes; informe listo para integración.
