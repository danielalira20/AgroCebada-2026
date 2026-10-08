"""T04: entradas, soporte físico, extracción mensual y contraste por centroide.

Lee únicamente el maestro. El modo preparar verifica todos los insumos y pesos;
el modo muestra extrae una selección explícita. Piloto selecciona por geometría
y máscara; completa extrae y verifica las 197 parcelas en 48 meses.
"""
import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import itertools
import json
import math
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import time
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import rasterio
from pyproj import CRS, Transformer
from rasterio.io import MemoryFile
from shapely import segmentize
from shapely.geometry import box
from shapely.ops import transform as transformar

try:
    from .t04_espacio import (METODO_AREA, PASO_AREA_GRADOS, TOLERANCIA_AREA_REL,
                            aplicar_pesos, firma_cuadricula, huella_json,
                            identidad_soporte, preparar_pesos)
except ImportError:  # Entrada directa desde consola.
    from t04_espacio import (METODO_AREA, PASO_AREA_GRADOS, TOLERANCIA_AREA_REL,
                            aplicar_pesos, firma_cuadricula, huella_json,
                            identidad_soporte, preparar_pesos)

try:
    from .t04_control import (METODO_CENTROIDE, preparar_centroides, comparar_centroide,
                             seleccionar_piloto, controlar_medias, validar_exportacion)
except ImportError:
    from t04_control import (METODO_CENTROIDE, preparar_centroides, comparar_centroide,
                            seleccionar_piloto, controlar_medias, validar_exportacion)

try:
    from .t04_t02 import conciliar
except ImportError:
    from t04_t02 import conciliar

PREFIJO = "DATASET_RETO_AGRO_2026/"
GEOMETRIAS = PREFIJO + "Parcelas_Reto_AGC_CONJUNTO_70_30.zip"
CATALOGO = PREFIJO + "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"
ARCHIVOS_CLIMA = (
    PREFIJO + "Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip",
    PREFIJO + "Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS.zip",
)
VARIABLES = ("PREC", "Tmin", "Tmax")
PERIODOS = tuple(f"{a}-{m:02d}" for a in range(2022, 2026) for m in range(1, 13))
ESPERADOS = set(itertools.product(VARIABLES, PERIODOS))
PATRON = re.compile(r"(PREC|Tmin|Tmax)_(\d{4})_(\d{2})\.tif")
UNIDADES = {"PREC": "mm/mes", "Tmin": "grados Celsius", "Tmax": "grados Celsius"}
ETIQUETAS_VARIABLE = {"PREC": "Precipitacion", "Tmin": "Tmin", "Tmax": "Tmax"}
FUENTES = {"PREC": "CHIRPS", "Tmin": "CHIRTS-ERA5", "Tmax": "CHIRTS-ERA5"}
PASO_LAEA = 0.0001


def sha(datos):
    return hashlib.sha256(datos).hexdigest()


@dataclass(frozen=True)
class Cuadricula:
    crs: object
    transform: object
    width: int
    height: int
    count: int = 1


@dataclass
class Mapa:
    cuadricula: Cuadricula
    datos: np.ma.MaskedArray
    meta: dict


def validar_zip(archivo):
    nombres = [i.filename for i in archivo.infolist() if not i.is_dir()]
    if len(nombres) != len(set(nombres)):
        raise ValueError("ZIP con nombres de miembros duplicados")
    malo = archivo.testzip()
    if malo:
        raise ValueError(f"CRC incorrecto: {malo}")


def validar_catalogo(geo, catalogo, cantidad=197):
    if geo.crs is None or CRS.from_user_input(geo.crs) != CRS.from_epsg(4326):
        raise ValueError("Geometrías requieren CRS EPSG:4326")
    for tabla, campo in ((geo, "ID_POLIGON"), (catalogo, "ID_POLIGONO")):
        if campo not in tabla or len(tabla) != cantidad:
            raise ValueError(f"Catálogo/geometrías: cantidad o campo {campo} incorrecto")
        ids = tabla[campo]
        if ids.isna().any() or ids.duplicated().any() or any(not isinstance(x, str) or not x or x != x.strip() for x in ids):
            raise ValueError(f"ID ausente, duplicado o alterado en {campo}")
    if set(geo.ID_POLIGON) != set(catalogo.ID_POLIGONO):
        raise ValueError("IDs de geometrías y catálogo no corresponden")
    if geo.geometry.isna().any() or geo.geometry.is_empty.any() or not geo.geometry.is_valid.all():
        raise ValueError("Geometría vacía o inválida; no se repara automáticamente")
    if not geo.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise ValueError("Se requieren geometrías poligonales")
    areas = pd.to_numeric(catalogo.AREA_HA, errors="raise")
    if not np.isfinite(areas).all() or (areas <= 0).any():
        raise ValueError("Área declarada inválida")
    # Unión por identidad, nunca por posición; únicamente dos columnas del CSV.
    declarado = dict(zip(catalogo.ID_POLIGONO, areas))
    return [{"id_parcela": fila.ID_POLIGON, "geometria": fila.geometry,
             "area_ha_origen": float(declarado[fila.ID_POLIGON])}
            for fila in geo.sort_values("ID_POLIGON").itertuples()]


