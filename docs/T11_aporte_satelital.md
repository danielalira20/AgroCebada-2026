# T11 · Aporte satelital

Revisa: Migue · Diseño registrado antes de correr: D021

## Cómo se corre

`python scripts/t11_aporte_satelital.py` (≈1 min). Escribe en `registro/t11/`.

Entradas: `registro/t07/tabla_comun.csv`, `registro/t03/particiones.csv` y, sólo para verificar, `registro/t03/predicciones_oof_referencias_media_mun__resp_grupo.csv`.

## Qué se comparó

- **Territorio:** `media_mun__resp_grupo` (D019).
- **Territorio + satélite:** territorio + Ridge ajustado al residuo (real − referencia calculada sin la fila, O4). α elegido por selección interna (T03 §5).
- **Configuraciones:** las 8 de D006, con las mismas parcelas, estimador y validación (O2). Escenarios A y B, 5 repeticiones × 5 particiones.
- Sin clima: el contraste con clima queda para después de T09.

| # | Variables además de territorio |
|---|---|
| 1 | Calidad Planet abr_oct (capturas, hueco máximo, nubosidad) |
| 2 | S2 compacto jun_oct |
| 3 | S2 compacto abr_oct |
| 4 | Planet compacto jun_oct |
| 5 | Planet compacto abr_oct |
| 6 | 5 + calidad Planet (mejora A) |
| 7 | 5 + heterogeneidad `pl_ndvi_std_en_maximo_abr_oct` (mejora B) |
| 8 | 5 centrado por municipio con la media del entrenamiento |

## Verificación

La referencia de T11 reproduce la de T08: 1380 predicciones fuera de muestra, diferencia máxima 8.9e-16, mismas fuentes y las mismas filas con respaldo (15 en A, 31 en B).

## Resultados (sin_respaldo, donde se decide según D019)

Referencia: A → RMSE 0.4926, MAE 0.3205, R² 0.6586 · B → RMSE 0.5220, MAE 0.3579, R² 0.6110.

| # | ΔRMSE A | ΔMAE A | ΔRMSE B | ΔMAE B |
|---|---|---|---|---|
| 1 | +0.0017 | +0.0063 | −0.0009 | +0.0036 |
| 2 | −0.0023 | +0.0019 | −0.0003 | +0.0014 |
| 3 | +0.0013 | +0.0044 | +0.0128 | +0.0210 |
| 4 | +0.0008 | +0.0024 | +0.0016 | +0.0030 |
| 5 | +0.0008 | +0.0037 | +0.0036 | +0.0064 |
| 6 | +0.0009 | +0.0056 | −0.0038 | +0.0004 |
| 7 | +0.0020 | +0.0068 | +0.0037 | +0.0074 |
| 8 | +0.0003 | +0.0026 | −0.0047 | −0.0029 |

**Ninguna configuración cumple la regla de T03**, ni con MAE (vigente) ni con RMSE, en ningún escenario ni subconjunto. La mayor mejora es la de la config 8 en B (ΔRMSE −0.0047; IC95 por celdas [−0.0202, +0.0006]; 4/5 repeticiones), que no alcanza el umbral y cuyo intervalo incluye el cero.

En 7 de las 8 configuraciones el α más elegido fue 10000: el modelo tiende a apagar el satélite y quedarse con la referencia.

## O2: ¿calidad de observación o señal espectral?

- **A:** ni la calidad (1 vs. referencia: +0.0017) ni lo espectral (6 vs. 1: −0.0009; 6 vs. 5: +0.0001) aportan.
- **B:** sumar calidad a Planet tiende a mejorar (6 vs. 5: −0.0074), pero con IC95 [−0.0415, +0.0034]. Es una tendencia, no evidencia.

No se atribuye mejora a ninguna fuente, y ninguna comparación demuestra causalidad. Como las parcelas son de temporal (FIRA, 2ª sesión, P1), la nubosidad podría reflejar lluvia más que calidad de la observación. Conviene revisarlo cuando exista T09.

## Ventanas (D005)

- **Planet:** abr_oct y jun_oct no se distinguen (ΔRMSE +0.0001 en A, +0.0020 en B). Varias columnas coinciden entre ventanas (máximos y valor al corte), así que la comparación sólo difiere en integral, días sobre la mitad y día de inicio.
- **S2:** abr_oct tiende a empeorar en B (+0.0131; IC95 [−0.0011, +0.0309]). Es consistente con que abril es mayormente previo a la siembra (FIRA P2), pero no es concluyente.
- **Propuesta:** si un frente posterior usa satélite, preferir jun_oct.

## Conclusión

Con estas variables resumidas por temporada y este estimador, el satélite no aporta información más allá de la referencia territorial. La referencia se mantiene. El presupuesto de D006 (8/8) quedó usado; no se agregan configuraciones.

## Limitaciones

- Variables resumidas por temporada, no curvas completas.
- Sólo hay calidad de Planet para la O2; S2 no tiene ese escalón.
- En la selección interna, los residuos salen del entrenamiento externo y no se recalculan en cada partición interna (D021).
- El R² reportado es el de determinación (1 − SSE/SST).

## Archivos

`registro/t11/`: `predicciones_oof_t11.csv`, `metricas_t11.csv`, `comparacion_emparejada_t11.csv`, `coeficientes_t11.csv`.