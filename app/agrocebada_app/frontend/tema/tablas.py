"""Tablas interactivas: celdas por tema; cabeceras salvia configuradas en Streamlit."""
import streamlit as st

from agrocebada_app.frontend.tema.paleta import es_oscuro


def tabla(data, **opciones):
    if not es_oscuro():
        data = data.style.set_properties(**{"background-color": "#F6F8F2", "color": "#293f2c"})
    return st.dataframe(data, **opciones)
