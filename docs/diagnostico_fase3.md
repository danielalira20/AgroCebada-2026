# Diagnóstico de errores y aplicabilidad · fase 3

**Responsable: Dani. Fecha: 14 de octubre de 2026. Estado: entrega local para revisión; no aprobación independiente ni nuevo modelo.** Rama `t15-diagnostico-fase3`, desde fase2 `d7f9a87`. Diseño registrado en `c75b621` antes de calcular. No se modifica T03, T02, T04, T05 ni T06; tampoco la tabla T07, etiquetas, particiones o predicciones existentes.

## Problema que resuelve y solución que implementa

Los errores compartidos de los modelos anteriores todavía no tenían una revisión conjunta de contornos, escala, capturas y curvas originales. Se reconstruyen las observaciones desde **DataSet.zip original**, se contrastan los resúmenes T06/T07, se preparan diez fichas dobles con mapas y curvas, y se comparan las señales de calidad con el error de **todas las 138 parcelas etiquetadas**. La calidad se inventaría para las 197; las 59 sin etiqueta no reciben error ni se utilizan para seleccionar parámetros.

Se mantienen los diez casos y diez controles congelados en fase0, con los cuatro fallos compartidos primero. Los controles se eligieron sin rendimiento ni error, pero son el mejor disponible: AGC_127/057 y AGC_049/092 tienen distinta calidad de contorno; AGC_069/139, distinta área por un factor cercano a cinco. No se reemplazan por controles más favorables tras ver curvas.

## 3.1 · Contornos, escala y cobertura

Se comprobaron identidad, validez y CRS de las **197 geometrías originales**; no fue necesario repararlas. Revisión visual asistida de las **20 imágenes locales del atlas** y sus curvas, con observaciones por ID en [revision_visual](../registro/diagnostico/fase3_revision_visual.csv). El atlas Esri de Jass no documenta la fecha de adquisición. Permite observar contornos y elementos visibles; no confirma cebada, manejo ni situación de campaña 2025. Se conservan las categorías A/B/C de Jass y la firmeza de su revisión, sin recalificar mirando etiquetas.

Las cuatro parcelas con mayor error compartido son **A**, con cobertura climática y de relieve completa. Sus áreas declaradas son 11.63, 1.97, 11.53 y 8.09 ha. No comparten un defecto evidente de contorno que explique las cuatro. El conjunto climático hasta octubre tiene cobertura mínima mayor que0.99999999999; cobertura completa no significa alta resolución ni información distinta por parcela.

Hay riesgos concretos de mezcla espacial en otros casos: **AGC_127**, claro en bosque con árboles incluidos (B); **AGC_049** y **AGC_055**, campos separados unidos por franja estrecha (C); **AGC_069**, sólo0.38 ha, junto a construcciones. Se ven también irregularidades o vegetación en controles. El rectángulo envolvente mide una escala, no el ancho mínimo real de los brazos de una parcela.

En A/todas, las parcelas C presentan MAE 0.5033 (n=5), B0.2192 (n=8) y A0.3183 (n=125). La alerta previa de contorno tiene MAE 0.3014 (n=24), frente a 0.3230 sin alerta (n=114). Son grupos pequeños y distribuidos de modo distinto por municipio; **no justifican borrar parcelas ni afirmar que corregir el contorno reducirá el MAE**. Las dos pendientes ausentes por D020 son AGC_023/170, ajenas al top10, y su MAE conjunto es0.0229; no explican los fallos principales.

