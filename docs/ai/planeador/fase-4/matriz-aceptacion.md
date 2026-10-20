# Matriz de aceptación · fase 4

CONFIRMED refiere exclusivamente a la evidencia indicada; no equivale a aceptación formal del equipo. Suite final desde `app/`: `evidencia/pruebas/20261020T005812834946Z/resultado.json`. Resultado final: 17/17 scripts OK, fuentes/base estables y huellas coincidentes con el árbol revisado.

| Caso | Evidencia | Estado |
|---|---|---|
| Nueve municipios, incluyendo sin reservadas | `test_planeador`, `test_municipios_planeador`, `test_consulta_rapida`; cifra/n/confianza exactos contra validación real | CONFIRMED |
| 59 y modelos media/mediana | Verificador inmutable, `test_planeador`, smoke `test_app` | CONFIRMED |
| 0/1/2/3/9/10 cosechas | `test_planeador`, `test_escenarios`, catálogo de municipios y consulta vacía; Nanacamilpa n=1 observado en navegador | CONFIRMED por pruebas y observación n=1 |
| Emiliano Zapata / marcas coincidentes | `test_escenarios`, `test_calculadora_visual` | CONFIRMED |
| Registrada fuera de rango | `test_planeador`, `test_escenarios`, `test_calculadora_visual` | CONFIRMED |
| Cuentas exactas, equilibrio y faltante/cubre/cero | Pruebas de cuenta/escenarios; tarjeta y tabla desde la misma cuenta; C2 abre al faltar | CONFIRMED |
| C2 sin rango y centavos | `test_escenarios`, `test_calculadora_visual`; n=1 visto en navegador | CONFIRMED |
| Vacío/cero/no finitos/overflow | `test_planeador`, `test_consulta_rapida`, pruebas de estado y cuenta común | CONFIRMED |
| Modo/vista/tema/parcela y superficies separadas | `test_recorridos_agricultor`, `test_calculadora_base`, estado; ida/vuelta observada en navegador | CONFIRMED |
| Oficial tras elegir media en Analista | `test_recorridos_agricultor`, cabecera sin cambios | CONFIRMED |
| Fichas por parcela y libreta | Pruebas de descargas y libreta; no ficha municipal nueva | CONFIRMED |
| Contexto histórico sin clima normal | `test_calculadora_visual`; C3 2025 sin cambio de cálculo | CONFIRMED |
| Recorridos × temas × 320/375/600/700/900/1400 | 24 capturas finales y mediciones DOM; sin desbordamiento en contenedores medidos | CONFIRMED |
| Nombre municipal largo / n=1 | Captura final Nanacamilpa 320 px; nombre completo en resumen; singular corregido | CONFIRMED |
| Teclado/foco del recorrido y detalle | Acciones reales en navegador y `teclado.json` | CONFIRMED, sin certificar lector de pantalla |
| Zoom real 200% | Confirmación exacta del usuario «Sí, funciona al 200%», registrada en `zoom.json` | CONFIRMED por usuario; no ejecutado por agente |
| Revisión independiente | TASK-012 / `.agent/revision-fase-4.md`; manifiesto, hashes y evidencia final releídos | CONFIRMED; sin defectos materiales |
| Cebi/fase 5 | Excluidos por instrucción humana | APLAZADO; no se certifica integración |
| T16/T18, despliegue, Docker | Sin intervención en sus decisiones/datos/infraestructura | FUERA DE ALCANCE |
