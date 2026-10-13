"""T11: aporte del frente satelital sobre la referencia territorial (D006, D019, D021, D022, D023, O2, O4).

v2 (D022, revisión de Dani al PR #15): la selección interna recalcula referencia y residuo dentro de
cada partición interna; estrato `otros` de T03 §5; desgloses y sensibilidad de T03 §4 bis.
v2.1 (D023, revisiones de Migue y Dani): comparación emparejada promediada primero por parcela (como
T08); desgloses por repetición y después promedio (T03 §4); controles que detienen el programa;
columna `candidato` con nombres estables. Las predicciones no cambian.

Uso:
    python scripts/t11_aporte_satelital.py
"""
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parents[1]
TABLA = RAIZ / "registro" / "t07" / "tabla_comun.csv"
PARTICIONES = RAIZ / "registro" / "t03" / "particiones.csv"
CALIDAD = RAIZ / "registro" / "t07" / "calidad_parcelas.csv"
OOF_T08 = RAIZ / "registro" / "t03" / "predicciones_oof_referencias_media_mun__resp_grupo.csv"
SALIDA = RAIZ / "registro" / "t11"
ESCENARIOS = {"A": "particion_principal", "B": "particion_espacial"}

# Modelo (D021): Ridge sobre el residuo de la referencia; α elegido por selección interna de T03 §5
# (4 particiones, semilla 0, estrato = municipio con ≥4 etiquetas en el entrenamiento, si no `otros`).
# Criterio de α: error cuadrático (D021). Empate: el α más grande (modelo más simple, T03 §4).
ALFAS = [0.1, 1, 3, 10, 30, 100, 300, 1000, 10000]
N_INTERNAS = 4
SEMILLA_INTERNA = 0
VERSION = "T11-v2.1"

# Comparación emparejada (mismos valores que T08)
N_BOOT = 5000
SEMILLA_BOOT = 20261006
COMPARACIONES = [(n, 0, "promocion") for n in range(1, 9)] + [
    (6, 1, "O2: espectral sobre calidad"),
    (6, 5, "O2: calidad sobre espectral"),
    (3, 2, "ventana S2: abr_oct frente a jun_oct"),
    (5, 4, "ventana Planet: abr_oct frente a jun_oct"),
]

# Columnas de D006 ({v} = ventana)
S2 = ["s2_ndvi_max_{v}", "s2_ndvi_integral_{v}", "s2_ndvi_dias_sobre_mitad_{v}",
      "s2_ndwi_en_maximo_{v}", "s2_ndvi_al_corte"]
PL = ["pl_ndvi_max_{v}", "pl_ndvi_integral_{v}", "pl_lai2_max_{v}",
      "pl_ndvi_dias_sobre_mitad_{v}", "pl_ndvi_dia_inicio_{v}", "pl_ndvi_al_corte"]
CALIDAD_PL = ["pl_capturas_abr_oct", "pl_hueco_max_abr_oct", "pl_nubosidad_media_abr_oct"]


def expandir(plantilla, v):
    return [c.format(v=v) for c in plantilla]


# Nombres estables para integrar resultados (T15/T16)
CANDIDATOS = {
    0: "media_mun__resp_grupo",
    1: "t11_c1_calidad_planet_abr_oct",
    2: "t11_c2_s2_jun_oct",
    3: "t11_c3_s2_abr_oct",
    4: "t11_c4_planet_jun_oct",
    5: "t11_c5_planet_abr_oct",
    6: "t11_c6_planet_abr_oct_calidad",
    7: "t11_c7_planet_abr_oct_heterogeneidad",
    8: "t11_c8_planet_abr_oct_centrado",
}

CONFIGS = {
    1: dict(cols=CALIDAD_PL, centrar=False),
    2: dict(cols=expandir(S2, "jun_oct"), centrar=False),
    3: dict(cols=expandir(S2, "abr_oct"), centrar=False),
    4: dict(cols=expandir(PL, "jun_oct"), centrar=False),
    5: dict(cols=expandir(PL, "abr_oct"), centrar=False),
    6: dict(cols=expandir(PL, "abr_oct") + CALIDAD_PL, centrar=False),
    7: dict(cols=expandir(PL, "abr_oct") + ["pl_ndvi_std_en_maximo_abr_oct"], centrar=False),
    8: dict(cols=expandir(PL, "abr_oct"), centrar=True),
}


