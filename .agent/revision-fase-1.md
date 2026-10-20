Scope: repositorio `AgroCebada-2026` · entrada `A pre-PR` · base confirmada por encargo `efbb2dd3c82b254550232f42e1ff7b1c51c351c0` · merge-base y HEAD `efbb2dd3c82b254550232f42e1ff7b1c51c351c0` · PR/issue ninguno · fecha 2026-10-19 · cambios locales incluidos y etiquetados local-only.

Fuentes: TASK-005/TASK-006, contratos-v1 y README de fase 0, fuentes base y actuales, llamadores de sesión/calculadora/PDF y código instalado de number_input. Se excluyen fase 0 previa, .pr-suggestions, Claude outputs, Cebi, activos y servicios externos.

Verdict: **approve**

Razón: no quedan hallazgos materiales abiertos en el alcance local revisado. El hallazgo inicial F-1 fue corregido por root y se releyeron el lector PDF completo, su diff y la regresión ampliada; ahora ambos consumidores omiten la cuenta cuando el área se limpia.

Método: tamaño L, H=463 líneas de cambios revisadas (61 tracked y 402 en cinco archivos nuevos), ruido=0; revisión individual acotada por TASK-006, sin subagentes ni pruebas ejecutadas. Lentes flow-and-state, frontend y tests; dos hipótesis cerradas: una corregida durante revisión y una refutada. Se leyó el diff completo de los tres archivos modificados y completos los cinco archivos nuevos. Inventario: modificados estado/sesion.py, vistas/agricultor/calculadora.py y componentes/descargas/boton_ficha.py (ampliación REV-01 autorizada por root); nuevos backend/dominio/planeador.py, frontend/estado/planeador.py y las tres pruebas test_planeador.py, test_estado_planeador.py y test_calculadora_base.py (rutas bajo app/).

Cobertura: flow-and-state → verificado y F-1; frontend → verificado y F-1; tests → pruebas inspeccionadas. Flujos completos: arranque → hidratación → panel PDF → calculadora; migración legacy → diccionario → callbacks → desmontaje/remontaje; referencia municipal → rango → cuenta; variante sin ID y sin segundo control de superficie. Sin divergencia de base (HEAD=base). I-1/I-2/I-3/I-5/I-6/I-7/I-9/I-10/I-12 revisados en el alcance; I-4/I-8/I-11 no aplican (sin DB/proveedor/auditoría/superficie de inyección nueva). Sin cambios de autorización, dependencias, archivos de datos, modelo, infraestructura ni efectos externos.

## Verificado

- Referencias: `app/agrocebada_app/backend/dominio/planeador.py:20-40 @ worktree (local-only)` selecciona sólo ENTRENAMIENTO, valida todas sus etiquetas, valida candidato explícito y devuelve ocho campos. n=0 devuelve sin_soporte y no llama al estadístico; no existe respaldo grupo/global ni uso de PREDICCION en esa función.
- Cuenta: `app/agrocebada_app/backend/dominio/planeador.py:43-70 @ worktree (local-only)` reutiliza columnas/cuentas/rango/equilibrio sin redondeo, distingue vacío/cero precio/costo, rechaza bool/no finitos y verifica productos/saldo/umbral. Rango nulo y cosecha registrada fuera de rango conservan fórmulas/orden. El límite mínimo de superficie sigue en 0.01; no se agrega máximo.
- Estado: `app/agrocebada_app/frontend/estado/planeador.py:4-48 @ worktree (local-only)` migra claves legacy, excluye área rápida del mapa de parcelas, conserva None explícito y separa superficies por ID sin escribir al catálogo. La hidratación ocurre antes de widgets en el flujo actual; el componente municipal no vuelve a escribir su widget externo de área rápida.
- Adaptador: `app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:28-70 @ worktree (local-only)` conserva firma y elección real/predicción; area_editable=False omite el segundo control de superficie. Las fórmulas, rótulos y presentación existente se conservan en la cuenta válida.
- No se detectaron secretos ni nuevos destinatarios de datos en los ocho archivos de fase 1.
- Relectura final adicional: preparar_area acepta diccionario v1 sin marca privada mediante get(..., False), conserva superficie canónica existente y mantiene la marca al limpiar por callback. Inspeccionado `test: app/tests/frontend/test_estado_planeador.py::EstadoPlaneadorTests.test_estado_v1_sin_marca_interna_conserva_area_existente`. Sin hallazgo adicional; ahora son cinco pruebas de estado inspeccionadas.

## Bloqueos

Ninguno — F-1 corregido y reexaminado; no queda ruptura alcanzable identificada en los flujos revisados.

## Decisiones abiertas

Ninguna — el caso corregido contradice un contrato cerrado y se resolvió técnicamente.

## Descartados / corregidos

### ✅ F-1 — [P2] El PDF revivía la cuenta al limpiar la superficie (CORREGIDO)

Estado final: `app/agrocebada_app/frontend/componentes/descargas/boton_ficha.py:28-33 @ worktree (local-only)` usa get(clave, default), conserva None y pasa por evaluar_cuenta; retorna None si pendiente/inválida. El contrato de área ausente conserva el default catálogo. `app/tests/frontend/test_calculadora_base.py:66-78 @ worktree (local-only)` verifica None antes/después de calculadora, ida/vuelta y restauración. Se leyó íntegramente la corrección y la prueba ampliada. Root informó ejecución aprobada de AppTest en runtime autorizado; este revisor no la ejecutó ni usa ese mensaje como resultado propio. Los párrafos siguientes preservan la evidencia histórica del hallazgo inicial.

