"""Carga segura de un dataset propio para analizarlo con el mismo procedimiento de T08.

Sólo se aceptan dos formatos y todo lo demás se rechaza con un motivo concreto:
  1. ZIP con el formato del reto: una tabla CSV (ID_POLIGONO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO) y el shapefile de
     las parcelas (.shp, .shx, .dbf y .prj, sueltos o en un .zip dentro del ZIP) con los campos ID_POLIGON, Municipio y
     Cultivo.
  2. Un CSV simple (sin mapa): ID_POLIGONO, MUNICIPIO, GRUPO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO.

Seguridad: el archivo se trata sólo como datos (nada se ejecuta); se revisan tipo real, tamaño, cantidad de archivos,
tamaño descomprimido, compresión sospechosa, rutas, enlaces y cifrado antes de leer nada; los archivos se escriben con
nombres propios en una carpeta temporal que se borra al terminar, y el resultado vive sólo en la sesión de quien subió.
"""
import io
import re
import stat
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import geopandas as gpd
import numpy as np
import pandas as pd

from agro_datos import con_centroides

MAX_MB = 50
MAX_DESCOMPRIMIDO_MB = 200
MAX_ARCHIVOS = 30
MAX_COMPRESION = 100                 # descomprimido / comprimido por archivo (más que esto parece bomba zip)
MAX_PARCELAS = 5000
MIN_CON_COSECHA = 10
EXT_PERMITIDAS = {".csv", ".shp", ".shx", ".dbf", ".prj", ".cpg", ".zip"}
IGNORAR = re.compile(r"(^|/)(__MACOSX/|\.DS_Store$|Thumbs\.db$)")
COLS_TABLA = ["ID_POLIGONO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"]
COLS_SIMPLE = ["ID_POLIGONO", "MUNICIPIO", "GRUPO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"]
CAMPOS_SHP = {"ID_POLIGON": "ID_POLIGONO", "Municipio": "municipio", "Cultivo": "grupo_registro"}
RENDIMIENTO = (0.1, 15.0)            # t/ha aceptados en parcelas con cosecha
AREA = (0.01, 10000.0)               # ha
MEXICO = (-118.5, 14.0, -86.5, 33.0)
ID_VALIDO = re.compile(r"^[A-Za-z0-9_.\- ]{1,40}$")

REQUISITOS = f"""**Formato 1 · ZIP como el del reto (con mapa).** Un `.zip` que contenga:
- **Tabla de parcelas** (`.csv`, UTF-8, separada por comas) con las columnas `ID_POLIGONO`, `AREA_HA`,
  `RENDIMIENTO_T_HA` y `CONJUNTO`. `CONJUNTO` vale `ENTRENAMIENTO` (parcelas con cosecha, con rendimiento entre
  {RENDIMIENTO[0]} y {RENDIMIENTO[1]:.0f} t/ha) o `PREDICCION` (parcelas a estimar, con el rendimiento vacío).
- **Polígonos de las parcelas** en shapefile: `.shp`, `.shx`, `.dbf` y `.prj` (sueltos o dentro de otro `.zip`), con
  los campos `ID_POLIGON` (los mismos IDs de la tabla), `Municipio` y `Cultivo` (grupo de registro).

**Formato 2 · CSV simple (sin mapa).** Un `.csv` con las columnas `ID_POLIGONO`, `MUNICIPIO`, `GRUPO`, `AREA_HA`,
`RENDIMIENTO_T_HA` y `CONJUNTO`, con las mismas reglas.

**Se rechaza** cualquier otra cosa: otros tipos de archivo (Excel, PDF, imágenes, programas, etc.), archivos de más de
{MAX_MB} MB, ZIP con más de {MAX_ARCHIVOS} archivos, más de {MAX_DESCOMPRIMIDO_MB} MB descomprimido, con contraseña, con
rutas raras o enlaces, más de {MAX_PARCELAS:,} parcelas, menos de {MIN_CON_COSECHA} parcelas con cosecha o ninguna por
estimar, IDs repetidos o que no coinciden entre tabla y polígonos, valores fuera de rango y polígonos inválidos o fuera
de México. El archivo no se guarda: se analiza en memoria, se borra al terminar y nadie más lo ve."""


