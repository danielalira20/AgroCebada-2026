"""Pruebas de la cartera por municipio:  python tests/backend/test_cartera.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from agrocebada_app.backend.datos import lectura  # noqa: E402
from agrocebada_app.backend.dominio.cartera import COLUMNAS, cartera_municipios, totales_cartera  # noqa: E402
from agrocebada_app.backend.dominio.rangos import rangos_municipio  # noqa: E402
from agrocebada_app.backend.modelo.estimador import predecir  # noqa: E402
from agrocebada_app.backend.rutas.localizador import rutas  # noqa: E402

p = lectura.leer_parcelas(rutas()["datos"])
rangos = rangos_municipio(p[p.CONJUNTO == "ENTRENAMIENTO"])


def cerca(a, b, tol=1.0):
    return abs(a - b) <= tol


# --- con la media
t = cartera_municipios(p, predecir(p, "media_mun__resp_grupo"), rangos)
assert list(t.columns) == COLUMNAS, list(t.columns)
tot = totales_cartera(t)
assert tot["parcelas"] == 59 and cerca(tot["hectareas"], 393.6, 0.05), tot
assert cerca(tot["produccion_t"], 1550) and cerca(tot["escenario_bajo_t"], 1379) and cerca(tot["escenario_alto_t"], 1717), tot
assert tot["mezcla_confianza"] is None and t.confianza.isna().all()
esperado = {"Chignahuapan": (29, 137.4, 4.48, 615, 537, 697), "Calpulalpan": (14, 75.2, 3.00, 226, 188, 263),
            "Singuilucan": (7, 66.9, 3.08, 206, 167, 234), "Almoloya": (4, 72.4, 4.52, 327, 317, 341),
            "Cuautepec de Hinojosa": (4, 34.2, 4.60, 157, 151, 164),
            "Nanacamilpa de Mariano Arista": (1, 7.5, 2.50, 19, 19, 19)}
f = t.set_index("municipio")
for m, (n, ha, est, prod, bajo, alto) in esperado.items():
    x = f.loc[m]
    assert x.parcelas == n and cerca(x.hectareas, ha, 0.05) and cerca(x.estimacion, est, 0.005), (m, dict(x))
    assert cerca(x.produccion_t, prod) and cerca(x.escenario_bajo_t, bajo) and cerca(x.escenario_alto_t, alto), (m, dict(x))
    assert abs(x.produccion_t - x.estimacion * x.hectareas) < 1e-9
# sin rango: los dos escenarios son la producción estimada y la nota lo dice
n = f.loc["Nanacamilpa de Mariano Arista"]
assert n.tipo_rango == "sin rango" and pd.isna(n.rango_bajo) and n.escenario_bajo_t == n.escenario_alto_t == n.produccion_t
assert "Sin rango" in n.escenario_nota and f.loc["Chignahuapan", "escenario_nota"] == ""
# escenarios = rango del municipio × hectáreas
c = f.loc["Chignahuapan"]
assert abs(c.escenario_bajo_t - c.rango_bajo * c.hectareas) < 1e-9 and abs(c.escenario_alto_t - c.rango_alto * c.hectareas) < 1e-9
# la suma de la tabla coincide con los totales
assert abs(t.produccion_t.sum() - tot["produccion_t"]) < 1e-9 and abs(t.escenario_bajo_t.sum() - tot["escenario_bajo_t"]) < 1e-9
assert abs(t.escenario_alto_t.sum() - tot["escenario_alto_t"]) < 1e-9 and t.parcelas.sum() == tot["parcelas"]
assert abs(t.hectareas.sum() - tot["hectareas"]) < 1e-9 and abs(tot["hectareas"] - p[p.CONJUNTO == "PREDICCION"].AREA_HA.sum()) < 1e-9

# --- con la mediana cambia la producción, no las parcelas ni las hectáreas
tm = cartera_municipios(p, predecir(p, "mediana_mun__resp_grupo"), rangos)
totm = totales_cartera(tm)
assert totm["parcelas"] == tot["parcelas"] and abs(totm["hectareas"] - tot["hectareas"]) < 1e-9
assert abs(totm["produccion_t"] - tot["produccion_t"]) > 1, (totm, tot)
assert (tm.set_index("municipio").parcelas == f.parcelas).all()

# --- la confianza (M01), si llega, se muestra tal cual
conf = pd.DataFrame({"municipio": list(f.index), "nivel": ["alta", "alta", "media", "media", "baja", "baja"],
                     "motivo": ""})
tc = cartera_municipios(p, predecir(p, "media_mun__resp_grupo"), rangos, conf)
mezcla = totales_cartera(tc)["mezcla_confianza"]
assert sum(mezcla.values()) == 59 and set(mezcla) == {"alta", "media", "baja"}, mezcla
print("OK")
