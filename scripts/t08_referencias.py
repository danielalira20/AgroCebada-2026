"""T08 · Referencias territoriales evaluadas con el protocolo T03.

Uso:
    python t08_referencias.py --datos RUTA/DATASET_RETO_AGRO_2026 \
        --particiones RUTA/particiones.csv --salida RUTA/SALIDA

Genera en --salida:
    predicciones_oof_referencias_<candidato>.csv   formato T03 §7, escenarios A y B
    metricas_referencias.csv                        MAE, RMSE, sesgo, R² por candidato y escenario
    metricas_por_municipio.csv                      MAE y n por candidato y municipio (escenario A)
    comparacion_emparejada.csv                      ΔMAE frente a la referencia base, IC95 y regla T03
    activacion_respaldos.csv                        cuándo se usa un respaldo (OOF y en las 59)
    predicciones_59_referencias.csv                 ajuste con las 138 etiquetas para las 59 reservadas

Sólo usa los rendimientos de entrenamiento de cada partición. Ninguna referencia se calcula
con las 138 etiquetas antes de evaluar.
"""
import argparse
import warnings
import zipfile
import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="The least populated class")

VERSION = "T08-v1"
BASE = "media_mun__resp_global"           # referencia del piloto, contra la que se compara
K_GRID = [0, 1, 2, 5, 10, 20, 50]         # presupuesto ≤ 8 configuraciones (T03 §5)
SEMILLA_INTERNA = 0
N_INTERNAS = 4
N_BOOT = 5000
SEMILLA_BOOT = 20261006


def cargar(datos: Path) -> pd.DataFrame:
    cat = pd.read_csv(datos / "ID_area_rendimiento_70_30_Reto_AgroCebada.csv", encoding="utf-8-sig")
    cat = cat.drop(columns=[c for c in cat.columns if c.startswith("Unnamed")])
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(datos / "Parcelas_Reto_AGC_CONJUNTO_70_30.zip") as z:
        z.extractall(tmp)
        geo = gpd.read_file(Path(tmp) / "Parcelas_Reto_AGC_CONJUNTO.shp")
    geo = pd.DataFrame(geo.drop(columns="geometry")).rename(columns={"ID_POLIGON": "ID_POLIGONO", "Cultivo": "grupo_registro"})
    d = cat.merge(geo[["ID_POLIGONO", "Municipio", "grupo_registro"]], on="ID_POLIGONO", validate="one_to_one")
    return d.rename(columns={"RENDIMIENTO_T_HA": "real", "Municipio": "municipio"}).set_index("ID_POLIGONO")


# ---------------------------------------------------------------- candidatos
def _agg(s, stat):
    return s.median() if stat == "mediana" else s.mean()


def referencia(stat, respaldo):
    """Estadístico municipal; si el municipio no tiene etiquetas, respaldo global o de grupo."""
    def predecir(tr, te):
        mun = tr.groupby("municipio").real.agg(lambda s: _agg(s, stat))
        out = te.municipio.map(mun)
        fuente = pd.Series(np.where(out.notna(), "municipio", None), index=te.index, dtype=object)
        if respaldo == "grupo":
            grp = tr.groupby("grupo_registro").real.agg(lambda s: _agg(s, stat))
            g = te.grupo_registro.map(grp)
            fuente[out.isna() & g.notna()] = "grupo"
            out = out.fillna(g)
        fuente[out.isna()] = "global"
        out = out.fillna(_agg(tr.real, stat))
        return out.values, fuente.values
    return predecir


def global_(stat):
    def predecir(tr, te):
        return np.full(len(te), _agg(tr.real, stat)), np.array(["global"] * len(te), dtype=object)
    return predecir


def _contraida(tr, te, k):
    """w·mediana_mun + (1−w)·mediana_grupo, con w = n/(n+k). Si no hay grupo, usa la global."""
    n = tr.municipio.value_counts()
    mun = tr.groupby("municipio").real.median()
    grp = tr.groupby("grupo_registro").real.median()
    padre = te.grupo_registro.map(grp).fillna(tr.real.median())
    nm = te.municipio.map(n).fillna(0).values
    w = nm / (nm + k) if k > 0 else (nm > 0).astype(float)
    pm = te.municipio.map(mun).fillna(padre).values
    return w * pm + (1 - w) * padre.values


