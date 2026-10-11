"""Contratos de entrada T07; lectura estricta y sin transformaciones aprendidas."""
import calendar
from collections import Counter
import csv
from datetime import date
import hashlib
import itertools
import json
import math
from pathlib import Path

UNIDADES = {"PREC": "mm/mes", "Tmin": "grados Celsius", "Tmax": "grados Celsius"}
ESTADOS = {"cobertura_completa", "cobertura_parcial", "todo_nodata", "sin_cobertura_espacial"}
BASE = ("id_parcela", "campania", "rendimiento_t_ha", "area_ha_origen",
        "municipio", "estado", "cultivo_origen", "conjunto_origen")
CLIMA = ("id_parcela", "periodo", "variable", "unidad", "media_ponderada",
         "estado", "cobertura_valida", "valor_centroide",
         "diferencia_media_menos_centroide", "centroide_dentro_parcela",
         "posterior_al_corte")


def sha(ruta):
    h = hashlib.sha256()
    with Path(ruta).open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def leer_json(ruta):
    def pares(items):
        d = {}
        for k, v in items:
            if k in d:
                raise ValueError(f"Clave JSON duplicada: {k}")
            d[k] = v
        return d
    def invalido(x):
        raise ValueError(f"JSON no finito: {x}")
    return json.loads(Path(ruta).read_text(encoding="utf-8"),
                      object_pairs_hook=pares, parse_constant=invalido)


