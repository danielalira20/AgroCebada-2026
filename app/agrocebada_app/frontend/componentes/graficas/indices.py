"""Curva de un índice de vegetación por sensor."""
import altair as alt
import streamlit as st

from agrocebada_app.frontend.componentes.graficas.base import grafica_base


def curva_indice(s, pid, col, nombre, alto=240):
    x = s[(s.ID_POLIGONO == pid) & s[col].notna()][["fecha", "sensor", col]].sort_values("fecha")
    if x.empty:
        st.info("No hay capturas despejadas de este índice para la parcela.")
        return
    base = alt.Chart(x).encode(
        x=alt.X("fecha:T", title=None, axis=alt.Axis(format="%d/%m")),
        y=alt.Y(f"{col}:Q", title=nombre),
        color=alt.Color("sensor:N", title=None, scale=alt.Scale(domain=["Planet", "Sentinel-2"],
                                                                range=["#9BE15D", "#5ED1E8"]),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("fecha:T", format="%d/%m/%Y"), "sensor", alt.Tooltip(f"{col}:Q", format=".2f")])
    st.altair_chart(grafica_base(base.mark_line(opacity=0.55, strokeWidth=2) + base.mark_circle(size=34, opacity=0.95),
                             alto), width="stretch")
