# T15: ejecutor, reportes y cierre operativo con Dani

15 de octubre de 2026. Responsable humana: Dani; apoyo técnico: Codex. Esta instrucción sustituye para este lote la espera de revisión de compañeros: «ya no van a revisar por cuestión de tiempos, ya sólo lo haremos tú y yo». Autoriza actualizar PR21 y terminar/comprobar el ejecutor; no autoriza ejecutar ahora la evaluación completa. No se atribuye aprobación nueva a Daf, Migue o Jass.

## Problema que resuelve

El contrato ya fija datos, ocho comparaciones y reglas, pero faltaba coordinar selección interna, ajuste externo y reportes con una salida completa verificable. Un error podía dejar trazas en memoria y ninguna entrega reproducible. También faltaba adaptar el cierre al cambio de disponibilidad de revisores.

## Solución que implementa

`scripts/t15_ejecutar.py` ofrece tres modos separados. `scripts/t15_ejecutor_reportes.py` valida OOF completas y produce métricas, contrastes y desgloses. `scripts/t15_registro_operativo.py` valida el [registro operativo](../registro/t15_contrato/registro_operativo_v1.json), con huellas de código y la instrucción de Dani.

Se conserva el [contrato v1](t15_contrato_comparaciones.md) como antecedente de diseño; sus pendientes de revisión humana describen el cierre anterior. El nuevo registro sustituye esa espera sin modificar las fuentes, las ocho comparaciones, las 60 opciones ni los criterios. El cierre pasa a Dani/Codex y pierde la revisión independiente adicional de los compañeros; no se presenta como aprobación externa.

Las precisiones documentales observadas en PR22 quedan explícitas para T15: A estratifica municipio/otros con cuatro internas, B agrupa celdas CHIRPS, C no entra en esta evaluación y agruparía municipios; desempate a seis decimales → referencia sola → λ mayor → junio–octubre → nombre. No es necesario esperar PR22 para usar este registro. No se edita ni se declara fusionado ese PR ajeno.

## Modos

1. **verificar:** carga contrato/registro, valida huellas y reconstruye las 200 internas; cero modelos. Es el modo predeterminado.
2. **prueba:** un procedimiento del principal en un contexto externo; conserva selección, puntuaciones, trazas, estados y OOF parcial con nombre explícito. No produce contrastes ni una clasificación de modelos.
3. **completa:** recorre A/B, cinco repeticiones y cinco particiones, con los ocho procedimientos y referencia. Requiere además `--confirmar-evaluacion-completa`, código registrado sin cambios y una solicitud posterior de Dani. No se usa ese modo en este trabajo.

Desde la raíz del repo:

```bash
python -m scripts.t15_ejecutar --modo verificar --salida reports/t15_preflight_nuevo
python -m scripts.t15_ejecutar --modo prueba --procedimiento G --escenario A --repeticion 1 --particion 0 --salida reports/t15_prueba_G_A_nueva
python -m unittest tests.test_t15_ejecutor tests.test_t15_comparaciones tests.test_evaluacion_comun_centrado_loo
```

Elegir destinos nuevos: no se sobrescribe una evidencia existente. Dentro del repo sólo se permite salida en `reports/`, ignorado por Git. Las salidas fuera del repo deben ser carpetas locales nuevas. No se generan datos ficticios para evaluar modelos; las modificaciones y controles de las pruebas verifican software y se mantienen en memoria o temporales.

## Flujo y trazabilidad

- Cada selección recibe sólo etiquetas de su entrenamiento externo. Imputación, escala y centros se aprenden de cada entrenamiento interno, conservando la implementación v3. Las etiquetas externas se unen a la predicción cuando ya terminó el ajuste.
- Las trazas internas se escriben inmediatamente mediante un callback. Se pasa una copia para que la persistencia no modifique la selección. Las selecciones y estados externos también se escriben en cuanto están disponibles.
- Las trazas incluyen candidato, escenario, repetición, partición, etapa, IDs, soporte, respaldos, singleton, λ/α, magnitud de corrección, huella del estado y advertencias. Los estados externos contienen coeficientes y transformaciones, no un ajuste final sobre 138.
- Un fallo o advertencia detiene la selección. Se conserva el manifiesto fallido y lo escrito hasta ese momento; no se omite una opción ni se completa con una referencia para ocultarlo. No se implementa reanudación automática de entregas fallidas: se usa una carpeta nueva.
- El manifiesto identifica commit, huellas de fuentes/código/artefactos, entorno, tiempo, memoria del proceso cuando está disponible y número de ajustes realmente realizados. Windows local no dispone de `resource`; se informa memoria no disponible en ese caso. La comprobación real de esta entrega se hace en Mac y Docker Linux, no acredita Windows nativo.

## Entrega completa prevista

