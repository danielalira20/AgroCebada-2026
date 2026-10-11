# Preparación de T09 · diagnóstico del punto 2 y revisión de Tab 8

Responsable: Dani. Revisión de T09: Migue. Estado: diagnóstico local exploratorio;
validación en el Docker común y revisión humana pendientes. Fecha: 11-oct-2026.
Base: `dev` con PR14 y PR16 integrados, commit `cb45807`.

## Problema que resuelve

La tabla común ya existe, pero sus columnas no representan 60 entradas
independientes. Antes de implementar T09 hay que distinguir calidad, información
territorial, redundancia y señal climática. También es necesario comprobar las
cifras de Tab 8 sin convertir observaciones descriptivas en selección previa
de variables o en resultados de un modelo que todavía no se ha entrenado.

## Solución que implementa

`scripts/t09_diagnostico_atributos.py` verifica la entrega T07 por sus huellas,
roles y población; produce ocho tablas agregadas y dos figuras opcionales.
Preserva las 197 parcelas, 138 etiquetas y 59 etiquetas ausentes. El municipio
se trata como categoría; 34 de las 35 candidatas son numéricas.

No imputa, elimina parcelas, elige ventanas, ajusta modelos ni cambia T03.
Las correlaciones con rendimiento usan exclusivamente las 138 etiquetadas y
son exploratorias. Si informan futuras decisiones, éstas deben registrarse y
repetirse dentro de cada entrenamiento: haber visto estos resultados forma
parte del historial exploratorio y no debe presentarse como selección ciega.

## 1. Qué rescatamos de Tab 8

Fuente revisada: [Tab 8](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk/edit?tab=t.xgecwo5w1w3m).
Se contrastó con el Plan unificado corregido, Selección de atributos y T03.
La pestaña de Jass se conserva como propuesta; esta revisión no la modifica.

### Columnas repetidas y sensores

Se confirman **siete pares idénticos en las 197 parcelas** entre abr_oct y jun_oct:

- Seis candidatas: `pl_ndvi_max`, `pl_lai2_max`, `pl_ndvi_std_en_maximo`,
  `s2_ndvi_max`, `s2_ndwi_en_maximo` y `s2_ndvi_std_en_maximo`.
- Una variable de calidad: `s2_hueco_max`.

Por tanto, «seis pares de candidatas» y «siete pares incluyendo calidad» son
recuentos compatibles. Conviene precisar el alcance, no reemplazar todos los
«seis» por «siete» sin mirar a qué columnas se referían.

La correlación Planet/Sentinel-2 del máximo NDVI es **0.914379** en las 138
etiquetadas, y **0.911327** tras descontar las medias municipales. Se confirma
la redundancia alta entre sensores, pero no que sea «más fuerte» que una
duplicación exacta. Correlación alta tampoco prueba que uno sea prescindible
para predecir ni que ambos sensores midan exactamente lo mismo.

Mantener una ventana por ajuste según el experimento, y conservar ambas en la
tabla. La coincidencia en 2025 no garantiza coincidencia en otra campaña.
La fecha de inicio de una curva resumida no acredita una fecha real de siembra
o emergencia. Las ablaciones entre sensores pertenecen a T11/T13/T15 y deben
respetar su presupuesto y selección interna; este diagnóstico no las ejecuta.

### Clima y municipio

Las cifras de Jass corresponden a **abril–octubre**, aunque su tabla no especifica
la ventana. Se reproducen con la tabla T07 aceptada:

| Variable | Fracción de variación entre municipios | Pearson global con rendimiento | Pearson dentro de municipio |
|---|---:|---:|---:|
| Lluvia abr–oct | 59.946 % | −0.46854 | −0.05531 |
| Tmin abr–oct | 91.603 % | +0.60933 | −0.04668 |
| Tmax abr–oct | 27.093 % | −0.28203 | −0.17539 |
| Lluvia jun–oct | 62.084 % | −0.34464 | −0.04722 |
| Tmin jun–oct | 86.849 % | +0.55380 | −0.09307 |
| Tmax jun–oct | 31.246 % | −0.33656 | −0.17692 |

La fracción se calcula como `1 − SS_dentro / SS_total`, con medias de estos
datos, y Pearson interno correlaciona las desviaciones de X e Y respecto de
su municipio. Son descripciones de la muestra, no R² predictivos ni efectos
causales. Los tres municipios con una sola etiqueta no aportan variación
interna; se conservan todas las parcelas y se indica el tamaño de cada grupo.

La señal global es compatible con un fuerte componente territorial, sobre
todo en Tmin. **Todavía no demuestra** que el modelo con clima mejorará poco,
que clima solo funcionará bien, que su señal sea exclusivamente ubicación o
que Tmax deba seleccionarse. T09 debe comparar territorio, clima y ambos.

También requiere precisión la equivalencia entre métodos: una regresión
conjunta con interceptos municipales sin penalizar puede calcularse mediante
centrado municipal coherente de X e Y. Una corrección en dos etapas con
referencias dejando fuera la fila no es, en general, el mismo procedimiento.
Se deben conservar como diseños distintos y documentar sus respectivos ajustes
dentro de cada entrenamiento, incluidas sus particiones internas.

