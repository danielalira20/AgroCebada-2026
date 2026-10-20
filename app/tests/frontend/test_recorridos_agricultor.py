"""Recorridos de producción: persistencia entre catálogo, consulta rápida y Analista."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest
from agrocebada_app.backend.datos import paquete
from agrocebada_app.backend.dominio.planeador import estimacion_municipio
from agrocebada_app.config import MODELO_OFICIAL


def html(at):
    assert not at.exception, at.exception
    return "\n".join(m.value for m in at.markdown if not m.value.startswith("<style>"))


def grupo(at, clave):
    return next(x for x in at.get("button_group") if x.key == clave)


def modo(at, valor):
    grupo(at, "agri_modo_control").set_value(valor).run()
    assert not at.exception, at.exception


d_antes = paquete.parcelas()
# Ejecuta el programa real y observa el lector PDF sin cambiar sus controles ni montar otro widget.
observador = '''
from agrocebada_app.frontend.componentes.descargas.boton_ficha import filas_calculadora
st.session_state["filas_pdf_prueba"] = (
    filas_calculadora(st.session_state["agri_parcela"], ctx.FICHA)
    if st.session_state["vista"] == "Agricultor" and st.session_state["agri_modo"] == "Parcela del catálogo"
    else None
)
'''
at = AppTest.from_string((APP / "app.py").read_text(encoding="utf-8") + observador, default_timeout=120)
at.session_state["bienvenida_completada"] = True
at.session_state["satelite"] = False
at.run()
assert not at.exception, at.exception
assert grupo(at, "agri_modo_control").value == "Parcela del catálogo"
assert at.selectbox(key="agri_parcela")
at.selectbox(key="agri_parcela").set_value("AGC_011").run()
at.number_input(key="calc_precio").set_value(6000.).run()
at.number_input(key="calc_costo").set_value(18000.).run()
at.number_input(key="calc_area_AGC_011").set_value(10.).run()
assert "$91,200" in html(at)
assert dict(at.session_state["filas_pdf_prueba"])["Producción en 10.00 ha"] == "45.2 t"
modo(at, "Consulta rápida")
assert at.selectbox(key="calc_municipio_rapido").value is None
assert at.number_input(key="calc_area_rapida").value is None
assert not at.get("deck_gl_json_chart")
assert not at.get("download_button")
assert at.session_state["filas_pdf_prueba"] is None
assert "AGC_011" not in html(at)
assert "Verdor y clima de 2025" not in html(at)
at.selectbox(key="calc_municipio_rapido").set_value("Apan").run()
at.number_input(key="calc_area_rapida").set_value(7.).run()
assert at.number_input(key="calc_precio").value == 6000.
assert len(at.number_input) == 3
assert "Referencia de Apan" in html(at)
resumen_claro = next(m.value for m in at.markdown if "<section class='rapida-resumen'" in m.value)
at.button(key="alternar_tema").click().run()
assert not at.exception, at.exception
assert at.session_state["tema"] == "oscuro"
assert resumen_claro in html(at)
assert at.selectbox(key="calc_municipio_rapido").value == "Apan"
assert at.number_input(key="calc_area_rapida").value == 7.
grupo(at, "vista").set_value("Analista").run()
assert not at.exception, at.exception
assert "class='kpis'" in html(at)
grupo(at, "modelo").set_value("media_mun__resp_grupo").run()
assert not at.exception, at.exception
grupo(at, "vista").set_value("Agricultor").run()
assert not at.exception, at.exception
assert grupo(at, "agri_modo_control").value == "Consulta rápida"
assert at.selectbox(key="calc_municipio_rapido").value == "Apan"
assert at.number_input(key="calc_area_rapida").value == 7.
oficial = estimacion_municipio(d_antes, "Apan", MODELO_OFICIAL)
assert f"{oficial['rendimiento_t_ha']:.2f}<span>t/ha" in html(at)
modo(at, "Parcela del catálogo")
assert at.selectbox(key="agri_parcela").value == "AGC_011"
assert at.number_input(key="calc_area_AGC_011").value == 10.
assert "$91,200" in html(at)
assert dict(at.session_state["filas_pdf_prueba"])["Producción en 10.00 ha"] == "45.2 t"
at.selectbox(key="agri_parcela").set_value("AGC_002").run()
at.number_input(key="calc_area_AGC_002").set_value(8.).run()
assert "Cosecha registrada 2025" in html(at)
modo(at, "Consulta rápida")
assert at.number_input(key="calc_area_rapida").value == 7.
at.number_input(key="calc_area_rapida").set_value(None).run()
assert "esc-tarjeta--" not in html(at)
modo(at, "Parcela del catálogo")
assert at.selectbox(key="agri_parcela").value == "AGC_002"
assert at.number_input(key="calc_area_AGC_002").value == 8.
assert "Producción en 8.00 ha" in dict(at.session_state["filas_pdf_prueba"])
modo(at, "Consulta rápida")
assert at.number_input(key="calc_area_rapida").value is None
at.number_input(key="calc_precio").set_value(None).run()
modo(at, "Parcela del catálogo")
assert at.number_input(key="calc_precio").value is None
assert "esc-tarjeta--" not in html(at)
assert at.session_state["filas_pdf_prueba"] is None
assert at.number_input(key="calc_area_AGC_002").value == 8.
assert paquete.parcelas().equals(d_antes)
print("OK: rutas de producción, tema, Analista, modo/municipio/parcela retenidos, áreas separadas y catálogo inmutable.")
