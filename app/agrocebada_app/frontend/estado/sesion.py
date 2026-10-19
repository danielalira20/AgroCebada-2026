"""Valores iniciales de la sesión."""
import streamlit as st

from agrocebada_app.config import MODELO_OFICIAL


def iniciar_sesion():
    valores = {
        "tema": "claro",
        "vista": "Agricultor",
        "modelo": MODELO_OFICIAL,
        "capa": "Todas",
        "vista_mapa": "3D",
        "bienvenida_completada": False,
        "bienvenida_paso": 0,
    }

    for k, v in valores.items():
        st.session_state.setdefault(k, v)
