"""Verdor y clima de la parcela elegida, como contexto: no entran en el cálculo de la estimación.
Un solo recuadro con dos tarjetas internas (verdor y clima) y, plegadas abajo, sus dos gráficas."""
import streamlit as st

from agrocebada_app.backend.dominio.clima_anomalia import comparar, frases
from agrocebada_app.backend.dominio.franja_verdor import frase_verdor
from agrocebada_app.frontend.componentes.graficas.clima import curva_clima, curva_clima_normal
from agrocebada_app.frontend.componentes.graficas.indices import curva_franja
from agrocebada_app.frontend.estado.cache import clima_normal
from agrocebada_app.frontend.tema.html import e, h, titulo

CONTEXTO = "Es contexto: no entra en el cálculo de la estimación."
ZONA = "la zona de unos 5 km alrededor de tu parcela"

_TARJETA = ("flex:1 1 300px;background:var(--vidrio);border:1px solid var(--borde);"
            "border-radius:14px;padding:14px 16px")


def _tarjeta(nombre, detalle, lineas):
    """Una tarjeta interna: nombre, explicación corta y el resumen con barra verde."""
    cuerpo = "<br>".join(e(x) for x in lineas)
    return (f"<div style='{_TARJETA}'>"
            f"<div style='font-weight:600;font-size:1rem'>{e(nombre)}</div>"
            f"<div class='nota' style='margin:2px 0 10px'>{e(detalle)}</div>"
            "<div style='border-left:3px solid var(--acento);padding:2px 0 2px 12px;font-size:.95rem;line-height:1.6;"
            f"color:var(--texto)'>{cuerpo}</div></div>")


def _lineas_clima(C, t):
    if C is None:
        return "En " + ZONA + ".", ["No hay información de lluvia y temperatura disponible para esta parcela."]
    if t is None:
        return f"Promedio mensual de {ZONA}.", ["Abre las gráficas para ver la lluvia y la temperatura de 2025."]
    return (f"En {ZONA}, contra el promedio 2022–2024.",
            frases(t) or ["La lluvia y la temperatura de 2025 quedaron cerca del promedio 2022–2024 en tu zona."])


def verdor_clima(ctx, pid):
    d, S, C = ctx.d, ctx.S, ctx.C
    t = comparar(C, clima_normal(), pid) if C is not None else None
    with st.container(key="glass_temporada"):
        titulo("Verdor y clima de 2025", f"Verdor de tu parcela y clima de tu zona en 2025. {CONTEXTO} "
               "Describe lo que pasó; no pronostica la cosecha.")

        # 1) dos tarjetas internas, siempre a la misma altura
        detalle_clima, lineas_clima = _lineas_clima(C, t)
        h("<div style='display:flex;flex-wrap:wrap;gap:14px;align-items:stretch;margin:6px 0 12px'>"
          + _tarjeta("Verdor", "Sube cuando el cultivo crece y baja al madurar o cosechar.",
                     [frase_verdor(d, S, pid)])
          + _tarjeta("Lluvia y temperatura", detalle_clima, lineas_clima)
          + "</div>")

        # 2) las dos gráficas, plegadas, cada una en su tarjeta
        with st.expander("Ver las gráficas"):
            g1, g2 = st.columns(2, gap="medium")
            with g1, st.container(border=True):
                h("<div style='font-weight:600;font-size:.95rem'>Verdor</div>")
                r = curva_franja(S, d, pid, alto=320)
                if r is not None:
                    _, hay_franja = r
                    nota = ("La línea verde es tu parcela. La franja gris marca los valores más comunes entre las "
                            "parcelas con cosecha de tu municipio, semana a semana." if hay_franja else
                            "La línea verde es tu parcela. Tu municipio tiene muy pocas parcelas con cosecha para "
                            "compararla.")
                    h(f"<div class='nota'>{nota}</div>")
            with g2, st.container(border=True):
                h("<div style='font-weight:600;font-size:.95rem'>Lluvia y temperatura</div>")
                if t is not None:
                    curva_clima_normal(t, alto=160)
                    h("<div class='nota'>La raya clara y la línea punteada son el promedio 2022–2024.</div>")
                elif C is not None:
                    curva_clima(C, pid)