El paquete entrega estadísticas satelitales por parcela, no imágenes2025 ni máscaras de píxeles válidos. No conocemos el método de extracción de bordes FIRA. Los escenarios nominales 3mPlanetScope y10/20mSentinel-2 sirven para ilustrar escala; **área/tamaño de píxel no es número de píxeles válidos**, ni100−nubosidad es cobertura. Las especificaciones oficiales describen esos sensores, sin acreditar el producto/procesamiento exacto FIRA. [Planet](https://docs.planet.com/data/imagery/planetscope/), [Copernicus](https://sentiwiki.copernicus.eu/web/s2-mission).

## 3.2 · Vecindad y mapas

Los mapas muestran el sesgo OOF T08 en las **138 etiquetas**, con el mismo rango de color en A/B, incluyendo los respaldos. Las tablas conservan también la máscara municipal135 y sus registros elegibles. No se infiere distancia en metros a partir de grados: los mapas generales usan longitud/latitud; los contornos locales usan EPSG6372 en metros.

Se cruzan los **87 pares T02** con las particiones:45 pares entre conocidas,190/225 separaciones de fold en A y23/225 en B. No se recalifica el umbral con distancias redondeadas. B agrupa celdas y reduce este cruce, pero no garantiza ausencia de toda dependencia espacial. Los pares del catálogo completo son **sólo auditoría**, nunca atributos aprendidos con etiquetas de evaluación.

AGC_171 y AGC_024 están a **0.92m por orillas**, comparten celda30_33 y ambas se sobreestiman. Pero AGC_008 y193, también cercanas a171, tienen sesgos A pequeños (−0.0616 y−0.0760). No aparece una explicación uniforme de error por celda: entradas climáticas compartidas acompañan rendimientos y errores distintos. Compartir celda principal tampoco asegura igualdad de todo el clima si el polígono cruza más celdas; AGC_026 toca dos, con fracción principal0.5802 y cobertura total completa.

## 3.3 · Capturas y curvas

Se preservaron los tres sensores, índices, fechas y vacíos originales. Las curvas se recortan antes de suavizar: Planet≤20% nube, Sentinel-2/Landsat≤5%, ventanaabr_oct yjun_oct, corte31oct2025. Se reutilizan las reglas T06 de inicio, pico, final, meseta y posible doble ciclo. Ninguna fecha se traduce a BBCH, siembra o cosecha. Las líneas unen observaciones válidas; el mayor hueco interno aparece sombreado, sin inventar capturas.

Se reproducen los rasgos de referencia T06: final observado **77/197 Planet y56/197 Sentinel-2**; posible doble ciclo42/20 y meseta23/27. Al cambiar a jun_oct cambian base y umbrales, por lo que mayor número de finales observables no prueba más cosechas: no se selecciona ventana por este resultado. Las fichas utilizan abr_oct y conservan ambos resultados en tablas.

**Los diez casos carecen de final observable antes del corte en ambos sensores.** Tienen67–95 capturas Planet y30–33 Sentinel-2; huecos máximos Planet18–25d y Sentinel-2 de20–28d. No son diez parcelas sin señal. AGC_049 tiene huecos25/20d alrededor de su máximo Sentinel-2; AGC_127, meseta en ambos sensores; AGC_162 tiene un máximo Sentinel-2 tardío. Estas son incertidumbres de observación, no fechas agronómicas confirmadas.

Entre las138 conocidas,84 no muestran final Planet y102 no lo muestran en Sentinel-2. Su MAE A/todas es0.3794/0.3498, frente a 0.2256/0.2328 cuando el final es observable. **Es asociación exploratoria**: los casos se seleccionaron por alto error, municipio y manejo pueden confundirla, y muchos controles también carecen de final. No se introducen datos posteriores al corte para completar ciclos ni se decide un modelo usando esa diferencia.

### Comparación adicional de los controles fijos

Tras ver las primeras fichas se registró esta ampliación descriptiva, sin nuevo experimento predictivo: comparar NDVI únicamente en **fechas válidas comunes**, sin interpolar huecos ni mezclar sensores. El RMSE de esa diferencia no es RMSE de rendimiento y no tiene umbral universal de equivalencia.

| Par fijo | Diferencia de rendimiento caso−control, t/ha | Fechas comunes Planet/S2 | RMSE diferencia NDVI Planet/S2 | Clima T07 idéntico |
|---|---:|---:|---:|---|
|171/197|−2.37|69/29|0.0507/0.0721|Sí, seis entradas|
|015/124|−2.41|77/28|0.0587/0.0660|Sí|
|024/100|−1.47|71/27|0.0552/0.0632|Sí|
|034/166|−0.50|56/25|0.0819/0.0892|No|

Hay diferencias en curvas y final observado; **no son curvas idénticas ni manejo confirmado igual**. Aun así, los tres primeros pares combinan clima idéntico, tamaño cercano y señales de verdor visualmente parecidas con etiquetas muy diferentes. Es una razón concreta para investigar trazabilidad del rendimiento, eventos y manejo por parcela en fase4, sin asumir etiqueta falsa. El verdor por sí solo no determina peso de grano.

Se contrastan20 atributos de calidad con MAE porID, globalmente y después de restar medias municipales de ambos atributos para el diagnóstico. Las mayores correlaciones absolutas residuales A/todas son pequeñas: cobertura pendiente0.1492, número de vecinas−0.1478 y hueco Sentinel-20.1229. No se calculan p-valores ni se seleccionan atributos por ellas; las80 filas de A/B y máscaras son idénticas Mac/Docker.

## 3.4 · Fechas, unidades y consistencia

Los originales contienen48,626 observaciones Landsat,59,040 Sentinel-2 y47,804 Planet, con **cero duplicaciones sensor+ID+fecha**. Se inventarían1,914/3,091/7,932 capturas posteriores al corte respectivamente; se conservan separadas de la extracción modelable. En las fichas están en zona gris, como diagnóstico. Disponibilidad histórica de cada captura: **no documentada**; fecha observada no acredita fecha de publicación. No se mezclan LAI2 Planet conLAISentinel-2 ni se asigna unidad física no documentada aVI6T.

La reconstrucción independiente de resúmenes y controles ofrece **11,032 contrastes** contra T07, con máximo2.8422e−14≤1e−9. Un segundo auditor, separado del productor, repite T06 y realiza **27,186 contrastes**, incluidos los8,668 valores compactos y una prueba que modifica índices posteriores al corte: ninguno cambia las entradas al corte. Linux reproduce los8,668 valores originales; Mac tiene la siguiente excepción explícita.

### Observación pendiente para Daf: recuento sobre el umbral

En [T06 línea463](../scripts/t06_satelite.py), `np.interp(a_ns(diario),a_ns(f),sv)` usa nanosegundos; línea464 compara con `base+0.5*amplitud`. Para **AGC_114 / pl_ndvi_dias_sobre_mitad_abr_oct**, la tabla conserva99. Docker devuelve99; Mac devuelve98. El20jul2025 está exactamente en0.4695 según aritmética racional de los decimales originales. En Mac la interpolación produce0.4695 y el umbral binario0.46950000000000003, diferencia5.55e−17; el día se excluye.

No es una fecha mal etiquetada, nube faltante ni fuga temporal. Se aisló la operación; no se atribuye indiscriminadamente aPROJ o al chip. La réplica con días relativos y el recuento racional conservan99. **No se editó el código de Daf ni T07.** Propuesta para Daf: interpolar con días relativos y fijar la regla de igualdad al umbral, probar las8668 variables en Mac/Docker y registrar el resultado. Si conserva esos mismos datos, no implica volver a entrenar los modelos anteriores; si cambia alguna entrada aceptada, revisar después el alcance. La implementación propia de diagnóstico ya usa días relativos. El auditor no oculta la excepción ni permite discrepancias nuevas.

## Incidencias propias y cómo se resolvieron

1. **Cruce tras reproyectar esquinas de celda.** El control detectó discrepancias de fracción de hasta 0.001318. Proyectar cuatro vértices convierte un borde largo en una cuerda ligeramente distinta. Se corrigió calculando intersección en la rejilla4326 original y área geodésica comoT02, con las tolerancias de redondeo originales, no ampliándolas para pasar. EPSG6372 sirve para escala local. El comparador incorrecto queda identificado como tal, nunca como peso de clima ni cambio de T04.
2. **Correlación falsa por redondeo de cobertura.**102 valores diferentes representaban coberturas completas a distancias menores a1e−9 de1. Se conserva la cifra original; sólo para asociación se normaliza esa zona numérica a1. No se presenta ruido microscópico como variación de calidad ni se imputa D020.
3. **Memoria y gráficos.** Las90 pruebas Linux pasaron, pero ejecutar después el productor en el mismo proceso retenía los datos de pruebas y agotó768MB. Se separaron procesos; productor limitado a1GB, auditor separado, sin cambiar cálculos o dependencias. Se corrigieron etiquetas solapadas de ejes logarítmicos en una figura. Docker se apaga al terminar.
4. **Diferencias físicas entre entornos.** El diseño inicial de1 micrómetro para rectángulos fue demasiado estricto para GEOS/PROJ: máximo0.000116m en ancho. Se registró explícitamente, después de observarlo, tolerancia1mm sólo para estas medidas diagnósticas y1e−8 para fracciones geodésicas; no se cambia tolerancia1e−9 de índices, MAE o datos de modelo. No cambian IDs, celdas, categorías, asociaciones o lectura visual. Las medidas literales de ambos entornos quedan conservadas.

## Entrega, comprobación y siguiente fase

- [PDF de12 páginas](../registro/diagnostico/fase3_fichas.pdf): diez pares, mapas A/B y calidad frente al error. PNG/PDF individuales y nueve CSV en [fase3](../registro/diagnostico/fase3/manifest.json).
- [Diccionario](../registro/diagnostico/fase3_diccionario.csv):183 columnas por archivo, significado, unidad y vacío. [Observación T06](../registro/diagnostico/fase3_observaciones_T06.json), [verificación](../registro/diagnostico/fase3_verificacion.json) y fuentes identificadas.
- **90 pruebas** con snapshots reales en Mac/Linux, sin omisiones; fuentes fase0–2 conservadas. Comparación de120,169 celdas CSV entre entornos, con tolerancias físicas explícitas. Cinco CSV exactos en bytes, cuatro con diferencias numéricas documentadas. Once de doce figuras idénticas por píxel; la ficha127 difiere en sólo dos píxeles de 2,592,000 por un nivel RGB, sin cambio visual ni de interpretación. PDF final renderizado y revisado.
- Reconstrucción: `python -m scripts.diagnostico_fase3 --salida DESTINO_NUEVO --series DESTINO_LOCAL_NUEVO`; auditado con `python -O -m scripts.auditar_diagnostico_fase3 --salida DESTINO`. Las series completas recuperadas siguen locales e ignoradas. No sobrescribir originales ni salidas históricas.

**Fase3 preparada para revisión independiente.** Aún no demuestra una mejora de MAE ni una causa agronómica. Fase4 debe cruzar las etiquetas, su precisión, denominador y procedencia con factores locales observados o faltantes, especialmente en171/015/024/034. Después corresponde registrar hipótesis y evaluar mejoras con selección interna y el procedimiento común; no corregir rendimientos, añadir observaciones posteriores ni borrar casos para mejorar el resultado. La propuesta previa de mediana/objetivoMAE sigue sin implementar y no se promovió aquí.

Referencias de procedimiento: skills de análisis exploratorio y GeoPandas/pensamiento crítico; Kassis etal.(2026), *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, [DOI](https://doi.org/10.48550/arXiv.2609.00065), v2 consultada14oct2026. Son apoyo de método, no evidencia de reducción deMAE. Plan operativo: pestaña Diagnóstico de errores y aplicabilidad, revisión congelada en fase0. No se modifica el GoogleDoc ni se publica esta rama.
