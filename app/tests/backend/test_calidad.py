"""Pruebas de la tarjeta de calidad del dato (M14):  python tests/backend/test_calidad.py  (desde app/)."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.calidad import contorno, escalon, frase_redondeo, imagenes, tarjeta  # noqa: E402

# --- escalón
assert escalon([2.5, 3.0, 3.5, 3.0]) == 0.5
assert escalon([4.1, 3.9, 4.5]) == 0.1
assert escalon([4.12, 3.87, 4.5]) == 0.01
assert escalon([4.123, 3.87, 4.5]) is None
assert escalon([3.0, 3.5]) is None            # muy pocas para saber

# --- datos inventados: R redondeado a 0.5 (+ una parcela por estimar), D con dos decimales, P con 2 parcelas
d = pd.DataFrame({"municipio": ["R"] * 5 + ["D"] * 3 + ["P"] * 2,
                  "CONJUNTO": ["ENTRENAMIENTO"] * 4 + ["PREDICCION"] + ["ENTRENAMIENTO"] * 5,
                  "real": [2.5, 3.0, 3.5, 3.0, np.nan, 4.12, 3.87, 4.5, 3.0, 3.5]},
                 index=["A1", "A2", "A3", "A4", "A5", "D1", "D2", "D3", "P1", "P2"])
assert frase_redondeo(d, "R") == (True, "Las cosechas de R vienen redondeadas a 0.5 t/ha: el dato registrado no "
                                  "distingue diferencias menores a 0.25 t/ha, así que ahí el error no puede ser más fino que eso.")
assert frase_redondeo(d, "D")[0] is False and "dos decimales" in frase_redondeo(d, "D")[1]
assert frase_redondeo(d, "P") == (False, "P sólo tiene 2 parcelas con cosecha: muy pocas para saber si vienen redondeadas.")
assert "no tiene parcelas con cosecha" in frase_redondeo(d, "Nada")[1]

# --- imágenes
sop = pd.DataFrame({"s2_capturas_despejadas": [10], "pl_capturas_despejadas": [40], "ls_capturas_despejadas": [3],
                    "s2_hueco_max_dias_jun_oct": [35.0], "pl_hueco_max_dias_jun_oct": [12.0],
                    "ls_hueco_max_dias_jun_oct": [np.nan]}, index=["A1"])
assert imagenes(sop, "A1") == {"despejadas": {"Sentinel-2": 10, "Planet": 40, "Landsat": 3},
                               "sensor_hueco": "Planet", "hueco_dias": 12.0}
assert imagenes(sop, "ZZ") is None and imagenes(None, "A1") is None

# --- contorno
cal = pd.DataFrame({"contorno_categoria": ["A", "B", "C"], "contorno_angosta_o_muy_pequena": ["no", "si", "no"],
                    "alerta_contorno_t03_bis": ["no", "si", "si"]}, index=["A1", "A2", "A3"])
assert contorno(cal, "A1") == {"alerta": False, "motivos": []}
assert contorno(cal, "A2")["alerta"] and len(contorno(cal, "A2")["motivos"]) == 2
assert contorno(cal, "A3")["motivos"][0].startswith("un mismo dibujo")
assert contorno(cal, "ZZ") is None

# --- tarjeta completa, sin las líneas de imágenes y sin soporte ni contorno
t = tarjeta(d, sop, cal, "A1")
assert [x["estado"] for x in t] == ["info", "info", "ok", "ojo"], t
assert [x["corto"] for x in t] == ["53 imágenes", "12 días", "Sigue la orilla", "Redondeadas a 0.5 t/ha"], t
assert t[0]["texto"] == "Sentinel-2: 10 · Planet: 40 · Landsat: 3"
assert [x["titulo"] for x in tarjeta(d, sop, cal, "A1", con_imagenes=False)] == [
    "Dibujo de la parcela", "Cosechas del municipio"]
assert tarjeta(d, sop, cal, "A2", con_imagenes=False)[0]["corto"] == "Con alerta"
assert [x["titulo"] for x in tarjeta(d, None, None, "A5")] == ["Cosechas del municipio"]
assert tarjeta(d, None, None, "P1")[0]["corto"] == "Muy pocas para saber"
print("datos inventados ✓")

# --- datos reales (si hay paquete): conteos contra soporte en 3 parcelas al azar y escalones conocidos
try:
    from agrocebada_app.backend.datos import paquete
    dr, sr = paquete.parcelas(), paquete.soporte()
except Exception as ex:  # noqa: BLE001
    dr = sr = None
    print(f"sin datos reales ({ex}); sólo se probaron los inventados")
if dr is not None and sr is not None:
    for pid in random.Random(14).sample(sorted(set(dr.index) & set(sr.index)), 3):
        im = imagenes(sr, pid)
        assert im["despejadas"]["Sentinel-2"] == sr.loc[pid, "s2_capturas_despejadas"], pid
        assert im["despejadas"]["Planet"] == sr.loc[pid, "pl_capturas_despejadas"], pid
        print(f"  {pid}: conteos iguales a soporte ✓")
    esperado = {"Calpulalpan": 0.5, "Emiliano Zapata": 0.5, "Singuilucan": 0.1, "Chignahuapan": 0.01}
    for m, paso in esperado.items():
        v = dr.loc[(dr.municipio == m) & (dr.CONJUNTO == "ENTRENAMIENTO"), "real"]
        assert escalon(v) == paso, (m, escalon(v))
    print("escalones iguales a la auditoría de T02 ✓")
print("OK")