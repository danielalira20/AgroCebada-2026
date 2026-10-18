"""Botón para descargar la ficha de una parcela en PDF (se arma al hacer clic)."""
import streamlit as st

from agrocebada_app.backend.ficha_pdf.armado import armar_ficha


@st.cache_data(show_spinner=False)
def ficha_bytes(pid, modelo, _ctx, confianza=None, calculadora=None):
    """Clave de caché: parcela, modelo y lo opcional (el contexto no se hashea, igual que antes con las variables
    globales). `confianza` (M01) y `calculadora` (M05) son opcionales: sin ellos la ficha sale igual que siempre."""
    return armar_ficha(pid, _ctx, modelo, confianza, calculadora)


def boton_ficha(pid, clave, modelo, ctx, confianza=None, calculadora=None):
    st.download_button("Descargar ficha (PDF)", data=lambda: ficha_bytes(pid, modelo, ctx, confianza, calculadora),
                       file_name=f"ficha_{pid}.pdf", mime="application/pdf", on_click="ignore", key=clave,
                       type="primary", width="stretch", help="Una página con la cifra, el rango de su municipio, el mapa, el verdor y el clima.")
