# TASK-005 — Desacoplar la cuenta y resolver referencia municipal

Type: IMPLEMENTATION. Status: DONE. Owner: root. Fecha: 2026-10-19.
Depends On: TASK-004 DONE. Ejecución secuencial, sin subagentes.

## Objective
Implementar P1-1/P1-2: referencia municipal pura y calculadora común sin depender de un ID, con adaptador por parcela y estado persistente dentro de sesión. Conservar apariencia, resultados, modelo y fuentes.
## Allowed Scope
Nuevo backend/dominio/planeador.py; frontend/vistas/agricultor/calculadora.py; nuevo frontend/estado/planeador.py; integración mínima de estado en frontend/estado/sesion.py; lector económico en frontend/componentes/descargas/boton_ficha.py (REV-01); pruebas nuevas de dominio/estado/calculadora e índices/documentación de la fase.
## Out of Scope
Cebi completo, sus recursos/contenidos/pruebas; selector o vista rápida; escenarios visuales/barra/C2/C3; cambios a estimador/rangos/confianza/cuentas legacy, datos/T18/config/CSS/analista; fases 2–5; commits y publicación.
## Inputs / Contracts
docs/ai/planeador/fase-0/contratos-v1.md y base.json (inmutables salvo nota explícita de aclaración). estimacion_municipio(d,municipio,modelo) retorna los ocho campos del §2, valida modelo y etiquetas, sin respaldo global. evaluar_cuenta compone columnas/cuentas/rango/equilibrio existentes, retorna estado pendiente/invalida/calculada, errores, tabla/rango/umbral; no implementa aún tarjetas ni C2. calculadora(ctx,pid) conserva firma y semántica; calculadora_base recibe municipio/rendimiento/etiqueta/área/clave, con variante sin segundo widget de área. Diccionario planeador y claves legacy según §6.
## Acceptance Criteria
Identidad de referencias para nueve municipios y las 59, ambos modelos; 0/1/2/3/9/10 cosechas; ningún uso de PREDICCION para referencia; rechazo de etiquetas no finitas y modelo inválido. Igualdad numérica de cuentas actuales. Estado conserva precios y áreas por parcela al desmontar widgets, respeta limpieza None y no cambia el catálogo. Variante municipal sin ID y sin campo de área duplicado. Ningún archivo de Cebi modificado.
## Required Checks / Definition of Done
Pruebas nuevas de dominio/estado y AppTest de calculadora/lector PDF si el entorno lo permite, regresión backend de cuentas/rangos/confianza y verificador de base fase 0. No ejecutar pruebas del bot ni regenerar datos. Si AppTest no arranca, diagnosticar limitación y distinguirla de regresión funcional; obtener validación de interfaz con entorno autorizado si es posible. Revisar diff y actualizar entrega/evidencias sin adelantar fase 2.
## Findings / Deviations / Final Result
Completado P1-1/P1-2: referencia municipal y evaluación de cuenta puras, estado canónico/migración, adaptador de parcela + calculadora común sin ID, hidratación antes del panel y lector PDF consistente con área vacía. Cinco archivos de producto (dos nuevos, tres modificados) y tres pruebas nuevas; ningún cambio a bot/CSS/modelo/datos/configuración. Referencia y base fase 0 inmutables.

Pruebas: 7 dominio + 5 estado OK; AppTest calculadora ampliado OK (incluido PDF antes/después de montaje y área limpiada/restaurada); regresiones existentes calculadora/rangos/confianza, PDF y tema OK; base fase 0 OK; sintaxis, git diff --check y alcance exacto comprobados. AppTest ejecutado en proceso local autorizado fuera del aislamiento de socketpair; ninguna alteración a runtime para pasar pruebas. No inspección visual de navegador ni Docker. Evidencia en docs/ai/planeador/fase-1/README.md y logs fase1 en .agent/.

Revisión independiente TASK-006: approve, sin hallazgos materiales abiertos; F-1 resuelto por REV-01 y comprobado por root. Se añadió marca interna opcional de inicialización de área rápida para conservar None y compatibilidad con estado v1.

Sin commits/cambio de rama/publicación; fases 2–5 no iniciadas. Cebi completo excluido; su integración nueva sólo cuando concluya trabajo paralelo.

## REV-01 — Compatibilidad de área limpiada en PDF
La revisión independiente encontró que el lector PDF usaba `area or AREA_HA`, reconstruyendo una cuenta mientras el formulario quedaba pendiente al limpiar área. Ampliación mínima necesaria: lector económico PDF consume evaluar_cuenta y usa default de catálogo únicamente si la clave no existe, no si contiene None. Prueba AppTest de limpiar/restaurar área y ausencia de cuentas PDF. Cebi permanece excluido; no cambia el contrato de ficha, sólo se evita un resultado inconsistente.
