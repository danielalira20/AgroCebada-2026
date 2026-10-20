# Revisión independiente de fase 4

Estado: revisión independiente terminada. Fecha local: 2026-10-19.

## Alcance

Revisión local-only sobre HEAD `efbb2dd3c82b254550232f42e1ff7b1c51c351c0`, sin PR ni commit nuevo. Base específica de esta fase: copias exactas de `.agent/fase4/antes/`, comparadas mediante diff con los cuatro archivos actuales. Se leyó completo el nuevo `app/herramientas/verificar_planeador.py`. Las modificaciones previas de fases 1–3 no se atribuyen a fase 4. Sin cambios del revisor en código, pruebas, datos, ramas o índice.

## Resultado de código

Sin candidatos materiales confirmados en los deltas y el runner. Dictamen del código/evidencia local revisados: **approve**, limitado a fase 4. Se revisaron README, matriz de aceptación y manifiesto final. Esta revisión no sustituye aceptación formal del equipo, aprobación científica T16, corrección histórica T18 ni despliegue.

## Método y cobertura

- Frontend: leídos todos los hunks, sus contextos, los componentes de escenarios, los callers del helper `titulo`, y las pruebas de consulta, escenarios, tema y app pertinentes. El nuevo argumento de nivel es opcional; los callers que no lo usan conservan el `div` escapado anterior (`app/agrocebada_app/frontend/tema/html.py:20 @ worktree (local-only)`). Sólo consulta rápida, referencia municipal y calculadora optan por encabezados semánticos.
- Compatibilidad y seguridad: `e()` sigue escapando título y subtítulo; no se agregaron datos externos a HTML sin escape en los deltas. Las reglas de tamaño aumentan especificidad dentro de escenarios/resumen rápido; las nuevas reglas de encabezados se restringen a los tres contenedores indicados (`app/assets/css/tema.css:766`, `:824`, `:833 @ worktree (local-only)`). No cambiaron fórmulas, estado, datos, mapas ni selectores de Cebi en estos hunks.
- Operación/reproducibilidad: el runner registra código de salida/log por script, distingue timeout/error de lanzamiento, verifica estabilidad de las fuentes enumeradas y de la base, y retorna error si algún caso o huella falla (`app/herramientas/verificar_planeador.py:84-113 @ worktree (local-only)`). `--caso` permite ejecución parcial identificable por la lista de casos; no representa por sí mismo aceptación completa de la matriz.
- Segunda pasada: root añadió una regla de fondo/texto para `summary` exclusivamente dentro de `glass_calculadora` (`app/assets/css/tema.css:811 @ worktree (local-only)`), tras medir texto oscuro sobre fondo oscuro con tema claro en `evidencia/antes-contraste.json`. El selector y los tokens no cambian otros módulos. El revisor leyó ese delta adicional; la medición y la inspección visual proceden de root.
- Tercera pasada: se leyó la corrección singular/plural de la muestra y su aserción existente, aisladas contra snapshot. Sólo cambia el texto de n=1; mantiene el conteo crudo. Se releyeron el runner con `cwd=APP` y huellas ampliadas de configuración/requirements/dependencias numéricas, que hacen explícito el directorio de ejecución y permiten cargar `app/.streamlit/config.toml`.
- No aplican a estos deltas: migraciones, permisos/autenticación, pagos, colas, APIs externas, dependencias instaladas o coordinación de despliegue.

## Pruebas y evidencia

- Ejecutado por el revisor: `.venv/Scripts/python.exe -B -X utf8 app/herramientas/verificar_planeador.py --help`, salida 0; comprobación de lectura de hashes y existencia de logs del manifiesto en curso, coincidentes en ese punto. No se ejecutó AppTest, servidor ni navegador por este revisor.
- Inspeccionados: contratos v1, matriz P4-1, TASK-011, pruebas `test_calculadora_visual`, `test_consulta_rapida`, `test_tema`, `test_descargas_ficha` y `test_app`.
- Inspección posterior: el manifiesto `20261020T004424081747Z` terminó `OK`, completo, 17 scripts. Tras corregir `summary`, la corrida dirigida `20261020T005017043298Z` también terminó `OK`, con visual/recorridos/tema/base (4 scripts). En ambos, `fuentes_estables` y `base_estable` son `true`. El revisor recalculó las huellas enumeradas en la corrida dirigida y coinciden con los archivos actuales. No se presenta la huella CSS de la suite de 17 como huella del CSS posterior.
- Los dos logs finales de `verificar_base_planeador` afirman conservación 197/138/59, ambos modelos, métricas, rangos, confianza y cuentas; conservan explícitamente los límites T16/T18.
- Leídos `mediciones-visual.json` y `teclado.json` producidos por root: en la evidencia disponible hay viewport sin desbordamiento de documento, cifras 44/32px y expansión con texto/fondo congruentes; el foco del detalle tiene outline visible. Son mediciones del navegador operado por root, no pruebas ejecutadas por el revisor.
- `zoom.json` registra que Ctrl+plus no cambió ancho, escala ni DPR. Esa evidencia acredita un intento sin efecto observable; no acredita zoom 200% ni permite cerrar ese criterio por equivalencia con viewport pequeño.
- Observación de procedencia comunicada a root: `fuentes_sha256` identifica sólo `FUENTES` y scripts seleccionados, no todo el repositorio ni todas las dependencias transitivas. Root añadió `evidencia/entorno.json` con versiones y huellas separadas de configuración, requirements y dependencias numéricas. Documentar esa distinción evita afirmar una identidad integral que el runner no calcula.

## Cierre de la evidencia final

- Manifiesto final `20261020T005812834946Z`: `completa=true`, `resultado=OK`, 17 scripts distintos y todos los códigos 0, todos los logs existen, `fuentes_estables=true`, `base_estable=true`. Directorio de ejecución: `app/`. El revisor recalculó cada SHA-256 enumerado contra archivos actuales: todos coinciden. El log final del verificador conserva la base y sus límites T16/T18.
- `mediciones-visual.json`: 24 registros con archivos únicos y presentes; dos recorridos, dos temas, seis anchos. Todos declaran configuración `app/.streamlit/config.toml` y `docAncho=viewport`. README limita correctamente la afirmación a contenedores medidos y capturas de sección. Los artefactos exploratorios previos no se usan como aceptación final.
- `teclado.json` final: configuración real, acciones descritas y foco con outline visible dentro del viewport. La inspección directa pertenece a root; el revisor cotejó los registros y el alcance de las afirmaciones.
- Zoom 200%: root confirmó al revisor que el usuario respondió explícitamente «Sí, funciona al 200%». README, matriz y `zoom.json` atribuyen esa comprobación al usuario y conservan el intento fallido del agente; no inventan navegador, dispositivo o versiones. No se presenta como reproducción del revisor ni del agente.
- README y matriz conservan los límites sobre Cebi/fase 5, T16/T18, aceptación formal, publicación, lector de pantalla, mapas externos y dispositivos no ensayados. Los tres pasos editoriales siguen los contratos v1 y no agregan promesas de elegibilidad o cosecha.

## Pendientes y decisión

Sin bloqueadores de código ni decisiones nuevas requeridas dentro de esta revisión local. Root actualizará únicamente la fila administrativa de revisión independiente y el estado de cierre del README, que aún reflejan «pendiente/en curso» al momento de esta lectura. Fuera de alcance permanecen Cebi, T16/T18, aceptación formal del equipo y despliegue; no se certifican por esta aprobación local. No se operó navegador ni se ejecutó la suite por el revisor: los resultados dinámicos son de root, con integridad de sus archivos comprobada de forma independiente.
