# T07 · Tabla común completa y verificación

10 de octubre de 2026. Responsable: Dani. Revisora: Jass.
Rama: `t07-tabla-comun`. Entrega computacional preparada y verificada;
**pendiente de revisión independiente de Jass**. `cierre_t07=false`.
Este documento sustituye el estado pendiente de clima/relieve de las fases
anteriores; sus borradores y evidencias históricas se conservan.

## Problema que resuelve

La tabla compartida contenía catálogo y satélite (197 × 52), pero aún faltaban
clima y relieve. La fuente climática mensual no puede unirse directamente al
rendimiento: multiplicaría las filas. La pendiente con cobertura insuficiente
requiere respetar D020 para evitar que un valor de una pequeña parte de la
parcela se presente como resumen modelable de toda ella.

## Solución que implementa

Integrar las entregas aceptadas de T04, T05 y T06 sobre el catálogo T02, por ID
y con una fila por parcela. Agregar clima sólo en las dos ventanas candidatas
de T03; incorporar elevación y pendiente modelable literalmente desde T05,
y conservar la calidad y la pendiente original en una tabla de auditoría.
Contrastar las cifras con un camino independiente y reproducir en carpetas
nuevas antes de preparar el PR hacia `dev`.

El plan unificado corregido se consultó de nuevo el 10 de octubre en el
[documento del equipo](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk/edit?tab=t.q0k09ka9rtmy).
La base Git identificada es `8d6f543d4b907a92cc00658905f238479e4e2e76`:
T04 está integrada por PR #11 y T05 por PR #12. La aceptación de esos insumos
no equivale a cerrar esta nueva integración T07.

## Fase 4: integración y contrato

| Bloque | Columnas en tabla común | Regla |
|---|---:|---|
| Catálogo T02 | 8 | Identidad y valores originales; 138 etiquetas y 59 vacías |
| Clima T04 | 6 | PREC acumulada; Tmin/Tmax ponderadas por días, en dos ventanas |
| Satélite T06 | 44 | Selección literal por ID, incluyendo calidad y NDVI al corte |
| Relieve T05 | 2 | Elevación media y pendiente media con piso D020 |
| Total | 60 | 197 filas, una por ID |

Las dos ventanas de 2025 permanecen candidatas: abril–octubre (214 días) y
junio–octubre (153 días). La lluvia se suma **en el tiempo**, después de la
ponderación espacial mensual de T04. Tmin/Tmax se promedian ponderando los días
de cada mes. No son temperaturas extremas de la ventana. Noviembre, diciembre
y los años anteriores no se incorporan a estas seis entradas.

El relieve es estático y aparece una vez por parcela; no se duplica por ventana.
`elevacion_media_m` conserva la media original, en m s.n.m., y su cobertura queda
visible en `calidad_relieve.csv`. `pendiente_media_t10_grados` conserva la media
original en grados sólo si la cobertura válida es al menos 0.5. Bajo ese piso
queda vacía: **AGC_023 y AGC_170**. El piso viene de D020, no se optimizó mirando
rendimientos. `pendiente_media_grados` original sigue disponible en calidad;
no se convierte en una tercera candidata para eludir la regla.

Hay cuatro parcelas con elevación parcial y cinco con pendiente parcial;
las 59 reservadas tienen cobertura completa para ambas variables. Las dos
pendientes ausentes no se rellenan ni ocasionan eliminación de parcelas.
Una imputación futura, si el experimento la requiere, se aprende dentro de
cada entrenamiento conforme a T03. Hay 29 parcelas con avisos T05; se conserva
la bandera de centroide exterior de AGC_182, sin cambiar su punto de consulta.

`contrato_columnas.json` distingue un objetivo, 35 candidatas, 18 columnas de
calidad, cinco metadatos y una de auditoría. Las 60 columnas no constituyen una
matriz automática de entrenamiento. El área declarada conserva su rol de
metadato; el área plana EPSG:6372 queda sólo en calidad, con unidad m².
Seleccionar una ventana, usar área/indicadores de calidad o definir un experimento
con estas columnas corresponde al protocolo y a la tarea de modelado.

