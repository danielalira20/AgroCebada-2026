# Procedimiento común para comparar bloques · comun-v1

Responsable: Dani. Revisión metodológica: Daf para T15; Migue para el protocolo T03 y cierre T16. Preparado localmente el 13 de octubre de 2026. **Todavía sin evaluación externa completa de este procedimiento ni ganador final.**

## Problema que resuelve

T09, T11 y T14 comparten datos y referencia, pero cambian simultáneamente atributos, métrica interna, regularización, intercepto y algunas particiones internas. Comparar sus resultados sirve para comparar procedimientos completos; no permite atribuir una diferencia sólo al clima o al satélite. También había distintos controles y formatos de entrega.

## Solución que implementa

Un diseño con huella propia, componentes comunes de referencia, corrección y selección, un verificador de datos/predicciones/registro y estadísticos emparejados compartidos. Cambiará únicamente el bloque explícitamente registrado de atributos en las futuras comparaciones T15. Las salidas históricas se conservan como resultados de sus procedimientos originales.

Fuentes: `registro/evaluacion_comun/procedimiento.json`. Huella **da633adf27c7f1cf2d7760dc2f190abe38d9a912f80a976717fc6213c48f76d3**. Base `dev` cb4580701b2bf28588e56ce3d73e64fbf2b6a738. Entradas aceptadas T02/T03/T07/T08 ancladas por su contenido; no se condiciona compatibilidad de datos a comentarios en sus scripts.

**Transparencia:** ya conocemos resultados de T09, T11 y T14. Esta armonización es posterior a ellos, aunque se registra antes de sus nuevas ejecuciones. No se describe como experimento ciego previo ni como validación con nuevas etiquetas. La selección repetida sobre las mismas 138 parcelas limita la interpretación de los resultados futuros. Las 59 siguen sin etiqueta y no se utilizan para diseñar umbrales o elegir parámetros.

## Políticas acordadas en esta propuesta

| Aspecto | Procedimiento común | Razón y límite |
|---|---|---|
| Unidad | Parcela 2025; 138 etiquetas, 59 objetivos vacíos | Mediciones y repeticiones no son nuevos ejemplos independientes. |
| Referencia | Media municipal → grupo → global de T08 | Misma base y mismos respaldos para todos los bloques. |
| Familia | Referencia + Ridge sobre residuos LOO, sin intercepto | Separa aportación de variables de una calibración constante no penalizada. Con coeficientes cero vuelve a la referencia. No garantiza que esta familia sea óptima. |
| Residuos | Cada referencia de entrenamiento excluye su propia parcela | Se recalcula también en cada entrenamiento interno. |
| Transformaciones | Mediana y escala aprendidas sólo con entrenamiento | No usan validación, las 59 ni estadísticas de los 197 para ajustarse. |
| Faltante admitido | Pendiente ausente por D020: mediana del entrenamiento + indicador fijo | Sólo los dos vacíos declarados de T07. Columna totalmente vacía en entrenamiento: error, sin inventar cero. |
| Área | Log natural del área declarada cuando el experimento la autorice | Positiva, transformación fija; no sustituir por área geodésica ni convertirla en producción confirmada. |
| Regularización | λ = 0.01, 0.1, 1, 10; α = n del entrenamiento × λ | Comparable entre tamaños de entrenamiento. No es un α universal ni una garantía de óptimo global. |
| Ventanas | abr_oct y jun_oct como opciones internas | No se fija una por resultados externos. Si se mezclan bloques temporales, usan una misma ventana en cada opción. Otra combinación temporal requiere experimento explícito. |
| Internas A | Cuatro estratificadas por municipio u otros, semilla 0 | Igual política de T03; orden estable por ID. Estrato insuficiente: detener, no silenciar. |
| Internas B | Cuatro agrupadas por celda CHIRPS | La búsqueda respeta el escenario espacial. Extensión explícita a T03, propuesta para revisión Migue. |
| Internas C | Cuatro agrupadas por municipio | Sólo diagnóstico de transferencia territorial; no decide el ganador para las 59. |
| Métrica interna | MAE concatenado sobre casos con municipio representado, en A/B | Se dirige al mismo soporte de la decisión externa; reporta también todas. En C se usan todas. |
| Opción simple | Referencia sola también participa en la selección interna | Permite decidir no corregir cuando las variables no ayudan dentro del entrenamiento. No asegura mejora externa. |
| Empates | MAE redondeado a 6 decimales; referencia, mayor λ, jun_oct, nombre | Regla estable; no elegir según el resultado externo. |
| Presupuesto | Hasta ocho procedimientos por experimento; ocho opciones con variables por procedimiento | Dos ventanas × cuatro λ, más referencia sin búsqueda. Estático: cuatro λ, no duplicar opciones. Ocho opciones temporales + referencia requieren 36 ajustes internos por contexto, más el ajuste elegido. No contar filas OOF como ajustes. |

