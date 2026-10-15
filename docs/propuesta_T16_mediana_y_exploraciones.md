# Propuesta para T16: mediana municipal si FIRA confirma MAE, y exploraciones adicionales

- **Autor:** Migue. **Para:** T16 (Dani) y quien quiera revisar.
- **Fecha:** 16 de octubre de 2026.
- **Qué cambia en el repo:** nada del código ni de los resultados aprobados. Este PR sólo agrega este documento y los scripts para verificarlo.
- **Qué se pide:** correr la verificación, revisar el razonamiento y decidir en T16 si vale la pena.

## 1. Resumen

Proponemos que T16 deje escrita, **antes de que FIRA confirme la métrica**, esta regla:

| Si FIRA confirma… | Referencia final |
|---|---|
| MAE | **mediana municipal** con respaldo por grupo |
| RMSE, R² o no confirma | **media municipal** con respaldo por grupo, como hoy (T03, T08) |

La ganancia esperada es pequeña (MAE de 0.319 a ~0.310 t/ha). Pero es la única opción, de todas las probadas, que mejora el MAE de forma consistente. Fijar la regla antes de conocer la respuesta de FIRA evita que la elección parezca hecha a conveniencia.

## 2. Situación actual

- **Referencia y modelo final hoy:** `media_mun__resp_grupo` (T08). En el escenario A: **MAE 0.319, RMSE 0.490, R² 0.666**.
- **La mediana ya se evaluó en T08** y no pasó la regla de T03:
  - ΔMAE −0.008 en `sin_respaldo` A, con 5 de 5 repeticiones a favor;
  - IC95 por celdas de −0.016 a +0.006, que toca el cero;
  - no llega al umbral de −0.01.
- Por el desempate de T03 se conservó la media del piloto. **Esta propuesta no contradice esa decisión**: sólo pide que la métrica oficial decida entre dos opciones igual de simples.

## 3. Por qué la mediana podría convenir

1. **Teoría.** La mediana es el valor que minimiza el error absoluto, y la media el que minimiza el error cuadrático [1, 2]. Por eso la métrica con que se califica decide qué estadístico conviene: con MAE, la mediana; con RMSE, la media [1]. Es un resultado conocido, no algo sacado de nuestros datos. La regresión de cuantiles generaliza la misma idea [3].
2. **Forma de los datos.** Los rendimientos tienen cola hacia abajo (asimetría −0.33; media 3.96 y mediana 4.34). La media se deja jalar por las parcelas bajas; la mediana no.
3. **Evidencia** (predicciones fuera del entrenamiento de T08, `sin_respaldo`):

| | Media (hoy) | Mediana |
|---|---|---|
| MAE A | 0.319 | **0.310** |
| RMSE A | 0.490 | **0.487** |
| R² A | 0.666 | **0.670** |
| MAE B | 0.380 | **0.363** |
| Parcelas que mejoran / empeoran (A) | — | 86 / 45 |
| Probabilidad de que sea mejor (bootstrap por celdas, A) | — | 90 % |
| Simulación de 20 000 evaluaciones de 59 parcelas con la composición real por municipio | — | gana en 80 %, ganancia típica −0.007 t/ha (90 % entre −0.020 y +0.007) |

**Por municipio (ΔMAE en A):**

- ayuda en Chignahuapan (−0.012) y Calpulalpan (−0.020), que suman 43 de las 59;
- casi no cambia en Almoloya y Cuautepec;
- empeora en Singuilucan (+0.027).

## 4. Riesgos

- **No pasa el umbral de T03.** La mejora es real en 80–90 % de los escenarios, pero no con 95 % de seguridad. El intervalo usa bootstrap por bloques espaciales [7, 8] porque las parcelas cercanas no son independientes.
- **Sesgo de +0.04 t/ha:** la mediana tiende a predecir un poco de más.
- **En 20 % de las simulaciones pierde**, en el peor caso hasta +0.012 t/ha.
- **No se debe mezclar** (mediana donde ayuda y media donde no): eso sería elegir viendo los resultados.
- **Cambia 36 de las 59 predicciones:** Chignahuapan de 4.48 a 4.52 y Singuilucan de 3.08 a 3.20. Las otras casi no cambian.

