"""Geometría de parcelas: vecinas, contorno simplificado y zoom para encuadrar un conjunto."""
import numpy as np


def vecinas(d, pid, radio=0.06):
    """Parcelas a ~6 km de la elegida (distancia en grados, suficiente para encuadrar el mapa)."""
    r = d.loc[pid]
    return d.index[np.hypot(d.lon_c - r.lon_c, d.lat_c - r.lat_c) < radio]


def anillo(geom):
    g = max(geom.geoms, key=lambda p: p.area) if geom.geom_type == "MultiPolygon" else geom
    g = g.simplify(0.00003)                      # ~3 m: menos vértices, bordes 3D más limpios
    return [(round(c[0], 6), round(c[1], 6)) for c in g.exterior.coords]


def zoom_para(gdf):
    x0, y0, x1, y1 = gdf.total_bounds
    lado = max(x1 - x0, (y1 - y0) * 1.3, 0.01)
    return float(np.clip(np.log2(560 / lado), 5, 14))       # deja ~50 % de margen en un mapa de ~1200 px
