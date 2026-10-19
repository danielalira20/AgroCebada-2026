"""Lluvia y temperatura mensuales de una parcela."""
import altair as alt
import pandas as pd
import streamlit as st

from agrocebada_app.frontend.tema.paleta import color_grafica

from agrocebada_app.config import MESES
from agrocebada_app.frontend.componentes.graficas.base import grafica_base


def curva_clima(c, pid, alto=240):
    x = c[c.id_parcela == pid]
    if x.empty:
        return
    orden = [MESES[m] for m in range(3, 11)]
    x = x.assign(mes=pd.to_datetime(x.periodo + "-01").dt.month.map(MESES))
    eje = alt.X("mes:O", sort=orden, title=None, axis=alt.Axis(labelAngle=0))
    lluvia = alt.Chart(x).mark_bar(color=color_grafica("#5ED1E8"), opacity=0.45, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=eje, y=alt.Y("PREC:Q", title="lluvia (mm/mes)"), tooltip=["mes", alt.Tooltip("PREC:Q", format=".0f")])
    temp = alt.Chart(x.melt(id_vars=["mes"], value_vars=["Tmax", "Tmin"], var_name="variable", value_name="°C")).mark_line(
        point=True, strokeWidth=2).encode(
        x=eje, y=alt.Y("°C:Q", title="temperatura (°C)"),
        color=alt.Color("variable:N", title=None, scale=alt.Scale(domain=["Tmax", "Tmin"], range=[color_grafica("#F5B544"), color_grafica("#7FB2FF")]),
                        legend=alt.Legend(orient="top")))
    st.altair_chart(grafica_base(alt.layer(lluvia, temp).resolve_scale(y="independent"), alto), width="stretch", theme=None)


def curva_clima_normal(t, alto=190):
    """Lluvia y temperatura de 2025 contra el promedio 2022–2024 (tabla de clima_anomalia.comparar)."""
    orden = [MESES[m] for m in range(3, 11)]
    x = t.assign(mes=t.mes.map(MESES))
    eje = alt.X("mes:O", sort=orden, title=None, axis=alt.Axis(labelAngle=0))
    ayuda = ["mes", alt.Tooltip("PREC:Q", title="2025 (mm)", format=".0f"),
             alt.Tooltip("PREC_normal:Q", title="promedio 2022–2024 (mm)", format=".0f")]
    barras = alt.Chart(x).mark_bar(color=color_grafica("#5ED1E8"), opacity=0.6, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=eje, y=alt.Y("PREC:Q", title="lluvia (mm/mes)"), tooltip=ayuda)
    marca = alt.Chart(x).mark_tick(color=color_grafica("#E8EEE9"), thickness=2, size=24).encode(
        x=eje, y="PREC_normal:Q", tooltip=ayuda)
    st.altair_chart(grafica_base(alt.layer(barras, marca), alto), width="stretch", theme=None)

    normal = x[["mes", "Tmax_normal", "Tmin_normal"]].rename(columns={"Tmax_normal": "Tmax", "Tmin_normal": "Tmin"})
    largo = pd.concat([
        x[["mes", "Tmax", "Tmin"]].melt(id_vars="mes", var_name="variable", value_name="°C").assign(serie="2025"),
        normal.melt(id_vars="mes", var_name="variable", value_name="°C").assign(serie="promedio 2022–2024")])
    temp = alt.Chart(largo).mark_line(point=True, strokeWidth=2).encode(
        x=eje, y=alt.Y("°C:Q", title="temperatura (°C)", scale=alt.Scale(zero=False)),
        color=alt.Color("variable:N", title=None, scale=alt.Scale(domain=["Tmax", "Tmin"], range=[color_grafica("#F5B544"), color_grafica("#7FB2FF")]),
                        legend=alt.Legend(orient="top")),
        strokeDash=alt.StrokeDash("serie:N", title=None,
                                scale=alt.Scale(domain=["2025", "promedio 2022–2024"], range=[[1, 0], [5, 4]]),
                                legend=alt.Legend(orient="top", symbolType="stroke", symbolStrokeColor=color_grafica("#E8EEE9"))),
        tooltip=["mes", "variable", "serie", alt.Tooltip("°C:Q", format=".1f")])
    st.altair_chart(grafica_base(temp, alto + 60), width="stretch", theme=None)
