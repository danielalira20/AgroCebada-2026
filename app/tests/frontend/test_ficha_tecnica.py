"""Modelo activo en Ficha técnica: python tests/frontend/test_ficha_tecnica.py (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.config import MODELOS


def pantalla(modelo):
    from agrocebada_app.backend.datos import paquete
    from agrocebada_app.frontend.estado.contexto import calcular
    from agrocebada_app.frontend.vistas.analista.pestanas.ficha_tecnica import ficha_tecnica

    d = paquete.parcelas()
    ctx = calcular(d, paquete.soporte(), paquete.series(), paquete.clima(), modelo, False)
    ficha_tecnica(ctx)


for modelo, cifra in [("media_mun__resp_grupo", "4.48"), ("mediana_mun__resp_grupo", "4.52")]:
    at = AppTest.from_function(pantalla, args=(modelo,), default_timeout=90).run()
    assert not at.exception, at.exception
    at.selectbox[0].set_value("AGC_011").run()
    assert not at.exception, at.exception
    texto = " ".join(m.value for m in at.markdown)
    assert f"Estimación · {MODELOS[modelo]}" in texto, (modelo, texto)
    assert f"<b class='kv'>{cifra}<" in texto, (modelo, texto)
    assert "Estimación (modelo final)" not in texto
    at.selectbox[0].set_value("AGC_002").run()
    assert not at.exception, at.exception
    texto = " ".join(m.value for m in at.markdown)
    assert "Rendimiento registrado" in texto and f"Estimación · {MODELOS[modelo]}" not in texto
    print(f"ficha técnica: {MODELOS[modelo]}, cifra correspondiente y parcela registrada")
print("OK")
