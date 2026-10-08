"""Construye el catálogo de las 197 parcelas y comprueba su identidad.

Uso (con el entorno de requirements.txt del repositorio):
    python scripts/construir_catalogo.py --datos RUTA/DATASET_RETO_AGRO_2026

El dataset original de FIRA no se modifica: solo se lee. --salida es opcional;
por omisión escribe en la carpeta tablas/ que está junto a scripts/.
--contornos es opcional: por omisión lee la tabla de revisión de contornos de la
carpeta hermana exploracion_parcelas_qgis/.

Genera en --salida:
    catalogo_parcelas.csv         197 filas, una por parcela.
    precision_etiqueta_por_municipio.csv   Finura con que está anotado el rendimiento, por grupo.
    comprobaciones_catalogo.csv   Cada comprobación, lo esperado, lo obtenido y si se cumple.
    huellas_archivos_leidos.csv   Huella SHA-256 de cada archivo que se leyó.

Las columnas están definidas en diccionario_columnas.md. No entrena ningún modelo.

Etapas implementadas hasta ahora: 1 (identidad), 2 (geometría y área), 3 (calidad de contorno)
y 4 (precisión de la etiqueta).
"""
import argparse
import hashlib
import itertools
import math
from collections import Counter
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pyproj
from shapely.geometry.polygon import orient

CARPETA = Path(__file__).resolve().parents[1]
SALIDA_POR_OMISION = CARPETA / "tablas"
CONTORNOS_POR_OMISION = (CARPETA.parent / "exploracion_parcelas_qgis" / "revision_contornos"
                         / "revision_contornos.csv")

CSV_RENDIMIENTO = "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"
CARPETA_SHAPEFILE = "Parcelas_Reto_AGC_CONJUNTO_70_30"
NOMBRE_SHAPEFILE = "Parcelas_Reto_AGC_CONJUNTO"
PARTES_SHAPEFILE = [".shp", ".dbf", ".shx", ".prj", ".cpg"]

IDS_ESPERADOS = {f"AGC_{n:03d}" for n in range(1, 198)}
CONJUNTOS = {"ENTRENAMIENTO", "PREDICCION"}
ESCRITURAS_CULTIVO = {"Cebada", "CEBADA"}
ESTADOS = {"Hidalgo", "Puebla", "Tlaxcala"}
MARCAS_CONTORNO = ["divisiones_internas", "arboles_dentro", "construccion_dentro",
                   "angosta_o_muy_pequena", "imagen_poco_clara"]
FIRMEZAS = {"piloto_confirmado_en_qgis", "confirmado_en_qgis",
            "revisado_en_qgis_sin_poder_confirmar", "primera_pasada_sobre_imagen"}
CONFIRMADAS = {"piloto_confirmado_en_qgis", "confirmado_en_qgis"}

comprobaciones = []


def comprobar(etapa, nombre, esperado, obtenido, cumple=None):
    """Anota una comprobación. Si no se indica, se cumple cuando lo obtenido es igual a lo esperado."""
    if cumple is None:
        cumple = esperado == obtenido
    comprobaciones.append(dict(etapa=etapa, comprobacion=nombre, esperado=str(esperado),
                               obtenido=str(obtenido), resultado="cumple" if cumple else "NO CUMPLE"))


def anotar(etapa, nombre, valor):
    """Anota un conteo descriptivo, sin valor esperado."""
    comprobaciones.append(dict(etapa=etapa, comprobacion=nombre, esperado="", obtenido=str(valor),
                               resultado="informativo"))


