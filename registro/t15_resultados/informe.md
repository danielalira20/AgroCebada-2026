# T15: evaluación del procedimiento común

Estimación retrospectiva de parcelas 2025. Resultados sobre etiquetas conocidas; no acredita otra campaña ni congela T16.

| Candidato | MAE por parcela | RMSE medio por repetición | R² medio por repetición |
|---|---:|---:|---:|
| comun_centrado_loo_v3_C | 0.322328 | 0.491714 | 0.659799 |
| comun_centrado_loo_v3_CG | 0.322684 | 0.488913 | 0.663672 |
| comun_centrado_loo_v3_CGP | 0.320428 | 0.489218 | 0.663245 |
| comun_centrado_loo_v3_CP | 0.323068 | 0.491744 | 0.659718 |
| comun_centrado_loo_v3_G | 0.323662 | 0.488554 | 0.664156 |
| comun_centrado_loo_v3_GP | 0.320189 | 0.488779 | 0.663842 |
| comun_centrado_loo_v3_P | 0.322987 | 0.492383 | 0.658835 |
| comun_centrado_loo_v3_S | 0.321670 | 0.490677 | 0.661212 |
| media_mun__resp_grupo | 0.320490 | 0.492593 | 0.658577 |

Decisión: A/sin_respaldo según contrato, intervalos por celdas; B y sin24 son sensibilidad. Los contrastes descriptivos no deciden promoción. Consultar denominadores y poblaciones en los CSV.

MAE y RMSE se expresan en t/ha. R² de objetivo constante queda vacío. Las repeticiones reutilizan parcelas. Las métricas por ID promedian errores, nunca predicciones antes de medir error. En B, el número de repeticiones elegibles por parcela puede variar; no confundir sus ponderaciones.

La selección humana conoce resultados anteriores y no constituye una validación externa ciega. No se atribuye aprobación a los revisores ni se generan predicciones de las 59.
