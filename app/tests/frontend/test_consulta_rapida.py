"""Consulta municipal aislada: referencia sin ID, sin mapa y con superficie única."""
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from streamlit.testing.v1 import AppTest
from agrocebada_app.backend.datos import paquete
from agrocebada_app.backend.dominio.confianza import confianza_municipios, confianza_parcela
from agrocebada_app.backend.dominio.planeador import estimacion_municipio, municipios_disponibles
from agrocebada_app.config import MODELO_OFICIAL


def pantalla(vacia=False):
    from types import SimpleNamespace
    import streamlit as st
    from agrocebada_app.backend.datos import paquete
    from agrocebada_app.backend.dominio.confianza import confianza_municipios
    from agrocebada_app.config import MODELO_OFICIAL
    from agrocebada_app.frontend.estado.sesion import iniciar_sesion
    from agrocebada_app.frontend.vistas.agricultor.consulta_rapida import consulta_rapida

    iniciar_sesion()
    d = paquete.parcelas()
    if vacia:
        d = d[d.CONJUNTO == "PREDICCION"]
    validacion = paquete.validacion(MODELO_OFICIAL, d.municipio)
    oa = (validacion[(validacion.escenario == "A") & (validacion.fuente == "municipio")]
          if validacion is not None else None)
    consulta_rapida(SimpleNamespace(d=d, modelo=MODELO_OFICIAL, conf=confianza_municipios(d, oa)))


def html(at):
    assert not at.exception, at.exception
    return "\n".join(m.value for m in at.markdown)


at = AppTest.from_function(pantalla, default_timeout=40).run()
assert not at.exception, at.exception
assert len(at.number_input) == 1
assert at.number_input[0].value is None
assert at.selectbox[0].value is None
assert "rapida-cifra" not in html(at)
d = paquete.parcelas()
validacion = paquete.validacion(MODELO_OFICIAL, d.municipio)
oa = (validacion[(validacion.escenario == "A") & (validacion.fuente == "municipio")]
      if validacion is not None else None)
conf = confianza_municipios(d, oa)
opciones = municipios_disponibles(d)
assert len(opciones) == 9
assert at.selectbox[0].options == opciones
for municipio in opciones:
    at.selectbox(key="calc_municipio_rapido").set_value(municipio).run()
    ref = estimacion_municipio(d, municipio, MODELO_OFICIAL)
    assert f"{ref['rendimiento_t_ha']:.2f}<span>t/ha" in html(at)
    assert f"Basada en {ref['n_cosecha_municipio']} cosechas registradas" in html(at)
    confianza = confianza_parcela(conf, municipio, ref["fuente"])
    assert escape(confianza["motivo"]) in html(at)
    assert f"Confianza {confianza['nivel']}" in html(at)
    assert len(at.number_input) == 3
    assert "esc-tarjeta--" not in html(at)
    assert not any(x.label == "Parcela" for x in at.selectbox)

at.selectbox(key="calc_municipio_rapido").set_value("Chignahuapan").run()
at.number_input(key="calc_area_rapida").set_value(10.).run()
at.number_input(key="calc_precio").set_value(6000.).run()
at.number_input(key="calc_costo").set_value(18000.).run()
assert "45.20 t" in html(at)
assert "$91,200" in html(at)
assert sum("(ha)" in x.label for x in at.number_input) == 1
assert not at.get("deck_gl_json_chart")
assert not at.get("download_button")
at.number_input(key="calc_area_rapida").set_value(None).run()
assert "rapida-cifra" in html(at)
assert "esc-tarjeta--" not in html(at)
assert "45.20 t" not in html(at)
assert at.session_state["planeador"]["area_rapida_ha"] is None
at.number_input(key="calc_area_rapida").set_value(1e308).run()
assert "rapida-cifra" in html(at)
assert "rapida-produccion" not in html(at)
assert "esc-tarjeta--" not in html(at)
assert at.warning
at.selectbox(key="calc_municipio_rapido").set_value(None).run()
assert "rapida-cifra" not in html(at)
assert "esc-tarjeta--" not in html(at)
assert len(at.number_input) == 1

vacia = AppTest.from_function(pantalla, args=(True,), default_timeout=40).run()
assert not vacia.exception, vacia.exception
assert len(vacia.selectbox) == 0
assert "rapida-cifra" not in html(vacia)
assert vacia.info
print("OK: nueve municipios, referencia sin parcela, área única, limpieza y ausencia de soporte.")