- `predicciones_oof.csv`: 12,420 filas, nueve procedimientos incluida referencia × 1,380 claves A/B. IDs, etiquetas, particiones, fuente y versiones verificadas. Ninguna de las 59 aparece.
- `selecciones.jsonl`: 400 selecciones externas, con todas las opciones internas puntuadas, incluida referencia sola.
- `trazas_ajustes.jsonl` y `estados_modelos.jsonl`: ajustes internos/externos y estados aprendidos. No se guardan sólo los ganadores internos.
- `metricas_resumen.csv` y `metricas_por_repeticion.csv`: 36 resúmenes y 180 filas por repetición. Todas/sin_respaldo y A/B explícitos.
- `contrastes.csv`: 72 filas de los 18 pares fijados. ΔMAE por parcela, ΔRMSE medio por repetición, IC95 por celdas y sensibilidad descriptiva por parcelas. Un contraste descriptivo nunca activa promoción aunque cumpla umbrales numéricos.
- `desgloses_calidad_y_sin24.csv`: municipio, grupo de registro, contorno, parcela angosta/pequeña, escalón de etiqueta, vecina etiquetada y sensibilidad sin las 24 con alerta. Esas columnas sólo intervienen después de predecir; no son predictores ni se retiran las 24 del entrenamiento.
- `frecuencia_referencia_sola.csv`: 16 filas, ocho candidatos × A/B, con denominadores y completitud.
- `informe.md`, `preflight.json` y `manifest.json`.

La salida de prueba tiene `oof_parcial_prueba.csv` y manifiesto `comprobacion_funcional_parcial`. El productor de reportes completos rechaza claves o candidatos faltantes antes de escribir tablas. No debe combinarse una prueba con otra como si constituyeran la evaluación completa.

## Métricas y límites

MAE/RMSE en t/ha; R² sin unidad. Para el resumen por ID se promedian errores de sus repeticiones, nunca se promedian predicciones antes de medir el error. Se informa también el promedio de métricas por repetición para compatibilidad con T03. En B las ponderaciones no son equivalentes. El R² de objetivo constante queda vacío, incluso cuando el decimal constante introduce redondeo en su media.

Sesgo, p90 del MAE por parcela y número de parcelas cuyo MAE supera 1 t/ha son diagnósticos; no se añaden como filtros para promover. Los IC por parcelas son descriptivos, la regla usa celdas. El informe no congela un ganador T16, calibra intervalos individuales ni acredita otra campaña. La elegibilidad final también requiere comprobar capacidad para predecir las 59; este ejecutor no las ajusta ni exporta.

Presupuesto conservado: hasta 12,000 Ridge internos y 400 externos. Las referencias internas se repiten por procedimiento para conservar trazabilidad simple; el manifiesto distingue referencia de Ridge. La referencia externa se calcula una vez por contexto. No se añaden SG, Q/E1, cuantílica, datos externos ni nuevas semillas por usar este ejecutor.

## Pruebas previstas y cierre

Se comprueban aislamiento de etiquetas externas, equivalencia con el selector v3, invariancia del callback, persistencia ante fallos, restricciones de modos/destinos, R² constante y métricas calculadas a mano. Los reportes integrales se prueban con controles numéricos de la referencia histórica en temporales; no son nuevos resultados de bloques. La prueba limitada real recorre un contexto sin ejecutar T15 completa. La evidencia final se registra en `registro/t15_contrato/verificacion_ejecutor.json` después de pasar las comprobaciones.

El [PR21](https://github.com/danielalira20/AgroCebada-2026/pull/21) reúne el complemento LOO, contrato y este ejecutor. La actualización está autorizada por Dani; no implica merge en `dev`. AGENTS.md, skills, originales y reportes locales permanecen fuera del lote publicado. Docker sólo se utiliza durante QA y se apaga al finalizar.

Apoyo de procedimiento: skills scikit-learn y scientific-critical-thinking, citadas en el contrato previo; [Scientific Agent Skills](https://arxiv.org/abs/2609.00065). Su uso no constituye evidencia de mejora de MAE.


## Resultado de esta entrega

Pasaron **64 pruebas en Mac y 64 en Docker común Linux/amd64 con Python -O**: 18 del ejecutor y 46 de contrato/v3. La prueba real adicional de S/B está limitada a repetición 1, partición 0. Se guardan 36 ajustes internos y dos externos (uno de referencia y uno seleccionado); no es una estimación del desempeño completo.

La comparación entre entornos verifica 11,575 elementos de selecciones, estados, trazas y predicciones. Diferencia numérica máxima 1.11e-15, dentro del límite 1e-12. Las huellas binarias de 33 estados difieren por redondeo; se contrastaron sus valores completos sin ampliar tolerancia. El preflight es idéntico por bytes. Una reconstrucción matricial separada reproduce las 34 predicciones S/B con diferencia máxima 8.88e-16.

Los reportes de software completan 12,420 claves, 400 selecciones, 36 resúmenes, 180 filas por repetición y 72 contrastes con controles históricos en temporales. Esa prueba no entrenó los ocho procedimientos ni generó un MAE nuevo de T15. Los CSV numéricos de esos controles no se publican como resultados.

Se integró dev 97a8906, que ya contenía T14. Los conflictos eran exclusivamente dos bitácoras: se conservaron nuestras filas y se añadieron D_T14_001 e IA_T14_001/002/003, sin renumerar ni cambiar su contenido. Código, tablas y documento T14 coinciden con dev. Las fuentes de T03/T07 y los estimadores comunes probados no cambian con esa integración. Tras integrar se comprueba otra vez el modo verificar, sin modelos. Docker quedó apagado.

El paquete está preparado para una solicitud posterior de evaluación completa. Este trabajo no la ejecuta ni fusiona PR21 en dev.
