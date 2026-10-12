"""T10: aporte de relieve y área sobre la referencia territorial (docs/T10_relieve_area.md, D_T10_001).

Predicción = referencia media_mun__resp_grupo (D019) + Ridge ajustado al residuo
(real − referencia calculada sin la fila, O4). Todo lo que se aprende (relleno, centrado,
escalado, referencia, residuo y la opción de la selección interna) se ajusta sólo con el
entrenamiento de cada partición.

Dos procedimientos (D_T10_001):
- ``t10`` (principal, decide): opciones «referencia sola» y α de la rejilla; se elige con el
  error absoluto en la validación interna; empate a lo más simple.
- ``puente_t11`` (descriptivo, nunca decide): procedimiento exacto de T11 v2 (D021–D022):
  sólo α, error cuadrático, empate al α más grande.

Uso, desde la raíz del repositorio:
    python -m scripts.t10_relieve_area --comprobar-referencia
    python -m scripts.t10_relieve_area --diagnostico --salida registro/t10
    python -m scripts.t10_relieve_area --evaluar --salida registro/t10
Los modos que escriben nunca sobrescriben un archivo existente.
"""
import argparse
import hashlib
import json
import platform
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parents[1]
TABLA = RAIZ / "registro" / "t07" / "tabla_comun.csv"
CALIDAD_PARCELAS = RAIZ / "registro" / "t07" / "calidad_parcelas.csv"
CALIDAD_RELIEVE = RAIZ / "registro" / "t07" / "calidad_relieve.csv"
PARTICIONES = RAIZ / "registro" / "t03" / "particiones.csv"
OOF_T08 = RAIZ / "registro" / "t03" / "predicciones_oof_referencias_media_mun__resp_grupo.csv"
P59_T08 = RAIZ / "registro" / "t03" / "predicciones_59_referencias.csv"
ENTRADAS = [TABLA, CALIDAD_PARCELAS, CALIDAD_RELIEVE, PARTICIONES, OOF_T08, P59_T08]

VERSION = "T10-v1"
ESCENARIOS = {"A": "particion_principal", "B": "particion_espacial"}
REFERENCIA_T08 = "media_mun__resp_grupo"

# Selección interna (T03 §5)
ALFAS = [0.1, 1, 3, 10, 30, 100, 300, 1000, 10000]
REFERENCIA_SOLA = None
N_INTERNAS = 4
SEMILLA_INTERNA = 0
PROCEDIMIENTOS = {
    "t10": dict(opciones=[REFERENCIA_SOLA] + ALFAS, criterio="absoluto", decide=True),
    "puente_t11": dict(opciones=list(ALFAS), criterio="cuadratico", decide=False),
}

# Comparación emparejada (los mismos valores que T08)
N_BOOT = 5000
SEMILLA_BOOT = 20261006

# Control de revuelto (sólo si alguna configuración del principal cumple la regla)
N_REVUELTO = 20
SEMILLA_REVUELTO = 20261012
UMBRAL_REVUELTO = 0.05

# Entradas (D_T10_001). El logaritmo es una transformación fija, no se aprende.
ELEV, PEND, AREA = "elevacion_media_m", "pendiente_media_t10_grados", "log_area_ha"
CONFIGS = {
    1: dict(nombre="elevacion", cols=[ELEV], centrar=False),
    2: dict(nombre="pendiente", cols=[PEND], centrar=False),
    3: dict(nombre="area", cols=[AREA], centrar=False),
    4: dict(nombre="relieve", cols=[ELEV, PEND], centrar=False),
    5: dict(nombre="relieve_area", cols=[ELEV, PEND, AREA], centrar=False),
    6: dict(nombre="relieve_area_centrado", cols=[ELEV, PEND, AREA], centrar=True),
}
DESCRIPTIVAS = [(5, 4, "area sobre relieve"), (6, 5, "centrado por municipio frente a sin centrar")]
CELDA_RELIEVE_HA = 1.44  # 120 m × 120 m


# ---------------------------------------------------------------- lectura
def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def leer_entradas():
    """Tabla común con log del área, particiones (690 filas) y la unión de ambas."""
    tabla = pd.read_csv(TABLA)
    part = pd.read_csv(PARTICIONES)
    assert tabla.id_parcela.is_unique and len(tabla) == 197
    assert tabla.area_ha_origen.gt(0).all()
    tabla[AREA] = np.log(tabla.area_ha_origen.astype(float))
    etiq = tabla[tabla.rendimiento_t_ha.notna()]
    assert len(etiq) == 138 and set(etiq.id_parcela) == set(part.ID_POLIGONO)
    # El grupo de registro de T03 es cultivo_origen de T07 (contrato_columnas.json).
    g = part.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").grupo_registro
    assert (etiq.set_index("id_parcela").cultivo_origen.reindex(g.index) == g).all()
    cols = [ELEV, PEND, AREA]
    d = part.merge(tabla[["id_parcela", "rendimiento_t_ha"] + cols], left_on="ID_POLIGONO",
                   right_on="id_parcela", how="left", validate="many_to_one")
    d = d.drop(columns="id_parcela").rename(columns={"rendimiento_t_ha": "real"})
    assert len(d) == 690 and d.real.notna().all()
    return tabla, part, d


