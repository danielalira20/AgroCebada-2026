"""Pruebas de la calculadora «¿me alcanza?» (M05):  python tests/backend/test_calculadora.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.dominio.calculadora import (columnas, cuentas, equilibrio, frase_equilibrio,  # noqa: E402
                                                         rango_municipio)
from agrocebada_app.backend.dominio.rangos import ANIO  # noqa: E402

# --- el caso del plan, comparado con la cuenta a mano: 5 ha, 4.48 t/ha, $6,000 por t, $18,000 por ha
t = cuentas([("Con la estimación", 4.48)], area=5, precio=6000, costo_ha=18000)
c = t["Con la estimación"]
assert abs(c["Producción (t)"] - 22.4) < 1e-9           # 4.48 × 5
assert abs(c["Ingreso"] - 134400) < 1e-6                 # 22.4 × 6,000
assert c["Costo"] == 90000                               # 18,000 × 5
assert abs(c["Ingreso menos costo"] - 44400) < 1e-6
assert c["¿Cubre costos?"] == "Sí"
assert equilibrio(6000, 18000) == 3.0                    # 18,000 ÷ 6,000
assert equilibrio(0, 18000) is None and equilibrio(None, 18000) is None
assert cuentas([("x", 2.0)], 5, 6000, 18000)["x"]["¿Cubre costos?"] == "No"
assert cuentas([("x", 3.0)], 5, 6000, 18000)["x"]["¿Cubre costos?"] == "Sí"   # justo en el equilibrio cubre

# --- datos inventados: M con 10 parcelas (P10–P90), T con 3 (mínimo–máximo), U con 1 (sin rango)
d = pd.DataFrame({"municipio": ["M"] * 11 + ["T"] * 3 + ["U"],
                  "CONJUNTO": ["ENTRENAMIENTO"] * 10 + ["PREDICCION"] + ["ENTRENAMIENTO"] * 4,
                  "real": [float(i) for i in range(1, 11)] + [np.nan, 2.0, 3.0, 5.0, 3.0]})
assert [n for n, _ in columnas(4.0, "Con la estimación", rango_municipio(d, "M"))] == [
    "Con la estimación", "Año bajo en tu municipio", "Año alto en tu municipio"]
assert [n for n, _ in columnas(4.0, "e", rango_municipio(d, "T"))] == ["e", "La más baja de tu municipio",
                                                                        "La más alta de tu municipio"]
assert columnas(4.0, "e", rango_municipio(d, "T"))[1:] == [("La más baja de tu municipio", 2.0),
                                                           ("La más alta de tu municipio", 5.0)]
assert len(columnas(4.0, "e", rango_municipio(d, "U"))) == 1
assert rango_municipio(d, "M")["n_cosecha"] == 10          # la parcela por estimar no cuenta

# --- frases del equilibrio
assert frase_equilibrio(d, "M", 3.0) == (f"Para cubrir el costo necesitas al menos 3.00 t/ha. En {ANIO}, 8 de cada 10 "
                                         "parcelas con cosecha de M llegaron a ese rendimiento.")
assert frase_equilibrio(d, "T", 3.0).endswith(f"En {ANIO}, 2 de las 3 parcelas con cosecha de T llegaron a ese rendimiento.")
assert frase_equilibrio(d, "U", 4.0).endswith("la única parcela con cosecha de U no llegó a ese rendimiento.")
assert "no tiene parcelas con cosecha" in frase_equilibrio(d, "Nada", 3.0)
assert frase_equilibrio(d, "M", 0.5).endswith("las 10 parcelas con cosecha de M llegaron a ese rendimiento.")
assert frase_equilibrio(d, "M", 20).endswith("ninguna de las 10 parcelas con cosecha de M llegó a ese rendimiento.")
assert frase_equilibrio(d, "M", 10.0).endswith("1 de cada 10 parcelas con cosecha de M llegaron a ese rendimiento.")
print("datos inventados ✓")

# --- datos reales (si hay paquete): Chignahuapan tiene rango P10–P90 y la frase va «de cada 10»
try:
    from agrocebada_app.backend.datos import paquete
    dr = paquete.parcelas()
except Exception as ex:  # noqa: BLE001
    dr = None
    print(f"sin datos reales ({ex}); sólo se probaron los inventados")
if dr is not None:
    r = rango_municipio(dr, "Chignahuapan")
    assert r["tipo_rango"] == "P10–P90" and len(columnas(4.48, "e", r)) == 3, r
    assert "de cada 10" in frase_equilibrio(dr, "Chignahuapan", 4.5)
    assert len(columnas(3.0, "e", rango_municipio(dr, "Apan"))) == 1      # una sola parcela: sin rango
    print("Chignahuapan y Apan con datos reales ✓")
print("OK")