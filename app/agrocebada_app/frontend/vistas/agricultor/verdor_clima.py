"""Verdor y clima de la parcela elegida, como contexto: no entran en el cálculo de la estimación."""
import streamlit as st

from agrocebada_app.backend.dominio.clima_anomalia import comparar, frases
from agrocebada_app.frontend.componentes.graficas.clima import curva_clima, curva_clima_normal
from agrocebada_app.frontend.componentes.graficas.indices import curva_franja
from agrocebada_app.frontend.estado.cache import clima_normal
from agrocebada_app.frontend.tema.html import h, titulo

CONTEXTO = "Es contexto: no entra en el cálculo de la estimación."


def verdor_clima(ctx, pid):
    d, S, C = ctx.d, ctx.S, ctx.C
    g1, g2 = st.columns(2)
    with g1, st.container(key="glass_ndvi"):
        titulo("Tu parcela comparada con las de tu municipio",
               "Verdor (NDVI): sube cuando el cultivo crece y baja al madurar o cosechar.")
        r = curva_franja(S, d, pid)
        if r is not None:
            sensor, hay_franja = r
            if hay_franja:
                nota = ("La línea verde es tu parcela. La franja gris marca los valores más comunes entre las "
                        "parcelas con cosecha de tu municipio, semana a semana.")
            else:
                nota = ("La línea verde es tu parcela. Tu municipio tiene muy pocas parcelas con cosecha para "
                        "compararla.")
            h(f"<div class='nota'>{nota} {CONTEXTO}</div>")
    with g2, st.container(key="glass_clima"):
        if C is None:
            titulo("Lluvia y temperatura", f"Promedio mensual de la zona de unos 5 km alrededor de tu parcela. {CONTEXTO}")
            st.info("No hay información de lluvia y temperatura disponible para esta parcela.")
            return
        t = comparar(C, clima_normal(), pid)
        if t is None:
            # sin el promedio 2022–2024 (paquete viejo o sin T04): la gráfica de siempre
            titulo("Lluvia y temperatura", f"Promedio mensual de la zona de unos 5 km alrededor de tu parcela. {CONTEXTO}")
            curva_clima(C, pid)
            return
        titulo("¿Cómo fue el clima de 2025?",
                f"La zona de unos 5 km alrededor de tu parcela, contra el promedio 2022–2024. {CONTEXTO}")
        curva_clima_normal(t, alto=160)
        lista = frases(t) or ["La lluvia y la temperatura de 2025 quedaron cerca del promedio 2022–2024 en tu zona."]
        h("<div class='nota'>La raya clara y la línea punteada son el promedio 2022–2024.<br>"
          + "<br>".join(f"• {f}" for f in lista) + "</div>")
