# Revisión independiente · fase 3

Fecha: 2026-10-19. Alcance: TASK-010, P3-1/P3-2 de TASK-009. Revisión local-only, sin commit. HEAD confirmado `efbb2dd3c82b254550232f42e1ff7b1c51c351c0`. Base efectiva de fase 3: copias exactas en `.agent/fase3/antes/`; las fases anteriores ya estaban sin commit y se excluyen de atribución. PR/issues: ninguno. Sin acceso externo, servicios, AppTest ni cambios de fuentes/pruebas. Root decide aceptación e integra sus resultados.

## Resultado

No encontré candidatos de defecto material en el alcance revisado. No hay cambios recomendados obligatorios derivados de esta lectura. Esto no certifica la apariencia en navegador, la interacción real con el mapa, la compatibilidad nueva con Cebi ni la ejecución de pruebas de integración por este revisor.

## Cobertura y método

Leídos completos el nuevo `consulta_rapida.py`, los cuatro deltas contra snapshots (`backend/dominio/planeador.py`, `frontend/estado/planeador.py`, `vistas/agricultor/vista.py`, `assets/css/tema.css`) y las cuatro pruebas nuevas indicadas por el contrato. Se aplicaron lentes de arquitectura/contratos, frontend/estado y pruebas; revisión secuencial de sus interacciones. Los callers reales abiertos fueron app.py, cabecera, contexto, sesión, calculadora, panel_parcela, selección, confianza y lector PDF. Se contrastó con contratos-v1 secciones 1–4 y 6–8. No hay migraciones, APIs externas, permisos, nuevas dependencias ni efectos externos dentro del delta.

- Cobertura municipal: `app/agrocebada_app/backend/dominio/planeador.py:20-29 @ worktree (local-only)` filtra ENTRENAMIENTO, exige cosechas finitas positivas y no depende de pred. El selector consume esa lista exacta en `frontend/vistas/agricultor/consulta_rapida.py:20-34`. La referencia existente valida modelo y no aplica respaldo regional en `backend/dominio/planeador.py:32-45`. Cabecera conserva MODELO_OFICIAL en Agricultor; contexto calcula confianza con ese mismo modelo.
- Separación de recorridos: `app/agrocebada_app/frontend/vistas/agricultor/vista.py:24-35 @ worktree (local-only)` retorna después de consulta rápida. No llega al panel/mapa, ficha, verdor ni contexto de una parcela. La nueva consulta no crea IDs ni escribe en d/pred. El recorrido de catálogo mantiene su cuerpo anterior.
- Estado: `app/agrocebada_app/frontend/estado/planeador.py:19-50 @ worktree (local-only)` separa modo/municipio canónicos de widgets desmontables; invalida municipio fuera de cobertura y restaura catálogo con setdefault para respetar cambios de callbacks. Las áreas rápida y por ID siguen separadas en líneas 62–86, con None retenido. La hidratación anterior conserva claves legacy para PDF.
- Resumen y cuentas: `app/agrocebada_app/frontend/vistas/agricultor/consulta_rapida.py:38-67 @ worktree (local-only)` permite referencia sin cuentas, muestra temporada y origen local, llama confianza_parcela con fuente municipal y oculta producción no finita. Pasa area_editable=False al componente real: una sola superficie. La cuenta sigue pasando por evaluar_cuenta, que bloquea productos/saldos no finitos. La referencia no se sustituye silenciosamente al faltar soporte.
- Frontend: etiquetas visibles en selector/entradas, confianza con palabra e icono, escape HTML de municipio y motivo, estilos nuevos acotados con tokens existentes. El resumen se apila a 700 px. No se cambian activos ni selectores de Cebi. La inspección de código no prueba dimensiones, foco ni contraste renderizado.

## Hipótesis refutadas

1. REFUTED: el nuevo catálogo podría excluir municipios sin parcelas reservadas. La implementación sólo lee ENTRENAMIENTO y la unitaria incluye A con cosecha sin PREDICCION y C con sólo PREDICCION; resultado A/B, no C.
2. REFUTED: cambiar de recorrido podría enviar superficie municipal al PDF de una parcela. Consulta rápida retorna antes de panel_parcela/ficha; calculadora_base no monta otra área; filas_calculadora lee exclusivamente calc_area_{pid}. La prueba de recorrido inspeccionada verifica áreas 10/8 ha por ID frente a 7 ha rápida y limpieza de None.
3. REFUTED: desmontar selector podría perder municipio o restaurar un valor borrado. Municipio de consulta vive en planeador.municipio_rapido y callbacks escriben None; la selección del catálogo tiene copia distinta, restituida sólo si falta su clave. Unitarias ejecutadas cubren limpieza por cobertura y no sobrescritura de selección nueva.

## Pruebas

Ejecutadas por este revisor:

- `.venv/Scripts/python.exe -B -X utf8 app/tests/backend/test_municipios_planeador.py`: salida 0, 2 pruebas, 0.045 s del runner.
- `.venv/Scripts/python.exe -B -X utf8 app/tests/frontend/test_estado_consulta.py`: salida 0, 4 pruebas, 0.001 s del runner.

Inspeccionadas, no ejecutadas aquí: test_consulta_rapida.py (nueve municipios, estado vacío, resumen, área única, overflow, sin mapa/ficha); test_recorridos_agricultor.py (app real, cambio de modo/Analista/tema, áreas independientes, limpieza y lector PDF). Segunda lectura posterior a la ampliación de root: la consulta ahora construye ctx.conf con validación real A/fuente municipal y compara motivo escapado y nivel exactos de confianza_parcela para los nueve municipios. El recorrido cambia explícitamente al modelo media en Analista y comprueba la referencia del MODELO_OFICIAL al regresar a Agricultor. La observación anterior de falta de aserción explícita sobre confianza queda cerrada. Se abrieron los registros `.agent/fase3-consulta.log` y `.agent/fase3-recorridos.log`: ambos terminan en OK. Son ejecuciones de root, no de este revisor. Root comunica también las regresiones previas exitosas; este revisor no las volvió a ejecutar.

## Límites

No inspeccioné píxeles en navegador ni ejecuté Cebi o sus pruebas propias. No hay solicitud de datos externos pendiente. La aceptación integral y la eventual revisión visual quedan a cargo de root; no se emite una aprobación de despliegue desde esta revisión parcial.
