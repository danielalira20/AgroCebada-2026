"""Prueba de la pestaña Evidencia sin navegador:  python tests/frontend/test_evidencia.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete
from agrocebada_app.backend.dominio.evidencia import variacion_ubicacion
from agrocebada_app.config import MODELOS

paquete.exigir_datos()
PROHIBIDAS = ["no sirve", "tu parcela dará", "de cada 10"]


def textos(tab):
    return " ".join(m.value for m in tab.markdown)


for modelo in MODELOS:
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=300)
    at.session_state["vista"] = "Analista"
    at.session_state["modelo"] = modelo
    at.run()
    assert not at.exception, (modelo, at.exception)       # incluye claves de contenedor repetidas
    etiquetas = [t.label for t in at.tabs]
    assert etiquetas.index("Validación") + 1 == etiquetas.index("Evidencia") == etiquetas.index("Método y límites") - 1, etiquetas
    tab = next(t for t in at.tabs if t.label == "Evidencia")
    t = textos(tab)
    # las tres preguntas, la regla y las cifras del informe
    for p in ("Pregunta 1 · ¿Qué índice de vegetación pesa más?", "Pregunta 2 · ¿Qué variable del clima pesa más?",
              "Pregunta 3 · ¿Qué combinación funciona mejor?"):
        assert p in t, p
    assert "0.3205 t/ha" in t and "Ninguna de las 8 pruebas registradas bajó el error" in t
    assert "Ninguna de las 4 pruebas registradas bajó el error" in t and "Ninguna de las 15 pruebas registradas pasó la regla" in t
    assert "0.3205 a 0.3126" in t and "excepción explícita" in t and "no demuestra que el clima" in t
    assert "Lo que aprendimos" in t and "Lo que el método no ve" in t
    for falta in ("Fecha de siembra", "Variedad", "Manejo"):
        assert falta in t, falta
    # cuánto explica la ubicación: sale de los datos reales (≈ 69 %), no de un texto fijo
    ubic = variacion_ubicacion(paquete.parcelas())
    assert ubic["pct"] == 69 and f"≈ {ubic['pct']}<" in t, ubic
    # el modelo mostrado en «Lo que aprendimos» es el vigente
    assert MODELOS[modelo] in t, modelo
    # tablas: una por pregunta y la completa, con icono y palabra en cada resultado
    tablas = [df.value for df in tab.dataframe]
    assert [len(x) for x in tablas] == [10, 4, 16, 30], [len(x) for x in tablas]
    completa = tablas[-1]
    assert completa["Registro"].iloc[:27].ne("—").sum() >= 27 - 3 and set(completa["Resultado"].str[:1]) <= {"✔", "▲", "⚠", "P"}
    assert not (completa["Resultado"] == "✔ Pasó la regla").any()
    assert "Prueba complementaria" in set(completa["Resultado"])
    assert not any(x in t.lower() for x in PROHIBIDAS)
    print(modelo, "OK")

# si la mediana no fuera el modelo oficial, la fila de T16 ya no se llamaría «modelo final»
from agrocebada_app.backend.dominio.evidencia import cierre_modelo_final  # noqa: E402
from agrocebada_app.backend.datos.experimentos import experimentos  # noqa: E402

assert "Se conserva el promedio" in cierre_modelo_final(experimentos(), "media_mun__resp_grupo")
print("OK")
