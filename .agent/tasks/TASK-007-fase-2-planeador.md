# TASK-007 — Escenarios visibles, equilibrio y orientación

Type: IMPLEMENTATION. Status: DONE. Owner: root. Fecha: 2026-10-19.
Depends On: TASK-005/006 DONE. Alcance autorizado: fase 2; fases 3–5 y Cebi excluidos.

## Objective / Inputs
Implementar P2-1/P2-2/P2-3 contra contratos-v1 y base fase 0: tarjetas y barra accesibles desde la misma tabla económica, orientación estructurada C2 y título histórico de temporada C3. Mantener estética, precisión y estado de fase 1.

## Allowed Scope
Extensión backend/dominio/planeador.py; nuevo frontend/componentes/escenarios/; integración en vistas/agricultor/calculadora.py y título/texto de verdor_clima.py; CSS nuevo y estrictamente limitado a escenarios dentro de assets/css/tema.css; formato económico compartido en lector PDF si hace falta mantener centavos. Pruebas nuevas de backend/presentación e índices/documentación. Todos bajo app/ salvo memoria/documentación.

## Out of Scope
Cambiar modelo, datos, fórmulas/retornos legacy de calculadora/rangos, 59/T18, analista, selector de modo o consulta rápida; modificar Cebi, recursos, preguntas, respuestas o pruebas propias; dependencias/configuración, commits/publicación.

## Contracts / Expected Outputs
escenarios_cuenta(resultado, etiqueta_referencia): IDs bajo/referencia/alto, campos numéricos y cobertura del contrato; resultado sin cuenta → lista vacía. posiciones_barra: marcas numéricas y equilibrio dentro de 0–100, dominio que incluye todos, manejo de igualdad/colisiones sin falsear posición. plan_si_sale_mal: falta/cubre/equilibrio, faltante, escenario, abierto y tres pasos v1; referencia central sólo si no hay bajo, sin cuenta → None. UI sólo dibuja, adapta rótulos de tabla sin alterar sus datos y usa tokens existentes claro/oscuro. C3: «Verdor y clima de 2025», contexto retrospectivo sin año normal.

## Acceptance Criteria
Tarjetas coinciden con tabla cruda; pocas cosechas no inventan rango; dato registrado conserva etiqueta y puede salir del rango; negativos/positivos/equilibrio y centavos consistentes; barra no divide por cero ni colisiona etiquetas; estado de expander responde al faltante; limpiar captura retira resultados; estilos responsive y sin semáforo meteorológico. Sin cambio numérico de base fase 0 ni archivos del bot.

## Validation / Definition of Done
Pruebas unitarias nuevas de escenario/posición/C2 y AppTest de presentación (cuentas, vacío, pocos datos, igualdad, pérdidas/equilibrio, tema), regresiones fase 1/PDF/tema y base fase 0. Revisión independiente antes de cerrar, sin afirmar validación visual si no se ejecutó en navegador. Registrar resultados y pendientes, actualizar estado y detenerse en fase 2.

## Findings / Deviations / Final Result
P2-1/P2-2/P2-3 implementados. Backend adapta tabla a tarjetas/C2 y posiciones robustas; componente separado presenta escenarios, equilibrio y orientación; C3 sólo cambia texto histórico. CSS aislado esc-* con tokens y apilado móvil. Formato de importes compartido con lector PDF para no ocultar centavos. No modelos/datos/legacy/Cebi/fases 3–5.

8 pruebas nuevas dominio, 7 referencia, 5 estado y regresiones cuentas/rangos/confianza OK; AppTest nuevo de tarjetas, dos temas, C3 sin clima, centavos/transiciones/limpieza y regresiones fase 1/PDF/tema OK. Base fase 0 y su hash intactos. Revisión independiente TASK-008 sin defectos materiales; root leyó el informe y confirmó log PDF final OK. Segunda pasada de root contrastó P2-1/2/3, productores/callers y estados frontera. Sin hallazgos abiertos de código. Entrega docs/ai/planeador/fase-2/README.md.

La instrucción posterior «continúa» se atendió auditando progreso y ampliando AppTest para alternar estilos con cuenta calculada y verificar C3 sin clima; ambos OK. Aceptación visual en navegador pendiente, explícita y sin sustitución por AppTest. Sin servidor, commits ni despliegues. Detención en fase 2.
