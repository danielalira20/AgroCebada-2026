"""Datos y procedimiento de T08 para la app, sin Streamlit (lo usan app.py, herramientas/preparar_datos.py y tests/frontend/test_app.py).

FACHADA TEMPORAL de la refactorización: las rutas, la lectura de datos y las constantes viven ahora en
`agrocebada_app/` y aquí se reexportan con los mismos nombres. Quedan en este archivo, hasta la etapa 3, `color_rgb`
y el procedimiento de T08 (`predecir`, `metricas`, ...).

La app lee primero el paquete compacto `datos_app/` (parquet, ~1 MB) que arma `herramientas/preparar_datos.py`. Si no
existe, lee las fuentes originales del repo (dataset del reto, T08, T03 y T04), que es más lento.
"""
import numpy as np
import pandas as pd

from agrocebada_app.backend.datos.elevacion import elevaciones  # noqa: F401
from agrocebada_app.backend.datos.lectura import (  # noqa: F401
    con_centroides, leer_clima, leer_oficial, leer_parcelas, leer_series, leer_soporte, leer_validacion)
from agrocebada_app.backend.datos.paquete import (  # noqa: F401
    clima, hay_datos, oficial, parcelas, series, soporte, usar_paquete, validacion)
from agrocebada_app.backend.rutas.localizador import buscar, buscar_dataset, raiz, rutas  # noqa: F401
from agrocebada_app.config import (  # noqa: F401
    APP as AQUI, CLAVE_DATASET, COLUMNAS_INDICES, MODELOS_CANDIDATOS as MODELOS, PALETA, PAQ, TEMPORADA)


def color_rgb(v):
    """Color de la escala de rendimiento (t/ha) como (r, g, b) 0-255."""
    (a, ca), (b, cb), (c, cc) = PALETA
    x, y, k = (ca, cb, (v - a) / (b - a)) if v <= b else (cb, cc, (v - b) / (c - b))
    k = float(np.clip(k, 0, 1))
    return tuple(int(x[i] + (y[i] - x[i]) * k) for i in range(3))


# ---------------------------------------------------------------- procedimiento de T08
def estadistico(modelo):
    return np.median if modelo.startswith("mediana") else np.mean


def predecir(d, modelo, ocultar=None):
    """Mismo procedimiento que T08: estadístico del municipio -> grupo de registro -> global, con las parcelas con
    cosecha. `ocultar` quita un municipio del entrenamiento (para mostrar el caso de información insuficiente)."""
    f = estadistico(modelo)
    tr, te = d[d.CONJUNTO == "ENTRENAMIENTO"], d[d.CONJUNTO == "PREDICCION"]
    if ocultar:
        tr = tr[tr.municipio != ocultar]
    mun, grp = tr.groupby("municipio").real.agg(f), tr.groupby("grupo_registro").real.agg(f)
    p = te.municipio.map(mun)
    fuente = np.where(p.notna(), "municipio", np.where(te.grupo_registro.map(grp).notna(), "grupo", "global"))
    p = p.fillna(te.grupo_registro.map(grp)).fillna(f(tr.real))
    n_mun = te.municipio.map(tr.municipio.value_counts()).fillna(0).astype(int)
    return pd.DataFrame({"municipio": te.municipio, "prediccion": p, "fuente": fuente, "n_municipio": n_mun,
                         "area_ha": te.AREA_HA})


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
