"""Gráfica original de Validación: registrado contra estimado por municipio."""
import altair as alt
import pandas as pd
import streamlit as st

from agrocebada_app.frontend.componentes.graficas.base import grafica_base
from agrocebada_app.frontend.tema.html import titulo


def dispersion(ctx):
    """Registrado contra estimado, con las parcelas de A · sin respaldo."""
    OA = ctx.OA
    with st.container(key="glass_disp_val"):
        titulo("Registrado contra estimado",
               f"Cada punto es una de las {OA.ID_POLIGONO.nunique()} parcelas de A · sin respaldo; sobre la "
               "diagonal la estimación sería perfecta.")
        sc = OA.groupby("ID_POLIGONO").agg(real=("real", "first"), estimacion=("prediccion", "mean"),
                                           municipio=("municipio", "first")).reset_index()
        dom = alt.Scale(domain=[2, 6])
        puntos = alt.Chart(sc).mark_circle(size=55, opacity=0.85).encode(
            x=alt.X("real:Q", title="registrado (t/ha)", scale=dom),
            y=alt.Y("estimacion:Q", title="estimado sin conocerlo (t/ha)", scale=dom),
            color=alt.Color("municipio:N", title=None,
                            legend=alt.Legend(orient="bottom", direction="horizontal", columns=2, labelLimit=220,
                                              labelFontSize=11, columnPadding=12, rowPadding=6)),
            tooltip=["ID_POLIGONO", "municipio", "real", alt.Tooltip("estimacion", format=".2f")])
        diag = alt.Chart(pd.DataFrame({"x": [2, 6], "y": [2, 6]})).mark_line(
            color="rgba(255,255,255,0.35)", strokeDash=[4, 4]).encode(
            x=alt.X("x:Q", scale=dom), y=alt.Y("y:Q", scale=dom))
        st.altair_chart(grafica_base(diag + puntos, 300), width="stretch")
