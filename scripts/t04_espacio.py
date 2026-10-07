"""T04: núcleo espacial compartido; conserva la comprobación de fase 2.

Intersecciones en la cuadrícula WGS84 original; áreas elipsoidales en m².
Los bordes lineales en lon/lat se densifican sólo para integrar el área.
No modifica geometrías, imágenes, particiones ni decide umbrales de calidad.
"""

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import geopandas as gpd
import numpy as np
from pyproj import CRS, Geod
from rasterio.io import MemoryFile
from shapely import segmentize
from shapely.geometry import box

GEOD = Geod(ellps="WGS84")
PASO_AREA_GRADOS = 0.0005
TOLERANCIA_AREA_REL = 1e-6
METODO_AREA = "wgs84_borde_lineal_cuadratura8_v2"
# Gauss–Legendre con transformación triangular (Duffy), sólo numpy existente.
_NODOS, _PESOS = np.polynomial.legendre.leggauss(8)
_U = ((_NODOS+1)/2)[:, None]
_V = ((_NODOS+1)/2)[None, :]
_PESOS_TRIANGULO = (_PESOS[:, None]*_PESOS[None, :]/4)*(1-_U)
_E2 = GEOD.f*(2-GEOD.f)


def _area_anillo(coordenadas):
    """Integra MN cos(lat) dlon dlat sobre un abanico de triángulos con signo.

    M,N son radios de curvatura WGS84. Las diferencias se toman en grados
    ANTES de convertir a radianes, evitando restar áreas geodésicas grandes
    para resolver intersecciones milimétricas. El abanico con signo también
    integra anillos cóncavos; los huecos se restan separadamente.
    """
    coords = np.asarray(coordenadas, dtype=float)[:, :2]
    origen = coords[0]
    a, b = coords[1:-1]-origen, coords[2:]-origen
    determinantes = a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]
    lat = np.deg2rad(origen[1]+a[:, 1, None, None]*_U
                    +b[:, 1, None, None]*(1-_U)*_V)
    densidad = GEOD.a**2*(1-_E2)*np.cos(lat)/(1-_E2*np.sin(lat)**2)**2
    integrales = np.sum(densidad*_PESOS_TRIANGULO, axis=(1, 2))
    return abs(math.fsum((determinantes*integrales).tolist())*(math.pi/180)**2)


def huella_json(valor):
    return hashlib.sha256(json.dumps(valor, sort_keys=True, allow_nan=False,
                                    separators=(",", ":")).encode()).hexdigest()


def identidad_soporte(geometria, crs_parcela, raster, paso=PASO_AREA_GRADOS):
    return huella_json({"geometria_sha256": hashlib.sha256(geometria.wkb).hexdigest(),
                       "crs_parcela": CRS.from_user_input(crs_parcela).to_wkt(),
                       "cuadricula": firma_cuadricula(raster),
                       "metodo": METODO_AREA, "paso_area_grados": paso})


def area_fisica(geometria, paso=PASO_AREA_GRADOS):
    """Área WGS84 por integración de bordes nativos; líneas/puntos aportan cero.

    Ámbito regional, sin cruce de antimeridiano. El paso aproxima el borde
    lineal nativo mediante subdivisión para controlar convergencia; no remuestrea
    el ráster. La integración estable reemplaza Geod en áreas diminutas.
    """
    if not math.isfinite(paso) or paso <= 0:
        raise ValueError("Paso de área no admisible")
    if geometria.is_empty:
        return 0.0
    if geometria.geom_type == "Polygon":
        p = segmentize(geometria, paso)
        return _area_anillo(p.exterior.coords)-math.fsum(_area_anillo(h.coords) for h in p.interiors)
    if geometria.geom_type in ("MultiPolygon", "GeometryCollection"):
        return math.fsum(area_fisica(g, paso) for g in geometria.geoms)
    return 0.0


def firma_cuadricula(raster):
    return {"crs": raster.crs.to_wkt() if raster.crs else None,
            "columnas": raster.width, "filas": raster.height,
            "transformacion": list(raster.transform)[:6]}


