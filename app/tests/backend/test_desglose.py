"""Pruebas del desglose de la estimación (M04):  python tests/backend/test_desglose.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.confianza import confianza_municipios  # noqa: E402
from agrocebada_app.backend.dominio.desglose import NO_ENTRA, NO_VE, desglose, valor_base  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402

MEDIA, MEDIANA = "media_mun__resp_grupo", "mediana_mun__resp_grupo"
PROHIBIDAS = ["tu parcela dará", "de cada 10", "± "]


def sin_prohibidas(x):
    textos = [x["frase"], x["motivo"], x["rango"], x["no_ve"], x["no_entra"]] + [t for fila in x["filas"] for t in fila]
    for t in textos:
        assert not any(p in t.lower() for p in PROHIBIDAS), t


# --- datos inventados: Aa tiene 3 parcelas con cosecha, Bb 1 y Cc ninguna (cae al valor global)
d = pd.DataFrame({
    "municipio": ["Aa", "Aa", "Aa", "Aa", "Bb", "Cc"],
    "CONJUNTO": ["ENTRENAMIENTO"] * 3 + ["PREDICCION", "ENTRENAMIENTO", "PREDICCION"],
    "real": [4.0, 5.0, 4.6, np.nan, 3.016, np.nan],
    "grupo_registro": ["G1"] * 5 + ["G2"], "AREA_HA": 1.0}, index=["p1", "p2", "p3", "p4", "p5", "p6"])
conf = confianza_municipios(d, None)
assert conf.set_index("municipio").nivel.to_dict() == {"Aa": "media", "Bb": "baja", "Cc": "baja"}

# --- la base es el estadístico del modelo sobre las parcelas con cosecha
assert abs(valor_base(d, MEDIA) - 4.154) < 1e-9 and abs(valor_base(d, MEDIANA) - 4.3) < 1e-9

# --- con la media: base 4.15 + diferencia = estimación (Aa: media de 4.0, 5.0 y 4.6)
pred = predecir(d, MEDIA)
x = desglose(d, pred, MEDIA, conf, "p4")
assert (x["base"], x["ajuste"], x["estimacion"], x["fuente"]) == (4.15, 0.38, 4.53, "municipio"), x
assert x["filas"] == [("Promedio de la región", "4.15 t/ha"), ("Por estar en Aa", "+0.38"), ("Estimación", "4.53 t/ha")]
assert x["frase"] == "Se parte del promedio de la región (4.15 t/ha); por estar en Aa se suma 0.38 y queda en 4.53 t/ha."
assert x["nivel"] == "media" and x["motivo"].startswith("Confianza media:")
assert x["rango"].startswith("Las 3 parcelas con cosecha de Aa dieron entre 4.00 y 5.00 t/ha")
assert x["no_ve"] == NO_VE == "fecha de siembra, variedad y manejo" and "no entran al cálculo" in NO_ENTRA
sin_prohibidas(x)

# --- con la mediana cambian la base, la etiqueta y la diferencia
x = desglose(d, predecir(d, MEDIANA), MEDIANA, conf, "p4")
assert (x["base"], x["ajuste"], x["estimacion"]) == (4.3, 0.3, 4.6), x
assert x["filas"][0] == ("Mediana de la región", "4.30 t/ha")
assert x["frase"] == "Se parte de la mediana de la región (4.30 t/ha); por estar en Aa se suma 0.30 y queda en 4.60 t/ha."

# --- diferencia negativa
p2 = pred.copy()
p2.loc["p4", "prediccion"] = 3.0
x = desglose(d, p2, MEDIA, conf, "p4")
assert x["ajuste"] == -1.15 and x["filas"][1] == ("Por estar en Aa", "-1.15") and "se resta 1.15" in x["frase"]

# --- redondeo: 4.536 - 4.154 se vería 4.54 = 4.15 + 0.39; redondeando por separado se vería 4.15 + 0.38 = 4.53
p2.loc["p4", "prediccion"] = 4.536
x = desglose(d, p2, MEDIA, conf, "p4")
assert (x["base"], x["ajuste"], x["estimacion"]) == (4.15, 0.39, 4.54), x
assert abs(x["base"] + x["ajuste"] - x["estimacion"]) < 1e-9

# --- el respaldo del grupo: otra fila de ajuste, confianza baja siempre
p2.loc["p4", ["prediccion", "fuente"]] = [3.2, "grupo"]
x = desglose(d, p2, MEDIA, conf, "p4")
assert x["filas"][1][0] == "Por su grupo de registro" and x["nivel"] == "baja" and "su grupo de registro" in x["motivo"]
assert "por su grupo de registro se resta 0.95" in x["frase"]
sin_prohibidas(x)

# --- sin cosechas ni en el municipio ni en el grupo: se usa el valor de la región, sin fila de ajuste
x = desglose(d, pred, MEDIA, conf, "p6")
assert x["fuente"] == "global" and x["ajuste"] == 0 and x["estimacion"] == x["base"] == 4.15
assert [f[0] for f in x["filas"]] == ["Promedio de la región", "Estimación"] and x["nivel"] == "baja"
assert x["frase"].startswith("Como no hay cosechas de su municipio ni de su grupo de registro")
assert "sólo tiene" not in x["rango"] and "no alcanza para dar un rango" in x["rango"]
sin_prohibidas(x)

# --- una parcela con cosecha registrada no tiene estimación que explicar
assert desglose(d, pred, MEDIA, conf, "p1") is None

# --- con los datos reales (necesita el paquete de datos o el registro de T08, como las demás pruebas)
from agrocebada_app.backend.datos import paquete  # noqa: E402

paquete.exigir_datos()
r = paquete.parcelas()
ESPERADO = {MEDIA: (3.96, 0.52, 4.48), MEDIANA: (4.34, 0.18, 4.52)}      # Chignahuapan
for modelo in (MEDIA, MEDIANA):
    O = paquete.validacion(modelo, r.municipio)
    assert O is not None, f"no encontré la validación de {modelo} (ni en datos_app/ ni en registro/t08)"
    OA = O[(O.escenario == "A") & (O.fuente == "municipio")]
    cf = confianza_municipios(r, OA)
    pr = predecir(r, modelo)
    assert len(pr) == 59
    xs = {pid: desglose(r, pr, modelo, cf, pid) for pid in pr.index}
    for pid, x in xs.items():       # las 59 suman exacto y la estimación es la que muestra el panel
        assert abs(x["base"] + x["ajuste"] - x["estimacion"]) < 1e-9, (modelo, pid, x["filas"])
        assert x["estimacion"] == round(float(pr.loc[pid, "prediccion"]), 2) and x["fuente"] == "municipio"
        assert x["nivel"] in ("alta", "media", "baja") and x["motivo"].startswith("Confianza ")
        sin_prohibidas(x)
    por_muni = pd.DataFrame({"m": pr.municipio, "e": [xs[i]["estimacion"] for i in pr.index]}).groupby("m").e.nunique()
    assert (por_muni == 1).all(), por_muni          # misma estimación en todo el municipio (AGC_011 = AGC_036)
    pid = pr.index[pr.municipio == "Chignahuapan"][0]
    assert (xs[pid]["base"], xs[pid]["ajuste"], xs[pid]["estimacion"]) == ESPERADO[modelo], xs[pid]["filas"]
    assert xs[pid]["nivel"] == "media" and xs[pid]["frase"].startswith("Se parte")
    assert len(set(pr.municipio)) == 6
print("OK")
