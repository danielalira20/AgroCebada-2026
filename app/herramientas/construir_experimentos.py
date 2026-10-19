"""Construye datos_estaticos/experimentos.csv para la pestaña «Evidencia» (M13).

Lee los resultados registrados en registro/ (T10, T12, T13, T14, T15, T16) y
escribe una tabla plana con una fila por prueba: error absoluto medio (MAE),
cambio frente a la referencia, intervalo, repeticiones que mejoran y si pasó la
regla de promoción de T03 §4. Todo en A / sin_respaldo (135 parcelas).

Las pruebas H1, H2 y MH2 NO están en registro/: viven en docs/t16_procedimiento_final.md §8
(exploratorias, posteriores a los resultados). Se anotan como «complementaria».

Uso (desde app/):  python herramientas/construir_experimentos.py
"""
import ast
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
REG = RAIZ / "registro"
SALIDA = Path(__file__).resolve().parents[1] / "datos_estaticos" / "experimentos.csv"

ESC, SUB = "A", "sin_respaldo"
UMBRAL = -0.01
MAE_REF = 0.320490  # media_mun__resp_grupo en A/sin_respaldo (T13, T15, T16, T12)
COLS = ["pregunta", "tarea", "prueba", "estado", "mae", "mae_referencia", "delta_mae",
        "ic_inf", "ic_sup", "reps_mejoran", "pasa_regla", "motivo", "registro", "fuente", "nota"]


def _motivo(delta, inf, sup, reps, pasa):
    """Por qué no pasó la regla de T03 §4, en palabras (nunca «no sirve»)."""
    if pasa:
        return "pasó la regla"
    if pd.isna(delta):
        return ""
    if delta > 0:
        partes = [f"el error sube {delta:+.4f}"]
    else:
        partes = []
        if delta > UMBRAL:
            partes.append("no llega a −0.01")
    if pd.notna(sup) and inf <= 0 <= sup:
        partes.append("el intervalo cruza cero")
    if pd.notna(reps) and reps < 4:
        partes.append(f"mejora en {int(reps)} de 5 repeticiones")
    return "no pasó la regla: " + "; ".join(partes) if partes else "no pasó la regla"


def _fila(pregunta, tarea, prueba, mae, delta, inf, sup, reps, pasa, registro, fuente,
          estado="registrada", nota="", ref=MAE_REF):
    return dict(pregunta=pregunta, tarea=tarea, prueba=prueba, estado=estado, mae=mae,
                mae_referencia=ref, delta_mae=delta, ic_inf=inf, ic_sup=sup, reps_mejoran=reps,
                pasa_regla=pasa, motivo=_motivo(delta, inf, sup, reps, pasa) if estado == "registrada" else "",
                registro=registro, fuente=fuente, nota=nota)


def _a_sin(df):
    return df[(df.escenario == ESC) & (df.subconjunto == SUB)]


def t13():
    c = _a_sin(pd.read_csv(REG / "t13/comparacion_emparejada_t13.csv"))
    c = c[c.tipo == "promocion"].set_index("config")
    m = _a_sin(pd.read_csv(REG / "t13/metricas_t13.csv")).set_index("config")
    nombres = {1: "NDVI Planet", 2: "LAI2 Planet", 3: "NDVI Sentinel-2", 4: "NDWI Sentinel-2",
               5: "VI6T Landsat", 6: "Los cinco índices juntos", 7: "Los cinco, sin NDVI",
               8: "Los cinco, sin VI6T"}
    ref = float(m.loc[0, "MAE"])
    out = []
    for k, nom in nombres.items():
        r = c.loc[k]
        out.append(_fila(1, "T13", nom, float(m.loc[k, "MAE"]), r.dMAE, r.IC95_celdas_MAE_inf,
                         r.IC95_celdas_MAE_sup, r.reps_mejoran_MAE, bool(r.cumple_regla_MAE),
                         f"E_T13_{k:03d}", "registro/t13/comparacion_emparejada_t13.csv", ref=ref))
    return out


def t14():
    c = _a_sin(pd.read_csv(REG / "t14/comparacion_emparejada_t14.csv")).set_index("candidato")
    nombres = {"ref_mas_lluvia": "Lluvia", "ref_mas_tmin": "Temperatura mínima",
               "ref_mas_tmax": "Temperatura máxima", "ref_mas_clima": "Clima conjunto (lluvia + Tmin + Tmax)"}
    out = []
    for cand, nom in nombres.items():
        r = c.loc[cand]
        out.append(_fila(2, "T14", nom, round(MAE_REF + r.dMAE, 4), r.dMAE, r.IC95_celdas_inf,
                         r.IC95_celdas_sup, r.reps_que_mejoran, bool(r.cumple_regla_T03), "D_T14_001",
                         "registro/t14/comparacion_emparejada_t14.csv",
                         nota="MAE = referencia de 135 parcelas + cambio emparejado "
                              "(metricas_t14.csv usa las 138: 0.3192)."))
    return out


