"""Contrato T06→T07: columnas literales, claves 1:1 y cobertura independiente."""
from datetime import date
from itertools import product

from scripts.t07_fuentes import BASE, numero
from scripts.t07_ventanas import VENTANAS

CORTE = date(2025, 10, 31)
SENSORES = {"pl": ("Planet", 20), "s2": ("Sentinel-2", 5), "ls": ("Landsat", 5)}
RASGOS = {
    "pl": ("ndvi_max", "ndvi_integral", "lai2_max", "ndvi_dias_sobre_mitad",
           "ndvi_dia_inicio", "ndvi_std_en_maximo", "capturas", "hueco_max", "nubosidad_media"),
    "s2": ("ndvi_max", "ndvi_integral", "ndvi_dias_sobre_mitad", "ndwi_en_maximo",
           "ndvi_std_en_maximo", "capturas", "hueco_max", "nubosidad_media"),
    "ls": ("vi6t_mediana", "capturas", "hueco_max", "nubosidad_media"),
}
META = {f"{p}_{r}_{w}": (p, r, w) for p in SENSORES for w in VENTANAS for r in RASGOS[p]}
META.update({f"{p}_ndvi_al_corte": (p, "ndvi_al_corte", "al_corte") for p in ("pl", "s2")})
CALIDAD = ("id_parcela", "sensor", "ventana", "umbral_nubosidad", "capturas",
           "hueco_max_dias", "hueco_max_interno_dias", "primera", "ultima",
           "dias_esperados", "dias_entre_primera_y_ultima", "meses_sin_captura",
           "nubosidad_media", "variables_ausentes", "estado")
UNIDADES = {
    "ndvi_max": "adimensional", "ndvi_integral": "NDVI·días",
    "lai2_max": "índice LAI2; unidad física no documentada en T06",
    "ndvi_dias_sobre_mitad": "días", "ndvi_dia_inicio": "día del año (2025)",
    "ndvi_std_en_maximo": "adimensional", "capturas": "capturas", "hueco_max": "días",
    "nubosidad_media": "%", "ndvi_al_corte": "adimensional", "ndwi_en_maximo": "adimensional",
    "vi6t_mediana": "índice VI6T; unidad física no documentada en T06",
}


def entero(valor, nombre, minimo=0, maximo=None):
    n = numero(valor)
    if not n.is_integer() or n < minimo or (maximo is not None and n > maximo):
        raise ValueError(f"Conteo/rango incompatible: {nombre}")
    return int(n)


def tipo(rasgo):
    return "calidad" if rasgo in {"capturas", "hueco_max", "nubosidad_media"} else (
        "heterogeneidad" if rasgo == "ndvi_std_en_maximo" else "compacta")


