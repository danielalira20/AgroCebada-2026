# Borrador del PR · T12 heterogeneidad municipal y contraste no lineal

**Título:** `T12: heterogeneidad municipal y contraste no lineal (resultado R2: se conserva la referencia)`

**Base sugerida:** `t15-centrado-municipal` (PR #21), porque T12 importa sin cambios el procedimiento común v3. Esa rama avanzó hasta `cc7d0ae`; antes de abrir el PR hay que fusionarla en esta rama (choques de texto esperables solo en `registro/decisiones.csv`, `experimentos.csv` y `uso_ia.csv`, sin IDs repetidos: se conservan las dos partes).

## Resumen

T12 pregunta si dejar que cada municipio tenga su propia regla de corrección (`het`), o usar un modelo que no sea una línea recta (`gb`), baja el error frente a la referencia `media_mun__resp_grupo` (D019), usando las mismas variables de T10 y T15 (relieve, área y Planet).

**Resultado: R2, señal sin umbral. No se promueve nada y se conserva la referencia.**

- `t12_het_GP` (único promovible), escenario A, sin respaldo: dMAE **−0.0009**, IC95 [−0.0066, +0.0047], mejora en 4 de 5 repeticiones. El IC incluye el cero y el cambio está lejos de −0.01 (T03 §4).
- Ablación (C1) frente a la misma corrección con una sola pendiente: −0.0006. Revuelto (C2): ninguna de las 20 mezclas iguala al resultado real, p = 0.0476.
- En B (zonas climáticas nuevas) no hay mejora: `het_GP` +0.0071.
- Los secundarios y los controles tampoco cumplen (`gb_GP` queda en ≈0 en B: −0.0007 por parcela, +0.0005 por repetición). `het_G` solo repara la pendiente común de relieve y área, que empeora a la referencia (+0.0032).
- Nota para T16 (no es decisión de T12): la mediana municipal como observación de referencia da menos error que la media en A y B (0.3126 contra 0.3205; 0.3398 contra 0.3579), lo que T08 ya había visto sin cumplir la regla.

## Resultados: qué queda establecido

Antes de T12 había una duda abierta (anotada en T10 y en D021): si las variables de T10, T11, T14 y T15 no ayudaban porque no sirven o porque se usaban con una sola regla y en línea recta. T12 la contesta para relieve, área y Planet:

| Se puede afirmar | Evidencia | Firmeza |
|---|---|---|
| Una regla por municipio no rescata a estas variables | 0 de 8 procedimientos cumplen T03 §4, en A y en B; mejor caso `het_GP` −0.0009, IC95 [−0.0066, +0.0047] | Firme para estas variables, esta campaña y 138 parcelas |
| Un modelo no lineal tampoco | `gb_GP` +0.0019 en A, ≈0 en B (−0.0007 por parcela, +0.0005 por repetición); el ajuste final elige no corregir | Firme, mismas condiciones |
| Con estas dos formas de modelo, la conclusión de T10, T11, T14 y T15 no mejora | Ni la regla por municipio (Ridge) ni árboles de profundidad 2 la cambian | Firme solo para esas dos variantes, relieve, área y Planet. No descarta otras formas de modelo ni otras variables |
| La regla común de relieve y área perjudica a la referencia | `control_comun_G` +0.0032 en A y +0.0092 en B (IC95 [+0.0031, +0.0249]); T10 vio +0.0027 | Bastante firme |
| Repartirla por municipio repara la pérdida, pero no gana | `het_G` frente a `control_comun_G` −0.0045 [−0.0083, −0.0011], 5 de 5 repeticiones; frente a la referencia −0.0014 | Firme como diagnóstico |
| El promedio municipal es difícil de superar | 8 alternativas, 25 repeticiones por escenario, ninguna lo supera de forma comprobable | Firme para lo probado |
| La mediana reproduce T08 | A 0.3126 contra 0.3205; B 0.3398 contra 0.3579; con la corrección encima empeora (+0.0018 en A) | Consistente con T08; a probar en T16 con su propia regla |

**Sobre «lo lineal».** T12 no prueba que lo lineal gane a lo no lineal; prueba que **lo simple (la referencia) no se supera**. En A los árboles quedan 0.0022 peor que su control lineal (el rango incluye el cero); en B quedan 0.0108 mejor por parcela (0.0097 por repetición), pero ese control ya empeoraba a la referencia (+0.0100).

**No queda establecido:** que otras formas de modelo (árboles más profundos, más datos) tampoco ayuden, que el −0.0009 sea un efecto real, que la causa sean variedad, siembra o manejo, que más parcelas ayuden, que otras variables no sirvan, que valga para otras campañas ni la reproducción en Mac.

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
4. **`docs/T12_heterogeneidad_municipal.md`** solo cambió la línea de estado, «(pendiente)» en el encabezado y dos **notas con fecha** (16 oct): §5.2 sobre `init='zero'` y §10 sobre la barrera 6. Las frases originales no se reescribieron.
5. **Unidades en B.** Los `dMAE` son «por parcela» (T03 §4). En B la referencia vale 0.3579 si se promedia el MAE de cada repetición, 0.3584 por registro y 0.3632 por parcela (16 de 135 parcelas solo se evalúan 4 veces); en A las tres dan 0.3205. La decisión se toma en A, así que esto no afecta la clasificación.
6. **Compatibilidad con T15 (16 oct).** Los commits nuevos de T15 hasta `cc7d0ae` no modifican ningún archivo fijado por T12 (14 de 14 idénticos, ningún script ni prueba previo tocado), por lo que los resultados no cambian y no se repitió la corrida.
7. **`init='zero'` en los árboles.** `init='zero'` solo fija en cero el punto de partida de las predicciones; después las hojas de los árboles sí pueden aprender un desplazamiento constante, a diferencia del Ridge, que no tiene intercepto. Por eso los árboles tuvieron un poco más de libertad que las demás familias. Se midió el efecto: el desplazamiento medio de `gb_GP` frente a la referencia es +0.0015 t/ha en A y +0.0001 en B, así que no aprendió un sesgo sistemático, y aun con esa libertad no mejora a la referencia. No es una fuga de datos. El diseño decía que «una mejora no puede venir solo de calibrar»; es incorrecto y está corregido con una nota fechada. El comentario del código no se toca porque el archivo está congelado.
8. **Revisión de Migue pendiente.** La condición 6 de las barreras («Migue revisó este diseño») **no se había cumplido** cuando se corrió con `--confirmo-barreras` el 15 de octubre: Jass confirmó las barreras sin una revisión previa de Migue. Migue todavía no revisó ni el diseño ni los resultados. Los resultados son válidos para el diseño tal como se registró, pero esa revisión puede pedir cambios; hasta entonces hay que leerlos como condicionales a ella.
9. **Pendientes:** reproducción en Mac y revisión metodológica de Migue.

## Para otros frentes

- **T15 (informativo, no pide cambiar su menú):** `control_comun_G`, `_P` y `_GP` de T12 usan exactamente las mismas opciones (ventana, λ, columnas) y el mismo código v3 que los procedimientos G, P y G+P del contrato de T15. T12 ya midió esas tres comparaciones (A/sin_respaldo: G +0.0032, P +0.0025, G+P −0.0003; ninguna cumple la regla, y en B ninguna mejora), así que T15 ya no es ciego para ellas; hay que anotarlo en su exposición previa. Cuando T15 corra su evaluación completa, esos tres deberían salir idénticos a `registro/t12/`: es una comprobación gratis.
- **T16 y T17:** se mantienen las predicciones de la referencia para las 59; las de T12 son exploratorias (ver la ficha de consumo del informe).
- **Frentes nuevos posibles** (cada uno como tarea propia con regla escrita antes de correr): Tmax centrada con Planet, fenología fina y borde rojo de Sentinel-2.
