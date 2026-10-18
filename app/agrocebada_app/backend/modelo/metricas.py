"""Métricas de error y validación rápida dejando una parcela fuera."""
import numpy as np
import pandas as pd

from agrocebada_app.backend.modelo.estimador import estadistico


def metricas(o):
    """MAE, RMSE, sesgo y R² promediados por repetición (igual que metricas_referencias.csv de T08)."""
    reps = []
    for _, g in o.groupby("repeticion"):
        reps.append(dict(MAE=g.ae.mean(), RMSE=np.sqrt((g.e ** 2).mean()), sesgo=g.e.mean(),
                         R2=1 - (g.e ** 2).sum() / ((g.real - g.real.mean()) ** 2).sum()))
    return pd.DataFrame(reps).mean()


def validacion_dejando_uno(d, modelo):
    """Validación rápida para datos subidos: cada parcela con cosecha se estima sin ella misma (mismo respaldo)."""
    f = estadistico(modelo)
    tr = d[d.CONJUNTO == "ENTRENAMIENTO"]
    y = tr.real.to_numpy(float)
    filas = []
    for i, (pid, r) in enumerate(tr.iterrows()):
        resto = tr.drop(index=pid)
        m = resto.real[resto.municipio == r.municipio]
        g = resto.real[resto.grupo_registro == r.grupo_registro]
        p, fuente = ((f(m), "municipio") if len(m) else (f(g), "grupo") if len(g) else (f(resto.real), "global"))
        filas.append((pid, r.municipio, y[i], p, fuente))
    o = pd.DataFrame(filas, columns=["ID_POLIGONO", "municipio", "real", "prediccion", "fuente"])
    return o.assign(ae=(o.prediccion - o.real).abs(), e=o.prediccion - o.real, repeticion=1)