## 5. Exploraciones adicionales: ninguna mejora la referencia

Todas usan las particiones y la regla de T03, con selección interna anidada [4, 5] y validación también por zonas (escenario B) [6, 9]. Comparan en `sin_respaldo` A y se hicieron **después** de ver los resultados de los frentes, así que son exploratorias.

| Exploración | Qué se probó | ΔMAE A | ¿Cumple? |
|---|---|---|---|
| Cribado de 117 atributos | satélite, clima, relieve y área; correlación con el residuo dentro del municipio contra un umbral de azar por permutaciones | ninguno supera el azar (máx. por azar 0.26; el mejor, 0.20) | — |
| Árbol de regresión con poda | rendimiento con municipio + 117 atributos | +0.059 (MAE 0.378) | no |
| Árbol sobre el residuo con poda | 117 atributos centrados | +0.0006 (la poda lo deja en 1 hoja) | no |
| PCA + Ridge | componentes de los 117 atributos | +0.0014 | no |
| Red neuronal (1 capa, regularizada) | rendimiento directo / residuo | +0.073 / +0.0006 | no |
| Parcelas vecinas a < 20 m | rendimiento de vecinas del mismo municipio | +0.004 | no |
| Historial NDVI 2022–2024 | potencial productivo de la parcela | +0.001 | no |
| Satélite alineado a la etapa del cultivo | NDVI, EVI y LAI a 30, 45 y 60 días del inicio de temporada | +0.0006 a +0.0021 | no |
| Opciones para MAE | media recortada, mediana por celda, mediana + LAD con clima | −0.004 a −0.007 (nada por encima de la mediana) | no |

**Contexto externo:**

- Un repositorio público con los mismos datos reporta MAE 0.331 y mejoras ≤ 0.001 con 299 atributos, XGBoost y trayectorias temporales [14].
- Nuestro enfoque, efecto del municipio más corrección con satélite y contracción, es el modelo clásico de estimación de áreas pequeñas [10, 11].
- La literatura atribuye las mejoras a datos que el reto no trae: fecha de siembra, manejo, suelo y clima diario [12, 13].
- Los rendimientos declarados o estimados tienen mucho error de medición [12]. Nuestras etiquetas vienen redondeadas (de 0.5 en 0.5 en Calpulalpan), y ese error pone un piso al MAE que ningún modelo puede bajar.

**Sobre las parcelas pegadas:** se mantienen separadas. Juntarlas dejaría 98 en vez de 138 y borraría el 23 % de la variación dentro del municipio. Su cercanía ya la controlan el escenario B y el IC por celdas.

## 6. ¿Vale la pena? Costo y beneficio

| | Mediana (si FIRA confirma MAE) |
|---|---|
| Costo de implementarla | un cambio de estadístico en la referencia de T08; no agrega datos, variables ni pasos |
| Complejidad | igual a la media; los dos son igual de explicables |
| Beneficio esperado | MAE −0.007 t/ha (de 0.319 a ~0.310), también mejor en RMSE y R² |
| Probabilidad de ganar | 80 % en la simulación de 59 parcelas; 90 % en el bootstrap por celdas |
| Riesgo | 20 % de perder, en el peor caso +0.012 t/ha; sesgo de +0.04 t/ha |
| Respaldo teórico | la mediana es el pronóstico óptimo cuando se califica con error absoluto [1, 2] |

**Lectura:** el costo es casi nulo y la apuesta es favorable (4 contra 1), con un riesgo acotado. Lo que la hace defendible es fijar la regla **antes** de conocer la métrica oficial, y apoyarla en la teoría y no sólo en nuestros resultados.

## 7. Cómo verificarlo

Desde la raíz del repo del equipo (los scripts usan `scripts/t08_referencias.py` y `scripts/t14_clima.py`):

```
python analisis/exploraciones_migue/prueba_mediana_vs_media.py scripts RUTA/DATASET_RETO_AGRO_2026 registro/t08 registro/t03/particiones.csv
python analisis/exploraciones_migue/exploracion_mae.py scripts RUTA/DATASET_RETO_AGRO_2026 registro/t03/particiones.csv RUTA/variables_clima_t14.csv
```

