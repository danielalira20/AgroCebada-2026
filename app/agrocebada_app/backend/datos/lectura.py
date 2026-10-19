"""Lectura de las fuentes originales (dataset del reto, T08, T03 y T04)."""
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from agrocebada_app.config import COLUMNAS_INDICES, MODELOS_CANDIDATOS, TEMPORADA


def leer_parcelas(datos):
    datos = Path(datos)
    cat = pd.read_csv(datos / "ID_area_rendimiento_70_30_Reto_AgroCebada.csv", encoding="utf-8-sig")
    cat = cat.drop(columns=[c for c in cat.columns if c.startswith("Unnamed")])
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(datos / "Parcelas_Reto_AGC_CONJUNTO_70_30.zip") as z:
        z.extractall(tmp)
        geo = gpd.read_file(Path(tmp) / "Parcelas_Reto_AGC_CONJUNTO.shp").to_crs(4326)
    geo = geo.rename(columns={"ID_POLIGON": "ID_POLIGONO", "Cultivo": "grupo_registro", "Municipio": "municipio"})
    d = cat.merge(geo[["ID_POLIGONO", "municipio", "grupo_registro", "Estado", "geometry"]], on="ID_POLIGONO",
                  validate="one_to_one").rename(columns={"RENDIMIENTO_T_HA": "real"}).set_index("ID_POLIGONO")
    return con_centroides(gpd.GeoDataFrame(d, geometry="geometry", crs=4326))


def con_centroides(d):
    c = d.geometry.to_crs(6372).centroid.to_crs(4326)       # centroides en proyección métrica de México
    return d.assign(lon_c=c.x, lat_c=c.y)


def leer_series(datos):
    datos = Path(datos)
    usar = ["ID_POLIGONO", "fecha_captura", "sensor", "porcentaje_nubosidad", *COLUMNAS_INDICES]
    x = pd.concat([pd.read_csv(datos / "Conjunto_datos_BASICO_AgroCebada2026.csv", usecols=usar),
                   pd.read_csv(datos / "Conjunto_datos_PRO_AgroCebada.csv", usecols=usar)], ignore_index=True)
    x["fecha"] = pd.to_datetime(x.fecha_captura, format="%d/%m/%Y")
    x = x[x.sensor.isin(["Sentinel-2", "Planet"]) & (x.porcentaje_nubosidad <= 20) & x.fecha.between(*TEMPORADA)]
    return x[["ID_POLIGONO", "fecha", "sensor", *COLUMNAS_INDICES]].reset_index(drop=True)


def leer_clima(t04):
    c = pd.read_csv(t04)
    c = c[c.periodo.between("2025-03", "2025-10")]
    return c.pivot_table(index=["id_parcela", "periodo"], columns="variable", values="media_ponderada").reset_index()
def leer_clima_normal(t04):
    """Promedio 2022–2024 por parcela y mes (marzo a octubre), para comparar contra el clima de 2025."""
    c = pd.read_csv(t04)
    c = c[c.periodo.between("2022-01", "2024-12")]
    c = c.assign(mes=c.periodo.str[5:].astype(int))
    c = c[c.mes.between(3, 10)]
    return (c.pivot_table(index=["id_parcela", "mes"], columns="variable", values="media_ponderada", aggfunc="mean")
            .reset_index().rename_axis(columns=None))


def leer_validacion(t08):
    partes = [pd.read_csv(Path(t08) / f"predicciones_oof_referencias_{m}.csv") for m in MODELOS_CANDIDATOS
              if (Path(t08) / f"predicciones_oof_referencias_{m}.csv").exists()]
    return pd.concat(partes, ignore_index=True) if partes else None


def leer_oficial(t08):
    f = Path(t08) / "predicciones_59_referencias.csv"
    return pd.read_csv(f) if f.exists() else None


def leer_entrega_final(t18):
    """Las 59 predicciones de la entrega de T18 (RENDIMIENTO_T_HA a 2 decimales), o None si no existe."""
    f = Path(t18) / "predicciones_finales.csv"
    return pd.read_csv(f, encoding="utf-8-sig").set_index("ID_POLIGONO") if f.exists() else None


def leer_soporte(t03):
    f = Path(t03) / "soporte_parcelas.csv"
    return pd.read_csv(f).set_index("ID_POLIGONO") if f.exists() else None

def leer_calidad(t07):
    """Revisión de contornos por parcela (T07): categoría del dibujo, si es angosta o muy pequeña y si tiene alerta."""
    f = Path(t07) / "calidad_parcelas.csv"
    if not f.exists():
        return None
    c = pd.read_csv(f).rename(columns={"id_parcela": "ID_POLIGONO"}).set_index("ID_POLIGONO")
    return c[["contorno_categoria", "contorno_angosta_o_muy_pequena", "alerta_contorno_t03_bis"]]