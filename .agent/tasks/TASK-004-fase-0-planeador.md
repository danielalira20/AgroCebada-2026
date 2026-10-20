# TASK-004 — Cerrar fase 0 del planeador

Type: VALIDATION / planificación contractual. Status: DONE. Owner: root.
Fecha: 2026-10-19. Depends On: TASK-001/002/003 DONE.

## Objective
Cerrar P0-1/P0-2 con decisiones operativas, contratos futuros, matriz de aceptación y una base reproducible de resultados actuales, sin adelantar funcionalidades de fase 1.

## Allowed Scope
Documentación docs/ai/planeador/fase-0/, índices/estado de auditoría, este contrato y herramienta de comprobación app/herramientas/verificar_base_planeador.py. Lectura de fuentes y pruebas existentes.

## Out of Scope
Cebi completo (código, pruebas, contenidos y recursos); UI, modelo, datos, configuración y pruebas de producto; fases 1–5; regenerar T18; cambios de rama, commits o publicación. No delegación necesaria: ejecución secuencial.

## Inputs
Solicitud humana de implementar fase 0 y aplazar fase 5/todo Cebi; auditoría previa; rama existente feature/agriultor-prediccion (el nombre humano omitió la n final). Código vigente efbb2dd.

## Expected Outputs / Contracts
README de cierre y contratos versionados, base JSON con fuentes/59 cifras/ambos modelos/métricas/rangos/confianza/cuentas ilustrativas; verificador de sólo lectura sin opción de sobrescribir esa base. Contratos futuros identificados como aún no implementados. Aprobación T16 y anomalía de huella T18 quedan pendientes externos explícitos.

## Acceptance Criteria
- Decisiones de entrada/costo cero/soporte/estado/C2/precisión cerradas con trazabilidad de autorización; sin atribuir aprobación metodológica.
- Base captura 197/138/59/9 y ambos modelos, métricas, inputs y hashes de datos activos; identifica límites opcionales.
- Verificación detecta cambio de una cifra, falta de fuente y cambio de modelo oficial; permite cambios paralelos en Cebi porque no depende de sus archivos.
- No modificación de archivos excluidos ni funcionalidad de usuario.

## Definition of Done
Releer y comprobar contratos contra fuentes; ejecutar verificador y controles negativos sin alterar base; validar enlaces/JSON y alcance de git; actualizar memoria y resultados. No confundir fase 0 cerrada con fase 1 implementada o con aceptación visual.

## Findings / Deviations / Final Result
Completado: docs/ai/planeador/fase-0/{README.md,contratos-v1.md,base.json,verificacion.md} y herramienta de lectura app/herramientas/verificar_base_planeador.py. Índices y memoria actualizados. Base de ambos modelos, 59 filas cada uno, cuatro poblaciones, rangos/confianza/cuentas de nueve municipios y once rutas (dos opcionales ausentes).

Pruebas: verificador CLI código 0; detecta cuatro mutaciones en memoria (cifra/modelo/presencia de fuente/población); controles de tolerancia/tipos/campos/no finitos; CLI base ausente código 1. Base intacta tras pruebas. Sin ejecución de Streamlit, bot ni pipelines científicos. Entorno y detalles de salida en verificacion.md.

Se conservó rama feature/agriultor-prediccion existente; nombre solicitado truncado interpretado conforme a contexto y comunicado. No se atribuyó aprobación T16 ni se arregló T18. Cebi completo fuera de alcance. Sin modificaciones a producto/datos/config/tests existentes, commits o publicación. Siguiente fase no iniciada.
