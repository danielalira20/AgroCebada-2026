"""Altitud de cada parcela (m) desde Terrain Tiles de AWS Open Data (formato terrarium, zoom 13), la misma fuente que
usa el mapa 3D de la app para el relieve. Así los bloques quedan apoyados sobre el terreno.

Uso (una vez, con internet, desde app/):  python herramientas/preparar_elevacion.py
Salida: datos_estaticos/elevacion_parcelas.csv  (ID_POLIGONO, elev_max_m, elev_centro_m)
"""
import io
import math
import os
import ssl
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from PIL import Image

AQUI = Path(__file__).resolve().parents[1]      # app/
sys.path.insert(0, str(AQUI))                   # para importar agrocebada_app desde app/

from agrocebada_app.backend.rutas.localizador import buscar_dataset  # noqa: E402

Z = 13
URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
ctx = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE"))
_cache = {}


def mosaico(x, y):
    if (x, y) not in _cache:
        with urllib.request.urlopen(URL.format(z=Z, x=x, y=y), context=ctx, timeout=30) as r:
            a = np.asarray(Image.open(io.BytesIO(r.read())).convert("RGB"), dtype=float)
        _cache[(x, y)] = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    return _cache[(x, y)]


def altitud(lon, lat):
    n = 2 ** Z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    x, y = int(fx), int(fy)
    px, py = min(int((fx - x) * 256), 255), min(int((fy - y) * 256), 255)
    return float(mosaico(x, y)[py, px])


def main(datos):
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(datos / "Parcelas_Reto_AGC_CONJUNTO_70_30.zip") as z:
        z.extractall(tmp)
        g = gpd.read_file(Path(tmp) / "Parcelas_Reto_AGC_CONJUNTO.shp").to_crs(4326)
    filas = []
    for pid, geom in zip(g.ID_POLIGON, g.geometry):
        partes = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        pts = [c for p in partes for c in p.simplify(0.00003).exterior.coords]
        c = geom.representative_point()
        filas.append(dict(ID_POLIGONO=pid, elev_max_m=round(max(altitud(p[0], p[1]) for p in pts), 1),
                          elev_centro_m=round(altitud(c.x, c.y), 1)))
    out = pd.DataFrame(filas).sort_values("ID_POLIGONO")
    out.to_csv(AQUI / "datos_estaticos" / "elevacion_parcelas.csv", index=False)
    print(f"{len(out)} parcelas · {len(_cache)} mosaicos · altitud {out.elev_centro_m.min():.0f}–{out.elev_centro_m.max():.0f} m")


if __name__ == "__main__":
    datos = Path(sys.argv[1]) if len(sys.argv) > 1 else buscar_dataset()      # AGRO_DATOS, data/raw/..., etc.
    if datos is None or not (datos / "Parcelas_Reto_AGC_CONJUNTO_70_30.zip").exists():
        raise SystemExit("No encontré el dataset del reto. Pásalo como argumento o fija AGRO_DATOS.")
    main(datos)
