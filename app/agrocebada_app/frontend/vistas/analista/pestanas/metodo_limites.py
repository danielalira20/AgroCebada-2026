"""Pestaña «Método y límites»: cómo se calcula, qué tan bien funciona, a qué parcelas sirve y límites.
Las cifras y los textos salen de backend/dominio/alcance.py; aquí sólo se dibujan."""
import streamlit as st

from agrocebada_app.backend.dominio.alcance import (
    error_principal, limites as lista_limites, pasos as lista_pasos, por_que_simple, tabla_alcance)
from agrocebada_app.config import MODELO_OFICIAL, MODELOS
from agrocebada_app.frontend.componentes.metodo.alcance import alcance
from agrocebada_app.frontend.componentes.metodo.limites import limites
from agrocebada_app.frontend.componentes.metodo.pasos import pasos
from agrocebada_app.frontend.componentes.metodo.resultados import fuentes, resultados


def metodo_limites(ctx):
    with st.container(key="metodo"):
        pasos(lista_pasos(ctx.d, MODELO_OFICIAL))
        r1, r2 = st.columns([3, 2])
        with r1:
            resultados(error_principal(ctx.O), por_que_simple(MODELO_OFICIAL), MODELOS[ctx.modelo])
        with r2:
            fuentes()
        alcance(tabla_alcance(ctx.O, ctx.conf, ctx.pred), MODELOS[ctx.modelo])
        limites(lista_limites())