def leer_mapa(contenido, variable, periodo, referencia):
    with MemoryFile(contenido) as memoria, memoria.open() as r:
        if r.crs is None or CRS.from_user_input(r.crs) != CRS.from_epsg(4326) or r.count != 1:
            raise ValueError(f"Banda/CRS incompatible: {referencia}")
        t = r.transform
        if not all(math.isfinite(x) for x in t) or t.a <= 0 or t.e >= 0 or t.b or t.d:
            raise ValueError(f"Transformación no admisible: {referencia}")
        if r.nodata != -9999 or r.dtypes != ("float32",):
            raise ValueError(f"Tipo/NoData diferente del contrato: {referencia}")
        etiquetas = r.tags()
        for campo, esperado in (("Variable", ETIQUETAS_VARIABLE[variable]), ("Periodo", periodo),
                                ("Unidad", UNIDADES[variable]), ("Fuente", FUENTES[variable])):
            if etiquetas.get(campo) != esperado:
                raise ValueError(f"Metadato {campo} incorrecto: {referencia}")
        agregacion = "Suma de precipitación diaria" if variable == "PREC" else "Promedio mensual"
        if etiquetas.get("Agregacion") != agregacion:
            raise ValueError(f"Agregación diferente del contrato: {referencia}")
        datos = r.read(1, masked=True)
        validos = datos.compressed()
        if not np.isfinite(validos).all():
            raise ValueError(f"Valor válido no finito: {referencia}")
        if variable == "PREC" and (validos < 0).any():
            raise ValueError(f"Precipitación válida negativa: {referencia}")
        q = Cuadricula(r.crs, r.transform, r.width, r.height)
        meta = {"variable": variable, "periodo": periodo, "archivo": referencia,
                "sha256_raster": sha(contenido), "cuadricula": firma_cuadricula(q),
                "cuadricula_id": huella_json(firma_cuadricula(q)), "unidad": UNIDADES[variable],
                "nodata": r.nodata, "tipo": r.dtypes[0], "etiquetas": etiquetas,
                "celdas_validas": int(validos.size),
                "minimo": float(validos.min()) if validos.size else None,
                "maximo": float(validos.max()) if validos.size else None}
    # Se conserva la matriz pequeña; no se mantienen 144 archivos/handles abiertos.
    return Mapa(q, datos, meta)


def validar_claves_mapas(claves):
    contador = Counter(claves)
    faltantes, extras = sorted(ESPERADOS-set(contador)), sorted(set(contador)-ESPERADOS)
    duplicados = sorted(k for k, n in contador.items() if n != 1)
    if faltantes or extras or duplicados:
        raise ValueError(f"Mapas: faltantes={faltantes}; extras={extras}; duplicados={duplicados}")


