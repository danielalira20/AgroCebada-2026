"""Prueba de la pestaña Validación sin navegador:  python tests/frontend/test_validacion.py  (desde app/)."""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[2]       # app/
sys.path.insert(0, str(APP))

from streamlit.testing.v1 import AppTest

from agrocebada_app.backend.datos import paquete
from agrocebada_app.backend.dominio.validacion import poblaciones, por_municipio
from agrocebada_app.config import MODELOS
from agrocebada_app.frontend.componentes.validacion.formato import etiqueta_confianza
from agrocebada_app.frontend.estado.contexto import calcular

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
    ctx = calcular(paquete.parcelas(), paquete.soporte(), paquete.series(), paquete.clima(), modelo, False)
    assert MODELOS[modelo] in t
    # la población principal, con su nombre y sus 135 parcelas; nunca "138 parcelas" para A · sin respaldo
    assert "Población principal" in t and "A · municipio conocido · sin respaldo" in t, modelo
    assert "135 parcelas distintas · 675 predicciones" in t, modelo
    assert "138 parcelas" not in t and "las 135 parcelas de A · sin respaldo" in t, modelo
    assert f"<b class='kv'>{mae}<" in t, (modelo, mae)
    pob = tabla(tab, "Población")
    assert pob["Parcelas"].tolist() == [138, 135, 138], modelo
    assert not pob["Población"].str.contains("principal").any()
    assert "Otras poblaciones, como apoyo (3)" in [x.label for x in tab.expander]
    esperado = poblaciones(ctx.O)
    assert pob["MAE (t/ha)"].tolist() == esperado.loc[~esperado.principal, "MAE"].tolist()
    # por municipio: confianza y regla a la vista
    pm = tabla(tab, "Confianza")
    assert len(pm) == 9 and set(pm["Confianza"]) == {"✔ Alta", "▲ Media", "◆ Baja"}, modelo
    assert {"Municipio", "Con cosecha", "MAE (t/ha)", "Dentro de ± MAE (%)", "Confianza"} == set(pm.columns)
    assert "val-municipios-movil" in t and "Nanacamilpa de Mariano Arista" in t
    esperados = por_municipio(ctx.conf, ctx.cob_mun)
    assert pm["Municipio"].tolist() == esperados.municipio.tolist()
    assert pm["MAE (t/ha)"].equals(esperados.mae_municipio.rename("MAE (t/ha)"))
    assert pm["Confianza"].tolist() == esperados.confianza.map(etiqueta_confianza).tolist()
    assert "Cómo se decide la confianza" in t and "10 o más parcelas con cosecha" in t, modelo
    # caso de información insuficiente: sin los datos del municipio, la confianza es baja
    next(x for x in tab.selectbox if x.label == "Municipio a ocultar").set_value("Chignahuapan").run()
    assert not at.exception, (modelo, at.exception)
    tab = pestana(at)
    ins = tabla(tab, "Confianza sin datos")
    assert set(ins["Confianza con datos"]) == {"Media"} and set(ins["Confianza sin datos"]) == {"Baja"}, modelo
    assert set(ins["Fuente sin datos"]) == {"grupo"} and len(ins) == 29, modelo
    t = textos(tab)
    assert "Confianza baja por falta de evidencia" in t and "Ninguna de las 59 estimaciones reales usa respaldo" in t, modelo
    # Recorrer todos los municipios con estimaciones, sin perder filas del detalle.
    for municipio in sorted(ctx.pred.municipio.unique()):
        next(x for x in tab.selectbox if x.label == "Municipio a ocultar").set_value(municipio).run()
        assert not at.exception, (modelo, municipio, at.exception)
        tab = pestana(at)
        detalle = tabla(tab, "Confianza sin datos")
        assert detalle["Parcela"].tolist() == ctx.pred.index[ctx.pred.municipio == municipio].tolist()
    # Cambiar el modelo dentro de la misma sesión debe actualizar resumen, regla y simulación.
    otro = next(m for m in MODELOS if m != modelo)
    at.segmented_control(key="modelo").set_value(otro).run()
    assert not at.exception, at.exception
    assert MODELOS[otro] in textos(pestana(at))
    print(f"validación ({modelo}): población principal, confianza por municipio e información insuficiente")
print("OK")