La rejilla cubre tres órdenes de intensidad. Si el óptimo interno cae en un extremo se registra; **no se amplía automáticamente** después de conocer la evaluación externa. Una expansión o familia nueva necesita registro y presupuesto nuevos. No se incorpora una red ni filtros Pearson sólo porque aumenten el número de pruebas.

La opción de referencia interna y la ausencia de intercepto son decisiones nuevas explícitas. T11-v2.1 mantiene su diseño anterior correctamente registrado. La media LOO de los residuos no tiene por qué ser cero por los respaldos: añadir un intercepto residual puede calibrar todos los municipios aunque las variables tengan coeficientes casi cero. Ese posible beneficio merece otro contraste declarado, no confundirlo con señal del bloque ni quitarlo de los resultados históricos.

## Comparación externa

No cambia las particiones de T03 ni la regla principal: A; B obligatorio; `sin_respaldo` como población de decisión. Conservar también `todas`, ambos escenarios y los desgloses municipales, grupo, contorno, angosta, escalón y vecinos. Recalcular sensibilidad sin las 24 alertas sobre las OOF existentes, sin retirar esas parcelas del entrenamiento ni elegir por ella.

- Métricas: MAE, RMSE, sesgo y R² por repetición y promedio posterior; R² con objetivo constante queda indefinido, no infinito ni un valor forzado. Sus promedios no necesariamente ordenan igual.
- ΔMAE emparejado: promedio de las diferencias de error de cada parcela sobre sus repeticiones elegibles y después promedio de parcelas. El informe distingue la diferencia entre métricas promedio por repetición, que puede ser otra cifra en B.
- ΔRMSE y signo de mejora: por repetición, como T03/T08.
- IC95: 5,000 remuestreos de celdas CHIRPS, semilla 20261006, percentiles 2.5/97.5. Cada bloque incluye todas sus parcelas y pesa según su número de parcelas. Ninguna celda vacía/ausente puede perderse silenciosamente.
- Promoción: ΔMAE ≤ −0.01; límite superior IC95 <0; mejora en ≥4/5 repeticiones; ΔRMSE ≤0.01. Sólo A/sin_respaldo puede acreditarse como promoción principal. T16 exige además revisión, disponibilidad finita para las 59 y decisión documentada.
- Un intervalo en estas parcelas no garantiza el desempeño de las 59 ni otra campaña. No se ofrece incertidumbre individual calibrada a partir de estos intervalos de diferencia entre procedimientos.

## Qué bloques se pueden registrar

Clima de T04/T07; relieve/área de T05/T07 y T10; Sentinel-2 y Planet compactos de T06/T07. Calidad de observación sólo si se declara explícitamente, para separarla de señal espectral. Contornos, escalón de etiqueta y vecinos del catálogo completo son auditoría, no predictoras automáticas. Grupo de registro se usa para referencia/desglose, no se interpreta como variedad.

**No se eligió aquí la combinación ganadora, el sensor ni una lista de ocho combinaciones basada en sus errores.** Después de revisar T10, T15/Dani–Daf registrará un conjunto pequeño de hipótesis y comparaciones de inclusión/exclusión de bloques, con iguales casos, familia y búsqueda. Si más de ocho procedimientos son necesarios, se debe explicar y registrar otro experimento; no ampliar de forma encubierta el presupuesto. Para combinaciones con varios bloques temporales la primera búsqueda usa una ventana compartida. Ventanas independientes multiplicarían la búsqueda y requieren otro diseño.

T12 conserva su contraste no lineal como procedimiento distinto. T13/T14 pueden aportar hipótesis y límites, sin convertir importancia o correlación en selección automática ni agregar todas sus variantes a T15.

## Verificador y componentes

- `scripts/evaluacion_comun_contrato.py`: huellas y universo, roles, objetivos, claves, semillas/folds, celdas, metadatos, finitud, calidad D020, OOF y presupuesto del registro. Sólo valida: no corrige ni entrena.
- `scripts/evaluacion_comun_modelo.py`: referencia, residuos LOO, transformaciones, Ridge, divisiones internas, desempates y selección. `seleccionar_registrado()` valida el registro y obtiene entrenamiento/evaluación del contexto congelado, sin entregar objetivos externos ni los de las 59 al ajuste.
- `scripts/evaluacion_comun_reportes.py`: métricas y contraste emparejado desde OOF validadas. No declara ganador T16.
- `tests/test_evaluacion_comun.py`: casos reales y cálculos unitarios aislados. Los datos de ejemplo de pruebas no se escriben como una tabla oficial ni se usan en la evaluación del reto.

