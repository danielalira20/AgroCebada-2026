"""Entrega compacta T04 y verificador sin ZIP, Docker ni dependencias externas.

El indicador temporal compara el fin del mes observado con un corte explícito.
No certifica disponibilidad histórica, elegibilidad para el modelo ni ventanas.
"""
import argparse
import calendar
from collections import Counter
import csv
from datetime import date
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import tempfile

BASE = ("id_parcela", "periodo", "variable", "unidad", "media_ponderada", "estado",
        "cobertura_valida", "valor_centroide", "diferencia_media_menos_centroide")
COLUMNAS = (*BASE, "centroide_dentro_parcela", "posterior_al_corte")
UNIDADES = {"PREC": "mm/mes", "Tmin": "grados Celsius", "Tmax": "grados Celsius"}
ESTADOS = {"cobertura_completa", "cobertura_parcial", "todo_nodata", "sin_cobertura_espacial"}


def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def leer_csv(ruta):
    with Path(ruta).open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        cabecera = lector.fieldnames or []
        if len(set(cabecera)) != len(cabecera):
            raise ValueError("Columnas duplicadas")
        filas = list(lector)
        if any(None in r or any(v is None for v in r.values()) for r in filas):
            raise ValueError("Filas con número de campos incorrecto")
        return cabecera, filas


def posterior(periodo, corte):
    if len(periodo) != 7 or periodo[4] != "-":
        raise ValueError("Periodo debe usar YYYY-MM")
    anio, mes = map(int, periodo.split("-"))
    ultimo = date(anio, mes, calendar.monthrange(anio, mes)[1])
    return ultimo > date.fromisoformat(corte)


def numero(texto):
    if texto == "":
        return None
    n = float(texto)
    if not math.isfinite(n):
        raise ValueError("Valor no finito")
    return n


def validar_filas(filas, ids, periodos, corte):
    esperadas = set(itertools.product(ids, periodos, UNIDADES))
    claves = [(r["id_parcela"], r["periodo"], r["variable"]) for r in filas]
    if len(claves) != len(esperadas) or set(claves) != esperadas:
        raise ValueError("Claves incompletas, duplicadas o ajenas al universo")
    for r in filas:
        if r["unidad"] != UNIDADES[r["variable"]] or r["estado"] not in ESTADOS:
            raise ValueError("Unidad o estado incompatible")
        media, centro, diferencia = (numero(r[k]) for k in ("media_ponderada", "valor_centroide", "diferencia_media_menos_centroide"))
        cobertura = numero(r["cobertura_valida"])
        ausente = r["estado"] in {"todo_nodata", "sin_cobertura_espacial"}
        if cobertura is None or not 0 <= cobertura <= 1 or ausente != (media is None) or ausente != (cobertura == 0):
            raise ValueError("Media, estado o cobertura incompatibles")
        if r["variable"] == "PREC" and any(x is not None and x < 0 for x in (media, centro)):
            raise ValueError("Precipitación negativa")
        if media is None or centro is None:
            if diferencia is not None:
                raise ValueError("Diferencia con dato ausente")
        elif diferencia is None or abs((media-centro)-diferencia) > 1e-12:
            raise ValueError("Diferencia media/centroide incompatible")
        if r["centroide_dentro_parcela"] not in {"True", "False"} or r["posterior_al_corte"] != str(posterior(r["periodo"], corte)):
            raise ValueError("Indicador geométrico o temporal incompatible")
    return {"filas": len(filas), "ids": len(ids), "periodos": len(periodos),
            "estados": dict(Counter(r["estado"] for r in filas)),
            "filas_posteriores_al_corte": sum(r["posterior_al_corte"] == "True" for r in filas),
            "filas_centroide_exterior": sum(r["centroide_dentro_parcela"] == "False" for r in filas)}