# ---------------------------------------------------------------- revisión de datos
def revisar_datos(tabla, part):
    print("tabla_comun:", tabla.shape)
    print(tabla.conjunto_origen.value_counts(), "\n")
    print("particiones:", part.shape)
    print("columnas:", list(part.columns), "\n")

    # 1) ¿Existen todas las columnas de las 8 configuraciones?
    faltan = {k: [c for c in cfg["cols"] if c not in tabla.columns] for k, cfg in CONFIGS.items()}
    print("columnas faltantes por config:", {k: v for k, v in faltan.items() if v} or "ninguna", "\n")

    # 2) Faltantes (NaN) por columna, en las 138 y en las 197
    entr = tabla[tabla.conjunto_origen == "ENTRENAMIENTO"]
    usadas = sorted({c for cfg in CONFIGS.values() for c in cfg["cols"]})
    nan = pd.DataFrame({"nan_138": entr[usadas].isna().sum(), "nan_197": tabla[usadas].isna().sum()})
    print("faltantes por columna:\n", nan[nan.sum(axis=1) > 0] if nan.values.any() else "ninguno", "\n")

    # 3) ¿Los ids de entrenamiento coinciden con los de las particiones?
    ids_tabla = set(entr.id_parcela)
    ids_part = set(part.ID_POLIGONO)
    print("ids en tabla y no en particiones:", sorted(ids_tabla - ids_part))
    print("ids en particiones y no en tabla:", sorted(ids_part - ids_tabla), "\n")


def preparar(tabla, part):
    """Une las particiones (138 parcelas × 5 repeticiones = 690 filas) con el rendimiento y las variables."""
    usadas = sorted({c for cfg in CONFIGS.values() for c in cfg["cols"]})
    d = part.merge(tabla[["id_parcela", "rendimiento_t_ha"] + usadas],
                   left_on="ID_POLIGONO", right_on="id_parcela", how="left", validate="many_to_one")
    d = d.drop(columns="id_parcela").rename(columns={"rendimiento_t_ha": "real"})
    if d.duplicated(["ID_POLIGONO", "repeticion"]).any():
        raise ValueError("Una parcela aparece más de una vez en la misma repetición de las particiones")
    if len(d) != 690 or d.real.isna().any():
        raise ValueError(f"Se esperaban 690 filas con rendimiento; hay {len(d)} y {int(d.real.isna().sum())} sin él")
    return d


def separar(dr, col, k):
    """Entrenamiento y evaluación de una partición externa; se detiene si comparten parcelas."""
    tr, te = dr[dr[col] != k], dr[dr[col] == k]
    if set(tr.ID_POLIGONO) & set(te.ID_POLIGONO):
        raise ValueError(f"Hay parcelas en entrenamiento y evaluación a la vez (partición {k})")
    return tr, te


# ---------------------------------------------------------------- referencia territorial
def referencia_municipal(tr, te):
    """media_mun__resp_grupo (D019): media del municipio en el entrenamiento;
    si el municipio no tiene parcelas ahí, media de su grupo; si tampoco, media global."""
    mun = tr.groupby("municipio").real.mean()
    grp = tr.groupby("grupo_registro").real.mean()
    ref = te.municipio.map(mun)
    fuente = np.where(ref.notna(), "municipio", None).astype(object)
    g = te.grupo_registro.map(grp)
    fuente[(ref.isna() & g.notna()).values] = "grupo"
    ref = ref.fillna(g)
    fuente[ref.isna().values] = "global"
    ref = ref.fillna(tr.real.mean())
    return ref.values, fuente


def referencia_sin_la_fila(tr):
    """O4: la referencia de cada parcela de entrenamiento se calcula sin esa parcela."""
    ref = np.empty(len(tr))
    for i in range(len(tr)):
        resto = tr.drop(index=tr.index[i])
        ref[i] = referencia_municipal(resto, tr.iloc[[i]])[0][0]
    return ref


