"""Conciliación espacial con una revisión identificada de T02; no lee etiquetas.

Reproduce las definiciones/redondeos de T02 para comprobar la referencia.
Luego contrasta su soporte con T04, conservando ambos métodos de área/centroide.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

from pyproj import Geod
from shapely.geometry import box
from shapely.geometry.polygon import orient

try:
    from .t02_contrato import DATOS_T02, PROCEDENCIA_T02, separar_huellas
except ImportError:  # Entrada directa del extractor.
    from t02_contrato import DATOS_T02, PROCEDENCIA_T02, separar_huellas

GEOD = Geod(ellps="WGS84")
CAMPOS = ("id_parcela", "area_ha_origen", "area_ha_geodesica", "centroide_lon",
          "centroide_lat", "celdas_clima_tocadas", "celda_clima_principal",
          "fraccion_en_celda_principal")


def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def leer_tabla(ruta, campos):
    with Path(ruta).open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        if any((lector.fieldnames or []).count(c) != 1 for c in campos):
            raise ValueError(f"Columnas T02 ausentes/duplicadas: {ruta}")
        filas = [{c: r[c] for c in campos} for r in lector]
    ids = [r["id_parcela"] for r in filas]
    if any(not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("IDs T02 vacíos o duplicados")
    return {r["id_parcela"]: r for r in filas}


def referencia_desde_tablas(carpeta, revision, entradas):
    """Copia sólo ocho campos espaciales; las etiquetas no pasan a la referencia."""
    carpeta = Path(carpeta)
    cat = leer_tabla(carpeta/"tablas/catalogo_parcelas.csv", CAMPOS[:5])
    sop = leer_tabla(carpeta/"tablas/soporte_por_parcela.csv",
                     ("id_parcela", "area_ha_origen", *CAMPOS[5:]))
    if set(cat) != set(sop):
        raise ValueError("IDs distintos entre las tablas T02")
    for i in cat:
        if float(cat[i]["area_ha_origen"]) != float(sop[i]["area_ha_origen"]):
            raise ValueError(f"Área de origen distinta entre tablas T02: {i}")
    return {"schema": "t04_referencia_t02_v2", "revision": revision,
            "ruta_en_repo": "analisis/auditoria_catalogo_y_etiquetas",
            "archivos_sha256": {p: sha(carpeta/p) for p in sorted(DATOS_T02)},
            "procedencia_t02_sha256": {p: sha(carpeta/p) for p in sorted(PROCEDENCIA_T02)},
            "entradas_sha256": entradas,
            "definiciones": {"area": "Geod WGS84, vértices originales; ha con 6 decimales",
                "centroide": "planar en lon/lat originales; 7 decimales",
                "fraccion": "área Geod de intersección / área Geod de parcela; 4 decimales"},
            "parcelas": [{**cat[i], **{c: sop[i][c] for c in CAMPOS[5:]}} for i in sorted(cat)]}


def area_t02(g):
    if g.is_empty:
        return 0.0
    if g.geom_type == "Polygon":
        return abs(GEOD.geometry_area_perimeter(orient(g, 1.0))[0])
    if g.geom_type in ("MultiPolygon", "GeometryCollection"):
        return math.fsum(area_t02(p) for p in g.geoms)
    return 0.0


def conciliar(parcelas, mapas, soportes, centroides, manifest, referencia, repo):
    referencia = Path(referencia)
    if not referencia.exists():
        return {"estado": "no_disponible", "motivo": "Falta la referencia identificada de T02"}
    ref = json.loads(referencia.read_text(encoding="utf-8"))
    datos_t02, procedencia_t02 = separar_huellas(
        ref.get("archivos_sha256"), ref.get("procedencia_t02_sha256"), ref.get("schema", "desconocido"))
    filas = ref["parcelas"]
    ids = [r["id_parcela"] for r in filas]
    if len(set(ids)) != len(ids) or set(ids) != {p["id_parcela"] for p in parcelas}:
        raise ValueError("IDs T02 duplicados o diferentes de T04")
    originales = {"ID_area_rendimiento_70_30_Reto_AgroCebada.csv": manifest["catalogo"]["sha256"]}
    originales.update({Path(m["archivo"]).name: m["sha256"] for m in manifest["geometrias"]["miembros"]})
    if ref["entradas_sha256"] != originales:
        raise ValueError("Huellas de entradas T02/T04 diferentes")
    # Si las tablas reales ya están en la rama, su identidad también se comprueba.
    canonical = Path(repo)/ref["ruta_en_repo"]
    presentes = [(canonical/p).exists() for p in datos_t02]
    if any(presentes):
        if not all(presentes) or any(sha(canonical/p) != h for p, h in datos_t02.items()):
            raise ValueError("T02 local cambió: identificar/revisar la nueva referencia antes de conciliar")
        cat = leer_tabla(canonical/"tablas/catalogo_parcelas.csv", CAMPOS[:5])
        sop = leer_tabla(canonical/"tablas/soporte_por_parcela.csv", ("id_parcela", *CAMPOS[5:]))
        for r in filas:
            i = r["id_parcela"]
            if {**cat[i], **sop[i]} != r:
                raise ValueError(f"Referencia filtrada no coincide con tablas T02: {i}")
    por_id = {r["id_parcela"]: r for r in filas}
    lluvia = next(m for (v, _), m in sorted(mapas.items()) if v == "PREC")
    qid, q = lluvia.meta["cuadricula_id"], lluvia.cuadricula
    detalle = []
    for p in sorted(parcelas, key=lambda p: p["id_parcela"]):
        i, g = p["id_parcela"], p["geometria"]
        r, s, c = por_id[i], soportes[i, qid], centroides[i, qid]
        a = area_t02(g)
        esperado = {"area_ha_origen": p["area_ha_origen"], "area_ha_geodesica": round(a/10000, 6),
                    "centroide_lon": round(g.centroid.x, 7), "centroide_lat": round(g.centroid.y, 7)}
        partes = {}
        for celda in s["celdas"]:
            x0, y0 = q.transform @ (celda["columna"], celda["fila"])
            x1, y1 = q.transform @ (celda["columna"]+1, celda["fila"]+1)
            ai = area_t02(g.intersection(box(x0, y1, x1, y0)))
            if ai > 0:
                partes[celda["celda"]] = ai/a
        principal = max(partes, key=partes.get)
        esperado.update(celdas_clima_tocadas=len(partes), fraccion_en_celda_principal=round(partes[principal], 4))
        for campo, valor in esperado.items():
            observado = float(r[campo])
            # La superficie publicada tiene resolución de 0.000001 ha.
            # Comparar intervalos de redondeo, no forzar el mismo último dígito
            # entre versiones de PROJ. Margen Geod 1e-8 relativo, separado
            # de las tolerancias del motor físico T04 (que no cambian).
            tolerancia = 0.5e-6 + abs(a/10000)*1e-8 if campo == "area_ha_geodesica" else 1e-12
            calculado = a/10000 if campo == "area_ha_geodesica" else valor
            if not math.isfinite(observado) or abs(observado-calculado) > tolerancia:
                raise ValueError(f"T02 no se reproduce: {i}/{campo}: {observado} != {valor}")
        principal_t04 = max(s["celdas"], key=lambda c: c["area_m2"])
        if principal != r["celda_clima_principal"] or principal != principal_t04["celda"] or len(partes) != len(s["celdas"]):
            raise ValueError(f"Soporte T02/T04 incompatible: {i}")
        if round(principal_t04["peso_espacial"], 4) != float(r["fraccion_en_celda_principal"]):
            raise ValueError(f"Fracción T02/T04 incompatible al redondeo publicado: {i}")
        detalle.append({"id_parcela": i,
            "diferencia_area_t04_menos_t02_pct": 100*(s["area_parcela_m2"]/10000-float(r["area_ha_geodesica"]))/float(r["area_ha_geodesica"]),
            "diferencia_area_t04_menos_geod_sin_redondear_pct": 100*(s["area_parcela_m2"]-a)/a,
            "diferencia_centroide_lon_grados": c["centroide_lon"]-float(r["centroide_lon"]),
            "diferencia_centroide_lat_grados": c["centroide_lat"]-float(r["centroide_lat"]),
            "diferencia_fraccion": principal_t04["peso_espacial"]-float(r["fraccion_en_celda_principal"])})
    campos = [k for k in detalle[0] if k != "id_parcela"]
    maximos = {}
    for campo in campos:
        mayor = max(detalle, key=lambda r: abs(r[campo]))
        maximos[campo] = {"valor_absoluto": abs(mayor[campo]), "id_parcela": mayor["id_parcela"]}
    return {"estado": "conciliada_con_referencia_identificada", "revision_t02": ref["revision"],
            "referencia_sha256": sha(referencia), "archivos_t02_sha256": datos_t02,
            "schema_referencia_t02": ref["schema"], "procedencia_t02_sha256": procedencia_t02,
            "politica_compatibilidad_t02": "tablas_identicas_procedencia_no_bloqueante",
            "origen": "tablas locales verificadas" if all(presentes) else "referencia espacial filtrada de tablas identificadas",
            "ids_verificados": len(ids), "areas_origen_iguales": len(ids), "celdas_principales_iguales": len(ids),
            "numero_celdas_igual": len(ids), "fracciones_iguales_a_4_decimales": len(ids),
            "catalogo_compatible_con_definicion_precision_t02": len(ids),
            "tolerancia_area_t02_ha": "0.5e-6 ha (semipaso publicado) + 1e-8 relativo Geod; no modifica tolerancias T04", "maximos": maximos,
            "interpretacion": "Las diferencias de área/centroide incluyen método y redondeo; T04/T03 conservan sus definiciones. Conciliar no equivale a aprobar toda T02 ni cerrar T04.",
            "detalle": detalle}