# ---------------------------------------------------------------- referencia territorial (D019)
def referencia_municipal(tr, te):
    """Media del municipio en el entrenamiento; si el municipio no está, media de su grupo;
    si tampoco, media global. Devuelve (predicción, fuente)."""
    mun = tr.groupby("municipio").real.mean()
    grp = tr.groupby("grupo_registro").real.mean()
    ref = te.municipio.map(mun)
    fuente = np.where(ref.notna(), "municipio", None).astype(object)
    g = te.grupo_registro.map(grp)
    fuente[(ref.isna() & g.notna()).to_numpy()] = "grupo"
    ref = ref.fillna(g)
    fuente[ref.isna().to_numpy()] = "global"
    ref = ref.fillna(tr.real.mean())
    return ref.to_numpy(dtype=float), fuente


def referencia_sin_la_fila(tr):
    """O4: referencia de cada fila de entrenamiento calculada sin esa fila (misma cascada
    municipio → grupo → global que referencia_municipal, aplicada al resto)."""
    y = tr.real.to_numpy(dtype=float)
    n = len(y)
    sm = tr.groupby("municipio").real.transform("sum").to_numpy(dtype=float)
    cm = tr.groupby("municipio").real.transform("count").to_numpy()
    sg = tr.groupby("grupo_registro").real.transform("sum").to_numpy(dtype=float)
    cg = tr.groupby("grupo_registro").real.transform("count").to_numpy()
    total = y.sum()
    out = np.where(cm > 1, (sm - y) / np.maximum(cm - 1, 1),
                   np.where(cg > 1, (sg - y) / np.maximum(cg - 1, 1), (total - y) / max(n - 1, 1)))
    return out


# ---------------------------------------------------------------- preparación de variables
def transformar(tr, te, cols, centrar):
    """Relleno con la mediana del entrenamiento, centrado municipal opcional (medias del
    entrenamiento; municipio ausente → media global) y escalado. Todo ajustado con `tr`."""
    xtr = tr[cols].astype(float)
    xte = te[cols].astype(float)
    mediana = xtr.median()
    if mediana.isna().any():
        raise ValueError("Una columna no tiene valores en el entrenamiento")
    xtr = xtr.fillna(mediana)
    xte = xte.fillna(mediana)
    if centrar:
        medias = xtr.groupby(tr.municipio.to_numpy()).mean()
        globales = xtr.mean()
        xtr = xtr - medias.reindex(tr.municipio.to_numpy()).to_numpy()
        m_te = medias.reindex(te.municipio.to_numpy()).fillna(globales)
        xte = xte - m_te.to_numpy()
    esc = StandardScaler().fit(xtr.to_numpy())
    return esc.transform(xtr.to_numpy()), esc.transform(xte.to_numpy())


# ---------------------------------------------------------------- selección interna (T03 §5)
def estrato_interno(tr):
    n = tr.municipio.map(tr.municipio.value_counts())
    return tr.municipio.where(n >= N_INTERNAS, "otros")


def particiones_internas(tr):
    """4 particiones internas; referencia y residuo de cada una sólo con su parte `a`."""
    skf = StratifiedKFold(N_INTERNAS, shuffle=True, random_state=SEMILLA_INTERNA)
    internas = []
    with warnings.catch_warnings():
        # En B el estrato `otros` puede tener 3 parcelas (D022); sklearn lo avisa, no es error.
        warnings.filterwarnings("ignore", message="The least populated class", category=UserWarning)
        cortes = list(skf.split(np.zeros(len(tr)), estrato_interno(tr)))
    for i_a, i_b in cortes:
        a, b = tr.iloc[i_a], tr.iloc[i_b]
        residuo_a = a.real.to_numpy(dtype=float) - referencia_sin_la_fila(a)
        ref_b, _ = referencia_municipal(a, b)
        internas.append((a, b, residuo_a, ref_b))
    return internas


def desempatar(errores, opciones):
    """Menor error (redondeado a 6 decimales); en empate gana lo más simple:
    primero «referencia sola», después el α más grande."""
    errores = np.round(np.asarray(errores, dtype=float), 6)
    empatadas = [opciones[j] for j in range(len(opciones)) if errores[j] == errores.min()]
    return min(empatadas, key=lambda op: (0, 0.0) if op is REFERENCIA_SOLA else (1, -float(op)))


