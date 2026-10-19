"""Tabla de pruebas de la pestaña «Evidencia» (dato fijo en datos_estaticos/; la arma herramientas/construir_experimentos.py)."""
import pandas as pd

from agrocebada_app.config import APP


def experimentos():
    f = APP / "datos_estaticos" / "experimentos.csv"
    return pd.read_csv(f, keep_default_na=False, na_values=[""]) if f.exists() else None
