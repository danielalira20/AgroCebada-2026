"""Selección de parcela en la vista del analista."""
import streamlit as st

from agrocebada_app.frontend.componentes.mapa.interaccion import parcela_clicada


def ids_filtrados(d, capa, municipio):
    """IDs de la combinación elegida, sin sustituir conjuntos cuando no hay coincidencias."""
    return [i for i in d.index if (municipio == "Todos" or d.loc[i, "municipio"] == municipio) and not (
        (capa == "Las 59" and d.loc[i, "CONJUNTO"] != "PREDICCION") or
        (capa == "Las 138" and d.loc[i, "CONJUNTO"] == "PREDICCION"))]


def validar_filtros(d):
    """Acepta filtros con resultados o restaura la última combinación válida antes de dibujar los controles."""
    capa = st.session_state.get("capa") or "Todas"
    municipio = st.session_state.get("municipio_an", "Todos")
    if ids_filtrados(d, capa, municipio):
        st.session_state["capa"] = capa
        st.session_state["municipio_an"] = municipio
        st.session_state["filtros_an_validos"] = (capa, municipio)
        return
    anterior = st.session_state.get("filtros_an_validos", ("Todas", "Todos"))
    st.session_state["capa"], st.session_state["municipio_an"] = anterior
    tipo = {"Las 59": "parcelas por estimar", "Las 138": "parcelas con cosecha registrada", "Todas": "parcelas"}[capa]
    lugar = f"en {municipio}" if municipio != "Todos" else "con los filtros seleccionados"
    st.session_state["aviso_filtros_an"] = f"No hay {tipo} {lugar}. Se conservó el filtro anterior."


def clic_analista(clave, d):
    pid = parcela_clicada(clave)
    if pid in d.index:
        st.session_state["buscar_id"] = pid
