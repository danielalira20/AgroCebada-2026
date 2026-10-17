# E2 · modelo común y registro previo

Esta entrega acredita adaptación y comprobaciones técnicas, **no una evaluación
completa de aporte ni una mejora demostrada de MAE**. Informe:
`docs/t15_e2_modelo_h3.md`.

- `registro_ejecucion_v1.json`: fuentes, código, cartera E2/E12/E2Q, dos ventanas,
  cuatro λ, referencia sola, contrastes, presupuesto y reglas. Registro inmutable
  anterior a la evaluación de aporte; no autoriza esa evaluación.
- `previa_linux/`: comprobación canónica con 16 ajustes auditables del adaptador
  y sus consultas. λ=0.1 fijado para verificar, no seleccionado por desempeño.
  Sus predicciones no son entrega final ni modelo ajustado con todas las etiquetas.
- `auditoria_mac.json`, `auditoria_linux.json`: ecuaciones normales y conjuntos
  explícitos sin importar productor ni scikit-learn; heredan el auditor E1.
- `comparacion_entornos.json`: 71,421 controles, diferencias <1e-12.
- `pruebas_27_mac.log`, `regresion_49_mac.log`, `pruebas_76_linux.log`: pruebas finales.
- `negativos_registro.json`: alteraciones de fuentes, código, permiso y reglas rechazadas.
- `incidentes/`: intentos iniciales fallidos, conservados por transparencia. No se
  usan como evidencia aprobada. El informe explica la corrección del comparador
  de prueba y el rechazo de una auditoría iniciada antes del cierre previo.
- `entorno_*.json`: versiones y arquitecturas efectivas.
- `entrega.json`: huellas de todos estos archivos y del código.

Para recalcular la auditoría sobre esta entrega desde la raíz:

```bash
.venv/bin/python -m scripts.t15_e2_auditar_modelo --entrega registro/t15_e2_modelo/previa_linux --salida reports/e2_auditoria_entrega_nueva.json
```

La integración usa únicamente la tabla INEGI canónica conservada en
`registro/t15_e2_extraccion/atributos_parcela.csv`, por ID. No necesita reproyectar
el CEM ni requiere mantener Docker encendido para consultar los resultados.

Pendientes: conexión del ejecutor/reportes E2 con guardia familiar; comprobación
de esa conexión; solicitud de evaluación completa. Aplicabilidad final a las 59,
selección T16, ajuste final y CSV de entrega siguen fuera de esta etapa.
