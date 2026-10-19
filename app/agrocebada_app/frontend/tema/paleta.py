"""Paleta de pantalla por sesión. Los colores del mapa y del PDF son independientes."""
import streamlit as st


def es_oscuro():
    return st.session_state.get("tema", "claro") == "oscuro"


def color(claro, oscuro):
    return oscuro if es_oscuro() else claro


def alternar_tema():
    st.session_state["tema"] = "claro" if es_oscuro() else "oscuro"


def color_grafica(valor, tema=None):
    """Equivalentes legibles de los colores originales sobre superficies claras."""
    if (tema or st.session_state.get("tema", "claro")) == "oscuro":
        return valor
    return {
        "#9be15d": "#397523", "#5ed1e8": "#087b94", "#f5b544": "#a15b08",
        "#7fb2ff": "#346dc1", "#e8eee9": "#284c3a", "#b4c5ba": "#758c80",
        "#ff7a45": "#bd4b24", "#95b6c8": "#426d83", "#c5a8eb": "#8053a4",
        "#59dcb1": "#167657", "#d8e3dc": "#3c5849", "#f5d08a": "#965e13",
        "#2fe0a0": "#167657", "#c59bff": "#8053a4", "#f2e86d": "#82720c", "#ff9ec4": "#a53b68",
        "rgba(255,255,255,0.35)": "#6e8275",
    }.get(valor.lower(), valor)
