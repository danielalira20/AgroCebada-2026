# E1/Q · entrega completa local

[Informe, resultados, incidencias y siguiente paso](../../docs/t15_e1_evaluacion.md). E1 no supera la regla principal; la referencia sigue vigente. No contiene un ajuste final con las 138 ni predicciones finales de las 59.

## Contenido

| Archivo | Contenido |
|---|---|
| registro_v1.json | Registro operativo antes de las nuevas OOF; autoriza Dani, sin atribuir revisión externa. |
| resultados/manifest.json | Manifiesto original de la corrida Linux, fuentes, entorno, presupuesto y huellas lógicas. |
| resultados/predicciones_oof.csv | 5,520 OOF: 2,760 nuevas Q/E1 y 2,760 S/referencia reutilizadas por huellas exactas. |
| resultados/predicciones_nuevas_incrementales.csv | Copia incremental original de las 2,760 OOF nuevas para recuperación. No son otro experimento. |
| resultados/selecciones.jsonl | 100 selecciones externas con puntuaciones y menú completo, incluida referencia sola. |
| resultados/trazas_ajustes.jsonl.gz | 3,700 trazas: 3,600 internas y 100 externas. Compresión sin pérdida. |
| resultados/estados_modelos.jsonl.gz | Los 100 estados externos: preparador, escalas, pools, centros y coeficientes cuando hay corrección. |
| resultados/metricas_resumen.csv / metricas_por_repeticion.csv | 16 resúmenes y 80 resultados por repetición, A/B y todas/sin_respaldo. |
| resultados/contrastes.csv | 16 contrastes: E1−referencia, E1−S, E1−Q y Q−S; IC espacial y regla. |
| resultados/desgloses_calidad_y_sin24.csv | 336 desgloses, sin retirar casos del entrenamiento. |
| resultados/frecuencia_referencia_sola.csv | Q y E1, A/B; cada fila corresponde a 25 selecciones. |
| resultados/informe.md | Resumen original del generador, conservado sin edición. |
| verificacion_previa.json | Puerta de ejecución: código, registro, pruebas y piloto verificados antes de la corrida completa. |
| auditoria_completa_mac.json / auditoria_completa_docker.json | Auditoría algebraica de la misma corrida: 132,490 comprobaciones por entorno. |
| auditoria_prueba_*_final.json | Auditoría del piloto previo; no se presenta como desempeño global. |
| tests_*_final.txt | Registros de las 115 pruebas por entorno; bytes originales de los logs, extensión de entrega .txt. |
| qa_ancla/ | 1,180 perturbaciones, resúmenes general/por retiro y manifiesto originales. |
| auditoria_QA_ancla_independiente.json | 12,234 controles desde raw, sin importar productor. Dictamen original local. |
| auditoria_QA_ancla_portable.json | Repetición con rutas explícitas, guardias activas con −O y huella del raw. Misma aritmética. |
| verificacion_paquete_mac.json / verificacion_paquete_docker.json | Auditoría posterior de esta entrega comprimida; no son otras corridas de entrenamiento. |
| guardias_paquete.json | Rechazo de OOF alterada, gzip corrupto y sobrescritura, sobre copias privadas con Python −O. |
| entrega.json | Inventario, huellas físicas/lógicas y procedencia de la compresión sin pérdida. |

El código, los originales y los datos comunes deben coincidir con las huellas. No editar el manifiesto original ni cambiar el contrato para saltar un fallo. Si otra rama modifica una fuente, revisar y registrar el cambio antes de adjudicarle estos resultados.

## Auditar sin volver a entrenar

Desde la raíz y con dependencias del proyecto, elegir una ruta de salida nueva cuyo directorio exista:

```bash
python -O scripts/t15_e1_auditar.py --ejecucion registro/t15_e1_evaluacion/resultados --salida reports/e1_revision_nueva.json
```

Reconstruye preparaciones y soluciones con NumPy/álgebra, sin importar el productor ni sklearn, y comprueba todas las selecciones, OOF y reportes. Lee gzip en memoria y verifica las huellas descomprimidas; no requiere descomprimir los archivos en el repositorio.

El ancla requiere además el CSV BASICO original local:

```bash
python -O scripts/t15_e1_auditar_ancla.py --qa registro/t15_e1_evaluacion/qa_ancla --salida reports/e1_ancla_revision_nueva.json
```

## Repetir la evaluación

Esto sí entrena. La corrida original usó commit `a32a59ff0616dda2f558393cc5af27b645bf2868`, Docker común Linux/amd64, sin red, 768 MiB y dos CPU. Mantener las fuentes fijadas y el original DataSet.zip identificado; el identificador local de la imagen no garantiza que exista en otro equipo. Dockerfile/requirements registran su construcción. Con el repo montado de sólo lectura en `/repo` y un destino nuevo escribible en `/evidencia`, el comando del módulo es:

```bash
python -O -m scripts.t15_e1_ejecutar --modo completa --confirmar-completa --verificacion /repo/registro/t15_e1_evaluacion/verificacion_previa.json --salida /evidencia/e1_reproduccion_nueva
```

Conservar `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1` y `MKL_NUM_THREADS=1`. Una fuente modificada debe detener el ejecutor. La verificación previa acredita las versiones concretas del código: no habilita una versión futura distinta. No se necesita repetir esta búsqueda para leer los CSV o auditar la entrega.
