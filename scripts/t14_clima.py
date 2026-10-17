"""T14 · Variable climática: ¿cuál aporta más sobre la referencia, lluvia, Tmin o Tmax?

Uso (desde la raíz del repo):
    python scripts/t14_clima.py --datos RUTA/DATASET_RETO_AGRO_2026 \
        --clima registro/t04/clima_parcela_mes.csv \
        --particiones registro/t03/particiones.csv --salida RUTA/SALIDA \
        [--catalogo analisis/auditoria_catalogo_y_etiquetas/tablas/catalogo_parcelas.csv] \
        [--pares analisis/auditoria_catalogo_y_etiquetas/tablas/pares_de_parcelas_cercanas.csv]

Protocolo (T03 y D019):
- Referencia: media_mun__resp_grupo (media del municipio; respaldo por grupo de registro y luego global).
- Candidatos definidos antes de ver resultados: la referencia sola y la referencia + una corrección Ridge
  del residuo con lluvia, Tmin, Tmax o las tres. v3 añade los mismos 4 con las variables centradas por
  municipio (H3, revisión de Dani): 8 procedimientos en total. El residuo de cada fila de entrenamiento usa una
  referencia calculada dejando fuera esa fila (T03 §5).
- α de Ridge ∈ ALFAS (6 configuraciones ≤ 8), elegido con 4 particiones internas estratificadas por
  municipio (estrato «otros» si hay < 4 etiquetas). Escalado ajustado dentro de cada entrenamiento.
- Variables: temporada 2025 con corte al 31 de octubre (sólo meses con posterior_al_corte = False),
  en las dos ventanas candidatas de T03 §6: abril–octubre y junio–octubre. PREC se suma (mm);
  Tmin y Tmax se promedian ponderando cada mes por sus días (°C).
- La tabla de clima se valida antes de usarla (columnas, claves únicas, meses, variables, unidades,
  estados, cobertura y bandera de corte); cualquier inconsistencia detiene el script.
- Comparación emparejada contra la referencia en los subconjuntos `todas` y `sin_respaldo`;
  la decisión se toma en `sin_respaldo`, con IC95 por bloques de celdas CHIRPS.

Genera en --salida:
    variables_clima_t14.csv               las 6 variables de temporada por parcela (197 filas)
    predicciones_oof_t14_<candidato>.csv  formato T03 §7 con columna fuente, escenarios A y B
    metricas_t14.csv                      MAE, RMSE, sesgo y R² por candidato y escenario
    comparacion_emparejada_t14.csv        ΔMAE frente a la referencia, IC95 y regla T03
    alfas_t14.csv                         α elegido en cada ajuste (una fila por ajuste)
    desglose_errores_t14.csv              MAE por municipio, grupo, precisión de la etiqueta, calidad de contorno
                                          y vecinas (T03 §4 bis)
    sensibilidad_sin_dudosas_t14.csv      la comparación emparejada sin las parcelas con alerta de contorno
    asociacion_dentro_municipio_t14.csv   r de cada variable con el rendimiento dentro del municipio, IC95 por celdas

La carpeta --salida debe ser nueva o estar vacía. Todo se escribe primero en una carpeta temporal y sólo se
mueve a --salida si la corrida termina bien.
    colinealidad_t14.csv                  correlaciones entre las 6 variables y VIF
    escala_compartida_t14.csv             cuántos valores climáticos distintos hay realmente
    predicciones_59_t14.csv               ajuste con las 138 etiquetas para las 59 reservadas
"""
import argparse
import shutil
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

VERSION = "T14-v3"
BASE = "referencia"
ALFAS = [0.1, 1, 10, 100, 1000, 10000]
N_INTERNAS = 4
SEMILLA_INTERNA = 0
N_BOOT = 5000
SEMILLA_BOOT = 20261006
VENTANAS = {
    "abr_oct": ["2025-04", "2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10"],
    "jun_oct": ["2025-06", "2025-07", "2025-08", "2025-09", "2025-10"],
}
GRUPOS = {
    "lluvia": ["prec_abr_oct", "prec_jun_oct"],
    "tmin": ["tmin_abr_oct", "tmin_jun_oct"],
    "tmax": ["tmax_abr_oct", "tmax_jun_oct"],
}
GRUPOS["clima"] = GRUPOS["lluvia"] + GRUPOS["tmin"] + GRUPOS["tmax"]
UNIDADES = {"PREC": "mm/mes", "Tmax": "grados Celsius", "Tmin": "grados Celsius"}
ESTADOS = {"cobertura_completa", "cobertura_parcial"}
COLUMNAS = ["id_parcela", "periodo", "variable", "unidad", "media_ponderada", "estado",
            "cobertura_valida", "posterior_al_corte"]
