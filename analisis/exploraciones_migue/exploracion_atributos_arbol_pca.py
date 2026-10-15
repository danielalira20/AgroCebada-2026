"""Exploración posterior sugerida por el profe (no decide nada): ¿qué atributos sirven?, árbol de decisión con poda
y PCA, todo con las particiones y la regla de T03 contra la referencia `media_mun__resp_grupo`.

1. Tabla amplia de atributos de la temporada 2025 (hasta el 31 de octubre; fechas con nubosidad <= 20 %):
   Sentinel-2 (22 índices, sin vi6t que viene vacío), Planet (4), Landsat (vi6t), en abr-oct y jun-oct,
   percentil 90 y media de cada índice; las 6 variables de clima de T14; elevación, pendiente y log(área).
2. Cribado: correlación de Spearman de cada atributo con el rendimiento y, dentro del municipio, con el residuo
   (rendimiento - media municipal). El umbral de azar sale de 1000 permutaciones del residuo dentro del municipio:
   el máximo |r| que daría el azar con tantos atributos.
3. Candidatos (se ajustan dentro de cada entrenamiento; opciones elegidas con 4 internas, MAE en sin_respaldo):
   - arbol_rendimiento: árbol de regresión sobre el rendimiento con municipio (one-hot) + todos los atributos;
     poda por costo-complejidad (ccp_alpha) elegida en internas; hojas de al menos 5 parcelas.
   - arbol_residuo: referencia + árbol sobre el residuo LOO con los atributos centrados por municipio.
   - pca_ridge: referencia + Ridge sobre k componentes principales de los atributos centrados por municipio y
     estandarizados (PCA ajustado sólo con el entrenamiento); k y alfa elegidos en internas.
4. Árboles finales con las 138 (estructura e importancia) y varianza explicada del PCA.

Uso (desde la raíz del repo del equipo):
    python exploracion_atributos_arbol_pca.py scripts RUTA/DATASET registro/t03/particiones.csv \
        RUTA/variables_clima_t14.csv RUTA/Parcelas.shp RUTA/carpeta_topografia SALIDA
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.model_selection import StratifiedKFold
from sklearn.tree import DecisionTreeRegressor, export_text

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
import t14_clima as T  # noqa: E402

DATOS, PART, CLIMA, SHP, TOPO, SALIDA = Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], Path(sys.argv[6]), Path(sys.argv[7])
SALIDA.mkdir(parents=True, exist_ok=True)
CCP = [0.0, 0.002, 0.005, 0.01, 0.02, 0.05]
KS = [1, 2, 3, 5, 10]
VENTANAS = {"abr_oct": "2025-04-01", "jun_oct": "2025-06-01"}


# ---------------------------------------------------------------- atributos
def satelite(archivo, sensor, prefijo, quitar=()):
    x = pd.read_csv(DATOS / archivo, low_memory=False)
    x = x[x.sensor == sensor].copy()
    x["f"] = pd.to_datetime(x.fecha_captura, format="%d/%m/%Y")
    x = x[(x.porcentaje_nubosidad <= 20) & (x.f <= "2025-10-31")]
    idx = [c[:-9] for c in x.columns if c.endswith("_promedio") and c[:-9] not in quitar]
    out = {}
    for w, ini in VENTANAS.items():
        z = x[x.f >= ini].groupby("ID_POLIGONO")
        for i in idx:
            out[f"{prefijo}_{i}_p90_{w}"] = z[f"{i}_promedio"].quantile(0.9)
            out[f"{prefijo}_{i}_media_{w}"] = z[f"{i}_promedio"].mean()
    return pd.DataFrame(out)


def relieve():
    geo = gpd.read_file(SHP).set_index("ID_POLIGON")
    rel = {}
    for nombre, tif in [("pendiente", "Pendiente_INEGI_CEM4_120m_grados.tif"), ("elevacion", "Elevacion_INEGI_CEM4_120m.tif")]:
        r = rasterio.open(next(TOPO.rglob(tif)))
        g = geo.to_crs(r.crs)
        rel[nombre] = pd.Series({pid: float(mask(r, [geom], crop=True, all_touched=True, filled=False)[0].compressed().mean())
                                 for pid, geom in g.geometry.items()})
    return pd.DataFrame(rel)


d = T.cargar(DATOS)
basico = "Conjunto_datos_BASICO_AgroCebada2026.csv"
v = pd.concat([satelite(basico, "Sentinel-2", "s2", quitar=("vi6t",)),
               satelite(basico, "Landsat", "ls", quitar=tuple(c[:-9] for c in pd.read_csv(DATOS / basico, nrows=1).columns
                                                              if c.endswith("_promedio") and c != "vi6t_promedio")),
               satelite("Conjunto_datos_PRO_AgroCebada.csv", "Planet", "pl"),
               pd.read_csv(CLIMA, index_col=0), relieve()], axis=1)
v["log_area"] = np.log(d.AREA_HA)
v = v.loc[d.index]
incompletos = v.columns[v.isna().any()]
print(f"atributos construidos: {v.shape[1]}; con algún faltante (se quitan): {len(incompletos)} {list(incompletos)}")
v = v.drop(columns=incompletos).loc[:, lambda z: z.std() > 0]
ATR = list(v.columns)
print("atributos usados:", len(ATR))
v.to_csv(SALIDA / "atributos_117.csv")   # la usa exploracion_red_neuronal.py
d = d.join(v)
part = pd.read_csv(PART)
celda = T.validar_particiones(part, d)
t = d[d.CONJUNTO == "ENTRENAMIENTO"]

# ---------------------------------------------------------------- cribado
res = t.real - t.groupby("municipio").real.transform("mean")
cen = t[ATR] - t.groupby("municipio")[ATR].transform("mean")
cr = pd.DataFrame({"r_rendimiento": t[ATR].corrwith(t.real, method="spearman"),
                   "r_dentro_municipio": cen.corrwith(res, method="spearman")})
rng = np.random.RandomState(0)
rk = cen.rank()
maxima = []
for _ in range(1000):
    p = res.groupby(t.municipio).transform(lambda s: pd.Series(rng.permutation(s.values), index=s.index))
    maxima.append(rk.corrwith(p.rank()).abs().max())
umbral = float(np.percentile(maxima, 95))
cr["supera_azar"] = cr.r_dentro_municipio.abs() > umbral
cr = cr.reindex(cr.r_dentro_municipio.abs().sort_values(ascending=False).index).round(3)
cr.to_csv(SALIDA / "cribado_atributos.csv")
print(f"\numbral de azar para max |r| dentro del municipio ({len(ATR)} atributos, 1000 permutaciones): {umbral:.3f}")
print("atributos que lo superan:", int(cr.supera_azar.sum()))
print(cr.head(12).to_string())


# ---------------------------------------------------------------- candidatos
def internas(tr):
    return StratifiedKFold(T.N_INTERNAS, shuffle=True, random_state=T.SEMILLA_INTERNA).split(tr, T.estratos(tr))


def elegir(tr, opciones, ajustar_pred):
    err = {o: [] for o in opciones}
    for i, j in internas(tr):
        a, va = tr.iloc[i], tr.iloc[j]
        _, fuente = T.REF(a, va)
        for o in opciones:
            err[o].append(np.abs(ajustar_pred(a, va, o) - va.real.values)[fuente == "municipio"])
    mae = {o: np.concatenate(e).mean() for o, e in err.items()}
    return min(mae, key=lambda o: round(mae[o], 6))       # empate -> la primera opción (la más simple)


MUNS = sorted(d.municipio.unique())


def onehot(z):
    return pd.concat([z[ATR], pd.get_dummies(z.municipio).reindex(columns=MUNS, fill_value=0).astype(float)], axis=1)


def arbol_y(tr, te, ccp):
    m = DecisionTreeRegressor(min_samples_leaf=5, ccp_alpha=ccp, random_state=0).fit(onehot(tr), tr.real)
    return m.predict(onehot(te))


def arbol_r(tr, te, ccp):
    c = T.centros(tr, ATR)
    m = DecisionTreeRegressor(min_samples_leaf=5, ccp_alpha=ccp, random_state=0).fit(
        T.restar_centro(tr, ATR, c), tr.real.values - T.ref_loo(tr))
    return T.REF(tr, te)[0] + m.predict(T.restar_centro(te, ATR, c))


def pca_ridge(tr, te, opc):
    k, alfa = opc
    c = T.centros(tr, ATR)
    xtr = T.restar_centro(tr, ATR, c)
    mu, sd = xtr.mean(), xtr.std(ddof=0).replace(0, 1)
    pca = PCA(n_components=k, random_state=0).fit((xtr - mu) / sd)
    ztr = pca.transform((xtr - mu) / sd)
    m = Ridge(alpha=alfa).fit(ztr, tr.real.values - T.ref_loo(tr))
    return T.REF(tr, te)[0] + m.predict(pca.transform((T.restar_centro(te, ATR, c) - mu) / sd))


elegidos = {"arbol_rendimiento": [], "arbol_residuo": [], "pca_ridge": []}
OPC_PCA = [(k, a) for k in KS for a in sorted(T.ALFAS, reverse=True)]   # primero lo más simple


def candidato(nombre, f, opciones):
    def predecir(tr, te):
        o = elegir(tr, opciones, f)
        elegidos[nombre].append(o)
        return f(tr, te, o), T.REF(tr, te)[1]
    return predecir


cands = {T.BASE: T.candidato([], []),
         "arbol_rendimiento": candidato("arbol_rendimiento", arbol_y, sorted(CCP, reverse=True)),
         "arbol_residuo": candidato("arbol_residuo", arbol_r, sorted(CCP, reverse=True)),
         "pca_ridge": candidato("pca_ridge", pca_ridge, OPC_PCA)}
oof = T.evaluar(t, part, cands, {n: [] for n in cands})
oof.to_csv(SALIDA / "oof_arbol_pca.csv", index=False)
e = T.emparejada(oof, celda)
e.to_csv(SALIDA / "emparejada_arbol_pca.csv", index=False)
pd.set_option("display.width", 220)
print("\n", T.resumir(oof).to_string(index=False))
print("\n", e[e.subconjunto == "sin_respaldo"][["escenario", "candidato", "dMAE", "IC95_celdas_inf", "IC95_celdas_sup",
                                                "reps_que_mejoran", "dRMSE", "cumple_regla_T03"]].to_string(index=False))
print("\nopciones elegidas:", {n: pd.Series([str(o) for o in x]).value_counts().head(6).to_dict() for n, x in elegidos.items()})

# ---------------------------------------------------------------- modelos finales con las 138 (descriptivo)
ccp_y = elegir(t, sorted(CCP, reverse=True), arbol_y)
fy = DecisionTreeRegressor(min_samples_leaf=5, ccp_alpha=ccp_y, random_state=0).fit(onehot(t), t.real)
print(f"\nÁRBOL SOBRE EL RENDIMIENTO (138 parcelas, ccp_alpha={ccp_y}, {fy.get_n_leaves()} hojas):")
print(export_text(fy, feature_names=list(onehot(t).columns), decimals=2))
imp = pd.Series(fy.feature_importances_, index=onehot(t).columns)
print("importancia:", imp[imp > 0].sort_values(ascending=False).round(3).to_dict())

ccp_r = elegir(t, sorted(CCP, reverse=True), arbol_r)
c = T.centros(t, ATR)
fr = DecisionTreeRegressor(min_samples_leaf=5, ccp_alpha=ccp_r, random_state=0).fit(
    T.restar_centro(t, ATR, c), t.real.values - T.ref_loo(t))
print(f"\nÁRBOL SOBRE EL RESIDUO (ccp_alpha={ccp_r}, {fr.get_n_leaves()} hojas):")
print(export_text(fr, feature_names=ATR, decimals=3))

x = T.restar_centro(d, ATR, T.centros(d, ATR))
pca = PCA(random_state=0).fit((x - x.mean()) / x.std(ddof=0))
var = pd.Series(pca.explained_variance_ratio_[:10].round(3), index=[f"PC{i + 1}" for i in range(10)])
print("\nPCA (197 parcelas, atributos centrados por municipio): varianza explicada", var.to_dict(),
      f"acumulada 5 = {pca.explained_variance_ratio_[:5].sum():.2f}")
for i in range(2):
    carga = pd.Series(pca.components_[i], index=ATR)
    print(f"PC{i + 1} pesa más en:", carga.abs().sort_values(ascending=False).head(6).index.tolist())
