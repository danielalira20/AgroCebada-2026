"""Prueba de la pestaña de cartera sin navegador:  python tests/frontend/test_cartera.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete

paquete.exigir_datos()

for modelo in ["media_mun__resp_grupo", "mediana_mun__resp_grupo"]:
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=300)
    at.session_state["vista"] = "Analista"
    at.session_state["modelo"] = modelo
    at.run()
    assert not at.exception, (modelo, at.exception)
    assert at.tabs[0].label == "Cartera", [t.label for t in at.tabs]
    textos = " ".join(m.value for m in at.tabs[0].markdown)
    assert "Parcelas</span>" in textos and "<b class='kv'>59<" in textos and "Hectáreas" in textos, modelo
    assert "Producción: escenario bajo a alto" in textos and "1,379–1,717" in textos, modelo
    assert "Estimación retrospectiva de la campaña 2025." in textos and "no una cifra oficial" in textos, modelo
    assert len(at.tabs[0].dataframe) == 1, modelo
    print(f"cartera ({modelo}): primera pestaña, sin errores")
print("OK")
