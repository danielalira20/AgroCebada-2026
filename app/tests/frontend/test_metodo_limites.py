"""Prueba de la pestaña Método y límites sin navegador:  python tests/frontend/test_metodo_limites.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete
from agrocebada_app.backend.dominio import alcance as al
from agrocebada_app.config import MODELOS
from agrocebada_app.frontend.estado.contexto import calcular

paquete.exigir_datos()
PROHIBIDAS = ["explican buena parte", "cerca de 20", "pr #", "tu parcela dará", "no sirve"]


def textos(tab):
    return " ".join(m.value for m in tab.markdown)


for modelo in MODELOS:
    at = AppTest.from_file(str(APP / "app.py"), default_timeout=300)
    at.session_state["vista"] = "Analista"
    at.session_state["modelo"] = modelo
    at.run()
    assert not at.exception, (modelo, at.exception)
    tab = next(t for t in at.tabs if t.label == "Método y límites")
    v = " ".join(m.value for m in next(t for t in at.tabs if t.label == "Validación").markdown)
    t = textos(tab)
    ctx = calcular(paquete.parcelas(), paquete.soporte(), paquete.series(), paquete.clima(), modelo, False)

    # los cuatro pasos se describen con el modelo final, aunque el selector tenga la media
    assert "la mediana del rendimiento" in t and "la media del rendimiento" not in t, modelo
    for paso in ("Datos", "Valor típico del municipio", "Asignación", "Validación"):
        assert paso in t, paso

    # las cifras de error son las de Validación (M12): mismas poblaciones, mismos números
    ep = al.error_principal(ctx.O)
    assert ep["a_parcelas"] == 135, ep
    for cifra in (ep["a_mae"], ep["b_mae"]):
        assert f"<b class='kv'>{cifra:.3f}<" in t, (modelo, cifra)
    assert f"<b class='kv'>{ep['a_mae']:.3f}<" in v, modelo
    assert MODELOS[modelo] in t

    # la tabla de alcance: cinco filas con icono y palabra, y los conteos de las 59 suman 59
    filas = al.tabla_alcance(ctx.O, ctx.conf, ctx.pred)
    assert "¿A qué parcelas sirve?" in t and len(filas) == 5
    for f in filas:
        assert f["sirve"] in t and f["situacion"] in t and f["estimaciones"] in t, f
    assert filas[3]["estimaciones"] == "Ninguna de las 59", filas[3]
    assert sum(int(f["estimaciones"].split(" ")[0]) for f in filas[:3]) == 59

    # enlace a Evidencia sin afirmar cuántas variantes se probaron; límites honestos
    assert "pestaña Evidencia" in t and "excepción explícita" in t
    assert "Lo que sigue" not in t
    assert "fecha de siembra, variedad y manejo" in t
    assert not any(p in t.lower() for p in PROHIBIDAS), [p for p in PROHIBIDAS if p in t.lower()]
    print(modelo, "OK")

print("OK")
