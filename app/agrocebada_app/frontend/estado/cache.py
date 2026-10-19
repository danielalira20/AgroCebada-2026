"""Lecturas de datos con caché de Streamlit (se leen una vez por sesión de servidor)."""
import streamlit as st

from agrocebada_app.backend.datos import elevacion, paquete


@st.cache_data(show_spinner="Leyendo parcelas…")
def cargar():
    return paquete.parcelas()


@st.cache_data
def elevaciones():
    return elevacion.elevaciones()


@st.cache_data(show_spinner="Leyendo series de satélite…")
def series():
    return paquete.series()


@st.cache_data
def clima():
    return paquete.clima()

@st.cache_data
def clima_normal():
    return paquete.clima_normal()

@st.cache_data
def soporte():
    return paquete.soporte()

@st.cache_data
def calidad():
    return paquete.calidad()

@st.cache_data
def oficial(modelo):
    return paquete.oficial(modelo)


@st.cache_data
def oof(modelo, municipios):
    return paquete.validacion(modelo, municipios)
