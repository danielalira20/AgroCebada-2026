# T07 · Contrato común y fases 0–2

Responsable: Dani. Revisora: Jass. Actualización al 11 de octubre: la integración
de catálogo, clima, satélite y relieve, incluidas las correcciones 1–5, fue
fusionada en `dev` por el [PR14](https://github.com/danielalira20/AgroCebada-2026/pull/14).
El manifiesto conserva el estado histórico del cálculo; no se reescribe una
evidencia de ejecución para simular una aprobación automática. El nuevo
[complemento de fichas](t07_fichas_atributos.md) tiene revisión propia pendiente.
Ver [correcciones del PR14](t07_correcciones_pr14.md) y [fases 4–5](t07_fase_4_5.md). Las [fases 0–2](t07_fases_0_2.md) y [fase 3](t07_fase_3.md) conservan
los antecedentes y sus evidencias históricas.
Acuerdo de Dani del 7 de octubre de 2026. T07 avanza por bloques según el plan
unificado corregido; el cálculo técnico no cierra tareas de otros integrantes.

## Problema que resuelve

Catálogo, clima y satélite tienen granularidades distintas. Una unión incorrecta
puede duplicar parcelas, perder casos sin dato o usar columnas de auditoría como
predictores. El clima mensual necesita agregación temporal explícita.

## Solución que implementa

Identificar cada fuente, validar claves y unidades y preparar catálogo base y
ventanas candidatas sin aprender transformaciones de los rendimientos.
Las fases 0–2 prepararon el contrato; las fases posteriores integran T06 y T05.

## Universo y columnas

- Campaña 2025: 197 IDs, 138 rendimientos originales, 59 ausentes.
- Clave común: id_parcela; ID_POLIGONO de T06 es su equivalencia.
- La tabla por parcela conserva una fila por ID; el clima por mes y los controles
  por ventana/variable siguen separados. No son nuevas etiquetas.
- Un ID duplicado, ajeno o vacío produce error; no se une por posición.
- Roles: objetivo, predictor_candidato, calidad, metadato,
  referencia_y_evaluacion y solo_auditoria.
  Una columna candidata requiere el diseño de su experimento para utilizarse.
- IDs, rutas, huellas y CONJUNTO no son predictores. El grupo de registro
  se conserva para el respaldo de referencia y los desgloses conforme a T03,
  con referencia aprendida sólo en entrenamiento; no es predictor automático.
- T07 no imputa etiquetas/entradas, escala, centra por municipio, selecciona
  variables por rendimiento ni cambia particiones. Eso corresponde al modelo,
  dentro de cada entrenamiento, conforme a T03.

## Contrato de ventanas

| Ventana | Inicio | Fin observado | Meses | Días |
|---|---|---|---|---|
| abr_oct | 2025-04-01 | 2025-10-31 | 7 | 214 |
| jun_oct | 2025-06-01 | 2025-10-31 | 5 | 153 |

Son periodos calendario candidatos, no fechas de siembra/cosecha confirmadas.

PREC: suma de medias espaciales mensuales, en mm acumulados. No sumar
profundidades entre celdas vecinas ni multiplicar por hectáreas.
Tmin/Tmax: suma de media mensual × días / días de la ventana, en °C.
Los metadatos T04 dicen «Suma de precipitación diaria» y «Promedio mensual».
La temperatura resultante es una media de los resúmenes mensuales suministrados;
no es un extremo absoluto ni una reconstrucción de temperaturas diarias.

El agregador conserva ausente el valor de una ventana con mes ausente o NoData,
con motivo y conteo. La entrada compacta T04 v1 exige historia íntegra: una fila
mensual ausente/duplicada es un fallo de contrato y detiene la preparación.
No se sustituye por cero ni se publica una suma parcial como acumulado completo.
Si todos los meses tienen media pero alguno tiene cobertura parcial, se conserva
el diagnóstico y se deja el resumen principal ausente: extrapolar o combinar
soportes parciales requiere un criterio posterior explícito. Los estados de
cobertura son los de T04; no se crea un umbral nuevo.

Las filas de otras fechas permanecen en la fuente, pero no se agregan a estas
ventanas. Un indicador temporal contradictorio o mes duplicado produce error.
Corte observado no equivale a disponibilidad histórica. La entrega se describe
como reconstrucción retrospectiva mientras no exista evidencia de disponibilidad.

## Entregables previstos de fases 0–2

- inventario_fuentes.json: identidad y estado de entradas y dependencias.
- catalogo_base.csv: 197 parcelas, atributos originales seleccionados.
- clima_ventanas.csv: 394 filas parcela × ventana, tres resúmenes climáticos.
- clima_variables.csv: 197 filas con seis predictores climáticos candidatos.
- calidad_ventanas.csv: 1,182 filas con meses, días, cobertura y motivo.
- diccionario_columnas.csv: definición, unidad, función, agregación y vacío.
- controles.json y manifest.json: comprobaciones y huellas para reproducir.

Ahora `registro/t07/` contiene la entrega completa de catálogo + T04 + T06 +
T05: 197 filas, 60 columnas y trece archivos con diccionario, calidad por bloque,
roles, inventario, controles y manifiesto. El clima procede del PR11 aceptado y
el relieve del PR12 revisado y fusionado. Sus borradores anteriores permanecen
históricos en `reports/`, ignorados por Git; no se reescriben sus revisiones.
La preparación computacional no cierra la revisión humana de T07.

## Dependencias y estado

La base `dev` identificada es `8d6f543d4b907a92cc00658905f238479e4e2e76`,
con T02 corregida, T03 alineado a D019, T04 (PR11), T05 (PR12), T06 y T08.
La [sincronización](t07_sincronizacion.md) conserva el historial de integración.
T07 no recalcula métricas T08 ni modifica T03: se reportan todas y
sin_respaldo; se decide en sin_respaldo frente a media_mun__resp_grupo.
Corte y ventanas permanecen candidatos al 31 de octubre de 2025.

El modo completo usa `t07_integrar.py --con-relieve` con una copia T04
identificada en Git. Los modos previos `--sin-clima` o sin relieve siguen
sirviendo para ejecutar integraciones parciales con los bloques ausentes
explícitos. Una fuente climática `en_revision` exige `--para-revision` y salida
local `reports/`; no se declara aceptada para saltar ese control.

Relieve conserva `elevacion_media_m` y `pendiente_media_t10_grados` como
candidatas. D020 deja vacía la pendiente bajo cobertura válida 0.5, sin retirar
parcelas ni imputar: AGC_023 y AGC_170. La pendiente original y la calidad
permanecen en `calidad_relieve.csv`. Se identifican las cinco tablas/metadatos
T05 y la entrada D020; los auxiliares T05 se conservan como procedencia archivada.
No se reproyecta ni reextraen los originales para hacer esta unión.

La tabla contiene 35 candidatas, 18 columnas de calidad, cinco metadatos, un
objetivo y una de referencia/evaluación; no son 60 entradas automáticas del modelo.
El PR14 con los cinco puntos fue fusionado en `dev`. `cierre_t07=false` describe
el estado guardado por la ejecución original, cuyo programa no infiere revisión
humana. La fecha/commit del merge y el alcance nuevo se registran en las fichas.
Archivo faltante, NoData, bloque no integrado y revisión pendiente son
situaciones distintas. La reproducción y el contraste independiente de las
fases 4–5 documentan los criterios y la evidencia actual.

## Guías y datos externos

Antes de fijar variables: consultar guías y registrar fuente, hipótesis y límites;
no atribuir variedad, régimen hídrico o manejo a las parcelas sin metadatos.
Al disponer de T08 y primera evaluación T09: revisar una carencia concreta y,
si se acuerda, comparar base frente a base + un bloque externo con igual
población, estimador, particiones y presupuesto. Volver a revisar antes de T16.
No se incorporan ahora clima diario, suelo o radar ni se elige ventana ganadora.

## Recursos de trabajo y referencias

Se usaron instrucciones privadas T04/T07 y Scientific Agent Skills (GeoPandas,
scikit-learn, análisis exploratorio y pensamiento crítico). Las skills quedan
fuera del repositorio. Los perfiles y revisiones son apoyo; no prueban mejora
predictiva ni reemplazan la revisión independiente.

Kassis, T., Agarwal, V., He, Y., Patel, D., y Brueckner, A. M. (2026).
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
Registro arXiv consultado el 7 de octubre de 2026: versión actual v2; sin revista
o DOI editorial registrado. No se toma el uso de skills como certificación.

[Prevención de fuga en scikit-learn](https://scikit-learn.org/stable/common_pitfalls.html).

## Compatibilidad y procedencia T02 · 9 de octubre

T04 y T07 usan scripts/t02_contrato.py. Sólo catálogo y soporte por parcela
condicionan la compatibilidad de la referencia; los tres auxiliares se conservan
como procedencia. El inventario registra sus huellas en la base Git identificada,
sin exigir que coincidan con las de la ejecución T04 anterior ni ejecutar esos
scripts. La auditoría verifica esa procedencia archivada y las dos tablas actuales.
Cambiar una tabla u original continúa bloqueando; cambiar un comentario T02
permite integrar las mismas cifras y documenta la nueva revisión. Se leen entregas
v1 completas y v2, rechazando contratos incompletos o huellas inválidas.
Los scripts T07 que sí se ejecutan mantienen sus propias huellas de código.

La calidad climática actual tiene 21 columnas y el diccionario 150 filas.
El [detalle de correcciones](t07_correcciones_pr14.md) especifica el contrato v2,
las nuevas columnas y las reglas de vacío. Los conteos anteriores en fases 0–5
describen la entrega previa a estas correcciones.

## Área T10 y desgloses T03 bis · correcciones 4–5

`area_ha_origen` es la candidata declarada para T10; se mantiene como metadato,
sin entrada automática a T09. Áreas geodésica T02 y plana T05 permanecen como
alternativas de auditoría. `area_t10` explicita fuente, unidades y condiciones.
No se confirma la equivalencia con la superficie usada para calcular rendimiento.

`calidad_parcelas.csv` contiene 197 filas × siete columnas, para unir por ID:
contorno A/B/C, marca de angosta, alerta secundaria T03, paso municipal,
presencia y número de vecinas etiquetadas a menos de 20 m. Unión uno a uno con
parcelas y muchos a uno con predicciones repetidas; sin perder o multiplicar filas.
Las seis auxiliares son sólo auditoría. Paso y vecindad describen el catálogo
completo; no se usan como información del entrenamiento. Cuatro pasos ausentes
se conservan vacíos. La vecindad excluye la propia parcela y respeta los pares
seleccionados antes de redondear distancias. Las dos fuentes adicionales se
verifican por huellas propias, sin ampliar la referencia climática T04 ni
reextraer mapas. El detalle de reglas y consumo está en las correcciones del PR14.

## Complemento documental de atributos · punto 1

`registro/t07_fichas/` reúne 60 fichas y pendientes por fuente. Hereda literalmente
las definiciones y roles de la entrega, añade disponibilidad y requisitos de
otra campaña y distingue periodo resumido de insumos necesarios. No modifica
los 13 archivos de `registro/t07/`, T03 ni la extracción. Ver
[alcance, hallazgos, reproducción y siguiente punto](t07_fichas_atributos.md).
