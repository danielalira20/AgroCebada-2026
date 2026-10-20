"""Piezas mínimas de HTML propio. Los textos que vienen de los datos pasan por e() antes de mostrarse."""
import html

import streamlit as st


def h(s):
    st.markdown(s, unsafe_allow_html=True)        # sólo HTML propio; los textos de datos pasan por e()


def e(s):
    return html.escape(str(s))


def chips(items):
    h("<div class='chips'>" + "".join(f"<div class='chip'><span>{e(k)}</span><b>{e(v)}</b></div>"
                                      for k, v in items) + "</div>")


def titulo(t, sub="", *, nivel=None):
    etiqueta = f"h{nivel}" if nivel in (1, 2, 3, 4, 5, 6) else "div"
    h(f"<{etiqueta} class='tit'>{e(t)}</{etiqueta}>" + (f"<div class='sub'>{e(sub)}</div>" if sub else ""))