def t10():
    c = pd.read_csv(REG / "t10/comparacion_emparejada_t10.csv")
    c = _a_sin(c[(c.procedimiento == "t10") & (c.tipo == "frente_a_referencia")]).set_index("candidato")
    m = _a_sin(pd.read_csv(REG / "t10/metricas_t10.csv"))
    m = m[m.procedimiento == "t10"].set_index("config")
    nombres = {5: "Relieve + área", 6: "Relieve + área, centrados por municipio"}
    out = []
    for k, nom in nombres.items():
        r = c.loc[k]
        out.append(_fila(3, "T10", nom, float(m.loc[k, "MAE"]), r.dMAE, r.IC95_celdas_inf,
                         r.IC95_celdas_sup, r.reps_que_mejoran, bool(r.cumple_regla_T03),
                         f"E_T10_{k:03d}", "registro/t10/comparacion_emparejada_t10.csv"))
    return out


def t12():
    c = _a_sin(pd.read_csv(REG / "t12/comparacion_emparejada_t12.csv"))
    c = c[(c.tipo == "frente_a_referencia") & (c.frente_a == "media_mun__resp_grupo")].set_index("candidato")
    m = _a_sin(pd.read_csv(REG / "t12/metricas_t12.csv"))
    m = m[m.repeticion == "promedio"].set_index("candidato")
    nombres = {"t12_het_GP": ("Relieve + área + Planet, con ajuste por municipio", 1),
               "t12_het_G": ("Relieve + área, con ajuste por municipio", 2),
               "t12_het_P": ("Planet, con ajuste por municipio", 3),
               "t12_gb_GP": ("Relieve + área + Planet, con boosting", 4)}
    out = []
    for cand, (nom, n) in nombres.items():
        r = c.loc[cand]
        out.append(_fila(3, "T12", nom, float(m.loc[cand, "MAE"]), r.dMAE, r.IC95_MAE_inf, r.IC95_MAE_sup,
                         r.repeticiones_mejoran_MAE, bool(r.cumple_regla_T03), f"E_T12_{n:03d}",
                         "registro/t12/comparacion_emparejada_t12.csv"))
    return out


def t15():
    c = _a_sin(pd.read_csv(REG / "t15_resultados/contrastes.csv"))
    c = c[c.tipo_contraste == "promocion"].set_index("candidato")
    m = _a_sin(pd.read_csv(REG / "t15_resultados/metricas_resumen.csv")).set_index("candidato")
    nombres = {"C": "Clima", "G": "Relieve y área", "P": "Planet", "S": "Sentinel-2",
               "CG": "Clima + relieve y área", "CP": "Clima + Planet", "GP": "Relieve y área + Planet",
               "CGP": "Clima + relieve y área + Planet"}
    ref = float(m.loc["media_mun__resp_grupo", "MAE_media_repeticiones"])
    out = []
    for k, nom in nombres.items():
        cand = f"comun_centrado_loo_v3_{k}"
        r = c.loc[cand]
        inf, sup = ast.literal_eval(r.IC95_celdas_MAE)
        out.append(_fila(3, "T15", nom, float(m.loc[cand, "MAE_media_repeticiones"]), r.dMAE, inf, sup,
                         r.repeticiones_mejoran_MAE, bool(r.cumple_regla_T03), "T15_comun_loo_v3_completa",
                         "registro/t15_resultados/contrastes.csv", ref=ref,
                         nota="Decisión D_T15_COMPLETA_001."))
    return out


def t16():
    c = pd.read_csv(REG / "t16_revision_mediana/contrastes.csv")
    r = c[(c.escenario == ESC) & (c.subconjunto == SUB) & (c.sensibilidad == "completa")].iloc[0]
    m = MAE_REF + r.dMAE_por_parcela
    return [_fila(3, "T16", "Mediana del municipio (modelo final)", round(m, 6), r.dMAE_por_parcela,
                  r.IC95_celdas_inf, r.IC95_celdas_sup, r.repeticiones_mejoran, bool(r.cumple_regla),
                  "D_T16_DECISION_001", "registro/t16_revision_mediana/contrastes.csv",
                  nota="Excepción explícita a T03, propuesta pendiente de aprobación (Dani y Migue).")]


def complementarias():
    f = "docs/t16_procedimiento_final.md"
    nota = "Prueba complementaria: definida después de ver los resultados, sin registro formal (§8)."
    datos = [(1, "H1: verdor Sentinel-2, sobre la media", 0.3177, -0.0028),
             (1, "H2: verdor compuesto, sobre la media", 0.3170, -0.0035),
             (3, "MH2: mediana + verdor compuesto", 0.3148, -0.0057)]
    return [_fila(p, "T16", n, mae, d, None, None, None, None, "", f + " §8",
                  estado="complementaria", nota=nota) for p, n, mae, d in datos]


def main():
    filas = t13() + t14() + t10() + t12() + t15() + t16() + complementarias()
    df = pd.DataFrame(filas)[COLS]
    for c in ["mae", "mae_referencia", "delta_mae", "ic_inf", "ic_sup"]:
        df[c] = df[c].astype(float).round(4) + 0.0  # + 0.0 evita «-0.0»
    df["reps_mejoran"] = df["reps_mejoran"].astype("Int64")
    SALIDA.parent.mkdir(exist_ok=True)
    df.to_csv(SALIDA, index=False)
    print(f"{len(df)} filas -> {SALIDA}")
    return df


if __name__ == "__main__":
    sys.exit(0 if main() is not None else 1)
