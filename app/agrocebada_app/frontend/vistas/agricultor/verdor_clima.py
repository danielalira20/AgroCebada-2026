"""Verdor y clima de la parcela elegida, como contexto: no entran en el cálculo de la estimación."""
import streamlit as st

from agrocebada_app.frontend.componentes.graficas.clima import curva_clima
from agrocebada_app.frontend.componentes.graficas.indices import curva_franja
from agrocebada_app.frontend.tema.html import h, titulo

CONTEXTO = "Es contexto: no entra en el cálculo de la estimación."


def verdor_clima(ctx, pid):
    d, S, C = ctx.d, ctx.S, ctx.C
    g1, g2 = st.columns(2)
    with g1, st.container(key="glass_ndvi"):
        titulo("Tu parcela comparada con las de tu municipio",
               "Verdor (NDVI): sube cuando el cultivo crece y baja al madurar o cosechar.")
        r = curva_franja(S, d, pid)
        if r is not None:
            sensor, hay_franja = r
            if hay_franja:
                nota = (f"La línea es tu parcela ({sensor}). La franja muestra dónde quedó la mitad central de las "
                        "parcelas con cosecha de tu municipio, semana a semana.")
            else:
                nota = (f"La línea es tu parcela ({sensor}). Tu municipio tiene muy pocas parcelas con cosecha para "
                        "dibujar una franja de comparación.")
            h(f"<div class='nota'>{nota} {CONTEXTO}</div>")
    with g2, st.container(key="glass_clima"):
        titulo("Lluvia y temperatura", f"Promedio mensual de la zona (píxel de ~5.5 km). {CONTEXTO}")
        if C is not None:
            curva_clima(C, pid)
        else:
            st.info("No encontré la tabla de clima.")