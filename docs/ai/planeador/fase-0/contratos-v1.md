# Contratos del planeador · versión 1

Estado: especificación operativa cerrada en fase 0; **tipos y funciones siguientes aún no implementados**. Fuente de autorización y límites: [README](README.md). Se revisarán de forma explícita si una implementación demuestra una incompatibilidad; no cambiar su significado silenciosamente.

## 1. Entradas y procedencia

- `d` conserva contrato de datos actual: índice ID_POLIGONO, CONJUNTO, real, municipio, grupo_registro y AREA_HA. Sólo ENTRENAMIENTO y `real` finito intervienen en referencias/rangos; nunca estimaciones de las 59 ni notas de libreta. Si hay una etiqueta de entrenamiento no finita, devolver error de datos; no descartarla silenciosamente para cambiar una cifra. Las etiquetas PREDICCION ausentes se mantienen ausentes.
- `modelo` es argumento explícito y debe pertenecer a `MODELOS_CANDIDATOS`. El modo Agricultor recibe `MODELO_OFICIAL` del llamador; evitar capturarlo como valor por defecto de otra sesión. No modificar la función actual `estadistico` ni el estimador oficial para implementar estas validaciones.
- `municipio` es una opción exacta del catálogo, con cosechas válidas; no hay texto libre ni geocodificación. No extender a todo México ni inferir grupo agronómico a partir del nombre.
- `area_ha`, `precio_t`, `costo_ha`: números finitos sin booleanos; área ≥0.01 y precio/costo >0 para tener una cuenta. Vacío/cero deja estado `pendiente`; negativos, área fuera de límite o no finitos dejan `invalida`, con motivo junto al campo. El resumen histórico puede mostrarse sin precio/costo y, sin área válida, sin toneladas.
- En esta versión no se fija un máximo nuevo de área; se comprueba que productos y saldos sean finitos antes de dibujarlos. No introducir un límite no aprobado ni modificar el contrato de carga de datasets.

## 2. Referencia municipal

Resultado futuro, campos obligatorios:

| Campo | Tipo / regla |
|---|---|
| `estado` | `disponible` o `sin_soporte` |
| `municipio` | string, opción consultada |
| `campania_base` | int 2025, derivado de la temporada configurada |
| `modelo` | clave de candidato validada |
| `rendimiento_t_ha` | float finito positivo si disponible; null sin soporte |
| `fuente` | `municipio` si disponible; null sin soporte |
| `n_cosecha_municipio` | int ≥0; conteo municipal de entrenamiento |
| `n_cosecha_fuente` | mismo conteo en v1, no tamaño global |

Municipio sin cosechas o catálogo sin entrenamiento: `sin_soporte`, cifras null y conteos 0. Municipio desconocido también sin soporte, con mensaje de cobertura; no utilizar la mediana global como si fuera local. La identidad con `predecir` aplica a casos con fuente municipal. El respaldo grupo/global del flujo de parcela permanece intacto y fuera de esta función nueva.

La confianza se obtiene de `confianza_parcela(ctx.conf, municipio, fuente)` para referencias disponibles. No recalcular sus umbrales, equiparar n con certeza o interpretar MAE como probabilidad individual. Sin soporte: mensaje de ausencia de referencia local y sin cuentas/escenarios; no presentar confianza histórica de otra zona.

## 3. Referencia de una cuenta

Campos: `tipo` (`municipal`, `estimacion_parcela`, `cosecha_registrada`), `municipio`, `campania_base`, `rendimiento_t_ha`, `etiqueta`, `area_ha`. Para parcela se conserva ID real; consulta rápida no fabrica IDs ni crea filas en `d` o `ctx.pred`.

La firma pública `calculadora(ctx, pid)` sigue existiendo como adaptador. En parcela reservada usa predicción; en ENTRENAMIENTO usa cosecha registrada como hoy. El componente común no decide otra referencia a partir del texto de etiqueta.

