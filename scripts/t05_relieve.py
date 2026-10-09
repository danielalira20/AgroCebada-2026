"""T05 · Relieve por parcela: funciones puras de extracción.

El método está en docs/t05_relieve.md. Aquí no se leen archivos: las funciones
reciben la geometría ya proyectada al CRS del ráster (EPSG:6372, cuadrícula
proyectada en metros) y un ráster abierto. Las áreas son planas en ese sistema.

Diferencia deliberada con scripts/t04_espacio.py: una parcela sin cobertura
espacial o con todo NoData no lanza error; recibe un estado y sus valores
quedan vacíos.
"""
import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from pyproj import CRS
from shapely.geometry import box

METODO_AREA = "plana_crs_raster_v1"
TOLERANCIA_AREA_REL = 1e-6      # La misma que TOLERANCIA_AREA_REL de T04.
TOLERANCIA_COMPLETA = 1e-9      # Cobertura completa: >= 1 - 1e-9, nunca == 1.
PISO_PENDIENTE_T10 = 0.5        # D020: solo pendiente, aplicado sin redondear.
AREA_CELDA_REFERENCIA_M2 = 120.0 * 120.0
MAX_POCAS_CELDAS = 4

ESTADOS = ("cobertura_completa", "cobertura_parcial", "todo_nodata", "sin_cobertura_espacial")


def firma_cuadricula(raster):
    return {"crs": raster.crs.to_wkt() if raster.crs else None,
            "columnas": raster.width, "filas": raster.height,
            "transformacion": list(raster.transform)[:6]}


def _validar(geometria, crs_parcela, raster):
    if crs_parcela is None or raster.crs is None:
        raise ValueError("CRS ausente")
    crs = CRS.from_user_input(raster.crs)
    if CRS.from_user_input(crs_parcela) != crs:
        raise ValueError("CRS incompatible entre parcela y ráster")
    if not crs.is_projected:
        raise ValueError("T05 requiere una cuadrícula proyectada")
    if crs.axis_info[0].unit_name not in ("metre", "meter"):
        raise ValueError("Unidades de la cuadrícula distintas de metros")
    t = raster.transform
    if not all(math.isfinite(x) for x in t) or t.a <= 0 or t.e >= 0 or t.b != 0 or t.d != 0:
        raise ValueError("Cuadrícula rotada o transformación no admisible")
    if geometria.geom_type not in ("Polygon", "MultiPolygon") or geometria.is_empty or not geometria.is_valid:
        raise ValueError("Geometría parcelaria no admisible")
    if not math.isfinite(geometria.area) or geometria.area <= 0:
        raise ValueError("Área parcelaria no admisible")


def preparar_soporte(geometria, crs_parcela, raster):
    """Celdas con intersección de área positiva y áreas de control.

    El área dentro de la extensión del ráster se calcula directamente
    (parcela ∩ extensión), no como residuo, para poder contrastarla con la
    suma de intersecciones por celda.
    """
    _validar(geometria, crs_parcela, raster)
    t = raster.transform
    area = geometria.area
    x0, y0 = t @ (0, 0)
    x1, y1 = t @ (raster.width, raster.height)
    extension = box(x0, y1, x1, y0)
    area_en_extension = geometria.intersection(extension).area
    xmin, ymin, xmax, ymax = geometria.bounds
    col0 = max(0, math.floor((xmin - t.c) / t.a) - 1)
    col1 = min(raster.width, math.floor((xmax - t.c) / t.a) + 2)
    fil0 = max(0, math.floor((ymax - t.f) / t.e) - 1)
    fil1 = min(raster.height, math.floor((ymin - t.f) / t.e) + 2)
    celdas = []
    for fila in range(fil0, fil1):
        for columna in range(col0, col1):
            cx0, cy0 = t @ (columna, fila)
            cx1, cy1 = t @ (columna + 1, fila + 1)
            a = geometria.intersection(box(cx0, cy1, cx1, cy0)).area
            if a > 0:
                celdas.append({"fila": fila, "columna": columna, "area_m2": a})
    area_celdas = math.fsum(c["area_m2"] for c in celdas)
    return {"metodo_area": METODO_AREA,
            "cuadricula": firma_cuadricula(raster),
            "area_parcela_m2": area,
            "area_en_extension_m2": area_en_extension,
            "area_fuera_mapa_m2": max(0.0, area - area_en_extension),
            "area_celdas_m2": area_celdas,
            "cobertura_espacial": area_en_extension / area,
            "celdas": celdas}


