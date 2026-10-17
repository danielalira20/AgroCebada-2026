# T15 E2 · evaluación completa INEGI

Problema: faltaba conectar INEGI al ejecutor común y evaluar su aporte conservando H3,
la selección interna y los criterios registrados. Solución: E2/E12/E2Q con fuentes
canónicas y selección anidada; comparadores previos reutilizados por identidad.

- `autorizacion_v1.json` añade la solicitud del 17 de octubre; no modifica el registro previo.
- `puerta_integracion_v1.json` y `previa/` conservan la integración comprobada ANTES de la corrida.
- `resultados/` conserva todos los artefactos originales y el manifiesto sin editar.
- Dos archivos JSONL se comprimen sin pérdida. El auditor los lee directamente;
  las huellas del manifiesto original se verifican sobre los bytes descomprimidos.
- Auditorías completas Mac/Linux independientes del productor y sklearn; controles
  adicionales de desgloses y H3 con scripts reproducibles en `comprobaciones/`.
- `decision_E2.json` aplica la regla registrada; no congela T16 ni genera el CSV de las 59.
- Informe detallado: `docs/t15_e2_evaluacion.md`. Métricas: distinguir A/B,
  todas/sin_respaldo y RMSE/R2 por repetición frente a igual peso por parcela.

Reauditar desde la raíz (salida nueva):

```bash
.venv/bin/python -O -m scripts.t15_e2_auditar_evaluacion --ejecucion registro/t15_e2_evaluacion/resultados --salida reports/e2_reauditoria_nueva.json
```

Las comprobaciones automatizadas no equivalen a una revisión humana externa.
Una campaña y disponibilidad histórica de estos bytes no acreditada: no garantía futura.
