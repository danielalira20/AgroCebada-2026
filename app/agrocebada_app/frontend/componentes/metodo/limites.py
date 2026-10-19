"""Límites de la estimación."""
import streamlit as st

from agrocebada_app.frontend.tema.html import e, h, titulo


def limites(lista):
    with st.container(key="glass_limites"):
        titulo("Límites", "Lo que esta estimación no puede decir.")
        h("<div class='limites'>" + "".join(f"<div class='limite'>{e(x)}</div>" for x in lista) + "</div>")
