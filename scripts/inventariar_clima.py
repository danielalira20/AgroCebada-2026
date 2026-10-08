"""Inventario del ZIP original, sin extraerlo ni modificar sus archivos.

Comprueba los 48 meses de cada variable climática del paquete 2022–2025.
No extrae clima por parcela ni decide el corte temporal de los experimentos.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

import numpy as np
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile


PATRON = re.compile(r"(PREC|Tmin|Tmax)_(\d{4})_(\d{2})\.tif", re.I)
NOMBRES = {"prec": "PREC", "tmin": "Tmin", "tmax": "Tmax"}


def recorrer_zip(contenido, origen, profundidad=0):
    if profundidad > 5:
        raise ValueError("Demasiados niveles de ZIP anidados.")
    with zipfile.ZipFile(io.BytesIO(contenido)) as archivo:
        for entrada in archivo.infolist():
            ruta = Path(entrada.filename)
            if entrada.is_dir() or "__MACOSX" in ruta.parts or ruta.name == ".DS_Store":
                continue
            datos = archivo.read(entrada)  # La lectura comprueba el CRC del miembro.
            referencia = f"{origen}!/{entrada.filename}"
            if ruta.suffix.lower() == ".zip":
                yield from recorrer_zip(datos, referencia, profundidad + 1)
            else:
                yield referencia, ruta.name, datos


def inventariar(paquete):
    contenido = paquete.read_bytes()
    manifiesto, capas, documentos = [], [], []
    periodos = Counter()
    for origen, nombre, datos in recorrer_zip(contenido, paquete.name):
        manifiesto.append({"archivo": origen, "bytes": len(datos),
                           "sha256": hashlib.sha256(datos).hexdigest()})
        coincide = PATRON.fullmatch(nombre)
        if not coincide:
            if "leeme" in nombre.lower():
                documentos.append({"archivo": origen,
                                   "texto": datos.decode("utf-8-sig", errors="replace")})
            continue
        variable = NOMBRES[coincide[1].lower()]
        anio, mes = int(coincide[2]), int(coincide[3])
        periodos[variable, anio, mes] += 1
        with MemoryFile(datos) as memoria, memoria.open() as raster:
            if raster.count != 1 or raster.crs is None:
                raise ValueError(f"Banda o CRS no admisible: {origen}")
            valores = raster.read(1, masked=True)
            validos = valores.compressed()
            if not len(validos) or not np.isfinite(validos).all():
                raise ValueError(f"Sin valores válidos o con valores no finitos: {origen}")
            if variable == "PREC" and (validos < 0).any():
                raise ValueError(f"Precipitación válida negativa: {origen}")
            capas.append({
                "archivo": origen, "variable": variable, "anio": anio, "mes": mes,
                "crs": raster.crs.to_string(), "columnas": raster.width,
                "filas": raster.height, "resolucion": list(raster.res),
                "transformacion": list(raster.transform)[:6],
                "nodata": raster.nodata, "celdas_validas": len(validos),
                "celdas_nodata": int(np.ma.getmaskarray(valores).sum()),
                "minimo": float(validos.min()), "maximo": float(validos.max()),
                "media": float(validos.mean()), "etiquetas_raster": raster.tags(),
            })
    esperados = {(v, a, m) for v in NOMBRES.values()
                 for a in range(2022, 2026) for m in range(1, 13)}
    faltantes = sorted(esperados - set(periodos))
    extras = sorted(set(periodos) - esperados)
    duplicados = sorted(k for k, n in periodos.items() if n > 1)
    if faltantes or extras or duplicados:
        raise ValueError(f"Periodos climáticos: faltantes={faltantes}; "
                         f"extras={extras}; duplicados={duplicados}")
    return {
        "estado": "inventario_verificado", "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "paquete": str(paquete), "sha256_paquete": hashlib.sha256(contenido).hexdigest(),
        "archivos_finales": len(manifiesto), "capas_climaticas": len(capas),
        "capas_por_variable": dict(Counter(c["variable"] for c in capas)),
        "periodos": "2022-01 a 2025-12, un archivo por variable y mes",
        "alcance": "Integridad de archivos e inventario; no es extracción zonal ni cierre de T04.",
        "manifiesto": manifiesto, "capas": capas, "documentacion_original": documentos,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paquete", type=Path, required=True)
    parser.add_argument("--salida", type=Path, default=Path("reports/inventario_clima.json"))
    args = parser.parse_args()
    if args.paquete.resolve() == args.salida.resolve():
        parser.error("La salida no puede sobrescribir el paquete original.")
    try:
        informe = inventariar(args.paquete)
        texto = json.dumps(informe, ensure_ascii=False, indent=2, allow_nan=False)
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto + "\n", encoding="utf-8")
    except (OSError, ValueError, zipfile.BadZipFile, RasterioError) as error:
        print(f"Inventario fallido: {error}", file=sys.stderr)
        return 1
    print(json.dumps({k: informe[k] for k in (
        "estado", "sha256_paquete", "archivos_finales", "capas_climaticas",
        "capas_por_variable", "alcance")}, ensure_ascii=False, indent=2))
    print(f"Informe guardado en {args.salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
