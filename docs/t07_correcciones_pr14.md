# T07 · Correcciones 1–5 del PR #14

10 de octubre de 2026. Rama `t07-tabla-comun`; base `dev` identificada
`8d6f543d4b907a92cc00658905f238479e4e2e76`. Cambios locales preparados para
revisión de Jass; `cierre_t07=false`. No se entrenaron modelos ni se modificó T03.

## Problema que resuelve

La lectura implícita de la bitácora podía rechazar D020 en configuraciones
Windows que usan cp1252. El contrato clasificaba el grupo de registro sólo como
auditoría, aunque T03/D019 requieren conservarlo para respaldos y reportes.
La calidad de ventanas no trasladaba los diagnósticos de celdas y centroide
que ya existían en T02/T04. También faltaban el área candidata explícita de T10
y una entrega por ID de las banderas necesarias para los desgloses de T03 bis.

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

### 4. Área candidata para T10

Se identifica **area_ha_origen**, la superficie declarada original del dataset,
como candidata explícita del experimento T10. Se conserva en `tabla_comun.csv`
como metadato: elegir esta candidata no autoriza incorporarla automáticamente
a T09 ni demuestra que mejore una predicción. T10 corresponde a Jass, con
revisión de Daf; su evaluación deberá contrastar el territorio frente al
territorio más relieve/área conforme al protocolo vigente.

Esta elección conserva el significado original de la superficie en vez de
sustituirla silenciosamente por una reconstrucción geométrica. Las alternativas
son `area_ha_geodesica` en el catálogo T02 (ha) y `area_parcela_6372_m2` en
`calidad_relieve.csv` (m², sólo con T05 integrado). Permanecen en auditoría.
Usar una alternativa en un modelo exigiría un experimento explícito, la
conversión de unidades correspondiente y trazabilidad de la elección.
`contrato_columnas.json/area_t10` hace verificable este acuerdo. Aún no está
confirmado que el área declarada sea la misma superficie utilizada como
denominador del rendimiento; no se presenta rendimiento × área como producción
confirmada ni se resuelve esa pregunta sin los organizadores.

### 5. Calidad por parcela para T03 bis

`calidad_parcelas.csv` entrega **197 filas y siete columnas**, ordenadas por ID.
No se cambian geometrías, etiquetas, particiones ni reglas para elegir ganador.
El diccionario clasifica las seis columnas auxiliares como `solo_auditoria`;
la clave es metadato. El contrato `calidad_t03_bis` impide su atribución como
predictores automáticos.

| Columna | Fuente y regla |
|---|---|
| id_parcela | ID original; una fila por parcela |
| contorno_categoria | A/B/C literal del catálogo T02 |
| contorno_angosta_o_muy_pequena | si/no literal del catálogo T02 |
| alerta_contorno_t03_bis | si si categoría B/C o marca de angosta; sensibilidad secundaria, no filtro de la evaluación principal |
| escalon_etiqueta_municipio | Paso municipal publicado por T02, contrastado entre soporte y precisión; vacío si no identificable |
| vecina_etiquetada_menos_20m | Existe otra parcela con etiqueta presente en los pares cercanos publicados por T02 |
| numero_vecinas_etiquetadas_menos_20m | Número de vecinas etiquetadas distintas; excluye la propia parcela y conserva cero real |

Los contornos son A:175, B:12 y C:10. Hay 24 etiquetadas con alerta de contorno;
70 de las 138 etiquetadas y 24 de las 59 reservadas tienen vecina etiquetada
cercana. El paso queda vacío para AGC_047, AGC_048, AGC_120 y AGC_164: no es
cero, no se asigna una clase arbitraria ni se elimina una parcela por ello.

**La vecindad se refiere al catálogo completo de 138 etiquetas conocidas**, no
al subconjunto de entrenamiento de un pliegue. Sólo sirve para desglosar errores.
El paso municipal también caracteriza etiquetas del catálogo completo. Usarlos
como entradas o como respaldo del entrenamiento requeriría otro contrato y
recalcular cualquier información dependiente de etiquetas sólo con entrenamiento.
Las parcelas reservadas no adquieren un rendimiento: reciben atributos auxiliares
por municipio y cercanía, manteniendo su objetivo vacío.

