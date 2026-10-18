"""Tarjeta «Cómo leer esta estimación» con la mascota."""
import streamlit as st

from agrocebada_app.frontend.tema.estilos import MASCOTA
from agrocebada_app.frontend.tema.html import h


def explicacion_cebi():
    with st.container(key="glass_explica"):
        h(f"<div class='mascota'><div class='cebi'>{MASCOTA}</div><div><div class='tit'>Cómo leer esta estimación</div>"
          "<div class='nota' style='margin-top:4px'>La cifra sale de las parcelas de tu municipio que ya tienen cosecha "
          "registrada. El verdor y el clima se muestran para seguimiento: no cambian la estimación y un color o una "
          "curva no son una recomendación agronómica. El rendimiento no indica calidad maltera ni capacidad de pago."
          "</div></div></div>")
