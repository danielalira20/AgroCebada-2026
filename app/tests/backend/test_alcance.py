"""Pruebas del alcance del método (M15):  python tests/backend/test_alcance.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio import alcance as al  # noqa: E402
from agrocebada_app.backend.dominio.confianza import MIN_ALTA, MIN_MEDIA  # noqa: E402
from agrocebada_app.backend.dominio.validacion import poblaciones  # noqa: E402

MEDIA, MEDIANA = "media_mun__resp_grupo", "mediana_mun__resp_grupo"
PROHIBIDAS = ["no sirve", "tu parcela dará"]


def val(esc, fuente, ae, e, ids, real):
    return pd.DataFrame({"escenario": esc, "fuente": fuente, "ID_POLIGONO": ids, "repeticion": 1,
                         "real": real, "ae": ae, "e": e, "municipio": "X"})


# --- validación inventada: A con municipio (0.2, 0.4), A con respaldo (1.0), B con municipio (0.5), B con respaldo (1.5)
O = pd.concat([val("A", "municipio", [0.2, 0.4], [0.2, -0.4], ["a1", "a2"], [4.0, 5.0]),
               val("A", "grupo", [1.0], [1.0], ["a3"], [3.0]),
               val("B", "municipio", [0.5, 0.5], [0.5, -0.5], ["b1", "b2"], [4.0, 5.0]),
               val("B", "grupo", [1.5], [1.5], ["b3"], [3.0])], ignore_index=True)
# --- 59 inventadas: Aa 10 parcelas (3 por estimar), Bb 4 (2), Cc 2 (1), Dd 1 (1), Ee ninguna (1)
conf = pd.DataFrame({"municipio": ["Aa", "Bb", "Cc", "Dd"], "n_cosecha": [10, 4, 2, 1]})
pred = pd.DataFrame({"municipio": ["Aa"] * 3 + ["Bb"] * 2 + ["Cc", "Dd", "Ee"], "fuente": "municipio"})

t = al.tabla_alcance(O, conf, pred)
assert len(t) == 5 and all(set(f) == set(al.COLUMNAS) for f in t)
assert [f["sirve"] for f in t] == [al.SI, al.CAUTELA, al.MUCHA, al.PARCIAL, al.NO]
assert all(f["sirve"][0] in "✔▲⚠✖" for f in t)

# --- los umbrales salen de la regla de confianza y los conteos de las estimaciones
assert f"{MIN_ALTA} o más parcelas" in t[0]["situacion"] and f"{MIN_MEDIA} a {MIN_ALTA - 1} parcelas" in t[1]["situacion"]
assert f"{MIN_MEDIA - 1} o menos" in t[2]["situacion"]
assert [f["estimaciones"] for f in t] == ["3 de las 8", "2 de las 8", "2 de las 8", "1 de las 8", "—"]

# --- los errores son los de Validación (M12): mismas poblaciones, mismas cifras
pob = poblaciones(O)
a = pob[pob.poblacion == "A · municipio conocido · sin respaldo"].iloc[0]
b = pob[pob.poblacion == "B · zona de lluvia nueva · sin respaldo"].iloc[0]
bt = pob[pob.poblacion == "B · zona de lluvia nueva · todas las predicciones"].iloc[0]
assert abs(a.MAE - 0.3) < 1e-12 and abs(b.MAE - 0.5) < 1e-12 and abs(bt.MAE - 0.8333333333) < 1e-9
assert f"{a.MAE:.3f} t/ha" in t[0]["error"] and f"{a.MAE:.3f} t/ha" in t[1]["error"]
assert f"{b.MAE:.3f} t/ha" in t[3]["error"] and f"sube a {bt.MAE:.3f} t/ha" in t[3]["error"]
assert "1.000 t/ha" in t[2]["error"]                      # error cuando el municipio no tenía cosechas (A, respaldo)

# --- sin validación no hay tabla; sin B, la fila lo dice en vez de inventar una cifra
assert al.tabla_alcance(None, conf, pred) == [] and al.tabla_alcance(O.iloc[0:0], conf, pred) == []
sin_b = al.tabla_alcance(O[O.escenario == "A"], conf, pred)
assert "No se pudo medir" in sin_b[3]["error"]
assert al._cuantas(0, 59) == "Ninguna de las 59" and al._cuantas(59, 59) == "Las 59"

# --- pasos del método: con el modelo final, no con el seleccionado
d = pd.DataFrame({"municipio": ["Aa", "Aa", "Bb", "Cc"], "CONJUNTO": ["ENTRENAMIENTO"] * 3 + ["PREDICCION"]})
p1, p2 = al.pasos(d, MEDIANA), al.pasos(d, MEDIA)
assert [n for n, _ in p1] == ["Datos", "Valor típico del municipio", "Asignación", "Validación"]
assert "3 parcelas con cosecha registrada en 2025, de 2 municipios" in p1[0][1]
assert "la mediana del rendimiento" in p1[1][1] and "la media del rendimiento" in p2[1][1]

# --- honestidad del texto
textos = " ".join(f["situacion"] + f["error"] + f["nota"] for f in t)
assert not any(x in textos.lower() for x in PROHIBIDAS), textos
assert "sólo usa cosechas de 2025" in textos

# --- error principal: las mismas cifras de Validación; por qué un modelo simple; límites
ep = al.error_principal(O)
assert abs(ep["a_mae"] - a.MAE) < 1e-12 and abs(ep["b_mae"] - b.MAE) < 1e-12 and ep["a_parcelas"] == 2 and ep["b_parcelas"] == 2
assert al.error_principal(None) is None and al.error_principal(O[O.escenario == "B"]) is None
assert al.error_principal(O[O.escenario == "A"])["b_mae"] is None
assert sum(int(f["estimaciones"].split(" ")[0]) for f in t[:4]) == len(pred)
m1, m2 = al.por_que_simple(MEDIANA), al.por_que_simple(MEDIA)
assert "excepción explícita" in m1 and "Se conserva el promedio" in m2 and "pestaña Evidencia" in m1 and "pestaña Evidencia" in m2
assert "cerca de 20" not in m1 and not any(ch.isdigit() for ch in m1), m1       # no afirma cuántas variantes se probaron
from agrocebada_app.backend.dominio.desglose import NO_VE  # noqa: E402
lim = al.limites()
assert any(NO_VE in x for x in lim) and not any("explican buena parte" in x for x in lim)
assert any("retrospectiva de 2025" in x for x in lim) and not any(p in " ".join(lim).lower() for p in PROHIBIDAS)

print("OK")
