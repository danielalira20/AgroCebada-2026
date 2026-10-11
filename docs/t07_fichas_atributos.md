# T07 · Fichas de atributos y preparación para otra campaña

Responsable: Dani. Revisora: Jass. Complemento del punto 1 de la pestaña
«Selección de atributos». Estado: preparado localmente para revisión.

## Problema que resuelve

La entrega T07 identifica qué significa cada columna, su unidad, función y
procedencia. Esa información está distribuida entre el diccionario, el contrato
y T04–T06. Tener una columna calculada para 2025 no demuestra que se pudiera
obtener antes de la predicción ni que se pueda conseguir para otra campaña.

## Solución que implementa

`registro/t07_fichas/` añade una ficha por cada una de las **60 columnas** de
`tabla_comun.csv`. Conserva literalmente los diez campos del diccionario original
y añade disponibilidad, dependencias temporales, requisitos futuros, tareas,
responsables y pendientes. Es documentación del contrato; no es una tabla nueva
de ejemplos ni una lista de atributos seleccionados.

La tabla mantiene 35 columnas con rol candidato, 18 de calidad, cinco metadatos,
un objetivo y una de referencia/evaluación. El área declarada sigue siendo un
metadato y una candidata explícita de T10. Calidad tiene usos experimentales
concretos en T11; no se prohíbe ni se incorpora automáticamente.

El complemento se genera **desde el diccionario y el contrato aceptados**, sin
copiar definiciones a mano. Tiene manifiesto propio y verifica las huellas de
la entrega original y de sus fuentes documentales. Así una aclaración no obliga
a repetir la extracción ni a cambiar la identidad del cálculo aceptado.

## Diferencias respecto a la entrega anterior

| Antes | Ahora |
|---|---|
| Definición, unidad, función, periodo, agregación y vacío en el diccionario. | Los mismos campos literales, más condiciones de uso y evidencia de disponibilidad. |
| Límites temporales dispersos entre T04, T06 y el contrato. | Fecha observada, periodo resumido, insumos necesarios y publicación separados por atributo. |
| Unidades LAI2/VI6T pendientes en una lista del contrato. | Cuatro fichas con estado pendiente y una aclaración asignada a T06 (Daf/Jass). |
| Requisitos de una campaña nueva implícitos. | Lista de datos, fechas, acceso, vigencia y controles que se necesitan por fuente. |
| Estado histórico «en revisión» dentro del manifiesto del cálculo. | Se conserva ese estado histórico y se documenta aparte la incorporación real por PR14. |

Las **13 piezas de `registro/t07/` permanecen idénticas**, al igual que los
originales y las fuentes T02–T06. No se modifican valores, etiquetas, ventanas,
reglas de calidad, particiones ni diseños de modelos. No se ejecuta el punto 2.

## Cómo leer las fichas

| Campos nuevos | Significado |
|---|---|
| `tarea_fuente`, `responsable_fuente`, `revisa_fuente` | Quién mantiene la fuente según el plan; Dani/Jass mantienen/revisan este complemento T07. |
| `frente_de_uso`, `condicion_de_uso` | Contexto previsto y límites; no equivalen a una selección aprobada por un modelo. |
| `unidad_estado` | `documentada` en el contrato vigente o `pendiente`; no se inventan escalas para completar la ficha. |
| `version_producto` | Lo que consta del producto; una huella identifica un archivo, no prueba su versión científica o publicación. |
| `periodo_resumen` | Ventana que describe el atributo. |
| `periodo_insumos_necesarios` | Serie/periodo necesario para reproducirlo; puede ser mayor que el resumen final. |
| `fecha_publicacion`, `disponibilidad_al_corte` | Primera publicación no documentada y uso operacional no acreditado. `No aplica como entrada predictiva` se reserva para ID/campaña/conjunto/objetivo. |
| `evidencia_disponibilidad`, `fuentes` | Referencias concretas que sustentan la afirmación o la ausencia de evidencia. |
| `soporte_espacial`, `control_calidad` | Escala, ponderación y archivo de calidad que debe consultarse. No se crea un umbral nuevo. |
| `requisitos_campania_futura`, `acceso_futuro` | Qué obtener/verificar antes de usar el procedimiento con datos nuevos; no garantizan desempeño. |
| `limite_interpretacion`, `aclaracion_faltante` | Precisiones complementarias; el significado original del diccionario sigue visible. |
| `pendientes` | IDs enlazados con `pendientes_documentales.csv`; cada asunto tiene tarea, responsable, revisor y efecto. |

Los campos documentales son explícitos, sin celdas vacías. «No documentada» no
equivale a «no existe»; «no acreditada» no significa «publicada después». Las
fichas no convierten una ausencia de evidencia en una fecha inventada.

## Hallazgos y cómo se atendieron

1. **El PR14 ya está integrado.** GitHub confirmó merge por `GangSonic` el
   2026-10-11 a las 02:59:01 UTC, commit
   `82c4aca9be4de64fae888066d81af1652ff651e1`, head integrado
   `b3882a96851ee0bec22b4b5042ccb01ee2b22041`, base `dev`.
   Es evidencia de incorporación, no una revisión independiente de estas fichas.
   El manifiesto de la ejecución original mantiene `cierre_t07=false`: el
   programa no deduce una aceptación humana. README y contrato distinguen ambos
   estados; no se reescribe el archivo histórico ni se fuerza ese indicador.
