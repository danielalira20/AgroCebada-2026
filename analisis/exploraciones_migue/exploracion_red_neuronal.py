"""Exploración (sugerencia del profe, no decide nada): red neuronal pequeña (perceptrón multicapa) con los mismos
117 atributos de exploracion_atributos_arbol_pca.py, particiones y regla de T03.

Candidatos (opciones elegidas en 4 internas por MAE en sin_respaldo; empate -> la más simple):
- red_rendimiento: la red predice el rendimiento directo con municipio (one-hot) + atributos estandarizados.
- red_residuo: referencia + red sobre el residuo LOO con los atributos centrados por municipio y estandarizados.
Opciones: 4 u 16 neuronas en una capa oculta; regularización L2 alfa en {1, 10, 100, 1000}; solver lbfgs.

Uso (desde la raíz del repo del equipo; reutiliza la tabla de atributos de exploracion_atributos_arbol_pca.py):
    python exploracion_red_neuronal.py scripts RUTA/DATASET registro/t03/particiones.csv RUTA/atributos_117.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.model_selection import StratifiedKFold
from sklearn.neural_network import MLPRegressor

warnings.filterwarnings("ignore", category=ConvergenceWarning)
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import t14_clima as T  # noqa: E402

DATOS, PART, ATR_CSV = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
v = pd.read_csv(ATR_CSV, index_col=0)
ATR = list(v.columns)
d = T.cargar(DATOS).join(v)
part = pd.read_csv(PART)
celda = T.validar_particiones(part, d)
t = d[d.CONJUNTO == "ENTRENAMIENTO"]
MUNS = sorted(d.municipio.unique())
OPC = [(h, a) for h in (4, 16) for a in (1000, 100, 10, 1)]   # de la más simple a la más flexible


def red(h, a):
    return MLPRegressor(hidden_layer_sizes=(h,), alpha=a, solver="lbfgs", max_iter=500, random_state=0)


def red_y(tr, te, o):
    def x(z):
        return pd.concat([z[ATR], pd.get_dummies(z.municipio).reindex(columns=MUNS, fill_value=0).astype(float)], axis=1)
    xtr, xte = x(tr), x(te)
    mu, sd = xtr.mean(), xtr.std(ddof=0).replace(0, 1)
    return red(*o).fit((xtr - mu) / sd, tr.real.values).predict((xte - mu) / sd)


def red_r(tr, te, o):
    c = T.centros(tr, ATR)
    xtr = T.restar_centro(tr, ATR, c)
    mu, sd = xtr.mean(), xtr.std(ddof=0).replace(0, 1)
    m = red(*o).fit((xtr - mu) / sd, tr.real.values - T.ref_loo(tr))
    return T.REF(tr, te)[0] + m.predict((T.restar_centro(te, ATR, c) - mu) / sd)


elegidas = {"red_rendimiento": [], "red_residuo": []}


def candidato(nombre, f):
    def predecir(tr, te):
        err = {o: [] for o in OPC}
        for i, j in StratifiedKFold(T.N_INTERNAS, shuffle=True, random_state=T.SEMILLA_INTERNA).split(tr, T.estratos(tr)):
            a, va = tr.iloc[i], tr.iloc[j]
            keep = T.REF(a, va)[1] == "municipio"
            for o in OPC:
                err[o].append(np.abs(f(a, va, o) - va.real.values)[keep])
        mae = {o: np.concatenate(e).mean() for o, e in err.items()}
        o = min(mae, key=lambda k: round(mae[k], 6))
        elegidas[nombre].append(o)
        return f(tr, te, o), T.REF(tr, te)[1]
    return predecir


cands = {T.BASE: T.candidato([], []), "red_rendimiento": candidato("red_rendimiento", red_y),
         "red_residuo": candidato("red_residuo", red_r)}
oof = T.evaluar(t, part, cands, {n: [] for n in cands})
e = T.emparejada(oof, celda)
pd.set_option("display.width", 220)
print(T.resumir(oof).to_string(index=False))
print(e[e.subconjunto == "sin_respaldo"][["escenario", "candidato", "dMAE", "IC95_celdas_inf", "IC95_celdas_sup",
                                          "reps_que_mejoran", "dRMSE", "cumple_regla_T03"]].to_string(index=False))
print("opciones elegidas:", {n: pd.Series([str(o) for o in x]).value_counts().head(4).to_dict() for n, x in elegidas.items()})
