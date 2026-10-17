"""T13 · control «solo intercepto» (D026, revisión de Jass al PR #20).

El Ridge de T11/T13 ajusta intercepto (fit_intercept=True). Con α muy grande los coeficientes van a
cero pero el intercepto queda: la media de los residuos de entrenamiento (sin la propia fila). Esa
media no es cero porque las parcelas de municipios con una sola etiqueta en el entrenamiento usan el
respaldo de grupo. Este control mide cuánto de la diferencia frente a la referencia es ese desfase,
sin ningún índice. Es descriptivo: no cambia D024 ni D025.

Uso:
    python scripts/t13_control_intercepto.py
"""
import importlib.util
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "registro" / "t13"


def cargar_t11():
    spec = importlib.util.spec_from_file_location("t11_para_control", RAIZ / "scripts" / "t11_aporte_satelital.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    if m.VERSION != "T11-v2.1":
        raise ValueError(f"El control se diseñó con T11-v2.1 y el código es {m.VERSION}")
    m.CANDIDATOS = {0: "media_mun__resp_grupo", 1: "t13_control_solo_intercepto"}
    return m


def predicciones(t11, d):
    """Referencia y referencia + media del residuo de entrenamiento, en A y B × 5 × 5."""
    filas = []
    for esc, col in t11.ESCENARIOS.items():
        for rep, dr in d.groupby("repeticion"):
            for k in sorted(dr[col].unique()):
                tr, te = t11.separar(dr, col, k)
                ref, fuente = t11.referencia_municipal(tr, te)
                intercepto = (tr.real.values - t11.referencia_sin_la_fila(tr)).mean()
                base = dict(ID_POLIGONO=te.ID_POLIGONO.values, repeticion=rep, particion=k, escenario=esc,
                            real=te.real.values, referencia=ref, fuente=fuente)
                filas.append(pd.DataFrame({**base, "config": 0, "intercepto": 0.0, "prediccion": ref}))
                filas.append(pd.DataFrame({**base, "config": 1, "intercepto": intercepto, "prediccion": ref + intercepto}))
    return pd.concat(filas, ignore_index=True)


def main():
    t11 = cargar_t11()
    d = t11.preparar(pd.read_csv(t11.TABLA), pd.read_csv(t11.PARTICIONES))
    t11.comprobar_referencia(d)
    oof = predicciones(t11, d)
    celda = d.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").celda_chirps
    filas = [dict(escenario=esc, **t11.comparar(o, celda, 1, 0, sub))
             for esc, o in oof.groupby("escenario") for sub in ["todas", "sin_respaldo"]]
    comp = pd.DataFrame(filas)
    rango = oof[oof.config == 1].drop_duplicates(["escenario", "repeticion", "particion"]).groupby("escenario").intercepto
    comp = comp.merge(rango.agg(intercepto_min="min", intercepto_max="max").reset_index(), on="escenario")
    SALIDA.mkdir(parents=True, exist_ok=True)
    comp.to_csv(SALIDA / "control_solo_intercepto_t13.csv", index=False)
    cols = ["escenario", "subconjunto", "dMAE", "IC95_celdas_MAE_inf", "IC95_celdas_MAE_sup", "reps_mejoran_MAE",
            "dRMSE", "intercepto_min", "intercepto_max"]
    pd.set_option("display.width", 200)
    print(comp[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
