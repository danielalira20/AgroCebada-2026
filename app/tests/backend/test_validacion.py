"""Pruebas de la validación (M12):  python tests/backend/test_validacion.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.confianza import confianza_municipios  # noqa: E402
from agrocebada_app.backend.dominio.validacion import (  # noqa: E402
    COLUMNAS_MUNICIPIOS, COLUMNAS_POBLACIONES, bloques_respaldo, comparacion_oculto, contraste_respaldo, descripcion_principal,
    frase_respaldo, poblaciones, por_municipio, regla_confianza)
from agrocebada_app.backend.modelo.metricas import metricas  # noqa: E402


def val(filas):
    """Validación inventada: (id, municipio, escenario, fuente, error) en 2 repeticiones; el rendimiento varía."""
    out = []
    for rep in (1, 2):
        for k, (pid, mun, esc, fuente, err) in enumerate(filas):
            real = 2.0 + (k % 4)
            out.append(dict(ID_POLIGONO=pid, repeticion=rep, escenario=esc, real=real, prediccion=real + err,
                            fuente=fuente, municipio=mun, ae=abs(err), e=err))
    return pd.DataFrame(out)


# 6 parcelas en A (una sin otras de su municipio: usa el grupo) y 3 en B
O = val([("P1", "X", "A", "municipio", 0.2), ("P2", "X", "A", "municipio", -0.4), ("P3", "X", "A", "municipio", 0.3),
         ("P4", "Y", "A", "municipio", 0.1), ("P5", "Y", "A", "municipio", -0.1), ("P6", "S", "A", "grupo", 0.5),
         ("P1", "X", "B", "municipio", 0.6), ("P4", "Y", "B", "grupo", -0.2), ("P6", "S", "B", "municipio", 0.3)])
OA = O[(O.escenario == "A") & (O.fuente == "municipio")]

# --- poblaciones: nombre completo, parcelas distintas distintas de las predicciones, la principal primero
pob = poblaciones(O)
assert list(pob.columns) == COLUMNAS_POBLACIONES
assert pob.poblacion.tolist() == ["A · municipio conocido · sin respaldo", "A · municipio conocido · todas las predicciones",
                                  "B · zona de lluvia nueva · sin respaldo", "B · zona de lluvia nueva · todas las predicciones"]
assert pob.principal.tolist() == [True, False, False, False]
assert pob.parcelas.tolist() == [5, 6, 2, 3] and pob.predicciones.tolist() == [10, 12, 4, 6]   # 5 de 6: no se mezclan
assert abs(pob.MAE.iloc[0] - metricas(OA).MAE) < 1e-12            # la principal es A · sin respaldo, como mA
assert abs(pob.MAE.iloc[0] - metricas(O[O.escenario == "A"]).MAE) > 1e-6
assert descripcion_principal(pob) == "A · municipio conocido · sin respaldo: 5 parcelas, la población que corresponde a las estimaciones reales."
assert descripcion_principal(pob.assign(principal=False)) == ""

# --- por municipio: todos los municipios, con su confianza; sin validación propia no hay error
d = pd.DataFrame({"municipio": ["X"] * 3 + ["Y"] * 2 + ["S"], "real": 3.0})
conf = confianza_municipios(d, OA)
cob = pd.Series({"X": 0.5, "Y": 1.0})
pm = por_municipio(conf, cob)
assert list(pm.columns) == COLUMNAS_MUNICIPIOS
assert pm.municipio.tolist() == ["X", "Y", "S"] and pm.n_cosecha.tolist() == [3, 2, 1]
assert pm.dentro.tolist() == ["50 %", "100 %", "—"] and pm.confianza.tolist() == ["Media", "Baja", "Baja"]
assert np.isnan(pm.set_index("municipio").loc["S", "mae_municipio"])

# --- la regla escrita sale de los mismos umbrales y del error general
r = regla_confianza(0.3126)
assert len(r) == 3 and [x.split(":")[0] for x in r] == ["Alta", "Media", "Baja"]
assert "10 o más parcelas con cosecha" in r[0] and "0.313 t/ha" in r[0]
assert "de 3 a 9 parcelas" in r[1] and "2 o menos parcelas" in r[2] and "grupo" in r[2]
assert "el error general." in regla_confianza()[0] and "nan" not in " ".join(regla_confianza())

# --- caso de información insuficiente: qué pasó en la validación y cuántas de las reales usan respaldo
pred = pd.DataFrame({"municipio": ["X", "X", "Y", "S"], "prediccion": [3.0, 3.1, 4.0, 2.5],
                     "fuente": ["municipio"] * 4}, index=["R1", "R2", "R3", "R4"])
c = contraste_respaldo(O, pred)
assert (c["predicciones"], c["parcelas"], c["estimaciones"], c["estimaciones_con_respaldo"]) == (2, 1, 4, 0), c
assert abs(c["mae"] - 0.5) < 1e-12 and abs(c["mae_municipio"] - OA.ae.mean()) < 1e-12
f = frase_respaldo(c)
partes = bloques_respaldo(c)
assert set(partes) == {"validacion", "limite", "estimaciones"}
assert " ".join(t for t in partes.values() if t) == f
assert "Ninguna" not in partes["validacion"] and "Ninguna" in partes["estimaciones"]
assert f.startswith("En la validación, 1 parcela no tuvo otras con cosecha en su municipio y se estimó con el valor del grupo (2 predicciones")
assert "MAE 0.50 t/ha, frente a" in f and "Con sólo 1 parcela no alcanza para comparar" in f
assert "no porque el error haya sido mayor" in f and "Ninguna de las 4 estimaciones reales usa respaldo" in f
f2 = frase_respaldo(contraste_respaldo(O, pred.assign(fuente=["municipio", "grupo", "grupo", "municipio"])))
assert "2 de las 4 estimaciones reales usan respaldo." in f2
sin_resp = contraste_respaldo(O[O.fuente == "municipio"], pred)
assert sin_resp["predicciones"] == 0 and frase_respaldo(sin_resp).startswith("En la validación todas las predicciones")
assert bloques_respaldo(sin_resp)["limite"] == ""
assert bloques_respaldo(dict(c, parcelas=20))["limite"] == ""

# --- ocultar un municipio: la estimación sin sus datos usa el grupo y la confianza baja
sim = pred.assign(prediccion=[3.6, 3.6, 3.9, 3.7], fuente=["grupo"] * 4)
t, motivo = comparacion_oculto(pred, sim, conf, "X")
assert t.index.tolist() == ["R1", "R2"]
assert t.columns.tolist() == ["estimación normal", "confianza normal", "sin datos del municipio", "fuente sin datos",
                              "confianza sin datos"]
assert t["confianza normal"].tolist() == ["Media", "Media"] and t["confianza sin datos"].tolist() == ["Baja", "Baja"]
assert t["fuente sin datos"].tolist() == ["grupo", "grupo"] and t["sin datos del municipio"].tolist() == [3.6, 3.6]
assert motivo.startswith("Confianza baja:") and "su grupo de registro" in motivo
assert comparacion_oculto(pred, sim.assign(fuente="global"), conf, "Y")[1].endswith("toda la región.")

# --- con los datos reales (necesita el paquete de datos o el registro de T08, como las demás pruebas)
from agrocebada_app.backend.datos import lectura, paquete  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402
from agrocebada_app.backend.rutas.localizador import rutas  # noqa: E402

p = lectura.leer_parcelas(rutas()["datos"])
for modelo, mae in [("media_mun__resp_grupo", 0.3205), ("mediana_mun__resp_grupo", 0.3126)]:
    O = paquete.validacion(modelo, p.municipio)
    assert O is not None, f"no encontré la validación de {modelo} (ni en datos_app/ ni en registro/t08)"
    OA = O[(O.escenario == "A") & (O.fuente == "municipio")]
    pob = poblaciones(O)
    # 138 contra 135: la principal son 135 parcelas; las que mezclan el respaldo, 138
    assert pob.parcelas.tolist() == [135, 138, 135, 138] and pob.predicciones.tolist() == [675, 690, 659, 690], \
        (modelo, pob[["parcelas", "predicciones"]].values.tolist())
    assert pob.principal.tolist() == [True, False, False, False]
    assert abs(pob.MAE.iloc[0] - mae) < 5e-4 and abs(pob.MAE.iloc[0] - metricas(OA).MAE) < 1e-12, (modelo, pob.MAE.iloc[0])
    assert descripcion_principal(pob).startswith("A · municipio conocido · sin respaldo: 135 parcelas")
    pred = predecir(p, modelo)
    c = contraste_respaldo(O, pred)
    assert (c["predicciones"], c["parcelas"], c["estimaciones"], c["estimaciones_con_respaldo"]) == (15, 3, 59, 0), c
    assert abs(c["mae_municipio"] - pob.MAE.iloc[0]) < 1e-12
    assert "Ninguna de las 59 estimaciones reales usa respaldo" in frase_respaldo(c)
    conf = confianza_municipios(p, OA)
    cob = OA.assign(dentro=OA.ae <= OA.municipio.map(OA.groupby("municipio").ae.mean())).groupby("municipio").dentro.mean()
    pm = por_municipio(conf, cob)
    assert len(pm) == 9 and pm.confianza.value_counts().to_dict() == {"Media": 4, "Baja": 3, "Alta": 2}, pm.confianza.value_counts().to_dict()
    assert f"{conf.mae_general.iloc[0]:.3f} t/ha" in regla_confianza(conf.mae_general.iloc[0])[0]   # sale de la tabla
    sim = predecir(p, modelo, ocultar="Chignahuapan")
    t, motivo = comparacion_oculto(pred, sim, conf, "Chignahuapan")
    assert len(t) == 29 and set(t["confianza normal"]) == {"Media"} and set(t["confianza sin datos"]) == {"Baja"}
    assert set(t["fuente sin datos"]) == {"grupo"} and motivo.startswith("Confianza baja:")
print("OK")