def elegir_opcion(internas, cfg, procedimiento):
    proc = PROCEDIMIENTOS[procedimiento]
    opciones = proc["opciones"]
    errores = np.zeros(len(opciones))
    for a, b, residuo_a, ref_b in internas:
        xa, xb = transformar(a, b, cfg["cols"], cfg["centrar"])
        yb = b.real.to_numpy(dtype=float)
        for j, op in enumerate(opciones):
            pred = ref_b if op is REFERENCIA_SOLA else ref_b + Ridge(alpha=op).fit(xa, residuo_a).predict(xb)
            e = pred - yb
            errores[j] += np.abs(e).sum() if proc["criterio"] == "absoluto" else (e ** 2).sum()
    return desempatar(errores, opciones)


def ajustar_y_predecir(tr, te, residuo, cfg, opcion):
    """Devuelve (corrección sobre la referencia, coeficientes). Con «referencia sola», cero."""
    if opcion is REFERENCIA_SOLA:
        return np.zeros(len(te)), np.full(len(cfg["cols"]), np.nan)
    xtr, xte = transformar(tr, te, cfg["cols"], cfg["centrar"])
    modelo = Ridge(alpha=opcion).fit(xtr, residuo)
    return modelo.predict(xte), modelo.coef_


def etiqueta_opcion(op):
    return "referencia_sola" if op is REFERENCIA_SOLA else f"alfa_{op:g}"


# ---------------------------------------------------------------- evaluación externa
def evaluar(d, configs=CONFIGS, procedimientos=PROCEDIMIENTOS, escenarios=ESCENARIOS, verbose=True):
    """Predicciones fuera del entrenamiento (formato T03 §7 + procedimiento, config, opción)."""
    preds, coefs = [], []
    for esc, col in escenarios.items():
        for rep, dr in d.groupby("repeticion", sort=True):
            for k in sorted(dr[col].unique()):
                tr, te = dr[dr[col] != k], dr[dr[col] == k]
                ref_te, fuente = referencia_municipal(tr, te)
                residuo = tr.real.to_numpy(dtype=float) - referencia_sin_la_fila(tr)
                internas = particiones_internas(tr)
                base = dict(ID_POLIGONO=te.ID_POLIGONO.to_numpy(), repeticion=rep, particion=k, escenario=esc,
                            real=te.real.to_numpy(dtype=float), referencia=ref_te, fuente=fuente)
                preds.append(pd.DataFrame({**base, "procedimiento": "referencia", "config": 0,
                                           "candidato": REFERENCIA_T08, "opcion": "referencia",
                                           "alfa": np.nan, "prediccion": ref_te}))
                for proc in procedimientos:
                    for n, cfg in configs.items():
                        op = elegir_opcion(internas, cfg, proc)
                        corr, coef = ajustar_y_predecir(tr, te, residuo, cfg, op)
                        preds.append(pd.DataFrame({**base, "procedimiento": proc, "config": n,
                                                   "candidato": f"{proc}_config{n}_{cfg['nombre']}",
                                                   "opcion": etiqueta_opcion(op),
                                                   "alfa": np.nan if op is REFERENCIA_SOLA else float(op),
                                                   "prediccion": ref_te + corr}))
                        coefs.append(pd.DataFrame({"procedimiento": proc, "config": n, "escenario": esc,
                                                   "repeticion": rep, "particion": k,
                                                   "opcion": etiqueta_opcion(op), "variable": cfg["cols"],
                                                   "coef": coef}))
            if verbose:
                print(f"  escenario {esc}, repetición {rep} lista", flush=True)
    oof = pd.concat(preds, ignore_index=True)
    oof["version"] = VERSION
    columnas = ["ID_POLIGONO", "repeticion", "particion", "escenario", "real", "prediccion", "candidato",
                "version", "fuente", "procedimiento", "config", "opcion", "alfa", "referencia"]
    return oof[columnas], pd.concat(coefs, ignore_index=True)


def comprobar_referencia(d, verbose=True):
    """La referencia de T10 debe reproducir las 1,380 predicciones de T08 con las mismas fuentes."""
    filas = []
    for esc, col in ESCENARIOS.items():
        for rep, dr in d.groupby("repeticion", sort=True):
            for k in sorted(dr[col].unique()):
                tr, te = dr[dr[col] != k], dr[dr[col] == k]
                ref, fuente = referencia_municipal(tr, te)
                filas.append(pd.DataFrame({"ID_POLIGONO": te.ID_POLIGONO.to_numpy(), "repeticion": rep,
                                           "escenario": esc, "ref": ref, "fuente_t10": fuente}))
    mia = pd.concat(filas, ignore_index=True)
    t08 = pd.read_csv(OOF_T08)
    comp = mia.merge(t08, on=["ID_POLIGONO", "repeticion", "escenario"], validate="one_to_one")
    r = dict(filas_comparadas=int(len(comp)), diferencia_maxima=float((comp.ref - comp.prediccion).abs().max()),
             misma_fuente=bool((comp.fuente_t10 == comp.fuente).all()),
             respaldo_por_escenario={e: int(n) for e, n in mia[mia.fuente_t10 != "municipio"].groupby("escenario").size().items()})
    if verbose:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    if not (r["filas_comparadas"] == 1380 and r["diferencia_maxima"] < 1e-9 and r["misma_fuente"]):
        raise ValueError(f"La referencia de T10 no reproduce T08: {r}")
    return r


