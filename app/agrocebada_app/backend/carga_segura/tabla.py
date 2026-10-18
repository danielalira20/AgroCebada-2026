"""Lectura y validación de la tabla de parcelas (CSV) y de los polígonos (shapefile)."""
import io

import geopandas as gpd
import numpy as np
import pandas as pd

from agrocebada_app.backend.carga_segura.errores import Rechazo, Resultado
from agrocebada_app.backend.carga_segura.reglas import (
    AREA, CAMPOS_SHP, COLS_SIMPLE, COLS_TABLA, ID_VALIDO, MAX_PARCELAS, MEXICO, MIN_CON_COSECHA, RENDIMIENTO)
from agrocebada_app.backend.datos.lectura import con_centroides


def columnas_de(b):
    try:
        return set(pd.read_csv(io.BytesIO(b), nrows=0, encoding="utf-8-sig").columns.str.strip())
    except Exception:
        return set()


def desde_csv_simple(contenido):
    if b"\x00" in contenido[:4096]:
        raise Rechazo("El .csv no es texto (parece un archivo binario).")
    cols = columnas_de(contenido)
    faltan = [c for c in COLS_SIMPLE if c not in cols]
    if faltan:
        if all(c in cols for c in COLS_TABLA):
            raise Rechazo("Esta tabla es la del reto: súbela en un ZIP junto con el shapefile, o agrega las columnas "
                          "MUNICIPIO y GRUPO para usar el CSV simple.")
        raise Rechazo(f"Al CSV le faltan columnas: {', '.join(faltan)}.")
    tabla, rev, avisos = leer_tabla(contenido, COLS_SIMPLE)
    d = tabla.rename(columns={"MUNICIPIO": "municipio", "GRUPO": "grupo_registro"})
    d["Estado"] = ""
    return Resultado(d, False, rev, avisos)


def texto_valido(s, campo):
    s = s.astype("string").str.strip()
    if s.isna().any() or (s == "").any():
        raise Rechazo(f"Hay valores vacíos en {campo}.")
    if (s.str.len() > 60).any():
        raise Rechazo(f"Hay textos de más de 60 caracteres en {campo}.")
    return s.astype(str)


def leer_tabla(contenido, columnas):
    try:
        t = pd.read_csv(io.BytesIO(contenido), encoding="utf-8-sig", dtype=str, nrows=MAX_PARCELAS + 1,
                        skipinitialspace=True)
    except UnicodeDecodeError:
        raise Rechazo("El .csv no está en UTF-8; guárdalo como «CSV UTF-8».") from None
    except Exception:
        raise Rechazo("No pude leer el .csv; revisa que esté separado por comas.") from None
    t.columns = t.columns.str.strip()
    t = t[columnas]
    if len(t) > MAX_PARCELAS:
        raise Rechazo(f"La tabla tiene más de {MAX_PARCELAS:,} parcelas.")
    avisos, rev = [], []
    t["ID_POLIGONO"] = texto_valido(t.ID_POLIGONO, "ID_POLIGONO")
    malos = t.ID_POLIGONO[~t.ID_POLIGONO.str.match(ID_VALIDO)]
    if len(malos):
        raise Rechazo(f"IDs con caracteres no permitidos (sólo letras, números, _ . - y espacio): {malos.iloc[0][:40]}")
    if t.ID_POLIGONO.duplicated().any():
        raise Rechazo(f"IDs repetidos: {', '.join(t.ID_POLIGONO[t.ID_POLIGONO.duplicated()].head(3))}.")
    t["CONJUNTO"] = texto_valido(t.CONJUNTO, "CONJUNTO").str.upper()
    otros = sorted(set(t.CONJUNTO) - {"ENTRENAMIENTO", "PREDICCION"})
    if otros:
        raise Rechazo(f"CONJUNTO sólo puede ser ENTRENAMIENTO o PREDICCION; encontré: {', '.join(otros[:3])}.")
    area = pd.to_numeric(t.AREA_HA, errors="coerce")
    if area.isna().any() or not area.between(*AREA).all():
        raise Rechazo(f"AREA_HA debe ser un número entre {AREA[0]} y {AREA[1]:,.0f} ha en todas las parcelas.")
    y = pd.to_numeric(t.RENDIMIENTO_T_HA, errors="coerce")
    tr = t.CONJUNTO == "ENTRENAMIENTO"
    if y[tr].isna().any() or not y[tr].between(*RENDIMIENTO).all():
        raise Rechazo(f"RENDIMIENTO_T_HA debe estar entre {RENDIMIENTO[0]} y {RENDIMIENTO[1]:.0f} t/ha en todas las "
                      "parcelas de ENTRENAMIENTO.")
    if y[~tr].notna().any():
        avisos.append(f"{int(y[~tr].notna().sum())} parcelas de PREDICCION traían rendimiento; se ignoró.")
        y[~tr] = np.nan
    if tr.sum() < MIN_CON_COSECHA:
        raise Rechazo(f"Se necesitan al menos {MIN_CON_COSECHA} parcelas con cosecha (ENTRENAMIENTO); hay {int(tr.sum())}.")
    if (~tr).sum() == 0:
        raise Rechazo("No hay parcelas por estimar (CONJUNTO = PREDICCION).")
    for c in ("MUNICIPIO", "GRUPO"):
        if c in t:
            t[c] = texto_valido(t[c], c)
    d = t.assign(AREA_HA=area.astype(float), real=y.astype(float)).drop(columns="RENDIMIENTO_T_HA")
    rev.append(f"Tabla válida: {len(d)} parcelas, {int(tr.sum())} con cosecha y {int((~tr).sum())} por estimar; IDs "
               "únicos, áreas y rendimientos dentro de rango.")
    return d.set_index("ID_POLIGONO"), rev, avisos