def comprobar_areas(soporte):
    """Detiene la entrega si se omitieron o duplicaron celdas (docs/t05_relieve.md)."""
    area = soporte["area_parcela_m2"]
    tol = TOLERANCIA_AREA_REL * area
    claves = [(c["fila"], c["columna"]) for c in soporte["celdas"]]
    if len(claves) != len(set(claves)):
        raise ValueError("Celda duplicada en el soporte")
    # Se vuelve a sumar desde la lista de celdas; no se confía en el total guardado.
    area_celdas = math.fsum(c["area_m2"] for c in soporte["celdas"])
    if abs(area_celdas - soporte["area_celdas_m2"]) > tol:
        raise ValueError("Total de celdas alterado")
    if area_celdas > area + tol:
        raise ValueError("Intersecciones exceden el área parcelaria")
    if abs(area_celdas - soporte["area_en_extension_m2"]) > tol:
        raise ValueError("Suma de intersecciones distinta del área directa")
    if abs(area_celdas + soporte["area_fuera_mapa_m2"] - area) > tol:
        raise ValueError("Balance de áreas incumplido")


def resumir_variable(soporte, raster, datos=None):
    """Media ponderada por área válida, extremos, cobertura y estado de una variable."""
    if firma_cuadricula(raster) != soporte["cuadricula"]:
        raise ValueError("Cuadrícula distinta: recalcular soporte")
    if datos is None:
        datos = raster.read(1, masked=True)
    if not np.ma.isMaskedArray(datos) or datos.shape != (raster.height, raster.width):
        raise ValueError("Datos y máscara no corresponden a la cuadrícula")
    celdas = []
    for c in soporte["celdas"]:
        v = datos[c["fila"], c["columna"]]
        valida = not np.ma.is_masked(v)
        if valida and not np.isfinite(v):
            raise ValueError("Valor válido no finito")
        celdas.append({**c, "valida": valida, "valor": float(v) if valida else None})
    validas = [c for c in celdas if c["valida"]]
    area_valida = math.fsum(c["area_m2"] for c in validas)
    media = minimo = maximo = None
    if area_valida > 0:
        media = math.fsum(c["valor"] * c["area_m2"] for c in validas) / area_valida
        minimo = min(c["valor"] for c in validas)
        maximo = max(c["valor"] for c in validas)
        if not minimo - 1e-9 <= media <= maximo + 1e-9:
            raise ValueError("Media fuera del rango válido")
    cobertura = area_valida / soporte["area_parcela_m2"]
    if not celdas:
        estado = "sin_cobertura_espacial"
    elif area_valida == 0:
        estado = "todo_nodata"
    elif cobertura >= 1 - TOLERANCIA_COMPLETA:
        estado = "cobertura_completa"
    else:
        estado = "cobertura_parcial"
    return {"media": media, "minimo": minimo, "maximo": maximo,
            "cobertura_valida": min(1.0, cobertura),
            "celdas_intersectadas": len(celdas), "celdas_validas": len(validas),
            "area_valida_m2": area_valida,
            "area_nodata_m2": soporte["area_celdas_m2"] - area_valida,
            "estado": estado, "celdas": celdas}


def pendiente_para_t10(resumen_pendiente):
    """D020: valor original si la cobertura válida (sin redondear) es >= 0.5; si no, vacío."""
    if resumen_pendiente["media"] is None:
        return None
    if resumen_pendiente["cobertura_valida"] >= PISO_PENDIENTE_T10:
        return resumen_pendiente["media"]
    return None


def valor_en_punto(raster, datos, x, y):
    """Valor de la celda que contiene el punto, sin interpolar: (valor, estado)."""
    col, fila = ~raster.transform @ (x, y)
    col, fila = math.floor(col), math.floor(fila)
    if not (0 <= fila < raster.height and 0 <= col < raster.width):
        return None, "fuera_de_cuadricula"
    v = datos[fila, col]
    if np.ma.is_masked(v):
        return None, "sin_dato"
    return float(v), "valido"