### Pearson

Adoptamos el criterio prudente de Jass: descripción o cálculo dentro del
entrenamiento que decide variables. No aplicamos un umbral universal de 0.3,
no eliminamos entradas y no interpretamos una asociación como causa.
El diagnóstico publica 561 pares entre las 34 candidatas numéricas; las
correlaciones clima–rendimiento se limitan a las seis columnas climáticas.
Los grupos con menos de cinco etiquetas quedan marcados como poco informativos;
una correlación con columna constante o menos de dos pares queda ausente.

### KS y selección de las parcelas

La respuesta 9 del documento oficial `Segunda_Sesion_Preguntas_Reto.docx`
confirma «muestreo aleatorio estratificado», sin detallar en esa respuesta
las variables de estratificación. Eso explica el diseño de selección; no
prueba igualdad de distribuciones, independencia espacial ni rendimiento futuro.

Se calculó el estadístico **D** entre etiquetadas y reservadas para las seis
entradas climáticas y el área declarada, junto con medianas y casos fuera del
rango observado. No se usan p-valores como puerta de aceptación: hay empates
y dependencia espacial, mientras que la prueba KS convencional supone muestras
independientes de distribuciones continuas. Un p-valor alto no prueba equivalencia.

Hay una cifra por aclarar en Tab 8: con `area_ha_origen`, las 138/59 parcelas
de T07 y `scipy.stats.ks_2samp` bilateral por defecto, se obtiene
`D=0.139400638664`, `p=0.355929220533`, no `p=0.81`. Este cálculo se hizo
sólo para auditar la cifra citada; no se usa como inferencia válida. Hay que
identificar la columna, versión y método del resultado anterior antes de
atribuirle un error. El generador entrega D descriptivo y no p-valores.

### DBSCAN y red pequeña

Recomendación de prioridad: dejar DBSCAN fuera de este diagnóstico y mantener
el contraste no lineal acotado en T12, a cargo de Diego con revisión de Migue.
No iniciar una red aquí. Una red también puede hacer regresión; la comparación
relevante es entre procedimientos con distinta complejidad, no «red o regresión».
Una prueba pequeña puede no mejorar bajo una configuración y evaluación dadas;
no descarta todas las redes de manera definitiva.

Las razones de Tab 8 para DBSCAN deben matizarse: sus parámetros se pueden
justificar, el municipio conocido no elimina toda estructura posible y los
casos con errores grandes de rendimiento no son necesariamente anomalías en X.
La razón operativa para no ejecutarlo ahora es la falta de una pregunta adicional
concreta que justifique su coste frente a los controles disponibles.

La afirmación de nueve parcelas a más de 1 t/ha de su promedio municipal
tampoco se reproduce bajo esa definición literal: aparecen **siete** al
comparar con la media del municipio en las 138 etiquetas. También son siete
con la media municipal dejando fuera la fila, donde tres municipios únicos
quedan sin referencia local. Una referencia con respaldo o predicciones fuera
de entrenamiento es otro cálculo; se necesita precisar cuál originó los nueve.
Ningún conteo autoriza eliminar parcelas.

## 2. Qué dejó el diagnóstico del punto 2

- Tabla completa: 197 × 60, IDs únicos, 138 etiquetas y 59 ausentes.
- Faltantes adicionales: sólo dos en `pendiente_media_t10_grados`, coherentes
  con D020. Las seis columnas climáticas están completas.
- Sólo `campania` es constante en toda la tabla; su función ya es metadato.
- Hay 43 perfiles climáticos exactos entre las 138 etiquetas, 22 entre las
  59 reservadas y 53 en el conjunto de 197. Son combinaciones de entradas,
  **no un cálculo del tamaño efectivo de muestra independiente**.
- El grupo climático mayor contiene 34 etiquetadas y 14 reservadas. Un modelo
  determinista de clima solo dará el mismo valor a parcelas con las mismas
  entradas. Agregar más capas no crea información para distinguirlas.
- Ninguna reservada queda fuera del rango marginal de las etiquetadas en las
  seis entradas climáticas. Esto no acredita soporte conjunto ni generalización
  a otras campañas. Una reservada sí queda fuera del rango de área; área es
  candidata de T10 y no se incorpora por ello a T09.
- D descriptivo de clima va de 0.07590 a 0.18312. No se fija un umbral de
  aceptación a partir de estos resultados.
- Se publican mediana/IQR/MAD además de media y desviación, cercas IQR sólo
  como marcas descriptivas y sensibilidad de Pearson al retirar una etiqueta
  cada vez. No se retira ninguna parcela de las entregas ni del futuro modelo.
- Se comprobaron también 300 resúmenes climáticos: seis columnas × los 50
  entrenamientos externos de A/B ya fijados. Esto describe esas particiones;
  no sustituye la futura selección dentro de sus entrenamientos internos.

