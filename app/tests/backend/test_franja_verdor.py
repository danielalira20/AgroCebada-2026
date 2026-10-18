"""Pruebas de la franja de verdor:  python tests/backend/test_franja_verdor.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.franja_verdor import franja_municipio, sensor_para  # noqa: E402

# municipio A: 4 parcelas con cosecha y 1 por estimar; municipio B: 2 con cosecha
d = pd.DataFrame({"municipio": ["A", "A", "A", "A", "A", "B", "B"],
                  "CONJUNTO": ["ENTRENAMIENTO"] * 4 + ["PREDICCION", "ENTRENAMIENTO", "ENTRENAMIENTO"]},
                 index=["p1", "p2", "p3", "p4", "p5", "q1", "q2"])
martes = pd.Timestamp("2025-07-08")          # su semana empieza el lunes 7 de julio
s = pd.DataFrame({"ID_POLIGONO": ["p1", "p2", "p3", "p4", "p5", "q1", "q2"], "fecha": [martes] * 7,
                  "sensor": ["Planet"] * 7, "ndvi_promedio": [0.2, 0.4, 0.6, 0.8, 0.99, 0.5, 0.5]})

# la parcela por estimar (p5) no entra en la franja; las 4 con cosecha sí
f = franja_municipio(d, s, "p5")
assert f is not None and len(f) == 1, f
assert f.semana.iloc[0] == pd.Timestamp("2025-07-07"), f.semana.iloc[0]
assert f.n.iloc[0] == 4, f
assert abs(f.p25.iloc[0] - 0.35) < 1e-9 and abs(f.p75.iloc[0] - 0.65) < 1e-9, f

# una parcela con cosecha no se compara consigo misma: para p1 quedan p2, p3 y p4
assert franja_municipio(d, s, "p1").n.iloc[0] == 3

# municipio con menos de 3 parcelas para comparar: sin franja
assert franja_municipio(d, s, "q1") is None

# sensor: Planet si hay suficientes capturas; si no, el que tenga datos; None si no hay datos
assert sensor_para(s, "p1", minimo=1) == "Planet"
s2 = pd.DataFrame({"ID_POLIGONO": ["z"], "fecha": [martes], "sensor": ["Sentinel-2"], "ndvi_promedio": [0.3]})
assert sensor_para(s2, "z") == "Sentinel-2"
assert sensor_para(s2, "otra") is None
print("OK")