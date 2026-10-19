"""Comparación visual de cambios de MAE; las pruebas complementarias no reciben intervalos inventados."""
import altair as alt
import pandas as pd
import streamlit as st

from agrocebada_app.backend.dominio.evidencia import REDUCCION_MINIMA, etiqueta_prueba, marca
from agrocebada_app.frontend.componentes.graficas.base import grafica_base


def datos_grafica(exp, oficial):
    t = exp.copy()
    t["nombre"] = [etiqueta_prueba(f, oficial) for f in t.itertuples()]
    t["etiqueta"] = [f"{i:02d} · {n[:27]}{'…' if len(n) > 27 else ''}" for i, n in enumerate(t.nombre, 1)]
    t["resultado"] = [marca(f) for f in t.itertuples()]
    t["tipo"] = ["Complementaria" if f.estado == "complementaria" else
                 "Pasó la regla" if bool(f.pasa_regla) else
                 "Baja el error" if f.delta_mae < 0 else "No baja el error" for f in t.itertuples()]
    return t


@st.cache_data(show_spinner=False, max_entries=64)
def especificacion(exp, oficial, reduccion):
    """Compila por selección de datos; cambiar filtros o catálogo invalida esta entrada de caché."""
    t = datos_grafica(exp, oficial)
    eje = alt.Y("etiqueta:N", sort=t.etiqueta.tolist(), title=None,
                axis=alt.Axis(labelLimit=125, labelFontSize=11, ticks=False, domain=False))
    paleta = {"Baja el error": "#9BE15D", "No baja el error": "#95B6C8", "Complementaria": "#C5A8EB", "Pasó la regla": "#59DCB1"}
    presentes = [n for n in paleta if n in set(t.tipo)]
    color = alt.Color("tipo:N", title=None, scale=alt.Scale(domain=presentes, range=[paleta[n] for n in presentes]),
                      legend=alt.Legend(orient="bottom", columns=1))
    detalle = [alt.Tooltip("nombre:N", title="Prueba"), alt.Tooltip("delta_mae:Q", title="Cambio (t/ha)", format="+.4f"),
               alt.Tooltip("mae:Q", title="MAE (t/ha)", format=".4f"), alt.Tooltip("resultado:N", title="Resultado")]
    base = alt.Chart(t)
    intervalos = base.transform_filter("datum.estado === 'registrada'").mark_rule(color="#758C80", strokeWidth=2).encode(
        y=eje, x=alt.X("ic_inf:Q", title="Cambio de MAE (t/ha)", axis=alt.Axis(format="+.3f", tickCount=3)), x2="ic_sup:Q",
        tooltip=detalle + [alt.Tooltip("ic_inf:Q", title="IC inferior", format="+.4f"),
                          alt.Tooltip("ic_sup:Q", title="IC superior", format="+.4f")])
    puntos = base.mark_point(filled=True, size=90, opacity=1).encode(
        y=eje, x=alt.X("delta_mae:Q", title="Cambio de MAE (t/ha)",
                      axis=alt.Axis(format="+.3f", tickCount=3)), color=color, tooltip=detalle)
    limite = alt.X("limite:Q", title="Cambio de MAE (t/ha)", axis=alt.Axis(format="+.3f", tickCount=3))
    cero = alt.Chart(pd.DataFrame({"limite": [0.0]})).mark_rule(color="#D8E3DC", strokeWidth=1).encode(x=limite)
    umbral = alt.Chart(pd.DataFrame({"limite": [-reduccion]})).mark_rule(color="#F5D08A", strokeDash=[4, 4]).encode(x=limite)
    return grafica_base(intervalos + cero + umbral + puntos, max(180, len(t) * 30)).to_dict()


def comparacion(exp, oficial):
    st.vega_lite_chart(spec=especificacion(exp, oficial, REDUCCION_MINIMA), width="stretch")
    st.caption(f"← Menos error · Más error →. Gris: intervalo del 95 %. Línea discontinua: reducción mínima de {REDUCCION_MINIMA:.2f} t/ha; "
               "es sólo una condición de la regla. Bajar el error no equivale a pasarla.")
