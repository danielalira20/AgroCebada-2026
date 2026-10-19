"""Pestaña «Evidencia»: las tres preguntas guía, la tabla de pruebas y lo que se aprendió.
Las cifras y los textos salen de backend/dominio/evidencia.py; aquí sólo se dibujan."""
import streamlit as st

from agrocebada_app.backend.datos.experimentos import experimentos
from agrocebada_app.backend.dominio.evidencia import PREGUNTAS, ajuste_final, referencia
from agrocebada_app.config import MODELO_OFICIAL
from agrocebada_app.frontend.componentes.evidencia.aprendizaje import aprendizaje
from agrocebada_app.frontend.componentes.evidencia.preguntas import introduccion, pregunta
from agrocebada_app.frontend.componentes.evidencia.tabla import tabla_completa


def evidencia(ctx):
    exp = experimentos()
    if exp is None:
        st.info("No se encontró la tabla de pruebas.")
        return
    with st.container(key="evidencia"):
        introduccion(referencia(exp), ajuste_final(ctx.O, ctx.modelo))
        for n in PREGUNTAS:
            pregunta(exp, n, MODELO_OFICIAL)
        tabla_completa(exp, MODELO_OFICIAL)
        aprendizaje(ctx, ajuste_final(ctx.O, ctx.modelo))
