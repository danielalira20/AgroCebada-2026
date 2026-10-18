"""Barra superior: marca, vista (agricultor o analista), modelo y fondo satelital."""
import streamlit as st

from agrocebada_app.config import MODELOS, MODELO_OFICIAL
from agrocebada_app.frontend.tema.estilos import MARCA
from agrocebada_app.frontend.tema.html import h


def cabecera():
    """Dibuja la barra y devuelve (es_agricultor, modelo, satelite)."""
    with st.container(key="glass_top"):
        c1, c2, c3, c4 = st.columns([3.2, 2.5, 2.5, 1.8], vertical_alignment="center")
        with c1:
            h(MARCA)
        vista = c2.segmented_control("Vista", ["Agricultor", "Analista"], key="vista", label_visibility="collapsed")
        agricultor = (vista or "Agricultor") == "Agricultor"
        modelo = MODELO_OFICIAL
        if not agricultor:
            modelo = c3.segmented_control("Modelo", list(MODELOS), format_func=MODELOS.get, key="modelo",
                                          label_visibility="collapsed",
                                          help="La media es la referencia oficial de T08. La mediana se propuso en el PR #23.")
            modelo = modelo or MODELO_OFICIAL
        satelite = c4.toggle("Satélite", value=True, key="satelite",
                             help="Imagen Sentinel-2 sobre el relieve. Apágalo si tu conexión es lenta.")
    return agricultor, modelo, satelite