def preparar_pesos(geometria, crs_parcela, raster, paso=PASO_AREA_GRADOS, *,
                   permitir_sin_cobertura=False):
    """Conserva todas las intersecciones con área positiva, independientemente de NoData."""
    if crs_parcela is None or raster.crs is None:
        raise ValueError("CRS ausente")
    if CRS.from_user_input(crs_parcela) != CRS.from_user_input(raster.crs):
        raise ValueError("CRS incompatible entre parcela y ráster")
    if CRS.from_user_input(raster.crs) != CRS.from_epsg(4326):
        raise ValueError("Esta comprobación requiere EPSG:4326")
    if geometria.geom_type not in ("Polygon", "MultiPolygon") or geometria.is_empty or not geometria.is_valid:
        raise ValueError("Geometría parcelaria no admisible")
    xmin, ymin, xmax, ymax = geometria.bounds
    if not (-180 <= xmin <= xmax <= 180 and -90 < ymin <= ymax < 90) or xmax-xmin > 180:
        raise ValueError("Geometría fuera del ámbito regional WGS84")
    t = raster.transform
    if not all(math.isfinite(x) for x in t) or t.a <= 0 or t.e >= 0 or t.b != 0 or t.d != 0:
        raise ValueError("Cuadrícula rotada o transformación no admisible")
    area = area_fisica(geometria, paso)
    if not math.isfinite(area) or area <= 0:
        raise ValueError("Área parcelaria no admisible")
    # Ventana acotada: se incluyen los contactos exactos para probar que no aportan área.
    col0, col1 = max(0, math.floor((xmin-t.c)/t.a)-1), min(raster.width, math.floor((xmax-t.c)/t.a)+2)
    row0, row1 = max(0, math.floor((ymax-t.f)/t.e)-1), min(raster.height, math.floor((ymin-t.f)/t.e)+2)
    celdas = []
    for fila in range(row0, row1):
        for columna in range(col0, col1):
            x0, y0 = t @ (columna, fila)
            x1, y1 = t @ (columna+1, fila+1)
            inter = geometria.intersection(box(x0, y1, x1, y0))
            if inter.is_empty or inter.area == 0:
                continue
            a = area_fisica(inter, paso)
            if not math.isfinite(a) or a <= 0:
                raise ValueError("Área de intersección no admisible")
            celdas.append({"fila": fila, "columna": columna,
                           "celda": f"{fila}_{columna}", "area_m2": a})
    total = math.fsum(c["area_m2"] for c in celdas)
    if total == 0 and not permitir_sin_cobertura:
        raise ValueError("Parcela sin cobertura espacial")
    if total > area*(1+TOLERANCIA_AREA_REL):
        raise ValueError("Intersecciones exceden el área parcelaria")
    for celda in celdas:
        celda["peso_espacial"] = celda["area_m2"]/total
    x0, y0 = t @ (0, 0)
    x1, y1 = t @ (raster.width, raster.height)
    completa = box(x0, y1, x1, y0).covers(geometria)
    return {"soporte_id": identidad_soporte(geometria, crs_parcela, raster, paso),
            "metodo_area": METODO_AREA,
            "crs_parcela": CRS.from_user_input(crs_parcela).to_wkt(),
            "cuadricula": firma_cuadricula(raster),
            "cobertura_espacial_completa": completa,
            "cobertura_espacial_bruta": total/area,
            "area_fuera_mapa_m2": 0.0 if completa else max(0.0, area-total),
            "geometria_sha256": hashlib.sha256(geometria.wkb).hexdigest(),
            "paso_area_grados": paso, "area_parcela_m2": area,
            "area_intersectada_m2": total, "celdas": celdas}


def aplicar_pesos(soporte, raster, *, datos=None, permitir_sin_cobertura=False):
    """Comprueba identidad de cuadrícula; renormaliza sólo entre áreas válidas del mapa."""
    if firma_cuadricula(raster) != soporte["cuadricula"]:
        raise ValueError("Cuadrícula distinta: recalcular pesos")
    if raster.count != 1:
        raise ValueError("Se requiere una banda")
    if soporte["metodo_area"] != METODO_AREA:
        raise ValueError("Método de soporte incompatible")
    esperado = huella_json({"geometria_sha256": soporte["geometria_sha256"],
                            "crs_parcela": soporte["crs_parcela"],
                            "cuadricula": soporte["cuadricula"],
                            "metodo": soporte["metodo_area"],
                            "paso_area_grados": soporte["paso_area_grados"]})
    if soporte["soporte_id"] != esperado:
        raise ValueError("Identidad o parámetros del soporte alterados")
    if datos is None:
        datos = raster.read(1, masked=True)
    if not np.ma.isMaskedArray(datos) or datos.shape != (raster.height, raster.width):
        raise ValueError("Datos y máscara no corresponden a la cuadrícula")
    celdas = []
    for celda in soporte["celdas"]:
        valor = datos[celda["fila"], celda["columna"]]
        valido = not np.ma.is_masked(valor)
        if valido and not np.isfinite(valor):
            raise ValueError("Valor válido no finito")
        celdas.append({**celda, "valida": valido,
                       "valor": float(valor) if valido else None})
    area_valida = math.fsum(c["area_m2"] for c in celdas if c["valida"])
    if area_valida == 0 and not permitir_sin_cobertura:
        raise ValueError("Parcela sin cobertura válida: todo NoData")
    for celda in celdas:
        celda["peso_valido"] = celda["area_m2"]/area_valida if celda["valida"] and area_valida else 0.0
    media = (math.fsum(c["valor"]*c["peso_valido"] for c in celdas if c["valida"])
             if area_valida else None)
    if not soporte["celdas"]:
        estado = "sin_cobertura_espacial"
    elif not area_valida:
        estado = "todo_nodata"
    elif soporte["cobertura_espacial_completa"] and all(c["valida"] for c in celdas):
        estado = "cobertura_completa"
    else:
        estado = "cobertura_parcial"
    if media is not None:
        validas = [c for c in celdas if c["valida"]]
        if abs(math.fsum(c["peso_valido"] for c in validas)-1) > 1e-12:
            raise ValueError("Pesos válidos no suman uno")
        if not min(c["valor"] for c in validas)-1e-12 <= media <= max(c["valor"] for c in validas)+1e-12:
            raise ValueError("Media fuera del rango válido")
    cobertura = area_valida/soporte["area_parcela_m2"]
    return {**soporte, "celdas": celdas, "estado": estado, "media_ponderada": media,
            "area_valida_m2": area_valida,
            "area_nodata_m2": soporte["area_intersectada_m2"]-area_valida,
            "cobertura_valida_bruta": cobertura,
            "cobertura_valida": min(1.0, cobertura)}


