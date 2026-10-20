# TASK-009 — Consulta rápida sin parcela

Type: IMPLEMENTATION. Status: DONE. Owner: root. Fecha: 2026-10-19.
Depends On: TASK-007/008 DONE. Usuario autoriza fase 3; Cebi completo sigue aplazado.

## Objective / Inputs
Implementar P3-1/P3-2 del plan y contratos v1 de fase 0: selector dentro de Agricultor, catálogo inicial, consulta rápida municipal sin ID, superficie única y resumen con confianza. Evidencia base: vista agricultor, panel_parcela, calculadora_base, estado planeador, estimacion_municipio y confianza_parcela leídos. Snapshot previo exacto .agent/fase3/antes/; HEAD efbb2dd3c82b254550232f42e1ff7b1c51c351c0, fases previas sin commit.

## Allowed Scope
Nueva vistas/agricultor/consulta_rapida.py; vista.py como enrutador conservando recorrido de catálogo; estado/planeador.py y sesion.py para modo/municipio persistentes; helper puro de municipios con soporte en dominio/planeador.py; CSS sólo nuevo y acotado; pruebas nuevas de estado/consulta/transiciones y documentación. Rutas bajo app/ salvo memoria/docs.

## Out of Scope
No modificar Cebi, sus preguntas/activos/pruebas propias, modelos/datos/OOF/rangos/fórmulas ni catálogo de parcelas. No PDF municipal ni ID ficticio, mapa/satélite/clima de otra parcela, nuevos respaldos territoriales, fases 4/5, commits/despliegues o dependencias.

## Contracts / Expected Outputs
agri_modo canónico inicial Parcela del catálogo, alternativa Consulta rápida; widget temporal separado para sobrevivir desmontaje. Municipio rápido en planeador.municipio_rapido, sin reutilizar agri_muni. Lista exacta de municipios ENTRENAMIENTO con cosechas válidas, sin filtrar por las 59. Inicial rápido sin municipio/área; selección fuera de cobertura invalida resumen sin respaldo regional. Referencia y n de estimacion_municipio(ctx.d, municipio, ctx.modelo), confianza desde confianza_parcela(ctx.conf,...,municipio). Captura de área única antes del resumen; calc_base recibe area_editable=False. Referencia visible sin cuentas válidas; toneladas sólo con área válida y producto finito. Sin mapa, parcela ni ficha municipal. Precio/costo compartidos, áreas independientes y None persistente.

## Design / Verified Decisions
Reusar segmented_control de la cabecera con etiqueta visible y contenedor glass; tokens/Inter/radios existentes, entradas con etiquetas y resumen con procedencia 2025. Dos columnas de entrada que Streamlit adapta; resumen apilado por CSS a 700px. Guía UI/UX local consultada para navegación: estado activo visible, conservación de captura; no se añaden URL/servicios por una recomendación genérica ajena al alcance.

## Acceptance Criteria / Validation / Definition of Done
AppTest de producción y fixture: nueve municipios, incluyendo sin PREDICCION, cifras/confianza correctas; sin referencia/soporte, área vacía y overflow; un único campo área, sin mapa/ID/Cebi/ficha en modo rápido. Transiciones catálogo→rápida→catálogo, municipio/parcela, Agricultor→Analista→Agricultor y tema; valores y PDF por parcela coherentes, catálogo inmutable. Unitarias de modo/municipio y regresiones previas relevantes, base fase 0 intacta, revisión independiente y root antes del cierre. Inspección visual declarada pendiente si no puede ejecutarse; no certificar bot. Entrega docs/ai/planeador/fase-3/README.md, actualizar memoria y detenerse antes de fase 4.

## Findings / Deviations / Final Result
P3-1/P3-2 implementados: selector con catálogo inicial, vista rápida municipal sin ID y superficie única, referencia/confianza históricas y calculadora existente. La selección del catálogo también se conserva en estado canónico para sobrevivir al desmontaje de sus widgets; restauración con setdefault respeta callbacks. Precio/costo compartidos, áreas y municipios independientes, sin PDF municipal ni contexto de parcela ajena.

6 unitarias nuevas y 20 previas OK; AppTest de consulta para nueve municipios, confianza exacta/overflow/vacíos, recorridos reales con PDF/temas/modelo oficial y regresiones previas de cuentas/escenarios/tema/fichas OK. Base/hash fase 0 y catálogo intactos. Revisión independiente TASK-010 sin defectos materiales; root contrastó contratos/callers y completó cobertura explícita de confianza real y modelo oficial tras Analista. Evidencia docs/ai/planeador/fase-3/README.md y logs fase3-*.

Sin cambios a Cebi, datos/modelos, dependencias, ramas, commits ni despliegues. Inspección visual/teclado pendiente; no se declara aceptación de fase 4. Fases 4–5 sin iniciar.