## 4. Rangos y escenarios

Reutilizar `rango_municipio`/`rangos.py`, sin cambiar cifras ni sus umbrales:

- ≥10: bajo=P10, alto=P90.
- 3–9: menor y mayor cosecha municipal observada.
- <3: sólo referencia, sin extremos ni barra de rango.

IDs estables de escenarios nuevos: `bajo`, `referencia`, `alto`. Cada uno contiene `id`, `etiqueta`, `rendimiento_t_ha`, `produccion_t`, `ingreso`, `costo`, `saldo`, `cobertura`. Reutilizar `columnas` y `cuentas` y adaptar su presentación sin cambiar sus retornos legacy ni rótulos compartidos en backend en esta extracción. El orden de la tabla existente se conserva; nuevas tarjetas pueden ordenarse bajo/referencia/alto por sus IDs, no índices accidentales.

Producción=rendimiento×área; ingreso=producción×precio; costo=costo_ha×área; saldo=ingreso−costo. Para decidir cobertura reutilizar tolerancia actual de cuentas: saldo <−1e−9 es `falta`; abs(saldo)≤1e−9 es `equilibrio`; saldo >1e−9 es `cubre`. Los tres estados son compatibles con la respuesta legacy Sí/No. Equilibrio t/ha=costo_ha/precio_t.

Las tres marcas pueden coincidir, como en Emiliano Zapata. Una cosecha individual también puede estar fuera de los extremos municipales. No imponer bajo<referencia<alto a una parcela registrada ni una amplitud positiva a un municipio.

## 5. Contenido ante faltante (C2)

Resultado obligatorio cuando hay cuenta válida: `estado` (falta/cubre/equilibrio), `escenario_id`, `saldo`, `faltante`, `abierto`, `titulo`, `apertura`, `pasos` (lista de tres strings). `faltante=max(0,−saldo)` cuando falta; 0 en los otros estados. `abierto=true` sólo cuando falta. Sin cuenta, no se construye este resultado ni se muestra un importe residual.

Referencia de estrés: escenario bajo si existe; en su ausencia, referencia central con aclaración «Con la única referencia disponible». No llamar bajo al escenario central. Con rango disponible pero saldo positivo/equilibrio, el bloque existe plegado; no retorna None ni desaparece.

Texto base v1: título «Si este escenario no cubre tus costos». Apertura condicional con monto y supuestos; para cuenta que cubre, informar cobertura según los números capturados. Pasos definidos para esta versión:

1. «Anota el faltante calculado y los números de precio, costo y superficie que usaste.»
2. «Revisa tus gastos y conserva tus registros de la campaña.»
3. «Comenta estas cuentas con tu asesor técnico y revisa qué opciones existen para tu caso.»

Nota: «Orientación general basada en tus supuestos; no garantiza apoyos ni resultados de cosecha». No incluir requisitos, programas, aseguramiento, recomendaciones de crédito o promesas de elegibilidad. Revisión editorial al integrar el componente; no depende de cambios del bot.

## 6. Estado de sesión y compatibilidad

Plan para implementar en fases 1/3, no claves agregadas hoy:

| Dato | Fuente de verdad y compatibilidad |
|---|---|
| `agri_modo` | Selector con inicial «Parcela del catálogo»; «Consulta rápida» como alternativa. |
| `planeador` | Diccionario de estado de negocio, independiente del ciclo de montaje de widgets: `precio_t`, `costo_ha`, `area_rapida_ha`, `municipio_rapido`, `areas_parcela_ha` (dict por ID). Inicial numérico null, salvo área de parcela que se inicializa del catálogo al entrar. |
| `calc_precio` / `calc_costo` | Claves legacy de widgets que se conservan. Se hidratan antes de montarlos y se sincronizan mediante callbacks al diccionario; nunca reasignar una clave después de instanciar su widget en la misma ejecución. |
| `calc_area_{pid}` | Clave legacy por parcela; refleja únicamente `areas_parcela_ha[pid]`, sin modificar AREA_HA de `d`. |
| `calc_area_rapida` | Único widget de hectáreas de consulta rápida. Se monta una vez, antes del resumen. Calculadora común recibe área y no crea otro widget para ese modo. |
| `agri_muni`, `agri_parcela`, `encuadre_agri` | Conservan significado actual del catálogo/mapa; no reutilizarlos como municipio de consulta rápida. |

