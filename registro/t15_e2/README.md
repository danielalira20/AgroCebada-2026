# E2 · contrato técnico de INEGI

[Especificación completa](../../docs/t15_e2_contrato_inegi.md) y [alternativas con evidencia](../../docs/t15_e2_alternativas_fundamentadas.md). Estado: contrato local preparado para implementación. **No hay extracción E2, entrenamientos, nuevas OOF ni predicciones finales de las 59.**

| Archivo | Contenido |
|---|---|
| contrato_tecnico_v1.json | Fuente fijada, rejilla, fórmulas, cobertura, modelo, comparaciones, presupuesto, criterios y puertas falsas. |
| diccionario_propuesto.csv | ID, tres predictores futuros y doce columnas de QA separadas, con unidades y significado del vacío. No es una tabla de valores extraídos. |
| preflight_diseno.json | Rejilla planeada, pipeline, margen de 210 m comprobado y control de orientación contra desplazamientos geodésicos. No contiene un raster reproyectado ni atributos E2. |
| verificacion_diseno.json | 27 comprobaciones analíticas, diez modificaciones peligrosas rechazadas y 34 fuentes comunes verificadas; originales locales comprobados por huella. No acredita un productor E2 aún inexistente. |
| comparacion_verificaciones.json | Misma salida en Mac normal y −O. Docker no se inició para este trabajo de diseño. |
| fuentes_alternativas.json | Estudios primarios, alcance de lectura, limitaciones y PR20/23/24 identificados por versión. |
| manifest_contrato.json | Inventario de entrega y huellas; las puertas para ejecutar siguen pendientes. |

## Verificar este diseño

Desde la raíz, con una salida nueva:

```bash
python -O scripts/t15_e2_verificar_diseno.py --salida reports/t15_e2_revision_nueva.json
```

Con `--con-datos-locales` se verifican además el TIFF INEGI y los cinco archivos vectoriales ya disponibles en `data/raw/`. El modo de verificación no descarga datos, importa un modelo, reproyecta un raster, extrae valores de parcelas ni utiliza rendimientos. Las superficies matemáticas de prueba no son muestras sintéticas para entrenar.

Los predictores previstos son TPI150 y exposición Este/Norte ponderada por inclinación, antes de generar OOF. Los planos aportan vector (0,0) válido; los NoData permanecen ausentes. La fuente actual tiene límites de datum y disponibilidad histórica explícitos. El control E2Q y la guardia adicional de intervalos para dos candidatos están registrados, con sus costes; no son modificaciones retrospectivas de T15 o E1.

Siguiente paso: implementar extractor y auditor independiente, comprobar cobertura y fórmula en las 197, fijar el CSV canónico y probar el adaptador sin fugas. Después registrar códigos y entradas exactas antes de solicitar una evaluación completa. No se habilita entrenamiento cambiando el booleano de este contrato histórico.
