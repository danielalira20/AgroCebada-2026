# Hallazgos y cuestiones pendientes

Verificado: 2026-10-19, `efbb2dd`. Índice de conocimiento relevante, sin repetir los informes que contienen las pruebas y consecuencias completas. No se implementaron reparaciones.

| ID | Prioridad | Estado, hallazgo y fuente |
|---|---|---|
| F-001 | Alta | CONFIRMED: modelo mediana oficial en código y T18 generado frente a decisión T16 documentada como propuesta condicionada. `app/agrocebada_app/config.py:17`; `docs/t16_procedimiento_final.md:3`; `registro/decisiones.csv:68`. Véase [procedencia](auditoria-investigacion.md). |
| F-002 | Alta | CONFIRMED: archivo T18 LF no coincide en bytes con traza CRLF; conversión sólo en memoria reproduce el hash declarado. `registro/t18/trazabilidad.json:56`; `.gitattributes:4`. La causa por normalización de Git es INFERRED; valores numéricos no muestran alteración. |
| F-003 | Alta para especificación | CONFIRMED: escenarios del plan se forman con distribución de parcelas de 2025. No es evidencia de años bajos/altos. `context/planeador_campaña.md:169`; `app/agrocebada_app/backend/dominio/rangos.py:25`. Revisar lenguaje antes de codificar. |
| F-004 | Alta para especificación | CONFIRMED: C4 propone global sin grupo, diferente del respaldo del estimador vigente. `context/planeador_campaña.md:244`; `backend/modelo/estimador.py:17` bajo `app/agrocebada_app/`. No afirmar equivalencia universal con T18. |
| F-005 | Alta si se utiliza historial | CONFIRMED: libreta aplica referencia vigente a años sin comprobar campaña y omite identidad al importar. `frontend/vistas/agricultor/bitacora.py:111`; `backend/dominio/bitacora.py:124` bajo `app/agrocebada_app/`. [Detalle backend](auditoria-backend.md). |
| F-006 | Media | CONFIRMED: procesamiento de libreta/datos propios en servidor Streamlit contradice «nada sale del navegador». `frontend/vistas/agricultor/bitacora.py:26`, `:159` bajo `app/agrocebada_app/`. No confundir falta de persistencia explícita con ejecución exclusivamente local del navegador. |
| F-007 | Media | CONFIRMED: cachés de lectura/descarga no identifican campaña/conjunto en claves. `frontend/estado/cache.py:7`; `componentes/descargas/boton_cifras.py:11` bajo frontend. Riesgo INFERRED al cambiar fuentes o introducir campañas, no evidencia de datos mezclados en la copia fija actual. |
| F-008 | Media | CONFIRMED: C2 siempre disponible frente a contrato que retorna None positivo; área rápida pedida dos veces; precisión contra T18 no especificada. `context/planeador_campaña.md:185`, `:259`, `:291`, `:383`. Resoluciones propuestas en [plan §3–5](planeador-campana-auditoria-y-plan.md). |
| F-009 | Media | CONFIRMED: paquete local activo sin normal climática ni calidad. Las lecturas opcionales no caen a originales. Resultado de lectura registrado en [entornos](environments.md); política en `backend/datos/paquete.py:55`, `:103` bajo `app/agrocebada_app/`. |
| F-010 | Media | CONFIRMED: selección naranja declarada no coincide con borde blanco del código; encuadre buscado usa vecinas en lugar de filtros generales. `frontend/componentes/mapa/mapa.py:36`; `frontend/vistas/analista/vista.py:60` bajo `app/agrocebada_app/`. Efecto perceptual exacto UNKNOWN sin navegador. |
| F-011 | Limitación de verificación | CONFIRMED: cinco scripts backend OK; AppTest mínimo se bloquea en socketpair/event loop del entorno antes de comprobar app. Evidencia, entorno y exclusiones en [entornos](environments.md). No atribuir el bloqueo a una regresión de AgroCebada. |

## Cuestiones abiertas

- Q-001 UNKNOWN: dónde consta la aprobación final de Dani/Migue a la excepción T16. Buscar evidencia del PR/decisión al cerrar metodología; no se inspeccionó GitHub.
- Q-002 UNKNOWN: si hay despliegue activo, qué configuración/datos utiliza y si la publicación está autorizada. El análisis no accedió a una instalación externa.
- Q-003 PROPOSED: definir default del nuevo modo, política de municipio sin soporte, costo cero y revisión humana del contenido de orientación. Opciones concretas en el plan, no preguntas bloqueantes para esta auditoría.
- Q-004 UNKNOWN: comportamiento visual y accesibilidad real en navegador/móvil; AppTest disponible en un entorno que permita su inicialización. Debe ser aceptación de implementación, no una afirmación actual.
- Q-005 UNKNOWN: desempeño para otra campaña o parcela nueva. Requiere etiquetas, disponibilidad temporal y evaluación específicas; coherencia con T18 no lo demuestra.
