# Revisión de mediana y cierre técnico T15/T12

[Dictamen media/mediana](../../docs/t16_revision_mediana.md) · [Estado de revisión T15/T12](../../docs/revision_t15_t12_cierre.md).

Se reproduce evidencia ya existente. La mediana no cumple promoción; no cambia T03/T15, no elige T16 ni exporta las 59. Las referencias se reconstruyen desde entrenamiento con fracciones exactas; las métricas usan OOF históricas intactas.

| Archivo | Contenido |
|---|---|
| diseno_revision.json | Alcance, exposición previa declarada, fuentes, reglas y tolerancia antes de producir tablas. |
| metricas.csv |16 filas: dos referencias × A/B × todas/sin_respaldo × completa/sin24. MAE por ID; RMSE y R² por repetición. |
| metricas_por_repeticion.csv |80 filas para conciliar agregaciones. |
| contrastes.csv |8 contrastes mediana−media; IC por celdas y condiciones de la regla, sin otra puerta de promoción. |
| por_municipio.csv |30 desgloses; municipios n<5 marcados como poco informativos. |
| diferencias_por_parcela.csv |546 perfiles de diferencia por ID/población/escenario, no nuevas etiquetas. |
| influencia_celdas.csv |22 retiradas de una celda sólo del resumen A/sin_respaldo; no nuevos entrenamientos. |
| contextos_verificados.csv |100 contextos de las dos referencias; IDs de entrenamiento y evaluación separados. |
| manifest.json |Huellas y alcance: 2,760 referencias, tolerancia1e-12, sin uso de etiquetas de reservadas. |
| comparacion_entornos.json |Pruebas Mac/Docker y concordancia exacta de tablas. |
| reproduccion_PR23_Mac.txt |Salida del script original sin modificar, pasando registro/t03 como ubicación correcta. |
| conciliacion_propuesta.json |Unión de tres bitácoras para PR21/PR24 fijados; propuesta no aplicada a otras ramas. |
| conciliacion_mediana_T12.json |Identidad de la referencia T08 leída por T12 y 192 valores cotejados; separación explícita del control mediana + corrección. |
| fuentes_verificadas.json |Versiones y fuentes públicas/recibidas; no se redistribuyen originales privados. |

`fraccion_remuestras_negativas_no_probabilidad_exito` describe las remuestras, no una probabilidad calibrada de acertar las 59. El p de Wilcoxon y la simulación del PR23 se conservan como diagnósticos; no sustituyen el intervalo espacial del protocolo.

Reproducción con las dependencias fijadas, desde la raíz y un destino nuevo:

```bash
python -O -m unittest tests.test_t16_revisar_mediana
python -O scripts/t16_revisar_mediana.py --salida reports/t16_revision_mediana_nueva
```

Los manifiestos del cálculo preceden a la escritura de esta documentación. Las comprobaciones de Docker usan Linux/amd64, sin red y repo de sólo lectura. Las fuentes y resultados previos no se sustituyen por estas tablas de auditoría.

La auditoría independiente completa y sus siete tablas se reprodujeron en ambos entornos. El script exploratorio original del PR23 terminó completo en Mac; su repetición literal en Docker quedó parcial por detención explícita del remuestreo largo redundante, tras coincidir la salida de A. Ver el alcance exacto en comparacion_entornos.json. No se presenta esa ejecución parcial como un error de cálculo ni como una validación completa de la simulación en Linux.