def huella(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def conteos(serie) -> str:
    c = serie.value_counts()
    return "; ".join(f"{k}: {v}" for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def leer_rendimiento(datos: Path):
    """Lee el CSV de rendimiento como texto, para no alterar ningún valor."""
    ruta = datos / CSV_RENDIMIENTO
    t = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    # El archivo trae una coma de sobra al final de cada línea: crea una columna sin nombre.
    sobrantes = [c for c in t.columns if c.startswith("Unnamed") or c.strip() == ""]
    vacias = all((t[c].str.strip() == "").all() for c in sobrantes)
    comprobar(1, "CSV: las columnas sin nombre (coma de sobra) están vacías", True, vacias)
    t = t.drop(columns=sobrantes)
    comprobar(1, "CSV: columnas", "ID_POLIGONO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO", ", ".join(t.columns))
    for c in t.columns:
        t[c] = t[c].str.strip()
    return ruta, t


def leer_contornos(datos: Path):
    """Lee el shapefile de la carpeta descomprimida."""
    base = datos / CARPETA_SHAPEFILE / NOMBRE_SHAPEFILE
    rutas = [base.with_suffix(s) for s in PARTES_SHAPEFILE]
    faltan = [r.name for r in rutas if not r.exists()]
    if faltan:
        raise FileNotFoundError(f"Faltan archivos del shapefile en {base.parent}: {faltan}")
    g = gpd.read_file(base.with_suffix(".shp"), encoding="utf-8")
    return rutas, g


def etapa_identidad(datos: Path):
    """Etapa 1: une el CSV de rendimiento con el shapefile por identificador."""
    ruta_csv, t = leer_rendimiento(datos)
    rutas_shp, g = leer_contornos(datos)

    comprobar(1, "Shapefile: columnas de atributos",
              "Cultivo, ID_POLIGON, área_ha, Municipio, Estado, CONJUNTO",
              ", ".join(c for c in g.columns if c != "geometry"))

    # Cuántas parcelas hay y si los identificadores son únicos y los esperados.
    comprobar(1, "CSV: número de filas", 197, len(t))
    comprobar(1, "CSV: identificadores distintos", 197, t.ID_POLIGONO.nunique())
    comprobar(1, "CSV: los identificadores son AGC_001 a AGC_197", True, set(t.ID_POLIGONO) == IDS_ESPERADOS)
    comprobar(1, "Shapefile: número de contornos", 197, len(g))
    comprobar(1, "Shapefile: identificadores distintos", 197, g.ID_POLIGON.nunique())
    comprobar(1, "Shapefile: los identificadores son AGC_001 a AGC_197", True, set(g.ID_POLIGON) == IDS_ESPERADOS)
    comprobar(1, "Identificadores que están en un archivo y no en el otro", 0,
              len(set(t.ID_POLIGONO) ^ set(g.ID_POLIGON)))

    # Celdas vacías en los atributos del shapefile.
    atributos = g.drop(columns="geometry")
    vacias = int((atributos.isna() | (atributos.astype(str).apply(lambda s: s.str.strip()) == "")).sum().sum())
    comprobar(1, "Shapefile: celdas de atributos vacías", 0, vacias)

    # Unión uno a uno por identificador; nunca por número de fila.
    u = t.merge(g.drop(columns="geometry"), left_on="ID_POLIGONO", right_on="ID_POLIGON",
                how="outer", suffixes=("", "_shp"), validate="one_to_one", indicator=True)
    comprobar(1, "Unión CSV–shapefile: filas emparejadas una a una", 197, int((u._merge == "both").sum()))
    comprobar(1, "Unión CSV–shapefile: filas sin pareja", 0, int((u._merge != "both").sum()))

    # Lo que ambos archivos repiten debe coincidir parcela por parcela.
    comprobar(1, "CONJUNTO distinto entre CSV y shapefile (parcelas)", 0, int((u.CONJUNTO != u.CONJUNTO_shp).sum()))
    dif_area = (u.AREA_HA.astype(float) - u["área_ha"].astype(float)).abs()
    comprobar(1, "Área distinta entre CSV y shapefile (parcelas)", 0, int((dif_area > 1e-9).sum()))

    # Valores permitidos.
    comprobar(1, "CONJUNTO solo toma ENTRENAMIENTO o PREDICCION", True, set(u.CONJUNTO) <= CONJUNTOS)
    comprobar(1, "Cultivo solo toma Cebada o CEBADA", True, set(u.Cultivo) <= ESCRITURAS_CULTIVO)
    comprobar(1, "Estado solo toma Hidalgo, Puebla o Tlaxcala", True, set(u.Estado) <= ESTADOS)
    areas = u.AREA_HA.astype(float)
    comprobar(1, "Áreas mayores que cero y finitas (parcelas)", 197, int(((areas > 0) & areas.map(math.isfinite)).sum()))

    # Etiquetas: 138 con rendimiento y 59 sin él, de acuerdo con el conjunto.
    con_rend = u.RENDIMIENTO_T_HA != ""
    comprobar(1, "Parcelas con rendimiento", 138, int(con_rend.sum()))
    comprobar(1, "Parcelas sin rendimiento", 59, int((~con_rend).sum()))
    comprobar(1, "Parcelas de ENTRENAMIENTO", 138, int((u.CONJUNTO == "ENTRENAMIENTO").sum()))
    comprobar(1, "Parcelas de PREDICCION", 59, int((u.CONJUNTO == "PREDICCION").sum()))
    comprobar(1, "Parcelas donde tener rendimiento no coincide con ser de ENTRENAMIENTO", 0,
              int((con_rend != (u.CONJUNTO == "ENTRENAMIENTO")).sum()))
    valores = pd.to_numeric(u.RENDIMIENTO_T_HA[con_rend], errors="coerce")
    comprobar(1, "Rendimientos que son números finitos mayores que cero", 138,
              int(((valores > 0) & valores.map(math.isfinite)).sum()))

    # Conteos descriptivos.
    anotar(1, "Parcelas por estado", conteos(u.Estado))
    anotar(1, "Parcelas por municipio", conteos(u.Municipio))
    anotar(1, "Parcelas por escritura del campo Cultivo", conteos(u.Cultivo))
    anotar(1, "Parcelas por estado y conjunto", conteos(u.Estado + " / " + u.CONJUNTO))

    catalogo = pd.DataFrame({
        "id_parcela": u.ID_POLIGONO,
        "conjunto_origen": u.CONJUNTO,
        "rendimiento_t_ha": u.RENDIMIENTO_T_HA,   # texto original; vacío en las 59 reservadas
        "area_ha_origen": u.AREA_HA,              # texto original
        "municipio": u.Municipio,
        "estado": u.Estado,
        "cultivo_origen": u.Cultivo,
    }).sort_values("id_parcela").reset_index(drop=True)
    return catalogo, [ruta_csv] + rutas_shp, g


def etapa_geometria(catalogo: pd.DataFrame, g: gpd.GeoDataFrame):
    """Etapa 2: revisa cada contorno, calcula su área y busca contornos repetidos o encimados.

    Devuelve el catálogo ampliado y las distancias de orilla a orilla de los pares a menos de 20 m.
    """
    # Sistema de coordenadas declarado en el .prj: latitud/longitud WGS84.
    comprobar(2, "Sistema de coordenadas del shapefile", "EPSG:4326",
              f"EPSG:{g.crs.to_epsg()}" if g.crs is not None else "sin declarar")

    g = g.set_index("ID_POLIGON").loc[catalogo.id_parcela]
    geoms = g.geometry
    comprobar(2, "Contornos vacíos", 0, int(geoms.is_empty.sum()))
    comprobar(2, "Contornos geométricamente válidos", 197, int(geoms.is_valid.sum()))
    comprobar(2, "Contornos de una sola pieza (tipo Polygon)", 197, int((geoms.geom_type == "Polygon").sum()))
    comprobar(2, "Contornos con huecos por dentro", 0, int(sum(len(p.interiors) > 0 for p in geoms)))
    alturas = [abs(c[2]) for p in geoms if p.has_z for c in p.exterior.coords]
    anotar(2, "Contornos declarados con altura (PolygonZ) / altura máxima encontrada",
           f"{int(sum(p.has_z for p in geoms))} / {max(alturas) if alturas else 0}")

    # Puntos del contorno, contando el punto final que repite al primero.
    puntos = [len(p.exterior.coords) for p in geoms]
    comprobar(2, "Contornos cuyo último punto repite al primero (cerrados)", 197,
              int(sum(p.exterior.coords[0][:2] == p.exterior.coords[-1][:2] for p in geoms)))

    # Área sobre el elipsoide WGS84 (geodésica), en hectáreas. No depende de ninguna proyección plana.
    geod = pyproj.Geod(ellps="WGS84")
    area_geo = [abs(geod.geometry_area_perimeter(orient(p, 1.0))[0]) / 10_000 for p in geoms]
    area_origen = catalogo.area_ha_origen.astype(float).values
    dif_pct = [100 * (a - o) / o for a, o in zip(area_geo, area_origen)]

    catalogo = catalogo.copy()
    catalogo["geometria_valida"] = ["si" if v else "no" for v in (geoms.is_valid & ~geoms.is_empty)]
    catalogo["puntos_contorno"] = puntos
    catalogo["area_ha_geodesica"] = [round(a, 6) for a in area_geo]
    catalogo["diferencia_area_pct"] = [round(d, 3) for d in dif_pct]
    catalogo["centroide_lon"] = [round(p.centroid.x, 7) for p in geoms]
    catalogo["centroide_lat"] = [round(p.centroid.y, 7) for p in geoms]

    # Área calculada frente a área registrada.
    mayor = max(range(197), key=lambda i: abs(dif_pct[i]))
    anotar(2, "Mayor diferencia entre área calculada y registrada",
           f"{dif_pct[mayor]:+.3f} % en {catalogo.id_parcela[mayor]} "
           f"({area_geo[mayor]:.6f} ha calculadas frente a {catalogo.area_ha_origen[mayor]} ha registradas)")
    comprobar(2, "Parcelas con diferencia de área mayor al 2 %", 0, int(sum(abs(d) > 2 for d in dif_pct)))
    # El área registrada tiene dos decimales: una diferencia de hasta 0.005 ha se explica solo por el redondeo.
    dentro = int(sum(abs(a - o) <= 0.005 + 1e-9 for a, o in zip(area_geo, area_origen)))
    anotar(2, "Parcelas cuya diferencia de área cabe en el redondeo a dos decimales (hasta 0.005 ha)", f"{dentro} de 197")
    iguales = int(sum(round(a, 2) == o for a, o in zip(area_geo, area_origen)))
    anotar(2, "Parcelas cuya área calculada, redondeada a dos decimales, es igual a la registrada", f"{iguales} de 197")
    anotar(2, "Mayor diferencia de área en hectáreas",
           f"{max(abs(a - o) for a, o in zip(area_geo, area_origen)):.4f} ha")

    # Puntos del contorno según la escritura del campo Cultivo.
    for escritura, grupo in catalogo.groupby("cultivo_origen"):
        s = grupo.puntos_contorno
        anotar(2, f"Puntos por contorno en {escritura} (mínimo / mediana / máximo)",
               f"{s.min()} / {s.median():g} / {s.max()}")
        anotar(2, f"Contornos de 5 puntos o menos en {escritura}", int((s <= 5).sum()))
    # Cuántos decimales traen las coordenadas: 6 decimales exactos o más.
    seis = [all(round(c[0], 6) == c[0] and round(c[1], 6) == c[1] for c in p.exterior.coords) for p in geoms]
    for escritura in sorted(catalogo.cultivo_origen.unique()):
        m = (catalogo.cultivo_origen == escritura).values
        anotar(2, f"Contornos de {escritura} con todas sus coordenadas a 6 decimales o menos",
               f"{int(sum(s for s, k in zip(seis, m) if k))} de {int(m.sum())}")

    # Contornos repetidos, encimados o en contacto, por pares. Se mide en metros (UTM zona 14 norte).
    planos = list(geoms.to_crs(32614))
    ids = list(catalogo.id_parcela)
    pares = repetidos = encimados = contacto = 0
    cercano = (math.inf, "", "")
    a_menos_de = {1: 0, 5: 0, 20: 0}   # pares con orillas a menos de 1, 5 y 20 metros
    orillas_cercanas = {}
    for i, j in itertools.combinations(range(197), 2):
        pares += 1
        a, b = planos[i], planos[j]
        if a.equals(b):
            repetidos += 1
        if a.intersects(b):
            if a.intersection(b).area > 0:
                encimados += 1
            else:
                contacto += 1
        d = a.distance(b)
        if d < cercano[0]:
            cercano = (d, ids[i], ids[j])
        for limite in a_menos_de:
            a_menos_de[limite] += d < limite
        if d < 20:
            orillas_cercanas[(ids[i], ids[j])] = d
    comprobar(2, "Pares de parcelas revisados", 19306, pares)
    comprobar(2, "Pares con contornos idénticos", 0, repetidos)
    comprobar(2, "Pares con contornos encimados (comparten superficie)", 0, encimados)
    comprobar(2, "Pares con contornos que se tocan sin encimarse", 0, contacto)
    anotar(2, "Par de parcelas más cercano, de orilla a orilla",
           f"{cercano[1]} y {cercano[2]}: {cercano[0]:.2f} m")
    anotar(2, "Pares con orillas a menos de 1 m / 5 m / 20 m",
           " / ".join(str(int(v)) for v in a_menos_de.values()))
    return catalogo, orillas_cercanas


def etapa_contorno(catalogo: pd.DataFrame, ruta: Path) -> pd.DataFrame:
    """Etapa 3: une la calificación de cada contorno, hecha sobre imagen satelital sin ver el rendimiento."""
    r = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    esperadas = ["ID_POLIGON", "categoria"] + MARCAS_CONTORNO + ["nota", "etapa", "confirmar_en_qgis", "fecha_revision"]
    comprobar(3, "Revisión de contornos: columnas", ", ".join(esperadas), ", ".join(r.columns))
    comprobar(3, "Revisión de contornos: no trae ninguna columna de rendimiento", True,
              not any("rend" in c.lower() for c in r.columns))
    comprobar(3, "Revisión de contornos: número de filas", 197, len(r))
    comprobar(3, "Revisión de contornos: identificadores distintos", 197, r.ID_POLIGON.nunique())
    comprobar(3, "Identificadores que están en la revisión y no en el catálogo, o al revés", 0,
              len(set(r.ID_POLIGON) ^ set(catalogo.id_parcela)))
    comprobar(3, "Categoría solo toma A, B o C", True, set(r.categoria) <= {"A", "B", "C"})
    comprobar(3, "Las cinco marcas solo toman si o no", True,
              all(set(r[m]) <= {"si", "no"} for m in MARCAS_CONTORNO))
    comprobar(3, "La firmeza solo toma los cuatro valores previstos", True, set(r.etapa) <= FIRMEZAS)

    u = catalogo.merge(r, left_on="id_parcela", right_on="ID_POLIGON", how="left", validate="one_to_one")
    comprobar(3, "Parcelas del catálogo que quedaron sin calificación de contorno", 0, int(u.categoria.isna().sum()))

    catalogo = catalogo.copy()
    catalogo["contorno_categoria"] = u.categoria.values
    for m in MARCAS_CONTORNO:
        catalogo[f"contorno_{m}"] = u[m].values
    catalogo["contorno_firmeza"] = u.etapa.values

    # Conteos del informe de la exploración de parcelas.
    cat = catalogo.contorno_categoria
    comprobar(3, "Parcelas en A / B / C", "175 / 12 / 10",
              " / ".join(str(int((cat == k).sum())) for k in "ABC"))
    comprobar(3, "Marcas: divisiones / árboles / construcción / angosta / imagen poco clara", "107 / 70 / 8 / 16 / 6",
              " / ".join(str(int((catalogo[f"contorno_{m}"] == "si").sum())) for m in MARCAS_CONTORNO))
    firme = catalogo.contorno_firmeza
    comprobar(3, "Confirmadas en QGIS / revisadas sin poder confirmar / primera pasada", "35 / 2 / 160",
              f"{int(firme.isin(CONFIRMADAS).sum())} / "
              f"{int((firme == 'revisado_en_qgis_sin_poder_confirmar').sum())} / "
              f"{int((firme == 'primera_pasada_sobre_imagen').sum())}")
    comprobar(3, "Parcelas en B o C que no están confirmadas en QGIS", 0,
              int((cat.isin(["B", "C"]) & ~firme.isin(CONFIRMADAS)).sum()))
    comprobar(3, "Parcelas de primera pasada que no están en A", 0,
              int(((firme == "primera_pasada_sobre_imagen") & (cat != "A")).sum()))
    mezcla = (cat.isin(["B", "C"]) | (catalogo.contorno_arboles_dentro == "si")
              | (catalogo.contorno_construccion_dentro == "si") | (catalogo.contorno_angosta_o_muy_pequena == "si"))
    comprobar(3, "Parcelas con algo dentro que mezcla la señal (B, C, árboles, construcción o angosta)", 96,
              int(mezcla.sum()))

    def abc(mascara):
        return " / ".join(str(int(((cat == k) & mascara).sum())) for k in "ABC")
    for escritura in sorted(catalogo.cultivo_origen.unique()):
        anotar(3, f"A / B / C en la escritura {escritura}", abc(catalogo.cultivo_origen == escritura))
    for conjunto in sorted(catalogo.conjunto_origen.unique()):
        anotar(3, f"A / B / C en {conjunto}", abc(catalogo.conjunto_origen == conjunto))
    anotar(3, "A / B / C en contornos de 5 puntos o menos", abc(catalogo.puntos_contorno <= 5))
    for municipio, grupo in catalogo.groupby("municipio"):
        c = grupo.contorno_categoria
        if (c != "A").any():
            anotar(3, f"A / B / C en {municipio}", " / ".join(str(int((c == k).sum())) for k in "ABC"))
    return catalogo


def decimales_escritos(texto: str) -> int:
    return len(texto.split(".")[1]) if "." in texto else 0


def es_multiplo(valor: float, paso: float) -> bool:
    return abs(valor / paso - round(valor / paso)) < 1e-6


def paso_comun(valores) -> str:
    """El escalón más grande del que todos los valores son múltiplos. Vacío con menos de 3 valores."""
    if len(valores) < 3:
        return ""
    for paso in (0.5, 0.1, 0.01):
        if all(es_multiplo(v, paso) for v in valores):
            return str(paso)
    return ""


def fila_precision(agrupacion, grupo, k, estado="", escritura=""):
    y = k.y
    cuenta = Counter(k.rendimiento_t_ha.astype(float))
    valor, veces = sorted(cuenta.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    return dict(agrupacion=agrupacion, grupo=grupo, estado=estado, cultivo_origen=escritura,
                parcelas_conocidas=len(k), rendimiento_minimo=y.min(), rendimiento_maximo=y.max(),
                valores_distintos=y.nunique(),
                con_0_decimales=int((k.dec == 0).sum()), con_1_decimal=int((k.dec == 1).sum()),
                con_2_decimales=int((k.dec == 2).sum()),
                multiplos_de_medio=int(k.medio.sum()), paso_comun=paso_comun(list(y)),
                valor_mas_repetido=valor, veces_valor_mas_repetido=veces,
                parcelas_con_valor_compartido=int(sum(n for n in cuenta.values() if n > 1)))


def etapa_precision(catalogo: pd.DataFrame, orillas_cercanas: dict):
    """Etapa 4: con qué finura está anotado el rendimiento y qué tanto se repite. No entrena nada."""
    catalogo = catalogo.copy()
    conocida = catalogo.rendimiento_t_ha != ""
    catalogo["rendimiento_decimales"] = [str(decimales_escritos(s)) if s else "" for s in catalogo.rendimiento_t_ha]
    catalogo["rendimiento_multiplo_de_medio"] = [("si" if es_multiplo(float(s), 0.5) else "no") if s else ""
                                                 for s in catalogo.rendimiento_t_ha]

    k = catalogo[conocida].copy()
    k["y"] = k.rendimiento_t_ha.astype(float)
    k["dec"] = k.rendimiento_decimales.astype(int)
    k["medio"] = k.rendimiento_multiplo_de_medio == "si"

    # Cifras generales ya obtenidas en auditorías previas del dataset.
    comprobar(4, "Rendimiento mínimo y máximo (t/ha)", "2.0 a 5.59", f"{k.y.min()} a {k.y.max()}")
    comprobar(4, "Rendimiento medio y mediano (t/ha)", "3.955 y 4.34", f"{k.y.mean():.3f} y {k.y.median():g}")
    comprobar(4, "Rendimientos distintos entre los 138", 67, int(k.y.nunique()))
    tres = sorted(Counter(k.y).items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    comprobar(4, "Los tres rendimientos más repetidos", "3.0 (19); 3.5 (13); 2.5 (11)",
              "; ".join(f"{v} ({n})" for v, n in tres))
    comprobar(4, "Rendimientos escritos con dos decimales", 80, int((k.dec == 2).sum()))
    comprobar(4, "Rendimientos escritos con uno o ningún decimal", 58, int((k.dec <= 1).sum()))
    anotar(4, "Rendimientos escritos con 0 / 1 / 2 decimales",
           " / ".join(str(int((k.dec == d).sum())) for d in (0, 1, 2)))
    for escritura, esperado in (("Cebada", "35 de 35"), ("CEBADA", "10 de 103")):
        g = k[k.cultivo_origen == escritura]
        comprobar(4, f"Múltiplos de 0.5 t/ha en la escritura {escritura}", esperado, f"{int(g.medio.sum())} de {len(g)}")
    comprobar(4, "Municipios con más de una escritura del campo Cultivo", 0,
              int((catalogo.groupby("municipio").cultivo_origen.nunique() > 1).sum()))

    # Tabla por municipio, por escritura y total.
    filas = []
    for municipio, g in k.groupby("municipio"):
        filas.append(fila_precision("municipio", municipio, g, g.estado.iloc[0], g.cultivo_origen.iloc[0]))
    filas.sort(key=lambda f: (-f["parcelas_conocidas"], f["grupo"]))
    for escritura in ("Cebada", "CEBADA"):
        filas.append(fila_precision("cultivo_origen", escritura, k[k.cultivo_origen == escritura]))
    filas.append(fila_precision("total", "todas", k))
    precision = pd.DataFrame(filas)

    # Finura por municipio: cuántas parcelas hay en cada escalón.
    paso_de = {f["grupo"]: f["paso_comun"] for f in filas if f["agrupacion"] == "municipio"}
    for paso in ("0.5", "0.1", "0.01"):
        municipios = sorted(m for m, p in paso_de.items() if p == paso)
        anotar(4, f"Municipios anotados en escalones de {paso} t/ha (parcelas conocidas)",
               f"{', '.join(municipios)} ({int(k.municipio.isin(municipios).sum())})")
    sin_paso = sorted(m for m, p in paso_de.items() if p == "")
    anotar(4, "Municipios con menos de 3 parcelas conocidas (finura no determinable)",
           "; ".join(f"{m}: {', '.join(k[k.municipio == m].rendimiento_t_ha)}" for m in sin_paso))

    # Último dígito de los rendimientos con dos decimales: si alguien redondea a ojo, sobran los 0 y los 5.
    ultimo = Counter(s[-1] for s in k.rendimiento_t_ha[k.dec == 2])
    anotar(4, "Último dígito de los rendimientos con dos decimales (dígito: veces)",
           "; ".join(f"{d}: {ultimo.get(d, 0)}" for d in "123456789"))

    # Si el rendimiento saliera de dividir toneladas redondas entre el área, rendimiento x área daría casi un entero.
    produccion = k.y * k.area_ha_origen.astype(float)
    lejania = (produccion - produccion.round()).abs().mean()
    anotar(4, "Distancia media de (rendimiento x área) a la tonelada entera más cercana; al azar sería 0.25",
           f"{lejania:.3f}")

    # Rendimientos idénticos entre parcelas cercanas del mismo municipio (distancia geodésica entre centros).
    geod = pyproj.Geod(ellps="WGS84")
    lon = k.centroide_lon.astype(float).values
    lat = k.centroide_lat.astype(float).values
    ids, y, mun = k.id_parcela.values, k.y.values, k.municipio.values
    grupos = {"escalones de 0.5": {m for m, p in paso_de.items() if p == "0.5"},
              "escalones de 0.1": {m for m, p in paso_de.items() if p == "0.1"},
              "escalones de 0.01": {m for m, p in paso_de.items() if p == "0.01"}}
    conteo = {(g, lim): [0, 0] for g in grupos for lim in (250, 500, 1000, None)}
    cercano_igual = {g: (math.inf, "", "") for g in grupos}
    for i, j in itertools.combinations(range(len(k)), 2):
        if mun[i] != mun[j]:
            continue
        g = next((g for g, ms in grupos.items() if mun[i] in ms), None)
        if g is None:
            continue
        d = geod.inv(lon[i], lat[i], lon[j], lat[j])[2]
        igual = y[i] == y[j]
        for lim in (250, 500, 1000, None):
            if lim is None or d < lim:
                conteo[(g, lim)][0] += 1
                conteo[(g, lim)][1] += igual
        if igual and d < cercano_igual[g][0]:
            cercano_igual[g] = (d, ids[i], ids[j])
    for g in grupos:
        partes = []
        for lim in (250, 500, 1000, None):
            pares, iguales = conteo[(g, lim)]
            partes.append(f"{'cualquier distancia' if lim is None else f'a menos de {lim} m'}: {int(iguales)} de {pares}")
        anotar(4, f"Pares del mismo municipio con rendimiento idéntico, municipios en {g}", "; ".join(partes))
        d, a, b = cercano_igual[g]
        if a:
            anotar(4, f"Par con rendimiento idéntico más cercano, municipios en {g}", f"{a} y {b}: {d:.0f} m entre centros")

    # Lo mismo para las parcelas pegadas (orillas a menos de 1, 5 y 20 m), cuando las dos son conocidas.
    rend = dict(zip(k.id_parcela, k.y))
    for lim in (1, 5, 20):
        ambos = [(a, b) for (a, b), d in orillas_cercanas.items() if d < lim and a in rend and b in rend]
        iguales = [(a, b) for a, b in ambos if rend[a] == rend[b]]
        anotar(4, f"Pares con orillas a menos de {lim} m: ambas conocidas / con rendimiento idéntico",
               f"{len(ambos)} / {len(iguales)}" + (f" ({'; '.join(a + ' y ' + b for a, b in iguales)})" if iguales else ""))
    escritura = dict(zip(k.id_parcela, k.cultivo_origen))
    municipio = dict(zip(k.id_parcela, k.municipio))
    for nombre in ("Cebada", "CEBADA"):
        ambos = [(a, b) for (a, b), d in orillas_cercanas.items()
                 if a in rend and b in rend and escritura[a] == nombre and escritura[b] == nombre]
        iguales = sum(rend[a] == rend[b] for a, b in ambos)
        anotar(4, f"Pares con orillas a menos de 20 m, ambas conocidas y de la escritura {nombre}: con rendimiento idéntico",
               f"{iguales} de {len(ambos)}")
    singuilucan = [(a, b) for (a, b), d in orillas_cercanas.items()
                   if a in rend and b in rend and municipio[a] == municipio[b] == "Singuilucan"]
    anotar(4, "Pares con orillas a menos de 20 m, ambas conocidas y de Singuilucan: con rendimiento idéntico",
           f"{sum(rend[a] == rend[b] for a, b in singuilucan)} de {len(singuilucan)}")
    return catalogo, precision


def guardar(tabla: pd.DataFrame, ruta: Path):
    tabla.to_csv(ruta, index=False, encoding="utf-8-sig", lineterminator="\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", type=Path, required=True, help="Carpeta DATASET_RETO_AGRO_2026")
    ap.add_argument("--salida", type=Path, default=SALIDA_POR_OMISION)
    ap.add_argument("--contornos", type=Path, default=CONTORNOS_POR_OMISION,
                    help="Tabla revision_contornos.csv de la exploración de parcelas")
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)

    catalogo, leidos, contornos = etapa_identidad(a.datos)
    catalogo, orillas_cercanas = etapa_geometria(catalogo, contornos)
    catalogo = etapa_contorno(catalogo, a.contornos)
    catalogo, precision = etapa_precision(catalogo, orillas_cercanas)

    huellas = pd.DataFrame([dict(archivo=r.relative_to(a.datos).as_posix(), bytes=r.stat().st_size,
                                 sha256=huella(r)) for r in leidos]
                           + [dict(archivo="exploracion_parcelas_qgis/revision_contornos/revision_contornos.csv",
                                   bytes=a.contornos.stat().st_size, sha256=huella(a.contornos))])
    comp = pd.DataFrame(comprobaciones)
    guardar(catalogo, a.salida / "catalogo_parcelas.csv")
    guardar(precision, a.salida / "precision_etiqueta_por_municipio.csv")
    guardar(comp, a.salida / "comprobaciones_catalogo.csv")
    guardar(huellas, a.salida / "huellas_archivos_leidos.csv")

    fallas = comp[comp.resultado == "NO CUMPLE"]
    print(comp.to_string(index=False))
    print(f"\ncatalogo_parcelas.csv: {catalogo.shape[0]} filas, {catalogo.shape[1]} columnas")
    print(f"Comprobaciones: {(comp.resultado == 'cumple').sum()} cumplen, {len(fallas)} no cumplen")
    if len(fallas):
        raise SystemExit("Hay comprobaciones que no se cumplen: revisar antes de usar el catálogo.")


if __name__ == "__main__":
    main()