# ---------------------------------------------------------------- métricas y comparación (T03 §4, como T08)
def metricas(y, p):
    e = p - y
    ss = ((y - y.mean()) ** 2).sum()
    return dict(MAE=np.abs(e).mean(), RMSE=np.sqrt((e ** 2).mean()), sesgo=e.mean(), R2=1 - (e ** 2).sum() / ss)


def subconjuntos(x):
    return [("todas", x.fuente.notna()), ("sin_respaldo", x.fuente == "municipio")]


def resumir(oof):
    filas = []
    for sub, mask in subconjuntos(oof):
        for (esc, proc, cfg, rep), g in oof[mask].groupby(["escenario", "procedimiento", "config", "repeticion"]):
            filas.append(dict(subconjunto=sub, escenario=esc, procedimiento=proc, config=cfg, repeticion=rep,
                              n=len(g), **metricas(g.real.to_numpy(), g.prediccion.to_numpy())))
    por_rep = pd.DataFrame(filas)
    return (por_rep.groupby(["subconjunto", "escenario", "procedimiento", "config"])
            .agg(n=("n", "mean"), MAE=("MAE", "mean"), RMSE=("RMSE", "mean"), sesgo=("sesgo", "mean"),
                 R2=("R2", "mean"), MAE_sd_rep=("MAE", "std")).reset_index())


def comparar(x, cand, base, celda):
    """ΔMAE emparejado de `cand` frente a `base` (claves (procedimiento, config)), igual que T08:
    promedio por parcela de sus repeticiones; IC95 por celdas CHIRPS y por parcelas."""
    filas = []
    x = x.assign(ae=(x.prediccion - x.real).abs(), se=(x.prediccion - x.real) ** 2)
    b_todas = x[(x.procedimiento == base[0]) & (x.config == base[1])].set_index(["ID_POLIGONO", "repeticion"])
    c_todas = x[(x.procedimiento == cand[0]) & (x.config == cand[1])].set_index(["ID_POLIGONO", "repeticion"])
    for sub, mask in subconjuntos(b_todas):
        b = b_todas[mask]
        c = c_todas.loc[b.index]
        d_rep = (c.ae - b.ae).groupby(level="repeticion").mean()
        d_parc = (c.ae - b.ae).groupby(level="ID_POLIGONO").mean()
        rng = np.random.RandomState(SEMILLA_BOOT)
        v = d_parc.to_numpy()
        bs_p = v[rng.randint(0, len(v), (N_BOOT, len(v)))].mean(axis=1)
        g = pd.DataFrame({"d": d_parc, "celda": celda.reindex(d_parc.index).to_numpy()}).groupby("celda").d
        suma, n = g.sum().to_numpy(), g.size().to_numpy()
        rng = np.random.RandomState(SEMILLA_BOOT)
        k = rng.randint(0, len(suma), (N_BOOT, len(suma)))
        bs_c = suma[k].sum(axis=1) / n[k].sum(axis=1)
        lo_p, hi_p = np.percentile(bs_p, [2.5, 97.5])
        lo_c, hi_c = np.percentile(bs_c, [2.5, 97.5])
        drmse = (np.sqrt(c.se.groupby(level="repeticion").mean()) - np.sqrt(b.se.groupby(level="repeticion").mean())).mean()
        signo = int((d_rep < 0).sum())
        filas.append(dict(subconjunto=sub, n_predicciones=len(b), n_celdas=len(suma), dMAE=d_parc.mean(),
                          IC95_celdas_inf=lo_c, IC95_celdas_sup=hi_c, IC95_parcelas_inf=lo_p, IC95_parcelas_sup=hi_p,
                          reps_que_mejoran=signo, dRMSE=drmse,
                          parcelas_mejoran=int((d_parc < 0).sum()), parcelas_empeoran=int((d_parc > 0).sum()),
                          cumple_regla_T03=bool(d_parc.mean() <= -0.01 and hi_c < 0 and signo >= 4 and drmse <= 0.01)))
    return filas


