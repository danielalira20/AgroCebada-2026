"""T04: centroide, piloto por geometría/máscaras y controles de tablas exportadas."""
from bisect import bisect_right
from collections import Counter, defaultdict
import csv
import itertools
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

try:
    from .t04_espacio import aplicar_pesos, preparar_pesos
except ImportError:
    from t04_espacio import aplicar_pesos, preparar_pesos

VARIABLES = ("PREC", "Tmin", "Tmax")
TOL_PESOS = 1e-12
TOL_RECONSTRUCCION = 1e-12
TOL_MEDIA = 1e-6
METODO_CENTROIDE = "centroide_epsg6372_a_4326_v1_limites_nativos"


def celda_punto(x, y, q):
    """Intervalos nativos equivalentes a floor; bordes internos derecha/abajo.

    La búsqueda compara contra los bordes representables originales. Evita
    convertir un borde exacto en 0.99999999999994 por inversión de la affine.
    No redondea/desplaza el punto ni usa una tolerancia espacial.
    """
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("Centroide no finito")
    t = q.transform
    if t.b or t.d or t.a <= 0 or t.e >= 0:
        raise ValueError("Centroide requiere cuadrícula nativa norte-arriba")
    columna = bisect_right([t.c+t.a*c for c in range(q.width+1)], x)-1
    fila = bisect_right([-(t.f+t.e*f) for f in range(q.height+1)], -y)-1
    return fila, columna


def preparar_centroides(parcelas, mapas):
    geometria = gpd.GeoSeries([p["geometria"] for p in parcelas], crs=4326)
    puntos = geometria.to_crs(6372).centroid.to_crs(4326)
    cuadriculas = {m.meta["cuadricula_id"]: m.cuadricula for m in mapas.values()}
    resultado = {}
    for p, punto in zip(parcelas, puntos):
        for qid, q in cuadriculas.items():
            f, c = celda_punto(punto.x, punto.y, q)
            resultado[p["id_parcela"], qid] = {
                "centroide_lon": punto.x, "centroide_lat": punto.y,
                "centroide_dentro_parcela": p["geometria"].covers(punto),
                "fila_centroide": f, "columna_centroide": c,
                "centroide_en_mapa": 0 <= f < q.height and 0 <= c < q.width}
    return resultado


def comparar_centroide(centroide, mapa, media):
    valor = None
    if not centroide["centroide_en_mapa"]:
        estado = "fuera_raster"
    else:
        d = mapa.datos[centroide["fila_centroide"], centroide["columna_centroide"]]
        if np.ma.is_masked(d):
            estado = "nodata"
        else:
            if not np.isfinite(d):
                raise ValueError("Valor válido del centroide no finito")
            estado, valor = "valido", float(d)
    diferencia = media-valor if media is not None and valor is not None else None
    return {**centroide, "estado_centroide": estado, "valor_centroide": valor,
            "diferencia_media_menos_centroide": diferencia,
            "diferencia_abs_centroide": abs(diferencia) if diferencia is not None else None}