def leer_csv(ruta):
    with Path(ruta).open(encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        nombres = lector.fieldnames or []
        if not nombres or len(set(nombres)) != len(nombres):
            raise ValueError("Cabecera vacía o columnas duplicadas")
        filas = list(lector)
    if not filas:
        raise ValueError("CSV sin filas")
    if any(None in r or any(v is None for v in r.values()) for r in filas):
        raise ValueError("CSV con número de campos incorrecto")
    return nombres, filas


def numero(s, vacio=False):
    if s == "" and vacio:
        return None
    n = float(s)
    if not math.isfinite(n):
        raise ValueError("Valor no finito")
    return n


def fin_mes(periodo):
    if len(periodo) != 7 or periodo[4] != "-" or not periodo.replace("-", "").isdigit():
        raise ValueError("Periodo debe usar YYYY-MM")
    a, m = map(int, periodo.split("-"))
    return date(a, m, calendar.monthrange(a, m)[1])


def validar_catalogo(filas, cantidad=197, conocidas=138):
    necesarios = set(BASE) - {"campania"}
    if not filas or any(not necesarios <= r.keys() for r in filas):
        raise ValueError("Catálogo sin campos requeridos")
    ids = [r["id_parcela"] for r in filas]
    if len(ids) != cantidad or len(set(ids)) != cantidad or any(not x or x.strip() != x for x in ids):
        raise ValueError("Catálogo con IDs vacíos/duplicados o cantidad incompatible")
    n = 0
    for r in filas:
        if numero(r["area_ha_origen"]) <= 0:
            raise ValueError("Área de origen no positiva")
        y = numero(r["rendimiento_t_ha"], vacio=True)
        if y is not None and y < 0:
            raise ValueError("Rendimiento negativo")
        if r["conjunto_origen"] not in {"ENTRENAMIENTO", "PREDICCION"}:
            raise ValueError("CONJUNTO desconocido")
        if (y is None) != (r["conjunto_origen"] == "PREDICCION"):
            raise ValueError("Etiqueta y conjunto incompatibles")
        if any(not r[k] for k in ("municipio", "estado", "cultivo_origen")):
            raise ValueError("Metadato territorial ausente")
        n += y is not None
    if n != conocidas:
        raise ValueError("Cantidad de etiquetas incompatible")
    return [{k: ("2025" if k == "campania" else r[k]) for k in BASE}
            for r in sorted(filas, key=lambda r: r["id_parcela"])]


def validar_mensuales(filas, ids, corte):
    indice = {}
    for r in filas:
        key = (r["id_parcela"], r["periodo"], r["variable"])
        if key in indice:
            raise ValueError("Mes/variable duplicado")
        if r["id_parcela"] not in ids or r["variable"] not in UNIDADES:
            raise ValueError("ID o variable ajeno al contrato")
        if r["unidad"] != UNIDADES[r["variable"]] or r["estado"] not in ESTADOS:
            raise ValueError("Unidad o estado incompatible")
        fin = fin_mes(r["periodo"])
        if r["posterior_al_corte"] != str(fin > date.fromisoformat(corte)):
            raise ValueError("Indicador de corte contradictorio")
        if r["centroide_dentro_parcela"] not in {"True", "False"}:
            raise ValueError("Indicador geométrico inválido")
        media = numero(r["media_ponderada"], vacio=True)
        cobertura = numero(r["cobertura_valida"])
        ausente = r["estado"] in {"todo_nodata", "sin_cobertura_espacial"}
        if not 0 <= cobertura <= 1 or ausente != (media is None) or ausente != (cobertura == 0):
            raise ValueError("Media, cobertura y estado contradictorios")
        centro = numero(r["valor_centroide"], vacio=True)
        delta = numero(r["diferencia_media_menos_centroide"], vacio=True)
        if media is None or centro is None:
            if delta is not None:
                raise ValueError("Diferencia con valor ausente")
        elif delta is None or abs((media - centro) - delta) > 1e-12:
            raise ValueError("Diferencia con centroide incompatible")
        if r["variable"] == "PREC" and any(v is not None and v < 0 for v in (media, centro)):
            raise ValueError("Precipitación negativa")
        indice[key] = r
    return indice


def leer_entrega(carpeta, ids):
    carpeta = Path(carpeta)
    m = leer_json(carpeta / "manifest.json")
    esperados = {"clima_parcela_mes.csv", "procedencia.json", "conciliacion_t02.json", "controles.json"}
    if m.get("schema") != "t04_entrega_compacta_v1" or set(m["archivos_sha256"]) != esperados:
        raise ValueError("Esquema/archivos T04 incompatible")
    for n, h in m["archivos_sha256"].items():
        if sha(carpeta / n) != h:
            raise ValueError(f"Huella T04 distinta: {n}")
    if len(m["ids"]) != len(set(m["ids"])) or set(m["ids"]) != set(ids):
        raise ValueError("IDs del manifiesto T04 incompatibles")
    periodos = [f"{a}-{mes:02d}" for a in range(2022, 2026) for mes in range(1, 13)]
    if m["periodos"] != periodos or m["corte_observacional_provisional"] != "2025-10-31":
        raise ValueError("Periodos o corte T04 incompatibles")
    cabecera, filas = leer_csv(carpeta / "clima_parcela_mes.csv")
    if cabecera != list(CLIMA) or m["columnas"] != list(CLIMA):
        raise ValueError("Columnas T04 incompatibles")
    indice = validar_mensuales(filas, set(ids), m["corte_observacional_provisional"])
    if set(indice) != set(itertools.product(ids, periodos, UNIDADES)):
        raise ValueError("Historia mensual T04 incompleta")
    pro = leer_json(carpeta / "procedencia.json")
    mapas = {(r["periodo"], r["variable"]): r for r in pro["mapas"]}
    if len(mapas) != len(pro["mapas"]) or set(mapas) != set(itertools.product(periodos, UNIDADES)):
        raise ValueError("Procedencia de mapas incompleta/duplicada")
    for (mes, v), mapa in mapas.items():
        tag = mapa["etiquetas"]
        agregado = "Suma de precipitación diaria" if v == "PREC" else "Promedio mensual"
        if mapa["unidad"] != UNIDADES[v] or tag.get("Agregacion") != agregado or tag.get("Periodo") != mes:
            raise ValueError("Agregación, unidad o periodo del mapa incompatible")
        if tag.get("Unidad") != UNIDADES[v]:
            raise ValueError("Unidad de metadatos incompatible")
        if v == "PREC" and int(tag.get("Dias_acumulados", 0)) != fin_mes(mes).day:
            raise ValueError("Días acumulados del mapa incompatibles")
    qids = {r["cuadricula_id"] for r in pro["mapas"]}
    soportes = [(s["id_parcela"], s["cuadricula_id"]) for s in pro["soportes"]]
    if len(set(soportes)) != len(soportes) or set(soportes) != set(itertools.product(ids, qids)):
        raise ValueError("Soportes incompletos/duplicados")
    control = {"filas": len(filas), "ids": len(ids), "periodos": len(periodos),
               "estados": dict(Counter(r["estado"] for r in filas)),
               "filas_posteriores_al_corte": sum(r["posterior_al_corte"] == "True" for r in filas),
               "filas_centroide_exterior": sum(r["centroide_dentro_parcela"] == "False" for r in filas)}
    if control != leer_json(carpeta / "controles.json"):
        raise ValueError("Controles T04 distintos del contenido")
    con = leer_json(carpeta / "conciliacion_t02.json")
    if con.get("estado") != "conciliada_con_referencia_identificada" or con.get("ids_verificados") != len(ids):
        raise ValueError("Conciliación T02 incompleta")
    return indice, m, pro, con


def soporte_lluvia_t02(filas, ids):
    """Conteo publicado de lluvia por parcela; no atribuirlo a otra cuadrícula."""
    indice = {}
    for r in filas:
        pid = r.get('id_parcela')
        n = r.get('celdas_clima_tocadas', '')
        if pid in indice or pid not in ids or not n.isdigit() or int(n) < 1:
            raise ValueError('Conteo/claves de soporte climático T02 incompatibles')
        indice[pid] = int(n)
    if set(indice) != set(ids):
        raise ValueError('Soporte climático T02 incompleto')
    return indice


def guardar_csv(ruta, campos, filas):
    with Path(ruta).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


def guardar_json(ruta, datos):
    Path(ruta).write_text(json.dumps(datos, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                          encoding="utf-8")