2. **Resumen final y datos necesarios no siempre coinciden.** En
   `scripts/t06_satelite.py`, `variables()` construye `ndvi_al_corte` sobre la curva
   `abr_oct` suavizada con mediana móvil centrada de tres capturas y después
   selecciona 17–31 de octubre. La primera captura seleccionada puede depender
   de una captura válida anterior al día 17. Las fichas de Planet y Sentinel-2
   declaran ambos periodos; no se cambia el cálculo ni se afirma uso posterior
   al corte. Esto evita reproducirlo erróneamente cargando sólo los últimos
   quince días. El suavizado sigue requiriendo recortar primero al corte.
3. **Vacío de elevación frente a pendiente.** El diccionario original usa una
   frase conjunta. `aclaracion_faltante` especifica que D020 (cobertura <0.5)
   afecta únicamente a la pendiente. Elevación conserva su regla original.
4. **Fechas/versiones desconocidas.** Clima y satélite no acreditan la publicación
   histórica de sus ediciones. Relieve tampoco tiene fecha de adquisición
   confirmada. Se conservan como pendientes verificables, sin excluir por ello
   columnas de la reconstrucción retrospectiva ni certificar uso en tiempo real.
5. **Interpretación del satélite.** La base previa al máximo es un estadístico
   de la curva; por sí sola no demuestra suelo desnudo ni fecha de siembra.
   LAI2 y VI6T mantienen sus cuatro unidades físicas pendientes. La nubosidad
   tampoco se convierte en fracción de superficie válida.

## Pendientes documentales y coordinación

Son ocho asuntos agrupados, no ocho errores nuevos del extractor. Algunos ya
estaban documentados; ahora quedan vinculados con todas las columnas afectadas.

| ID | Tarea / responsable / revisa | Qué falta sustentar |
|---|---|---|
| P01 | T04 / Dani / Jass | Versión/variante, publicación mensual exacta y acceso climático futuro. |
| P02 | T06 / Daf / Jass | Disponibilidad, procesamiento y acceso a series equivalentes de cada sensor. |
| P03 | T06 / Daf / Jass | Unidad física y escala exactas de LAI2/VI6T. |
| P04 | T06 / Daf / Jass | Definición de nubosidad, máscara y tratamiento de bordes. |
| P05 | T05 / Jass / Dani | Antigüedad/edición y acceso al relieve para el uso previsto. |
| P06 | T02 / Jass / Dani | Denominador/superficie, protocolo/humedad de etiqueta y grupo original. |
| P07 | T02 / Jass / Dani | Identidad, contornos y municipio disponibles en una campaña nueva. |
| P08 | T03 / Migue / Jass | Fecha objetivo y admisibilidad de entradas antes de un uso operacional. |

No se envían consultas a compañeros ni organizadores mediante este cambio.
Estas aclaraciones no bloquean por sí mismas documentar o preparar el diseño
retrospectivo de T09. Sí impiden prometer una predicción operacional validada
para otros años sin nueva evidencia.

## Reproducción y validación

Desde la raíz del repositorio, con Python estándar o `.venv`; Docker no hace falta:

```bash
python -m scripts.t07_fichas_atributos --generar reports/t07_fichas_reproduccion
python -m scripts.t07_fichas_atributos --verificar registro/t07_fichas
python -m unittest tests.test_t07_fichas_atributos -v
```

La salida de generación debe ser nueva. Se rechazan originales/entradas como
destino. `--verificar` regenera en memoria y compara los tres archivos completos:
una definición, fuente, rol, unidad o ficha alterada requiere revisión, no una
actualización silenciosa. Se conserva UTF-8 y fin de línea LF. El programa lee
la cabecera de la tabla común y huellas de archivos, no calcula estadísticas
con sus valores ni usa rendimientos para decidir nada.

Comprobación local del 11 de octubre: **253 pruebas aprobadas (13 nuevas)**,
dos generaciones idénticas de los tres archivos, 13 piezas de T07 intactas y
verificador original aprobado (1,182 contrastes climáticos, 1,182 del centroide
y 394 de relieve). Evidencia local: `reports/t07_fichas_atributos_20261011/`.

## Punto 2: propuesta posterior, todavía sin ejecutar

1. Acordar alcance y entradas del diagnóstico, manteniendo la población y roles.
2. Revisar faltantes, constantes, rangos y duplicaciones por bloque. Separar
   diagnóstico de calidad de exclusión de parcelas o atributos; no imputar aquí.
3. Preparar Pearson X–X y X–rendimiento, diagramas y tamaños de muestra, con
   revisión dentro de municipios cuando haya soporte. Si informan selección,
   computarlos sólo en el entrenamiento correspondiente. Las 59 sin etiqueta
   no se usan para optimizar umbrales, imputaciones ni selección.
4. Registrar hipótesis de redundancia sin borrar ventanas por coincidencias en
   2025, sin convertir correlación en causalidad ni aplicar umbral universal.
5. Integrar los diagnósticos en el diseño T09 con revisión de Migue; los
   subconjuntos climáticos y el presupuesto se coordinan con T14/T03.

La presente entrega no implementa ninguno de esos cinco pasos.

Referencias operativas: [Plan y selección de atributos](https://docs.google.com/document/d/1G2-cyDyIHyaQsGjbdzdvvsU65rnc6Tc4SrnIZAoNynk),
[PR14](https://github.com/danielalira20/AgroCebada-2026/pull/14),
[disponibilidad T04](t04_version_disponibilidad.md), [método T06](T06_satelite.md),
[método T05](t05_relieve.md) y [contrato T07](t07_contrato.md).
