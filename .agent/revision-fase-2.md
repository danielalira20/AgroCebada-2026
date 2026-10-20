# Revisión independiente de fase 2

Fecha: 2026-10-19. Revisor: revision_fase2. Contrato: TASK-008. Resultado del alcance delegado: **sin candidatos materiales confirmados**; la decisión final corresponde a root.

## Alcance y método

Revisión local A, sin PR ni issue. HEAD confirmado al principio y al cierre: `efbb2dd3c82b254550232f42e1ff7b1c51c351c0`. La base específica es el snapshot previo a fase 2 de `.agent/fase2/antes/`, autorizado por TASK-008, porque fase 1 permanece sin commit. No se interpreta el diff completo contra HEAD como si fuera fase 2. Se leyeron completos los deltas de los cinco archivos de ese snapshot, el componente nuevo `frontend/componentes/escenarios/`, las dos pruebas nuevas y los contratos v1/TASK-007. Todo código revisado está en worktree, local-only.

Lentes delegadas: contratos y precisión; flujo y estado; presentación y accesibilidad; pruebas. Lectura de callers pertinentes: calculadora legacy/rangos, helper HTML, tablas por tema y generación PDF. Sin migraciones, API externa, auth, integración, datos ni dependencias modificadas dentro del alcance. Se inspeccionaron los ajustes finales de escape `e(que)`, docstring PDF y caso negativo de $0.50 después de la primera lectura.

## Hallazgos

No se encontraron defectos funcionales o contractuales materiales en este alcance. Ningún bloqueo ni decisión de producto adicional propuesta.

## Verificado e intentos de refutación

- **Tarjetas frente a tabla/PDF.** Se intentó encontrar una segunda fórmula o datos redondeados usados como entrada. `app/agrocebada_app/backend/dominio/planeador.py:91` adapta los campos crudos de la misma tabla y conserva su nombre legacy en `columna`; `frontend/vistas/agricultor/calculadora.py:88` sólo renombra la tabla visible; `frontend/componentes/descargas/boton_ficha.py:35` toma el mismo escenario bajo. No se modifica el backend legacy. Los índices del adaptador corresponden al orden explícito de `columnas`, no al orden de presentación de tarjetas. Hipótesis REFUTED.
- **Pocos datos y cosecha individual fuera del rango.** Se buscó imposición de bajo < referencia < alto o creación de extremos sin soporte. `planeador.py:100` sólo crea extremos cuando la tabla tiene tres columnas; `planeador.py:113` incluye cada valor real y el umbral en el dominio. Los casos n=1/2, referencia 8 frente a extremos 2–5 y umbral 1e308 están cubiertos por las pruebas nuevas. Hipótesis REFUTED.
- **División por cero y coincidencias.** `planeador.py:125` normaliza para evitar overflow y trata amplitud cero con posición 50. `escenarios/vista.py:24` reemplaza marcas cercanas por texto sin desplazar sus posiciones. La igualdad de las cuatro marcas tiene prueba. Hipótesis REFUTED.
- **Orientación errónea si la referencia central cubre pero el bajo pierde.** `planeador.py:143` elige bajo, conserva faltante exacto y no omite el objeto en cubre/equilibrio; sin rango identifica la única referencia. El `next` anidado evalúa su default anticipadamente, pero todos los productores reales incluyen referencia; no se encontró un caller alcanzable sin ella. No se eleva una entrada inventada a defecto. Hipótesis REFUTED.
- **Estado y resultados obsoletos.** El retorno temprano en `calculadora.py:56` retira tarjetas/expander cuando falta captura; la clave del expander en `escenarios/vista.py:56` distingue estado y escenario. Se inspeccionó la prueba de transición falta → cubre → equilibrio → falta y limpieza. Hipótesis REFUTED dentro de los casos observados.
- **Faltante pequeño mostrado como cero.** `planeador.py:79` conserva centavos para importes menores de un peso y expresa cantidades inferiores a medio centavo sin llamarlas cero. Reutiliza tolerancia legacy; las tarjetas toman magnitud acompañada por palabra/estado. La prueba AppTest final inspeccionada verifica $0.50 y apertura. Hipótesis REFUTED.
- **Escape y semántica visual.** Strings de datos de tarjetas/orientación y las tres ramas de frase central pasan por `e`; la prueba nueva comprueba etiqueta con `<script>`. Tarjetas tienen lista, encabezados y definición de cifras; palabra/icono acompañan color. La barra es redundante y se oculta a lectores, conservando cifras en tarjetas/equilibrio. CSS añadido usa exclusivamente `.esc-*`, tokens existentes y apilado a 700 px; barra retirada a 600 px. Esto verifica intención del código, no píxeles ni comportamiento de lector de pantalla real.
- **C3 y límites.** `verdor_clima.py:54` cambia sólo título/subtítulo retrospectivos; cálculo y gráficos se mantienen. No se extiende a consulta rápida ni se modifica Cebi.

## Pruebas y evidencia

Ejecutada por este revisor: `.venv/Scripts/python.exe -B -X utf8 app/tests/backend/test_escenarios.py`, exit 0, 8 pruebas OK, 5.77 s totales del proceso (suite 0.066 s). No se ejecutó AppTest ni servicio por este revisor.

Inspeccionadas, ejecutadas por root: `.agent/fase2-backend.log` (escenarios, planeador, estado, calculadora, rangos, confianza y base inmutable: OK), `.agent/fase2-visual.log` (AppTest nuevo y caso $0.50: OK), `.agent/fase2-regresion-cuenta.log` y `.agent/fase2-regresion-tema.log` (OK). El log PDF estaba aún en curso al leerlo; root comunicó resultado final OK. Esta comunicación no se presenta como ejecución propia. Advertencias de ScriptRunContext son esperables en AppTest; la advertencia R² de varianza cero pertenece a la regresión existente.

## Pendientes y limitaciones

Sin inspección de navegador, capturas móvil/escritorio, interacción de teclado real ni lector de pantalla. No se certifican colisiones de píxeles, estética final o aceptación visual con AppTest. La separación porcentual de marcas y los breakpoints deben observarse en la revisión visual posterior. Cebi permanece excluido; conservar claves no demuestra su integración futura. No se accedió a sistemas externos ni se tocaron fuentes/pruebas. Root debe verificar su ejecución final de PDF y cerrar la decisión global.
