# Borrador del PR · T12 heterogeneidad municipal y contraste no lineal

**Título:** `T12: heterogeneidad municipal y contraste no lineal (resultado R2: se conserva la referencia)`

**Base sugerida:** `t15-centrado-municipal` (PR #21), porque T12 importa sin cambios el procedimiento común v3.

## Resumen

T12 pregunta si dejar que cada municipio tenga su propia regla de corrección (`het`), o usar un modelo que no sea una línea recta (`gb`), baja el error frente a la referencia `media_mun__resp_grupo` (D019), usando las mismas variables de T10 y T15 (relieve, área y Planet).

**Resultado: R2, señal sin umbral. No se promueve nada y se conserva la referencia.**

- `t12_het_GP` (único promovible), escenario A, sin respaldo: dMAE **−0.0009**, IC95 [−0.0066, +0.0047], mejora en 4 de 5 repeticiones. El IC incluye el cero y el cambio está lejos de −0.01 (T03 §4).
- Ablación (C1) frente a la misma corrección con una sola pendiente: −0.0006. Revuelto (C2): ninguna de las 20 mezclas iguala al resultado real, p = 0.0476.
- En B (zonas climáticas nuevas) no hay mejora: `het_GP` +0.0071.
- Los secundarios y los controles tampoco cumplen. `het_G` solo repara la pendiente común de relieve y área, que empeora a la referencia (+0.0032).
- Nota para T16 (no es decisión de T12): la mediana municipal como observación de referencia da menos error que la media en A y B (0.3126 contra 0.3205; 0.3398 contra 0.3579), lo que T08 ya había visto sin cumplir la regla.

## Qué incluye

- **Diseño** escrito antes de correr: `docs/T12_heterogeneidad_municipal.md`, `registro/t12/procedimiento_t12.json`, `D_T12_001`, `E_T12_001` a `E_T12_008`.
- **Código:** `scripts/t12_heterogeneidad.py` (congelado, SHA-256 `3b4f55c7…1717`), `t12_evaluar.py`, `t12_controles.py`, `t12_auditar.py`, `t12_reproducir.py`.
- **Pruebas sintéticas:** `tests/test_t12_*.py`, con mutaciones comprobadas en el auditor y en el comparador.
- **Resultados:** `registro/t12/` con `manifest.json` (huellas de código, entradas y salidas), controles C2 a C6 y `auditoria_t12.json`.
- **Cierre:** `analisis/heterogeneidad_municipal/` (informe en lenguaje sencillo, bitácora y este borrador), `D_T12_002`, `IA_T12_002` y los experimentos cerrados.

## Cómo comprobarlo

Desde la raíz del repositorio:

```powershell
.\ejecutar.ps1 python -m unittest tests.test_t12_heterogeneidad tests.test_t12_evaluar tests.test_t12_controles tests.test_t12_auditar tests.test_t12_reproducir
.\ejecutar.ps1 python -m scripts.t12_auditar --controles
.\ejecutar.ps1 python -m scripts.t12_evaluar --salida reports/t12_repro --confirmo-barreras --procesos 2
.\ejecutar.ps1 python -m scripts.t12_reproducir --reproduccion reports/t12_repro --etiqueta "<sistema>"
```

La auditoría independiente (otro código, NumPy, sin Ridge) coincide con diferencia máxima de 1.8e-15. La reproducción en Windows con Docker es idéntica byte a byte; la de Mac está pendiente.

## Para revisar con cuidado

1. **Diseño no ciego.** El equipo conocía los resultados de T08 a T15 y correlaciones dentro de los municipios con las mismas 138 parcelas; está declarado en `D_T12_001`. Los IC son nominales (138 parcelas, 13 comparaciones).
2. **Revuelto con 20 permutaciones.** El p mínimo posible es 0.0476; no es una prueba fina.
3. **Clasificación R2 y no R3.** Se discute en `D_T12_002`: el MAE mejora nominalmente y el control común mejora igual en el cuarto de mayor error.
4. **`docs/T12_heterogeneidad_municipal.md`** solo cambió la línea de estado; el diseño no se reescribió después de ver resultados.
5. **Pendientes:** reproducción en Mac y revisión metodológica de Migue.

## Para otros frentes

- **T15:** la pendiente común de relieve y área empeora a la referencia en A; no incluir ese bloque sin otro que lo acompañe.
- **T16 y T17:** se mantienen las predicciones de la referencia para las 59; las de T12 son exploratorias (ver la ficha de consumo del informe).
- **Frentes nuevos posibles** (cada uno como tarea propia con regla escrita antes de correr): Tmax centrada con Planet, fenología fina y borde rojo de Sentinel-2.

🤖 Generated with [Claude Code](https://claude.ai/code)

https://claude.ai/code/session_01PWio1rHrJq65HwAF7cMLvm
