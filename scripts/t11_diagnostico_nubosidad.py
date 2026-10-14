"""T11 · diagnóstico sin etiquetas (O2): ¿la calidad de observación de Planet refleja lluvia?

En parcelas de temporal, más nubosidad o menos capturas limpias podrían deberse a más lluvia.
Este diagnóstico NO usa el rendimiento: sólo relaciona las columnas de calidad de Planet
(abr_oct) con la lluvia acumulada (abr_oct) de T07, en las 197 parcelas, en las 138 y en las 59,
en general y dentro de cada municipio (quitando la media municipal).

Uso:
    python scripts/t11_diagnostico_nubosidad.py
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TABLA = RAIZ / "registro" / "t07" / "tabla_comun.csv"
SALIDA = RAIZ / "registro" / "t11" / "diagnostico_nubosidad_lluvia.csv"
CALIDAD = ["pl_nubosidad_media_abr_oct", "pl_capturas_abr_oct", "pl_hueco_max_abr_oct"]
LLUVIA = "prec_acumulada_mm_abr_oct"


def correlaciones(t, poblacion):
    filas = []
    dentro = t[CALIDAD + [LLUVIA]] - t.groupby("municipio")[CALIDAD + [LLUVIA]].transform("mean")
    for col in CALIDAD:
        for alcance, datos in [("general", t), ("dentro_de_municipio", dentro)]:
            par = datos[[col, LLUVIA]].dropna()
            filas.append(dict(poblacion=poblacion, alcance=alcance, variable=col, n=len(par),
                              pearson=par[col].corr(par[LLUVIA]),
                              spearman=par[col].corr(par[LLUVIA], method="spearman")))
    return filas


def main():
    t = pd.read_csv(TABLA)
    filas = correlaciones(t, "197_parcelas")
    filas += correlaciones(t[t.conjunto_origen == "ENTRENAMIENTO"], "138_etiquetadas")
    filas += correlaciones(t[t.conjunto_origen == "PREDICCION"], "59_reservadas")
    r = pd.DataFrame(filas)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    r.to_csv(SALIDA, index=False)
    pd.set_option("display.width", 160)
    print(r.round(3).to_string(index=False))
    print(f"\nescrito en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()