"""Estilo común de las gráficas (fondo transparente, rejilla tenue)."""
import streamlit as st

from agrocebada_app.frontend.tema.paleta import color_grafica


def grafica_base(ch, alto, tema=None):
    tema = tema or st.session_state.get("tema", "claro")
    oscuro = tema == "oscuro"
    texto = "#E7EFE9" if oscuro else "#293F2C"
    return ch.properties(height=alto, background="transparent").configure_view(strokeWidth=0).configure_axis(
        labelColor=texto, titleColor=texto,
        gridColor="rgba(255,255,255,0.07)" if oscuro else "#DFE5D9",
        domainColor="rgba(255,255,255,0.18)" if oscuro else "#A3B29B",
        tickColor="rgba(255,255,255,0.18)" if oscuro else "#A3B29B"
    ).configure_legend(labelColor=texto, titleColor=texto).configure_title(color=texto).configure_range(
        category=[color_grafica(c, tema) for c in
                  ["#9BE15D", "#2FE0A0", "#F5B544", "#7FB2FF", "#FF7A45", "#C59BFF", "#F2E86D", "#5ED1E8", "#FF9EC4"]])