def comparaciones(oof, celda):
    filas = []
    for esc, x in oof.groupby("escenario"):
        for proc, cfg_proc in PROCEDIMIENTOS.items():
            for n in CONFIGS:
                for f in comparar(x, (proc, n), ("referencia", 0), celda):
                    filas.append(dict(escenario=esc, tipo="frente_a_referencia", procedimiento=proc, candidato=n,
                                      frente_a="referencia", elegible=cfg_proc["decide"], **f))
            for cand, base, tipo in DESCRIPTIVAS:
                for f in comparar(x, (proc, cand), (proc, base), celda):
                    filas.append(dict(escenario=esc, tipo=f"descriptiva: {tipo}", procedimiento=proc, candidato=cand,
                                      frente_a=f"config {base}", elegible=False, **f))
        for n in CONFIGS:
            for f in comparar(x, ("t10", n), ("puente_t11", n), celda):
                filas.append(dict(escenario=esc, tipo="descriptiva: principal frente a puente", procedimiento="t10",
                                  candidato=n, frente_a="puente_t11", elegible=False, **f))
    return marcar_candidatas(pd.DataFrame(filas))


def marcar_candidatas(comp):
    """Candidata a promover (antes del revuelto): procedimiento principal frente a la referencia,
    cumple la regla de T03 en `sin_respaldo` (D019) y en el escenario A, que es el principal
    (T03 §3). B es sensibilidad: cumplir sólo en B no promueve."""
    comp = comp.copy()
    comp["candidata_a_promover"] = (comp.elegible & comp.cumple_regla_T03
                                    & (comp.subconjunto == "sin_respaldo") & (comp.escenario == "A"))
    return comp


def decidir(comp, revuelto):
    """Decisión final (D_T10_001 §7–8): se promueve sólo la candidata que además supera el control
    de revuelto. Cada fila guarda el motivo de la decisión."""
    comp = comp.copy()
    sostiene = {(r.escenario, int(r.config)): bool(r.se_sostiene) for r in revuelto.itertuples()}
    supera, promueve, motivo = [], [], []
    for r in comp.itertuples():
        s = sostiene.get((r.escenario, int(r.candidato))) if r.candidata_a_promover else None
        supera.append(s)
        promueve.append(bool(r.candidata_a_promover and s is True))
        if not r.elegible:
            m = "no elegible: comparación descriptiva o procedimiento puente"
        elif r.subconjunto != "sin_respaldo":
            m = "informativo: la regla se aplica en sin_respaldo (D019)"
        elif not r.cumple_regla_T03:
            m = "no cumple la regla de T03"
        elif r.escenario != "A":
            m = "cumple sólo en B: sensibilidad, no promueve (T03 §3)"
        elif s is None:
            m = "candidata sin control de revuelto: no promueve"
        elif s:
            m = "cumple la regla en A y supera el control de revuelto"
        else:
            m = "cumple la regla en A pero no supera el control de revuelto"
        motivo.append(m)
    comp["supera_revuelto"] = pd.array(supera, dtype="boolean")
    comp["promueve"] = promueve
    comp["motivo"] = motivo
    return comp


# ---------------------------------------------------------------- desgloses y sensibilidad
def atributos_parcela(tabla):
    """Banderas por parcela para los desgloses (T03 §4 bis y tamaño/cobertura de T10)."""
    cal = pd.read_csv(CALIDAD_PARCELAS, dtype={"escalon_etiqueta_municipio": str})
    rel = pd.read_csv(CALIDAD_RELIEVE)
    a = tabla[["id_parcela", "area_ha_origen"]].merge(cal, on="id_parcela", validate="one_to_one")
    a = a.merge(rel[["id_parcela", "avisos"]], on="id_parcela", validate="one_to_one")
    av = a.avisos.fillna("")
    a["contorno"] = np.where(a.contorno_categoria == "A", "A", "B o C")
    a["escalon"] = a.escalon_etiqueta_municipio.fillna("sin escalón")
    a["tramo_area"] = pd.cut(a.area_ha_origen, [0, 2, 5, np.inf], right=False,
                             labels=["menos de 2 ha", "2 a 5 ha", "mas de 5 ha"]).astype(str)
    a["menor_a_una_celda"] = np.where(av.str.contains("parcela_menor_a_una_celda"), "si", "no")
    a["cobertura_parcial_relieve"] = np.where(av.str.contains("cobertura_parcial"), "si", "no")
    a["pocas_celdas_validas"] = np.where(av.str.contains("pocas_celdas_validas"), "si", "no")
    return a.set_index("id_parcela")


EJES = {"municipio": "municipio", "grupo_registro": "grupo_registro", "contorno": "contorno",
        "angosta_o_muy_pequena": "contorno_angosta_o_muy_pequena", "escalon_etiqueta": "escalon",
        "vecina_etiquetada_menos_20m": "vecina_etiquetada_menos_20m", "tramo_area": "tramo_area",
        "menor_a_una_celda": "menor_a_una_celda", "cobertura_parcial_relieve": "cobertura_parcial_relieve",
        "pocas_celdas_validas": "pocas_celdas_validas"}