def contraida():
    """La intensidad k se elige con 4 particiones internas estratificadas (T03 §5)."""
    from sklearn.model_selection import StratifiedKFold
    elegidos = []

    def predecir(tr, te):
        skf = StratifiedKFold(N_INTERNAS, shuffle=True, random_state=SEMILLA_INTERNA)
        estrato = tr.municipio.where(tr.municipio.map(tr.municipio.value_counts()) >= N_INTERNAS, "otros")
        mae = {}
        for k in K_GRID:
            e = []
            for i, j in skf.split(tr, estrato):
                e.append(np.abs(_contraida(tr.iloc[i], tr.iloc[j], k) - tr.real.values[j]))
            mae[k] = np.concatenate(e).mean()
        k = min(mae, key=lambda x: (round(mae[x], 6), x))
        elegidos.append(k)
        fuente = np.where(te.municipio.isin(tr.municipio), f"contraida_k{k}", "grupo")
        return _contraida(tr, te, k), fuente
    predecir.elegidos = elegidos
    return predecir


def candidatos():
    c = {
        "mediana_global": global_("mediana"),
        "media_global": global_("media"),
        "media_mun__resp_global": referencia("media", "global"),
        "media_mun__resp_grupo": referencia("media", "grupo"),
        "mediana_mun__resp_global": referencia("mediana", "global"),
        "mediana_mun__resp_grupo": referencia("mediana", "grupo"),
        "mediana_mun_contraida_grupo": contraida(),
    }
    return c


# ---------------------------------------------------------------- evaluación
def metricas(y, p):
    e = p - y
    ss = ((y - y.mean()) ** 2).sum()
    return dict(MAE=np.abs(e).mean(), RMSE=np.sqrt((e ** 2).mean()), sesgo=e.mean(), R2=1 - (e ** 2).sum() / ss)


def evaluar(d, part, cands):
    t = d[d.CONJUNTO == "ENTRENAMIENTO"]
    oof = []
    for nombre, f in cands.items():
        for escenario, col in [("A", "particion_principal"), ("B", "particion_espacial")]:
            for rep, pr in part.groupby("repeticion"):
                pr = pr.set_index("ID_POLIGONO")
                for k in sorted(pr[col].unique()):
                    ids_te = pr.index[pr[col] == k]
                    ids_tr = pr.index[pr[col] != k]
                    pred, fuente = f(t.loc[ids_tr], t.loc[ids_te])
                    oof.append(pd.DataFrame(dict(ID_POLIGONO=ids_te, repeticion=rep, particion=k, escenario=escenario,
                                                 real=t.loc[ids_te, "real"].values, prediccion=pred,
                                                 candidato=nombre, version=VERSION, fuente=fuente)))
    return pd.concat(oof, ignore_index=True)


def resumir(oof):
    filas = []
    for (c, esc), x in oof.groupby(["candidato", "escenario"]):
        m = pd.DataFrame([metricas(r.real.values, r.prediccion.values) for _, r in x.groupby("repeticion")])
        filas.append(dict(candidato=c, escenario=esc, **{f"{k}": m[k].mean() for k in m},
                          **{f"{k}_sd_rep": m[k].std(ddof=0) for k in ["MAE", "RMSE"]}))
    return pd.DataFrame(filas).sort_values(["escenario", "MAE"]).round(4)


def por_municipio(oof):
    a = oof[oof.escenario == "A"].assign(ae=lambda x: (x.prediccion - x.real).abs())
    r = a.groupby(["candidato", "municipio"]).agg(MAE=("ae", "mean"), n_parcelas=("ID_POLIGONO", "nunique")).reset_index()
    r["poco_informativo"] = r.n_parcelas < 5
    return r.round(4)