def guardar_json(ruta, objeto):
    ruta.write_text(json.dumps(objeto, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def verificar(carpeta):
    carpeta = Path(carpeta)
    m = json.loads((carpeta/"manifest.json").read_text(encoding="utf-8"))
    if m.get("schema") != "t04_entrega_compacta_v1":
        raise ValueError("Esquema de entrega desconocido")
    archivos = {"clima_parcela_mes.csv", "procedencia.json", "conciliacion_t02.json", "controles.json"}
    if set(m["archivos_sha256"]) != archivos:
        raise ValueError("Lista de archivos de entrega incompatible")
    for nombre, huella in m["archivos_sha256"].items():
        if sha(carpeta/nombre) != huella:
            raise ValueError(f"Huella distinta: {nombre}")
    cabecera, filas = leer_csv(carpeta/"clima_parcela_mes.csv")
    if cabecera != list(COLUMNAS):
        raise ValueError("Columnas compactas incompatibles")
    control = validar_filas(filas, m["ids"], m["periodos"], m["corte_observacional_provisional"])
    if control != json.loads((carpeta/"controles.json").read_text(encoding="utf-8")):
        raise ValueError("Resumen de controles distinto de los datos")
    pro = json.loads((carpeta/"procedencia.json").read_text(encoding="utf-8"))
    mapas = [(r["variable"], r["periodo"]) for r in pro["mapas"]]
    if len(set(mapas)) != len(mapas) or set(mapas) != set(itertools.product(UNIDADES, m["periodos"])):
        raise ValueError("Procedencia de mapas incompleta/duplicada")
    soportes = [(s["id_parcela"], s["cuadricula_id"]) for s in pro["soportes"]]
    qids = {r["cuadricula_id"] for r in pro["mapas"]}
    if len(set(soportes)) != len(soportes) or set(soportes) != set(itertools.product(m["ids"], qids)):
        raise ValueError("Procedencia de soportes incompleta/duplicada")
    for mapa in pro["mapas"]:
        if mapa["unidad"] != UNIDADES[mapa["variable"]]:
            raise ValueError("Unidad de mapa distinta de la tabla")
    con = json.loads((carpeta/"conciliacion_t02.json").read_text(encoding="utf-8"))
    if con["estado"] != "conciliada_con_referencia_identificada" or con["ids_verificados"] != len(m["ids"]):
        raise ValueError("Conciliación T02 incompleta")
    return {"resultado": "aprobado", **control, "zip_necesario_para_verificar_entrega": False,
            "disponibilidad_historica_certificada": False, "cierre_t04": False}


def preparar(origen, salida, corte):
    origen, salida = Path(origen), Path(salida)
    if salida.exists():
        raise FileExistsError(f"La entrega ya existe: {salida}")
    m = json.loads((origen/"manifest.json").read_text(encoding="utf-8"))
    estado = json.loads((origen/"estado.json").read_text(encoding="utf-8"))
    if m["modo"] != "completa" or estado["estado"] != "extraccion_verificada_local":
        raise ValueError("La entrega requiere una extracción completa verificada")
    con = m["conciliacion_t02_aceptada"]
    if not isinstance(con, dict) or con.get("estado") != "conciliada_con_referencia_identificada":
        raise ValueError("La extracción aún no tiene conciliación T02 verificable")
    ids, periodos = m["seleccion"]["ids"], m["seleccion"]["periodos"]
    if len(ids) != 197 or len(set(ids)) != 197 or periodos != [f"{a}-{mes:02d}" for a in range(2022, 2026) for mes in range(1, 13)]:
        raise ValueError("Universo diferente de las 197 parcelas y 48 meses aprobados")
    # Sólo la preparación necesita el entorno del proyecto; verificar es stdlib.
    try:
        from .t04_control import validar_exportacion
    except ImportError:
        from t04_control import validar_exportacion
    validar_exportacion(origen)
    cabecera, originales = leer_csv(origen/"clima_parcela_mes.csv")
    if not set((*BASE, "centroide_dentro_parcela")) <= set(cabecera):
        raise ValueError("La extracción carece de columnas necesarias")
    filas = [{**{k: r[k] for k in (*BASE, "centroide_dentro_parcela")},
              "posterior_al_corte": str(posterior(r["periodo"], corte))} for r in originales]
    control = validar_filas(filas, ids, periodos, corte)
    soportes = json.loads((origen/"soportes.json").read_text(encoding="utf-8"))
    pro = {"sha256_paquete": m["sha256_paquete"], "catalogo": m["catalogo"], "geometrias": m["geometrias"],
           "mapas": m["mapas"], "metodo_area": m["metodo_area"], "paso_area_grados": m["paso_area_grados"],
           "metodo_centroide": m["metodo_centroide"], "codigo": m["codigo"],
           "dependencias": m["dependencias"], "bibliotecas_nativas": m["bibliotecas_nativas"],
           "requirements_sha256": m["requirements_sha256"], "python": m["python"],
           "soportes": [{k: s[k] for k in ("id_parcela", "cuadricula_id", "soporte_id", "geometria_sha256")} for s in soportes]}
    salida.parent.mkdir(parents=True, exist_ok=True)
    temporal = Path(tempfile.mkdtemp(prefix=".t04-entrega-incompleta-", dir=salida.parent))
    try:
        with (temporal/"clima_parcela_mes.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNAS); w.writeheader(); w.writerows(filas)
        # Valores copiados literalmente: no redondeo ni segundo cálculo de medias.
        _, exportadas = leer_csv(temporal/"clima_parcela_mes.csv")
        if any(any(a[k] != b[k] for k in (*BASE, "centroide_dentro_parcela")) for a, b in zip(originales, exportadas)) or len(originales) != len(exportadas):
            raise ValueError("Se alteraron valores al preparar la entrega")
        guardar_json(temporal/"procedencia.json", pro)
        guardar_json(temporal/"conciliacion_t02.json", con)
        guardar_json(temporal/"controles.json", control)
        publico = {"schema": "t04_entrega_compacta_v1", "ids": ids, "periodos": periodos,
            "columnas": list(COLUMNAS), "corte_observacional_provisional": corte,
            "alcance_temporal": "posterior_al_corte usa fin de mes; False NO implica disponible en esa fecha",
            "disponibilidad_historica_fira": "no documentada", "versiones_producto_fira": "sin número documentado; CHIRPS y CHIRTS-ERA5 según metadatos",
            "uso": "historia mensual descriptiva; admisibilidad/ventanas/modelo pendientes del protocolo",
            "fuente_archivos_sha256": {p: sha(origen/p) for p in ("clima_parcela_mes.csv", "soportes.json", "manifest.json", "controles.json")},
            "codigo_entrega_sha256": sha(Path(__file__)), "archivos_sha256": {p: sha(temporal/p) for p in ("clima_parcela_mes.csv", "procedencia.json", "conciliacion_t02.json", "controles.json")},
            "cierre_t04": False}
        guardar_json(temporal/"manifest.json", publico)
        verificacion = verificar(temporal)
        temporal.rename(salida)
        return {**verificacion, "bytes_csv": (salida/"clima_parcela_mes.csv").stat().st_size}
    finally:
        if temporal.exists():
            shutil.rmtree(temporal)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verificar", type=Path)
    p.add_argument("--origen", type=Path)
    p.add_argument("--salida", type=Path)
    p.add_argument("--corte")
    a = p.parse_args()
    if a.verificar:
        if a.origen or a.salida or a.corte:
            p.error("--verificar no admite otras opciones")
        r = verificar(a.verificar)
    else:
        if not (a.origen and a.salida and a.corte):
            p.error("Se requieren --origen, --salida y --corte explícito")
        r = preparar(a.origen, a.salida, a.corte)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
