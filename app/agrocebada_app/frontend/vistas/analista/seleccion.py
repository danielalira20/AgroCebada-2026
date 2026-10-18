"""Selección de parcela en la vista del analista."""
import streamlit as st

from agrocebada_app.frontend.componentes.mapa.interaccion import parcela_clicada


def clic_analista(clave, d):
    pid = parcela_clicada(clave)
    if pid in d.index:
        st.session_state["buscar_id"] = pid
