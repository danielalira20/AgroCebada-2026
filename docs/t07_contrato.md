# T07 · Contrato común y fases 0–2

Responsable: Dani. Revisora: Jass. Estado al 8 de octubre: catálogo + T06 integrados; clima real preparado sólo para revisión local.
Ver [fase 3](t07_fase_3.md) para entrega, controles y pendientes actuales.
Acuerdo de Dani del 7 de octubre de 2026. T07 avanza por bloques según el plan
unificado corregido; el cálculo técnico no cierra tareas de otros integrantes.

## Problema que resuelve

Catálogo, clima y satélite tienen granularidades distintas. Una unión incorrecta
puede duplicar parcelas, perder casos sin dato o usar columnas de auditoría como
predictores. El clima mensual necesita agregación temporal explícita.

## Solución que implementa

Identificar cada fuente, validar claves y unidades y preparar catálogo base y
ventanas candidatas sin aprender transformaciones de los rendimientos.
Fases 0–2 no integran todavía las variables de T06 ni el relieve de T05.

## Universo y columnas

- Campaña 2025: 197 IDs, 138 rendimientos originales, 59 ausentes.
- Clave común: id_parcela; ID_POLIGONO de T06 es su equivalencia.
- La tabla por parcela conserva una fila por ID; el clima por mes y los controles
  por ventana/variable siguen separados. No son nuevas etiquetas.
- Un ID duplicado, ajeno o vacío produce error; no se une por posición.
- Roles: objetivo, predictor_candidato, calidad, metadato, solo_auditoria.
  Una columna candidata requiere el diseño de su experimento para utilizarse.
- IDs, rutas, huellas y CONJUNTO no son predictores. El grupo de registro
  conserva su procedencia; usarlo requiere el contraste explícito de T03.
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

Ahora registro/t07/ contiene catálogo + T06, con diccionario, calidad, roles,
inventario, controles y manifiesto. Las ventanas climáticas reales se calcularon
sólo como borrador local en reports/ por autorización expresa de Dani el
8 de octubre. Se incorporarán al registro tras revisar la actualización de
referencia T02 de T04. No se crean filas de relleno ni valores simulados.
La evidencia provisional anterior permanece sólo en reports/, ignorado.
Originales inmutables.

## Dependencias y estado

La base dev `11d947098d8d6e56902a7f09a2c75953f09fdb21` incluye T02 corregida
(PR #9), T04 mensual (PR #6), T06 (PR #4) y las referencias T08 (PR #8).
La actualización de referencia T02 de T04 fue revalidada localmente en la rama
`t04-actualizar-referencia-t02` (`7b2b4b4`); su publicación/revisión y posterior
incorporación a dev siguen pendientes. T07 no incorpora esa rama sin revisión.
El [registro de sincronización](t07_sincronizacion.md) conserva la evidencia.
t07_preparar.py --sin-clima conserva el modo inicial de catálogo y estados de
bloques. t07_integrar.py --sin-clima añade T06 al catálogo. Ambos registran
T04 pendiente, sin generar clima. El modo climático normal rechaza una fuente
marcada en_revision y referencias T02 incompatibles.
El PR #10 de T03 está cerrado sin merge en la consulta del 8 de octubre.
La discrepancia de población para decidir entre T03 y D019/T08 sigue pendiente
del acuerdo del equipo; no afecta a esta unión descriptiva.
T05 no entregada se registra como pendiente, sin inventar relieve.
Archivo faltante, NoData y bloque pendiente son situaciones distintas.
La fase 2 está calculada y verificada en borrador real local; su aceptación e
integración compartida siguen pendientes. t07_integrar.py --para-revision
permite esa revisión sólo en reports/; el modo normal conserva el bloqueo de
fuentes en_revision. Véase la fase 3.

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
