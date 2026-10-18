"""Nota en lenguaje sencillo que explica de dónde sale la cifra de una parcela."""
import pandas as pd


def nota_de(d, pred, cob_mun, pid):
    """`cob_mun`: por municipio, fracción de parcelas conocidas que quedaron dentro del error típico."""
    r = d.loc[pid]
    if r.CONJUNTO != "PREDICCION":
        return ("Esta parcela ya tiene su cosecha registrada. Sirve para comprobar el método: se estimó como si no se "
                "conociera y se comparó.")
    p, n = pred.loc[pid], int(pred.loc[pid, "n_municipio"])
    origen = (f"la única parcela de {r.municipio} con cosecha registrada" if n == 1 else
              f"las {n} parcelas de {r.municipio} con cosecha registrada")
    nota = f"Es el rendimiento típico de {origen} en 2025."
    if pd.notna(p.error_tipico) and r.municipio in cob_mun.index:
        nota += (f" Al probarlo con parcelas conocidas, {cob_mun[r.municipio] * 10:.0f} de cada 10 quedaron dentro "
                 f"de ± {p.error_tipico:.2f} t/ha.")
    return nota