def avisos(area_parcela_m2, elevacion, pendiente, centroide_dentro,
           estado_centroide_elevacion, estado_centroide_pendiente):
    """Hechos con umbral declarado; ninguno excluye parcelas por sí mismo."""
    lista = []
    if pendiente["cobertura_valida"] < PISO_PENDIENTE_T10:
        lista.append("pendiente_bajo_piso_50")
    if elevacion["estado"] == "cobertura_parcial":
        lista.append("cobertura_parcial_elevacion")
    if pendiente["estado"] == "cobertura_parcial":
        lista.append("cobertura_parcial_pendiente")
    if min(elevacion["celdas_validas"], pendiente["celdas_validas"]) <= MAX_POCAS_CELDAS:
        lista.append("pocas_celdas_validas")
    if area_parcela_m2 < AREA_CELDA_REFERENCIA_M2:
        lista.append("parcela_menor_a_una_celda")
    if not centroide_dentro:
        lista.append("centroide_fuera_de_parcela")
    if estado_centroide_elevacion != "valido":
        lista.append("centroide_sin_dato_elevacion")
    if estado_centroide_pendiente != "valido":
        lista.append("centroide_sin_dato_pendiente")
    return lista


# ---------------------------------------------------------------------------
# Extracción sobre archivos reales (paso 4). Escribe en una carpeta nueva bajo
# data/processed/t05/; la publicación en registro/t05/ se hace aparte.
# ---------------------------------------------------------------------------

NOMBRE_SHP = "Parcelas_Reto_AGC_CONJUNTO.shp"
NOMBRE_ELEVACION = "Elevacion_INEGI_CEM4_120m.tif"
NOMBRE_PENDIENTE = "Pendiente_INEGI_CEM4_120m_grados.tif"
CRS_PARCELAS = "EPSG:4326"
CRS_RELIEVE = "EPSG:6372"
NODATA_RELIEVE = -9999.0
COLUMNA_ID_SHP = "ID_POLIGON"

COLUMNAS_PARCELA = (
    "id_parcela", "area_parcela_6372_m2", "cobertura_espacial",
    "elevacion_media_m", "elevacion_cobertura_valida", "elevacion_celdas_intersectadas",
    "elevacion_celdas_validas", "elevacion_area_valida_m2", "elevacion_min_m",
    "elevacion_max_m", "estado_elevacion",
    "pendiente_media_grados", "pendiente_cobertura_valida", "pendiente_celdas_intersectadas",
    "pendiente_celdas_validas", "pendiente_area_valida_m2", "pendiente_min_grados",
    "pendiente_max_grados", "estado_pendiente",
    "pendiente_media_t10_grados",
    "elevacion_centroide_m", "pendiente_centroide_grados",
    "diferencia_elevacion_centroide_m", "diferencia_pendiente_centroide_grados",
    "centroide_dentro_parcela", "avisos")
COLUMNAS_CELDA = ("id_parcela", "fila", "columna", "area_interseccion_m2",
                  "elevacion_m", "elevacion_valida", "pendiente_grados", "pendiente_valida")


def buscar_unico(raiz, nombre):
    encontrados = sorted(Path(raiz).rglob(nombre))
    if len(encontrados) != 1:
        raise ValueError(f"Se esperaba un solo {nombre} bajo {raiz}; hay {len(encontrados)}")
    return encontrados[0]


def leer_parcelas(ruta_shp):
    """Contornos con `id_parcela` (desde ID_POLIGON), reproyectados a EPSG:6372."""
    import geopandas as gpd
    gdf = gpd.read_file(ruta_shp)
    if gdf.crs is None or CRS.from_user_input(gdf.crs) != CRS.from_user_input(CRS_PARCELAS):
        raise ValueError("CRS de parcelas distinto del esperado")
    if COLUMNA_ID_SHP not in gdf.columns:
        raise ValueError(f"Falta la columna {COLUMNA_ID_SHP}")
    ids = gdf[COLUMNA_ID_SHP].astype(str)
    if ids.duplicated().any() or (ids.str.strip() == "").any():
        raise ValueError("IDs de parcela duplicados o vacíos")
    gdf = gdf.assign(id_parcela=ids).to_crs(CRS_RELIEVE)
    return [(fila.id_parcela, fila.geometry) for fila in gdf.itertuples()]


def comprobar_relieve(elevacion, pendiente):
    """Detiene la entrega si los dos TIFF no comparten cuadrícula, CRS o NoData."""
    if firma_cuadricula(elevacion) != firma_cuadricula(pendiente):
        raise ValueError("Cuadrículas de elevación y pendiente no alineadas")
    for r in (elevacion, pendiente):
        if CRS.from_user_input(r.crs) != CRS.from_user_input(CRS_RELIEVE):
            raise ValueError("CRS del relieve distinto de EPSG:6372")
        if r.count != 1 or r.nodata != NODATA_RELIEVE:
            raise ValueError("Banda o NoData del relieve inesperados")


