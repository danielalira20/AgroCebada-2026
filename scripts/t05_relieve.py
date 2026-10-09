"""T05 · Relieve por parcela: funciones puras de extracción.

El método está en docs/t05_relieve.md. Aquí no se leen archivos: las funciones
reciben la geometría ya proyectada al CRS del ráster (EPSG:6372, cuadrícula
proyectada en metros) y un ráster abierto. Las áreas son planas en ese sistema.

Diferencia deliberada con scripts/t04_espacio.py: una parcela sin cobertura
espacial o con todo NoData no lanza error; recibe un estado y sus valores
quedan vacíos.
"""
import math

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
