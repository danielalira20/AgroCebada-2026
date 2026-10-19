"""¿A qué parcelas sirve?: la tabla de alcance de la cifra."""
import streamlit as st

from agrocebada_app.backend.dominio.alcance import CAUTELA, MUCHA, NO, PARCIAL, SI
from agrocebada_app.frontend.tema.html import e, h, titulo

CLASE = {SI: "val-alta", CAUTELA: "val-media", PARCIAL: "val-media", MUCHA: "val-baja", NO: "alc-no"}


def alcance(filas, modelo):
    with st.container(key="glass_alcance"):
        titulo("¿A qué parcelas sirve?", f"Para qué casos vale la cifra y para cuáles no. Errores de {modelo}.")
        if not filas:
            st.info("No hay validación para armar la tabla.")
            return
        cab = ("<div class='alc-cab'><span>¿Sirve?</span><span>Situación</span><span>Error en la validación</span>"
               "<span>De las 59</span></div>")
        cuerpo = "".join(
            f"<article class='alc-fila'><div><span class='val-confianza {CLASE[f['sirve']]}'>{e(f['sirve'])}</span></div>"
            f"<div><p>{e(f['situacion'])}</p><small>{e(f['nota'])}</small></div><p>{e(f['error'])}</p>"
            f"<p class='alc-cuantas'>{e(f['estimaciones'])}</p></article>" for f in filas)
        h(f"<div class='alc'>{cab}{cuerpo}</div>")
        h("<p class='nota'>Los umbrales son los de la regla de confianza (pestaña Validación). «De las 59» cuenta las "
          "estimaciones por municipio; la confianza de cada una puede ser menor si su error en la validación fue mayor.</p>")
