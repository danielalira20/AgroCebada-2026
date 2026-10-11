# T07 · Correcciones 1–3 del PR #14

10 de octubre de 2026. Rama `t07-tabla-comun`; base `dev` identificada
`8d6f543d4b907a92cc00658905f238479e4e2e76`. Cambios locales preparados para
revisión de Jass; `cierre_t07=false`. No se entrenaron modelos ni se modificó T03.

## Problema que resuelve

La lectura implícita de la bitácora podía rechazar D020 en configuraciones
Windows que usan cp1252. El contrato clasificaba el grupo de registro sólo como
auditoría, aunque T03/D019 requieren conservarlo para respaldos y reportes.
La calidad de ventanas no trasladaba los diagnósticos de celdas y centroide
que ya existían en T02/T04.

## Solución que implementa

### 1. Lectura independiente de la configuración del equipo

Las lecturas de D020 en `t07_relieve.py` y `t07_verificar.py` especifican UTF-8.
La prueba de regresión ejecuta integración y verificación sobre fuentes reales,
simulando cp1252 para cualquier lectura de la bitácora sin codificación explícita.
También comprueba que ambas funciones pidan UTF-8. No se ejecutó en un equipo
Windows: la evidencia es una simulación del fallo de codificación identificado.
No cambia D020 ni las tolerancias numéricas de T05.

### 2. Grupo conservado para referencia y evaluación

`cultivo_origen` equivale a `grupo_registro` en T03. Tiene ahora el rol
`referencia_y_evaluacion`: respaldo por grupo cuando falta soporte municipal,
calculado sólo dentro del entrenamiento, y desgloses del error por grupo.
`contrato_columnas.json` declara esos usos, prohíbe normalizar el texto original
y aclara que el grupo no es predictor automático ni el estrato interno de T03
(que sigue siendo municipio/otros). Las pruebas verifican conservación literal,
exclusión de predictores y rechazo del rol anterior o de predictor automático.

La tabla común conserva 60 columnas: 35 candidatas, 18 de calidad, cinco
metadatos, un objetivo y una para referencia/evaluación. Ningún cálculo de
referencia se ejecuta en T07; este contrato prepara su uso conforme a T03.

### 3. Calidad espacial y sensibilidad por ventana

`calidad_ventanas.csv` conserva sus trece columnas anteriores y añade ocho:

| Columna | Significado |
|---|---|
| celdas_lluvia_tocadas_t02 | Conteo de intersecciones de lluvia publicado por T02; no celdas válidas ni conteo de temperatura |
| centroide_dentro_parcela | Bandera geométrica climática original T04, sin desplazar el punto |
| meses_centroide_validos | Meses presentes con valor finito en el centroide |
| dias_centroide_validos | Días de esos meses; no implica ventana completa |
| periodos_sin_centroide | Meses ausentes o sin valor del centroide |
| valor_centroide_ventana | PREC sumada; Tmin/Tmax ponderadas por días, sólo si están todos los meses |
| diferencia_media_menos_centroide | Media espacial de ventana menos agregado del centroide, con los mismos meses y pesos |
| estado_comparacion_centroide | comparable, centroide_incompleto o ventana_no_completa |

El conteo es un atributo de parcela repetido por ventana/variable. Su nombre,
definición, producto y procedencia identifican la cuadrícula de **lluvia T02**;
no se atribuye ese conteo a la cuadrícula de temperatura. Ambas cuadrículas
presentan el mismo conteo en el detalle local actual, pero el contrato no
asume que esa coincidencia se mantenga en futuras entregas. No se requieren
archivos locales privados ni volver a extraer mapas para reproducir T07.

Hay 166 parcelas con una celda de lluvia, 29 con dos y dos con tres: 31 con
varias. Los centroides climáticos exteriores son AGC_078, AGC_152 y AGC_182.
La bandera de relieve T05 permanece separada y no sustituye a la de clima.

Una comparación sólo se publica si la media principal de ventana y el agregado
del centroide están completos. Si falta un mes del centroide, queda vacío su
agregado y la diferencia; se indican meses y días válidos. Si la media tiene
cobertura parcial, la diferencia queda vacía aunque el centroide esté completo.
Un centroide con cero real sí es válido. `comparable` certifica disponibilidad
para la comparación, no pertenencia del centroide al polígono ni exactitud
predictiva. Este diagnóstico no modifica predictores ni usa rendimientos.

## Verificación y conservación

- Suite completa: **230 pruebas aprobadas**, diez más que la entrega anterior.
- 1,182 resúmenes climáticos contrastados con Decimal: máximo `1.02e-13`.
- 1,182 agregados del centroide contrastados con Decimal: máximo `8e-14`.
  Las diferencias frente al centroide también se recalculan independientemente.
- Dos ejecuciones en carpetas nuevas: doce archivos idénticos entre ejecuciones.
- Tabla común, catálogo, variables y ventanas climáticas y calidades de satélite
  y relieve: idénticos byte a byte a la versión anterior. Las trece columnas
  anteriores de calidad climática también se conservaron literalmente.
- 197 IDs, 138 etiquetas originales y 59 vacías conservados; maestro y 24
  archivos fuente intactos. No se imputa, elige ventana, reproyecta ni extrae.
- Las pruebas rechazan conteos/claves inválidos, bandera geométrica inconsistente,
  alteraciones de sensibilidad incluso con huellas nuevas y comparaciones
  incompletas presentadas como completas.

El diccionario pasa de 135 a 143 filas. Se regeneran cinco derivados:
calidad_ventanas.csv, contrato_columnas.json, controles.json,
diccionario_columnas.csv y manifest.json. Las versiones de integración y contrato
son `t07_integracion_bloques_v2` y `t07_columnas_por_funcion_v2`; los modos de
preparación previos también identifican su contrato v2. Para una entrega anterior,
usar su revisión de código o regenerar; no alterar manualmente sus huellas.
Los pasos de reproducción de [fases 4–5](t07_fase_4_5.md) siguen aplicándose.

Se corrigió un problema de la prueba nueva: macOS presenta rutas temporales
mediante alias `/tmp` y `/private/tmp`; la simulación ahora resuelve ambas rutas
para asegurar que intercepta realmente las lecturas. La fixture de fases 0–2
incluye una tabla de soporte válida, en vez de texto de relleno; sólo afecta
pruebas aisladas, no los datos compartidos.

## Pendientes y estado de publicación

Estos cambios atienden exclusivamente las observaciones 1, 2 y 3 de Jass.
Siguen pendientes el criterio explícito de área para T10 (punto 4) y la entrega
o contrato de unión para desgloses T03 bis (punto 5). No se declara cerrada T07
ni se publica el lote sin nueva autorización de Dani. Jass debe revisar las
correcciones antes del cierre. Evidencia local ignorada:
`reports/t07_correcciones_pr14_20261010/`.

[Correcciones solicitadas por Jass](https://github.com/danielalira20/AgroCebada-2026/pull/14#issuecomment-6101334053).
[Calidad y complementos](https://github.com/danielalira20/AgroCebada-2026/pull/14#issuecomment-6101340933).