class Rechazo(Exception):
    """El archivo no cumple el formato o las reglas de seguridad; el mensaje dice por qué."""


@dataclass
class Resultado:
    datos: pd.DataFrame                               # índice ID_POLIGONO; GeoDataFrame si trae polígonos
    con_mapa: bool
    revisiones: list = field(default_factory=list)    # lo que se comprobó
    avisos: list = field(default_factory=list)        # lo que se ajustó sin rechazar


# ---------------------------------------------------------------- archivo
def revisar(nombre: str, contenido: bytes) -> Resultado:
    ext = Path(nombre or "").suffix.lower()
    if ext not in {".zip", ".csv"}:
        raise Rechazo(f"Tipo de archivo no permitido ({ext or 'sin extensión'}). Sólo se aceptan .zip o .csv.")
    if len(contenido) > MAX_MB * 1024 * 1024:
        raise Rechazo(f"El archivo pesa {len(contenido) / 1e6:.0f} MB; el máximo es {MAX_MB} MB.")
    if not contenido:
        raise Rechazo("El archivo está vacío.")
    if ext == ".zip":
        return _desde_zip(contenido)
    return _desde_csv_simple(contenido)


def _es_zip(b):
    return b[:4] == b"PK\x03\x04"


def _abrir_zip(contenido, nivel):
    if not _es_zip(contenido):
        raise Rechazo("El .zip no es un ZIP válido (su contenido real es de otro tipo).")
    try:
        z = zipfile.ZipFile(io.BytesIO(contenido))
    except zipfile.BadZipFile:
        raise Rechazo("El .zip está dañado o no es un ZIP válido.") from None
    entradas = [i for i in z.infolist() if not i.is_dir() and not IGNORAR.search(i.filename)]
    if len(entradas) > MAX_ARCHIVOS:
        raise Rechazo(f"El ZIP trae {len(entradas)} archivos; el máximo es {MAX_ARCHIVOS}.")
    total = 0
    for i in entradas:
        ruta = PurePosixPath(i.filename.replace("\\", "/"))
        if ruta.is_absolute() or ".." in ruta.parts or re.match(r"^[A-Za-z]:", i.filename):
            raise Rechazo(f"Ruta no permitida dentro del ZIP: {i.filename[:60]}")
        if stat.S_ISLNK(i.external_attr >> 16):
            raise Rechazo(f"El ZIP trae un enlace simbólico ({ruta.name}); no se permiten.")
        if i.flag_bits & 0x1:
            raise Rechazo("El ZIP tiene contraseña; súbelo sin cifrar.")
        if ruta.suffix.lower() not in EXT_PERMITIDAS:
            raise Rechazo(f"Archivo no permitido dentro del ZIP: {ruta.name[:60]}. Sólo .csv, .shp, .shx, .dbf, .prj, "
                          f".cpg y un .zip con el shapefile.")
        if ruta.suffix.lower() == ".zip" and nivel > 0:
            raise Rechazo("Hay un ZIP dentro de otro ZIP dentro de otro ZIP; sólo se permite un nivel.")
        if i.compress_size and i.file_size / i.compress_size > MAX_COMPRESION:
            raise Rechazo(f"{ruta.name[:60]} se descomprime demasiado (posible bomba zip).")
        total += i.file_size
        if total > MAX_DESCOMPRIMIDO_MB * 1024 * 1024:
            raise Rechazo(f"El ZIP descomprimido pasa de {MAX_DESCOMPRIMIDO_MB} MB.")
    return z, entradas, total


