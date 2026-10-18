"""Lectura del clic del usuario sobre el mapa."""
import streamlit as st


def parcela_clicada(clave):
    """ID de la parcela que se acaba de clicar en el mapa `clave`, o None."""
    try:
        objetos = st.session_state[clave].selection.objects.get("parcelas") or []
        return objetos[0]["id"] if objetos else None
    except (KeyError, AttributeError, TypeError, IndexError):
        return None
