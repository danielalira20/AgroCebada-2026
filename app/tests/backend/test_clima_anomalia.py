"""Prueba la comparación de clima 2025 contra 2022–2024 con datos inventados (no usa el dataset)."""
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # app/

from agrocebada_app.backend.datos.lectura import leer_clima_normal  # noqa: E402
from agrocebada_app.backend.dominio.clima_anomalia import comparar, frases  # noqa: E402

# 2025 contra lo normal: agosto 25 % más seco, julio con días 1.5 °C más calurosos,
# marzo con +140 % de lluvia pero sólo 7 mm de diferencia (no debe decir nada)
c = pd.DataFrame({"id_parcela": "P1", "periodo": ["2025-03", "2025-07", "2025-08"],
                  "PREC": [12.0, 105.0, 75.0], "Tmax": [22.0, 25.5, 24.0], "Tmin": [5.0, 10.0, 10.0]})
cn = pd.DataFrame({"id_parcela": "P1", "mes": [3, 7, 8],
                   "PREC": [5.0, 100.0, 100.0], "Tmax": [22.0, 24.0, 24.0], "Tmin": [5.0, 10.0, 10.0]})

t = comparar(c, cn, "P1")
assert list(t.mes) == [3, 7, 8]
f = frases(t)
assert f == ["En julio, los días fueron 1.5 °C más calurosos que el promedio 2022–2024.",
             "Agosto fue 25 % más seco que el promedio 2022–2024 en tu zona."], f
assert comparar(c, None, "P1") is None
assert comparar(c, cn, "OTRA") is None
assert frases(None) == []

# más del doble de lluvia: se dice en veces, no en %
t2 = comparar(c.assign(PREC=[12.0, 300.0, 75.0]), cn, "P1")
assert "En julio cayó 3.0 veces la lluvia promedio de 2022–2024 en tu zona." in frases(t2), frases(t2)

# leer_clima_normal: promedia sólo 2022–2024 y sólo marzo a octubre
filas = []
for anio, lluvia in [(2022, 90), (2023, 100), (2024, 110), (2025, 999)]:
    for mes in [1, 8]:
        for var, val in [("PREC", lluvia), ("Tmax", 24.0), ("Tmin", 9.0)]:
            filas.append(dict(id_parcela="P1", periodo=f"{anio}-{mes:02d}", variable=var, media_ponderada=val))
with tempfile.TemporaryDirectory() as tmp:
    ruta = Path(tmp) / "clima.csv"
    pd.DataFrame(filas).to_csv(ruta, index=False)
    n = leer_clima_normal(ruta)
assert list(n.mes) == [8], n
assert n.PREC.iloc[0] == 100 and n.Tmax.iloc[0] == 24.0, n
print("OK")