def referencia_oof(d):
    """Predicciones fuera de muestra de la referencia, en A y B × 5 repeticiones × 5 particiones."""
    filas = []
    for esc, col in ESCENARIOS.items():
        for rep, dr in d.groupby("repeticion"):
            for k in sorted(dr[col].unique()):
                tr, te = separar(dr, col, k)
                ref, fuente = referencia_municipal(tr, te)
                filas.append(pd.DataFrame({"ID_POLIGONO": te.ID_POLIGONO.values, "repeticion": rep,
                                           "escenario": esc, "ref": ref, "fuente_t11": fuente}))
    return pd.concat(filas, ignore_index=True)


def comprobar_referencia(d, ruta_t08=OOF_T08):
    """La referencia de T11 debe dar las mismas predicciones fuera de muestra que T08; si no, se detiene."""
    mia = referencia_oof(d)
    t08 = pd.read_csv(ruta_t08)
    comp = mia.merge(t08, on=["ID_POLIGONO", "repeticion", "escenario"], validate="one_to_one")
    dif = (comp.ref - comp.prediccion).abs().max()
    misma = bool((comp.fuente_t11 == comp.fuente).all())
    print(f"filas comparadas: {len(comp)} (esperadas 1380)")
    print(f"máxima diferencia con T08: {dif:.2e}")
    print("misma fuente en todas:", misma)
    print("filas con respaldo por escenario:\n", mia[mia.fuente_t11 != "municipio"].groupby("escenario").size())
    if len(comp) != 1380 or not dif < 1e-9 or not misma:
        raise ValueError(f"La referencia de T11 no reproduce T08 (filas {len(comp)}, diferencia {dif}, misma fuente {misma})")


# ---------------------------------------------------------------- modelo: referencia + Ridge(residuo)
def transformar(tr, te, cfg):
    """Prepara las columnas de una config usando SÓLO el entrenamiento (centrado y escalado)."""
    cols = cfg["cols"]
    xtr = tr[cols].astype(float)
    xte = te[cols].astype(float)
    assert xtr.notna().all().all() and xte.notna().all().all(), "hay faltantes: falta imputar"
    if cfg["centrar"]:
        # Config 8: restar el promedio municipal de cada variable, calculado con el entrenamiento.
        medias = xtr.groupby(tr.municipio.values).mean()
        global_ = xtr.mean()
        xtr = xtr - medias.reindex(tr.municipio.values).values
        xte = xte - medias.reindex(te.municipio.values).fillna(global_).values
    esc = StandardScaler().fit(xtr)
    return esc.transform(xtr), esc.transform(xte)


def estrato_interno(tr):
    """T03 §5: municipio si tiene al menos 4 etiquetas en este entrenamiento; si no, `otros`."""
    n = tr.municipio.map(tr.municipio.value_counts())
    return tr.municipio.where(n >= N_INTERNAS, "otros")


def particiones_internas(tr):
    """Las 4 particiones internas, con referencia y residuo calculados SÓLO con su parte de entrenamiento.
    No dependen de la config, así que se calculan una vez por entrenamiento externo."""
    skf = StratifiedKFold(N_INTERNAS, shuffle=True, random_state=SEMILLA_INTERNA)
    internas = []
    for i_a, i_b in skf.split(tr, estrato_interno(tr)):
        a, b = tr.iloc[i_a], tr.iloc[i_b]
        residuo_a = a.real.values - referencia_sin_la_fila(a)  # O4 dentro de la parte interna
        ref_b, _ = referencia_municipal(a, b)                    # referencia de validación, sólo con `a`
        internas.append((a, b, residuo_a, ref_b))
    return internas


