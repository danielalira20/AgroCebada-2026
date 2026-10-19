"""Prueba del mes de mayor verdor (frase de M07):  python tests/backend/test_mes_verde.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.franja_verdor import mes_mas_verde  # noqa: E402

# municipio A: 4 parcelas con cosecha que llegan a su máximo en agosto; p5 (por estimar) en septiembre
fechas = pd.to_datetime(["2025-06-02", "2025-07-07", "2025-08-04", "2025-09-01"])
filas = []
for pid in ["p1", "p2", "p3", "p4"]:
    filas += [dict(ID_POLIGONO=pid, fecha=f, sensor="Planet", ndvi_promedio=v) for f, v in zip(fechas, [0.3, 0.5, 0.8, 0.6])]
filas += [dict(ID_POLIGONO="p5", fecha=f, sensor="Planet", ndvi_promedio=v) for f, v in zip(fechas, [0.3, 0.5, 0.6, 0.9])]
s = pd.DataFrame(filas)
d = pd.DataFrame({"municipio": ["A"] * 5, "CONJUNTO": ["ENTRENAMIENTO"] * 4 + ["PREDICCION"]},
                 index=["p1", "p2", "p3", "p4", "p5"])

assert mes_mas_verde(d, s, "p5") == ("septiembre", "agosto"), mes_mas_verde(d, s, "p5")
# con sólo 2 parcelas para comparar no hay franja: sólo el mes de la parcela
d2 = d.loc[["p1", "p2", "p5"]]
assert mes_mas_verde(d2, s[s.ID_POLIGONO.isin(d2.index)], "p5") == ("septiembre", None)
assert mes_mas_verde(d, s, "nadie") is None
print("OK")