def cargar_entradas(paquete):
    original = paquete.read_bytes()
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        validar_zip(z)
        geometria_zip = z.read(GEOMETRIAS)
        with zipfile.ZipFile(io.BytesIO(geometria_zip)) as gz:
            validar_zip(gz)
            miembros_geo = [{"archivo": f"DataSet.zip!/{GEOMETRIAS}!/{i.filename}",
                             "sha256": sha(gz.read(i))} for i in gz.infolist() if not i.is_dir()]
        geo = gpd.read_file(io.BytesIO(geometria_zip))
        catalogo_bytes = z.read(CATALOGO)
        cabecera = next(csv.reader(io.StringIO(catalogo_bytes.decode("utf-8-sig"))))
        if any(cabecera.count(c) != 1 for c in ("ID_POLIGONO", "AREA_HA")):
            raise ValueError("Columnas de catálogo ausentes o duplicadas")
        catalogo = pd.read_csv(io.BytesIO(catalogo_bytes), encoding="utf-8-sig",
                               usecols=["ID_POLIGONO", "AREA_HA"], dtype={"ID_POLIGONO": str})
        parcelas = validar_catalogo(geo, catalogo)
        mapas, claves = {}, []
        for interior in ARCHIVOS_CLIMA:
            with zipfile.ZipFile(io.BytesIO(z.read(interior))) as clima:
                validar_zip(clima)
                for i in sorted(clima.infolist(), key=lambda i: i.filename):
                    if i.is_dir() or not i.filename.lower().endswith(".tif"):
                        continue
                    match = PATRON.fullmatch(Path(i.filename).name)
                    if not match:
                        raise ValueError(f"TIFF climático inesperado: {i.filename}")
                    variable, anio, mes = match.groups()
                    periodo = f"{anio}-{mes}"
                    clave = (variable, periodo)
                    claves.append(clave)
                    if clave in mapas:
                        raise ValueError(f"Mapa duplicado: {clave}")
                    referencia = f"DataSet.zip!/{interior}!/{i.filename}"
                    mapas[clave] = leer_mapa(clima.read(i), variable, periodo, referencia)
        validar_claves_mapas(claves)
    avisos_cuadricula = []
    for periodo in PERIODOS:
        minima, maxima = mapas["Tmin", periodo], mapas["Tmax", periodo]
        if minima.meta["cuadricula_id"] != maxima.meta["cuadricula_id"]:
            avisos_cuadricula.append(f"{periodo}: Tmin/Tmax distintas; sin contraste celda a celda ni remuestreo")
            continue
        comunes = ~(np.ma.getmaskarray(minima.datos) | np.ma.getmaskarray(maxima.datos))
        if np.any(minima.datos.data[comunes] > maxima.datos.data[comunes]):
            raise ValueError(f"Tmin mayor que Tmax en celdas válidas: {periodo}")
    manifest = {"sha256_paquete": sha(original), "paquete": str(paquete.resolve()),
                "catalogo": {"archivo": f"DataSet.zip!/{CATALOGO}", "sha256": sha(catalogo_bytes),
                             "columnas_leidas": ["ID_POLIGONO", "AREA_HA"], "cantidad": len(parcelas)},
                "geometrias": {"sha256_zip": sha(geometria_zip), "miembros": miembros_geo,
                               "crs": geo.crs.to_wkt(), "tipos": dict(Counter(geo.geometry.geom_type)),
                               "parcelas_con_huecos": sum(any(p.interiors for p in (g.geoms if g.geom_type == "MultiPolygon" else [g])) for g in geo.geometry)},
                "mapas": [mapas[k].meta for k in sorted(mapas)],
                "avisos_cuadricula": avisos_cuadricula,
                "memoria_matrices_bytes": sum(m.datos.data.nbytes+np.ma.getmaskarray(m.datos).nbytes for m in mapas.values()),
                "version_producto": "no documentada", "disponibilidad_historica": "no documentada",
                "conciliacion_t02_aceptada": {"estado": "no_evaluada"}}
    return parcelas, mapas, manifest


def area_laea(geometria):
    cx, cy = geometria.centroid.coords[0]
    tr = Transformer.from_crs(4326, f"+proj=laea +lat_0={cy:.17g} +lon_0={cx:.17g} +ellps=WGS84 +units=m", always_xy=True)
    return transformar(tr.transform, segmentize(geometria, PASO_LAEA)).area