def desgloses(oof, part, atrib):
    p = part.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO")
    d = oof.join(atrib, on="ID_POLIGONO")
    d["municipio"] = d.ID_POLIGONO.map(p.municipio)
    d["grupo_registro"] = d.ID_POLIGONO.map(p.grupo_registro)
    d["e"] = d.prediccion - d.real
    paso = pd.to_numeric(d.escalon_etiqueta_municipio, errors="coerce")
    d["bajo_resolucion"] = np.where(paso.notna(), d.e.abs() < paso / 2, np.nan)
    # T03 §4: métricas por repetición y después el promedio de las repeticiones (no se juntan antes).
    filas = []
    for sub, mask in subconjuntos(d):
        for nombre, col in EJES.items():
            for (esc, proc, cfg, cat), g in d[mask].groupby(["escenario", "procedimiento", "config", col]):
                por_rep = pd.DataFrame([dict(MAE=x.e.abs().mean(), RMSE=np.sqrt((x.e ** 2).mean()), sesgo=x.e.mean(),
                                             prop=x.bajo_resolucion.mean())
                                        for _, x in g.groupby("repeticion")])
                filas.append(dict(subconjunto=sub, escenario=esc, procedimiento=proc, config=cfg, desglose=nombre,
                                  categoria=cat, n_parcelas=g.ID_POLIGONO.nunique(), n_predicciones=len(g),
                                  n_repeticiones=len(por_rep), MAE=por_rep.MAE.mean(), RMSE=por_rep.RMSE.mean(),
                                  sesgo=por_rep.sesgo.mean(), prop_error_menor_medio_escalon=por_rep.prop.mean(),
                                  MAE_sd_rep=por_rep.MAE.std()))
    r = pd.DataFrame(filas)
    r["poco_informativo"] = r.n_parcelas < 5
    return r


def sensibilidad_sin_alerta(oof, atrib):
    """T03 §4 bis: métricas sin las 24 etiquetadas con alerta de contorno; ¿se mantiene el orden?"""
    alerta = atrib.alerta_contorno_t03_bis == "si"
    sin = oof[~oof.ID_POLIGONO.map(alerta).astype(bool)]
    con, sin_ = resumir(oof), resumir(sin)
    m = con.merge(sin_, on=["subconjunto", "escenario", "procedimiento", "config"], suffixes=("", "_sin24"))
    for suf in ["", "_sin24"]:
        ref = m[m.config == 0].set_index(["subconjunto", "escenario"])
        for met in ["MAE", "RMSE"]:
            idx = pd.MultiIndex.from_frame(m[["subconjunto", "escenario"]])
            m["d" + met + suf] = m[met + suf].to_numpy() - ref[met + suf].reindex(idx).to_numpy()
        m["orden_MAE" + suf] = m.groupby(["subconjunto", "escenario"])["MAE" + suf].rank(method="min")
    m["parcelas_sin_alerta"] = int(sin.ID_POLIGONO.nunique())
    return m


def frecuencia_opciones(oof):
    x = oof[oof.config > 0].drop_duplicates(["procedimiento", "config", "escenario", "repeticion", "particion"])
    return (x.groupby(["procedimiento", "config", "escenario", "opcion"]).size()
            .rename("ajustes").reset_index())


# ---------------------------------------------------------------- control de revuelto
def revolver_dentro_de_municipio(d, cols, rng):
    """Revuelve juntas las columnas `cols` entre parcelas etiquetadas del mismo municipio
    (una permutación por parcela, aplicada igual en las 5 repeticiones)."""
    p = d.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO")
    nuevo = p[cols].copy()
    for _, ids in p.groupby("municipio").groups.items():
        ids = list(ids)
        nuevo.loc[ids, cols] = p.loc[rng.permutation(ids), cols].to_numpy()
    out = d.copy()
    for c in cols:
        out[c] = out.ID_POLIGONO.map(nuevo[c])
    return out


