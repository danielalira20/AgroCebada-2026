"""Introducción y tarjetas de las tres preguntas guía."""
import streamlit as st

from agrocebada_app.backend.dominio.evidencia import (
    CAUTELA, PREGUNTAS, REGLA, cierre_modelo_final, resumen, tabla)
from agrocebada_app.frontend.tema.html import e, h, titulo

COLUMNAS = {"prueba": "Prueba", "mae": "MAE (t/ha)", "cambio": "Cambio (t/ha)", "repeticiones": "Repeticiones que mejoran",
            "resultado": "Resultado"}
FORMATOS = {"MAE (t/ha)": st.column_config.NumberColumn(format="%.4f"),
            "Cambio (t/ha)": st.column_config.NumberColumn(format="%+.4f")}


def introduccion(referencia, ajuste):
    with st.container(key="glass_evid_intro"):
        titulo("Lo que se probó antes de elegir el método", "Las tres preguntas guía del reto y las pruebas que las responden.")
        pob = f"{ajuste['parcelas']} parcelas con cosecha, " if ajuste else ""
        h(f"<p class='evid-texto'>Cada prueba se evaluó con las cosechas de 2025: {e(pob)}cada una se estimó sin usar su "
          f"propia cosecha, repitiendo la validación 5 × 5. La referencia es el promedio del municipio (error medio de "
          f"{referencia:.4f} t/ha). «Cambio» es cuánto sube (+) o baja (−) ese error: negativo es mejor.</p>")
        h(f"<p class='nota'>{e(REGLA)} Una prueba que no la pasa no se promovió: eso no quiere decir que el dato no "
          f"aporte nada, sólo que no mejoró lo suficiente con estas parcelas.</p>")


def _compacta(exp, n, oficial):
    t = tabla(exp, n, oficial)[list(COLUMNAS)].rename(columns=COLUMNAS)
    st.dataframe(t, hide_index=True, width="stretch", height=min(35 * (len(t) + 1) + 3, 460), column_config=FORMATOS)
    return t


def pregunta(exp, n, oficial):
    info, r = PREGUNTAS[n], resumen(exp, n, oficial)
    with st.container(key=f"glass_evid_p{n}"):
        titulo(f"Pregunta {n} · {info['titulo']}", info["probado"])
        h(f"<p class='evid-resp'>{e(r['frase'])}</p>")
        _compacta(exp, n, oficial)
        if (exp[exp.pregunta == n].estado == "complementaria").any():
            h("<p class='nota'>Las pruebas complementarias se hicieron después de conocer los resultados, sin registro "
              "formal ni intervalo; no cuentan para la regla (docs/t16_procedimiento_final.md §8).</p>")
        if n == 3:
            h(f"<p class='evid-resp'>{e(cierre_modelo_final(exp, oficial))}</p>")
        if n == 3 or r["pasan"] == 0:
            h(f"<p class='nota'>{e(CAUTELA)}</p>")