def validar(columnas, filas, definiciones, cobertura, catalogo):
    """Ninguna fila ausente o duplicada se convierte en una unión silenciosa."""
    ids = [r["id_parcela"] for r in catalogo]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Catálogo T07 con IDs vacíos/duplicados")
    if len(columnas) != len(set(columnas)) or set(columnas) != {"ID_POLIGONO", *META}:
        raise ValueError("Columnas T06 incompatibles con el contrato de 44 variables")
    sids = [r.get("ID_POLIGONO") for r in filas]
    if len(sids) != len(ids) or len(set(sids)) != len(ids) or set(sids) != set(ids):
        raise ValueError("IDs T06 ausentes, ajenos o duplicados")
    nombres = [r.get("columna") for r in definiciones]
    if len(nombres) != len(META) or len(set(nombres)) != len(META) or set(nombres) != set(META):
        raise ValueError("Diccionario T06 incompleto o duplicado")
    for d in definiciones:
        p, rasgo, w = META[d["columna"]]
        sensor, u = SENSORES[p]
        ventana = "31-oct (sin ventana)" if w == "al_corte" else w
        if (d["sensor"] != sensor or numero(d["umbral_nubosidad"]) != u or
                d["ventana"] != ventana or d["tipo"] != tipo(rasgo) or not d["definicion"].strip()):
            raise ValueError(f"Sensor/ventana/tipo/umbral T06 contradictorio: {d['columna']}")
    por_id = {r["ID_POLIGONO"]: r for r in filas}
    grupos = {r["id_parcela"]: r["conjunto_origen"] for r in catalogo}
    cov = {}
    for r in cobertura:
        k = (r["ID_POLIGONO"], r["sensor"], entero(r["umbral_nubosidad"], "umbral"), r["ventana"])
        if k in cov:
            raise ValueError("Cobertura T06 con clave duplicada")
        cov[k] = r
    esperadas = set(product(ids, (s for s, _ in SENSORES.values()), (0, 5, 20), VENTANAS))
    if set(cov) != esperadas:
        raise ValueError("Cobertura T06 incompleta o con claves ajenas")
    for k, r in cov.items():
        pid, _, _, w = k
        inicio = date.fromisoformat(VENTANAS[w][0] + "-01")
        dias = (CORTE - inicio).days + 1
        n = entero(r["capturas"], "capturas")
        h = entero(r["hueco_max_dias"], "hueco", maximo=dias)
        hi = entero(r["hueco_max_interno_dias"], "hueco interno", maximo=h)
        entero(r["meses_sin_captura"], "meses sin captura", maximo=len(VENTANAS[w]))
        if r["CONJUNTO"] != grupos[pid]:
            raise ValueError("CONJUNTO T06 no coincide con T02")
        if n:
            primera, ultima = date.fromisoformat(r["primera"]), date.fromisoformat(r["ultima"])
            if not inicio <= primera <= ultima <= CORTE or (n == 1 and primera != ultima):
                raise ValueError("Fechas T06 fuera de ventana/corte o contradictorias")
            if h < max((primera - inicio).days, (CORTE - ultima).days):
                raise ValueError("Hueco T06 omite los bordes de la ventana")
        elif r["primera"] or r["ultima"] or hi != 0 or h != dias - 1:
            raise ValueError("Cobertura T06 sin capturas contradictoria")
    for pid, r in por_id.items():
        if set(r) != set(columnas):
            raise ValueError("Fila T06 con columnas incompatibles")
        for c, (p, rasgo, w) in META.items():
            x = numero(r[c], vacio=True)
            if x is None:
                if rasgo in {"capturas", "hueco_max"}:
                    raise ValueError("Control T06 requerido ausente")
                continue
            dias = (CORTE - date.fromisoformat(VENTANAS[w][0] + "-01")).days + 1 if w in VENTANAS else 15
            if rasgo in {"capturas", "hueco_max", "ndvi_dias_sobre_mitad"}:
                entero(r[c], c, maximo=None if rasgo == "capturas" else dias)
            elif rasgo == "ndvi_dia_inicio":
                entero(r[c], c, minimo=date.fromisoformat(VENTANAS[w][0] + "-01").timetuple().tm_yday,
                       maximo=CORTE.timetuple().tm_yday)
            elif rasgo == "nubosidad_media" and not 0 <= x <= 100:
                raise ValueError("Nubosidad T06 fuera de 0–100 %")
            elif rasgo in {"ndvi_std_en_maximo", "ndvi_integral"} and x < 0:
                raise ValueError("Dispersión/integral T06 negativa")
        for p, (sensor, u) in SENSORES.items():
            for w in VENTANAS:
                q = cov[(pid, sensor, u, w)]
                if (numero(r[f"{p}_capturas_{w}"]) != numero(q["capturas"]) or
                        numero(r[f"{p}_hueco_max_{w}"]) != numero(q["hueco_max_dias"])):
                    raise ValueError(f"Calidad compacta T06 distinta de cobertura: {pid}/{sensor}/{w}")
    calidad = []
    for pid in sorted(ids):
        r = por_id[pid]
        for p, (sensor, u) in SENSORES.items():
            for w in VENTANAS:
                q = cov[(pid, sensor, u, w)]
                ausentes = sorted(c for c, (pref, _, ventana) in META.items() if pref == p and ventana == w and r[c] == "")
                span = (date.fromisoformat(q["ultima"]) - date.fromisoformat(q["primera"])).days if q["primera"] else ""
                calidad.append(dict(id_parcela=pid, sensor=sensor, ventana=w, umbral_nubosidad=u,
                    **{k: q[k] for k in ("capturas", "hueco_max_dias", "hueco_max_interno_dias", "primera", "ultima", "meses_sin_captura")},
                    dias_esperados=(CORTE - date.fromisoformat(VENTANAS[w][0] + "-01")).days + 1,
                    dias_entre_primera_y_ultima=span, nubosidad_media=r[f"{p}_nubosidad_media_{w}"],
                    variables_ausentes=";".join(ausentes), estado="valores_ausentes" if ausentes else "valores_presentes"))
    equivalencias = []
    for p in SENSORES:
        for rasgo in RASGOS[p]:
            a, b = (f"{p}_{rasgo}_{w}" for w in VENTANAS)
            pares = [(numero(por_id[i][a], vacio=True), numero(por_id[i][b], vacio=True)) for i in sorted(ids)]
            if all(x == y for x, y in pares):
                equivalencias.append(dict(columna_a=a, columna_b=b, parcelas=len(ids), tipo="igualdad_numerica_observada",
                                          accion="conservar_ambas; seleccionar_solo_en_experimento_explicito"))
    return por_id, calidad, equivalencias


