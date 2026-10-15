"""Exploración posterior (vista después de T09–T15, no decide nada): dos ideas nuevas contra la referencia.

1. Vecinas: referencia + w × (promedio de las etiquetadas del mismo municipio a < 20 m del borde − media municipal),
   con w elegido en 4 internas (MAE en sin_respaldo; empate → w menor). Sólo usa etiquetas del entrenamiento.
2. Historial: NDVI de Sentinel-2 (p90 y media, abr–oct, nubosidad ≤ 20 %) promediado en 2022–2024, como "potencial
   productivo" de la parcela, con la corrección Ridge de T14 (sin centrar y centrado).

Uso (desde la raíz del repo del equipo):
    python exploracion_vecinas_historial.py scripts RUTA/DATASET_RETO_AGRO_2026 registro/t03/particiones.csv RUTA/Parcelas.shp
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import t14_clima as T  # noqa: E402

DATOS, PART, SHP = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
DIST, WS = 20.0, [0, 0.25, 0.5, 0.75, 1.0]
d = T.cargar(DATOS)
part = pd.read_csv(PART)
celda = T.validar_particiones(part, d)
t = d[d.CONJUNTO == "ENTRENAMIENTO"]

g = gpd.read_file(SHP).to_crs(32614).set_index("ID_POLIGON").geometry.loc[t.index]
M = np.array([[a.distance(b) for b in g] for a in g])
np.fill_diagonal(M, np.inf)
D = pd.DataFrame(M, index=t.index, columns=t.index)


def vecinas(tr, te, w):
    base, fuente = T.REF(tr, te)
    mun = tr.groupby("municipio").real.mean()
    c = np.zeros(len(te))
    for k, (i, m) in enumerate(zip(te.index, te.municipio)):
        cand = tr.index[(tr.municipio == m).values]
        cerca = cand[(D.loc[i, cand] < DIST).values] if len(cand) else cand
        if len(cerca):
            c[k] = tr.loc[cerca, "real"].mean() - mun[m]
    return base + w * c, fuente


def candidato_vecinas(ws):
    def predecir(tr, te):
        err = {w: [] for w in WS}
        for i, j in StratifiedKFold(T.N_INTERNAS, shuffle=True, random_state=T.SEMILLA_INTERNA).split(tr, T.estratos(tr)):
            a, v = tr.iloc[i], tr.iloc[j]
            for w in WS:
                p, f = vecinas(a, v, w)
                err[w].append(np.abs(p - v.real.values)[f == "municipio"])
        mae = {w: np.concatenate(e).mean() for w, e in err.items()}
        w = min(mae, key=lambda x: (round(mae[x], 6), x))
        ws.append(w)
        return vecinas(tr, te, w)
    return predecir


x = pd.read_csv(DATOS / "Conjunto_datos_BASICO_AgroCebada2026.csv",
                usecols=["ID_POLIGONO", "fecha_captura", "sensor", "ndvi_promedio", "porcentaje_nubosidad"])
x = x[(x.sensor == "Sentinel-2") & (x.porcentaje_nubosidad <= 20) & x.ndvi_promedio.notna()]
x["f"] = pd.to_datetime(x.fecha_captura, format="%d/%m/%Y")
x = x[x.f.dt.month.between(4, 10) & x.f.dt.year.between(2022, 2024)]
anual = x.groupby(["ID_POLIGONO", x.f.dt.year]).ndvi_promedio
d = d.join(pd.DataFrame({"hist_p90": anual.quantile(0.9).groupby(level=0).mean(),
                         "hist_media": anual.mean().groupby(level=0).mean()}))
t = d[d.CONJUNTO == "ENTRENAMIENTO"]

ws, alfas = [], {"historial": [], "historial_centrado": []}
cands = {T.BASE: T.candidato([], []),
         "vecinas_20m": candidato_vecinas(ws),
         "historial": T.candidato(["hist_p90", "hist_media"], alfas["historial"]),
         "historial_centrado": T.candidato(["hist_p90", "hist_media"], alfas["historial_centrado"], True)}
oof = T.evaluar(t, part, cands, {**alfas, T.BASE: [], "vecinas_20m": []})
e = T.emparejada(oof, celda)
pd.set_option("display.width", 220)
print(e[e.subconjunto == "sin_respaldo"][["escenario", "candidato", "dMAE", "IC95_celdas_inf", "IC95_celdas_sup",
                                          "reps_que_mejoran", "dRMSE", "cumple_regla_T03"]].to_string(index=False))
print("w elegidos (vecinas):", pd.Series(ws).value_counts().to_dict())
