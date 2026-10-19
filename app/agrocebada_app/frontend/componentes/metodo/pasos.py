"""Cómo se calcula: los cuatro pasos del método."""
import streamlit as st

from agrocebada_app.frontend.tema.html import e, h, titulo


def pasos(lista):
    with st.container(key="glass_metodo"):
        titulo("Cómo se calcula", "La aplicación usa los datos de cosecha de 2025 para dar una estimación basada en el "
                                  "valor típico de cada municipio.")
        h("<div class='pasos'>" + "".join(f"<div class='paso'><div class='n'>{i}</div><b>{e(t)}</b><p>{e(x)}</p></div>"
                                          for i, (t, x) in enumerate(lista, 1)) + "</div>")
