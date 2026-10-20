"""Consulta municipal sin identificar una parcela ni mostrar contexto de otra ubicación."""
from math import isfinite

import streamlit as st

from agrocebada_app.backend.dominio.confianza import confianza_parcela
from agrocebada_app.backend.dominio.planeador import estimacion_municipio, municipios_disponibles
from agrocebada_app.frontend.estado.planeador import guardar_entrada, preparar_area, preparar_municipio
from agrocebada_app.frontend.tema.html import e, h, titulo
from agrocebada_app.frontend.vistas.agricultor.calculadora import calculadora_base

_ICONO = {"alta": "✔", "media": "▲", "baja": "⚠"}


def consulta_rapida(ctx):
    with st.container(key="glass_consulta_rapida"):
        titulo("Consulta rápida", "Compara tus cuentas con una referencia de tu municipio, sin elegir una parcela.")
        h("<p class='rapida-contexto'>La consulta cubre únicamente los municipios disponibles en este catálogo. "
          "Si tu municipio no aparece, aún no contamos con una referencia local.</p>")
        try:
            opciones = municipios_disponibles(ctx.d)
        except ValueError as exc:
            st.error(str(exc))
            return
        preparar_municipio(st.session_state, opciones)
        if not opciones:
            st.info("Aún no hay municipios con cosechas registradas para esta consulta.")
            return
        preparar_area(st.session_state, "calc_area_rapida", None)
        c1, c2 = st.columns(2)
        municipio = c1.selectbox("Municipio de la consulta", opciones, index=None,
                                 placeholder="Elige tu municipio", key="calc_municipio_rapido",
                                 on_change=guardar_entrada,
                                 args=(st.session_state, "calc_municipio_rapido", "municipio_rapido"))
        area = c2.number_input("Superficie de la consulta (ha)", min_value=0.01, value=None, step=0.5,
                               placeholder="tus hectáreas", key="calc_area_rapida", on_change=guardar_entrada,
                               args=(st.session_state, "calc_area_rapida", "area_rapida_ha"))
        if municipio is None:
            st.info("Elige un municipio para ver su referencia histórica.")
            return
        referencia = estimacion_municipio(ctx.d, municipio, ctx.modelo)
        if referencia["estado"] != "disponible":
            st.info("No hay cosechas registradas suficientes para una referencia local en este municipio.")
            return

    rendimiento = referencia["rendimiento_t_ha"]
    confianza = confianza_parcela(ctx.conf, municipio, referencia["fuente"])
    produccion = rendimiento * area if area is not None and isfinite(area) and area >= 0.01 else None
    if produccion is not None and not isfinite(produccion):
        produccion = None
        st.warning("La superficie es demasiado grande para calcular una producción finita.")
    con_area = (f"<div class='rapida-produccion'><span>Producción de referencia en {area:.2f} ha</span>"
                f"<strong>{produccion:,.2f} t</strong></div>" if produccion is not None else
                "<p class='rapida-contexto'>Escribe una superficie válida para ver las toneladas en esa área.</p>")
    with st.container(key="glass_referencia_rapida"):
        titulo(f"Referencia de {municipio}")
        h("<section class='rapida-resumen' aria-label='Referencia histórica municipal'>"
          f"<div><p class='rapida-contexto'>Parcelas con cosecha de {referencia['campania_base']}</p>"
          f"<p class='rapida-cifra'>{rendimiento:.2f}<span>t/ha</span></p>{con_area}</div>"
          f"<div class='rapida-soporte'><p>Basada en {referencia['n_cosecha_municipio']} cosechas registradas "
          f"en {e(municipio)}.</p><p><b>{_ICONO[confianza['nivel']]} Confianza {e(confianza['nivel'])}</b></p>"
          f"<p>{e(confianza['motivo'])}</p></div></section>"
          "<p class='rapida-contexto'>Es una referencia histórica del municipio, no una predicción de tu parcela "
          "ni una garantía de cosecha. La superficie sólo se usa para calcular toneladas y tus cuentas.</p>")

    calculadora_base(ctx, municipio, rendimiento, "Referencia del municipio", area, "calc_area_rapida",
                     area_editable=False)
