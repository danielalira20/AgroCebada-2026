"""Lo que usa la app: el paquete compacto `datos_app/` (parquet) o, si no existe, las fuentes originales."""
import os

import geopandas as gpd
import pandas as pd

from agrocebada_app.backend.datos import lectura
from agrocebada_app.backend.rutas.localizador import rutas
from agrocebada_app.config import PAQ


def usar_paquete():
    return (PAQ / "parcelas.parquet").exists() and not os.environ.get("AGRO_SIN_PAQUETE")


def hay_datos():
    return usar_paquete() or rutas()["datos"] is not None


def parcelas():
    if usar_paquete():
        return gpd.read_parquet(PAQ / "parcelas.parquet")
    return lectura.leer_parcelas(rutas()["datos"])


def series():
    if usar_paquete():
        return pd.read_parquet(PAQ / "series.parquet")
    return lectura.leer_series(rutas()["datos"])


def clima():
    if usar_paquete():
        f = PAQ / "clima.parquet"
        return pd.read_parquet(f) if f.exists() else None
    t04 = rutas()["t04"]
    return lectura.leer_clima(t04) if t04 else None


def validacion(modelo, municipios):
    if usar_paquete():
        f = PAQ / "validacion.parquet"
        o = pd.read_parquet(f) if f.exists() else None
    else:
        t08 = rutas()["t08"]
        o = lectura.leer_validacion(t08) if t08 else None
    if o is None or not (o.candidato == modelo).any():
        return None
    o = o[o.candidato == modelo].copy()
    o["municipio"] = o.ID_POLIGONO.map(municipios)
    return o.assign(ae=(o.prediccion - o.real).abs(), e=o.prediccion - o.real)


def oficial(modelo):
    if usar_paquete():
        f = PAQ / "oficial_59.csv"
        o = pd.read_csv(f) if f.exists() else None
    else:
        t08 = rutas()["t08"]
        o = lectura.leer_oficial(t08) if t08 else None
    return None if o is None else o[o.candidato == modelo].set_index("ID_POLIGONO").prediccion


def soporte():
    if usar_paquete():
        f = PAQ / "soporte.parquet"
        return pd.read_parquet(f) if f.exists() else None
    t03 = rutas()["t03"]
    return lectura.leer_soporte(t03) if t03 else None
