"""Curvas de índices de vegetación: por sensor (ficha técnica) y contra la franja del municipio (agricultor)."""
import altair as alt
import streamlit as st

from agrocebada_app.frontend.tema.paleta import color_grafica

from agrocebada_app.backend.dominio.franja_verdor import franja_municipio, sensor_para
from agrocebada_app.config import MESES_EJE
from agrocebada_app.frontend.componentes.graficas.base import grafica_base


def _eje_meses():
    return alt.Axis(tickCount="month", labelExpr=MESES_EJE)


def curva_indice(s, pid, col, nombre, alto=240):
    x = s[(s.ID_POLIGONO == pid) & s[col].notna()][["fecha", "sensor", col]].sort_values("fecha")
    if x.empty:
        st.info("No hay capturas despejadas de este índice para la parcela.")
        return
    base = alt.Chart(x).encode(
        x=alt.X("fecha:T", title=None, axis=_eje_meses()),
        y=alt.Y(f"{col}:Q", title=nombre),
        color=alt.Color("sensor:N", title=None, scale=alt.Scale(domain=["Planet", "Sentinel-2"],
                                                                range=[color_grafica("#9BE15D"), color_grafica("#5ED1E8")]),
                        legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("fecha:T", format="%d/%m/%Y"), "sensor", alt.Tooltip(f"{col}:Q", format=".2f")])
    st.altair_chart(grafica_base(base.mark_line(opacity=0.55, strokeWidth=2) + base.mark_circle(size=34, opacity=0.95),
                                 alto), width="stretch", theme=None)


def curva_franja(s, d, pid, col="ndvi_promedio", nombre="NDVI", alto=240):
    """Curva de la parcela sobre la franja normal (percentiles 25 a 75) de las parcelas con cosecha de su municipio.
    Devuelve (sensor, hay_franja) o None si la parcela no tiene datos."""
    sensor = sensor_para(s, pid, col)
    if sensor is None:
        st.info("No hay capturas despejadas de este índice para la parcela.")
        return None
    x = s[(s.ID_POLIGONO == pid) & (s.sensor == sensor) & s[col].notna()][["fecha", col]].sort_values("fecha")
    linea = alt.Chart(x).encode(
        x=alt.X("fecha:T", title=None, axis=_eje_meses()), y=alt.Y(f"{col}:Q", title=nombre),
        tooltip=[alt.Tooltip("fecha:T", title="fecha", format="%d/%m/%Y"),
                 alt.Tooltip(f"{col}:Q", title="tu parcela", format=".2f")])
    capas = [linea.mark_line(color=color_grafica("#9BE15D"), strokeWidth=2.2), linea.mark_circle(color=color_grafica("#9BE15D"), size=30)]
    f = franja_municipio(d, s, pid, col, sensor)
    if f is not None:
        franja = alt.Chart(f).mark_area(color=color_grafica("#B4C5BA"), opacity=0.3).encode(
            x=alt.X("semana:T", title=None, axis=_eje_meses()), y=alt.Y("p25:Q", title=nombre), y2="p75:Q",
            tooltip=[alt.Tooltip("semana:T", title="semana del", format="%d/%m"),
                     alt.Tooltip("p25:Q", title="parte baja de la franja", format=".2f"),
                     alt.Tooltip("p75:Q", title="parte alta de la franja", format=".2f"),
                     alt.Tooltip("n:Q", title="parcelas con dato")])
        capas.insert(0, franja)
    st.altair_chart(grafica_base(alt.layer(*capas), alto), width="stretch", theme=None)
    return sensor, f is not None