Mejora incorporada: contrastar las relaciones globales con las internas del
municipio y con la cantidad de perfiles climáticos distintos. Ayuda a distinguir
asociación territorial de capacidad real para discriminar parcelas, sin
adelantar qué modelo ganará.

## 3. Reproducción y controles

Desde la raíz, en el entorno del proyecto:

```bash
python -m scripts.t09_diagnostico_atributos --salida reports/t09_diagnostico/nueva_ejecucion
python -m scripts.t09_diagnostico_atributos --salida reports/t09_diagnostico/con_figuras --figuras
python -m unittest tests.test_t09_diagnostico_atributos -v
```

Cada salida debe ser nueva y estar en `reports/`. El manifiesto identifica
datos, particiones, código y versiones. Los ocho CSV se pueden generar sin
Matplotlib; las figuras lo requieren. `reports/` sigue fuera de Git.

Tablas: `perfil_columnas.csv`, `pares_ventanas.csv`,
`pearson_entradas_etiquetadas.csv`, `clima_rendimiento.csv`,
`clima_por_municipio.csv`, `soporte_reservadas.csv`,
`perfiles_climaticos.csv`, `clima_entrenamientos_externos.csv`.
Los grupos municipales se identifican con tokens estables en las tablas
agregadas; la entrega original conserva su catálogo. La seudonimización
no convierte esos datos en anónimos.

Pruebas independientes: Pearson y D contrastados con SciPy; centrado municipal
y fracción de variación contrastados mediante una matriz de indicadores y
mínimos cuadrados; etiquetas/entradas de reservadas perturbadas sólo en memoria
para comprobar que no cambian las correlaciones supervisadas; duplicados,
etiquetas indebidas, texto numérico, infinitos y salidas protegidas rechazados.

Durante el desarrollo se corrigieron dos problemas del diagnóstico: tratar
municipio como si fuera numérico y depender de una biblioteca de figuras ausente
en el entorno local. Se separaron las candidatas por tipo y las figuras quedaron
opcionales, con comprobación de dependencia antes de escribir resultados.
Después se instalaron las versiones gráficas ya fijadas en `requirements.txt`;
no se cambiaron las versiones acordadas del repositorio. Las ejecuciones que
fallaron no tienen manifiesto final y no son evidencia de reproducción exitosa.

La evidencia válida se conserva en `reports/t09_diagnostico_20261011/`:
`verificado_1` y `verificado_2` para la doble ejecución numérica, `con_figuras`
para visualización y `perfil_skill.json` como contraste de las 197 filas sin
truncamiento. Docker no se inició; la reproducción en el entorno común de Jass
sigue pendiente y no se declara igualdad entre plataformas.

Verificación local: **266 pruebas aprobadas, incluidas 13 nuevas**; dos
ejecuciones numéricas con sus ocho CSV y manifiesto idénticos; 14 archivos
fuente con huellas intactas; perfil independiente de las 197 filas sin
truncamiento; dos figuras inspeccionadas y `pip check` sin dependencias rotas.
La prueba de perturbación de las reservadas y los casos inválidos usa sólo
copias en memoria, no datos fabricados para completar la entrega.

## 4. Qué sigue para T09

1. Migue revisa el alcance del diagnóstico y las aclaraciones de Tab 8 que
   afectan la interpretación; Jass puede identificar las fuentes de p=0.81 y
   del conteo de nueve. No bloquean el diagnóstico ya reproducido.
2. Acordar la propuesta de territorio/clima/ambos, el cómputo de presupuesto,
   ventanas, penalización y población de puntuación interna. Usar la propuesta
   de diseño existente; este informe no la convierte en decisión aprobada.
3. Implementar el procedimiento y sus pruebas con las referencias y
   transformaciones ajustadas dentro de cada entrenamiento, incluida la
   selección interna. Mantener la referencia exacta T08 como candidato.
4. Evaluar según T03: MAE, RMSE, sesgo, R², comparaciones emparejadas, IC por
   celdas, desgloses y sensibilidad de calidad; validar en Docker y solicitar
   revisión de Migue. T11/T14 no sustituyen este experimento.

Los datos externos se valoran después de la primera T09, frente a una carencia
concreta y con presupuesto y disponibilidad explícitos. Una campaña no prueba
desempeño futuro; el diagnóstico no certifica disponibilidad histórica al corte.

## Fuentes

- Plan unificado corregido, Selección de atributos y Tab 8 del documento común.
- Respuesta 9 de `Segunda_Sesion_Preguntas_Reto.docx`, proporcionado por Dani.
- [T03](T03_protocolo_evaluacion.md), [contrato T07](t07_contrato.md) y
  [fichas](t07_fichas_atributos.md).
- [SciPy KS de dos muestras](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ks_2samp.html).
- [scikit-learn: prevención de fuga](https://scikit-learn.org/stable/common_pitfalls.html).
- Apoyo metodológico: skills privadas T07, análisis exploratorio y pensamiento
  crítico. Kassis, T., Agarwal, V., He, Y., Patel, D. y Brueckner, A. M. (2026),
  [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
  Registro consultado el 11-oct-2026, revisión actual v2; sin revista registrada.