def _desde_zip(contenido):
    revisiones = []
    archivos = {}                     # nombre propio -> bytes (sin usar las rutas del ZIP)
    z, entradas, total = _abrir_zip(contenido, 0)
    pendientes = [(z, entradas)]
    vistos_zip = 0
    while pendientes:
        zz, ents = pendientes.pop()
        for i in ents:
            b = zz.read(i)
            if len(b) != i.file_size:
                raise Rechazo(f"{PurePosixPath(i.filename).name[:60]} no coincide con el tamaño declarado.")
            base = PurePosixPath(i.filename.replace("\\", "/")).name
            if base.lower().endswith(".zip"):
                vistos_zip += 1
                if vistos_zip > 1:
                    raise Rechazo("Sólo se permite un .zip interno (el del shapefile).")
                z2, e2, t2 = _abrir_zip(b, 1)
                total += t2
                if total > MAX_DESCOMPRIMIDO_MB * 1024 * 1024:
                    raise Rechazo(f"El ZIP descomprimido pasa de {MAX_DESCOMPRIMIDO_MB} MB.")
                pendientes.append((z2, e2))
                continue
            if base in archivos:
                raise Rechazo(f"Hay dos archivos con el mismo nombre ({base[:60]}).")
            archivos[base] = b
    revisiones.append(f"ZIP válido: {len(archivos)} archivos, {total / 1e6:.1f} MB descomprimido, sin rutas raras, "
                      "enlaces ni contraseña.")

    csvs = {n: b for n, b in archivos.items() if n.lower().endswith(".csv")}
    shps = [n for n in archivos if n.lower().endswith(".shp")]
    if not csvs:
        raise Rechazo("El ZIP no trae la tabla de parcelas (.csv).")
    tablas, simples = [], []
    for n, b in csvs.items():
        cols = _columnas(b)
        if all(c in cols for c in COLS_SIMPLE):
            simples.append(n)
        elif all(c in cols for c in COLS_TABLA):
            tablas.append(n)
    if not shps:
        if len(simples) == 1:
            res = _desde_csv_simple(csvs[simples[0]])
            res.revisiones.insert(0, revisiones[0])
            return res
        raise Rechazo("El ZIP no trae el shapefile de las parcelas (.shp, .shx, .dbf y .prj).")
    if len(tablas) != 1:
        faltan = ", ".join(COLS_TABLA)
        raise Rechazo(f"Se necesita exactamente una tabla .csv con las columnas {faltan}; encontré {len(tablas)}.")
    if len(shps) != 1:
        raise Rechazo(f"Se necesita exactamente un shapefile (.shp); encontré {len(shps)}.")
    raiz = shps[0][:-4]
    for ext in (".shx", ".dbf", ".prj"):
        if not any(n.lower() == (raiz + ext).lower() for n in archivos):
            raise Rechazo(f"Al shapefile le falta el archivo {raiz}{ext}.")

    tabla, rev, avisos = _tabla(csvs[tablas[0]], COLS_TABLA)
    revisiones += rev
    with tempfile.TemporaryDirectory() as tmp:
        for n, b in archivos.items():
            if n.lower().startswith(raiz.lower() + "."):
                ext = n[len(raiz):].lower()
                (Path(tmp) / f"parcelas{ext}").write_bytes(b)      # nombre propio, nunca la ruta del ZIP
        try:
            geo = gpd.read_file(Path(tmp) / "parcelas.shp", rows=MAX_PARCELAS + 1)
        except Exception:
            raise Rechazo("No pude leer el shapefile; revisa que .shp, .shx, .dbf y .prj sean del mismo archivo.") from None
    d, rev2 = _con_poligonos(tabla, geo)
    return Resultado(d, True, revisiones + rev2, avisos)


def _columnas(b):
    try:
        return set(pd.read_csv(io.BytesIO(b), nrows=0, encoding="utf-8-sig").columns.str.strip())
    except Exception:
        return set()