def _dif(a, b):
    return None if a is None or b is None else a - b


def extraer_parcela(id_parcela, geom, elevacion, d_elev, pendiente, d_pend):
    soporte = preparar_soporte(geom, CRS_RELIEVE, elevacion)
    comprobar_areas(soporte)
    e = resumir_variable(soporte, elevacion, d_elev)
    p = resumir_variable(soporte, pendiente, d_pend)
    c = geom.centroid
    ce, est_e = valor_en_punto(elevacion, d_elev, c.x, c.y)
    cp, est_p = valor_en_punto(pendiente, d_pend, c.x, c.y)
    dentro = geom.covers(c)  # Como T04: el polígono cubre el punto, incluido su borde.
    fila = {
        "id_parcela": id_parcela, "area_parcela_6372_m2": soporte["area_parcela_m2"],
        "cobertura_espacial": soporte["cobertura_espacial"],
        "elevacion_media_m": e["media"], "elevacion_cobertura_valida": e["cobertura_valida"],
        "elevacion_celdas_intersectadas": e["celdas_intersectadas"],
        "elevacion_celdas_validas": e["celdas_validas"], "elevacion_area_valida_m2": e["area_valida_m2"],
        "elevacion_min_m": e["minimo"], "elevacion_max_m": e["maximo"], "estado_elevacion": e["estado"],
        "pendiente_media_grados": p["media"], "pendiente_cobertura_valida": p["cobertura_valida"],
        "pendiente_celdas_intersectadas": p["celdas_intersectadas"],
        "pendiente_celdas_validas": p["celdas_validas"], "pendiente_area_valida_m2": p["area_valida_m2"],
        "pendiente_min_grados": p["minimo"], "pendiente_max_grados": p["maximo"],
        "estado_pendiente": p["estado"],
        "pendiente_media_t10_grados": pendiente_para_t10(p),
        "elevacion_centroide_m": ce, "pendiente_centroide_grados": cp,
        "diferencia_elevacion_centroide_m": _dif(e["media"], ce),
        "diferencia_pendiente_centroide_grados": _dif(p["media"], cp),
        "centroide_dentro_parcela": dentro,
        "avisos": ";".join(avisos(soporte["area_parcela_m2"], e, p, dentro, est_e, est_p)),
    }
    celdas = [{"id_parcela": id_parcela, "fila": ce_["fila"], "columna": ce_["columna"],
               "area_interseccion_m2": ce_["area_m2"],
               "elevacion_m": ce_["valor"], "elevacion_valida": ce_["valida"],
               "pendiente_grados": cp_["valor"], "pendiente_valida": cp_["valida"]}
              for ce_, cp_ in zip(e["celdas"], p["celdas"])]
    return fila, celdas


def _texto(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)  # Sin redondear.
    return str(v)


def escribir_csv(ruta, columnas, filas):
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")  # LF siempre (lección del verificador de T04).
        w.writerow(columnas)
        for fila in filas:
            w.writerow([_texto(fila[c]) for c in columnas])


def extraer(dataset, salida):
    """Extrae todas las parcelas; solo escribe si todo pasó los controles que detienen."""
    import rasterio
    salida = Path(salida)
    if salida.exists() and any(salida.iterdir()):
        raise ValueError("La salida debe ser una carpeta nueva o vacía")
    parcelas = leer_parcelas(buscar_unico(dataset, NOMBRE_SHP))
    with rasterio.open(buscar_unico(dataset, NOMBRE_ELEVACION)) as re_, \
         rasterio.open(buscar_unico(dataset, NOMBRE_PENDIENTE)) as rp:
        comprobar_relieve(re_, rp)
        de, dp = re_.read(1, masked=True), rp.read(1, masked=True)
        filas, celdas = [], []
        for id_parcela, geom in parcelas:
            f, c = extraer_parcela(id_parcela, geom, re_, de, rp, dp)
            filas.append(f)
            celdas.extend(c)
    filas.sort(key=lambda f: f["id_parcela"])
    celdas.sort(key=lambda c: (c["id_parcela"], c["fila"], c["columna"]))
    salida.mkdir(parents=True, exist_ok=True)
    escribir_csv(salida / "relieve_parcela.csv", COLUMNAS_PARCELA, filas)
    escribir_csv(salida / "relieve_celdas.csv", COLUMNAS_CELDA, celdas)
    return filas, celdas