def con_poligonos(tabla, geo):
    if len(geo) > MAX_PARCELAS:
        raise Rechazo(f"El shapefile tiene más de {MAX_PARCELAS:,} polígonos.")
    faltan = [c for c in CAMPOS_SHP if c not in geo.columns]
    if faltan:
        raise Rechazo(f"Al shapefile le faltan los campos: {', '.join(faltan)}.")
    if geo.crs is None:
        raise Rechazo("El shapefile no dice su sistema de coordenadas (falta o está vacío el .prj).")
    geo = geo.to_crs(4326).rename(columns=CAMPOS_SHP)
    geo["ID_POLIGONO"] = texto_valido(geo.ID_POLIGONO, "ID_POLIGON")
    geo["municipio"] = texto_valido(geo.municipio, "Municipio")
    geo["grupo_registro"] = texto_valido(geo.grupo_registro, "Cultivo")
    geo["Estado"] = geo["Estado"].fillna("").astype(str).str.slice(0, 60) if "Estado" in geo else ""
    if geo.ID_POLIGONO.duplicated().any():
        raise Rechazo("El shapefile tiene IDs repetidos en ID_POLIGON.")
    a, b = set(tabla.index), set(geo.ID_POLIGONO)
    if a != b:
        raise Rechazo(f"Los IDs no coinciden: {len(a - b)} de la tabla no están en los polígonos y {len(b - a)} "
                      "polígonos no están en la tabla.")
    if not geo.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise Rechazo("Hay geometrías que no son polígonos.")
    invalidos = ~geo.is_valid
    if invalidos.any():
        geo.loc[invalidos, "geometry"] = geo.loc[invalidos].buffer(0)
        if not geo.is_valid.all() or geo.is_empty.any():
            raise Rechazo("Hay polígonos inválidos que no se pudieron reparar.")
    x0, y0, x1, y1 = geo.total_bounds
    if x0 < MEXICO[0] or y0 < MEXICO[1] or x1 > MEXICO[2] or y1 > MEXICO[3]:
        raise Rechazo("Hay polígonos fuera de México; revisa el sistema de coordenadas (.prj).")
    d = tabla.join(geo.set_index("ID_POLIGONO")[["municipio", "grupo_registro", "Estado", "geometry"]])
    d = con_centroides(gpd.GeoDataFrame(d, geometry="geometry", crs=4326))
    rev = [f"Polígonos válidos: {len(geo)} parcelas en {d.municipio.nunique()} municipios, IDs iguales a la tabla, "
           "dentro de México."]
    return d, rev
