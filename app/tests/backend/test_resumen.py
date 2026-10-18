"""Pruebas del recuadro del mapa (M04):  python tests/backend/test_resumen.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.confianza import confianza_municipios  # noqa: E402
from agrocebada_app.backend.dominio.resumen import detalles  # noqa: E402

# Aa: 3 parcelas con cosecha (confianza media) y una por estimar; Bb: sólo 1 con cosecha (baja) y una por estimar con
# respaldo del grupo
d = pd.DataFrame({
    "municipio": ["Aa", "Aa", "Aa", "Aa", "Bb", "Bb"],
    "CONJUNTO": ["ENTRENAMIENTO"] * 3 + ["PREDICCION", "ENTRENAMIENTO", "PREDICCION"],
    "real": [4.0, 5.0, 4.6, np.nan, 3.0, np.nan], "AREA_HA": [1.0, 2.0, 1.5, 2.0, 1.0, 3.0]},
    index=["p1", "p2", "p3", "p4", "p5", "p6"])
pred = pd.DataFrame({"municipio": ["Aa", "Bb"], "prediccion": [4.5, 3.0], "fuente": ["municipio", "grupo"],
                     "n_municipio": [3, 1], "error_tipico": [0.3, 0.5], "aviso": ["", "pocas parcelas"]},
                    index=["p4", "p6"])
conf = confianza_municipios(d, None)
oof = pd.Series({"p1": 4.1})
det = detalles(d, pred, oof, conf)

assert set(det) == set(d.index)
a = det["p4"].split("\n")
assert a[0] == "Estimación: 4.50 t/ha · Confianza media", a
assert a[1] == "Área: 2.00 ha · producción 9.0 t" and a[2] == "Base: 3 parcelas con cosecha de Aa"
assert a[3].startswith("Las 3 parcelas con cosecha de Aa dieron entre 4.00 y 5.00 t/ha") and len(a) == 4, a
b = det["p6"].split("\n")
assert b[0] == "Estimación: 3.00 t/ha · Confianza baja" and "respaldo por grupo" in b[2], b
assert b[3].startswith("Bb sólo tiene 1 parcela con cosecha") and b[4] == "Aviso: pocas parcelas", b
# ya no aparece el error típico, y las parcelas con cosecha siguen igual
for pid, t in det.items():
    assert "error típico" not in t.lower() and "±" not in t and "tu parcela dará" not in t.lower(), t
assert det["p1"] == "Rendimiento registrado: 4.00 t/ha\nLo que estimó el método sin conocerla: 4.10 t/ha\nÁrea: 1.00 ha"
assert det["p2"] == "Rendimiento registrado: 5.00 t/ha\nÁrea: 2.00 ha"
print("OK")