# ---------------------------------------------------------------------------
# Controles sobre datos reales (paso 5). Leen los CSV escritos, que son lo que
# el equipo usará, y escriben controles.json junto a ellos.
# ---------------------------------------------------------------------------
TOLERANCIA_T02 = 0.00005 + 1e-9   # T02 redondea coberturas a cuatro decimales.


def _numero(v):
    return None if v in ("", None) else float(v)


def leer_csv(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def conciliar_con_t02(filas, t02):
    """Compara coberturas con T02. Una diferencia mayor que la tolerancia es aviso, no
    detiene la ejecución, pero T05 no se da por cerrada hasta explicarla."""
    ids = {f["id_parcela"] for f in filas}
    resultado = {"ids_solo_en_t05": sorted(ids - set(t02)),
                 "ids_solo_en_t02": sorted(set(t02) - ids),
                 "tolerancia": TOLERANCIA_T02, "max_diferencia": 0.0, "discrepancias": []}
    for f in filas:
        if f["id_parcela"] not in t02:
            continue
        for variable, col_t05 in (("elevacion", "elevacion_cobertura_valida"),
                                  ("pendiente", "pendiente_cobertura_valida")):
            a, b = _numero(f[col_t05]), t02[f["id_parcela"]][variable]
            d = abs(a - b)
            resultado["max_diferencia"] = max(resultado["max_diferencia"], d)
            if d > TOLERANCIA_T02:
                resultado["discrepancias"].append(
                    {"id_parcela": f["id_parcela"], "variable": variable, "t05": a, "t02": b})
    return resultado


def comprobar_reservadas(filas, conjunto):
    """Las parcelas de PREDICCION deben tener cobertura completa en las dos variables."""
    reservadas = [f for f in filas if conjunto.get(f["id_parcela"]) == "PREDICCION"]
    incompletas = sorted(f["id_parcela"] for f in reservadas
                         if f["estado_elevacion"] != "cobertura_completa"
                         or f["estado_pendiente"] != "cobertura_completa")
    return {"reservadas": len(reservadas), "incompletas": incompletas}


def comprobar_tablas(filas, celdas):
    """Coherencia entre relieve_parcela.csv y relieve_celdas.csv; detiene si falla."""
    por_id = {}
    for c in celdas:
        n, a = por_id.get(c["id_parcela"], (0, 0.0))
        por_id[c["id_parcela"]] = (n + 1, a + float(c["area_interseccion_m2"]))
    peor = 0.0
    for f in filas:
        n, a = por_id.get(f["id_parcela"], (0, 0.0))
        if n != int(f["elevacion_celdas_intersectadas"]):
            raise ValueError(f"Celdas distintas entre tablas: {f['id_parcela']}")
        area = float(f["area_parcela_6372_m2"])
        peor = max(peor, abs(a - area * float(f["cobertura_espacial"])) / area)
    if peor > TOLERANCIA_AREA_REL:
        raise ValueError("Áreas de celdas no suman el área de la parcela")
    if set(por_id) != {f["id_parcela"] for f in filas}:
        raise ValueError("IDs distintos entre tablas")
    return {"max_diferencia_area_relativa": peor}


def comparar_areas_fisicas(parcelas, elevacion, d_elev, pendiente, d_pend):
    """Control, no decisión de método: medias y coberturas con pesos de área física
    WGS84 (función ya probada de T04) frente a pesos de área plana EPSG:6372."""
    from pyproj import Transformer
    from shapely.ops import transform as transformar
    from scripts.t04_espacio import area_fisica
    a_wgs = Transformer.from_crs(CRS_RELIEVE, CRS_PARCELAS, always_xy=True).transform
    t = elevacion.transform
    peor = {"elevacion_media_m": 0.0, "pendiente_media_grados": 0.0, "cobertura": 0.0}
    for _, geom in parcelas:
        soporte = preparar_soporte(geom, CRS_RELIEVE, elevacion)
        fisicas = []
        for c in soporte["celdas"]:
            x0, y0 = t @ (c["columna"], c["fila"])
            x1, y1 = t @ (c["columna"] + 1, c["fila"] + 1)
            pieza = geom.intersection(box(x0, y1, x1, y0))
            fisicas.append(area_fisica(transformar(a_wgs, pieza)))
        total_fisico = area_fisica(transformar(a_wgs, geom))
        for nombre, raster, datos in (("elevacion_media_m", elevacion, d_elev),
                                      ("pendiente_media_grados", pendiente, d_pend)):
            plana = resumir_variable(soporte, raster, datos)
            validas = [(c, af) for c, af in zip(plana["celdas"], fisicas) if c["valida"]]
            if not validas:
                continue
            area_v = math.fsum(af for _, af in validas)
            media_f = math.fsum(c["valor"] * af for c, af in validas) / area_v
            peor[nombre] = max(peor[nombre], abs(media_f - plana["media"]))
            peor["cobertura"] = max(peor["cobertura"],
                                    abs(area_v / total_fisico - plana["cobertura_valida"]))
    return {"max_diferencia_" + k: v for k, v in peor.items()}


def controlar(dataset, salida, ruta_soporte_t02, ruta_catalogo_t02):
    import rasterio
    salida = Path(salida)
    filas = leer_csv(salida / "relieve_parcela.csv")
    celdas = leer_csv(salida / "relieve_celdas.csv")
    catalogo = leer_csv(ruta_catalogo_t02)
    conjunto = {c["id_parcela"]: c["conjunto_origen"] for c in catalogo}
    ids = [f["id_parcela"] for f in filas]
    if len(ids) != len(set(ids)) or set(ids) != set(conjunto):
        raise ValueError("IDs de T05 distintos del catálogo de T02")
    t02 = {c["id_parcela"]: {"elevacion": float(c["cobertura_elevacion"]),
                             "pendiente": float(c["cobertura_pendiente"])}
           for c in leer_csv(ruta_soporte_t02)}
    parcelas = leer_parcelas(buscar_unico(dataset, NOMBRE_SHP))
    with rasterio.open(buscar_unico(dataset, NOMBRE_ELEVACION)) as re_, \
         rasterio.open(buscar_unico(dataset, NOMBRE_PENDIENTE)) as rp:
        comprobar_relieve(re_, rp)
        areas = comparar_areas_fisicas(parcelas, re_, re_.read(1, masked=True),
                                       rp, rp.read(1, masked=True))
    c = {"parcelas": len(filas), "ids_coinciden_con_catalogo": True,
         "tablas": comprobar_tablas(filas, celdas),
         "reservadas": comprobar_reservadas(filas, conjunto),
         "conciliacion_t02": conciliar_con_t02(filas, t02),
         "areas_plana_frente_a_fisica": areas}
    avisos_ = []
    if c["reservadas"]["incompletas"]:
        avisos_.append("reservadas_con_cobertura_incompleta")
    if c["conciliacion_t02"]["discrepancias"] or c["conciliacion_t02"]["ids_solo_en_t02"] \
            or c["conciliacion_t02"]["ids_solo_en_t05"]:
        avisos_.append("discrepancia_con_t02")
    c["avisos"] = avisos_
    c["resultado"] = "aprobado" if not avisos_ else "aprobado_con_avisos_t05_no_cerrada"
    with open(salida / "controles.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(c, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return c


# ---------------------------------------------------------------------------
# Publicación y verificación (paso 6). La entrega compartida vive en registro/t05/.
# ---------------------------------------------------------------------------
ESQUEMA_ENTREGA = "t05_entrega_v1"
ARCHIVOS_ENTREGA = ("relieve_parcela.csv", "relieve_celdas.csv", "controles.json", "procedencia.json")
TOLERANCIA_REPRODUCCION = 1e-9   # Relativa (mínimo absoluto 1e-9) al comparar una nueva extracción.


def huella(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def escribir_json(ruta, objeto):
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        json.dump(objeto, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def versiones_entorno():
    import geopandas, numpy, pyogrio, pyproj, rasterio, shapely
    return {"python": sys.version.split()[0], "numpy": numpy.__version__,
            "rasterio": rasterio.__version__, "shapely": shapely.__version__,
            "pyproj": pyproj.__version__, "geopandas": geopandas.__version__,
            "pyogrio": pyogrio.__version__}


def procedencia(dataset):
    import rasterio
    dataset = Path(dataset)
    shp = buscar_unico(dataset, NOMBRE_SHP)
    fuentes = []
    for rol, ruta in [("parcelas_" + s[1:], shp.with_suffix(s)) for s in (".shp", ".shx", ".dbf", ".prj")] + \
                     [("elevacion", buscar_unico(dataset, NOMBRE_ELEVACION)),
                      ("pendiente", buscar_unico(dataset, NOMBRE_PENDIENTE))]:
        fuentes.append({"rol": rol, "archivo": ruta.relative_to(dataset).as_posix(),
                        "bytes": ruta.stat().st_size, "sha256": huella(ruta)})
    with rasterio.open(buscar_unico(dataset, NOMBRE_ELEVACION)) as r:
        cuadricula = {"crs": CRS_RELIEVE, "resolucion_m": [r.transform.a, -r.transform.e],
                      "columnas": r.width, "filas": r.height, "nodata": r.nodata,
                      "transformacion": list(r.transform)[:6]}
    return {"documento_metodo": "docs/t05_relieve.md", "decision_de_uso": "D020",
            "fuentes": fuentes, "cuadricula_relieve": cuadricula,
            "unidades": {"elevacion": "m s.n.m.", "pendiente": "grados"},
            "metodo_pendiente_declarado": "Horn 3x3 (LEEME de la entrega)",
            "parcelas": {"crs": CRS_PARCELAS, "columna_id_origen": COLUMNA_ID_SHP,
                         "columna_id": "id_parcela", "reproyeccion": CRS_RELIEVE},
            "metodo_area": METODO_AREA,
            "tolerancias": {"area_relativa": TOLERANCIA_AREA_REL, "cobertura_completa": TOLERANCIA_COMPLETA,
                            "conciliacion_t02": TOLERANCIA_T02, "reproduccion": TOLERANCIA_REPRODUCCION},
            "piso_pendiente_t10": PISO_PENDIENTE_T10,
            "codigo_sha256": {"scripts/t05_relieve.py": huella(Path(__file__))},
            "entorno": versiones_entorno()}


def publicar(dataset, origen, destino, ruta_soporte_t02, ruta_catalogo_t02):
    """Vuelve a controlar la extracción de `origen` y la publica en `destino` con manifiesto."""
    origen, destino = Path(origen), Path(destino)
    if destino.exists() and any(destino.iterdir()):
        raise ValueError("El destino debe ser una carpeta nueva o vacía")
    c = controlar(dataset, origen, ruta_soporte_t02, ruta_catalogo_t02)
    destino.mkdir(parents=True, exist_ok=True)
    for nombre in ("relieve_parcela.csv", "relieve_celdas.csv", "controles.json"):
        shutil.copyfile(origen / nombre, destino / nombre)
    escribir_json(destino / "procedencia.json", procedencia(dataset))
    celdas = leer_csv(destino / "relieve_celdas.csv")
    escribir_json(destino / "manifest.json", {
        "schema": ESQUEMA_ENTREGA,
        "nota": "Hashes de todos los archivos de entrega excepto este manifiesto.",
        "archivos_sha256": {n: huella(destino / n) for n in ARCHIVOS_ENTREGA},
        "parcelas": c["parcelas"], "celdas": len(celdas),
        "resultado_controles": c["resultado"]})
    return c


def _cabecera(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return next(csv.reader(f))


def _iguales(a, b):
    if a == b:
        return True
    try:
        x, y = float(a), float(b)
    except ValueError:
        return False
    return abs(x - y) <= max(1e-9, TOLERANCIA_REPRODUCCION * max(abs(x), abs(y)))


def comparar_extracciones(publicada, nueva):
    """Reproducción numérica: mismas filas y columnas; números dentro de la tolerancia."""
    for nombre, clave in (("relieve_parcela.csv", ("id_parcela",)),
                          ("relieve_celdas.csv", ("id_parcela", "fila", "columna"))):
        a, b = leer_csv(Path(publicada) / nombre), leer_csv(Path(nueva) / nombre)
        if len(a) != len(b):
            raise ValueError(f"Reproducción distinta: número de filas en {nombre}")
        for fa, fb in zip(a, b):
            if tuple(fa[k] for k in clave) != tuple(fb[k] for k in clave) or set(fa) != set(fb):
                raise ValueError(f"Reproducción distinta: filas o columnas en {nombre}")
            for col in fa:
                if not _iguales(fa[col], fb[col]):
                    raise ValueError(f"Reproducción distinta: {nombre} {fa[clave[0]]} {col}")


def verificar(carpeta, reproducir=False, dataset=None):
    """Integridad (hashes y estructura) y, si se pide, reproducción numérica."""
    carpeta = Path(carpeta)
    m = json.loads((carpeta / "manifest.json").read_text(encoding="utf-8"))
    if m.get("schema") != ESQUEMA_ENTREGA:
        raise ValueError("Esquema de entrega desconocido")
    if set(m["archivos_sha256"]) != set(ARCHIVOS_ENTREGA):
        raise ValueError("Lista de archivos de entrega incompatible")
    for nombre, valor in m["archivos_sha256"].items():
        if huella(carpeta / nombre) != valor:
            raise ValueError(f"Huella distinta: {nombre}")
    if tuple(_cabecera(carpeta / "relieve_parcela.csv")) != COLUMNAS_PARCELA or \
            tuple(_cabecera(carpeta / "relieve_celdas.csv")) != COLUMNAS_CELDA:
        raise ValueError("Columnas de entrega incompatibles")
    filas, celdas = leer_csv(carpeta / "relieve_parcela.csv"), leer_csv(carpeta / "relieve_celdas.csv")
    ids = [f["id_parcela"] for f in filas]
    if len(ids) != len(set(ids)) or len(ids) != m["parcelas"] or len(celdas) != m["celdas"]:
        raise ValueError("Conteos de entrega incompatibles con el manifiesto")
    comprobar_tablas(filas, celdas)
    controles = json.loads((carpeta / "controles.json").read_text(encoding="utf-8"))
    if controles["resultado"] != m["resultado_controles"]:
        raise ValueError("Resultado de controles distinto del manifiesto")
    resumen = {"resultado": "integridad_aprobada", "parcelas": len(ids), "celdas": len(celdas),
               "resultado_controles": controles["resultado"], "reproduccion": "no_solicitada"}
    if reproducir:
        with tempfile.TemporaryDirectory() as tmp:
            extraer(dataset, Path(tmp) / "nueva")
            comparar_extracciones(carpeta, Path(tmp) / "nueva")
        resumen["reproduccion"] = "aprobada"
    return resumen


def main(argv=None):
    ap = argparse.ArgumentParser(description="T05: relieve por parcela (docs/t05_relieve.md)")
    modo = ap.add_mutually_exclusive_group(required=True)
    modo.add_argument("--extraer", action="store_true")
    modo.add_argument("--controlar", action="store_true")
    modo.add_argument("--publicar", action="store_true")
    modo.add_argument("--verificar", metavar="CARPETA", help="Normalmente registro/t05")
    ap.add_argument("--dataset", default="data/raw/DATASET_RETO_AGRO_2026")
    ap.add_argument("--salida", help="Carpeta de extracción bajo data/processed/t05/")
    ap.add_argument("--destino", default="registro/t05")
    ap.add_argument("--reproducir", action="store_true",
                    help="Con --verificar: extrae de nuevo y compara con tolerancia")
    t02 = "analisis/auditoria_catalogo_y_etiquetas/tablas/"
    ap.add_argument("--soporte-t02", default=t02 + "soporte_por_parcela.csv")
    ap.add_argument("--catalogo-t02", default=t02 + "catalogo_parcelas.csv")
    a = ap.parse_args(argv)
    if a.verificar:
        print(json.dumps(verificar(a.verificar, a.reproducir, a.dataset), ensure_ascii=False, indent=2))
        return
    if not a.salida:
        ap.error("--salida es obligatoria con --extraer, --controlar y --publicar")
    if a.controlar or a.publicar:
        f = publicar if a.publicar else controlar
        args = (a.dataset, a.salida, a.destino) if a.publicar else (a.dataset, a.salida)
        c = f(*args, a.soporte_t02, a.catalogo_t02)
        print(json.dumps(c, ensure_ascii=False, indent=2, sort_keys=True))
        return
    filas, celdas = extraer(a.dataset, a.salida)
    estados = {}
    for f in filas:
        clave = (f["estado_elevacion"], f["estado_pendiente"])
        estados[clave] = estados.get(clave, 0) + 1
    print(f"Parcelas: {len(filas)} · celdas: {len(celdas)}")
    for (ee, ep), n in sorted(estados.items()):
        print(f"  elevación={ee} · pendiente={ep}: {n}")


if __name__ == "__main__":
    main()