def preparar_soportes(parcelas, mapas):
    cuadriculas = {m.meta["cuadricula_id"]: m.cuadricula for m in mapas.values()}
    soportes, controles = {}, []
    for parcela in parcelas:
        geom, idp = parcela["geometria"], parcela["id_parcela"]
        independiente = area_laea(geom)
        for qid, q in sorted(cuadriculas.items()):
            s = preparar_pesos(geom, 4326, q, permitir_sin_cobertura=True)
            fino = preparar_pesos(geom, 4326, q, PASO_AREA_GRADOS/2, permitir_sin_cobertura=True)
            if [(c["fila"], c["columna"]) for c in s["celdas"]] != [(c["fila"], c["columna"]) for c in fino["celdas"]]:
                raise ValueError(f"Celdas distintas al refinar: {idp}/{qid}")
            diferencias = [abs(s["area_parcela_m2"]-fino["area_parcela_m2"])/fino["area_parcela_m2"],
                           abs(s["area_parcela_m2"]-independiente)/independiente]
            contraste_celdas = []
            for c, cf in zip(s["celdas"], fino["celdas"]):
                x0, y0 = q.transform @ (c["columna"], c["fila"])
                x1, y1 = q.transform @ (c["columna"]+1, c["fila"]+1)
                ai = area_laea(geom.intersection(box(x0, y1, x1, y0)))
                diferencia = max(abs(c["area_m2"]-cf["area_m2"])/cf["area_m2"], abs(c["area_m2"]-ai)/ai)
                diferencias.append(diferencia)
                contraste_celdas.append({"celda": c["celda"], "area_laea_m2": ai, "diferencia_rel": diferencia})
            if max(diferencias) > TOLERANCIA_AREA_REL:
                raise ValueError(f"Precisión física no aprobada: {idp}/{qid}, error={max(diferencias)}")
            if s["celdas"] and abs(math.fsum(c["peso_espacial"] for c in s["celdas"])-1) > 1e-12:
                raise ValueError(f"Pesos espaciales no suman uno: {idp}/{qid}")
            s.update(id_parcela=idp, area_ha_origen=parcela["area_ha_origen"], cuadricula_id=qid)
            soportes[idp, qid] = s
            controles.append({"id_parcela": idp, "cuadricula_id": qid, "area_laea_m2": independiente,
                              "error_rel_maximo": max(diferencias), "celdas": contraste_celdas})
    return soportes, controles


def extraer(parcelas, mapas, soportes, ids, periodos, centroides=None):
    ids, periodos = list(ids), list(periodos)
    universo = {p["id_parcela"] for p in parcelas}
    if not ids or not periodos or len(ids) != len(set(ids)) or len(periodos) != len(set(periodos)):
        raise ValueError("Selección vacía o duplicada")
    if set(ids)-universo or set(periodos)-set(PERIODOS):
        raise ValueError("ID o periodo solicitado ausente")
    por_id = {p["id_parcela"]: p for p in parcelas}
    centroides = preparar_centroides(parcelas, mapas) if centroides is None else centroides
    identidades = {}
    filas, celdas = [], []
    for variable, periodo in sorted(itertools.product(VARIABLES, periodos)):
        mapa = mapas[variable, periodo]
        qid = mapa.meta["cuadricula_id"]
        for idp in sorted(ids):
            soporte = soportes[idp, qid]
            if (idp, qid) not in identidades:
                identidades[idp, qid] = identidad_soporte(por_id[idp]["geometria"], 4326, mapa.cuadricula)
            if soporte["soporte_id"] != identidades[idp, qid]:
                raise ValueError(f"Identidad de soporte incompatible: {idp}/{variable}/{periodo}")
            resultado = aplicar_pesos(soporte, mapa.cuadricula, datos=mapa.datos, permitir_sin_cobertura=True)
            claves = {"id_parcela": idp, "periodo": periodo, "variable": variable,
                      "soporte_id": soporte["soporte_id"], "cuadricula_id": qid,
                      "sha256_raster": mapa.meta["sha256_raster"]}
            fila = {**claves, "unidad": mapa.meta["unidad"], "area_ha_origen": soporte["area_ha_origen"]}
            fila.update({k: resultado[k] for k in ("media_ponderada", "estado", "area_parcela_m2",
                        "area_intersectada_m2", "area_valida_m2", "area_nodata_m2",
                        "cobertura_espacial_completa", "cobertura_espacial_bruta", "area_fuera_mapa_m2",
                        "cobertura_valida_bruta", "cobertura_valida")})
            fila["motivo"] = {"cobertura_completa": "geometría cubierta y todas sus celdas válidas",
                               "cobertura_parcial": ("geometría fuera del mapa y celdas NoData" if not resultado["cobertura_espacial_completa"] and resultado["area_nodata_m2"] > 0
                                  else "geometría fuera del mapa" if not resultado["cobertura_espacial_completa"]
                                  else "celdas NoData"),
                               "todo_nodata": "intersecciones positivas sin datos válidos",
                               "sin_cobertura_espacial": "sin intersecciones de área positiva"}[resultado["estado"]]
            fila.update(comparar_centroide(centroides[idp, qid], mapa, resultado["media_ponderada"]))
            filas.append(fila)
            celdas.extend({**claves, **c} for c in resultado["celdas"])
    esperadas = set(itertools.product(ids, periodos, VARIABLES))
    obtenidas = [(r["id_parcela"], r["periodo"], r["variable"]) for r in filas]
    if len(obtenidas) != len(esperadas) or set(obtenidas) != esperadas:
        raise ValueError("Claves de extracción incompletas o duplicadas")
    return sorted(filas, key=lambda r: (r["id_parcela"], r["periodo"], r["variable"])), celdas


