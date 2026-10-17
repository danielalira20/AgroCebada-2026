"""Lluvia y temperatura mensuales de una parcela."""
import altair as alt
import pandas as pd
import streamlit as st

from agrocebada_app.config import MESES
from agrocebada_app.frontend.componentes.graficas.base import grafica_base


def curva_clima(c, pid, alto=240):
    x = c[c.id_parcela == pid]
    if x.empty:
        return
    orden = [MESES[m] for m in range(3, 11)]
    x = x.assign(mes=pd.to_datetime(x.periodo + "-01").dt.month.map(MESES))
    eje = alt.X("mes:O", sort=orden, title=None, axis=alt.Axis(labelAngle=0))
    lluvia = alt.Chart(x).mark_bar(color="#5ED1E8", opacity=0.45, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=eje, y=alt.Y("PREC:Q", title="lluvia (mm/mes)"), tooltip=["mes", alt.Tooltip("PREC:Q", format=".0f")])
    temp = alt.Chart(x.melt(id_vars=["mes"], value_vars=["Tmax", "Tmin"], var_name="variable", value_name="°C")).mark_line(
        point=True, strokeWidth=2).encode(
        x=eje, y=alt.Y("°C:Q", title="temperatura (°C)"),
        color=alt.Color("variable:N", title=None, scale=alt.Scale(domain=["Tmax", "Tmin"], range=["#F5B544", "#7FB2FF"]),
                        legend=alt.Legend(orient="top")))
    st.altair_chart(grafica_base(alt.layer(lluvia, temp).resolve_scale(y="independent"), alto), width="stretch")