REF = referencia("media", "grupo")


def exigir(condicion, mensaje):
    """Como assert, pero no se desactiva con `python -O` (revisión de Dani)."""
    if not condicion:
        raise ValueError(mensaje)


# ---------------------------------------------------------------- variables
def validar_clima(c: pd.DataFrame) -> pd.DataFrame:
    """Contrato de entrada de T04. Cualquier inconsistencia detiene el script (revisión de Diego)."""
    faltan = set(COLUMNAS) - set(c.columns)
    exigir(not faltan, f"faltan columnas en la tabla de clima: {sorted(faltan)}")
    exigir(not c.duplicated(["id_parcela", "periodo", "variable"]).any(), "claves (id, periodo, variable) repetidas")
    exigir(set(c.variable) == set(UNIDADES), f"variables inesperadas: {sorted(set(c.variable))}")
    mal = c[c.unidad != c.variable.map(UNIDADES)]
    exigir(mal.empty, f"unidades incorrectas: {mal[['variable', 'unidad']].drop_duplicates().values.tolist()}")
    exigir(set(c.estado) <= ESTADOS, f"estados no permitidos: {sorted(set(c.estado) - ESTADOS)}")
    exigir(c.cobertura_valida.between(0, 1).all(), "cobertura_valida fuera de [0, 1]")
    corte = c.posterior_al_corte.astype(str).str.lower()
    exigir(corte.isin(["true", "false"]).all(), "posterior_al_corte con valores distintos de True/False")
    exigir(c.periodo.str.fullmatch(r"\d{4}-\d{2}").all(), "periodo con formato distinto de AAAA-MM")
    fin_mes = pd.to_datetime(c.periodo + "-01") + pd.offsets.MonthEnd(0)
    exigir((corte.eq("true") == (fin_mes > pd.Timestamp("2025-10-31"))).all(), "posterior_al_corte no coincide con el corte")
    meses = sorted(set().union(*VENTANAS.values()))
    v = c[c.periodo.isin(meses) & corte.eq("false")]
    n = v.groupby(["id_parcela", "variable"]).periodo.nunique()
    exigir((n == len(meses)).all() and len(n) == c.id_parcela.nunique() * len(UNIDADES), "faltan meses en la temporada")
    exigir(np.isfinite(v.media_ponderada).all() and (v.cobertura_valida > 0).all(), "clima vacío en la temporada")
    return v


def variables_clima(ruta: Path) -> pd.DataFrame:
    c = validar_clima(pd.read_csv(ruta))
    c = c.assign(dias=pd.to_datetime(c.periodo + "-01").dt.days_in_month)
    out = {}
    for nombre, meses in VENTANAS.items():
        x = c[c.periodo.isin(meses)]
        out[f"prec_{nombre}"] = x[x.variable == "PREC"].groupby("id_parcela").media_ponderada.sum()
        for var in ["Tmin", "Tmax"]:
            t = x[x.variable == var].assign(p=lambda z: z.media_ponderada * z.dias).groupby("id_parcela")
            out[f"{var.lower()}_{nombre}"] = t.p.sum() / t.dias.sum()
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


def centros(tr, cols):
    """Promedio de cada variable por municipio, grupo de registro y global, aprendido sólo con `tr`."""
    return (tr.groupby("municipio")[cols].mean(), tr.groupby("grupo_registro")[cols].mean(), tr[cols].mean())


def restar_centro(z, cols, c):
    """Resta el centro del municipio; si el municipio no está en el entrenamiento, el del grupo y luego el global."""
    cm, cg, gl = c
    centro = cm.reindex(z.municipio).set_axis(z.index).fillna(cg.reindex(z.grupo_registro).set_axis(z.index)).fillna(gl)
    return z[cols] - centro