### Archivos compartidos

| Archivo en registro/t07 | Filas | Propósito |
|---|---:|---|
| catalogo_base.csv | 197 | Identidad y etiquetas originales |
| tabla_comun.csv | 197 | Catálogo y tres bloques de entradas |
| clima_ventanas.csv | 394 | Resúmenes por parcela y ventana |
| clima_variables.csv | 197 | Seis columnas climáticas anchas |
| calidad_ventanas.csv | 1,182 | Meses, días, cobertura y motivo por variable |
| calidad_satelite.csv | 1,182 | Capturas, huecos y presencia por sensor/ventana |
| calidad_relieve.csv | 197 | 24 columnas de auditoría T05, sin imputación |
| diccionario_columnas.csv | 135 | Definición, unidad, función y vacío por archivo/columna |

Completan los doce archivos `contrato_columnas.json`, `inventario_fuentes.json`,
`controles.json` y `manifest.json`. Las mediciones mensuales originales siguen
en T04 y las 2,253 intersecciones de relieve en T05; no se duplican aquí.
La entrega compacta permite al equipo usar T07 sin volver a extraer mapas.

### Huellas y consistencia

T02 usa dos tablas para compatibilidad y tres auxiliares como procedencia.
T05 verifica sus cinco archivos publicados y la entrada D020 archivada en la
base identificada. Los auxiliares T05 se registran como procedencia histórica,
sin ejecutar su extractor ni reproyectar geometrías. Añadir otra decisión al
registro no invalida D020: se identifica **esa entrada**, no toda la bitácora.
El código que sí se ejecuta en T07 conserva sus propias huellas.

Los archivos T07 se guardan con saltos de línea LF, fijados también mediante
`.gitattributes`, para evitar que la copia Git en Windows cambie sus huellas.
No se normalizaron las fuentes anteriores T04/T05/T06.

## Fase 5: comprobación y reproducción

La unión exige claves exactas y rechaza duplicados, IDs ajenos, colisiones de
columnas o cambios en unidades, corte y fuentes. La auditoría verifica la
conservación literal del catálogo, las etiquetas y T06, además de los roles,
el diccionario y el conjunto exacto de columnas permitido por cada bloque.

El verificador climático emplea Decimal y un calendario explícito independiente
para recalcular los 1,182 resúmenes. El nuevo contraste de relieve usa Decimal
con 40 dígitos, reconstruyendo por parcela y variable desde sus celdas: máscara,
datos válidos, área válida, conteos, mínimo, máximo, media ponderada,
cobertura, estado y sensibilidad al centroide. No llama a PROJ ni al extractor
T05. Verifica asimismo el piso D020 y las 24 columnas de calidad literalmente.

| Control | Resultado |
|---|---|
| Suite completa | 220 pruebas aprobadas; 17 nuevas en esta etapa |
| Universo y etiquetas | 197 IDs, 138 etiquetas originales, 59 ausentes |
| Valores T06 | 8,668 valores transferidos literalmente |
| Clima | 1,182 resúmenes; máxima diferencia Decimal 1.02e-13 |
| Relieve | 394 medias desde 2,253 celdas; máxima diferencia 5.21e-13 |
| Cobertura de relieve | Máxima diferencia 1.84e-16 |
| Balance espacial de relieve | Máxima diferencia relativa 2.79e-12 |
| Reproducción | 12 archivos idénticos entre dos ejecuciones nuevas |
| Continuidad | Catálogo anterior idéntico y las 52 columnas previas conservadas por ID |
| Clima previo | CSV de seis variables idéntico al borrador real anterior |

