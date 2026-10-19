"""Casos de presentación que no cubren los datos habituales: python tests/frontend/test_validacion_presentacion.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
from streamlit.testing.v1 import AppTest

from agrocebada_app.frontend.componentes.validacion.formato import insignia, resumen_estimacion


def resumen(valores, fuentes=None, niveles=None):
    return resumen_estimacion(pd.Series(valores, dtype=float), pd.Series(fuentes or ["grupo"] * len(valores), dtype=str),
                              pd.Series(niveles or ["Baja"] * len(valores), dtype=str))


assert resumen([]) is None
assert resumen([3.5, 3.5])["valor"] == "3.50"
assert resumen([3.5, 3.6])["valor"] == "Varios valores"
assert resumen([3.1411, 3.1412])["valor"] == "Varios valores", "No ocultar diferencias mediante el redondeo"
assert resumen([3.5, 3.5], ["grupo", "global"])["valor"] == "Varios valores"
assert resumen([3.5, 3.5], niveles=["Media", "Baja"])["valor"] == "Varios valores"
assert resumen([float("nan")])["valor"] == "Varios valores"
assert "<script>" not in insignia("<script>")


def pantalla(caso):
    from types import SimpleNamespace

    import pandas as pd

    from agrocebada_app.backend.dominio.validacion import COLUMNAS_POBLACIONES
    from agrocebada_app.frontend.componentes.validacion.resultados import resultados
    from agrocebada_app.frontend.componentes.validacion.simulacion import comparacion
    from agrocebada_app.frontend.vistas.analista.pestanas.validacion import validacion

    if caso == "sin-validacion":
        validacion(SimpleNamespace(O=None, OA=None))
    elif caso == "sin-principal":
        fila = ["B · zona de lluvia nueva · sin respaldo", 1, 5, .2, .3, .1, .5, False]
        resultados(pd.DataFrame([fila], columns=COLUMNAS_POBLACIONES), "Modelo de prueba")
    else:
        tabla = pd.DataFrame({"estimación normal": [3., 3.], "confianza normal": ["Media", "Media"],
                              "sin datos del municipio": [3.5, 3.7], "fuente sin datos": ["grupo", "global"],
                              "confianza sin datos": ["Baja", "Baja"]}, index=pd.Index(["P1", "P2"], name="ID_POLIGONO"))
        normal = pd.DataFrame({"prediccion": [3., 3.], "fuente": ["municipio"] * 2}, index=tabla.index)
        sim = pd.DataFrame({"prediccion": [3.5, 3.7], "fuente": ["grupo", "global"]}, index=tabla.index)
        if caso == "vacio":
            tabla, normal, sim = tabla.iloc[:0], normal.iloc[:0], sim.iloc[:0]
        comparacion(tabla, normal, sim, {"validacion": "Evidencia", "limite": "Pocos casos", "estimaciones": "Uso real"},
                    "Motivo exclusivo del primer grupo")


for caso in ["sin-validacion", "sin-principal", "vacio", "mixto"]:
    at = AppTest.from_function(pantalla, args=(caso,)).run()
    assert not at.exception, (caso, at.exception)
    texto = " ".join(m.value for m in at.markdown)
    if caso == "mixto":
        assert all(t in texto for t in ["Varios valores", "Grupo de registro", "Toda la región"])
        assert len(at.dataframe[0].value) == 2
        assert "Motivo exclusivo del primer grupo" not in " ".join(c.value for c in at.caption)
    elif caso == "sin-principal":
        assert len(at.info) == 1 and "val-metricas" not in texto
        assert len(at.dataframe[0].value) == 1
    else:
        assert len(at.info) == 1 and not at.dataframe
print("OK: resumen sin promedios, valores distintos, respaldo global/mixto, vacíos y principal ausente")


def pantalla_grafica(modelo):
    from unittest.mock import patch

    import streamlit as st

    from agrocebada_app.backend.datos import paquete
    from agrocebada_app.frontend.componentes.graficas.dispersion_validacion import dispersion
    from agrocebada_app.frontend.estado.contexto import calcular

    ctx = calcular(paquete.parcelas(), paquete.soporte(), paquete.series(), paquete.clima(), modelo, False)
    real = st.altair_chart

    def registrar(chart, **kwargs):
        st.session_state["grafica"] = chart.to_dict()
        return real(chart, **kwargs)

    with patch.object(st, "altair_chart", side_effect=registrar):
        dispersion(ctx)


for modelo in ["media_mun__resp_grupo", "mediana_mun__resp_grupo"]:
    at = AppTest.from_function(pantalla_grafica, args=(modelo,), default_timeout=90).run()
    assert not at.exception, at.exception
    spec = at.session_state["grafica"]
    diagonal, puntos = spec["layer"]
    assert puntos["mark"] == {"type": "circle", "opacity": .85, "size": 55}
    assert diagonal["mark"]["strokeDash"] == [4, 4]
    assert puntos["encoding"]["color"]["legend"]["columns"] == 2
    assert puntos["encoding"]["x"]["scale"]["domain"] == [2, 6]
    assert puntos["encoding"]["y"]["scale"]["domain"] == [2, 6]
    datos = spec["datasets"][puntos["data"]["name"]]
    assert len(datos) == 135 and len({x["ID_POLIGONO"] for x in datos}) == 135
    assert set(puntos["encoding"]["tooltip"][i]["field"] for i in range(4)) == {
        "ID_POLIGONO", "municipio", "real", "estimacion"}
    print(f"OK: gráfica original, 135 puntos, diagonal, leyenda y tooltip ({modelo})")