def control_revuelto(d, comp, celda):
    """Sólo para las candidatas a promover del principal (escenario A, sin_respaldo; D_T10_001 §8)."""
    filas = []
    for _, r in comp[comp.candidata_a_promover].iterrows():
        cfg = {r.candidato: CONFIGS[r.candidato]}
        esc = {r.escenario: ESCENARIOS[r.escenario]}
        rng = np.random.RandomState(SEMILLA_REVUELTO)
        dmaes = []
        for i in range(N_REVUELTO):
            dp = revolver_dentro_de_municipio(d, CONFIGS[r.candidato]["cols"], rng)
            o, _ = evaluar(dp, configs=cfg, procedimientos={"t10": PROCEDIMIENTOS["t10"]}, escenarios=esc, verbose=False)
            f = [x for x in comparar(o, ("t10", r.candidato), ("referencia", 0), celda) if x["subconjunto"] == "sin_respaldo"][0]
            dmaes.append(f["dMAE"])
        frac = float(np.mean(np.asarray(dmaes) <= r.dMAE))
        filas.append(dict(escenario=r.escenario, config=r.candidato, dMAE_observado=r.dMAE, revueltos=N_REVUELTO,
                          fraccion_igual_o_mejor=frac, dMAE_revueltos=";".join(f"{v:.6f}" for v in dmaes),
                          se_sostiene=frac <= UMBRAL_REVUELTO))
    return pd.DataFrame(filas, columns=["escenario", "config", "dMAE_observado", "revueltos",
                                        "fraccion_igual_o_mejor", "dMAE_revueltos", "se_sostiene"])


# ---------------------------------------------------------------- predicciones para las 59
def predicciones_59(tabla):
    """Cada procedimiento × configuración ajustado con las 138 (selección interna incluida) y aplicado
    a las 59. Sólo para T16 y la app: las 59 no tienen etiqueta y no intervienen en ninguna elección."""
    t = tabla.rename(columns={"rendimiento_t_ha": "real", "cultivo_origen": "grupo_registro"})
    tr = t[t.real.notna()].sort_values("id_parcela").reset_index(drop=True)
    te = t[t.real.isna()].sort_values("id_parcela").reset_index(drop=True)
    assert len(tr) == 138 and len(te) == 59
    ref_te, fuente = referencia_municipal(tr, te)
    t08 = pd.read_csv(P59_T08)
    t08 = t08[t08.candidato == REFERENCIA_T08].set_index("ID_POLIGONO").prediccion
    dif = np.abs(ref_te - t08.reindex(te.id_parcela).to_numpy()).max()
    if not dif < 1e-9:
        raise ValueError(f"La referencia de las 59 no reproduce T08 (diferencia {dif})")
    residuo = tr.real.to_numpy(dtype=float) - referencia_sin_la_fila(tr)
    internas = particiones_internas(tr)
    filas = [pd.DataFrame(dict(ID_POLIGONO=te.id_parcela, procedimiento="referencia", config=0,
                               candidato=REFERENCIA_T08, opcion="referencia", prediccion=ref_te, fuente=fuente))]
    for proc in PROCEDIMIENTOS:
        for n, cfg in CONFIGS.items():
            op = elegir_opcion(internas, cfg, proc)
            corr, _ = ajustar_y_predecir(tr, te, residuo, cfg, op)
            filas.append(pd.DataFrame(dict(ID_POLIGONO=te.id_parcela, procedimiento=proc, config=n,
                                           candidato=f"{proc}_config{n}_{cfg['nombre']}",
                                           opcion=etiqueta_opcion(op), prediccion=ref_te + corr, fuente=fuente)))
    out = pd.concat(filas, ignore_index=True)
    out["version"] = VERSION
    if not np.isfinite(out.prediccion).all():
        raise ValueError("Predicción no finita para las 59")
    return out


# ---------------------------------------------------------------- diagnóstico sin rendimientos
def diagnostico_atributos(tabla):
    """Sólo usa municipio y las variables de entrada: nunca el rendimiento."""
    cols = [ELEV, PEND, AREA]
    etiq = tabla.rendimiento_t_ha.notna()
    filas = []
    for pob, x in [("138_etiquetadas", tabla[etiq]), ("197_parcelas", tabla)]:
        for c in cols:
            v = x[[c, "municipio"]].dropna()
            media_mun = v.groupby("municipio")[c].transform("mean")
            r2 = 1 - ((v[c] - media_mun) ** 2).sum() / ((v[c] - v[c].mean()) ** 2).sum()
            filas.append(dict(diagnostico="parte_explicada_por_municipio", poblacion=pob, variable=c, otra="",
                              n=len(v), valor=r2))
        cor = x[cols].corr()
        for i, a in enumerate(cols):
            for b in cols[i + 1:]:
                n = int(x[[a, b]].dropna().shape[0])
                filas.append(dict(diagnostico="correlacion_pearson_entre_variables", poblacion=pob, variable=a,
                                  otra=b, n=n, valor=cor.loc[a, b]))
    res = tabla[~etiq]
    for c in cols:
        lo, hi = tabla.loc[etiq, c].min(), tabla.loc[etiq, c].max()
        fuera = res[c].notna() & ((res[c] < lo) | (res[c] > hi))
        filas.append(dict(diagnostico="reservadas_fuera_del_rango_etiquetado", poblacion="59_reservadas", variable=c,
                          otra=";".join(res.loc[fuera, "id_parcela"]), n=int(res[c].notna().sum()), valor=int(fuera.sum())))
        filas.append(dict(diagnostico="faltantes", poblacion="138_etiquetadas", variable=c, otra="",
                          n=int(etiq.sum()), valor=int(tabla.loc[etiq, c].isna().sum())))
        filas.append(dict(diagnostico="faltantes", poblacion="59_reservadas", variable=c, otra="",
                          n=int((~etiq).sum()), valor=int(res[c].isna().sum())))
    return pd.DataFrame(filas)


