"""Valores iniciales de la sesión."""
import streamlit as st

from agrocebada_app.config import MODELO_OFICIAL


def iniciar_sesion():
    for k, v in {"vista": "Agricultor", "modelo": MODELO_OFICIAL, "capa": "Todas", "vista_mapa": "3D"}.items():
        st.session_state.setdefault(k, v)
