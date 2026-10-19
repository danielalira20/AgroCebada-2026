"""Prueba de «Las 59 estimaciones» (M11) sin navegador:  python tests/frontend/test_estimaciones.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete
from agrocebada_app.config import MODELO_OFICIAL

paquete.exigir_datos()

for modelo in ["media_mun__resp_grupo", "mediana_mun__resp_grupo"]:
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=300)
    at.session_state["vista"] = "Analista"
    at.session_state["modelo"] = modelo
    at.run()
    assert not at.exception, (modelo, at.exception)
    assert at.tabs[1].label == "Las 59 estimaciones", [t.label for t in at.tabs]
    pestana = at.tabs[1]

    # verificaciones: la de "entrega final" sólo aparece con el modelo oficial; la de "archivo de referencia" en el otro
    texto = " ".join(m.value for m in pestana.markdown)
    if modelo == MODELO_OFICIAL:
        assert "Coinciden con la entrega final" in texto, modelo
        assert "Coinciden con el archivo de referencia" not in texto, modelo
    else:
        assert "Coinciden con el archivo de referencia" in texto, modelo
        assert "Coinciden con la entrega final" not in texto, modelo

    # tabla ancha: las columnas nuevas de M11 están presentes
    assert len(pestana.dataframe) == 1, modelo
    tabla = pestana.dataframe[0].value
    for col in ["confianza", "rango del municipio", "motivo de la confianza"]:
        assert col in tabla.columns, (modelo, tabla.columns.tolist())
    assert set(tabla["confianza"].str.split().str[-1]) <= {"Alta", "Media", "Baja"}, modelo
    assert not tabla["rango del municipio"].isna().any(), modelo

    # tarjetas móviles: una por cada una de las 59, con su insignia de confianza y sin escapar mal el HTML
    assert texto.count("est-tarjeta-titulo") == 59, (modelo, texto.count("est-tarjeta-titulo"))
    assert "val-confianza" in texto and "<script>" not in texto, modelo
    print(f"estimaciones ({modelo}): confianza, rango y tarjetas móviles sin errores")
print("OK")