def elegir_alfa(internas, cfg):
    """Selección interna sin fuga: se predice el rendimiento de `b` como ref_b + Ridge(residuo de `a`)."""
    errores = np.zeros(len(ALFAS))
    for a, b, residuo_a, ref_b in internas:
        xa, xb = transformar(a, b, cfg)
        for j, alfa in enumerate(ALFAS):
            pred = ref_b + Ridge(alpha=alfa).fit(xa, residuo_a).predict(xb)
            errores[j] += ((pred - b.real.values) ** 2).sum()
    errores = np.round(errores, 6)
    candidatos = [j for j in range(len(ALFAS)) if errores[j] == errores.min()]
    return ALFAS[max(candidatos)]  # empate: el α más grande


def evaluar_todo(d):
    """Corre la referencia y las 8 configs en A y B × 5 repeticiones × 5 particiones."""
    preds, coefs = [], []
    for esc, col in ESCENARIOS.items():
        for rep, dr in d.groupby("repeticion"):
            for k in sorted(dr[col].unique()):
                tr, te = separar(dr, col, k)
                ref_te, fuente = referencia_municipal(tr, te)
                residuo = tr.real.values - referencia_sin_la_fila(tr)  # O4
                internas = particiones_internas(tr)
                base = dict(ID_POLIGONO=te.ID_POLIGONO.values, repeticion=rep, particion=k,
                            escenario=esc, real=te.real.values, referencia=ref_te, fuente=fuente)
                preds.append(pd.DataFrame({**base, "config": 0, "alfa": np.nan, "prediccion": ref_te}))
                for n, cfg in CONFIGS.items():
                    alfa = elegir_alfa(internas, cfg)
                    xtr, xte = transformar(tr, te, cfg)
                    modelo = Ridge(alpha=alfa).fit(xtr, residuo)
                    preds.append(pd.DataFrame({**base, "config": n, "alfa": alfa,
                                               "prediccion": ref_te + modelo.predict(xte)}))
                    coefs.append(pd.DataFrame({"config": n, "escenario": esc, "repeticion": rep,
                                               "particion": k, "alfa": alfa,
                                               "variable": cfg["cols"], "coef": modelo.coef_}))
            print(f"  escenario {esc}, repetición {rep} lista")
    out = pd.concat(preds, ignore_index=True)
    out["candidato"] = out.config.map(CANDIDATOS)
    out["version"] = VERSION
    return out, pd.concat(coefs, ignore_index=True)


def metricas(y, p):
    e = p - y
    ss = ((y - y.mean()) ** 2).sum()
    return dict(MAE=np.abs(e).mean(), RMSE=np.sqrt((e ** 2).mean()), sesgo=e.mean(),
                R2=1 - (e ** 2).sum() / ss)


def resumir(oof):
    """Métricas por repetición (138 predicciones fuera de muestra) y promedio de las 5,
    en 'todas' y en 'sin_respaldo' (D019)."""
    filas = []
    for sub, mask in [("todas", oof.fuente.notna()), ("sin_respaldo", oof.fuente == "municipio")]:
        for (esc, cfg, rep), g in oof[mask].groupby(["escenario", "config", "repeticion"]):
            filas.append(dict(subconjunto=sub, escenario=esc, config=cfg, repeticion=rep,
                              n=len(g), **metricas(g.real.values, g.prediccion.values)))
    por_rep = pd.DataFrame(filas)
    res = (por_rep.groupby(["subconjunto", "escenario", "config"])
           .agg(n=("n", "mean"), MAE=("MAE", "mean"), RMSE=("RMSE", "mean"), sesgo=("sesgo", "mean"),
                R2=("R2", "mean"), RMSE_sd_rep=("RMSE", lambda s: s.std(ddof=0)))
           .reset_index())
    res.insert(3, "candidato", res.config.map(CANDIDATOS))
    return res


# ---------------------------------------------------------------- comparación emparejada (regla T03)
def intervalo(pp, bloque, metrica):
    """IC95 por bootstrap de bloques (celdas CHIRPS o parcelas) para ΔMAE o ΔRMSE."""
    g = pp.groupby(bloque)
    n = g.size().values
    rng = np.random.RandomState(SEMILLA_BOOT)
    k = rng.randint(0, len(n), (N_BOOT, len(n)))
    nn = n[k].sum(axis=1)
    if metrica == "MAE":
        dif = (g.ae_c.sum() - g.ae_b.sum()).values
        bs = dif[k].sum(axis=1) / nn
    else:
        sc, sb = g.se_c.sum().values, g.se_b.sum().values
        bs = np.sqrt(sc[k].sum(axis=1) / nn) - np.sqrt(sb[k].sum(axis=1) / nn)
    return np.percentile(bs, [2.5, 97.5])