def seleccionar_piloto(parcelas, mapas, soportes, centroides):
    """Selecciona usando geometría/soporte/máscaras, nunca valores ni etiquetas."""
    razones = defaultdict(list)
    def agregar(idp, razon):
        razones[idp].append(razon)
    por_id = {p["id_parcela"]: p for p in parcelas}
    for idp in ("AGC_014", "AGC_065"):
        if idp in por_id:
            agregar(idp, "referencia de fase 2")
    todos = sorted(soportes.values(), key=lambda s: (s["id_parcela"], s["cuadricula_id"]))
    if not todos:
        raise ValueError("Piloto sin soporte")
    agregar(min(todos, key=lambda s: (s["area_parcela_m2"], s["id_parcela"]))["id_parcela"], "menor área geométrica")
    agregar(min(todos, key=lambda s: (-s["area_parcela_m2"], s["id_parcela"]))["id_parcela"], "mayor área geométrica")
    agregar(min(todos, key=lambda s: (-len(s["celdas"]), s["id_parcela"]))["id_parcela"], "mayor número de celdas")
    positivos = [(c["area_m2"], s["id_parcela"]) for s in todos for c in s["celdas"]]
    if positivos:
        agregar(min(positivos)[1], "menor intersección positiva")
    for idp in ("AGC_143", "AGC_191"):
        if idp in por_id:
            agregar(idp, "caso investigado en control de precisión")
    especiales = {
        "multiparte": [p["id_parcela"] for p in parcelas if p["geometria"].geom_type == "MultiPolygon"],
        "huecos": [p["id_parcela"] for p in parcelas if any(g.interiors for g in (p["geometria"].geoms if p["geometria"].geom_type == "MultiPolygon" else [p["geometria"]]))],
        "centroide fuera de parcela": sorted({idp for (idp, _), c in centroides.items() if not c["centroide_dentro_parcela"]}),
        "sin cobertura espacial": sorted({s["id_parcela"] for s in todos if not s["celdas"]}),
        "cobertura espacial parcial": sorted({s["id_parcela"] for s in todos if s["celdas"] and not s["cobertura_espacial_completa"]})}
    periodos = {"2025-07"}
    for anio in ("2022", "2023", "2024"):
        periodos.add(min(m.meta["periodo"] for m in mapas.values() if m.meta["periodo"].startswith(anio)))
    ausencia = defaultdict(list)
    for (variable, periodo), m in sorted(mapas.items()):
        mascara = np.ma.getmaskarray(m.datos)
        for p in parcelas:
            s = soportes[p["id_parcela"], m.meta["cuadricula_id"]]
            validas = sum(not mascara[c["fila"], c["columna"]] for c in s["celdas"])
            if s["celdas"] and validas < len(s["celdas"]):
                tipo = "todo NoData" if validas == 0 else "NoData parcial"
                ausencia[tipo].append((p["id_parcela"], periodo, variable))
    for razon, ids in especiales.items():
        if ids:
            agregar(min(ids), razon)
    for razon, candidatos in ausencia.items():
        idp, periodo, _ = min(candidatos)
        agregar(idp, razon)
        periodos.add(periodo)
    cambios_mascara = {}
    for v in VARIABLES:
        ms = sorted((m for (vv, _), m in mapas.items() if vv == v), key=lambda m: m.meta["periodo"])
        for extremo in (min, max):
            elegido = extremo(ms, key=lambda m: (m.meta["celdas_validas"], m.meta["periodo"]))
            periodos.add(elegido.meta["periodo"])
        primero = np.ma.getmaskarray(ms[0].datos)
        cambios = [m.meta["periodo"] for m in ms[1:] if m.datos.shape != ms[0].datos.shape or not np.array_equal(primero, np.ma.getmaskarray(m.datos))]
        cambios_mascara[v] = cambios
        if cambios:
            periodos.update([ms[0].meta["periodo"], cambios[0]])
    return sorted(razones), sorted(periodos), {
        "criterio": "selección por geometría, soportes y máscaras antes de extraer medias; desempate por ID/periodo",
        "razones_por_id": dict(sorted(razones.items())), "periodos": sorted(periodos),
        "casos_no_existentes_en_originales": [k for k, x in especiales.items() if not x]+[k for k in ("todo NoData", "NoData parcial") if not ausencia[k]],
        "cambios_mascara_respecto_primer_mes": cambios_mascara}


def controlar_medias(parcelas, mapas, soportes, areas_control, filas):
    """Contraste independiente LAEA y paso refinado, en cada fila solicitada."""
    geometrias = {p["id_parcela"]: p["geometria"] for p in parcelas}
    finos, areas = {}, {(a["id_parcela"], a["cuadricula_id"]): {c["celda"]: c["area_laea_m2"] for c in a["celdas"]} for a in areas_control}
    max_fino, max_laea, peor_fino, peor_laea = 0.0, 0.0, None, None
    for r in filas:
        clave = r["id_parcela"], r["cuadricula_id"]
        m = mapas[r["variable"], r["periodo"]]
        if clave not in finos:
            finos[clave] = preparar_pesos(geometrias[clave[0]], 4326, m.cuadricula, .00025, permitir_sin_cobertura=True)
        refinado = aplicar_pesos(finos[clave], m.cuadricula, datos=m.datos, permitir_sin_cobertura=True)["media_ponderada"]
        validas = [(areas[clave][c["celda"]], float(m.datos[c["fila"], c["columna"]])) for c in soportes[clave]["celdas"] if not np.ma.is_masked(m.datos[c["fila"], c["columna"]])]
        total = math.fsum(a for a, _ in validas)
        independiente = math.fsum(a/total*v for a, v in validas) if total else None
        media = r["media_ponderada"]
        if media is None:
            if refinado is not None or independiente is not None:
                raise ValueError(f"Ausencia inconsistente: {clave}")
            continue
        df, dl = abs(media-refinado), abs(media-independiente)
        identidad = {k: r[k] for k in ("id_parcela", "variable", "periodo")}
        if df > max_fino:
            max_fino, peor_fino = df, identidad
        if dl > max_laea:
            max_laea, peor_laea = dl, identidad
        if df > TOL_MEDIA or dl > TOL_MEDIA:
            raise ValueError(f"Contraste de media no aprobado: {identidad}, fino={df}, LAEA={dl}")
    return {"filas_comprobadas": len(filas), "tolerancia_media_abs": TOL_MEDIA,
            "max_diferencia_refinamiento": max_fino, "peor_refinamiento": peor_fino,
            "max_diferencia_laea": max_laea, "peor_laea": peor_laea}


