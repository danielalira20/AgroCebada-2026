"""Integración de calculadora/estado/PDF sin dibujar ni probar Cebi."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest


def pantalla(municipal=False):
    from types import SimpleNamespace

    import streamlit as st

    from agrocebada_app.backend.datos import paquete
    from agrocebada_app.backend.dominio.planeador import estimacion_municipio
    from agrocebada_app.backend.modelo.estimador import predecir
    from agrocebada_app.config import MODELO_OFICIAL
    from agrocebada_app.frontend.componentes.descargas.boton_ficha import filas_calculadora
    from agrocebada_app.frontend.estado.planeador import guardar_entrada, preparar_area
    from agrocebada_app.frontend.estado.sesion import iniciar_sesion
    from agrocebada_app.frontend.vistas.agricultor.calculadora import calculadora, calculadora_base

    iniciar_sesion()
    vista = st.selectbox("Vista de prueba", ["Cuenta", "Otra vista"], key="vista_prueba")
    if vista == "Otra vista":
        st.write("Widgets de cuenta desmontados")
        return
    d = paquete.parcelas()
    ctx = SimpleNamespace(d=d)
    if municipal:
        preparar_area(st.session_state, "calc_area_rapida", 10.0)
        area = st.number_input("Hectáreas de la consulta", min_value=0.01, value=None, key="calc_area_rapida",
                               on_change=guardar_entrada, args=(st.session_state, "calc_area_rapida", "area_rapida_ha"))
        ref = estimacion_municipio(d, "Chignahuapan", MODELO_OFICIAL)
        calculadora_base(ctx, "Chignahuapan", ref["rendimiento_t_ha"], "Referencia municipal", area,
                         "calc_area_rapida", area_editable=False)
    else:
        ctx.pred = predecir(d, MODELO_OFICIAL)
        pid = st.selectbox("Parcela de prueba", ["AGC_011", "AGC_002"], key="parcela_prueba")
        st.session_state["cuenta_pdf_antes"] = filas_calculadora(pid, ctx)
        calculadora(ctx, pid)
        st.session_state["cuenta_para_pdf"] = filas_calculadora(pid, ctx)


def html(at):
    return "\n".join(m.value for m in at.markdown)


at = AppTest.from_function(pantalla, default_timeout=40).run()
assert not at.exception, at.exception
assert len(at.number_input) == 3
at.number_input(key="calc_precio").set_value(6000.0).run()
at.number_input(key="calc_costo").set_value(18000.0).run()
at.number_input(key="calc_area_AGC_011").set_value(10.0).run()
assert not at.exception, at.exception
assert "tu estimación (4.52 t/ha en 10.00 ha)" in html(at)
assert "$91,200" in html(at)
assert dict(at.session_state["cuenta_para_pdf"])["Producción en 10.00 ha"] == "45.2 t"
at.selectbox(key="vista_prueba").set_value("Otra vista").run()
at.selectbox(key="vista_prueba").set_value("Cuenta").run()
assert not at.exception, at.exception
assert at.number_input(key="calc_precio").value == 6000.0
assert at.number_input(key="calc_area_AGC_011").value == 10.0
at.number_input(key="calc_area_AGC_011").set_value(None).run()
assert not at.exception, at.exception
assert at.session_state["cuenta_para_pdf"] is None
assert at.session_state["cuenta_pdf_antes"] is None
assert "sí cubres tus costos" not in html(at)
at.selectbox(key="vista_prueba").set_value("Otra vista").run()
at.selectbox(key="vista_prueba").set_value("Cuenta").run()
assert at.number_input(key="calc_area_AGC_011").value is None
assert at.session_state["cuenta_para_pdf"] is None
assert at.session_state["cuenta_pdf_antes"] is None
at.number_input(key="calc_area_AGC_011").set_value(10.0).run()
assert dict(at.session_state["cuenta_para_pdf"])["Producción en 10.00 ha"] == "45.2 t"
at.number_input(key="calc_precio").set_value(None).run()
assert at.session_state["planeador"]["precio_t"] is None
assert "sí cubres tus costos" not in html(at)
at.selectbox(key="vista_prueba").set_value("Otra vista").run()
at.selectbox(key="vista_prueba").set_value("Cuenta").run()
assert at.number_input(key="calc_precio").value is None
at.selectbox(key="parcela_prueba").set_value("AGC_002").run()
at.number_input(key="calc_precio").set_value(6000.0).run()
assert "Con tu cosecha registrada" in html(at)
at.selectbox(key="parcela_prueba").set_value("AGC_011").run()
assert at.number_input(key="calc_area_AGC_011").value == 10.0
assert not at.exception, at.exception

rapida = AppTest.from_function(pantalla, args=(True,), default_timeout=40).run()
assert not rapida.exception, rapida.exception
assert len(rapida.number_input) == 3
assert [x.label for x in rapida.number_input].count("Hectáreas de la consulta") == 1
assert not any(x.label == "Área (ha)" for x in rapida.number_input)
rapida.number_input(key="calc_precio").set_value(5500.0).run()
rapida.number_input(key="calc_costo").set_value(22000.0).run()
assert not rapida.exception, rapida.exception
assert "la referencia de tu municipio (4.52 t/ha en 10.00 ha)" in html(rapida)
assert "$28,600" in html(rapida)
print("OK: parcela estimada/registrada, cuenta municipal sin ID, área única, retención, limpieza y datos para PDF.")