def comparar(oof_esc, celda, cand, base, sub):
    """Candidato frente a base en un escenario y subconjunto; regla de T03 con MAE y con RMSE."""
    b = oof_esc[oof_esc.config == base].set_index(["ID_POLIGONO", "repeticion"]).sort_index()
    c = oof_esc[oof_esc.config == cand].set_index(["ID_POLIGONO", "repeticion"]).loc[b.index]
    mask = b.fuente.notna() if sub == "todas" else b.fuente == "municipio"
    b, c = b[mask], c[mask]
    f = pd.DataFrame({"y": b.real, "ae_c": (c.prediccion - c.real).abs(), "ae_b": (b.prediccion - b.real).abs(),
                      "se_c": (c.prediccion - c.real) ** 2, "se_b": (b.prediccion - b.real) ** 2})

    # Por repetición (138 predicciones o menos en sin_respaldo)
    r = f.groupby(level="repeticion")
    d_mae = r.ae_c.mean() - r.ae_b.mean()
    d_rmse = np.sqrt(r.se_c.mean()) - np.sqrt(r.se_b.mean())
    ss = r.y.apply(lambda y: ((y - y.mean()) ** 2).sum())
    d_r2 = (r.se_b.sum() - r.se_c.sum()) / ss

    # Por parcela (promedio de sus repeticiones), para el bootstrap
    pp = f.groupby(level="ID_POLIGONO").mean()
    pp["celda"] = celda.reindex(pp.index).values
    pp["parcela"] = pp.index
    mae_c, mae_p = intervalo(pp, "celda", "MAE"), intervalo(pp, "parcela", "MAE")
    rmse_c, rmse_p = intervalo(pp, "celda", "RMSE"), intervalo(pp, "parcela", "RMSE")

    # Como T08: ΔMAE = promedio por parcela (cada parcela pesa igual aunque tenga distinto número de
    # repeticiones elegibles); ΔRMSE y el signo por repetición.
    dMAE, dRMSE = (pp.ae_c - pp.ae_b).mean(), d_rmse.mean()
    reps_mae, reps_rmse = int((d_mae < 0).sum()), int((d_rmse < 0).sum())
    return dict(
        subconjunto=sub, config=cand, candidato=CANDIDATOS[cand], frente_a=CANDIDATOS[base],
        n_predicciones=len(f), n_parcelas=len(pp), n_celdas=pp.celda.nunique(),
        dMAE=dMAE, IC95_celdas_MAE_inf=mae_c[0], IC95_celdas_MAE_sup=mae_c[1],
        IC95_parcelas_MAE_inf=mae_p[0], IC95_parcelas_MAE_sup=mae_p[1], reps_mejoran_MAE=reps_mae,
        dRMSE=dRMSE, IC95_celdas_RMSE_inf=rmse_c[0], IC95_celdas_RMSE_sup=rmse_c[1],
        IC95_parcelas_RMSE_inf=rmse_p[0], IC95_parcelas_RMSE_sup=rmse_p[1], reps_mejoran_RMSE=reps_rmse,
        dR2=d_r2.mean(),
        parcelas_mejoran=int((pp.ae_c < pp.ae_b).sum()), parcelas_empeoran=int((pp.ae_c > pp.ae_b).sum()),
        cumple_regla_MAE=bool(dMAE <= -0.01 and mae_c[1] < 0 and reps_mae >= 4 and dRMSE <= 0.01),
        cumple_regla_RMSE=bool(dRMSE <= -0.01 and rmse_c[1] < 0 and reps_rmse >= 4 and dMAE <= 0.01),
    )


