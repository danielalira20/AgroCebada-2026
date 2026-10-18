"""Avisos que acompañan a cada estimación."""
import pandas as pd


def avisos_de(pred, sop):
    out = {}
    for pid, r in pred.iterrows():
        a = []
        if r.n_municipio == 1:
            a.append("se basa en una sola parcela con cosecha de su municipio")
        if r.fuente != "municipio":
            a.append("su municipio no tiene parcelas con cosecha: se usó el respaldo")
        if sop is not None and pid in sop.index and sop.loc[pid, "etiquetadas_en_misma_celda"] == 0:
            a.append("está en una zona de lluvia sin parcelas con cosecha registrada")
        out[pid] = "; ".join(a)
    return pd.Series(out)
