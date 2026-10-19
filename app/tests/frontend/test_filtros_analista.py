"""Filtros sin coincidencias: python tests/frontend/test_filtros_analista.py (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest


def pantalla():
    from unittest.mock import patch

    import streamlit as st

    from agrocebada_app.backend.datos import paquete
    from agrocebada_app.config import MODELO_OFICIAL
    from agrocebada_app.frontend.estado.contexto import calcular
    from agrocebada_app.frontend.estado.sesion import iniciar_sesion
    from agrocebada_app.frontend.vistas.analista import vista

    d = paquete.parcelas()
    ctx = calcular(d, paquete.soporte(), paquete.series(), paquete.clima(), MODELO_OFICIAL, False)
    iniciar_sesion()
    st.session_state['mapas_dibujados'] = []
    st.session_state['avisos_filtro'] = []
    dibujar = vista.mapa
    notificar = st.toast

    def registrar(*args, **kwargs):
        st.session_state['mapas_dibujados'].append({'ids': list(args[2]), 'clave': kwargs['clave']})
        return dibujar(*args, **kwargs)

    def avisar(body, **kwargs):
        st.session_state['avisos_filtro'].append({'texto': body, **kwargs})
        return notificar(body, **kwargs)

    with patch.object(vista, 'mapa', side_effect=registrar), patch.object(st, 'toast', side_effect=avisar):
        vista.mostrar(ctx)


def caja(at, etiqueta):
    return next(x for x in at.selectbox if x.label == etiqueta)


at = AppTest.from_function(pantalla, default_timeout=90).run()
assert not at.exception, at.exception
at.segmented_control(key='vista_mapa').set_value('Desde arriba').run()
caja(at, 'Municipio').set_value('Emiliano Zapata').run()
anterior = at.session_state['mapas_dibujados'][0]
at.segmented_control(key='capa').set_value('Las 59').run()
assert not at.exception, at.exception
assert at.session_state['mapas_dibujados'] == [anterior], 'Debe conservar el mapa y su clave anteriores'
assert at.segmented_control(key='capa').value == 'Todas', 'Debe deshacer el filtro sin coincidencias'
assert caja(at, 'Municipio').value == 'Emiliano Zapata'
aviso = at.session_state['avisos_filtro']
assert len(aviso) == 1 and 'No hay parcelas por estimar en Emiliano Zapata' in aviso[0]['texto']
assert 'Se conservó el filtro anterior' in aviso[0]['texto'] and aviso[0]['duration'] == 5
assert not any('No hay parcelas' in i.value for i in at.info), 'No debe dejar una franja persistente'
assert len(at.tabs) == 6 and any(t.label == 'Ficha técnica' for t in at.tabs)
at.run()
assert at.session_state['avisos_filtro'] == [], 'El aviso no debe reaparecer en otros reruns'

for capa in ['Las 138', 'Todas']:
    at.segmented_control(key='capa').set_value(capa).run()
    assert not at.exception, at.exception
    assert len(at.session_state['mapas_dibujados']) == 1
    assert len(at.session_state['mapas_dibujados'][0]['ids']) == 3, capa
    assert at.segmented_control(key='vista_mapa').value == 'Desde arriba', 'El filtro vacío no debe reiniciar el modo del mapa'
    assert not any('No hay parcelas' in i.value for i in at.info)

caja(at, 'Municipio').set_value('Chignahuapan').run()
at.segmented_control(key='capa').set_value('Las 59').run()
assert not at.exception, at.exception
assert len(at.session_state['mapas_dibujados'][0]['ids']) == 29
anterior = at.session_state['mapas_dibujados'][0]
caja(at, 'Municipio').set_value('Emiliano Zapata').run()
assert not at.exception, at.exception
assert caja(at, 'Municipio').value == 'Chignahuapan', 'Debe restaurar el municipio, no sólo la capa'
assert at.segmented_control(key='capa').value == 'Las 59'
assert at.session_state['mapas_dibujados'] == [anterior]
assert len(at.session_state['avisos_filtro']) == 1
caja(at, 'Municipio').set_value('Emiliano Zapata').run()
assert len(at.session_state['avisos_filtro']) == 1, 'Un nuevo intento inválido debe avisar de nuevo'
caja(at, 'Municipio').set_value('Todos').run()
assert not at.exception, at.exception
assert len(at.session_state['mapas_dibujados'][0]['ids']) == 59
caja(at, 'Buscar parcela por ID').set_value('AGC_011').run()
assert not at.exception, at.exception
assert 'AGC_011' in at.session_state['mapas_dibujados'][0]['ids'], 'La búsqueda por ID conserva su encuadre'
caja(at, 'Buscar parcela por ID').set_value('(ninguna)').run()
assert not at.exception, at.exception
assert len(at.session_state['mapas_dibujados'][0]['ids']) == 59
print('OK: filtro rechazado, mapa/clave/modo conservados, aviso único de 5 s, ambos selectores y búsqueda directa')