def comparaciones(oof, celda):
    filas = []
    for esc, oof_esc in oof.groupby("escenario"):
        for cand, base, tipo in COMPARACIONES:
            for sub in ["todas", "sin_respaldo"]:
                filas.append(dict(escenario=esc, tipo=tipo, **comparar(oof_esc, celda, cand, base, sub)))
    return pd.DataFrame(filas)


# ---------------------------------------------------------------- desgloses y sensibilidad (T03 §4 y §4 bis)
def unir_calidad(oof):
    cal = pd.read_csv(CALIDAD, dtype={"escalon_etiqueta_municipio": str})
    out = oof.merge(cal, left_on="ID_POLIGONO", right_on="id_parcela", how="left", validate="many_to_one")
    assert len(out) == len(oof) and out.contorno_categoria.notna().all()
    out["contorno"] = np.where(out.contorno_categoria == "A", "A", "B o C")
    out["escalon"] = out.escalon_etiqueta_municipio.fillna("sin escalón")
    return out


def desgloses(oof, part):
    """Error por municipio, grupo, contorno, angosta, escalón de la etiqueta y vecindad.
    T03 §4: métricas por repetición y después promedio de las repeticiones."""
    d = unir_calidad(oof)
    p = part.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO")
    d["municipio"] = d.ID_POLIGONO.map(p.municipio)
    d["grupo_registro"] = d.ID_POLIGONO.map(p.grupo_registro)
    d["e"] = d.prediccion - d.real
    paso = pd.to_numeric(d.escalon_etiqueta_municipio, errors="coerce")
    d["bajo_resolucion"] = np.where(paso.notna(), d.e.abs() < paso / 2, np.nan)
    ejes = {"municipio": "municipio", "grupo_registro": "grupo_registro", "contorno": "contorno",
            "angosta_o_muy_pequena": "contorno_angosta_o_muy_pequena", "escalon_etiqueta": "escalon",
            "vecina_etiquetada_menos_20m": "vecina_etiquetada_menos_20m"}
    filas = []
    for sub, mask in [("todas", d.fuente.notna()), ("sin_respaldo", d.fuente == "municipio")]:
        for nombre, col in ejes.items():
            for (esc, cfg, cat, rep), g in d[mask].groupby(["escenario", "config", col, "repeticion"]):
                filas.append(dict(subconjunto=sub, escenario=esc, config=cfg, desglose=nombre, categoria=cat,
                                  repeticion=rep, ids=frozenset(g.ID_POLIGONO), n_predicciones=len(g),
                                  MAE=g.e.abs().mean(), RMSE=np.sqrt((g.e ** 2).mean()), sesgo=g.e.mean(),
                                  prop_error_menor_medio_escalon=g.bajo_resolucion.mean()))
    por_rep = pd.DataFrame(filas)
    claves = ["subconjunto", "escenario", "config", "desglose", "categoria"]
    r = (por_rep.groupby(claves)
         .agg(n_parcelas=("ids", lambda s: len(frozenset().union(*s))), n_repeticiones=("repeticion", "nunique"),
              n_predicciones=("n_predicciones", "sum"), MAE=("MAE", "mean"), RMSE=("RMSE", "mean"),
              sesgo=("sesgo", "mean"), MAE_sd_rep=("MAE", lambda s: s.std(ddof=0)),
              prop_error_menor_medio_escalon=("prop_error_menor_medio_escalon", "mean"))
         .reset_index())
    r.insert(3, "candidato", r.config.map(CANDIDATOS))
    r["poco_informativo"] = r.n_parcelas < 5
    return r


def sensibilidad_sin_alerta(oof):
    """T03 §4 bis: repetir las métricas sin las 24 etiquetadas con alerta de contorno (B, C o angosta)
    y ver si se mantiene el orden de los candidatos. Mide estabilidad; no decide."""
    d = unir_calidad(oof)
    sin = d[d.alerta_contorno_t03_bis != "si"]
    print(f"  parcelas sin alerta: {sin.ID_POLIGONO.nunique()} de {d.ID_POLIGONO.nunique()}")
    con, sin_ = resumir(oof), resumir(sin).drop(columns="candidato")
    m = con.merge(sin_, on=["subconjunto", "escenario", "config"], suffixes=("", "_sin24"))
    for sufijo in ["", "_sin24"]:
        for met in ["MAE", "RMSE"]:
            ref = m[m.config == 0].set_index(["subconjunto", "escenario"])[met + sufijo]
            m["d" + met + sufijo] = m[met + sufijo] - m.set_index(["subconjunto", "escenario"]).index.map(ref)
            m["orden_" + met + sufijo] = m.groupby(["subconjunto", "escenario"])[met + sufijo].rank(method="min")
    return m


