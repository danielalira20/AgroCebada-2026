"""T14 · Variable climática: ¿cuál aporta más sobre la referencia, lluvia, Tmin o Tmax?

Uso (desde la raíz del repo):
    python scripts/t14_clima.py --datos RUTA/DATASET_RETO_AGRO_2026 \
        --clima registro/t04/clima_parcela_mes.csv \
        --particiones registro/t03/particiones.csv --salida RUTA/SALIDA

Protocolo (T03 y D019):
- Referencia: media_mun__resp_grupo (media del municipio; respaldo por grupo de registro y luego global).
- Candidatos definidos antes de ver resultados: la referencia sola y la referencia + una corrección Ridge
  del residuo con lluvia, Tmin, Tmax o las tres. El residuo de cada fila de entrenamiento usa una
  referencia calculada dejando fuera esa fila (T03 §5).
- α de Ridge ∈ ALFAS (6 configuraciones ≤ 8), elegido con 4 particiones internas estratificadas por
  municipio (estrato «otros» si hay < 4 etiquetas). Escalado ajustado dentro de cada entrenamiento.
- Variables: temporada 2025 con corte al 31 de octubre (sólo meses con posterior_al_corte = False).
  Etapa temprana = abril–junio y tardía = julio–octubre. PREC se suma; Tmin y Tmax se promedian.
- Comparación emparejada contra la referencia en los subconjuntos `todas` y `sin_respaldo`;
  la decisión se toma en `sin_respaldo`, con IC95 por bloques de celdas CHIRPS.

Genera en --salida:
    variables_clima_t14.csv               las 6 variables de temporada por parcela (197 filas)
    predicciones_oof_t14_<candidato>.csv  formato T03 §7 con columna fuente, escenarios A y B
    metricas_t14.csv                      MAE, RMSE, sesgo y R² por candidato y escenario
    comparacion_emparejada_t14.csv        ΔMAE frente a la referencia, IC95 y regla T03
    alfas_t14.csv                         α elegido en cada ajuste
    colinealidad_t14.csv                  correlaciones entre las 6 variables y VIF
    escala_compartida_t14.csv             cuántos valores climáticos distintos hay realmente
    predicciones_59_t14.csv               ajuste con las 138 etiquetas para las 59 reservadas
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t08_referencias import cargar, metricas, referencia  # noqa: E402

warnings.filterwarnings("ignore", message="The least populated class")

VERSION = "T14-v1"
BASE = "referencia"
ALFAS = [0.1, 1, 10, 100, 1000, 10000]
N_INTERNAS = 4
SEMILLA_INTERNA = 0
N_BOOT = 5000
SEMILLA_BOOT = 20261006
TEMPRANA = ["2025-04", "2025-05", "2025-06"]
TARDIA = ["2025-07", "2025-08", "2025-09", "2025-10"]
GRUPOS = {
    "lluvia": ["prec_temprana", "prec_tardia"],
    "tmin": ["tmin_temprana", "tmin_tardia"],
    "tmax": ["tmax_temprana", "tmax_tardia"],
}
GRUPOS["clima"] = GRUPOS["lluvia"] + GRUPOS["tmin"] + GRUPOS["tmax"]
REF = referencia("media", "grupo")


# ---------------------------------------------------------------- variables
def variables_clima(ruta: Path) -> pd.DataFrame:
    c = pd.read_csv(ruta)
    c = c[~c.posterior_al_corte.astype(str).str.lower().eq("true")]
    out = {}
    for etapa, meses in [("temprana", TEMPRANA), ("tardia", TARDIA)]:
        n = c[c.periodo.isin(meses)].groupby(["id_parcela", "variable"]).media_ponderada.count().unstack()
        assert (n == len(meses)).all().all(), f"faltan meses de clima en la etapa {etapa}"
        x = c[c.periodo.isin(meses)].groupby(["id_parcela", "variable"]).media_ponderada
        out[f"prec_{etapa}"] = x.sum().unstack()["PREC"]
        out[f"tmin_{etapa}"] = x.mean().unstack()["Tmin"]
        out[f"tmax_{etapa}"] = x.mean().unstack()["Tmax"]
    v = pd.DataFrame(out)[GRUPOS["clima"]]
    v.index.name = "ID_POLIGONO"
    return v


# ---------------------------------------------------------------- modelo
def ref_loo(tr):
    """Referencia de cada fila de entrenamiento calculada sin esa fila (media municipal → grupo → global)."""
    y = tr.real
    def sin_fila(clave):
        s = tr.groupby(clave).real.transform("sum") - y
        n = tr.groupby(clave).real.transform("count") - 1
        return (s / n).where(n > 0)
    out = sin_fila("municipio").fillna(sin_fila("grupo_registro"))
    return out.fillna((y.sum() - y) / (len(y) - 1)).values


def ajustar(tr, cols, alfa):
    r = tr.real.values - ref_loo(tr)
    mu, sd = tr[cols].mean(), tr[cols].std(ddof=0).replace(0, 1)
    m = Ridge(alpha=alfa).fit((tr[cols] - mu) / sd, r)
    return lambda te: m.predict((te[cols] - mu) / sd)


def estratos(tr):
    return tr.municipio.where(tr.municipio.map(tr.municipio.value_counts()) >= N_INTERNAS, "otros")


def elegir_alfa(tr, cols):
    skf = StratifiedKFold(N_INTERNAS, shuffle=True, random_state=SEMILLA_INTERNA)
    mae = {a: [] for a in ALFAS}
    for i, j in skf.split(tr, estratos(tr)):
        a_tr, a_va = tr.iloc[i], tr.iloc[j]
        base, _ = REF(a_tr, a_va)
        for a in ALFAS:
            mae[a].append(np.abs(base + ajustar(a_tr, cols, a)(a_va) - a_va.real.values))
    mae = {a: np.concatenate(e).mean() for a, e in mae.items()}
    return min(mae, key=lambda a: (round(mae[a], 6), -a))   # empate → más contracción


def candidato(cols, alfas):
    def predecir(tr, te):
        base, fuente = REF(tr, te)
        if not cols:
            return base, fuente
        a = elegir_alfa(tr, cols)
        alfas.append(a)
        return base + ajustar(tr, cols, a)(te), fuente
    return predecir


# ---------------------------------------------------------------- evaluación
def evaluar(t, part, cands, alfas):
    oof = []
    for nombre, f in cands.items():
        for escenario, col in [("A", "particion_principal"), ("B", "particion_espacial")]:
            for rep, pr in part.groupby("repeticion"):
                pr = pr.set_index("ID_POLIGONO")
                for k in sorted(pr[col].unique()):
                    ids_te, ids_tr = pr.index[pr[col] == k], pr.index[pr[col] != k]
                    n0 = len(alfas[nombre])
                    pred, fuente = f(t.loc[ids_tr], t.loc[ids_te])
                    a = alfas[nombre][n0] if len(alfas[nombre]) > n0 else np.nan
                    oof.append(pd.DataFrame(dict(ID_POLIGONO=ids_te, repeticion=rep, particion=k, escenario=escenario,
                                                 real=t.loc[ids_te, "real"].values, prediccion=pred, candidato=nombre,
                                                 version=VERSION, fuente=fuente, alfa=a)))
    return pd.concat(oof, ignore_index=True)


def resumir(oof):
    filas = []
    for (c, esc), x in oof.groupby(["candidato", "escenario"]):
        m = pd.DataFrame([metricas(r.real.values, r.prediccion.values) for _, r in x.groupby("repeticion")])
        filas.append(dict(candidato=c, escenario=esc, **m.mean().to_dict(),
                          MAE_sd_rep=m.MAE.std(ddof=0), RMSE_sd_rep=m.RMSE.std(ddof=0)))
    return pd.DataFrame(filas).sort_values(["escenario", "MAE"]).round(4)


def emparejada(oof, celda):
    """Igual que T08: ΔMAE por parcela frente a BASE, IC95 por celdas (regla) y por parcelas (referencia)."""
    filas = []
    for esc, x in oof.groupby("escenario"):
        x = x.assign(ae=(x.prediccion - x.real).abs(), se=(x.prediccion - x.real) ** 2)
        base_todas = x[x.candidato == BASE].set_index(["ID_POLIGONO", "repeticion"])
        for sub, mask in [("todas", base_todas.fuente.notna()), ("sin_respaldo", base_todas.fuente == "municipio")]:
            base = base_todas[mask]
            for c, y in x.groupby("candidato"):
                if c == BASE:
                    continue
                y = y.set_index(["ID_POLIGONO", "repeticion"]).loc[base.index]
                d = y.ae - base.ae
                d_rep, d_parc = d.groupby(level="repeticion").mean(), d.groupby(level="ID_POLIGONO").mean()
                rng = np.random.RandomState(SEMILLA_BOOT)
                v = d_parc.values
                bs_p = v[rng.randint(0, len(v), (N_BOOT, len(v)))].mean(axis=1)
                g = pd.DataFrame({"d": d_parc, "celda": celda.reindex(d_parc.index).values}).groupby("celda").d
                suma, n = g.sum().values, g.size().values
                rng = np.random.RandomState(SEMILLA_BOOT)
                k = rng.randint(0, len(suma), (N_BOOT, len(suma)))
                bs_c = suma[k].sum(axis=1) / n[k].sum(axis=1)
                lo_p, hi_p = np.percentile(bs_p, [2.5, 97.5])
                lo_c, hi_c = np.percentile(bs_c, [2.5, 97.5])
                drmse = (np.sqrt(y.se.groupby(level="repeticion").mean())
                         - np.sqrt(base.se.groupby(level="repeticion").mean())).mean()
                signo = int((d_rep < 0).sum())
                cumple = (d_parc.mean() <= -0.01) and (hi_c < 0) and (signo >= 4) and (drmse <= 0.01)
                filas.append(dict(escenario=esc, subconjunto=sub, n_predicciones=len(base), candidato=c, frente_a=BASE,
                                  dMAE=d_parc.mean(), IC95_celdas_inf=lo_c, IC95_celdas_sup=hi_c,
                                  IC95_parcelas_inf=lo_p, IC95_parcelas_sup=hi_p, n_celdas=len(suma),
                                  reps_que_mejoran=signo, dRMSE=drmse, cumple_regla_T03=cumple))
    return pd.DataFrame(filas).sort_values(["escenario", "subconjunto", "dMAE"]).round(4)


# ---------------------------------------------------------------- diagnósticos (no eligen nada)
def colinealidad(v):
    r = v.corr().round(3)
    vif = {}
    for c in v.columns:
        otras = v.drop(columns=c)
        X = np.column_stack([np.ones(len(v)), otras.values])
        beta, *_ = np.linalg.lstsq(X, v[c].values, rcond=None)
        res = v[c].values - X @ beta
        r2 = 1 - res.var() / v[c].var(ddof=0)
        vif[c] = round(1 / (1 - r2), 1) if r2 < 1 else np.inf
    r["VIF"] = pd.Series(vif)
    return r


def escala(v, d, celda):
    t = d[d.CONJUNTO == "ENTRENAMIENTO"]
    vt = v.loc[t.index].round(4)
    return pd.DataFrame([
        dict(medida="parcelas_etiquetadas", valor=len(vt)),
        dict(medida="valores_climaticos_distintos", valor=len(vt.drop_duplicates())),
        dict(medida="celdas_chirps_del_centroide", valor=celda.reindex(t.index).nunique()),
        dict(medida="parcelas_por_valor_climatico_mediana", valor=float(vt.groupby(list(vt.columns)).size().median())),
        dict(medida="parcelas_por_valor_climatico_max", valor=int(vt.groupby(list(vt.columns)).size().max())),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", type=Path, required=True)
    ap.add_argument("--clima", type=Path, required=True)
    ap.add_argument("--particiones", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)

    d = cargar(a.datos)
    v = variables_clima(a.clima)
    assert v.index.is_unique and set(d.index) <= set(v.index) and np.isfinite(v.values).all(), "clima incompleto"
    d = d.join(v)
    v.round(4).to_csv(a.salida / "variables_clima_t14.csv")
    part = pd.read_csv(a.particiones)
    assert not part.ID_POLIGONO.isin(d.index[d.CONJUNTO == "PREDICCION"]).any(), "ID reservado en particiones"
    celda = part.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps

    nombres = {BASE: [], "ref_mas_lluvia": GRUPOS["lluvia"], "ref_mas_tmin": GRUPOS["tmin"],
               "ref_mas_tmax": GRUPOS["tmax"], "ref_mas_clima": GRUPOS["clima"]}
    alfas = {n: [] for n in nombres}
    cands = {n: candidato(cols, alfas[n]) for n, cols in nombres.items()}
    t = d[d.CONJUNTO == "ENTRENAMIENTO"]
    oof = evaluar(t, part, cands, alfas)
    cols = ["ID_POLIGONO", "repeticion", "particion", "escenario", "real", "prediccion", "candidato", "version", "fuente"]
    for c, x in oof.groupby("candidato"):
        x[cols].to_csv(a.salida / f"predicciones_oof_t14_{c}.csv", index=False)
    oof[oof.candidato != BASE][["candidato", "escenario", "repeticion", "particion", "alfa"]] \
        .to_csv(a.salida / "alfas_t14.csv", index=False)

    m = resumir(oof)
    m.to_csv(a.salida / "metricas_t14.csv", index=False)
    e = emparejada(oof, celda)
    e.to_csv(a.salida / "comparacion_emparejada_t14.csv", index=False)
    colinealidad(v).to_csv(a.salida / "colinealidad_t14.csv")
    escala(v, d, celda).to_csv(a.salida / "escala_compartida_t14.csv", index=False)

    p = d[d.CONJUNTO == "PREDICCION"]
    fin = []
    for n in nombres:
        al = []
        pred, fuente = candidato(nombres[n], al)(t, p)
        fin.append(pd.DataFrame(dict(ID_POLIGONO=p.index, candidato=n, prediccion=pred, fuente=fuente,
                                     alfa=al[0] if al else np.nan, version=VERSION)))
    fin = pd.concat(fin, ignore_index=True)
    assert fin.groupby("candidato").ID_POLIGONO.nunique().eq(59).all() and np.isfinite(fin.prediccion).all()
    fin.to_csv(a.salida / "predicciones_59_t14.csv", index=False)

    pd.set_option("display.width", 200)
    print(m.to_string(index=False), "\n")
    print(e.to_string(index=False), "\n")
    print(colinealidad(v).to_string(), "\n")
    print(escala(v, d, celda).to_string(index=False))
    print("\nα elegidos:", {n: pd.Series(x).value_counts().to_dict() for n, x in alfas.items() if x})


if __name__ == "__main__":
    main()
