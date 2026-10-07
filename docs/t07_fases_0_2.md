# T07 · Preparación y evidencia de fases 0–2

Responsable: Dani. Revisora: Jass. Fecha: 7 de octubre de 2026.
Estado: fases 0–2 implementadas y comprobadas localmente; T07 en revisión.

## Problema que resuelve

El clima mensual de T04 no tiene la misma granularidad que el catálogo de
parcelas ni las ventanas de T06. Una unión por posición o una suma con meses
faltantes puede producir resultados aparentemente completos. Además, mezclar
referencias distintas de T02 y T04 impide saber qué se calculó.

## Solución que implementa

Una preparación reproducible por ID, con entradas identificadas, seis candidatos
climáticos, controles separados por variable y diccionario de todas las columnas.
Los valores no dependen de las etiquetas de rendimiento. Las siguientes fases
integrarán satélite y relieve; no se entrenan modelos en esta entrega.

## Fase 0: fuentes y dependencias

Base dev: `540193d6cdc48c90b4b361e6044ae52f9d6f9b0a`.
T04: copia exacta de `bfd818467c69878829c7e61c175ec574ed9d4dd2`,
entrega de PR #6, todavía en revisión en la consulta realizada.
No se fusionó daniela-dev, el PR #7 ni la conciliación local de bitácoras.

El inventario conserva las huellas de los cinco archivos de referencia T02,
el protocolo T03, la entrega T04 y la tabla/diccionario/documento T06.
T06 está integrado en la base; eso no demuestra aceptación completa o
reproducción de su motor en este equipo. T05 no tiene entrega identificada en
esta base: no se fabrican columnas de relieve.

Las entradas deben coincidir con los archivos de la revisión Git indicada.
Si cambia T02, el proceso se detiene hasta actualizar y revalidar la referencia
de T04. Indicar una revisión nueva no permite saltarse esta comprobación.
El inventario no consulta continuamente GitHub: describe la base de la ejecución.

La auditoría local con GeoPandas verificó los cinco componentes del shapefile
contra T04: 197 IDs compatibles, geometrías Polygon válidas, sin vacías ni nulas,
EPSG:4326 y presencia de Z en las 197. Sólo se comprobó identidad/validez;
no se midieron áreas en grados ni se repararon geometrías. La agregación temporal
usa las medias T04, sin repetir su extracción espacial ni utilizar Z como elevación.
El maestro DataSet.zip conserva la misma huella que la procedencia T04.

## Fase 1: contrato y catálogo

`catalogo_base.csv`: 197 filas, campaña 2025, 138 rendimientos originales y
59 vacíos de PREDICCION. Se conservó el texto de las etiquetas y atributos
seleccionados. No se copiaron auditorías calculadas a partir del rendimiento
como entradas del modelo.

El diccionario cubre 36 columnas de las cuatro tablas. Separa objetivo,
predictor candidato, calidad, metadato y sólo auditoría. ID y CONJUNTO nunca
son predictores; Cultivo conserva su procedencia y requiere el contraste T03.
No hay imputación, escalado, selección por rendimiento ni cambios de particiones.

## Fase 2: ventanas climáticas

| Ventana | Periodo calendario | Meses | Días |
|---|---|---:|---:|
| abr_oct | abril–octubre de 2025 | 7 | 214 |
| jun_oct | junio–octubre de 2025 | 5 | 153 |

Lluvia: suma de medias espaciales mensuales, en mm acumulados de ventana.
Temperatura: media mensual ponderada por días, en grados Celsius.
Los 144 metadatos originales confirman la agregación mensual declarada.
Tmin/Tmax no representan extremos absolutos ni permiten inferir días de helada.

Si una media mensual es NoData, la ventana queda vacía con diagnóstico.
Si existe media pero la cobertura es parcial, también se deja vacío el valor
principal: combinar superficies parciales requiere una decisión explícita.
Lluvia cero válida permanece cero. Las otras variables y parcelas se conservan.
La entrega compacta T04 v1 exige historia completa: una fila faltante o duplicada
es un fallo de contrato y detiene la preparación. Además, el agregador se probó
defensivamente con meses ausentes para impedir que una reutilización posterior
publique totales incompletos.

No se emplean noviembre/diciembre. El corte al 31 de octubre es provisional
y observacional; no acredita que el producto final estuviera publicado ese día.
Las ventanas son candidatas calendario, no fechas de siembra/cosecha confirmadas.

## Resultados y comprobaciones