# ---------------------------------------------------------------- tabla
def _desde_csv_simple(contenido):
    if b"\x00" in contenido[:4096]:
        raise Rechazo("El .csv no es texto (parece un archivo binario).")
    cols = _columnas(contenido)
    faltan = [c for c in COLS_SIMPLE if c not in cols]
    if faltan:
        if all(c in cols for c in COLS_TABLA):
            raise Rechazo("Esta tabla es la del reto: súbela en un ZIP junto con el shapefile, o agrega las columnas "
                          "MUNICIPIO y GRUPO para usar el CSV simple.")
        raise Rechazo(f"Al CSV le faltan columnas: {', '.join(faltan)}.")
    tabla, rev, avisos = _tabla(contenido, COLS_SIMPLE)
    d = tabla.rename(columns={"MUNICIPIO": "municipio", "GRUPO": "grupo_registro"})
    d["Estado"] = ""
    return Resultado(d, False, rev, avisos)


def _texto(s, campo):
    s = s.astype("string").str.strip()
    if s.isna().any() or (s == "").any():
        raise Rechazo(f"Hay valores vacíos en {campo}.")
    if (s.str.len() > 60).any():
        raise Rechazo(f"Hay textos de más de 60 caracteres en {campo}.")
    return s.astype(str)


def _tabla(contenido, columnas):
    try:
        t = pd.read_csv(io.BytesIO(contenido), encoding="utf-8-sig", dtype=str, nrows=MAX_PARCELAS + 1,
                        skipinitialspace=True)
    except UnicodeDecodeError:
        raise Rechazo("El .csv no está en UTF-8; guárdalo como «CSV UTF-8».") from None
    except Exception:
        raise Rechazo("No pude leer el .csv; revisa que esté separado por comas.") from None
    t.columns = t.columns.str.strip()
    t = t[columnas]
    if len(t) > MAX_PARCELAS:
        raise Rechazo(f"La tabla tiene más de {MAX_PARCELAS:,} parcelas.")
    avisos, rev = [], []
    t["ID_POLIGONO"] = _texto(t.ID_POLIGONO, "ID_POLIGONO")
    malos = t.ID_POLIGONO[~t.ID_POLIGONO.str.match(ID_VALIDO)]
    if len(malos):
        raise Rechazo(f"IDs con caracteres no permitidos (sólo letras, números, _ . - y espacio): {malos.iloc[0][:40]}")
    if t.ID_POLIGONO.duplicated().any():
        raise Rechazo(f"IDs repetidos: {', '.join(t.ID_POLIGONO[t.ID_POLIGONO.duplicated()].head(3))}.")
    t["CONJUNTO"] = _texto(t.CONJUNTO, "CONJUNTO").str.upper()
    otros = sorted(set(t.CONJUNTO) - {"ENTRENAMIENTO", "PREDICCION"})
    if otros:
        raise Rechazo(f"CONJUNTO sólo puede ser ENTRENAMIENTO o PREDICCION; encontré: {', '.join(otros[:3])}.")
    area = pd.to_numeric(t.AREA_HA, errors="coerce")
    if area.isna().any() or not area.between(*AREA).all():
        raise Rechazo(f"AREA_HA debe ser un número entre {AREA[0]} y {AREA[1]:,.0f} ha en todas las parcelas.")
    y = pd.to_numeric(t.RENDIMIENTO_T_HA, errors="coerce")
    tr = t.CONJUNTO == "ENTRENAMIENTO"
    if y[tr].isna().any() or not y[tr].between(*RENDIMIENTO).all():
        raise Rechazo(f"RENDIMIENTO_T_HA debe estar entre {RENDIMIENTO[0]} y {RENDIMIENTO[1]:.0f} t/ha en todas las "
                      "parcelas de ENTRENAMIENTO.")
    if y[~tr].notna().any():
        avisos.append(f"{int(y[~tr].notna().sum())} parcelas de PREDICCION traían rendimiento; se ignoró.")
        y[~tr] = np.nan
    if tr.sum() < MIN_CON_COSECHA:
        raise Rechazo(f"Se necesitan al menos {MIN_CON_COSECHA} parcelas con cosecha (ENTRENAMIENTO); hay {int(tr.sum())}.")
    if (~tr).sum() == 0:
        raise Rechazo("No hay parcelas por estimar (CONJUNTO = PREDICCION).")
    for c in ("MUNICIPIO", "GRUPO"):
        if c in t:
            t[c] = _texto(t[c], c)
    d = t.assign(AREA_HA=area.astype(float), real=y.astype(float)).drop(columns="RENDIMIENTO_T_HA")
    rev.append(f"Tabla válida: {len(d)} parcelas, {int(tr.sum())} con cosecha y {int((~tr).sum())} por estimar; IDs "
               "únicos, áreas y rendimientos dentro de rango.")
    return d.set_index("ID_POLIGONO"), rev, avisos