# ---------------------------------------------------------------- principal
def main():
    tabla = pd.read_csv(TABLA)
    part = pd.read_csv(PARTICIONES)
    revisar_datos(tabla, part)
    d = preparar(tabla, part)
    comprobar_referencia(d)

    print("\ncorriendo referencia + 8 configs...")
    t0 = time.time()
    oof, coefs = evaluar_todo(d)
    print(f"listo en {time.time() - t0:.0f} s")

    SALIDA.mkdir(parents=True, exist_ok=True)
    oof.to_csv(SALIDA / "predicciones_oof_t11.csv", index=False)
    coefs.to_csv(SALIDA / "coeficientes_t11.csv", index=False)
    res = resumir(oof)
    res.to_csv(SALIDA / "metricas_t11.csv", index=False)

    pd.set_option("display.width", 200)
    print("\nalfa elegido (veces por config, ambos escenarios):")
    print(oof[oof.config > 0].drop_duplicates(["config", "escenario", "repeticion", "particion"])
          .groupby("config").alfa.value_counts().unstack(fill_value=0))
    print("\nmétricas en sin_respaldo (config 0 = referencia):")
    print(res[res.subconjunto == "sin_respaldo"].round(4).to_string(index=False))

    print("\ncomparación emparejada (bootstrap por celdas, puede tardar un poco)...")
    celda = d.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps
    comp = comparaciones(oof, celda)
    comp.to_csv(SALIDA / "comparacion_emparejada_t11.csv", index=False)
    cols = ["escenario", "subconjunto", "config", "dRMSE", "IC95_celdas_RMSE_inf",
            "IC95_celdas_RMSE_sup", "reps_mejoran_RMSE", "dMAE", "IC95_celdas_MAE_sup", "reps_mejoran_MAE",
            "dR2", "cumple_regla_RMSE", "cumple_regla_MAE"]
    print("\nfrente a la referencia, sin_respaldo (aquí se decide, D019):")
    sel = (comp.tipo == "promocion") & (comp.subconjunto == "sin_respaldo")
    print(comp.loc[sel, cols].round(4).to_string(index=False))
    print("\ncomparaciones descriptivas (O2 y ventanas), sin_respaldo:")
    sel = (comp.tipo != "promocion") & (comp.subconjunto == "sin_respaldo")
    print(comp.loc[sel, ["tipo"] + cols].round(4).to_string(index=False))
    print("\n¿alguna config cumple la regla frente a la referencia (cualquier escenario/subconjunto)?")
    prom = comp[comp.tipo == "promocion"]
    print("  con MAE:", prom.cumple_regla_MAE.any(), "| con RMSE:", prom.cumple_regla_RMSE.any())

    print("\ndesgloses del error (T03 §4 y §4 bis)...")
    des = desgloses(oof, part)
    des.to_csv(SALIDA / "desglose_error_t11.csv", index=False)
    print(f"  {len(des)} filas en desglose_error_t11.csv")

    print("\nsensibilidad sin las 24 parcelas con alerta de contorno (T03 §4 bis):")
    sens = sensibilidad_sin_alerta(oof)
    sens.to_csv(SALIDA / "sensibilidad_sin_alerta_t11.csv", index=False)
    cols = ["escenario", "config", "dRMSE", "dRMSE_sin24", "orden_RMSE", "orden_RMSE_sin24",
            "dMAE", "dMAE_sin24", "orden_MAE", "orden_MAE_sin24"]
    print(sens.loc[sens.subconjunto == "sin_respaldo", cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()