Location: `app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:60-63 @ worktree (local-only)`; consumidor `app/agrocebada_app/frontend/componentes/descargas/boton_ficha.py:22-34 @ efbb2dd (base)`.

Certainty: Inference.

Cambio: el área pasa de value=float(r.AREA_HA) en `app/agrocebada_app/frontend/vistas/agricultor/calculadora.py:44 @ efbb2dd (base)` a value=None y callback persistente. None es ahora un valor intencionado, y `evaluar_cuenta` lo considera pendiente (líneas 47-59).

Activación reproducible: seleccionar parcela, capturar precio/costo positivos, modificar su área y después vaciar Área (ha). El callback conserva None. En el siguiente rerun, iniciar_sesion restaura None antes de panel_parcela; filas_calculadora ejecuta `get(clave) or r.AREA_HA` y devuelve producción/saldo con la superficie del catálogo. La calculadora inferior devuelve pendiente y oculta su cuenta.

Impacto: usuarios que limpian el área con precio/costo presentes reciben un PDF con un supuesto de superficie que acaban de borrar; rompe el contrato de invalidar la presentación anterior cuando deja de existir cuenta válida (`contract: docs/ai/planeador/fase-0/contratos-v1.md#6`).

Evidencia de orden: `app/app.py:29 @ efbb2dd (base)` inicia estado; `app/agrocebada_app/frontend/vistas/agricultor/vista.py:28-42 @ efbb2dd (base)` llama panel antes de calculadora; `app/agrocebada_app/frontend/vistas/agricultor/panel_parcela.py:93 @ efbb2dd (base)` llama boton_ficha; boton_ficha llama filas_calculadora en líneas 42-43.

Intento de refutación: se reabrieron base, callback, hidratación y lector PDF. La hidratación no corrige el caso: restaura exactamente None. No hay validación de área ni llamada a evaluar_cuenta en el lector. El guard de precio/costo no cubre el área vacía. El test de integración limpia precio, cuyo guard sí funciona, y consulta el PDF después de calculadora. Código instalado `.venv/Lib/site-packages/streamlit/elements/widgets/number_input.py:911-913` confirma clearable=(value is None). No se atribuye reproducción ejecutada.

Recomendación: distinguir área ausente (primera entrada: catálogo) de área explícitamente None (sin cuenta), y validar con la misma evaluación antes de exportar. Añadir regresión con precio/costo presentes y área limpiada, tanto antes del montaje de calculadora como después de desmontar/remontar. Requiere ampliar mínimamente el alcance a boton_ficha.py; root confirmó que lo hará.

### ✅ F-2 — La hidratación podría perder datos al desmontar widgets

Hipótesis original: la limpieza automática de Streamlit podría borrar las capturas y volver a valores del catálogo.

Evidencia refutatoria: el diccionario de negocio conserva copias independientes, guardar_entrada conserva None y preparar_area usa setdefault por parcela. Hidratar restaura lectores antes del panel PDF en iniciar_sesion. Casos inspeccionados en `test: app/tests/frontend/test_estado_planeador.py::EstadoPlaneadorTests.test_restaurar_tras_desmontar_widgets` y `test_areas_separadas_y_limpiar_none`. La incoherencia específica de la exportación está separada en F-1.

## Pruebas

- Ejecutadas: ninguna — TASK-006 asigna ejecución y AppTest exclusivamente a root para evitar interferencia en estado/recursos. Sin instalaciones ni servicios.
- Inspeccionadas: las siete pruebas de dominio, cinco de estado y flujo de integración completo en test_calculadora_base.py. Comprueban 0/1/2/3/9/10, ambos modelos, nueve municipios y 59 predicciones, cuentas manuales/legacy, no finitos/overflow, None, áreas por parcela, rango igual, remontaje y control de superficie único. Los números esperados no son validación visual.
- Regresión ampliada inspeccionada: área limpiada → lector PDF sin cuenta antes/después de montaje, desmontaje/remontaje y restauración. No se añadió en este archivo un caso de números enormes para PDF; su rechazo se traza a evaluar_cuenta, ya cubierto en la prueba de dominio. La revisión de soporte nulo comprueba el retorno puro; no hay pantalla municipal de producción en fase 1.

## Pendientes

- F-1 cerrado por lectura de la corrección y regresión; sin pendientes materiales del revisor.
- No pude verificar resultados de ejecución, visuales ni runtime completo; root realiza pruebas y segunda revisión. No se atribuye compatibilidad de Cebi, aceptación visual o cierre metodológico T16/T18.
- La herramienta collect-diff.sh no se ejecutó: inventario limitado reconstruido mediante git diff/status/rev-parse/merge-base y lectura de cinco nuevos archivos conforme al contrato explícito. No se modificaron fuentes/índice/ramas.

## Decisión

**approve**

Sin condiciones de código en este alcance. Root conserva la responsabilidad de sus pruebas, segunda revisión e integración; esta aprobación no acredita inspección visual ni publicación.
