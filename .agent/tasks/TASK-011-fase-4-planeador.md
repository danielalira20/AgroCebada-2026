# TASK-011 — Integración y aceptación del planeador

Type: VALIDATION / CORRECTION. Status: DONE. Owner: root. Fecha: 2026-10-19.
Depends On: fases 0–3 implementadas; TASK-009/010 DONE. Usuario autoriza fase 4; Cebi sigue aplazado.

## Objective / Inputs / Contracts
Ejecutar P4-1 y matriz de aceptación del plan; contratos v1 y base inmutable fase 0. Revisar UI/teclado y contenido económico/histórico, corregir defectos demostrados de integración conservando estética y resultados. HEAD efbb2dd3c82b254550232f42e1ff7b1c51c351c0; fases previas locales sin commit. Evidencia previa en entregas fase-0 a fase-3.

## Allowed Scope
Validación integrada del código actual de app/, ajustes mínimos demostrados de accesibilidad/responsive/contratos en calculadora, escenarios, consulta, estado y CSS no relacionado con bot; pruebas de regresión y nuevas sólo para fallos reales no cubiertos; documentación/evidencia local para T19. Navegador vía cua_repl y servidor sólo loopback. Snapshots exactos antes de editar cada archivo bajo .agent/fase4/antes/.

## Out of Scope
Cebi/preguntas/diálogo/activos/pruebas propias, modelos/datos/OOF/rangos/fórmulas, aprobación T16/reparación de huella T18, exposición pública, despliegue/commits/dependencias o aceptar en nombre del equipo. No nueva funcionalidad de fase 5.

## Verified Environment / Decisions
La skill histórica built-in-browser describe herramientas Claude_Browser y afirma imposibilidad de localhost por host remoto. La documentación actual del proveedor cua_repl para IAB declara entorno local del usuario y documenta explícitamente validación localhost, viewport y recarga. Se usa esa capacidad actual comprobable; no se asume que el bloqueo descrito en fases previas siga vigente. Sólo navegadores IAB y MCP Apps disponibles; sin control nativo ni Chrome. Revisión web-design-guidelines consultando fuente oficial Vercel, adaptada a Streamlit y patrones existentes.

## Acceptance Criteria / Expected Outputs
Matriz documentada: nueve municipios, estados económicos/vacíos/escaso soporte, referencias registradas/fuera de rango, transiciones modo/vista/tema y modelo oficial; PDF por parcela y base fase 0 intactos. UI en 320/375/600/700/900/1400 px y temas, foco/teclado y zoom 200% cuando herramienta lo permita; no atribuir casos no ejecutados. Evidencia guardada localmente, correcciones justificadas, revisión independiente y pasada final de root; diferenciar implementación comprobada de aprobación humana de contenido y publicación.

## Definition of Done
Pruebas pertinentes aprobadas, incidencias materiales corregidas o pendientes explícitos con causa; snapshots/suite y capturas reproducibles, docs/ai/planeador/fase-4/README.md y memoria actualizadas. No afirmar cierre integral si quedan criterios de aceptación sin validar. Mantener siguiente fase bot pendiente.

## Findings / Deviations / Final Result
P4-1 completado en alcance local. Corregidas cifras 16px por cascada Streamlit (ahora44/32px), encabezados semánticos opcionales, contraste de summary abierto claro y singular n=1. Ampliación mínima de alcance: helper titulo con keyword nivel opcional y default HTML idéntico; tres llamadas nuevas, sin alterar Cebi. Nueva herramienta de regresión reproducible de 17 scripts, cwdAPP, logs/códigos/timeouts, versiones/huellas y verificación de estabilidad. Prueba existente de muestra actualizada al singular.

Suite final 17/17 OK desde app/ con configuración nativa correcta: evidencia/pruebas/20261020T005812834946Z. Las corridas previas17+4 y capturas de raíz son exploratorias, preservadas y diferenciadas. Matriz 24 capturas finales y medidas únicas (dos recorridos/dos temas/seis anchos), sin desbordes medidos; encabezados44/32px y contraste congruente. Nombre largo/n=1 y teclado Enter/Espacio/Tab/flechas verificados. El navegador integrado no aplicó zoom; el usuario confirmó explícitamente «Sí, funciona al 200%», atribuido a usuario en zoom.json, no al agente.

Revisión independiente TASK-012 y pasada final root sin defectos materiales. Hashes actuales, enlaces y base fase0 intactos. Docs/ai/planeador/fase-4/README.md y matriz-aceptacion.md entregados; registro disponible para T19 sin afirmar aceptación formal. No Cebi/datos/modelo/fórmulas/dependencias/commits/despliegues. Lector de pantalla real, otros navegadores/dispositivos, Docker, T16/T18 y bot fuera de alcance. Instancia privada de revisión en 127.0.0.1:8503; no publicación. Fase 5 sigue aplazada.