def validar_exportacion(carpeta, mapas=None):
    """Vuelve a leer tablas: claves, áreas, pesos, medias, máscaras y centroide."""
    import json
    def leer(nombre):
        with (carpeta/nombre).open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    def numero(x):
        if x == "":
            return None
        v = float(x)
        if not math.isfinite(v):
            raise ValueError("Número exportado no finito")
        return v
    def booleano(x):
        if x not in ("True", "False"):
            raise ValueError("Booleano exportado inválido")
        return x == "True"
    def igual(a, b, tolerancia=0.0):
        if (a is None) != (b is None) or a is not None and abs(a-b) > tolerancia:
            raise ValueError(f"Reconstrucción exportada distinta: {a} != {b}")
    manifest = json.loads((carpeta/"manifest.json").read_text())
    soportes = {s["soporte_id"]: s for s in json.loads((carpeta/"soportes.json").read_text())}
    fuentes = {(m["variable"], m["periodo"]): m for m in manifest["mapas"]}
    esperadas = set(itertools.product(manifest["seleccion"]["ids"], manifest["seleccion"]["periodos"], VARIABLES))
    filas = leer("clima_parcela_mes.csv")
    claves = [(r["id_parcela"], r["periodo"], r["variable"]) for r in filas]
    if len(claves) != len(esperadas) or set(claves) != esperadas:
        raise ValueError("Exportación con claves ausentes, extras o duplicadas")
    if manifest.get("modo") == "completa" and (len(esperadas) != 28368 or len(manifest["seleccion"]["ids"]) != 197 or len(manifest["seleccion"]["periodos"]) != 48):
        raise ValueError("Universo completo incorrecto")
    tabla_soporte = {}
    for c in leer("soporte_celdas.csv"):
        clave = c["soporte_id"], c["celda"]
        if clave in tabla_soporte:
            raise ValueError("Celda de soporte exportada duplicada")
        tabla_soporte[clave] = c
    esperadas_soporte = {(s["soporte_id"], c["celda"]) for s in soportes.values() for c in s["celdas"]}
    if set(tabla_soporte) != esperadas_soporte:
        raise ValueError("Tabla de soporte incompleta")
    for s in soportes.values():
        for c in s["celdas"]:
            d = tabla_soporte[s["soporte_id"], c["celda"]]
            if any(d[k] != str(s[k]) for k in ("id_parcela", "cuadricula_id", "geometria_sha256", "metodo_area", "paso_area_grados")):
                raise ValueError("Referencia de soporte exportada incompatible")
            for k in ("fila", "columna", "area_m2", "peso_espacial"):
                igual(numero(d[k]), c[k])
    grupos = defaultdict(list)
    unicas = set()
    for c in leer("valores_celdas.csv"):
        clave = c["id_parcela"], c["periodo"], c["variable"]
        ident = (*clave, c["celda"])
        if clave not in esperadas or ident in unicas:
            raise ValueError("Detalle de celdas duplicado o sin registro de clima")
        unicas.add(ident)
        grupos[clave].append(c)
    max_error = 0.0
    for r, clave in zip(filas, claves):
        s = soportes[r["soporte_id"]]
        fuente = fuentes[r["variable"], r["periodo"]]
        if r["id_parcela"] != s["id_parcela"] or r["cuadricula_id"] != s["cuadricula_id"] or r["cuadricula_id"] != fuente["cuadricula_id"] or r["sha256_raster"] != fuente["sha256_raster"] or r["unidad"] != fuente["unidad"]:
            raise ValueError("Enlace clima/soporte/mapa incorrecto")
        cs = grupos[clave]
        if {c["celda"] for c in cs} != {c["celda"] for c in s["celdas"]}:
            raise ValueError("Detalle de celdas incompleto por parcela/mes/variable")
        validas = []
        for c in cs:
            if any(c[k] != r[k] for k in ("soporte_id", "cuadricula_id", "sha256_raster")):
                raise ValueError("Enlace de celda incorrecto")
            sc = tabla_soporte[s["soporte_id"], c["celda"]]
            if any(c[k] != sc[k] for k in ("fila", "columna", "area_m2", "peso_espacial")):
                raise ValueError("Área/peso/posición de celda exportada incompatible")
            v, valida = numero(c["valor"]), booleano(c["valida"])
            if valida != (v is not None):
                raise ValueError("Máscara y valor exportados incompatibles")
            if mapas is not None:
                m = mapas[r["variable"], r["periodo"]]
                original = m.datos[int(c["fila"]), int(c["columna"])]
                if valida != (not np.ma.is_masked(original)):
                    raise ValueError("Máscara exportada distinta del mapa original")
                igual(v, float(original) if valida else None)
            if valida:
                validas.append(c)
            else:
                igual(numero(c["peso_valido"]), 0.0)
        av = math.fsum(numero(c["area_m2"]) for c in validas)
        total, area = s["area_intersectada_m2"], s["area_parcela_m2"]
        for campo in ("area_parcela_m2", "area_intersectada_m2", "area_ha_origen", "area_fuera_mapa_m2", "cobertura_espacial_bruta"):
            igual(numero(r[campo]), s[campo])
        igual(numero(r["area_valida_m2"]), av)
        igual(numero(r["area_nodata_m2"]), total-av)
        igual(numero(r["cobertura_valida_bruta"]), av/area)
        igual(numero(r["cobertura_valida"]), min(1.0, av/area))
        for c in validas:
            igual(numero(c["peso_valido"]), numero(c["area_m2"])/av, TOL_PESOS)
        if validas:
            igual(math.fsum(numero(c["peso_valido"]) for c in validas), 1.0, TOL_PESOS)
        reconstruida = math.fsum(numero(c["valor"])*numero(c["peso_valido"]) for c in validas) if av else None
        media = numero(r["media_ponderada"])
        igual(media, reconstruida, TOL_RECONSTRUCCION)
        if media is not None:
            max_error = max(max_error, abs(media-reconstruida))
        estado = ("sin_cobertura_espacial" if not cs else "todo_nodata" if not av else
                  "cobertura_completa" if s["cobertura_espacial_completa"] and len(validas) == len(cs) else "cobertura_parcial")
        if r["estado"] != estado or not r["motivo"] or booleano(r["cobertura_espacial_completa"]) != s["cobertura_espacial_completa"]:
            raise ValueError("Estado/motivo/cobertura exportado incompatible")
        if "valor_centroide" in r:
            valor = numero(r["valor_centroide"])
            df = media-valor if media is not None and valor is not None else None
            igual(numero(r["diferencia_media_menos_centroide"]), df, TOL_RECONSTRUCCION)
            igual(numero(r["diferencia_abs_centroide"]), abs(df) if df is not None else None, TOL_RECONSTRUCCION)
            booleano(r["centroide_dentro_parcela"])
            if mapas is not None:
                m = mapas[r["variable"], r["periodo"]]
                f, c = celda_punto(numero(r["centroide_lon"]), numero(r["centroide_lat"]), m.cuadricula)
                if (f, c) != (int(r["fila_centroide"]), int(r["columna_centroide"])):
                    raise ValueError("Índice del centroide incompatible con su punto")
                dentro = 0 <= f < m.cuadricula.height and 0 <= c < m.cuadricula.width
                esperado = comparar_centroide({"centroide_en_mapa": dentro, "fila_centroide": f, "columna_centroide": c}, m, media)
                if r["estado_centroide"] != esperado["estado_centroide"] or booleano(r["centroide_en_mapa"]) != dentro:
                    raise ValueError("Estado de centroide incompatible")
                igual(valor, esperado["valor_centroide"])
    return {"estado": "exportacion_verificada", "filas_clima": len(filas), "filas_valores_celdas": len(unicas),
            "estados": dict(Counter(r["estado"] for r in filas)), "max_error_reconstruccion": max_error,
            "tolerancia_reconstruccion_abs": TOL_RECONSTRUCCION, "tolerancia_pesos_abs": TOL_PESOS,
            "mascaras_valores_contrastados_original": mapas is not None}
