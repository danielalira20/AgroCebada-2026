# T15 · resultados completos del 16 de octubre de 2026

[Informe e interpretación](../../docs/t15_resultados.md). Ninguno de los ocho procedimientos promociona en A/sin_respaldo. Se conserva la referencia; no hay ganador T16 ni predicciones finales de las 59.

## Contenido

| Archivo | Contenido |
|---|---|
| predicciones_oof.csv | 12,420 OOF: nueve procedimientos, 138 parcelas, cinco repeticiones y A/B. No son ejemplos independientes nuevos. |
| selecciones.jsonl | 400 selecciones con todas las opciones y puntuaciones internas, incluida referencia sola. |
| trazas_ajustes.jsonl.gz | Las 14,050 trazas completas: 13,600 internas y 450 externas. gzip sin pérdida. |
| estados_modelos.jsonl.gz | Los 450 estados externos, con transformaciones, centros y coeficientes. gzip sin pérdida. |
| metricas_resumen.csv / metricas_por_repeticion.csv | 36 resúmenes y 180 resultados por repetición; población y ponderación explícitas. |
| contrastes.csv | 72 contrastes; regla principal A/sin_respaldo e IC por celdas. |
| desgloses_calidad_y_sin24.csv | 756 desgloses; retirar 24 sólo del resumen, nunca del entrenamiento. |
| frecuencia_referencia_sola.csv | 16 frecuencias, cada una con 25 selecciones. |
| preflight.json / manifest.json / informe.md | Salidas originales intactas del ejecutor. El manifiesto conserva las huellas de los JSONL descomprimidos. |
| registro_inicio.json | Instantánea histórica: commit, autorización de ejecución y huellas de 821 archivos antes de la corrida. Su «sin push» describe ese momento. |
| auditoria_independiente.json | Dictamen original de 554,410 comprobaciones, sin importar el productor. No es revisión humana externa. |
| diseno_auditoria.json / ampliacion_auditoria_v2.json / correccion_auditoria_v3.json | Tolerancias y evolución declarada del auditor; no cambian resultados ni reglas. |
| verificacion_portable.json | Revisión posterior en Mac: 554,410 comprobaciones y guardias frente a alteración/sobrescritura. |
| entrega.json | Inventario y huellas del paquete publicado, compresión y adaptación portable del auditor. |

## Verificar sin volver a entrenar

Desde la raíz del repositorio, la comprobación de integridad sólo necesita Python y Git:

```bash
python scripts/t15_auditar_entrega.py --solo-integridad
```

La revisión numérica usa las dependencias fijadas del proyecto. Descomprime en lectura, reconstruye las 282 soluciones Ridge externas por álgebra, verifica selecciones, particiones, H3 y reportes. No llama al ejecutor ni a los estimadores del repo, no repite la búsqueda de parámetros ni sobrescribe el dictamen original:

```bash
python -O scripts/t15_auditar_entrega.py --salida reports/t15_revision_nueva/auditoria.json
```

Elegir una salida nueva. También puede ejecutarse en el Docker común con la misma raíz montada y una salida escribible siguiendo los lanzadores del README. La comprobación portable posterior a la publicación se distingue de la corrida y auditoría originales en Linux/amd64.

El auditor portable conserva literalmente los cálculos de la versión local registrada; adapta rutas, lectura gzip, procedencia y destino. Tiene una huella nueva, indicada en entrega.json. Las entradas computacionales actuales deben coincidir con la corrida. Las huellas históricas de documentación/bitácoras pueden diferir después de publicar: en ese caso se verifican contra el commit Git fijado, sin afirmar que sus bytes actuales sean los originales. Se necesita ese commit accesible; un clon superficial debe obtenerlo antes de auditar.

## Reproducir la evaluación original

Commit de ejecución: cc7d0ae5437490d63408d74b4a3693a7b4494d55. Método comun-centrado-loo-v3; fuentes y entorno exactos en manifest.json. Imagen usada: sha256:b2dea1bd162fb607dedb4e1a670edde239743db940d2868e2167f7414e8875aa; Linux/amd64, sin red, repo sólo lectura, 768 MiB, dos CPU y BLAS a un hilo. El identificador de imagen local no garantiza disponibilidad en otro equipo; Dockerfile y requirements.txt registran su construcción.

En ese commit y entorno, con una salida nueva y escribible, la invocación del módulo fue:

```bash
python -O -m scripts.t15_ejecutar --modo completa --confirmar-evaluacion-completa --salida /evidencia/ejecucion_docker
```

Ese comando sí repite entrenamientos; no es necesario para consultar o auditar los resultados compartidos. Las 821 huellas fijadas acreditan fuentes de esa corrida, no convierten cambios futuros en resultados de aquel commit.

## Interpretación

Principal A/sin_respaldo: 135 parcelas, 675 OOF por procedimiento. Referencia MAE 0.3204897104 t/ha; RMSE medio por repetición 0.4925930954; R² medio por repetición 0.6585767448. La mínima reducción puntual, GP −0.000300 t/ha, no alcanza la regla. B, sin24 e intervalos por parcelas son sensibilidades, no otras formas de elegir ganador.

El campo metodo_comun_acreditado=false del manifiesto original es un retorno fijo del validador genérico de CSV, que no acredita entrenamiento leyendo OOF. La evidencia del método está en código fijado, trazas, estados y auditoría; se conserva el manifiesto sin retocarlo.

SG, E1/Q, cuantílica y datos externos no se evaluaron aquí. Los estados son ajustes de validación cruzada, no un modelo final entrenado con las 138 ni una garantía para otro año. Los originales, rutas personales y bitácoras privadas quedan fuera del paquete.
