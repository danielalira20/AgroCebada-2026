"""Selección de parcela en la vista del agricultor."""
import streamlit as st

from agrocebada_app.frontend.componentes.mapa.interaccion import parcela_clicada


def clic_agricultor(clave, d):
    pid = parcela_clicada(clave)
    if pid in d.index:                  # se cambia la parcela elegida, no el encuadre del mapa
        st.session_state["agri_muni"], st.session_state["agri_parcela"] = d.loc[pid, "municipio"], pid


def primera_reservada(d, muni):
    ids = sorted(d.index[d.municipio == muni])
    res = [i for i in ids if d.loc[i, "CONJUNTO"] == "PREDICCION"]
    return res[0] if res else ids[0]
