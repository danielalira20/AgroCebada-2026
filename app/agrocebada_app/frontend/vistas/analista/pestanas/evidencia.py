"""Pestaña «Evidencia»: las tres preguntas guía, la tabla de pruebas y lo que se aprendió.
Las cifras y los textos salen de backend/dominio/evidencia.py; aquí sólo se dibujan."""
import streamlit as st

from agrocebada_app.backend.datos.experimentos import experimentos
from agrocebada_app.backend.dominio.evidencia import ajuste_final
from agrocebada_app.config import MODELO_OFICIAL
from agrocebada_app.frontend.componentes.evidencia.aprendizaje import aprendizaje
from agrocebada_app.frontend.componentes.evidencia.preguntas import introduccion, preguntas
from agrocebada_app.frontend.componentes.evidencia.tabla import explorador, tabla_completa


def evidencia(ctx):
    exp = experimentos()
    if exp is None or exp.empty:
        st.info("No se encontró la tabla de pruebas.")
        return
    with st.container(key="evidencia"):
        introduccion(exp, MODELO_OFICIAL)
        preguntas(exp, MODELO_OFICIAL)
        explorador(exp, MODELO_OFICIAL)
        aprendizaje(ctx, ajuste_final(ctx.O, ctx.modelo))
        tabla_completa(exp, MODELO_OFICIAL)
