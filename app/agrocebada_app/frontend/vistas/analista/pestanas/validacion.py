"""Pestaña «Validación»: métricas por población, confianza por municipio, dispersión e información insuficiente.
Las cifras y los textos salen de backend/dominio/validacion.py; aquí sólo se dibujan."""
import streamlit as st

from agrocebada_app.backend.dominio.validacion import (
    bloques_respaldo, comparacion_oculto, contraste_respaldo, poblaciones, por_municipio,
    regla_confianza)
from agrocebada_app.backend.modelo.estimador import predecir
from agrocebada_app.config import MODELOS
from agrocebada_app.frontend.componentes.graficas.dispersion_validacion import dispersion
from agrocebada_app.frontend.componentes.validacion.resultados import resultados
from agrocebada_app.frontend.componentes.validacion.municipios import municipios, reglas_confianza
from agrocebada_app.frontend.componentes.validacion.simulacion import comparacion
from agrocebada_app.frontend.tema.html import titulo


def _insuficiente(ctx):
    """Oculta un municipio y muestra qué valor y qué confianza tendría la estimación sin sus datos."""
    pred = ctx.pred
    with st.container(key="glass_insuf"):
        titulo("¿Y si no hubiera datos de tu municipio?", "Oculta sus cosechas para ver de dónde saldría la estimación.")
        if pred.empty:
            st.info("No hay parcelas por estimar para simular este caso.")
            return
        oculto = st.selectbox("Municipio a ocultar", sorted(pred.municipio.unique()), key="val_municipio_oculto")
        sim = predecir(ctx.d, ctx.modelo, ocultar=oculto)
        tabla, motivo = comparacion_oculto(pred, sim, ctx.conf, oculto)
        comparacion(tabla, pred.loc[tabla.index], sim.loc[tabla.index],
                    bloques_respaldo(contraste_respaldo(ctx.O, pred)), motivo)


def validacion(ctx):
    if ctx.O is None or ctx.OA is None or ctx.OA.empty:
        st.info("No se encontraron los resultados de validación del modelo.")
        return
    with st.container(key="validacion"):
        resultados(poblaciones(ctx.O), MODELOS[ctx.modelo])
        municipios(por_municipio(ctx.conf, ctx.cob_mun))
        with st.container(key="val_regla_grafica"):
            v1, v2 = st.columns([2, 3])
            with v1:
                mae_general = float(ctx.conf.mae_general.iloc[0]) if len(ctx.conf) else float("nan")
                reglas_confianza(regla_confianza(mae_general))
            with v2:
                dispersion(ctx)
        _insuficiente(ctx)
