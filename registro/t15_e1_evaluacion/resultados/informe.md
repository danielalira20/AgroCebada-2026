# T15: evaluación del procedimiento común

Estimación retrospectiva de parcelas 2025. Resultados sobre etiquetas conocidas; no acredita otra campaña ni congela T16.

| Candidato | MAE por parcela | RMSE medio por repetición | R² medio por repetición |
|---|---:|---:|---:|
| comun_centrado_loo_v3_E1 | 0.321531 | 0.490979 | 0.660809 |
| comun_centrado_loo_v3_Q | 0.321420 | 0.490700 | 0.661194 |
| comun_centrado_loo_v3_S | 0.321670 | 0.490677 | 0.661212 |
| media_mun__resp_grupo | 0.320490 | 0.492593 | 0.658577 |

Decisión: A/sin_respaldo según contrato, intervalos por celdas; B y sin24 son sensibilidad. Los contrastes descriptivos no deciden promoción. Consultar denominadores y poblaciones en los CSV.

MAE y RMSE se expresan en t/ha. R² de objetivo constante queda vacío. Las repeticiones reutilizan parcelas. Las métricas por ID promedian errores, nunca predicciones antes de medir error. En B, el número de repeticiones elegibles por parcela puede variar; no confundir sus ponderaciones.

La selección humana conoce resultados anteriores y no constituye una validación externa ciega. No se atribuye aprobación a los revisores ni se generan predicciones de las 59.
