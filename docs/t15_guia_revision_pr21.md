# T15 · guía de revisión del PR #21

14 de octubre de 2026. Responsable: Dani. Revisión de T15: Daf; revisión metodológica y protocolo: Migue.

## Problema que resuelve

Los comentarios del PR #21 se hicieron sobre `e152abb`, versión v2. La implementación posterior v3, el borrador B y la aplicabilidad descriptiva C necesitan una revisión propia. Una conformidad sobre el antecedente no acredita esos cambios nuevos.

## Solución que implementa

Esta actualización del [PR #21](https://github.com/danielalira20/AgroCebada-2026/pull/21), hacia `dev`, reúne la fase A verificada hasta `f703e6d` y B/C hasta `51334b2`, junto con esta guía. Conserva la conversación y los commits del antecedente. El commit exacto objeto de revisión es el HEAD que muestra GitHub; debe constar en la revisión.

La publicación permite revisar; no acepta el registro experimental, ejecuta T15 completo, congela T16 ni produce las 59 predicciones finales.

## Orden de lectura

| Parte | Documento | Código o evidencia principal |
|---|---|---|
| A: alinear referencia y centro sin la propia fila | [Método v3](evaluacion_comun_centrado_loo_v3.md), [informe A](t15_fase_a_coherencia.md) | [Implementación](../scripts/evaluacion_comun_centrado_loo.py), [auditor independiente](../scripts/evaluacion_comun_centrado_loo_auditar.py), [pruebas](../tests/test_evaluacion_comun_centrado_loo.py), [verificación](../registro/evaluacion_comun/verificacion_centrado_loo_v3.json) |
| B: cerrar qué comparar y con qué presupuesto | [Propuesta B](t15_fase_b_documental.md) | [Borrador estructurado](../registro/t15_plan/borrador_fase_b.json), [propuesta principal v3](../registro/evaluacion_comun/propuesta_t15_centrado_loo_v3.json) |
| C: soporte de las 59, sin nuevas predicciones | [Informe C](diagnostico_aplicabilidad59.md) | [Perfil por parcela](../registro/diagnostico/aplicabilidad59/perfil_59.csv), [diccionario](../registro/diagnostico/aplicabilidad59/diccionario.csv), [verificación](../registro/diagnostico/aplicabilidad59/verificacion.json), [auditor](../scripts/auditar_aplicabilidad59.py) |

## Qué necesito que revise Daf

- Que centros y residuos usan los mismos otros IDs durante cada entrenamiento; la predicción usa únicamente estadísticas guardadas del entrenamiento completo.
- Que el reporte de `referencia_sola` tiene denominador y estado completo/parcial, sin confundir apagar un bloque con demostrar aporte.
- El caso de municipio con una sola etiqueta: en ajuste usa respaldo grupo/global sin esa fila; en predicción, si el municipio está representado, utiliza su centro municipal del entrenamiento. No se presenta como variación intramunicipal observada.
- Las ocho comparaciones y 60 opciones principales, y las condiciones separadas de V20/E1/E2. Revisar el borrador no equivale a autorizar automáticamente todas sus extensiones.
- Que C describe cobertura y soporte, no confianza individual ni mejora predictiva. Los errores que desglosa son históricos de T08.

Para V20 falta recibir el script del análisis de alternativas y distinguir pares de parcelas. Esa extensión no bloquea T15 principal. La incidencia T06 AGC_114 de 98/99 días sigue separada; si cambia una entrada utilizada, versionaremos y repetiremos sólo los consumidores afectados.

## Qué necesito que revise Migue

- Compatibilidad de v3 con la referencia territorial, las poblaciones elegibles de A/B y la política de grupos pequeños, incluido el caso de una sola etiqueta.
- Confirmar/documentar en T03 las internas B por celda como extensión prospectiva ya acordada en el antecedente, sin reescribir evaluaciones históricas.
- Que B conserva ventanas, búsqueda, presupuesto y regla T03, y mantiene las extensiones como decisiones separadas.
- La unidad de agregación de C: en B algunos IDs tienen cuatro repeticiones elegibles y otros cinco. Promediar por ID, por registro o por repetición da cifras distintas con las mismas predicciones; no es una mejora nueva del modelo.

No pido aprobar un nuevo MAE, un modelo ganador ni las predicciones de las 59: esas entregas todavía no existen para v3.

## Procedencia de observaciones y análisis

Cada observación se limita al PR y commit indicados; no se traslada automáticamente al HEAD más reciente.

| Material | PR / versión examinada | Alcance |
|---|---|---|
| Comentarios de Daf y Migue que motivan esta actualización | [PR #21](https://github.com/danielalira20/AgroCebada-2026/pull/21), `e152abbc959796eccddbe9ded7e5645aa463342a` | Conformidad con observaciones sobre v2; nueva revisión v3 pendiente. [Daf](https://github.com/danielalira20/AgroCebada-2026/pull/21#pullrequestreview-5512774979), [Migue](https://github.com/danielalira20/AgroCebada-2026/pull/21#pullrequestreview-5519332634). |
| Corrección H3 de T09 integrada en la base | [PR #18](https://github.com/danielalira20/AgroCebada-2026/pull/18), `9e25f02822adeead73baefac0632102de47ef04d` | Antecedente integrado; no evaluación de la nueva v3 común. |
| Reproducción de T10 del informe del 13-oct | [PR #17](https://github.com/danielalira20/AgroCebada-2026/pull/17), `d92cb7005d540c4561ae8cde32c858f653a8507c` | Versión exacta reconstruida en [revisión T10/T11](revision_T10_T11_20261013.md); no adoptar su método como v3. |
| Reproducción de T11 del informe del 13-oct | [PR #15](https://github.com/danielalira20/AgroCebada-2026/pull/15), `a2dbc14bf73ecd549b79383c8f2cd0317a42d3bf` | Versión exacta reconstruida; se distingue de la aprobación humana de otro commit. |
| Observaciones preliminares de T14 en fase A | [PR #13](https://github.com/danielalira20/AgroCebada-2026/pull/13), `48907a7a3cfcb903d7182e24ffa7b855ced285ea` | El HEAD consultado al publicar es `4ea73cf0565b5416ee288093ce6b9a3bd3f9054d`. Las notas anteriores no acreditan una revisión de ese HEAD. |
| Inventario de T13 en fase A | [PR #20](https://github.com/danielalira20/AgroCebada-2026/pull/20), `d9a8031f3cf0e6fafa59e05d39d654efda20b695` | El HEAD consultado al publicar es `50e656bdea1087be9c408cd96885cb7115abaa0e`; requiere distinguir la versión examinada. |
| Análisis de alternativas de Daf | Archivo `analisis_alternativas.md`, recibido el 14-oct; sin PR identificado | SHA-256 `f98eb239c4a2e6c7dfa9f8e63efa45bff3fe1cf5da6b2e174ce832cc9109603c`. Resultados de vecinas pendientes de reproducir con su script. |

## Comprobaciones y estado de los registros

A: 91 pruebas focalizadas aprobadas en Mac y Docker Linux/amd64 con Python -O; contraste independiente de 250 ajustes técnicos. C: 28 pruebas en ambos entornos y auditor independiente de 297,889 comparaciones por entorno. Evidencias detalladas en los JSON enlazados. No son una evaluación completa ni nuevos ejemplos independientes.

Los informes y manifiestos anteriores conservan la fecha/estado de su producción local: campos como `publicado: false`, o frases que dicen que no hubo push en esa fase, son instantáneas históricas. Esta guía y GitHub identifican la entrega sometida ahora a revisión. Las propuestas continúan pendientes/no ejecutables hasta cerrar la revisión y registrar la aceptación correspondiente.

No cambian originales, etiquetas, T07 ni resultados históricos. Los detalles pesados permanecen locales; se comparten derivados compactos, contratos, diccionario y verificaciones.

Pruebas focalizadas desde la raíz en el entorno común, sin ejecutar la evaluación completa:

```text
python -m unittest tests.test_evaluacion_comun tests.test_evaluacion_comun_centrado tests.test_evaluacion_comun_centrado_loo tests.test_diagnostico_aplicabilidad59 tests.test_aplicabilidad_agregacion
```

Para reproducir C y su auditoría con destinos nuevos, seguir los comandos de [reproducción de C](diagnostico_aplicabilidad59.md#reproducción) y los lanzadores Docker del README. No hace falta iniciar una corrida T15 para revisar esta entrega.