- 28,368 filas mensuales y 144 mapas identificados en la entrada T04.
- 394 filas parcela × ventana y 197 filas con seis candidatos climáticos.
- 1,182 controles parcela × ventana × variable, todos completos.
- Cobertura mínima: 0.9999999999978246, conservada sin imponer otro umbral.
- 27 pruebas T07 pasan: claves, etiquetas, unidades, corte, archivos alterados,
  referencia incompatible, cero real, NoData, ausencias, cobertura parcial,
  días 30/31 y febrero bisiesto, orden, Tmin/Tmax y salida protegida.
- Tres ejecuciones completas producen los ocho archivos idénticos byte a byte
  en este entorno. No se ha afirmado reproducción en Windows o Mac Intel.
- Contraste independiente de los 1,182 resúmenes con Decimal (50 dígitos):
  diferencia máxima PREC 1.02e-13 mm, Tmin 3.12e-15 °C y Tmax 3.97e-15 °C;
  límite de comparación absoluto 1e-10 en la unidad de cada variable.
- Las seis comprobaciones sintéticas del entorno geoespacial también pasan.
- Preparación completa medida: 0.69 s y 75,907,072 bytes de memoria máxima
  residente (~72.4 MiB) en este Mac. Es una medición local, no un requisito
  mínimo universal. Los ocho derivados ocupan 167,401 bytes (~164 KiB).

Ejemplo AGC_014: lluvia abr_oct = 924.41292359592 mm;
jun_oct = 792.4847072158113 mm. Son dos resúmenes de la misma parcela,
no dos etiquetas independientes.

La evidencia local está en reports/t07_20261007/: perfil_clima.json,
auditoria_geometria.json, contraste_decimal.json, reproduccion.json,
recursos_ejecucion.txt y entorno.json. reports/ permanece ignorado.
Estos controles validan preparación temporal y procedencia; no sustituyen
la revisión espacial T04 ni prueban mejora predictiva.

## Reproducir

Desde la raíz del repositorio, con el entorno de Python del proyecto. En Windows
el ejecutable equivalente es `.venv\Scripts\python.exe`; en Mac/Linux, el que
se muestra abajo. No hace falta iniciar Docker para esta preparación.
Las revisiones Git indicadas deben estar disponibles localmente; la entrega T04
ya contiene los resúmenes, por lo que no se necesita DataSet.zip para agregar.

```sh
.venv/bin/python scripts/t07_preparar_insumos.py \
  --revision-t04 bfd818467c69878829c7e61c175ec574ed9d4dd2 \
  --estado-t04 en_revision \
  --salida reports/t07_mis_insumos

.venv/bin/python scripts/t07_preparar.py \
  --clima reports/t07_mis_insumos \
  --revision-t04 bfd818467c69878829c7e61c175ec574ed9d4dd2 \
  --base-dev 540193d6cdc48c90b4b361e6044ae52f9d6f9b0a \
  --salida reports/t07_mi_reproduccion

.venv/bin/python -m unittest discover -s tests -v
```

Cada salida debe ser nueva: no se sobrescriben entradas ni resultados existentes.
Comparar las huellas de manifest.json con registro/t07/manifest.json.
Si se modifica código o entradas, regenerar con esas identidades y revisar
las diferencias; no editar a mano valores o huellas para hacerlos coincidir.

## Pendientes y alcance siguiente

1. Revisar las correcciones de T02 y actualizar/revalidar T04 al aceptarlas.
2. Jass reproduce y revisa esta entrega; T07 no se declara cerrada.
3. Fase 3: adaptar y unir T06 por ID, revisar roles, calidad y redundancias.
4. Fase 4: integrar T05 después de revisar su entrega, sin perder parcelas.
5. Selección de ventana, imputación o escalado se aprenden dentro del
   entrenamiento conforme a T03. No se elige ganador aquí.

Guías: usarlas para formular hipótesis antes de añadir variables; no atribuir
manejo o calendario a las parcelas sin evidencia. Datos externos: reconsiderar
después de T08 y la primera evaluación T09, y antes de congelar T16. Cualquier
extensión necesita fuente, hipótesis, disponibilidad y comparación controlada.
No se añadieron productos externos, datos diarios ni nuevas métricas agronómicas.

## Uso de skills

Se creó la skill privada agrocebada-t07 y se usó el contrato privado T04.
GeoPandas apoyó identidad/validez; análisis exploratorio perfiló las 28,368 filas
completas sin exponer valores en su reporte; scikit-learn orientó la separación
entre preparación fija y aprendizaje dentro de particiones; pensamiento crítico
ayudó a distinguir población, disponibilidad, cálculo y capacidad predictiva.
No se importaron automáticamente dependencias nuevas al entorno del proyecto.
Las skills y AGENTS.md quedan fuera de Git. La referencia a
[Scientific Agent Skills](https://doi.org/10.48550/arXiv.2609.00065)
está incluida en docs/t07_contrato.md.
