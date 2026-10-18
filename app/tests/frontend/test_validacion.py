"""Prueba de la pestaña Validación sin navegador:  python tests/frontend/test_validacion.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete

paquete.exigir_datos()


def pestana(at):
    return next(t for t in at.tabs if t.label == "Validación")


def tabla(tab, columna):
    """La primera tabla de la pestaña que trae esa columna."""
    return next(df.value for df in tab.dataframe if columna in df.value.columns)


def textos(tab):
    return " ".join(m.value for m in tab.markdown)


for modelo, mae in [("media_mun__resp_grupo", "0.320"), ("mediana_mun__resp_grupo", "0.313")]:
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=300)
    at.session_state["vista"] = "Analista"
    at.session_state["modelo"] = modelo
    at.run()
    assert not at.exception, (modelo, at.exception)
    tab = pestana(at)
    t = textos(tab)
    # la población principal, con su nombre y sus 135 parcelas; nunca "138 parcelas" para A · sin respaldo
    assert "Población principal" in t and "A · municipio conocido · sin respaldo: 135 parcelas" in t, modelo
    assert "138 parcelas" not in t and "las 135 parcelas de A · sin respaldo" in t, modelo
    assert f"<b class='kv'>{mae}<" in t, (modelo, mae)
    pob = tabla(tab, "Población")
    assert pob["Parcelas"].tolist() == [135, 138, 135, 138], modelo
    assert pob["Población"].iloc[0].endswith("(principal)") and pob["Población"].str.contains("sin respaldo").sum() == 2
    # por municipio: confianza y regla a la vista
    pm = tabla(tab, "Confianza")
    assert len(pm) == 9 and set(pm["Confianza"]) == {"Alta", "Media", "Baja"}, modelo
    assert "Cómo se decide la confianza" in t and "10 o más parcelas con cosecha" in t, modelo
    # caso de información insuficiente: sin los datos del municipio, la confianza es baja
    next(x for x in tab.selectbox if x.label == "Municipio a ocultar").set_value("Chignahuapan").run()
    assert not at.exception, (modelo, at.exception)
    tab = pestana(at)
    ins = tabla(tab, "confianza sin datos")
    assert set(ins["confianza normal"]) == {"Media"} and set(ins["confianza sin datos"]) == {"Baja"}, modelo
    assert set(ins["fuente sin datos"]) == {"grupo"} and len(ins) == 29, modelo
    t = textos(tab)
    assert "Confianza baja:" in t and "Ninguna de las 59 estimaciones reales usa respaldo" in t, modelo
    print(f"validación ({modelo}): población principal, confianza por municipio e información insuficiente")
print("OK")
