"""Procedimiento de T08: estadístico del municipio -> grupo de registro -> global."""
import numpy as np
import pandas as pd


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
