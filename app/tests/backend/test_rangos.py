"""Pruebas del rango de cosechas reales por municipio:  python tests/backend/test_rangos.py  (desde app/)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from agrocebada_app.backend.datos import lectura  # noqa: E402
from agrocebada_app.backend.dominio.rangos import COLUMNAS, cerca_del_municipio, rango_de, rangos_municipio  # noqa: E402
from agrocebada_app.backend.rutas.localizador import rutas  # noqa: E402

# --- datos inventados: un municipio de 1, uno de 3 y uno de 10 parcelas
d = pd.DataFrame({"municipio": ["U"] + ["T"] * 3 + ["D"] * 10,
                  "real": [3.0, 1.0, 2.0, 4.0] + [float(i) for i in range(1, 11)]})
t = rangos_municipio(d).set_index("municipio")
assert list(rangos_municipio(d).columns) == COLUMNAS
assert t.loc["U", "tipo_rango"] == "sin rango" and np.isnan(t.loc["U", "bajo"]) and np.isnan(t.loc["U", "alto"])
assert t.loc["U", "texto"] == "U sólo tiene 1 parcela con cosecha: no alcanza para dar un rango.", t.loc["U", "texto"]
assert t.loc["T", "tipo_rango"] == "mínimo–máximo" and (t.loc["T", "bajo"], t.loc["T", "alto"]) == (1.0, 4.0)
assert t.loc["T", "dentro"] == 3 and t.loc["T", "texto"] == "Las 3 parcelas con cosecha de T dieron entre 1.00 y 4.00 t/ha en 2025."
assert t.loc["D", "tipo_rango"] == "P10–P90"
assert abs(t.loc["D", "bajo"] - np.percentile(range(1, 11), 10)) < 1e-9 and abs(t.loc["D", "alto"] - 9.1) < 1e-9
assert t.loc["D", "dentro"] == 8 and t.loc["D", "texto"] == "En D, 8 de 10 parcelas con cosecha dieron entre 1.90 y 9.10 t/ha en 2025."
# dos parcelas: sin rango, en plural; sin parcelas: fila que lo explica
assert "sólo tiene 2 parcelas" in rango_de(pd.DataFrame({"municipio": ["Z", "Z"], "real": [1.0, 2.0]}), "Z")["texto"]
r0 = rango_de(d, "Nada")
assert r0["tipo_rango"] == "sin rango" and r0["n_cosecha"] == 0 and "no tiene parcelas con cosecha" in r0["texto"]
# parcelas sin rendimiento registrado no cuentan
assert rangos_municipio(pd.concat([d, pd.DataFrame({"municipio": ["T"], "real": [np.nan]})])).set_index("municipio").loc["T", "n_cosecha"] == 3

# --- datos del reto
datos = rutas()["datos"]
p = lectura.leer_parcelas(datos)
cosecha = p[p.CONJUNTO == "ENTRENAMIENTO"]
r = rangos_municipio(cosecha).set_index("municipio")
esperado = {"Chignahuapan": (3.91, 5.07, 57, 71, "P10–P90"), "Calpulalpan": (2.50, 3.50, 30, 30, "P10–P90"),
            "Singuilucan": (2.50, 3.50, 14, 16, "P10–P90"), "Almoloya": (4.38, 4.71, 8, 10, "P10–P90"),
            "Cuautepec de Hinojosa": (4.40, 4.79, 5, 5, "mínimo–máximo")}
for m, (lo, hi, dentro, n, tipo) in esperado.items():
    f = r.loc[m]
    assert (round(f.bajo, 2), round(f.alto, 2), f.dentro, f.n_cosecha, f.tipo_rango) == (lo, hi, dentro, n, tipo), (m, dict(f))
assert r.loc["Chignahuapan", "texto"] == "En Chignahuapan, 57 de 71 parcelas con cosecha dieron entre 3.91 y 5.07 t/ha en 2025."
assert r.loc["Cuautepec de Hinojosa", "texto"] == "Las 5 parcelas con cosecha de Cuautepec de Hinojosa dieron entre 4.40 y 4.79 t/ha en 2025."
ez = r.loc["Emiliano Zapata"]
assert ez.n_cosecha == 3 and ez.bajo == ez.alto == 3.5 and ez.dentro == 3
assert ez.texto == "Las 3 parcelas con cosecha de Emiliano Zapata dieron 3.5 t/ha en 2025.", ez.texto
for m in ("Nanacamilpa de Mariano Arista", "Apan", "Tepeapulco"):
    assert r.loc[m, "tipo_rango"] == "sin rango" and r.loc[m, "n_cosecha"] == 1, m
assert r.loc["Nanacamilpa de Mariano Arista", "texto"] == "Nanacamilpa de Mariano Arista sólo tiene 1 parcela con cosecha: no alcanza para dar un rango."
assert not r.texto.str.contains("tu parcela dará|de cada 10", regex=True).any()

# el rango sale sólo de la cosecha registrada: ni las estimaciones ni el modelo lo mueven
con_otras_cols = cosecha.assign(prediccion=99.0, modelo="mediana_mun__resp_grupo")
assert rangos_municipio(con_otras_cols).equals(rangos_municipio(cosecha))
assert rango_de(cosecha, "Chignahuapan") == rangos_municipio(cosecha).set_index("municipio", drop=False).loc["Chignahuapan"].to_dict()

# --- cerca del valor del municipio (con la media)
for dist, estricto, esp in ((0.5, True, 72), (0.5, False, 83), (0.6, True, 88)):
    pct, frase = cerca_del_municipio(cosecha, "media", dist, estricto)
    assert round(pct) == esp, (dist, estricto, pct)
    assert f"{esp} %" in frase and ("a menos de" if estricto else "o menos") in frase and "media" in frase, frase
assert "mediana" in cerca_del_municipio(cosecha, "mediana", 0.5)[1]
print("OK")
