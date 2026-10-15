# Revisión del PR #22 · extensión de T03 y notas de T14

15 de octubre de 2026. Revisión: Dani. PR [#22](https://github.com/danielalira20/AgroCebada-2026/pull/22), commit examinado `f73f376d81210b7b78e97532759d54b309f7a02f`, base `dev@97a8906b243b63f1e7c24ec85f7050642d9a98f5`. Contraste de implementación con PR #21 `4afabf081a341f3321fcd58a211d18b43ee5a3b4`. No se modificó la rama de Migue, no se fusionó ni publicó una revisión en GitHub.

## Dictamen y alcance

La extensión de B por celdas y el uso de MAE concatenado en casos con referencia municipal son compatibles con el procedimiento común v3. Las cifras estructurales reproducidas coinciden. **Pediría dos precisiones de texto antes de integrar:** la regla de C y el desempate completo. No encontré en este diff un cambio de cálculos predictivos: modifica cuatro archivos de documentación/bitácoras, sin scripts ni tablas de resultados.

Esta revisión no vuelve a ajustar T08–T14, no ejecuta T15 ni genera predicciones. Comprobar particiones no acredita los nuevos ΔMAE/IC de la verificación externa citada por Migue.

## Observaciones para Migue

### 1. Alinear la descripción de C · P2

En `docs/T03_protocolo_evaluacion.md`, línea 130 añadida, se agrupan A y C como internas estratificadas con `otros` y semilla 0. El contrato v3 (`seleccion.C`) y `scripts/evaluacion_comun_modelo.py:133–148` usan **GroupKFold por municipio para C**, sin barajar; sólo A usa la estratificación indicada.

Consecuencia: quien implemente C siguiendo ese texto obtiene otro procedimiento. No afecta al T15 principal actual, que sólo evalúa A/B, pero sí a una reproducción o comparación posterior de C.

Redacción sugerida: «A mantiene internas estratificadas por municipio/otros, semilla 0. C no forma parte del T15 principal; el diagnóstico C del procedimiento común usa GroupKFold por municipio. La extensión de B no modifica resultados históricos de C». Si se pretende otro alcance de C, nombrar la versión explícitamente en vez de presentar ambas reglas como equivalentes.

### 2. Expresar el desempate completo · P2

La línea 129 dice que gana el α mayor. `clave_opcion` y el contrato v3 definen antes la prioridad de **referencia sola** y después los desempates de ventana/nombre: MAE redondeado a seis decimales → referencia sola → mayor λ → junio–octubre → nombre de opción. Dentro del mismo entrenamiento, mayor λ equivale a mayor α porque α=n·λ.

Consecuencia: otro ejecutor podría elegir una corrección que no aporta frente a la referencia en un empate, o resolver de forma distinta dos ventanas. El código actual está bien; falta reflejarlo en el protocolo.

Redacción sugerida: «Se usa el desempate del procedimiento común v3: MAE interno redondeado a seis decimales; a igualdad, referencia sola; entre opciones con variables, mayor λ, después junio–octubre y nombre estable de opción».

## Cifras comprobadas

Se reconstruyeron los 50 entrenamientos externos A/B y sus cuatro particiones internas; para el contraste histórico de B se construyeron además las internas estratificadas con la misma regla y semilla. No se ajustó ningún estimador. Los conteos siguientes son **apariciones parcela/validación**, dependientes y repartidas entre los entrenamientos, no 2,760 parcelas distintas.

| Escenario y regla interna | Particiones internas inspeccionadas | Registros de validación | Sin referencia municipal | Con una sola referencia municipal |
|---|---:|---:|---:|---:|
| A, común v3 estratificada |100|2,760|60|30|
| B, común v3 por celda |100|2,760|206|360|
| B, contraste estratificado |100|2,760|72|28|

Todas las internas B comunes conservan las celdas separadas entre entrenamiento y validación. En cada contexto cada ID se valida exactamente una vez. Se comprobó también que C común deja municipios enteros fuera. El agrupamiento respeta la finalidad de [GroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html); no supone por sí mismo independencia geográfica perfecta.

Se consultaron únicamente las predicciones históricas existentes para verificar:

- A/sin_respaldo: 135 parcelas, 675 registros, MAE 0.320489710387 tanto por parcela como por registro.
- B/sin_respaldo: 135 parcelas, 659 registros; 119 con cinco repeticiones y 16 con cuatro. MAE por parcela 0.363187374908; por registro 0.358432042728. Son dos ponderaciones de los mismos resultados, no una mejora.
- Referencia municipal con una sola etiqueta en la evaluación externa: 0 casos en A y 34 en B. MAE histórico de esos 34: 0.197352941176.
- AGC_120: referencia **ya publicada** de 2.5 t/ha; su única etiqueta municipal es AGC_048. La cifra de 1.9 km es coherente si se refiere a **orillas** (1,882.994 m, diagnóstico C previo). Entre centroides son 2,598.138 m. No se detectó una contradicción: hay que distinguir ambas distancias.

## Requisitos y límites que quedan explícitos

- **Trazas del punto 5, línea 131:** el selector común guarda totales elegibles y de validación, pero aún no emite automáticamente todos los campos nuevos por partición (`internas` y referencia única). Este requisito lo tenemos que cubrir en el corredor T15 antes de la evaluación completa. La tabla de esta revisión muestra que los conteos se pueden obtener; no se afirma que ya estén incorporados en el selector. No exige recalcular modelos históricos ni cambiar los cálculos de Migue.
- **Evidencia externa:** el script `entregas/revisiones/verificar_t15_v3.py` del repositorio `nova-cz/agrocebada` devuelve HTTP 404 con el acceso actual. No se pudo inspeccionar ni ejecutar. Los ΔMAE, IC y cambios de α de la línea 136 y la nota T14 quedan **atribuidos a la revisión de Migue**, no reproducidos aquí. Sería conveniente compartir una tabla compacta, comando y versión de esa comprobación. El grid de T14 (`[0.1,1,10,100,1000,10000]`) es distinto del menú T15 α=n·λ: esa nota no acredita homogeneidad completa de ambos procedimientos.
- **Exploración previa:** la cartera principal ya estaba definida en PR21 antes de recibir estas cifras de B. Conservar esa versión; no elegir nuevas variantes o parámetros por los nuevos resultados externos. Las extensiones posteriores conservan su carácter exploratorio y registro separado.
- **Bitácoras:** D026 e IA_T03_001/IA_T14_004/IA_T14_005 son entradas nuevas, sin colisiones nuevas y sin modificar filas anteriores. `IA_T07_012` ya estaba duplicada en la base `dev`; no lo introduce PR22. Su conciliación está en PR21: conservar una sola entrada idéntica al integrar, sin abrir otra renumeración ni eliminar registros distintos.

## Entrega y reproducción

[Verificación y fuentes](../registro/revisiones/pr22/verificacion.json), [particiones inspeccionadas](../registro/revisiones/pr22/particiones_internas.csv) y [conciliación de bitácoras](../registro/revisiones/pr22/bitacoras.json) y [fuentes documentales examinadas](../registro/revisiones/pr22/fuentes_documentales.json). El script de revisión es propio, de lectura, y no llama a `fit` de un estimador:

```text
python -O -m scripts.revisar_pr22_particiones --salida reports/revision_pr22_nueva
```

El destino debe ser nuevo. La revisión se realiza desde la rama que contiene el procedimiento común del PR21; ejecutar el script desde una rama que no contenga ese código no es una comprobación equivalente. PR22 continúa abierto y pendiente de decisión humana.

Apoyo de análisis: skills privadas EDA y pensamiento crítico científico, con sus límites de unidades, dependencia y alcance. Referencia: Kassis, T., Agarwal, V., He, Y., Patel, D. y Brueckner, A. M. (2026), *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, arXiv, versión consultada v2, [DOI](https://doi.org/10.48550/arXiv.2609.00065). Esta atribución no valida empíricamente nuestro método.
