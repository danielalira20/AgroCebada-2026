"""Pestaña «Cartera»: producción estimada por municipio y su escenario bajo–alto."""
import textwrap

import altair as alt
import streamlit as st

from agrocebada_app.backend.dominio.cartera import cartera_municipios, totales_cartera
from agrocebada_app.backend.dominio.confianza import NIVELES
from agrocebada_app.backend.dominio.rangos import ANIO, rangos_municipio
from agrocebada_app.frontend.componentes.graficas.base import grafica_base
from agrocebada_app.frontend.tema.html import e, h, titulo

TIPOS = {"P10–P90": "Rango típico", "mínimo–máximo": "De la menor a la mayor cosecha", "sin rango": "Sin rango"}
NOTA = (f"Estimación retrospectiva de la campaña {ANIO}. Los escenarios suponen que todo un municipio tiene un año "
        "bueno o malo a la vez. Con 59 parcelas y una campaña es una demostración, no una cifra oficial de "
        "producción regional.")


ANCHO_ETIQUETA = 16     # caracteres por renglón en el eje: los nombres largos se parten en dos renglones


def _t(x):
    return f"{x:,.0f} t"


def grafica_cartera(t, alto_fila=46):
    """Barras de producción por municipio; la línea con topes marca del escenario bajo al alto. Los valores van
    también en el texto y el tooltip, así que no dependen del color."""
    x = t.assign(sin_rango=t.tipo_rango == "sin rango",
                 renglones=t.municipio.map(lambda m: "\n".join(textwrap.wrap(m, ANCHO_ETIQUETA))))
    orden = list(x.renglones)
    y = alt.Y("renglones:N", sort=orden, title=None, axis=alt.Axis(labelLimit=0, labelFontSize=11, labelLineHeight=13))
    ayuda = [alt.Tooltip("municipio:N", title="Municipio"), alt.Tooltip("produccion_t:Q", title="Producción estimada (t)", format=",.0f"),
             alt.Tooltip("escenario_bajo_t:Q", title="Escenario bajo (t)", format=",.0f"),
             alt.Tooltip("escenario_alto_t:Q", title="Escenario alto (t)", format=",.0f")]
    barras = alt.Chart(x).mark_bar(color="#9BE15D", opacity=0.55, cornerRadiusTopRight=4,
                                   cornerRadiusBottomRight=4, size=20).encode(
        y=y, x=alt.X("produccion_t:Q", title="toneladas", axis=alt.Axis(format=",.0f")), tooltip=ayuda)
    linea = alt.Chart(x[~x.sin_rango]).mark_rule(color="#E8EEE9", strokeWidth=2).encode(
        y=y, x="escenario_bajo_t:Q", x2="escenario_alto_t:Q", tooltip=ayuda)
    topes = alt.Chart(x[~x.sin_rango].melt(id_vars=["renglones"], value_vars=["escenario_bajo_t", "escenario_alto_t"],
                                           value_name="t")).mark_tick(
        color="#E8EEE9", thickness=2, size=18, orient="vertical").encode(y=y, x="t:Q")
    capas = [barras, linea, topes]
    et = x.assign(etiqueta=x.apply(lambda f: _t(f.produccion_t) + (" · sin rango" if f.sin_rango else ""), axis=1))
    capas.append(alt.Chart(et).mark_text(align="left", dx=8, color="#E8EEE9", fontSize=11).encode(
        y=y, x="escenario_alto_t:Q", text="etiqueta:N"))
    st.altair_chart(grafica_base(alt.layer(*capas), max(180, alto_fila * len(x))), width="stretch")


def cartera(ctx):
    d = ctx.d
    rangos = rangos_municipio(d[d.CONJUNTO == "ENTRENAMIENTO"])
    t = cartera_municipios(d, ctx.pred, rangos, ctx.conf)
    tot = totales_cartera(t)
    with st.container(key="glass_cartera"):
        titulo("Cartera por municipio",
               "Producción estimada de las parcelas por estimar y lo que pasaría si todo el municipio tuviera "
               "un año bajo o uno alto.")
        if tot["mezcla_confianza"]:
            mezcla = tot["mezcla_confianza"]      # en el orden alta, media, baja y con la inicial en mayúscula
            cuarto = ("Confianza", " · ".join(f"{mezcla[k]} {k.capitalize()}" for k in NIVELES if k in mezcla), "parcelas")
        else:
            cuarto = ("Producción: escenario bajo a alto",
                      f"{tot['escenario_bajo_t']:,.0f}–{tot['escenario_alto_t']:,.0f}", "t")
        kp = [("Parcelas", f"{tot['parcelas']:,}", ""), ("Hectáreas", f"{tot['hectareas']:,.1f}", "ha"),
              ("Producción estimada", f"{tot['produccion_t']:,.0f}", "t"), cuarto]
        h("<div class='kpis'>" + "".join(
            f"<div class='mini'><span>{e(k)}</span><b class='kv'>{e(v)}<small>{e(u)}</small></b></div>"
            for k, v, u in kp) + "</div>")

        titulo("Producción por municipio", "La barra es la producción estimada; la línea con topes va del escenario "
                                           "bajo al alto.")
        grafica_cartera(t)

        a, b = st.columns([3, 1], vertical_alignment="center")
        with a:
            titulo("Tabla por municipio")
        vista = t.assign(tipo_rango=t.tipo_rango.map(TIPOS),
                         confianza=t.confianza.map(lambda v: v.capitalize() if isinstance(v, str) else v)).rename(columns={
            "municipio": "Municipio", "parcelas": "Parcelas", "hectareas": "Hectáreas",
            "estimacion": "Estimación (t/ha)", "tipo_rango": "Tipo de rango",
            "rango_bajo": "Año bajo del municipio (t/ha)", "rango_alto": "Año alto del municipio (t/ha)",
            "produccion_t": "Producción estimada (t)", "escenario_bajo_t": "Escenario bajo (t)",
            "escenario_alto_t": "Escenario alto (t)", "confianza": "Confianza", "escenario_nota": "Nota"})
        if t.confianza.isna().all():
            vista = vista.drop(columns="Confianza")
        b.download_button("Descargar CSV", vista.to_csv(index=False).encode("utf-8"),
                          file_name="cartera_por_municipio.csv", mime="text/csv", type="primary", width="stretch")
        dos = [c for c in vista.columns if c.endswith("(t)") or c.endswith("(t/ha)") or c == "Hectáreas"]
        st.dataframe(vista, hide_index=True, width="stretch",
                     column_config={c: st.column_config.NumberColumn(format="%.2f" if "t/ha" in c or c == "Hectáreas"
                                                                     else "%.0f") for c in dos})
        h(f"<div class='nota'>{e(NOTA)}</div>")
