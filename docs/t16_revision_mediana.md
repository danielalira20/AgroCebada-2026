# T16 · revisión de media y mediana municipal

16 de octubre de 2026. Responsable: Dani; apoyo técnico: Codex. Revisión local en rama propia; sin adopción automática, publicación, merge ni predicciones finales de las 59.

## Dictamen

La mediana municipal muestra un MAE menor y mejoras pequeñas en RMSE y R² sobre las mismas OOF. La reconstrucción independiente no encuentra errores de cálculo ni filtraciones en las referencias. **La mediana no cumple la regla vigente para sustituir a la media:** la mejora principal es menor de 0.01 t/ha y el intervalo espacial incluye cero. Se conserva la media como referencia de comparación; la propuesta del PR23 necesita precisiones antes de aceptarse como decisión T16.

Esta revisión reproduce evidencia ya conocida de T08/T12/T15; no constituye un nuevo experimento ciego. No se disminuye el umbral ni se cambia de población para declarar una ganancia.

## Qué se comprobó

- [PR23](https://github.com/danielalira20/AgroCebada-2026/pull/23), commit `fd4120a3d0efadba6ba2dd488499818f615ba9aa`: documento, README y script de comparación leídos íntegramente. Las demás exploraciones se inventariaron; no se ejecutan aquí ni se acreditan por extensión.
- Las 2,760 OOF de media/mediana se reconstruyen en 100 contextos de procedimiento/escenario/repetición/partición desde T07/T03. Se usan fracciones exactas para medias/medianas de entrenamiento, sin importar T08 ni modelos del repo. Diferencia máxima frente a T08: 8.88e-16; media T08 frente a referencia T15: 8.88e-16; tolerancia conservada 1e-12.
- Cada objetivo está fuera de su entrenamiento; B mantiene separadas las celdas; las fuentes municipio/grupo/global, etiquetas y claves coinciden. Ninguna reservada tiene un rendimiento utilizable ni participa en los entrenamientos.
- Las métricas se calculan sobre predicciones históricas intactas, sin redondearlas ni promediar predicciones antes de medir error. Se separan por ID, repetición, población y escenario.
- La referencia mediana leída por T12 es el mismo CSV T08 por bytes. Se cotejaron 192 valores de MAE/RMSE/R²/sesgo de sus referencias con esta revisión. Se distingue de `t12_control_mediana_het_GP`, que añade una corrección heterogénea: sus OOF no tienen por qué coincidir con la mediana sola. Una comprobación provisional que exigía esa igualdad se corrigió al identificar ambos procedimientos; no era un fallo de los modelos. El control añadido tiene MAE A/sin_respaldo 0.314434, mayor que 0.312585 de la mediana pura.

## Cifras conciliadas

MAE y RMSE en t/ha. RMSE y R² de la tabla: promedio de métricas por repetición. La regla decide en A/sin_respaldo, no en todas las 138.

| Población A | Referencia | MAE | RMSE | R² |
|---|---|---:|---:|---:|
| Principal: 135 parcelas, 675 OOF | Media | 0.320490 | 0.492593 | 0.658577 |
| Principal: 135 parcelas, 675 OOF | Mediana | 0.312585 | 0.490683 | 0.661223 |
| Todas: 138 parcelas, 690 OOF | Media | 0.319250 | 0.489826 | 0.666382 |
| Todas: 138 parcelas, 690 OOF | Mediana | 0.309703 | 0.487196 | 0.669959 |

Principal: ΔMAE = −0.0079045252; ΔRMSE = −0.0019103483. Las cinco repeticiones favorecen a la mediana; 86 parcelas mejoran, 45 empeoran y cuatro empatan con tolerancia 1e-12. Sesgo principal: media +0.000338, mediana +0.038037 t/ha; la menor pérdida absoluta no elimina la tendencia a sobreestimar.

| Condición vigente | Resultado de mediana |
|---|---|
| ΔMAE ≤ −0.01 | No: −0.007905 |
| IC95 por celdas completamente negativo | No: [−0.016298, +0.005805] |
| Mejora en al menos 4/5 repeticiones | Sí: 5/5 |
| ΔRMSE ≤ +0.01 | Sí: −0.001910 |

Bootstrap principal: 5,000 remuestras, semilla 20261006, 22 celdas. La reproducción literal del PR23 usa 20,000 remuestras y da aproximadamente [−0.0163, +0.0057]. Es una resolución Monte Carlo distinta, no un error: no se cambia el presupuesto de 5,000 del protocolo ni se elige el intervalo más favorable.

### Escenario B y ponderación

En B/sin_respaldo hay 135 parcelas y 659 OOF: algunas parcelas tienen cuatro repeticiones elegibles y otras cinco. Por parcela, MAE media 0.363187 → mediana 0.347481; Δ = −0.015706, IC95 por celdas [−0.044325, +0.020661]. Por promedio de repeticiones, MAE 0.357867 → 0.339817. Las dos parejas son correctas para ponderaciones distintas; no se mezclan ni se usa B como otra puerta para promover. RMSE medio 0.521985 → 0.516424; R² medio 0.610963 → 0.619180.

## Sensibilidades y límites de la mejora

Sin las 24 parcelas con alertas, sólo en el resumen, la mejora principal baja a −0.004288 t/ha. El RMSE empeora +0.002445 y sólo tres de cinco repeticiones mejoran MAE. La sensibilidad conserva 111 parcelas/555 OOF; no se retiró a nadie de sus entrenamientos ni se usa ese subconjunto para elegir otro modelo.

Por municipio, ΔMAE A/sin_respaldo: Calpulalpan −0.020278, Chignahuapan −0.012283, Almoloya −0.005000, Cuautepec +0.006000, Singuilucan +0.027083 y Emiliano Zapata 0 (sólo tres etiquetas). No se arma un híbrido media/mediana según estas cifras: eso escogería reglas después de ver sus errores.

Como control adicional, al retirar cada celda una a una sólo del resumen, el ΔMAE queda entre −0.009971 y −0.002821: conserva signo negativo, pero sigue sin alcanzar el umbral. No es una nueva validación dejando celdas fuera del entrenamiento ni borra la incertidumbre del bootstrap.

## Problemas de la propuesta y correcciones necesarias

1. **Poblaciones mezcladas.** La sección 3 del documento atribuye su tabla a sin_respaldo, pero 0.319/0.310 y R² 0.666/0.670 son de todas. Se resuelve etiquetando cada población y usando 0.320490/0.312585 para la decisión. Sus resultados computados reproducen; el problema está en la presentación.
2. **Porcentaje de remuestras interpretado como probabilidad real.** El 90 % por celdas es la fracción de remuestras con ΔMAE negativo; no una probabilidad calibrada de ganar en las 59. El 80 % es el resultado de una simulación con errores conocidos, composición municipal fijada y un caso añadido con cero. No observa etiquetas de las 59 ni garantiza transferir la distribución de errores. El «peor caso +0.012» no es un límite de riesgo futuro. Mantener ambos como diagnósticos condicionados, sin usarlos para saltar la regla espacial.
3. **Wilcoxon no reemplaza el IC espacial.** El script reporta p≈0.012 en A, calculado sobre diferencias por parcela. Ese contraste no preserva automáticamente la dependencia espacial del protocolo. No constituye otra vía de aceptación ni contradice un intervalo por celdas que cruza cero.
4. **Teoría condicional frente a estimación muestral.** Bajo error absoluto, el objetivo óptimo es la mediana condicional de la distribución verdadera; eso no garantiza que una mediana municipal estimada con pocas etiquetas supere a una media fuera de muestra. La asimetría global tampoco demuestra la forma de cada municipio. Se corrige la justificación; no se declara una victoria matemática de este estimador.
5. **Decisión después de resultados.** Escribir una regla antes de una eventual respuesta de FIRA no la convierte en previa a los resultados ya vistos. T03 ya admite la mediana y fija cómo compararla. Adoptarla pese a fallar dos condiciones sería una excepción metodológica explícita, no el cumplimiento del protocolo ni un desempate por simplicidad. Esta revisión no hace esa excepción.
6. **Ruta de reproducción.** El comando del PR usa registro/t08; las OOF compartidas están en registro/t03. Se reprodujo el script sin modificarlo pasando esa ruta correcta. Conviene corregir el ejemplo para evitar pedir regeneraciones innecesarias.
7. **Referencia versus modelo final.** Aún no existe una decisión T16 congelada. La media es la referencia vigente. Si se cambia sólo la referencia simple, se usa su implementación comprobada; si se cambia la base de una corrección residual, hay que volver a diseñar/verificar y ajustar esa corrección. No se sustituye el número municipal en predicciones antiguas dejando los coeficientes anteriores.

## Qué sabemos realmente de la métrica de FIRA

Las [bases oficiales, criterios de evaluación](https://www.fira.gob.mx/Nd/Reto%20Agrocebada%20Bases.pdf) enumeran RMSE, MAE, r² u otras métricas del Comité, sin fijar MAE exclusivo. El documento de la segunda sesión del 9-oct recibido por Dani contiene 14 preguntas y no confirma esa elección. Su transcripción de la reunión recoge que el equipo decide la métrica; es un indicio para justificar la selección interna, no una confirmación escrita de que la calificación reservada usará sólo MAE.

Se puede seguir trabajando con MAE primario y RMSE de control, como ya se acordó, sin detenerse esperando preguntas nuevas. No se atribuye a FIRA una confirmación ausente. La regla condicional del PR23 requiere reescritura: debe reconocer la evidencia actual y el momento de la decisión, no presentar la espera como una garantía de imparcialidad ni prescribir mediana automáticamente. Las huellas del documento recibido y de la transcripción se guardan en fuentes_verificadas.json; no se publican los originales.

## Recomendación operativa para T16

- Conservar la media como referencia y la mediana como alternativa auditada que mejora puntualmente, sin aceptación automática. Informar ambas con poblaciones e incertidumbre correctas.
- Continuar E1/Q sobre su comparador S y referencia media fijados; no cambiar su base según el resultado de esta revisión.
- Antes de congelar T16, declarar la función de pérdida y aplicar el criterio vigente. Una excepción a T03 necesita acuerdo explícito y explicación del cambio posterior a resultados; confirmar MAE no demuestra por sí mismo que esta mediana muestral sea mejor.
- La mediana no queda descartada para cualquier decisión práctica: su menor MAE puntual y su simplicidad son argumentos a favor, y una decisión bajo pérdida esperada no exige por principio un p<0.05. Aquí existe además una regla de selección ya acordada que no cumple. Elegirla por una excepción sería una decisión distinta, con incertidumbre y cambio declarados, sin denominarla mejora confirmada ni esconder su resultado en sin24. No se toma esa decisión en esta revisión.
- No ampliar ahora la búsqueda por municipio, mezclar referencias ni reutilizar las OOF como si acreditaran otra campaña. La selección final y el ajuste/exportación de las 59 siguen separados.

## Mensaje preparado para Migue

Migue, revisé el PR23 y reproduje tu script en Mac; también hice una reconstrucción independiente en el Docker común. Las referencias y los cálculos coinciden. En la población principal, media → mediana da MAE 0.320490 → 0.312585, RMSE 0.492593 → 0.490683 y R² 0.658577 → 0.661223. Sí hay una mejora puntual, pero el IC por celdas cruza cero y no llega al umbral de 0.01, así que por ahora conservamos la media como referencia. Antes de aceptar el documento, corregiría la tabla marcada sin_respaldo que contiene cifras de todas, la interpretación del 80/90 % como probabilidades reales de ganar y el comando que apunta a registro/t08 en vez de registro/t03. También aclararía que decidir antes de una respuesta de FIRA no borra que ya vimos los resultados. Las bases no fijan MAE exclusivo; podemos justificar nuestro MAE interno sin afirmar una confirmación de FIRA. Dejé ambos conjuntos, las sensibilidades y el dictamen completos para revisarlos. No cambié tu rama ni los resultados históricos.

Mensaje preparado, no enviado. No se adopta una excepción a T03 por escribirlo.

## Evidencia y reproducción

[Tablas y procedencia](../registro/t16_revision_mediana/README.md). [Verificador independiente](../scripts/t16_revisar_mediana.py), 12 controles de software en Mac normal/optimizado y Docker Linux/amd64 optimizado. Los siete CSV y el manifiesto son idénticos por bytes entre Mac y Docker; los resultados T15 y sus fuentes computacionales conservan sus huellas. Docker se detiene al terminar.

La reproducción literal del script de Migue terminó completa en Mac, incluida su simulación exploratoria de 20,000 remuestras con composición de 59. En Docker, su salida A/bootstrap coincidió; se detuvo expresamente la repetición de esa simulación después de más de 16 minutos, una vez completadas todas las pruebas y la auditoría independiente decisiva en Linux/amd64. El proceso terminó con código137 por esa orden de detención; no se diagnostica un error numérico ni OOM por ese código. Se declara como reproducción literal parcial en Docker, no como aprobación integral de ese script en Linux. La simulación no interviene en la regla de promoción y su resultado80% no se usa como probabilidad real de ganar.

```bash
python -O -m unittest tests.test_t16_revisar_mediana
python -O scripts/t16_revisar_mediana.py --salida reports/t16_revision_mediana_nueva
```

El segundo comando reconstruye y audita referencias existentes; no llama a los estimadores T15 ni produce las 59. Usar un destino nuevo. No simula observaciones agrícolas; los remuestreos de incertidumbre reutilizan errores conocidos y los ejemplos de las pruebas sólo verifican software.

Apoyo de procedimiento: scikit-learn y pensamiento crítico científico. [Selección de función de pérdida, documentación oficial](https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics). Kassis, T.; Agarwal, V.; He, Y.; Patel, D.; Brueckner, A. M. (2026), [Scientific Agent Skills](https://arxiv.org/abs/2609.00065), versión actual v2 comprobada. Las skills apoyan la revisión; no certifican la mejora.
