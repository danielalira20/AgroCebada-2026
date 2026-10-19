"""Conclusiones breves de las preguntas guía y método de evaluación bajo demanda."""
import streamlit as st

from agrocebada_app.backend.dominio.evidencia import (
    CAUTELA, MEDIANA, PREGUNTAS, REGLA, cierre_modelo_final, referencia, resumen)
from agrocebada_app.config import MODELOS
from agrocebada_app.frontend.tema.html import e, h, titulo


def introduccion(exp, oficial):
    registradas = exp[exp.estado == "registrada"]
    pasan = int(registradas.pasa_regla.astype(bool).sum())
    ref = referencia(exp)
    with st.container(key="glass_evid_intro"):
        h("<div class='eyebrow'>Evidencia del método · campaña 2025</div>")
        titulo("Las pruebas detrás del método")
        conclusion = ("Ninguna prueba registrada superó la regla de promoción." if pasan == 0 and len(registradas)
                      else f"{pasan} de {len(registradas)} pruebas registradas superaron la regla.")
        h(f"<p class='evid-conclusion'>{e(conclusion)}</p><div class='evid-contadores'>"
          f"<span><b>{len(registradas)}</b> registradas</span><span><b>{pasan}</b> pasan la regla</span>"
          f"<span><b>{int((exp.estado == 'complementaria').sum())}</b> complementarias</span></div>")
        decision = exp[(exp.tarea == "T16") & (exp.estado == "registrada")]
        if oficial == MEDIANA and not decision.empty:
            f = decision.iloc[0]
            h("<div class='evid-decision'><div><span class='evid-pill'>Decisión del método</span>"
              f"<h3>{e(MODELOS[oficial])}</h3><p>Configurada por su menor error. Es una excepción explícita "
              "a la regla, no una mejora confirmada.</p></div><div class='evid-compara'>"
              f"<div><span>Media de referencia</span><b>{f.mae_referencia:.4f}<small>t/ha</small></b></div>"
              "<span aria-hidden='true'>→</span>"
              f"<div><span>Mediana evaluada</span><b>{f.mae:.4f}<small>t/ha</small></b></div></div></div>")
        else:
            valor = f" · MAE {ref:.4f} t/ha" if ref is not None else ""
            h(f"<p class='nota'>Configuración oficial: {e(MODELOS.get(oficial, oficial))}{e(valor)}.</p>")


def preguntas(exp, oficial):
    tarjetas = []
    for n, info in PREGUNTAS.items():
        r = resumen(exp, n, oficial)
        if not r["n"]:
            respuesta = "Sin pruebas registradas"
        elif r["pasan"]:
            respuesta = f"{r['pasan']} pruebas superan la regla"
        elif r["cambio_mejor"] >= 0:
            respuesta = "Ninguna opción redujo el error"
        else:
            respuesta = "Hay menos error, sin mejora confirmada"
        tarjetas.append(f"<article class='evid-pregunta'><span class='eyebrow'>Pregunta {n}</span>"
                        f"<h3>{e(info['titulo'])}</h3><p>{e(respuesta)}</p>"
                        f"<small>{r['n']} registradas · {r['pasan']} pasan la regla</small></article>")
    h("<div class='evid-preguntas'>" + "".join(tarjetas) + "</div>")
    with st.expander("Respuestas completas y criterio de promoción", expanded=False):
        h(f"<p class='evid-texto'><b>Cómo se decide:</b> {e(REGLA)}</p>"
          "<p class='evid-texto'>Cada parcela se estima sin usar su propia cosecha, con validación cruzada 5 × 5.</p>")
        for n, info in PREGUNTAS.items():
            titulo(f"Pregunta {n} · {info['titulo']}", info["probado"])
            h(f"<p class='evid-texto'>{e(resumen(exp, n, oficial)['frase'])}</p>")
        h(f"<p class='evid-texto'>{e(cierre_modelo_final(exp, oficial))}</p>")
    h(f"<p class='evid-cautela'>{e(CAUTELA)}</p>")