La comprobación de OOF verifica **integridad de filas, etiquetas, respaldos, particiones y referencia**. No puede demostrar, sólo mirando predicciones, cómo se entrenó un programa externo. Por eso declara `metodo_comun_acreditado=false`: un histórico correcto no pasa a ser una ejecución del nuevo procedimiento. Para acreditarlo habrá que guardar diseño, registro, versión de código, entorno, selección interna y estados de cada ajuste, y revisar la ejecución. El estado del modelo común incluye medias municipales/grupo/global, columnas, coeficientes, escala, mediana, α, λ e IDs de entrenamiento.

## Cómo utilizarlo

Desde la raíz del repositorio:

```bash
python -m scripts.evaluacion_comun_contrato
python -m scripts.evaluacion_comun_contrato --oof registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv
python -m unittest tests.test_evaluacion_comun -v
```

`--oof` puede repetirse para entregas A/B con el formato T03. C y archivos que mezclen ventanas/fuentes/procedimientos sin identificadores únicos deben separarse mediante un adaptador explícito; el verificador no elimina filas en silencio. El esquema de registro se explica en [registro de experimentos](evaluacion_comun_registro.md). No hay ejecutor completo ni CLI para generar la entrega final de las 59 en este paquete.

La huella del diseño y las huellas de datos deben coincidir en todos los equipos. La ruta local no participa en la identidad. Un cambio de datos exige nueva revisión; un comentario en el script de otro frente no invalida por sí solo la identidad de los datos.

## Validación de esta entrega

**Cierre comprobado:** 294 pruebas completas en Mac, 41 específicas en Docker y 41 con Python optimizado. Dos comprobaciones técnicas Docker son idénticas por bytes; Mac/Docker difieren como máximo 4.44e-16. Los cinco controles con matrices independientes difieren como máximo 8.88e-16 t/ha. No se ejecutó evaluación externa completa ni se generaron predicciones finales de las 59.

La evidencia completa queda local en `reports/evaluacion_comun_20261013/`. Se verifican las fuentes originales y los commits de T09, sin mezclar su PR18 con esta rama. Pruebas de rechazo incluyen referencia alterada, ID duplicado entre folds, reservadas con objetivo, celda inválida y predicción infinita; siguen activas con Python optimizado. Los 50 entrenamientos externos reales admiten las cuatro divisiones internas comunes, sin el aviso de estrato insuficiente de las internas municipales B.

Se comprueba matemáticamente un contexto real y cinco grupos de atributos (clima, S2, Planet, relieve/área y su combinación) con parámetros fijos. Son controles técnicos frente a mínimos cuadrados independientes, sin medir error externo ni elegir bloques ganadores. No es una evaluación completa nueva.

## Responsabilidades y siguientes hitos

1. Dani deja el diseño, núcleo y controles listos en `t15-procedimiento-comun`; publicación únicamente con autorización de su lote.
2. Daf revisa T15 y las definiciones satelitales; Migue revisa extensión de internas B, criterio común y presupuesto en T03/T16. Jass verifica compatibilidad de T10/relieve. Es coordinación documentada; no se enviaron mensajes automáticamente.
3. Terminar la revisión T10 y actualizar las comprobaciones de la corrección T11; mantener T14 y T09 con sus pendientes. Esta propuesta no los fusiona ni los marca aceptados.
4. Registrar combinaciones, ejecutar con el entorno Docker común, reproducir y guardar todas las selecciones y estados. Si no se cumplen condiciones, mantener referencia sola; no extender búsquedas para forzar mejora.
5. T16 congela; T18 ajusta con 138 y entrega 59 finitas; T17 y T19 consumen la misma identidad y límites. Datos externos o pronóstico para otra campaña necesitan hipótesis, disponibilidad y etiquetas futuras para validarse.

## Referencias

[Validación cruzada, scikit-learn](https://scikit-learn.org/stable/modules/cross_validation.html), [prevención de filtraciones](https://scikit-learn.org/stable/common_pitfalls.html), [Ridge y su objetivo](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html). Estas fuentes sustentan la separación entrenamiento/selección/evaluación, transformaciones dentro de folds y comportamiento de la penalización; no determinan un λ óptimo para Agrocebada.

Skills utilizadas: scikit-learn y pensamiento crítico científico. Atribución: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. [DOI](https://doi.org/10.48550/arXiv.2609.00065), registro actual v2 consultado el 13-oct-2026. No constituyen evidencia de mejora del rendimiento.