- **Lo que debe salir:** ΔMAE −0.0079 en A, 86 parcelas que mejoran y 45 que empeoran, P(mediana mejor) 90 % y la simulación con 80 % a favor.
- **El resto de las exploraciones** tiene su comando en el README de la carpeta.

## 8. Qué pedimos a quien revise

1. Correr `prueba_mediana_vs_media.py` y confirmar los números.
2. Revisar si el razonamiento de las secciones 3 y 4 es correcto.
3. Opinar, con la sección 6, si vale la pena dejar la regla de la sección 1 en T16 y anotarla en el registro de decisiones antes de que FIRA conteste.


## Referencias

**Teoría de la métrica y el estadístico**

- [1] Gneiting, T. (2011). Making and evaluating point forecasts. *Journal of the American Statistical Association*, 106(494), 746–762. https://doi.org/10.1198/jasa.2011.r10138
- [2] Hastie, T., Tibshirani, R. y Friedman, J. (2009). *The Elements of Statistical Learning* (2.ª ed.), sección 2.4. Springer. PDF libre de los autores: https://hastie.su.domains/ElemStatLearn/
- [3] Koenker, R. y Bassett, G. (1978). Regression quantiles. *Econometrica*, 46(1), 33–50. https://doi.org/10.2307/1913643

**Validación**

- [4] Varma, S. y Simon, R. (2006). Bias in error estimation when using cross-validation for model selection. *BMC Bioinformatics*, 7, 91. https://doi.org/10.1186/1471-2105-7-91
- [5] Cawley, G. C. y Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *Journal of Machine Learning Research*, 11, 2079–2107. https://www.jmlr.org/papers/v11/cawley10a.html
- [6] Roberts, D. R. et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography*, 40(8), 913–929. https://doi.org/10.1111/ecog.02881
- [7] Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. *The Annals of Statistics*, 17(3), 1217–1241. https://doi.org/10.1214/aos/1176347265
- [8] Efron, B. y Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall/CRC.
- [9] Ploton, P. et al. (2020). Spatial validation reveals poor predictive performance of large-scale ecological mapping models. *Nature Communications*, 11, 4540. https://doi.org/10.1038/s41467-020-18321-y

**Estimación de rendimiento y áreas pequeñas**

- [10] Battese, G. E., Harter, R. M. y Fuller, W. A. (1988). An error-components model for prediction of county crop areas using survey and satellite data. *Journal of the American Statistical Association*, 83(401), 28–36. https://doi.org/10.1080/01621459.1988.10478561
- [11] Rao, J. N. K. y Molina, I. (2015). *Small Area Estimation* (2.ª ed.). Wiley.
- [12] Lobell, D. B. et al. (2020). Eyes in the sky, boots on the ground: assessing satellite- and ground-based approaches to crop yield measurement and analysis. *American Journal of Agricultural Economics*, 102(1), 202–219. PDF: https://web.stanford.edu/~mburke/papers/lobell_et_al_AJAE_2019.pdf
- [13] Revisión sistemática de Sentinel-2 para estimar rendimiento (2026): https://arxiv.org/pdf/2603.23779 · estudio de 481 campos en Ucrania (fecha de siembra entre los predictores más importantes): https://ujrs.org.ua/ujrs/article/view/275 · cebada y etapa fenológica (BBCH-41): https://www.mdpi.com/2072-4292/17/6/957

**Comparación externa**

- [14] Repositorio público con los mismos datos del reto (métricas en `Base_De_Datos/metricas_validacion_50_splits.csv` y `Base_De_Datos/Fenologia_Cultivo/01_Diagnostico_Modelo/`): https://github.com/muniveedlam/Modelo_predictivo

*Nota:* las referencias 1 a 12 son obras publicadas; conviene abrir cada enlace y confirmar los datos antes de citarlas en el informe final. Las de la 13 se consultaron por resumen. La 14 se leyó directo de sus archivos públicos y se usa sólo para comparar, no se copió nada.
