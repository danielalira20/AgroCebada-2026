"""Resumen principal y poblaciones auxiliares, con datos calculados por el dominio."""
import streamlit as st

from agrocebada_app.frontend.tema.tablas import tabla as tabla_visual

from agrocebada_app.frontend.tema.html import e, h, titulo

TRES_DECIMALES = ["MAE (t/ha)", "RMSE (t/ha)", "Sesgo (t/ha)", "R²"]


def resultados(pob, modelo):
    with st.container(key="glass_val"):
        titulo("Resultado en municipios conocidos", f"{modelo} · Validación cruzada 5 × 5")
        principal = pob[pob.principal]
        if principal.empty:
            st.info("No hay resultados de la población principal para este modelo.")
        else:
            p = principal.iloc[0]
            h(f"<p class='val-contexto'><b>Población principal</b> · {e(p.poblacion)}</p>")
            items = [("MAE", f"{p.MAE:.3f}", "t/ha"), ("RMSE", f"{p.RMSE:.3f}", "t/ha"),
                     ("Sesgo", f"{p.sesgo:+.3f}", "t/ha"), ("R²", f"{p.R2:.3f}", "")]
            h("<div class='fila val-metricas'>" + "".join(
                f"<div class='mini'><span>{e(k)}</span><b class='kv'>{e(v)}<small>{e(u)}</small></b></div>"
                for k, v, u in items) + "</div>")
            h(f"<p class='val-contexto'>{int(p.parcelas)} parcelas distintas · {int(p.predicciones)} predicciones. "
              "Métricas promediadas por repetición.</p>")
            h("<p class='nota'>Sin respaldo: el municipio tenía cosechas conocidas al estimar. "
              "El error de esta evaluación no garantiza el rendimiento de otra parcela.</p>")
        apoyo = pob[~pob.principal].drop(columns="principal").rename(columns={
            "poblacion": "Población", "parcelas": "Parcelas", "predicciones": "Predicciones", "MAE": "MAE (t/ha)",
            "RMSE": "RMSE (t/ha)", "sesgo": "Sesgo (t/ha)", "R2": "R²"})
        if not apoyo.empty:
            with st.expander(f"Otras poblaciones, como apoyo ({len(apoyo)})", expanded=False):
                st.caption("Cada fila evalúa una población diferente; no son comparaciones directas de desempeño.")
                tabla_visual(apoyo, hide_index=True, width="stretch",
                             column_config={c: st.column_config.NumberColumn(format="%.3f") for c in TRES_DECIMALES})
