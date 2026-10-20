"""Guía de uso: un tour que difumina la pantalla y resalta lo que se explica (assets/js/guia.js)."""
import base64

import streamlit as st

from agrocebada_app.config import APP

_JS = (APP / "assets" / "js" / "guia.js").read_text(encoding="utf-8")
# El script va en base64: st.html sanea el HTML y se comía el código (tiene «<» y «&&»); así llega intacto.
_CARGADOR = ("(0, eval)(new TextDecoder().decode(Uint8Array.from(atob('"
             + base64.b64encode(_JS.encode("utf-8")).decode("ascii") + "'), c => c.charCodeAt(0))))")


def guia():
    """Instala el tour en la página (una sola vez por navegador). No dibuja nada en el flujo de la app."""
    st.html(f"<script>{_CARGADOR}</script>", unsafe_allow_javascript=True)