def ajustar(tr, cols, alfa, centrado=False):
    """Ridge sobre el residuo LOO. Con `centrado`, las variables se expresan respecto al centro municipal del
    entrenamiento al aprender y al predecir (H3: medir sólo lo que aporta el clima dentro del municipio)."""
    r = tr.real.values - ref_loo(tr)
    if centrado:
        c = centros(tr, cols)
        xtr = restar_centro(tr, cols, c)
        sd = xtr.std(ddof=0).replace(0, 1)
        m = Ridge(alpha=alfa).fit(xtr / sd, r)
        return lambda te: m.predict(restar_centro(te, cols, c) / sd)
    mu, sd = tr[cols].mean(), tr[cols].std(ddof=0).replace(0, 1)
    m = Ridge(alpha=alfa).fit((tr[cols] - mu) / sd, r)
    return lambda te: m.predict((te[cols] - mu) / sd)


def estratos(tr):
    return tr.municipio.where(tr.municipio.map(tr.municipio.value_counts()) >= N_INTERNAS, "otros")


def elegir_alfa(tr, cols, centrado=False):
    skf = StratifiedKFold(N_INTERNAS, shuffle=True, random_state=SEMILLA_INTERNA)
    mae = {a: [] for a in ALFAS}
    for i, j in skf.split(tr, estratos(tr)):
        a_tr, a_va = tr.iloc[i], tr.iloc[j]
        base, _ = REF(a_tr, a_va)
        for a in ALFAS:
            mae[a].append(np.abs(base + ajustar(a_tr, cols, a, centrado)(a_va) - a_va.real.values))
    mae = {a: np.concatenate(e).mean() for a, e in mae.items()}
    return min(mae, key=lambda a: (round(mae[a], 6), -a))   # empate → más contracción


def candidato(cols, alfas, centrado=False):
    def predecir(tr, te):
        base, fuente = REF(tr, te)
        if not cols:
            return base, fuente
        a = elegir_alfa(tr, cols, centrado)
        alfas.append(a)
        return base + ajustar(tr, cols, a, centrado)(te), fuente
    return predecir


# ---------------------------------------------------------------- evaluación
def validar_particiones(part, d):
    """Rechaza IDs repetidos, IDs faltantes o reservados y celdas ausentes o inconsistentes (revisión de Dani)."""
    faltan = {"ID_POLIGONO", "repeticion", "particion_principal", "particion_espacial", "celda_chirps"} - set(part.columns)
    exigir(not faltan, f"faltan columnas en particiones: {sorted(faltan)}")
    exigir(not part.duplicated(["ID_POLIGONO", "repeticion"]).any(), "ID repetido dentro de una repetición")
    etiquetadas = set(d.index[d.CONJUNTO == "ENTRENAMIENTO"])
    for rep, x in part.groupby("repeticion"):
        exigir(set(x.ID_POLIGONO) == etiquetadas, f"la repetición {rep} no tiene exactamente las 138 etiquetadas")
    exigir(not part.ID_POLIGONO.isin(d.index[d.CONJUNTO == "PREDICCION"]).any(), "ID reservado en particiones")
    exigir(part.celda_chirps.notna().all(), "celda CHIRPS ausente")
    exigir(part.groupby("ID_POLIGONO").celda_chirps.nunique().eq(1).all(), "una parcela tiene más de una celda")
    exigir(part[["particion_principal", "particion_espacial"]].notna().all().all(), "partición ausente")
    return part.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps


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


def emparejada(oof, celda, excluir=()):
    """Igual que T08: ΔMAE por parcela frente a BASE, IC95 por celdas (regla) y por parcelas (referencia).
    `excluir`: IDs que se quitan de la comparación (sensibilidad de T03 §4 bis)."""
    filas = []
    oof = oof[~oof.ID_POLIGONO.isin(set(excluir))]
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