def comprobar_reales(paquete):
    """Lee las geometrías y seis mapas de julio directamente del maestro."""
    with zipfile.ZipFile(paquete) as exterior:
        def interior(nombre):
            return zipfile.ZipFile(io.BytesIO(exterior.read("DATASET_RETO_AGRO_2026/"+nombre)))
        geo = gpd.read_file(io.BytesIO(exterior.read("DATASET_RETO_AGRO_2026/Parcelas_Reto_AGC_CONJUNTO_70_30.zip")))
        resultados = []
        with interior("Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip") as lluvia, interior("Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS.zip") as temp:
            for id_parcela in ("AGC_014", "AGC_065"):
                filas = geo[geo.ID_POLIGON == id_parcela]
                if len(filas) != 1:
                    raise ValueError(f"ID ausente o duplicado: {id_parcela}")
                geom = filas.geometry.item()
                cache = {}
                for variable, z, miembro in (
                    ("PREC", lluvia, "Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025/Precipitacion_mensual/2025/PREC_2025_07.tif"),
                    ("Tmin", temp, "Reto_AgroCebada_Temperatura_2022_2025/Tmin/2025/Tmin_2025_07.tif"),
                    ("Tmax", temp, "Reto_AgroCebada_Temperatura_2022_2025/Tmax/2025/Tmax_2025_07.tif")):
                    contenido = z.read(miembro)
                    with MemoryFile(contenido) as memoria, memoria.open() as raster:
                        firma = json.dumps(firma_cuadricula(raster), sort_keys=True)
                        reutilizado = firma in cache
                        if not reutilizado:
                            cache[firma] = preparar_pesos(geom, geo.crs, raster)
                        calculo = aplicar_pesos(cache[firma], raster)
                        fino = preparar_pesos(geom, geo.crs, raster, PASO_AREA_GRADOS/2)
                        media_fina = aplicar_pesos(fino, raster)["media_ponderada"]
                        if abs(fino["area_parcela_m2"]-calculo["area_parcela_m2"])/calculo["area_parcela_m2"] > TOLERANCIA_AREA_REL or abs(media_fina-calculo["media_ponderada"]) > 1e-6:
                            raise ValueError("Control de convergencia no aprobado; revisar integración de áreas")
                    resultados.append({"id_parcela": id_parcela, "variable": variable,
                        "periodo": "2025-07", "miembro_original": miembro,
                        "sha256_raster": hashlib.sha256(contenido).hexdigest(),
                        "pesos_reutilizados": reutilizado,
                        "convergencia_media_diferencia": abs(media_fina-calculo["media_ponderada"]),
                        "convergencia_area_diferencia_m2": abs(fino["area_parcela_m2"]-calculo["area_parcela_m2"]),
                        **calculo})
    return {"alcance": "Dos ejemplos de fase 2; no entrega climática final de 197 IDs",
            "sha256_paquete": hashlib.sha256(paquete.read_bytes()).hexdigest(),
            "metodo_area": METODO_AREA,
            "resultados": resultados}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paquete", required=True, type=Path)
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()
    if args.salida.resolve() == args.paquete.resolve():
        parser.error("La salida no puede sobrescribir el paquete")
    informe = comprobar_reales(args.paquete)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    print(json.dumps([{k:r[k] for k in ("id_parcela", "variable", "media_ponderada", "cobertura_valida")} for r in informe["resultados"]], indent=2))


if __name__ == "__main__":
    main()
