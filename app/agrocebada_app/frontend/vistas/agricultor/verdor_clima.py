"""Verdor y clima de la parcela elegida."""
import streamlit as st

from agrocebada_app.frontend.componentes.graficas.clima import curva_clima
from agrocebada_app.frontend.componentes.graficas.indices import curva_indice
from agrocebada_app.frontend.tema.html import titulo


def verdor_clima(ctx, pid):
    S = ctx.S
    C = ctx.C
    g1, g2 = st.columns(2)
    with g1, st.container(key="glass_ndvi"):
        titulo("Verdor de tu parcela en 2025", "Sube cuando el cultivo crece y baja al madurar o cosechar.")
        curva_indice(S, pid, "ndvi_promedio", "NDVI")
    with g2, st.container(key="glass_clima"):
        titulo("Lluvia y temperatura", "Promedio mensual de la zona (pixel de ~5.5 km).")
        if C is not None:
            curva_clima(C, pid)
        else:
            st.info("No hay información de lluvia y temperatura disponible para esta parcela.")