def emparejada(oof, celda):
    """ΔMAE emparejado por parcela frente a BASE, con dos intervalos (T03 §4):
    - IC95_celdas: bootstrap por bloques espaciales (regla de decisión). Se remuestrean, con reemplazo,
      las celdas CHIRPS que contienen parcelas etiquetadas; el estadístico es el ΔMAE medio de todas las
      parcelas de las celdas elegidas.
    - IC95_parcelas: bootstrap de parcelas independientes (sólo como referencia; ignora la cercanía).
    """
    filas = []
    for esc, x in oof.groupby("escenario"):
        x = x.assign(ae=(x.prediccion - x.real).abs(), se=(x.prediccion - x.real) ** 2)
        base = x[x.candidato == BASE].set_index(["ID_POLIGONO", "repeticion"])
        for c, y in x.groupby("candidato"):
            if c == BASE:
                continue
            y = y.set_index(["ID_POLIGONO", "repeticion"]).loc[base.index]
            d_rep = (y.ae - base.ae).groupby(level="repeticion").mean()
            d_parc = (y.ae - base.ae).groupby(level="ID_POLIGONO").mean()
            # bootstrap de parcelas
            rng = np.random.RandomState(SEMILLA_BOOT)
            v = d_parc.values
            bs_p = v[rng.randint(0, len(v), (N_BOOT, len(v)))].mean(axis=1)
            # bootstrap por bloques (celdas CHIRPS)
            g = pd.DataFrame({"d": d_parc, "celda": celda.reindex(d_parc.index).values}).groupby("celda").d
            suma, n = g.sum().values, g.size().values
            rng = np.random.RandomState(SEMILLA_BOOT)
            k = rng.randint(0, len(suma), (N_BOOT, len(suma)))
            bs_c = suma[k].sum(axis=1) / n[k].sum(axis=1)
            lo_p, hi_p = np.percentile(bs_p, [2.5, 97.5])
            lo_c, hi_c = np.percentile(bs_c, [2.5, 97.5])
            drmse = (np.sqrt(y.se.groupby(level="repeticion").mean()) - np.sqrt(base.se.groupby(level="repeticion").mean())).mean()
            signo = int((d_rep < 0).sum())
            cumple = (d_parc.mean() <= -0.01) and (hi_c < 0) and (signo >= 4) and (drmse <= 0.01)
            filas.append(dict(escenario=esc, candidato=c, frente_a=BASE, dMAE=d_parc.mean(),
                              IC95_celdas_inf=lo_c, IC95_celdas_sup=hi_c, IC95_parcelas_inf=lo_p, IC95_parcelas_sup=hi_p,
                              n_celdas=len(suma), reps_que_mejoran=signo, dRMSE=drmse,
                              parcelas_mejoran=int((d_parc < 0).sum()), parcelas_empeoran=int((d_parc > 0).sum()),
                              cumple_regla_T03=cumple))
    return pd.DataFrame(filas).sort_values(["escenario", "dMAE"]).round(4)


def activaciones(oof, d, cands):
    a = oof[oof.escenario == "A"].groupby(["candidato", "fuente"]).size().rename("n_predicciones_oof").reset_index()
    t = d[d.CONJUNTO == "ENTRENAMIENTO"]
    p = d[d.CONJUNTO == "PREDICCION"]
    finales = []
    for c, f in cands.items():
        pred, fuente = f(t, p)
        finales.append(pd.DataFrame(dict(ID_POLIGONO=p.index, candidato=c, prediccion=pred, fuente=fuente,
                                         municipio=p.municipio.values, version=VERSION)))
    fin = pd.concat(finales, ignore_index=True)
    b = fin.groupby(["candidato", "fuente"]).size().rename("n_en_las_59").reset_index()
    return a.merge(b, on=["candidato", "fuente"], how="outer").fillna(0), fin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", type=Path, required=True)
    ap.add_argument("--particiones", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)

    d = cargar(a.datos)
    part = pd.read_csv(a.particiones)
    assert not part.ID_POLIGONO.isin(d.index[d.CONJUNTO == "PREDICCION"]).any(), "ID reservado en particiones"
    cands = candidatos()
    oof = evaluar(d, part, cands)
    oof = oof.merge(d[["municipio"]], left_on="ID_POLIGONO", right_index=True)
    cols = ["ID_POLIGONO", "repeticion", "particion", "escenario", "real", "prediccion", "candidato", "version"]
    for c, x in oof.groupby("candidato"):
        x[cols + ["fuente"]].to_csv(a.salida / f"predicciones_oof_referencias_{c}.csv", index=False)

    m = resumir(oof)
    m.to_csv(a.salida / "metricas_referencias.csv", index=False)
    por_municipio(oof).to_csv(a.salida / "metricas_por_municipio.csv", index=False)
    celda = part.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps
    e = emparejada(oof, celda)
    e.to_csv(a.salida / "comparacion_emparejada.csv", index=False)
    act, fin = activaciones(oof, d, cands)
    act.to_csv(a.salida / "activacion_respaldos.csv", index=False)
    assert fin.groupby("candidato").ID_POLIGONO.nunique().eq(59).all() and np.isfinite(fin.prediccion).all()
    fin.to_csv(a.salida / "predicciones_59_referencias.csv", index=False)

    pd.set_option("display.width", 200)
    print(m.to_string(index=False))
    print()
    print(e.to_string(index=False))
    print()
    print(act.to_string(index=False))
    k = pd.Series(cands["mediana_mun_contraida_grupo"].elegidos).value_counts().to_dict()
    print("\nk elegido en la contracción (selección interna):", k)


if __name__ == "__main__":
    main()
