# T10 → T17: entradas fuera del rango de entrenamiento

- **Fecha:** 12 de octubre de 2026. Atiende el comentario 8 del PR T10.
- **Estado:** pendiente de implementación y revisión en T17. Esta ficha no implementa avisos ni modifica predicciones.
- **Evidencia:** `registro/t10/diagnostico_atributos_t10.csv` y §3 del método T10. Comparación de las 59 reservadas con las 138 etiquetadas.

## Casos observados

| Parcela | Variable | Valor reservado | Límite etiquetado rebasado | Distancia al límite |
|---|---|---:|---:|---:|
| AGC_088 | Elevación | 2,906.0 m | Máximo: 2,904.0 m | 2.0 m por encima |
| AGC_153 | Pendiente | 0.282° | Mínimo: 0.288° | 0.006° por debajo |
| AGC_091 | Área declarada | 0.35 ha | Mínimo: 0.38 ha | 0.03 ha por debajo |

Los valores están redondeados para presentación; el detector debe comparar los valores originales sin redondear. T10 usa el logaritmo del área; para áreas positivas, el orden y la condición de estar fuera del rango coinciden en ambas escalas.

## Alcance y decisiones pendientes

El ajuste final de T10 elige «referencia sola» en las seis configuraciones: elevación, pendiente y área no intervienen en esas predicciones. La distancia al rango, por sí sola, no demuestra seguridad ni error predictivo de otro modelo. Se retira como conclusión vigente la frase histórica «No es una extrapolación relevante» de la bitácora.

En T17, el equipo debe definir y revisar qué hacer cuando una variable utilizada por el modelo desplegado esté fuera de rango: avisar y predecir, recurrir a una referencia o rechazar la entrada. Esta ficha no elige esa política. No recortar valores, sustituirlos por límites ni cambiar el modelo automáticamente sin una decisión evaluada y registrada. Para variables que el modelo no usa, el aviso debe identificarse como información de los atributos, sin atribuirle un efecto sobre la predicción actual.

## Criterios de aceptación para T17

1. Guardar, junto con la versión del modelo y sus unidades, los mínimos y máximos calculados sólo con su entrenamiento; no ampliar los límites con las entradas a predecir. En validación, usar el entrenamiento de cada partición.
2. Detectar valores estrictamente menores que el mínimo o mayores que el máximo; los valores iguales al límite están dentro. Comparar antes del redondeo de presentación.
3. Identificar parcela, variable, valor, rango y versión de referencia. Distinguir variables utilizadas por el modelo de atributos informativos.
4. Con las 138 etiquetadas de T10 como referencia, recuperar los tres casos de la tabla. Probar además valores en el límite, dentro y fuera; tratar los faltantes mediante su validación específica, sin confundirlos con valores fuera de rango.
5. Verificar que habilitar el aviso informativo conserva las 59 predicciones actuales. Cualquier política futura que cambie una predicción requiere evaluación y registro propios.
6. Antes de cerrar T17, registrar la política seleccionada, la persona responsable y su revisión. Un control de rangos individuales no descarta combinaciones de variables nuevas ni garantiza precisión fuera del entrenamiento.
