"""Integración de tarjetas y orientación con cambios reales de captura, sin Cebi."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from streamlit.testing.v1 import AppTest


def pantalla(reales=(2., 3., 5.), referencia=4., etiqueta="Referencia del municipio"):
    from types import SimpleNamespace
    import pandas as pd
    import streamlit as st
    from agrocebada_app.frontend.estado.sesion import iniciar_sesion
    from agrocebada_app.frontend.tema.estilos import estilo_actual
    from agrocebada_app.frontend.vistas.agricultor.calculadora import calculadora_base

    iniciar_sesion()
    st.markdown(f"<style>{estilo_actual()}</style>", unsafe_allow_html=True)
    d = pd.DataFrame({"municipio": ["M"] * len(reales), "CONJUNTO": ["ENTRENAMIENTO"] * len(reales),
                      "real": list(reales)})
    calculadora_base(SimpleNamespace(d=d), "M", referencia, "Referencia", 5., "calc_area_rapida",
                     etiqueta_escenario=etiqueta)


def html(at):
    assert not at.exception, at.exception
    return "\n".join(m.value for m in at.markdown if not m.value.startswith("<style>"))


def cuenta(*args):
    at = AppTest.from_function(pantalla, args=args, default_timeout=30)
    at.session_state["calc_precio"] = 6000.
    at.session_state["calc_costo"] = 18000.
    return at.run()


at = cuenta()
contenido = html(at)
tarjetas = dict(re.findall(r"<article class='esc-tarjeta esc-tarjeta--([^']+)'[^>]*>(.*?)</article>", contenido))
assert list(tarjetas) == ["bajo", "referencia", "alto"]
for sid, produccion, ingreso, saldo in (("bajo", "10.00 t", "$60,000", "$30,000"),
                                      ("referencia", "20.00 t", "$120,000", "$30,000"),
                                      ("alto", "25.00 t", "$150,000", "$60,000")):
    assert all(x in tarjetas[sid] for x in (produccion, ingreso, "$90,000", saldo)), tarjetas[sid]
assert "no pronostican tu cosecha" in contenido
assert "Año bajo" not in contenido
assert at.expander[0].proto.expanded
assert "te faltarían $30,000" in contenido
assert list(at.dataframe[0].value.columns) == ["Referencia del municipio", "Menor rendimiento registrado",
                                              "Mayor rendimiento registrado"]
estilo_claro = at.markdown[0].value
at.session_state["tema"] = "oscuro"
at.run()
assert at.markdown[0].value != estilo_claro
assert html(at) == contenido
assert at.expander[0].proto.expanded
at.session_state["tema"] = "claro"
at.run()
assert at.markdown[0].value == estilo_claro
assert html(at) == contenido

at.number_input(key="calc_costo").set_value(6000.).run()
assert not at.expander[0].proto.expanded
assert "cubrirías tus costos" in html(at)
at.number_input(key="calc_costo").set_value(12000.).run()
assert not at.expander[0].proto.expanded
assert "justo cubrirías tus costos" in html(at)
at.number_input(key="calc_costo").set_value(18000.).run()
assert at.expander[0].proto.expanded
at.number_input(key="calc_area_rapida").set_value(None).run()
assert "esc-tarjeta--" not in html(at)
assert len(at.expander) == 0

for reales in ((3.,), (3., 4.)):
    pocas = cuenta(reales)
    contenido = html(pocas)
    assert contenido.count("<article ") == 1
    assert "esc-pista" not in contenido
    assert "Con la única referencia disponible" in contenido

iguales = cuenta((3., 3., 3.), 3.)
assert "justo cubres tus costos" in html(iguales)
assert "Las marcas coinciden" in html(iguales)
assert "esc-pista" not in html(iguales)
assert not iguales.expander[0].proto.expanded
iguales.number_input(key="calc_costo").set_value(18000.1).run()
assert "te faltarían $0.50" in html(iguales)
assert "<strong>$0.50</strong>" in html(iguales)
assert iguales.expander[0].proto.expanded

registrada = cuenta((2., 3., 5.), 8., "Cosecha registrada 2025")
assert "Cosecha registrada 2025" in html(registrada)
assert "8.00<span>t/ha" in html(registrada)
assert "50.000000%" in html(registrada)  # 5 está a mitad de la escala 2–8.

segura = cuenta((2., 3., 5.), 4., "<script>prueba</script>")
assert "&lt;script&gt;prueba&lt;/script&gt;" in html(segura)
assert "<script>prueba</script>" not in html(segura)


def contexto_historico():
    from types import SimpleNamespace
    from agrocebada_app.backend.datos import paquete
    from agrocebada_app.frontend.vistas.agricultor.verdor_clima import verdor_clima

    verdor_clima(SimpleNamespace(d=paquete.parcelas(), S=paquete.series(), C=None), "AGC_011")


historico = AppTest.from_function(contexto_historico, default_timeout=40).run()
assert "Verdor y clima de 2025" in html(historico)
assert "no pronostica la cosecha" in html(historico)
assert "No hay información de lluvia y temperatura" in html(historico)
print("OK: tarjetas/tabla, dos temas, faltante y reapertura, equilibrio, limpieza, poco soporte, colisiones, referencia registrada y contexto sin clima.")