def desglose(oof, d, catalogo=None, pares=None):
    """MAE por grupo a partir de las predicciones fuera del entrenamiento (no reentrena; T03 §4 bis)."""
    t = d[d.CONJUNTO == "ENTRENAMIENTO"]
    atr = t[["municipio", "grupo_registro"]].copy()
    # escalón de la etiqueta DEL MUNICIPIO (T03 §4 bis; mismo criterio que paso_comun de T02): el paso más
    # grueso que comparten todas las etiquetas del municipio. Sólo para reportar; nunca es variable del modelo.
    atr["escalon_etiqueta_municipio"] = t.municipio.map(escalon_municipal(t))
    if catalogo is not None:
        cat = pd.read_csv(catalogo, encoding="utf-8-sig")
        cat = cat.rename(columns={"id_parcela": "ID_POLIGONO"}).set_index("ID_POLIGONO")
        for c in ["contorno_categoria", "contorno_angosta_o_muy_pequena"]:
            if c in cat:
                atr[c] = cat[c].reindex(atr.index).astype(str)
        dudosa = pd.Series(False, index=atr.index)
        if "contorno_categoria" in atr:
            dudosa |= atr.contorno_categoria.isin(["B", "C"])
        if "contorno_angosta_o_muy_pequena" in atr:
            dudosa |= atr.contorno_angosta_o_muy_pequena.str.lower().isin(["sí", "si", "true", "1"])
        atr["parcela_dudosa_4bis"] = dudosa
    if pares is not None:
        pr = pd.read_csv(pares, encoding="utf-8-sig")
        ids = [c for c in pr.columns if "id" in c.lower()][:2]
        exigir(len(ids) == 2, f"no encontré las dos columnas de ID en {pares}")
        con_vecina = set()
        for a, b in pr[ids].values:
            if a in t.index and b in t.index:
                con_vecina |= {a, b}
        atr["vecina_etiquetada_20m"] = atr.index.isin(con_vecina)
    x = oof.assign(ae=(oof.prediccion - oof.real).abs()).join(atr, on="ID_POLIGONO")
    # subconjunto sin_respaldo: filas cuya referencia usó el municipio (las mismas para todos los candidatos)
    con_mun = set(map(tuple, oof[(oof.candidato == BASE) & (oof.fuente == "municipio")][["ID_POLIGONO", "repeticion", "escenario"]].values))
    x["sin_respaldo"] = [k in con_mun for k in map(tuple, x[["ID_POLIGONO", "repeticion", "escenario"]].values)]
    filas = []
    for sub, xs in [("todas", x), ("sin_respaldo", x[x.sin_respaldo])]:
        for col in atr.columns:
            for (esc, c, g), z in xs.groupby(["escenario", "candidato", col]):
                filas.append(dict(escenario=esc, subconjunto=sub, candidato=c, atributo=col, grupo=g, MAE=z.ae.mean(),
                                  n_parcelas=z.ID_POLIGONO.nunique(), poco_informativo=z.ID_POLIGONO.nunique() < 5))
    return pd.DataFrame(filas).round(4), (set(atr.index[atr.parcela_dudosa_4bis]) if "parcela_dudosa_4bis" in atr else None)


def escalon_municipal(t):
    """'0.5' si todas las etiquetas del municipio son múltiplos de 0.5, '0.1' si lo son de 0.1, si no '0.01'.
    Con una sola etiqueta no hay paso común: queda 'sin_escalon', igual que paso_comun vacío en T02."""
    cent = (t.real * 100).round().astype(int)
    def paso(c):
        if len(c) < 2:
            return "sin_escalon"
        return "0.5" if (c % 50 == 0).all() else "0.1" if (c % 10 == 0).all() else "0.01"
    return cent.groupby(t.municipio).apply(paso)


