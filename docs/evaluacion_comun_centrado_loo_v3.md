# Procedimiento común v3: residuo y centro sin la propia fila

Problema que resuelve: v2 aprende un residuo respecto a la referencia que excluye la propia fila, pero utiliza una desviación de entrada respecto a la media municipal que incluye esa fila. Son contrastes con escalas distintas, particularmente en municipios pequeños.

Solución que implementa: v3 calcula cada centro de entrenamiento con **los mismos IDs y el mismo respaldo** que la referencia residual sin esa fila. Escala global, log de área, imputación de pendiente e indicador continúan ajustándose exclusivamente en el entrenamiento del fit. En predicción, centros y referencia provienen del entrenamiento completo guardado. No se ajustan con validación ni reservadas.

## Estado y alcance

Diseño fijado antes de cálculos técnicos el 14oct2026. Implementación para revisión; no evaluación completa T15, selección de ganador, ajuste final de las 59 ni cambio de etiquetas. v1/v2 y T09/T10/T11/T13/T14 históricos permanecen identificados y sin sustitución. Las revisiones del PR21 sobre e152abb son comentarios con conformidad y observaciones para v2; la implementación v3 necesita revisión del nuevo commit.

## Definición verificable

Para cada i del entrenamiento, P_i contiene todos los otros IDs del municipio. Si no existen, los otros IDs del grupo de registro; si tampoco existen, todos los otros IDs del entrenamiento. Nunca contiene i, validación o reservadas. Si el entrenamiento contiene sólo una fila, una corrección LOO es indefinible y se rechaza; la referencia sola sí puede ajustarse.

Con Z calculada por transformaciones ajustadas en el entrenamiento:

- r_i = y_i − promedio de y_j para j en P_i.
- D_i = Z_i − promedio de Z_j para j en P_i.
- beta minimiza ||r − D beta||² + n·lambda·||beta||², sin intercepto.
- Predicción nueva = referencia municipal/grupo/global del entrenamiento + (Z_nueva − centro correspondiente del entrenamiento) beta.

Para n municipal ≥ 2, r_i = n/(n−1)(y_i−media_y_municipal), y D_i = n/(n−1)(Z_i−media_Z_municipal). La identidad explica la alineación; no se seleccionó comparando MAE externos. Ambas matrices suman cero por municipio en esos grupos. No se pretende que los residuos de singletons con respaldo sumen cero, ni se fuerza corrección media cero en validación.

**Caso que requiere cuidado adicional:** una fila única en su municipio tendrá durante fit el centro de grupo/global calculado sin ella, como su referencia residual. Durante predict, ese municipio sí existe en el entrenamiento completo y usa su centro municipal. La predicción de la misma fila de entrenamiento tiene corrección cero, pero su fila D de ajuste puede no ser cero. Esta diferencia es la consecuencia explícita de la referencia LOO y debe revisarse; no se elimina la fila ni se modifica n·lambda para ocultarla.

Las transformaciones de X no se reajustan por cada fila LOO: son operaciones no supervisadas aprendidas dentro del entrenamiento correspondiente. Excluir la propia etiqueta se aplica a la referencia residual; excluir la propia fila al centro se aplica a P_i. Dentro de cada división interna se vuelven a aprender todas las transformaciones y pools desde su propio entrenamiento.

## Conservación y barreras

- Fuentes, 197 IDs, 138 etiquetas/59 ausentes, particiones y referencia originales preservadas.
- Misma rejilla lambda y presupuesto de ocho procedimientos/60 opciones. La propuesta v3 sigue no ejecutable y requiere revisión y registro definitivo antes de T15.
- No cambia T03; Migue debe documentar la extensión de internas B por celda. Se registra la conformidad del antecedente sin afirmar que esa documentación ya cambió.
- Estado con fuente, conteos y IDs de cada centro sin fila, copia profunda, serialización y versión. Cambiar parámetros después del fit exige reajustar; un fit fallido invalida el estado.
- Reporte de selección con frecuencia de referencia sola por candidato/escenario, denominador y estado completo/parcial. Un bloque apagado no se presenta como bloque que ayuda.
- La incidencia T06 de AGC114, 98/99 días, sigue separada: corrección corresponde a Daf. Si una reproducción conservase los 8,668 valores compartidos no necesitaría reentrenar; si cambia una entrada usada, versionar y repetir sólo consumidores afectados.

## Verificación prevista

1. Contraste por eliminación explícita de filas, incluidos municipios de 0/1/2 ejemplos, grupo único, constantes, log e indicador de faltante.
2. Matriz independiente con NumPy/Fraction; no reconstruir la fórmula usando el mismo helper productor. Comparar transformación, pools, r, D, beta, fuentes y predicción; conservar tolerancias previas.
3. Controles técnicos con lambda fija 0.1 en los 50 contextos A/B y cinco bloques: 250 ajustes, sin MAE externo, selección de ganador o ajuste de las59.
4. Comprobaciones de selección interna y aislamiento de etiquetas/entradas externas, orden/lote, copia de estado, clone/joblib y fallos, incluidas guardias con Python -O.
5. Reproducción Mac y Docker Linux/amd64 común. Contar ajustes técnicos separados de búsquedas completas y detener Colima al finalizar.

## Fuentes

[PR21](https://github.com/danielalira20/AgroCebada-2026/pull/21), comentarios de Daf/Migue sobre e152abb consultados el 14oct2026; [T03](T03_protocolo_evaluacion.md); diseños y evidencia v1/v2 conservados en registro/evaluacion_comun. El inventario fase A distingue cambios de código, datos, documentos y revisión.

Apoyo metodológico: scikit-learn y scientific-critical-thinking. Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. [arXiv:2609.00065](https://arxiv.org/abs/2609.00065), [DOI](https://doi.org/10.48550/arXiv.2609.00065); registro vigente v2 consultado el14oct2026. No acredita mejora predictiva.