# ---------------------------------------------------------------- escritura
def escribir(salida, nombre, df):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    ruta = salida / nombre
    if ruta.exists():
        raise FileExistsError(f"{ruta} ya existe; usar una carpeta nueva para no sobrescribir evidencia")
    ruta.write_bytes(df.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    return ruta


def escribir_manifiesto(salida, comando, extra):
    salida = Path(salida)
    ruta = salida / "manifest.json"
    if ruta.exists():
        raise FileExistsError(f"{ruta} ya existe")
    archivos = {p.name: sha256(p) for p in sorted(salida.iterdir()) if p.is_file()}
    m = dict(tarea="T10", version=VERSION, decision="D_T10_001", comando=comando,
             entradas_sha256={str(p.relative_to(RAIZ).as_posix()): sha256(p) for p in ENTRADAS},
             codigo_sha256={"scripts/t10_relieve_area.py": sha256(Path(__file__))},
             archivos_sha256=archivos,
             entorno=dict(python=platform.python_version(), sistema=platform.system(), arquitectura=platform.machine(),
                          numpy=np.__version__, pandas=pd.__version__, scikit_learn=sklearn.__version__),
             **extra)
    ruta.write_bytes((json.dumps(m, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


# ---------------------------------------------------------------- principal
def main(argv=None):
    ap = argparse.ArgumentParser(description="T10: relieve y área sobre la referencia territorial (docs/T10_relieve_area.md)")
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--comprobar-referencia", action="store_true", help="sólo verifica que la referencia reproduce T08")
    modo.add_argument("--diagnostico", action="store_true", help="diagnóstico de atributos sin rendimientos")
    modo.add_argument("--evaluar", action="store_true", help="evaluación completa (principal y puente)")
    ap.add_argument("--salida", type=Path)
    a = ap.parse_args(argv)
    pd.set_option("display.width", 200)

    tabla, part, d = leer_entradas()
    if a.comprobar_referencia:
        comprobar_referencia(d)
        return
    if a.salida is None:
        ap.error("--salida es obligatoria en este modo")
    if a.diagnostico:
        diag = diagnostico_atributos(tabla)
        print(diag.round(4).to_string(index=False))
        escribir(a.salida, "diagnostico_atributos_t10.csv", diag)
        return

    comprobar_referencia(d)
    t0 = time.time()
    print("\nevaluando referencia + 6 configuraciones × 2 procedimientos (A y B)...")
    oof, coefs = evaluar(d)
    celda = d.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps
    comp = comparaciones(oof, celda)
    atrib = atributos_parcela(tabla)
    res = resumir(oof)
    des = desgloses(oof, part, atrib)
    sens = sensibilidad_sin_alerta(oof, atrib)
    freq = frecuencia_opciones(oof)
    rev = control_revuelto(d, comp, celda)
    comp = decidir(comp, rev)
    p59 = predicciones_59(tabla)
    for nombre, df in [("predicciones_oof_t10.csv", oof), ("coeficientes_t10.csv", coefs),
                       ("metricas_t10.csv", res), ("comparacion_emparejada_t10.csv", comp),
                       ("desglose_error_t10.csv", des), ("sensibilidad_sin_alerta_t10.csv", sens),
                       ("frecuencia_opciones_t10.csv", freq), ("control_revuelto_t10.csv", rev),
                       ("predicciones_59_t10.csv", p59)]:
        escribir(a.salida, nombre, df)
    escribir_manifiesto(a.salida, "python -m scripts.t10_relieve_area --evaluar --salida " + Path(a.salida).as_posix(),
                        dict(promueve=bool(comp.promueve.any()), segundos=round(time.time() - t0)))
    sel = (comp.tipo == "frente_a_referencia") & (comp.subconjunto == "sin_respaldo")
    print(comp.loc[sel, ["escenario", "procedimiento", "candidato", "dMAE", "IC95_celdas_sup", "reps_que_mejoran",
                         "dRMSE", "cumple_regla_T03", "promueve", "motivo"]].round(4).to_string(index=False))
    print("\n¿alguna configuración del principal se promueve?", bool(comp.promueve.any()))


if __name__ == "__main__":
    sys.exit(main())
