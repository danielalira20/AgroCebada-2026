# Problema y límites

El sistema y la propuesta deben comprenderse antes de diseñar su implementación. No se presupone que los documentos históricos reflejen el código vigente.

INV-001 (actualizado por instrucción humana, fase 4): ejecutar P4-1, integración/aceptación funcional y visual contra contratos y base; corregir defectos demostrados manteniendo estética/cifras. No fase 5 ni cambios a Cebi, datos, estimador o configuración científica.
INV-002: preservar los cambios locales previos. El usuario autorizó commits locales por fases al terminar la fase 4; no autorizó push, despliegues ni otras operaciones externas.
INV-003: afirmaciones verificadas con ruta:línea; distinguir CONFIRMED, INFERRED y UNKNOWN.
INV-004: la estética y flujos existentes son el punto de partida; no proponer un rediseño gratuito.
INV-005: no publicar datos ni secretos. Análisis del repositorio local, sin asumir un entorno de producción.

La salida serán archivos Markdown de auditoría bajo docs/ai/ y registros de esta operación bajo .agent/. La propuesta original permanece intacta.

Actualización de alcance: el usuario autorizó fase 0 después de la auditoría. Cebi y todo lo relacionado con él quedan excluidos por trabajo paralelo, incluida fase 5. Contrato vigente de la nueva operación: ../tasks/TASK-004-fase-0-planeador.md. No se requiere decidir aprobación T16 o reparar T18 para capturar su estado actual.

Nueva instrucción posterior: fase 1 autorizada, TASK-005 vigente. Se explicó al usuario que Cebi completo sigue aplazado; conservar claves compartidas/PDF no autoriza modificar el bot. No se implementa consulta rápida ni nuevas tarjetas todavía.

Instrucción más reciente: fase 2 autorizada, TASK-007 vigente; fase 1 cerrada. Se permiten los componentes visuales y C2/C3 del plan, no consulta rápida ni cambios a Cebi. Los estados anteriores describen entregas previas.

Fase 3 cerrada: TASK-009/TASK-010 DONE, consulta y estado verificados sin modificar Cebi. Siguiente fase 4 no iniciada. Evidencia docs/ai/planeador/fase-3/README.md.

Fase 4 cerrada: TASK-011/012 DONE; suite final, matriz visual y teclado verificados, zoom 200% confirmado por usuario. Evidencia docs/ai/planeador/fase-4/. Fase 5/Cebi siguen aplazados. No nuevas implementaciones autorizadas.