T02 seleccionó los 87 pares con distancia de orillas **sin redondear <20 m** y
luego publicó distancias a dos decimales. T07 respeta la pertenencia a esa tabla;
no vuelve a filtrar por el número publicado. Una futura distancia publicada
20.00 puede representar 19.999 m y seguir siendo válida. Una prueba protege
este caso, los pares propios/duplicados/ajenos y las fuentes contradictorias.

Para consumir la calidad, cargar los IDs como texto y hacer una unión izquierda
por `id_parcela`, validando `one_to_one` para la tabla de parcelas o `many_to_one`
para predicciones fuera de entrenamiento repetidas por pliegue. Verificar que
no aumente el número de filas ni queden IDs sin pareja; usar los campos unidos
sólo en reportes. No unir por posición ni conservarlos en la matriz de entradas.
En pandas, `predicciones.merge(calidad, on="id_parcela", how="left",
validate="many_to_one", indicator=True)` permite comprobar que todas las filas
queden como `both`. Mantener el paso ausente como ausente y el conteo cero como
cero. La alerta prepara la sensibilidad T03 ya acordada; T07 no recalcula métricas.

Las dos fuentes adicionales (pares cercanos y precisión municipal) tienen
huellas propias en `fuentes_calidad_t03_bis_sha256`. Cambiarlas exige regenerar
esta calidad, pero no cambia la referencia de las dos tablas de T04 ni obliga
a repetir los 144 mapas. Los comentarios de scripts T02 siguen siendo procedencia
archivada, sin bloquear por sí mismos la integración.

## Verificación y conservación

- Suite completa actual: **240 pruebas aprobadas**. Los puntos 1–3 habían pasado 230;
  los puntos 4–5 agregan diez comprobaciones de contrato, casos límite y alteraciones.
- 1,182 resúmenes climáticos contrastados con Decimal: máximo `1.02e-13`.
- 1,182 agregados del centroide contrastados con Decimal: máximo `8e-14`.
  Las diferencias frente al centroide también se recalculan independientemente.
- Dos ejecuciones en carpetas nuevas: trece archivos idénticos entre ejecuciones.
- Tabla común, catálogo, variables y ventanas climáticas y calidades de satélite
  y relieve: idénticos byte a byte a la versión anterior. Las 21 columnas
  de calidad climática de los puntos 1–3 también se conservaron literalmente.
- 197 IDs, 138 etiquetas originales y 59 vacías conservados; maestro y 26
  archivos fuente intactos. No se imputa, elige ventana, reproyecta ni extrae.
- Las pruebas rechazan conteos/claves inválidos, bandera geométrica inconsistente,
  alteraciones de sensibilidad incluso con huellas nuevas y comparaciones
  incompletas presentadas como completas.

El diccionario pasa de 143 a **150 filas** respecto a los puntos 1–3. Se añade
calidad_parcelas.csv y se regeneran contrato_columnas.json, controles.json,
diccionario_columnas.csv, inventario_fuentes.json y manifest.json. Las siete
CSV anteriores de datos/calidad, salvo el diccionario, permanecen byteidénticas.
Las versiones de integración y contrato son `t07_integracion_bloques_v2` y
`t07_columnas_por_funcion_v2`; el verificador exige las fuentes y contratos
actuales. Para una entrega anterior, usar su revisión de código o regenerar;
no alterar manualmente sus huellas. Los pasos de reproducción de
[fases 4–5](t07_fase_4_5.md) siguen aplicándose.

Se corrigió un problema de la prueba nueva: macOS presenta rutas temporales
mediante alias `/tmp` y `/private/tmp`; la simulación ahora resuelve ambas rutas
para asegurar que intercepta realmente las lecturas. La fixture de fases 0–2
incluye una tabla de soporte válida, en vez de texto de relleno; sólo afecta
pruebas aisladas, no los datos compartidos.

## Pendientes y estado de publicación

Los cinco puntos de Jass están atendidos y comprobados localmente. La nueva
revisión independiente y el cierre humano siguen pendientes (`cierre_t07=false`).
No se publica el lote sin nueva autorización de Dani. Evidencias históricas de
1–3: `reports/t07_correcciones_pr14_20261010/`; de 4–5 y entrega actual:
`reports/t07_correcciones_4_5_pr14_20261010/`.

[Correcciones solicitadas por Jass](https://github.com/danielalira20/AgroCebada-2026/pull/14#issuecomment-6101334053).
[Calidad y complementos](https://github.com/danielalira20/AgroCebada-2026/pull/14#issuecomment-6101340933).
