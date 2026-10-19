"""Conversación flotante: respuestas, historial por parcela, reinicio y calculadora."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

PAGINA = """
from types import SimpleNamespace
import numpy as np
import pandas as pd
import streamlit as st
from agrocebada_app.backend.dominio.confianza import confianza_municipios
from agrocebada_app.frontend.vistas.agricultor.pregunta_cebi import pregunta_cebi

d = pd.DataFrame({'municipio': ['M'] * 12,
    'CONJUNTO': ['ENTRENAMIENTO'] * 10 + ['PREDICCION'] * 2,
    'real': list(range(1, 11)) + [np.nan, np.nan], 'AREA_HA': [5.] * 12},
    index=[f'M{i}' for i in range(1, 11)] + ['P1', 'P2'])
pred = pd.DataFrame({'prediccion': [5.5, 5.5], 'fuente': ['municipio'] * 2,
    'n_municipio': [10, 10]}, index=['P1', 'P2'])
ctx = SimpleNamespace(d=d, pred=pred, modelo='mediana_mun__resp_grupo',
    conf=confianza_municipios(d, None), oof_parcela=None, C=None, S=None)
pid = st.selectbox('Parcela', ['P1', 'P2', 'M1'], key='parcela_prueba')
st.number_input('Precio', value=0., key='calc_precio')
st.number_input('Costo', value=0., key='calc_costo')
pregunta_cebi(ctx, pid)
"""


def conversacion(at):
    return next(m.value for m in at.markdown if "class='cebi-conversacion'" in m.value)


for tema in ("claro", "oscuro"):
    at = AppTest.from_string(PAGINA, default_timeout=30)
    at.session_state["tema"] = tema
    at.run()
    assert not at.exception, at.exception
    assert len(at.get("popover")) == 1 and not at.get("dialog")
    assert len([b for b in at.button if b.key.startswith("cebi_P1_")]) == 10   # 9 preguntas y «empezar de nuevo»
    assert at.button(key="cebi_P1_0").label == "Mi estimación"
    assert at.button(key="cebi_P1_0").proto.help == "¿Por qué mi parcela tiene 5.50?"
    # el compositor ya no es maqueta: hay campo de escritura de verdad y grabadora de voz
    assert at.chat_input(key="cebi_P1_texto").placeholder == "Escribe tu pregunta…"
    assert "Preguntar hablando" in [x.label for x in at.expander]
    assert not [m for m in at.markdown if "próximamente" in m.value]
    assert "Tu parcela P1 tiene una estimación de 5.50 t/ha" in conversacion(at)
    assert at.button(key="cebi_P1_borrar").disabled
    for indice in range(9):
        at.button(key=f"cebi_P1_{indice}").click().run()
        assert not at.exception, at.exception
    assert at.session_state["cebi_P1"] == list(range(9))
    assert conversacion(at).count("class='cebi-pregunta'") == 4
    assert "¿Por qué mi vecino" not in conversacion(at)
    at.button(key="cebi_P1_2").click().run()
    assert at.session_state["cebi_P1"] == [0, 1, 3, 4, 5, 6, 7, 8, 2]
    at.selectbox(key="parcela_prueba").select("P2").run()
    assert at.session_state["cebi_P2"] == []
    assert "Tu parcela P2" in conversacion(at) and "cebi-pregunta" not in conversacion(at)
    at.selectbox(key="parcela_prueba").select("P1").run()
    assert at.session_state["cebi_P1"] == [0, 1, 3, 4, 5, 6, 7, 8, 2]
    at.number_input(key="calc_precio").set_value(4000.).run()
    at.number_input(key="calc_costo").set_value(1000.).run()
    at.button(key="cebi_P1_5").click().run()        # «¿Me alcanza para mis costos?»
    assert "$110,000" in conversacion(at) and "$105,000" in conversacion(at), conversacion(at)
    at.button(key="cebi_P1_borrar").click().run()
    assert not at.exception, at.exception
    assert at.session_state["cebi_P1"] == [] and at.button(key="cebi_P1_borrar").disabled
    assert "cebi-pregunta" not in conversacion(at)
    at.selectbox(key="parcela_prueba").select("M1").run()
    assert len([b for b in at.button if b.key.startswith("cebi_M1_")]) == 8   # 7 preguntas y «empezar de nuevo»
    at.button(key="cebi_M1_0").click().run()
    assert not at.exception, at.exception
    assert "¿Cómo le fue a mi parcela" in conversacion(at)

print("OK: popover, preguntas de ambas clases de parcela, historial de cuatro turnos, aislamiento, reinicio y costos actualizados")

# --- texto libre: se enruta a una respuesta conocida, y lo que no sabe lo admite
at = AppTest.from_string(PAGINA, default_timeout=30).run()
at.chat_input(key="cebi_P1_texto").set_value("me alcanza para los gastos").run()
assert not at.exception, at.exception
turno = at.session_state["cebi_P1"][-1]
assert turno[0] == "libre" and turno[1] == "me alcanza para los gastos"
assert turno[2] is not None, "debió reconocer la pregunta de costos"
texto = conversacion(at)
assert "me alcanza para los gastos" in texto, "la burbuja muestra lo que la persona escribió, no la pregunta del botón"

at.chat_input(key="cebi_P1_texto").set_value("cuando debo sembrar").run()
assert not at.exception, at.exception
assert at.session_state["cebi_P1"][-1][2] is None, "no debe enrutar una pregunta que no sabe"
texto = conversacion(at)
assert "No entendí" in texto and "inventar" in texto, texto[-300:]
print("texto libre: enruta lo que sabe y admite lo que no, sin inventar")

# --- con conversación los botones pasan a la fila que se desliza
at = AppTest.from_string(PAGINA, default_timeout=30).run()
assert any("Explora tu parcela" in m.value for m in at.markdown)
at.button(key="cebi_P1_0").click().run()
assert any("Más preguntas" in m.value for m in at.markdown), "la etiqueta cambia al haber conversación"
print("OK")
