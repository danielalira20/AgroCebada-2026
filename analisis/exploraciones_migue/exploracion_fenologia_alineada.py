"""Exploración (idea de la literatura, no de nuestros resultados; no decide nada): alinear el satélite a la etapa
del cultivo de cada parcela en vez de usar ventanas fijas de calendario.

Sin fecha de siembra, se estima el inicio de temporada (SOS) de cada parcela con Planet (la serie más densa):
NDVI suavizado (mediana móvil de 3 fechas, nubosidad <= 20 %, 1 mar - 31 oct 2025); base = percentil 5 antes del
pico; SOS = primer día en que el NDVI cruza base + 50 % de la amplitud. Atributos: el día del SOS (aproxima la
siembra) y NDVI, EVI y LAI interpolados a SOS + 30, 45 y 60 días (etapas comparables entre parcelas).

Candidatos (Ridge de T14 sobre el residuo, variables centradas por municipio, alfa en 4 internas), 5 procedimientos:
sos, ndvi_alineado, evi_alineado, lai_alineado, todo.

Uso (desde la raíz del repo del equipo):
    python exploracion_fenologia_alineada.py scripts RUTA/DATASET_RETO_AGRO_2026 registro/t03/particiones.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import t14_clima as T  # noqa: E402

DATOS, PART = Path(sys.argv[2]), sys.argv[3]
DIAS = [30, 45, 60]
d = T.cargar(DATOS)

x = pd.read_csv(DATOS / "Conjunto_datos_PRO_AgroCebada.csv")
x["f"] = pd.to_datetime(x.fecha_captura, format="%d/%m/%Y")
x = x[(x.porcentaje_nubosidad <= 20) & x.ndvi_promedio.notna() & (x.f >= "2025-03-01") & (x.f <= "2025-10-31")]
x["doy"] = x.f.dt.dayofyear


def alinear(g):
    g = g.sort_values("doy").groupby("doy", as_index=False).mean(numeric_only=True)
    s = {i: g[f"{i}_promedio"].rolling(3, center=True, min_periods=1).median().values for i in ["ndvi", "evi", "lai"]}
    doy, nd = g.doy.values, s["ndvi"]
    ip = int(np.argmax(nd))
    base = np.percentile(nd[: ip + 1], 5)
    umbral = base + 0.5 * (nd[ip] - base)
    sos = float(doy[np.argmax((nd >= umbral) & (np.arange(len(nd)) <= ip))])
    out = {"sos": sos}
    for i in ["ndvi", "evi", "lai"]:
        for k in DIAS:
            out[f"{i}_sos{k}"] = float(np.interp(sos + k, doy, s[i]))
    return pd.Series(out)


v = x.groupby("ID_POLIGONO").apply(alinear, include_groups=False)
print("parcelas con fenología:", len(v), "de", len(d), "| SOS (día del año): mediana", v.sos.median(),
      "rango", v.sos.min(), "-", v.sos.max())
d = d.join(v)
t = d[d.CONJUNTO == "ENTRENAMIENTO"]
res = t.real - t.groupby("municipio").real.transform("mean")
cen = t[v.columns] - t.groupby("municipio")[list(v.columns)].transform("mean")
print("Spearman con el residuo dentro del municipio:", cen.corrwith(res, method="spearman").round(2).to_dict())

part = pd.read_csv(PART)
celda = T.validar_particiones(part, d)
grupos = {"sos": ["sos"],
          "ndvi_alineado": [f"ndvi_sos{k}" for k in DIAS],
          "evi_alineado": [f"evi_sos{k}" for k in DIAS],
          "lai_alineado": [f"lai_sos{k}" for k in DIAS],
          "todo": list(v.columns)}
alfas = {n: [] for n in [T.BASE, *grupos]}
cands = {T.BASE: T.candidato([], alfas[T.BASE])}
cands.update({n: T.candidato(c, alfas[n], True) for n, c in grupos.items()})
oof = T.evaluar(t, part, cands, alfas)
e = T.emparejada(oof, celda)
pd.set_option("display.width", 220)
print(e[e.subconjunto == "sin_respaldo"][["escenario", "candidato", "dMAE", "IC95_celdas_inf", "IC95_celdas_sup",
                                          "reps_que_mejoran", "dRMSE", "cumple_regla_T03"]].to_string(index=False))
print("alfas:", {n: pd.Series(a).value_counts().head(3).to_dict() for n, a in alfas.items() if a})