def escribir_csv(ruta, filas, columnas=None):
    columnas = columnas or list(filas[0])
    with ruta.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)  # float repr conserva precisión; None es campo vacío.


def escribir_json(ruta, objeto):
    ruta.write_text(json.dumps(objeto, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def publicar_local(salida, manifest, soportes, controles, filas=None, valores=None, *, mapas=None, controles_medias=None, verificar=False):
    """Publicación local atómica: sólo aparece una carpeta final tras guardar todo."""
    if salida.exists():
        raise FileExistsError(f"La ejecución ya existe: {salida}")
    salida.parent.mkdir(parents=True, exist_ok=True)
    temporal = Path(tempfile.mkdtemp(prefix=".t04-incompleto-", dir=salida.parent))
    try:
        escribir_json(temporal/"manifest.json", manifest)
        escribir_json(temporal/"soportes.json", list(soportes.values()))
        escribir_json(temporal/"controles_soporte.json", {"tolerancia_area_rel": TOLERANCIA_AREA_REL,
                      "paso_laea_grados": PASO_LAEA, "resultados": controles})
        detalle = [{"id_parcela": s["id_parcela"], "soporte_id": s["soporte_id"],
                    "cuadricula_id": s["cuadricula_id"], "geometria_sha256": s["geometria_sha256"],
                    "metodo_area": s["metodo_area"], "paso_area_grados": s["paso_area_grados"], **c}
                   for s in soportes.values() for c in s["celdas"]]
        escribir_csv(temporal/"soporte_celdas.csv", detalle, ["id_parcela", "soporte_id", "cuadricula_id",
                      "geometria_sha256", "metodo_area", "paso_area_grados", "fila", "columna", "celda", "area_m2", "peso_espacial"])
        if filas is not None:
            escribir_csv(temporal/"clima_parcela_mes.csv", filas)
            escribir_csv(temporal/"valores_celdas.csv", valores, ["id_parcela", "periodo", "variable", "soporte_id",
                          "cuadricula_id", "sha256_raster", "fila", "columna", "celda", "area_m2",
                          "peso_espacial", "valida", "valor", "peso_valido"])
        verificacion = validar_exportacion(temporal, mapas) if verificar and filas is not None else None
        if verificacion:
            escribir_json(temporal/"controles.json", {"exportacion": verificacion, "medias": controles_medias})
        escribir_json(temporal/"estado.json", {"estado": "extraccion_verificada_local" if verificacion else "preparacion_local",
                      "alcance": manifest["alcance"], "filas_clima": len(filas) if filas is not None else 0,
                      "cierre_t04": False})
        temporal.rename(salida)
    finally:
        if temporal.exists():
            shutil.rmtree(temporal)


def ejecutar(paquete, salida, ids=None, periodos=None, modo=None, referencia_t02=None):
    inicio = time.perf_counter()
    repo = Path(__file__).resolve().parents[1]
    base = (repo/"data/processed/t04").resolve()
    destino = salida.resolve()
    if not destino.is_relative_to(base) or destino == base:
        raise ValueError("Salida debe ser una ejecución nueva bajo data/processed/t04/")
    if destino.exists():
        raise FileExistsError(f"La ejecución ya existe: {destino}")
    modo = modo or ("muestra" if ids else "preparacion")
    if modo not in ("preparacion", "muestra", "piloto", "completa"):
        raise ValueError("Modo desconocido")
    if modo in ("piloto", "completa") and (ids or periodos):
        raise ValueError("Piloto/completa definen su selección; no admiten IDs/periodos manuales")
    if bool(ids) != bool(periodos):
        raise ValueError("Para muestra se requieren IDs y periodos juntos")
    parcelas, mapas, manifest = cargar_entradas(paquete)
    soportes, controles = preparar_soportes(parcelas, mapas)
    centroides = preparar_centroides(parcelas, mapas)
    referencia_t02 = referencia_t02 or repo/"registro/referencia_t02_t04.json"
    conciliacion = conciliar(parcelas, mapas, soportes, centroides, manifest, referencia_t02, repo)
    manifest["conciliacion_t02_aceptada"] = conciliacion
    seleccion_piloto = None
    if modo == "piloto":
        ids, periodos, seleccion_piloto = seleccionar_piloto(parcelas, mapas, soportes, centroides)
    elif modo == "completa":
        ids, periodos = [p["id_parcela"] for p in parcelas], list(PERIODOS)
    manifest.update(modo=modo, metodo_centroide=METODO_CENTROIDE, seleccion_piloto=seleccion_piloto, fecha_utc=datetime.now(timezone.utc).isoformat(), metodo_area=METODO_AREA,
                    paso_area_grados=PASO_AREA_GRADOS,
                    dependencias={n: importlib.metadata.version(n) for n in ("numpy", "rasterio", "shapely", "pyproj", "geopandas", "pandas", "affine", "pyogrio")},
                    bibliotecas_nativas={"PROJ": pyproj.proj_version_str, "GDAL": rasterio.__gdal_version__},
                    requirements_sha256=sha((repo/"requirements.txt").read_bytes()),
                    python=platform.python_version(), sistema=platform.system(), arquitectura=platform.machine(),
                    codigo={p.name: sha(p.read_bytes()) for p in (Path(__file__), Path(__file__).with_name("t04_espacio.py"), Path(__file__).with_name("t04_control.py"), Path(__file__).with_name("t04_t02.py"))},
                    commit_base=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
                    cuadriculas=len({m.meta["cuadricula_id"] for m in mapas.values()}), soportes=len(soportes),
                    parametros={"tolerancia_area_rel": TOLERANCIA_AREA_REL, "tolerancia_suma_pesos_abs": 1e-12,
                                "tolerancia_media_refinamiento_abs": 1e-6, "paso_laea_grados": PASO_LAEA},
                    alcance={"preparacion": "entradas y soporte; sin extracción mensual", "muestra": "muestra técnica explícita", "piloto": "piloto seleccionado por geometría y máscaras", "completa": "197 parcelas × 48 meses × 3 variables; extracción histórica descriptiva"}[modo],
                    seleccion={"ids": sorted(ids or []), "periodos": sorted(periodos or [])},
                    pendientes=["reproducción entre ejecuciones", "revisión Dani/Jass de esta entrega"] + ([] if conciliacion["estado"] == "conciliada_con_referencia_identificada" else ["conciliación T02 no disponible"]))
    filas, valores = extraer(parcelas, mapas, soportes, ids, periodos, centroides) if ids else (None, None)
    control_medias = controlar_medias(parcelas, mapas, soportes, controles, filas) if filas is not None else None
    manifest["tiempo_calculo_segundos"] = time.perf_counter()-inicio
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        manifest["memoria_proceso_pico_bytes"] = rss if platform.system() == "Darwin" else rss*1024
    except ImportError:
        manifest["memoria_proceso_pico_bytes"] = None
    publicar_local(destino, manifest, soportes, controles, filas, valores, mapas=mapas,
                   controles_medias=control_medias, verificar=True)
    return {"mapas": len(mapas), "parcelas": len(parcelas), "cuadriculas": manifest["cuadriculas"],
            "soportes": len(soportes), "filas_muestra": len(filas) if filas is not None else 0,
            "error_area_rel_maximo": max(c["error_rel_maximo"] for c in controles), "salida": str(destino)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--paquete", required=True, type=Path)
    p.add_argument("--salida", required=True, type=Path)
    p.add_argument("--referencia-t02", type=Path, help="Referencia espacial identificada; por defecto registro/referencia_t02_t04.json")
    p.add_argument("--ids", nargs="+")
    p.add_argument("--periodos", nargs="+")
    opciones = p.add_mutually_exclusive_group()
    opciones.add_argument("--piloto", action="store_true")
    opciones.add_argument("--completa", action="store_true")
    args = p.parse_args()
    print(json.dumps(ejecutar(args.paquete, args.salida, args.ids, args.periodos, "piloto" if args.piloto else "completa" if args.completa else None, args.referencia_t02), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