Las diferencias de medias se comparan con tolerancia absoluta 1e-9 en la unidad
de cada variable. El área válida admite máximo de 1e-9 m² y 1e-9 relativo; el
balance espacial admite 1e-6 relativo, como comprobación de las intersecciones.
La identidad de celdas, conteos y máscaras es exacta. No se modificaron las
tolerancias de reproducción entre arquitecturas de T05.

Se encontró un problema en el nuevo control: T05 conserva coberturas espaciales
como 1.000000000000001 por redondeo de operaciones geométricas. Exigir ≤ 1 sin
margen rechazaba datos válidos. T07 admite sólo un excedente de 1e-12 y conserva
el texto original, verificando a la vez su balance de áreas. Una prueba rechaza
1.00000001. No se redondearon las fuentes ni se relajaron máscaras o D020.

Las pruebas incluyen duplicados, alteración de pesos, máscaras contradictorias,
medias erróneas incluso cuando las copias coinciden, calidad alterada aun con
huella recalculada, reordenamiento de filas y etiquetas que no intervienen en
las candidatas. El contraste Decimal detecta un error numérico que una simple
comparación de huellas no detectaría si el archivo y el manifiesto se alterasen
juntos. Las pruebas anteriores de meses fuera de ventana siguen aprobadas.

### Reproducir y revisar

Desde la raíz del repositorio, con el entorno Python 3.12 y dependencias del
README, usar `python` del entorno activado. Cada salida debe ser nueva:

```text
python -m scripts.t07_preparar_insumos --revision-t04 8d6f543d4b907a92cc00658905f238479e4e2e76 --salida reports/t07_revision_equipo/entrada_t04 --estado-t04 aceptada
python -m scripts.t07_integrar --base-dev 8d6f543d4b907a92cc00658905f238479e4e2e76 --clima reports/t07_revision_equipo/entrada_t04 --revision-t04 8d6f543d4b907a92cc00658905f238479e4e2e76 --con-relieve --salida reports/t07_revision_equipo/completa
python -m scripts.t07_verificar --entrega reports/t07_revision_equipo/completa --clima reports/t07_revision_equipo/entrada_t04
python -m unittest discover -s tests -v
```

Para verificar los derivados preparados, usar el mismo verificador con
`--entrega registro/t07` y la copia T04 recién identificada. El estado aceptada
corresponde al PR11 fusionado y revisado, no lo otorga el programa. Si se ensaya
una fuente pendiente, se mantiene `en_revision` y se usa `--para-revision` sólo
en `reports/`. Los modos previos sin clima/relieve siguen disponibles para
revisar entregas parciales, con bloques ausentes identificados explícitamente.

Jass debe contrastar el contrato, las dos ventanas, los casos de pendiente
parcial y el diccionario, y reproducir las salidas desde las revisiones indicadas.
Su revisión humana determinará el cierre; completar estos controles no lo marca
automáticamente. Evidencia local detallada en `reports/t07_completa_20261010/`:
plan consultado, fuentes antes/después, dos ejecuciones, contrastes, pruebas y
casos de revisión. Los informes anteriores se conservan con su base histórica.

## Límites y siguiente paso

Las ventanas no son fases fenológicas confirmadas. La tabla es retrospectiva:
la fecha de observación no acredita disponibilidad del producto en esa fecha.
Cuatro columnas LAI2/VI6T conservan unidad física pendiente de confirmación.
Los meses sin capturas de Landsat y las siete parejas equivalentes observadas
entre ventanas siguen documentados; tener valor no garantiza cobertura suficiente.
No se elimina una pareja ni se elige sensor/ventana por observar rendimientos.

T07 queda lista localmente para el PR hacia `dev`, con Jass como revisora. No se
entrenan modelos, cambian particiones ni incorporan datos externos en esta etapa.
Las guías se usan para formular hipótesis antes de definir variables; la primera
evaluación T09 frente a T08 es el hito acordado para decidir un bloque externo
con igual población, particiones y presupuesto, y se revisará antes de T16.
No se promete una mejora predictiva por el hecho de integrar más entradas.