def unir(catalogo, columnas, satelite, clima=None):
    """Conserva texto/precisión original; cada bloque debe tener todas las claves."""
    satcols = tuple(c for c in columnas if c != "ID_POLIGONO")
    ids = {r["id_parcela"] for r in catalogo}
    if set(satelite) != ids:
        raise ValueError("Unión T06 con claves incompatibles")
    climaticas = ()
    ci = {}
    if clima is not None:
        ci = {r["id_parcela"]: r for r in clima}
        if len(ci) != len(clima) or set(ci) != ids:
            raise ValueError("Unión T04 con claves incompatibles")
        climaticas = tuple(c for c in clima[0] if c != "id_parcela")
        if any(set(r) != {"id_parcela", *climaticas} for r in clima):
            raise ValueError("Columnas climáticas contradictorias")
    campos = (*BASE, *climaticas, *satcols)
    if len(campos) != len(set(campos)):
        raise ValueError("Colisión de columnas entre bloques")
    filas = [{**r, **({c: ci[r['id_parcela']][c] for c in climaticas} if clima is not None else {}),
              **{c: satelite[r['id_parcela']][c] for c in satcols}}
             for r in sorted(catalogo, key=lambda r: r["id_parcela"])]
    return campos, filas


def diccionario_satelite(definiciones, archivo="tabla_comun.csv"):
    out = []
    for d in definiciones:
        p, rasgo, w = META[d["columna"]]
        out.append(dict(archivo=archivo, columna=d["columna"], definicion=d["definicion"], unidad=UNIDADES[rasgo],
            funcion="calidad" if tipo(rasgo) == "calidad" else "predictor_candidato", producto=d["sensor"],
            periodo="2025-10-17/2025-10-31" if w == "al_corte" else "2025-04-01/2025-10-31" if w == "abr_oct" else "2025-06-01/2025-10-31",
            agregacion=f"T06: {d['definicion']} Umbral de nubosidad: {d['umbral_nubosidad']} %.",
            significado_vacio="Resumen no observado/calculable en T06; no equivale a cero; consultar calidad_satelite.csv y T06",
            procedencia="inventario_fuentes.json; diccionario T06; calidad_satelite.csv"))
    return out


def diccionario_calidad():
    des = {
        "id_parcela": ("Clave original", "sin unidad", "metadato"),
        "sensor": ("Sensor de la fuente T06", "categoría", "metadato"),
        "ventana": ("Ventana calendario candidata; no fecha de cultivo confirmada", "categoría", "metadato"),
        "umbral_nubosidad": ("Umbral fijado en T06; no elegido por rendimiento en T07", "%", "calidad"),
        "capturas": ("Capturas válidas; no días de observación independientes", "capturas", "calidad"),
        "hueco_max_dias": ("Hueco máximo que incluye los bordes; no fracción de superficie", "días", "calidad"),
        "hueco_max_interno_dias": ("Hueco máximo entre capturas; excluye bordes", "días", "calidad"),
        "primera": ("Primera captura válida dentro de ventana y corte", "fecha ISO", "calidad"),
        "ultima": ("Última captura válida dentro de ventana y corte", "fecha ISO", "calidad"),
        "dias_esperados": ("Duración inclusiva del calendario, no capturas disponibles", "días", "calidad"),
        "dias_entre_primera_y_ultima": ("Distancia entre extremos observados; no cobertura diaria garantizada", "días", "calidad"),
        "meses_sin_captura": ("Meses del calendario sin captura válida al umbral T06", "meses", "calidad"),
        "nubosidad_media": ("Media de nubosidad de todas las capturas informadas; puede ser indicador de zona", "%", "calidad"),
        "variables_ausentes": ("Columnas de esa ventana ausentes en T06, separadas por ;", "categoría", "calidad"),
        "estado": ("valores_presentes o valores_ausentes; presencia no garantiza calidad suficiente", "categoría", "calidad"),
    }
    return [dict(archivo="calidad_satelite.csv", columna=c, definicion=des[c][0], unidad=des[c][1], funcion=des[c][2],
        producto="T06", periodo="ventana y sensor de cada fila", agregacion="control, sin transformación aprendida",
        significado_vacio="Ninguna variable ausente" if c == "variables_ausentes" else
            "Sin captura válida; no equivale a cero" if c in {"primera", "ultima", "dias_entre_primera_y_ultima", "nubosidad_media"} else "No permitido",
        procedencia="inventario_fuentes.json; cobertura_ventana.csv T06") for c in CALIDAD]
