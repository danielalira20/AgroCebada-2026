"""Botón para descargar la ficha de una parcela en PDF (se arma al hacer clic)."""
import streamlit as st

from agrocebada_app.backend.ficha_pdf.armado import armar_ficha


@st.cache_data(show_spinner=False)
def ficha_bytes(pid, modelo, _ctx):
    """Clave de caché: parcela y modelo (el contexto no se hashea, igual que antes con las variables globales)."""
    return armar_ficha(pid, _ctx)


def boton_ficha(pid, clave, modelo, ctx):
    st.download_button("Descargar ficha (PDF)", data=lambda: ficha_bytes(pid, modelo, ctx),
                       file_name=f"ficha_{pid}.pdf", mime="application/pdf", on_click="ignore", key=clave,
                       type="primary", width="stretch", help="Una página con la cifra, el mapa, el verdor y el clima.")