def asociacion_dentro(v, d, celda):
    """Correlación de Pearson entre cada variable y el rendimiento, ambos expresados respecto a la media de su
    municipio (138 etiquetadas), con IC95 por bootstrap de celdas CHIRPS. Descriptivo: no elige variables."""
    t = d[d.CONJUNTO == "ENTRENAMIENTO"]
    y = t.real - t.groupby("municipio").real.transform("mean")
    c = celda.reindex(t.index).values
    celdas = pd.unique(c)
    rng = np.random.RandomState(SEMILLA_BOOT)
    muestras = [np.concatenate([np.flatnonzero(c == k) for k in rng.choice(celdas, len(celdas))]) for _ in range(N_BOOT)]
    filas = []
    for col in v.columns:
        x = (t[col] - t.groupby("municipio")[col].transform("mean")).values
        r = np.corrcoef(x, y.values)[0, 1]
        bs = [np.corrcoef(x[i], y.values[i])[0, 1] for i in muestras]
        lo, hi = np.nanpercentile(bs, [2.5, 97.5])
        filas.append(dict(variable=col, r_dentro_municipio=r, IC95_celdas_inf=lo, IC95_celdas_sup=hi,
                          excluye_cero=bool(lo > 0 or hi < 0), n=len(t)))
    return pd.DataFrame(filas).round(3)


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
    ap.add_argument("--catalogo", type=Path, help="catálogo de T02 (calidad de contorno), opcional")
    ap.add_argument("--pares", type=Path, help="pares de parcelas cercanas de T02, opcional")
    a = ap.parse_args()
    exigir(not a.salida.exists() or not any(a.salida.iterdir()),
           f"{a.salida} ya tiene archivos: usa una carpeta nueva para no mezclar corridas")
    final, a.salida = a.salida, a.salida.with_name(f".{a.salida.name}.en_proceso")
    shutil.rmtree(a.salida, ignore_errors=True)
    a.salida.mkdir(parents=True)

    d = cargar(a.datos)
    v = variables_clima(a.clima)
    exigir(v.index.is_unique and set(d.index) <= set(v.index) and np.isfinite(v.values).all(), "clima incompleto")
    d = d.join(v)
    v.round(4).to_csv(a.salida / "variables_clima_t14.csv")
    part = pd.read_csv(a.particiones)
    celda = validar_particiones(part, d)

    # 8 procedimientos (T03 §5): 4 sin centrar (v2) y los mismos 4 centrados por municipio (H3)
    nombres = {BASE: ([], False)}
    for g in ["lluvia", "tmin", "tmax", "clima"]:
        nombres[f"ref_mas_{g}"] = (GRUPOS[g], False)
        nombres[f"ref_mas_{g}_centrado"] = (GRUPOS[g], True)
    alfas = {n: [] for n in nombres}
    cands = {n: candidato(cols, alfas[n], cen) for n, (cols, cen) in nombres.items()}
    t = d[d.CONJUNTO == "ENTRENAMIENTO"]
    oof = evaluar(t, part, cands, alfas)
    cols = ["ID_POLIGONO", "repeticion", "particion", "escenario", "real", "prediccion", "candidato", "version", "fuente"]
    for c, x in oof.groupby("candidato"):
        x[cols].to_csv(a.salida / f"predicciones_oof_t14_{c}.csv", index=False)
    oof[oof.candidato != BASE][["candidato", "escenario", "repeticion", "particion", "alfa"]] \
        .drop_duplicates().to_csv(a.salida / "alfas_t14.csv", index=False)
    des, dudosas = desglose(oof, d, a.catalogo, a.pares)
    des.to_csv(a.salida / "desglose_errores_t14.csv", index=False)

    m = resumir(oof)
    m.to_csv(a.salida / "metricas_t14.csv", index=False)
    e = emparejada(oof, celda)
    e.to_csv(a.salida / "comparacion_emparejada_t14.csv", index=False)
    if dudosas is not None:
        sens = emparejada(oof, celda, excluir=dudosas).assign(sin_parcelas_dudosas=len(dudosas))
        sens.to_csv(a.salida / "sensibilidad_sin_dudosas_t14.csv", index=False)
    colinealidad(v).to_csv(a.salida / "colinealidad_t14.csv")
    asociacion_dentro(v, d, celda).to_csv(a.salida / "asociacion_dentro_municipio_t14.csv", index=False)
    escala(v, d, celda).to_csv(a.salida / "escala_compartida_t14.csv", index=False)

    p = d[d.CONJUNTO == "PREDICCION"]
    fin = []
    for n in nombres:
        al = []
        pred, fuente = candidato(nombres[n][0], al, nombres[n][1])(t, p)
        fin.append(pd.DataFrame(dict(ID_POLIGONO=p.index, candidato=n, prediccion=pred, fuente=fuente,
                                     alfa=al[0] if al else np.nan, version=VERSION)))
    fin = pd.concat(fin, ignore_index=True)
    exigir(fin.groupby("candidato").ID_POLIGONO.nunique().eq(59).all() and np.isfinite(fin.prediccion).all(),
           "las 59 reservadas no tienen predicción finita")
    fin.to_csv(a.salida / "predicciones_59_t14.csv", index=False)
    if final.exists():
        final.rmdir()
    a.salida.rename(final)          # sólo si todo terminó bien; si falla, no queda nada mezclado
    a.salida = final

    pd.set_option("display.width", 200)
    print(m.to_string(index=False), "\n")
    print(e.to_string(index=False), "\n")
    print(colinealidad(v).to_string(), "\n")
    print(escala(v, d, celda).to_string(index=False))
    print("\nα elegidos:", {n: pd.Series(x).value_counts().to_dict() for n, x in alfas.items() if x})


if __name__ == "__main__":
    main()
