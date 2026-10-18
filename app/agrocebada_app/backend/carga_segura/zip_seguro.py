"""Revisión de un ZIP subido (tipos, rutas, enlaces, tamaños, bombas zip) y lectura de lo que trae."""
import io
import re
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import geopandas as gpd

from agrocebada_app.backend.carga_segura.errores import Rechazo, Resultado
from agrocebada_app.backend.carga_segura.reglas import (
    COLS_SIMPLE, COLS_TABLA, EXT_PERMITIDAS, IGNORAR, MAX_ARCHIVOS, MAX_COMPRESION, MAX_DESCOMPRIMIDO_MB, MAX_PARCELAS)
from agrocebada_app.backend.carga_segura.tabla import columnas_de, con_poligonos, desde_csv_simple, leer_tabla


def es_zip(b):
    return b[:4] == b"PK\x03\x04"


def abrir_zip(contenido, nivel):
    if not es_zip(contenido):
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


def desde_zip(contenido):
    revisiones = []
    archivos = {}                     # nombre propio -> bytes (sin usar las rutas del ZIP)
    z, entradas, total = abrir_zip(contenido, 0)
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
                z2, e2, t2 = abrir_zip(b, 1)
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
        cols = columnas_de(b)
        if all(c in cols for c in COLS_SIMPLE):
            simples.append(n)
        elif all(c in cols for c in COLS_TABLA):
            tablas.append(n)
    if not shps:
        if len(simples) == 1:
            res = desde_csv_simple(csvs[simples[0]])
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

    tabla, rev, avisos = leer_tabla(csvs[tablas[0]], COLS_TABLA)
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
    d, rev2 = con_poligonos(tabla, geo)
    return Resultado(d, True, revisiones + rev2, avisos)