Al desmontar widgets, su limpieza no debe borrar los valores del diccionario. Al cambiar modo, tema o vista se retiene captura; limpiar un campo propaga null, sin recuperar un valor viejo por `x or anterior`. El PDF del catálogo sigue leyendo precio/costo y área de la parcela correspondiente; no recibe una cuenta rápida ni un pid ficticio. Si deja de existir soporte/cuenta válida, invalidar la presentación anterior y no mantener su saldo en pantalla.

Lectores actuales inventariados: productor de valores en `frontend/vistas/agricultor/calculadora.py:39–44`; lectura PDF en `frontend/componentes/descargas/boton_ficha.py:22–29`. Hay además un consumidor en el bot; sus archivos no se modifican, congelan ni prueban en esta fase. Su revisión de integración queda aplazada por instrucción humana; conservar claves es un requisito de compatibilidad, no una declaración de que la futura integración ya pasó.

## 7. Representación y precisión

- 2025 y el origen muestral próximos a cifras. «Rendimiento bajo/alto» describe referencias de parcelas, no campañas futuras.
- Rendimientos y área visibles con dos decimales, producción con precisión del componente existente; importes con pesos/separador de miles. Valores crudos permanecen en cuentas/estado.
- Igualdad entre tarjetas y tabla se verifica sobre valores crudos; render usa una política consistente. Con saldo no nulo menor de $0.50, mostrar centavos para no afirmar «faltan $0»; en equilibrio por tolerancia mostrar «justo cubre».
- Comparación de referencia municipal con estimador: tolerancia absoluta 1e−12 t/ha, rtol=0. T18: comparar a dos decimales o atol=0.005 t/ha, rtol=0, siempre con identidad de IDs. La huella de archivo es un control distinto.
- Verificador de base general: tolerancias absolutas y relativas 1e−12 para resultados crudos, categorías/estructuras exactas y bytes de fuentes exactos. No usar esa tolerancia general como contrato del CSV final.
- Barra incluye equilibrio y valores, maneja extremos iguales y colisiones; en móvil las cifras textuales sustituyen la barra si no hay espacio. Posición siempre responde al valor real; no desplazar para aparentar separación.
- Mantener Inter, tokens claro/oscuro, `glass_*`, bordes/radios y detalle plegable. Tarjetas apiladas en móvil, texto e iconos además de color; no modificar CSS/activos del bot ni escalas cartográficas.

## 8. Criterios de salida y siguiente fase

Fase 0 termina con base verificable y decisiones anteriores documentadas. T16 y anomalía histórica de T18 permanecen pendientes identificados; no bloquean una extracción de calculadora que mantenga resultados y que no publique una nueva afirmación metodológica.

Fase 1 debe demostrar equivalencia de las cuentas actuales, referencia de los nueve municipios, casos sin soporte, área única y conservación de claves/estado sin tocar bot. Las fases de UI deben probar n=0/1/2/3/9/10, rango nulo, cosecha registrada fuera de rango, captura vacía/cero/no finita, faltante/cubre/equilibrio y transiciones ida/vuelta. Inspección de navegador y aprobación visual siguen pendientes para la aceptación de implementación.

Fase 5 y cualquier integración nueva con Cebi están **aplazadas**, sin dependencia obligatoria para fases 1–4. Si el trabajo paralelo cambia claves compartidas, debe revisarse el contrato al integrar, sin atribuir por anticipado compatibilidad al bot.
