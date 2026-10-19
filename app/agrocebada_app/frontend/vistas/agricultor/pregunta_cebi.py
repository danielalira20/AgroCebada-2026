"""«Pregúntale a Cebi» en la vista del agricultor (M19): una tarjeta chica que abre una ventana con preguntas fijas
y respuestas en burbujas. Sin campo de texto libre: Cebi sólo contesta lo que sabe. La plática se guarda mientras se
use la página y empieza de nuevo al cambiar de parcela."""
import streamlit as st

from agrocebada_app.backend.dominio.respuestas import respuestas, saludo
from agrocebada_app.frontend.estado.cache import clima_normal
from agrocebada_app.frontend.tema.estilos import MASCOTA
from agrocebada_app.frontend.tema.html import e, h

_TU = ("<div style='display:flex;justify-content:flex-end;margin:10px 0'>"
       "<div style='max-width:75%;padding:8px 12px;border-radius:14px 14px 4px 14px;font-size:.9rem;"
       "background:#9BE15D;color:#10200F;font-weight:500'>{}</div></div>")
_CEBI = ("<div class='mascota' style='margin:10px 0'><div class='cebi'>{}</div>"
         "<div style='max-width:75%;padding:8px 12px;border-radius:14px 14px 14px 4px;font-size:.9rem;"
         "background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.14);color:#E8EEE9'>{}</div></div>")


@st.dialog("Pregúntale a Cebi", width="large")
def _platica(ctx, pid):
    lista = respuestas(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid, oof=ctx.oof_parcela,
                       precio=st.session_state.get("calc_precio"), costo=st.session_state.get("calc_costo"),
                       area=st.session_state.get(f"calc_area_{pid}"), clima=ctx.C, normal=clima_normal())
    clave = f"cebi_{pid}"
    hechas = st.session_state.setdefault(clave, [])
    h("<div class='nota'>Elige una pregunta y Cebi te contesta con los datos de tu parcela.</div>")
    cols = st.columns(2)
    for i, (pregunta, _) in enumerate(lista):
        if cols[i % 2].button(pregunta, key=f"{clave}_{i}", width="stretch"):
            if i in hechas:          # si ya la había preguntado, la mueve al final en vez de repetirla
                hechas.remove(i)
            hechas.append(i)
    burbujas = [_CEBI.format(MASCOTA, e(saludo(ctx.d, ctx.pred, ctx.modelo, ctx.conf, pid)))]
    for i in hechas[-4:]:                         # las últimas cuatro preguntas
        pregunta, respuesta = lista[i]
        burbujas += [_TU.format(e(pregunta)), _CEBI.format(MASCOTA, e(respuesta))]
    h("".join(burbujas))
    if hechas and st.button("Empezar de nuevo", key=f"{clave}_borrar"):
        hechas.clear()
        st.rerun(scope="fragment")


def pregunta_cebi(ctx, pid):
    """Tarjeta chica en la página; el botón abre la ventana con la plática."""
    h("<style>.st-key-glass_cebi button, .st-key-glass_cebi button p {color:#10200F !important;"
        "font-weight:600}</style>")
    with st.container(key="glass_cebi"):
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        with c1:
            h(f"<div class='mascota'><div class='cebi'>{MASCOTA}</div><div><div class='tit'>¿Tienes dudas sobre tu "
              "parcela?</div><div class='nota' style='margin-top:4px'>Cebi te contesta con los datos de tu parcela: "
              "por qué tiene ese número, qué tanto confiar, si te alcanza para tus costos y más.</div></div></div>")
        with c2:
            if st.button("Pregúntale a Cebi", key=f"abrir_cebi_{pid}", type="primary", width="stretch"):
                _platica(ctx, pid)