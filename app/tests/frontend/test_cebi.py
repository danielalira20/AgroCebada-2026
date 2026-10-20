"""Conversación flotante: respuestas, historial por parcela, reinicio y calculadora."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.dominio import transcribir as voz

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


def rotulo(at):
    return next(m.value for m in at.markdown if "class='cebi-sugerencias" in m.value)


def tema(at, pid, cual="parcela"):
    """El primer toque: Cebi pregunta de qué se quiere hablar y, al escoger, salen las preguntas de ese tema."""
    at.button(key=f"cebi_{pid}_t_{cual}").click().run()
    assert not at.exception, at.exception


for tema in ("claro", "oscuro"):
    at = AppTest.from_string(PAGINA, default_timeout=30)
    at.session_state["tema"] = tema
    at.run()
    assert not at.exception, at.exception
    assert len(at.get("popover")) == 1 and not at.get("dialog")
    # al empezar sólo hay dos pastillas (de qué quieres hablar), no las doce preguntas
    assert sorted(b.key for b in at.button if b.key.startswith("cebi_P1_")) == [
        "cebi_P1_borrar", "cebi_P1_cambiar", "cebi_P1_t_cuenta", "cebi_P1_t_parcela"]
    assert at.button(key="cebi_P1_t_parcela").label == "Mi parcela" and at.button(key="cebi_P1_t_cuenta").label == "Mi cuenta"
    assert "¿Qué quieres explorar?" in rotulo(at) and at.button(key="cebi_P1_cambiar").disabled
    tema(at, "P1")
    assert "Explora tu parcela" in rotulo(at) and not at.button(key="cebi_P1_cambiar").disabled
    assert len([b for b in at.button if b.key.startswith("cebi_P1_")]) == 11   # 9 preguntas, «cambiar de tema» y «empezar de nuevo»
    assert at.button(key="cebi_P1_0").label == "Mi estimación"
    assert at.button(key="cebi_P1_0").proto.help == "¿Por qué mi parcela tiene 5.50?"
    # el compositor ya no es maqueta: hay campo de escritura de verdad y, junto a él, el micrófono
    assert at.chat_input(key="cebi_P1_texto").placeholder == "Escribe tu pregunta…"
    assert not [x for x in at.expander if "hablando" in x.label], "el micrófono no se esconde en un expander"
    assert len(at.get("audio_input")) == (1 if voz.disponible() else 0)
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
    assert at.button(key="cebi_P2_t_parcela").label == "Mi parcela", "cada parcela empieza preguntando el tema"
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
    assert at.button(key="cebi_P1_t_parcela").label == "Mi parcela", "empezar de nuevo vuelve a preguntar el tema"
    at.selectbox(key="parcela_prueba").select("M1").run()
    tema(at, "M1")
    assert len([b for b in at.button if b.key.startswith("cebi_M1_")]) == 9   # 7 preguntas, «cambiar de tema» y «empezar de nuevo»
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

# --- la ✕ cierra sin borrar: Streamlit no deja cerrar un popover desde Python, así que se le cambia la llave y
# vuelve a nacer cerrado; lo que se preguntó vive en la sesión, no en el popover, y sigue ahí al reabrir
at = AppTest.from_string(PAGINA, default_timeout=30).run()
assert at.button(key="cebi_cerrar_chat").label == "✕"
tema(at, "P1")
at.button(key="cebi_P1_0").click().run()
historial = list(at.session_state["cebi_P1"])
at.button(key="cebi_cerrar_chat").click().run()
assert not at.exception, at.exception
assert at.session_state["cebi_vuelta"] == 1, "la llave del popover tiene que cambiar para que se cierre"
assert at.session_state["cebi_P1"] == historial, "cerrar no borra la conversación"
assert len(at.get("popover")) == 1, "el acceso a Cebi sigue ahí"
at.button(key="cebi_cerrar_chat").click().run()
assert at.session_state["cebi_vuelta"] == 2 and at.session_state["cebi_P1"] == historial
print("la ✕ cierra la conversación y no se la lleva")

# --- con conversación los botones pasan a la fila que se desliza
at = AppTest.from_string(PAGINA, default_timeout=30).run()
assert "¿Qué quieres explorar?" in rotulo(at)
tema(at, "P1")
assert "Explora tu parcela" in rotulo(at)
at.button(key="cebi_P1_0").click().run()
assert "Más preguntas" in rotulo(at), "la etiqueta cambia al haber conversación"
print("inicio de dos pastillas y paso a la fila que se desliza")

# --- «Mi cuenta»: tres preguntas que salen de la misma cuenta que la calculadora «¿Me alcanza?»
at = AppTest.from_string(PAGINA, default_timeout=30).run()
tema(at, "P1", "cuenta")
assert "Tu cuenta" in rotulo(at) and not at.button(key="cebi_P1_cambiar").disabled
assert [b.label for b in at.button if b.key.startswith("cebi_P1_c")] == ["Mi equilibrio", "Año bajo o alto", "Si no alcanza"]
assert not [b for b in at.button if b.key in ("cebi_P1_0", "cebi_P1_t_parcela")], "no se mezclan los dos temas"
at.button(key="cebi_P1_c0").click().run()      # sin precio ni costo no inventa nada
assert "Escribe tu precio por tonelada y tu costo por hectárea" in conversacion(at), conversacion(at)
assert at.session_state["cebi_P1"] == [-3], "las de la cuenta se guardan contadas desde el final"
at.number_input(key="calc_precio").set_value(6000.).run()
at.number_input(key="calc_costo").set_value(18000.).run()      # 5 ha × $18,000 = $90,000 contra 27.5 t × $6,000
at.button(key="cebi_P1_c0").click().run()
assert "necesitas al menos 3.00 t/ha" in conversacion(at) and "queda por encima de ese punto" in conversacion(at)
at.button(key="cebi_P1_c1").click().run()
assert "un rendimiento bajo de tu municipio (1.90 t/ha) te faltarían $33,000." in conversacion(at), conversacion(at)
at.button(key="cebi_P1_c2").click().run()
assert "Anota el faltante calculado" in conversacion(at) and "no garantiza apoyos" in conversacion(at)
assert at.session_state["cebi_P1"] == [-3, -2, -1]
# cambiar de tema no borra lo hablado y vuelve a ofrecer los dos temas
historial = list(at.session_state["cebi_P1"])
at.button(key="cebi_P1_cambiar").click().run()
assert not at.exception, at.exception
assert at.session_state["cebi_P1"] == historial and at.button(key="cebi_P1_t_parcela").label == "Mi parcela"
assert "¿Qué quieres explorar?" in rotulo(at) and at.button(key="cebi_P1_cambiar").disabled
# escribir sin escoger tema también llega a «Mi cuenta»
at.chat_input(key="cebi_P1_texto").set_value("que pasa si el año sale bajo").run()
assert not at.exception, at.exception
assert at.session_state["cebi_P1"][-1] == ("libre", "que pasa si el año sale bajo", -2)
assert "un rendimiento bajo de tu municipio" in conversacion(at)
print("Mi cuenta: tres preguntas, misma cuenta que la calculadora, historial estable y texto libre")
print("OK")
