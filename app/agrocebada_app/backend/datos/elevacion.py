"""Altitud de cada parcela (dato fijo en datos_estaticos/)."""
import pandas as pd

from agrocebada_app.config import APP


def elevaciones():
    f = APP / "datos_estaticos" / "elevacion_parcelas.csv"
    return pd.read_csv(f).set_index("ID_POLIGONO").elev_max_m if f.exists() else None