# ---------------------------------------------------------------- polígonos
def _con_poligonos(tabla, geo):
    if len(geo) > MAX_PARCELAS:
        raise Rechazo(f"El shapefile tiene más de {MAX_PARCELAS:,} polígonos.")
    faltan = [c for c in CAMPOS_SHP if c not in geo.columns]
    if faltan:
        raise Rechazo(f"Al shapefile le faltan los campos: {', '.join(faltan)}.")
    if geo.crs is None:
        raise Rechazo("El shapefile no dice su sistema de coordenadas (falta o está vacío el .prj).")
    geo = geo.to_crs(4326).rename(columns=CAMPOS_SHP)
    geo["ID_POLIGONO"] = _texto(geo.ID_POLIGONO, "ID_POLIGON")
    geo["municipio"] = _texto(geo.municipio, "Municipio")
    geo["grupo_registro"] = _texto(geo.grupo_registro, "Cultivo")
    geo["Estado"] = geo["Estado"].fillna("").astype(str).str.slice(0, 60) if "Estado" in geo else ""
    if geo.ID_POLIGONO.duplicated().any():
        raise Rechazo("El shapefile tiene IDs repetidos en ID_POLIGON.")
    a, b = set(tabla.index), set(geo.ID_POLIGONO)
    if a != b:
        raise Rechazo(f"Los IDs no coinciden: {len(a - b)} de la tabla no están en los polígonos y {len(b - a)} "
                      "polígonos no están en la tabla.")
    if not geo.geom_type.isin(["Polygon", "MultiPolygon"]).all():
        raise Rechazo("Hay geometrías que no son polígonos.")
    invalidos = ~geo.is_valid
    if invalidos.any():
        geo.loc[invalidos, "geometry"] = geo.loc[invalidos].buffer(0)
        if not geo.is_valid.all() or geo.is_empty.any():
            raise Rechazo("Hay polígonos inválidos que no se pudieron reparar.")
    x0, y0, x1, y1 = geo.total_bounds
    if x0 < MEXICO[0] or y0 < MEXICO[1] or x1 > MEXICO[2] or y1 > MEXICO[3]:
        raise Rechazo("Hay polígonos fuera de México; revisa el sistema de coordenadas (.prj).")
    d = tabla.join(geo.set_index("ID_POLIGONO")[["municipio", "grupo_registro", "Estado", "geometry"]])
    d = con_centroides(gpd.GeoDataFrame(d, geometry="geometry", crs=4326))
    rev = [f"Polígonos válidos: {len(geo)} parcelas en {d.municipio.nunique()} municipios, IDs iguales a la tabla, "
           "dentro de México."]
    return d, rev


def plantilla_csv():
    """CSV de ejemplo del formato simple (IDs y valores inventados, sólo para mostrar las columnas)."""
    return ("ID_POLIGONO,MUNICIPIO,GRUPO,AREA_HA,RENDIMIENTO_T_HA,CONJUNTO\n"
            "P_001,Mi municipio,CEBADA,5.20,4.10,ENTRENAMIENTO\n"
            "P_002,Mi municipio,CEBADA,3.75,3.60,ENTRENAMIENTO\n"
            "P_003,Mi municipio,CEBADA,8.10,,PREDICCION\n").encode("utf-8")
