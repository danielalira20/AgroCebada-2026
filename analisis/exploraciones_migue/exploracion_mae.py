"""Exploración orientada al MAE (no decide nada): estimadores robustos y jerárquicos, con particiones y regla de T03
contra la referencia `media_mun__resp_grupo`.

Candidatos (todos con respaldo grupo -> global):
- mediana_mun: mediana del municipio (la de T08, como control).
- media_recortada: media recortada al 20 % por municipio (entre la media y la mediana).
- mediana_celda: jerarquía municipio -> celda CHIRPS dentro del municipio (estimación de áreas pequeñas):
  w * mediana(municipio, celda) + (1 - w) * mediana(municipio), w = n_celda / (n_celda + k), k elegido en 4 internas.
- mediana_lad_clima: mediana del municipio + regresión de mediana (LAD, cuantil 0.5, penalización L1 elegida en
  internas) del residuo (real - mediana municipal sin la fila) con las 6 variables de clima de T14 centradas por municipio.

Uso (desde la raíz del repo del equipo):
    python exploracion_mae.py scripts RUTA/DATASET registro/t03/particiones.csv RUTA/variables_clima_t14.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import trim_mean
from sklearn.linear_model import QuantileRegressor
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import t14_clima as T  # noqa: E402

DATOS, PART, CLIMA = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
d = T.cargar(DATOS).join(pd.read_csv(CLIMA, index_col=0))
part = pd.read_csv(PART)
celda = T.validar_particiones(part, d)
d["celda"] = celda.reindex(d.index)
t = d[d.CONJUNTO == "ENTRENAMIENTO"]
CLIM = T.GRUPOS["clima"]


def estadistico(f):
    """Referencia con el estadístico f por municipio; respaldo grupo -> global (como T08)."""
    def predecir(tr, te):
        mun, grp = tr.groupby("municipio").real.agg(f), tr.groupby("grupo_registro").real.agg(f)
        p = te.municipio.map(mun)
        fuente = np.where(p.notna(), "municipio", np.where(te.grupo_registro.map(grp).notna(), "grupo", "global"))
        p = p.fillna(te.grupo_registro.map(grp)).fillna(f(tr.real))
        return p.values, fuente
    return predecir


MEDIANA = estadistico(np.median)


def internas(tr):
    return StratifiedKFold(T.N_INTERNAS, shuffle=True, random_state=T.SEMILLA_INTERNA).split(tr, T.estratos(tr))


def elegir(tr, opciones, f):
    err = {o: [] for o in opciones}
    for i, j in internas(tr):
        a, va = tr.iloc[i], tr.iloc[j]
        keep = T.REF(a, va)[1] == "municipio"
        for o in opciones:
            err[o].append(np.abs(f(a, va, o) - va.real.values)[keep])
    mae = {o: np.concatenate(e).mean() for o, e in err.items()}
    return min(mae, key=lambda o: round(mae[o], 6))       # empate -> la primera (la más conservadora)


def celda_mun(tr, te, k):
    base, _ = MEDIANA(tr, te)
    if k == np.inf:
        return base
    g = tr.groupby(["municipio", "celda"]).real.agg(["median", "size"])
    key = pd.MultiIndex.from_arrays([te.municipio, te.celda])
    med, n = g["median"].reindex(key).values, g["size"].reindex(key).fillna(0).values
    w = n / (n + k)
    return np.where(np.isnan(med), base, w * np.nan_to_num(med) + (1 - w) * base)


def mediana_loo(tr):
    out = []
    for i, (m, g) in enumerate(zip(tr.municipio, tr.grupo_registro)):
        otros = tr.real.drop(tr.index[i])
        mm = otros[tr.municipio.drop(tr.index[i]) == m]
        mg = otros[tr.grupo_registro.drop(tr.index[i]) == g]
        out.append(mm.median() if len(mm) else (mg.median() if len(mg) else otros.median()))
    return np.array(out)


def lad(tr, te, a):
    base, _ = MEDIANA(tr, te)
    c = T.centros(tr, CLIM)
    xtr = T.restar_centro(tr, CLIM, c)
    mu, sd = xtr.mean(), xtr.std(ddof=0).replace(0, 1)
    m = QuantileRegressor(quantile=0.5, alpha=a, solver="highs").fit((xtr - mu) / sd, tr.real.values - mediana_loo(tr))
    return base + m.predict((T.restar_centro(te, CLIM, c) - mu) / sd)


elegidas = {"mediana_celda": [], "mediana_lad_clima": []}


def con_internas(nombre, f, opciones):
    def predecir(tr, te):
        o = elegir(tr, opciones, f)
        elegidas[nombre].append(o)
        return f(tr, te, o), T.REF(tr, te)[1]
    return predecir


cands = {T.BASE: T.candidato([], []),
         "mediana_mun": MEDIANA,
         "media_recortada": estadistico(lambda s: trim_mean(s, 0.2)),
         "mediana_celda": con_internas("mediana_celda", celda_mun, [np.inf, 30, 10, 3, 1]),
         "mediana_lad_clima": con_internas("mediana_lad_clima", lad, [1.0, 0.1, 0.01, 0.001])}
oof = T.evaluar(t, part, cands, {n: [] for n in cands})
e = T.emparejada(oof, celda)
pd.set_option("display.width", 220)
print(T.resumir(oof).to_string(index=False))
print(e[e.subconjunto == "sin_respaldo"][["escenario", "candidato", "dMAE", "IC95_celdas_inf", "IC95_celdas_sup",
                                          "reps_que_mejoran", "dRMSE", "cumple_regla_T03"]].to_string(index=False))
print("opciones elegidas:", {n: pd.Series([str(o) for o in x]).value_counts().to_dict() for n, x in elegidas.items()})
